// Cartera: inventario documental global de O.C., independiente de la fuente Sheets.
// Nunca sincroniza Drive desde el navegador ni interpreta importes financieros.
(() => {
  "use strict";
  const panel = document.getElementById("cartera-drive-panel");
  const byId = (id) => document.getElementById(id);
  const body = byId("cartera-drive-body");
  const resumen = byId("cartera-drive-resumen");
  const mensaje = byId("cartera-drive-mensaje");
  const soportePanel = byId("cartera-drive-soportes");
  const soporteBody = byId("cartera-drive-soportes-body");
  const soporteEstado = byId("cartera-drive-soportes-estado");
  const anterior = byId("cartera-drive-anterior");
  const siguiente = byId("cartera-drive-siguiente");
  const campo = byId("cartera-drive-buscar");
  const LIMITE = 30;
  let offset = 0;
  let total = 0;
  let consultaActual = 0;

  function celda(fila, valor) {
    const td = document.createElement("td");
    td.textContent = valor === null || valor === undefined || valor === "" ? "—" : String(valor);
    fila.appendChild(td);
    return td;
  }

  function vaciarConMensaje(target, columnas, texto) {
    const tr = document.createElement("tr");
    const td = celda(tr, texto);
    td.colSpan = columnas;
    td.className = "empty";
    target.replaceChildren(tr);
  }

  function fechaLegible(valor) {
    if (!valor) return "—";
    const fecha = new Date(valor);
    return Number.isNaN(fecha.getTime())
      ? "—"
      : fecha.toLocaleDateString("es-CO", { year: "numeric", month: "short", day: "numeric" });
  }

  async function obtenerJson(url) {
    const response = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
    let contenido;
    try { contenido = await response.json(); } catch (_) { contenido = null; }
    if (!response.ok) {
      if (response.status === 401) throw new Error("Tu sesión expiró. Ingresa nuevamente.");
      if (response.status === 403) throw new Error("El inventario requiere alcance global de Cartera.");
      throw new Error(contenido?.detail || "No fue posible consultar las órdenes documentales.");
    }
    return contenido;
  }

  async function cargar() {
    if (panel.hidden) return;
    const version = ++consultaActual;
    byId("cartera-drive-refrescar").disabled = true;
    mensaje.textContent = "Consultando el índice documental…";
    vaciarConMensaje(body, 5, "Consultando…");
    soportePanel.hidden = true;
    const qs = new URLSearchParams({
      buscar: campo.value.trim(),
      limit: String(LIMITE),
      offset: String(offset),
    });
    try {
      const data = await obtenerJson("/api/v1/cartera/ocs/drive/ordenes?" + qs);
      if (version !== consultaActual || panel.hidden) return;
      total = data.total;
      resumen.textContent =
        data.total_ocs_detectadas + " OC candidatas · " +
        data.archivos_vigentes + " archivos actuales · " +
        data.archivos_sin_oc + " archivos sin referencia GM.";
      body.replaceChildren();
      for (const item of data.items) {
        const tr = document.createElement("tr");
        celda(tr, item.numero_oc);
        celda(tr, item.soportes);
        celda(tr, fechaLegible(item.ultima_modificacion));
        celda(tr, "Sin validar");
        const td = celda(tr, "");
        const boton = document.createElement("button");
        boton.type = "button";
        boton.className = "secondary-button";
        boton.textContent = "Ver soportes";
        boton.addEventListener("click", () => cargarSoportes(item.numero_oc));
        td.appendChild(boton);
        body.appendChild(tr);
      }
      if (!data.items.length) vaciarConMensaje(body, 5, "No se encontraron órdenes para ese filtro o el índice aún no tiene documentos.");
      anterior.disabled = offset === 0;
      siguiente.disabled = offset + LIMITE >= total;
      byId("cartera-drive-pagina").textContent =
        total ? (offset + 1) + "–" + Math.min(offset + data.items.length, total) + " de " + total : "Sin resultados";
      mensaje.textContent = "Índice consultado. Para incorporar nuevos documentos, TI debe ejecutar la sincronización autorizada.";
    } catch (error) {
      if (version !== consultaActual || panel.hidden) return;
      vaciarConMensaje(body, 5, error.message);
      mensaje.textContent = error.message;
      anterior.disabled = true;
      siguiente.disabled = true;
    } finally {
      if (version === consultaActual) byId("cartera-drive-refrescar").disabled = false;
    }
  }

  async function cargarSoportes(oc) {
    if (panel.hidden) return;
    const version = consultaActual;
    soportePanel.hidden = false;
    byId("cartera-drive-titulo").textContent = "Soportes · " + oc + " (referencia sin validar)";
    soporteEstado.textContent = "Consultando soportes…";
    vaciarConMensaje(soporteBody, 4, "Consultando…");
    try {
      const data = await obtenerJson(
        "/api/v1/cartera/ocs/drive/ordenes/" + encodeURIComponent(oc) + "/soportes"
      );
      if (version !== consultaActual || panel.hidden) return;
      soporteBody.replaceChildren();
      for (const archivo of data.items) {
        const tr = document.createElement("tr");
        celda(tr, archivo.nombre);
        celda(tr, archivo.ruta);
        celda(tr, archivo.revision);
        const td = celda(tr, "");
        // Nunca convertir el nombre ni un valor arbitrario de API en HTML/JS ejecutable.
        if (/^https:\/\/drive\.google\.com\/file\/d\/[A-Za-z0-9_-]+\/view$/.test(archivo.url_origen)) {
          const enlace = document.createElement("a");
          enlace.href = archivo.url_origen;
          enlace.textContent = "Abrir original";
          enlace.target = "_blank";
          enlace.rel = "noopener noreferrer";
          td.appendChild(enlace);
        }
        soporteBody.appendChild(tr);
      }
      soporteEstado.textContent = data.total + " soporte(s) indexado(s), revisión más reciente por archivo.";
    } catch (error) {
      if (version !== consultaActual || panel.hidden) return;
      vaciarConMensaje(soporteBody, 4, error.message);
      soporteEstado.textContent = error.message;
    }
  }

  window.configurarCarteraDrive = function (sesion) {
    const global = sesion?.permisos?.["cartera.ver"] === "TODAS";
    panel.hidden = !global;
    ++consultaActual;
    if (!global) {
      vaciarConMensaje(body, 5, "Sin acceso al inventario multiempresa.");
      soportePanel.hidden = true;
    }
  };
  window.cargarCarteraDrive = cargar;

  byId("cartera-drive-form").addEventListener("submit", (event) => {
    event.preventDefault();
    offset = 0;
    cargar();
  });
  byId("cartera-drive-refrescar").addEventListener("click", cargar);
  anterior.addEventListener("click", () => {
    offset = Math.max(0, offset - LIMITE);
    cargar();
  });
  siguiente.addEventListener("click", () => {
    if (offset + LIMITE < total) {
      offset += LIMITE;
      cargar();
    }
  });
})();
