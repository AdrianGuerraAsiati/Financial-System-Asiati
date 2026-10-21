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
  const orden = byId("cartera-drive-orden");
  let limite = 30;
  let offset = 0;
  let total = 0;
  let consultaActual = 0;
  let consultaSoporte = 0;
  let soportesActuales = [];
  let paginaSoportes = 1;
  const formulario = byId("cartera-drive-form");
  const tamanoOrdenes = document.createElement("select");
  tamanoOrdenes.id = "cartera-drive-por-pagina";
  [10, 20, 30, 50, 100].forEach((n) => tamanoOrdenes.add(new Option(String(n), String(n), false, n === 30)));
  const labelOrdenes = document.createElement("label");
  labelOrdenes.htmlFor = tamanoOrdenes.id;
  labelOrdenes.textContent = "Órdenes por página";
  labelOrdenes.appendChild(tamanoOrdenes);
  formulario.insertBefore(labelOrdenes, orden.closest("label"));
  tamanoOrdenes.addEventListener("change", () => {
    limite = Number(tamanoOrdenes.value) || 30;
    offset = 0;
    cargar();
  });
  orden.addEventListener("change", () => {
    offset = 0;
    cargar();
  });

  const filtroSoportes = document.createElement("input");
  filtroSoportes.type = "search";
  filtroSoportes.id = "cartera-drive-soportes-buscar";
  filtroSoportes.placeholder = "Archivo o carpeta";
  const labelSoportes = document.createElement("label");
  labelSoportes.htmlFor = filtroSoportes.id;
  labelSoportes.textContent = "Buscar soporte";
  labelSoportes.appendChild(filtroSoportes);
  const tamanoSoportes = document.createElement("select");
  tamanoSoportes.id = "cartera-drive-soportes-por-pagina";
  [10, 20, 50, 100].forEach((n) => tamanoSoportes.add(new Option(String(n), String(n), false, n === 20)));
  const labelTamano = document.createElement("label");
  labelTamano.htmlFor = tamanoSoportes.id;
  labelTamano.textContent = "Archivos por página";
  labelTamano.appendChild(tamanoSoportes);
  const controlesSoportes = document.createElement("div");
  controlesSoportes.className = "cartera-list-toolbar";
  controlesSoportes.append(labelSoportes, labelTamano);
  const pieSoportes = document.createElement("div");
  pieSoportes.className = "cartera-list-footer";
  const totalSoportes = document.createElement("span");
  totalSoportes.id = "cartera-drive-soportes-total";
  totalSoportes.className = "table-footnote";
  totalSoportes.setAttribute("aria-live", "polite");
  const navegacion = document.createElement("div");
  navegacion.className = "pagination";
  const anteriorSoportes = document.createElement("button");
  anteriorSoportes.type = "button";
  anteriorSoportes.textContent = "Anterior";
  anteriorSoportes.className = "secondary-button";
  anteriorSoportes.id = "cartera-drive-soportes-anterior";
  const paginaTextoSoportes = document.createElement("span");
  paginaTextoSoportes.className = "table-footnote";
  paginaTextoSoportes.id = "cartera-drive-soportes-pagina";
  const siguienteSoportes = document.createElement("button");
  siguienteSoportes.type = "button";
  siguienteSoportes.textContent = "Siguiente";
  siguienteSoportes.className = "secondary-button";
  siguienteSoportes.id = "cartera-drive-soportes-siguiente";
  navegacion.append(anteriorSoportes, paginaTextoSoportes, siguienteSoportes);
  pieSoportes.append(totalSoportes, navegacion);
  soporteEstado.after(controlesSoportes);
  soporteBody.closest(".table-wrap").after(pieSoportes);
  const normalizar = (v) => String(v ?? "").normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es-CO");

  function renderSoportes() {
    const filtro = normalizar(filtroSoportes.value.trim());
    const items = soportesActuales.filter((archivo) => !filtro ||
      [archivo.nombre, archivo.ruta, archivo.tipo_mime].some((v) =>
        normalizar(v).includes(filtro)));
    const porPagina = Number(tamanoSoportes.value) || 20;
    const paginas = Math.max(1, Math.ceil(items.length / porPagina));
    paginaSoportes = Math.min(Math.max(1, paginaSoportes), paginas);
    const desde = (paginaSoportes - 1) * porPagina;
    soporteBody.replaceChildren();
    for (const archivo of items.slice(desde, desde + porPagina)) {
      const tr = document.createElement("tr");
      celda(tr, archivo.nombre);
      celda(tr, archivo.ruta);
      celda(tr, archivo.revision);
      const td = celda(tr, "");
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
    if (!soporteBody.children.length) vaciarConMensaje(soporteBody, 4,
      filtro ? "No hay soportes que coincidan con el filtro." : "No se encontraron soportes.");
    totalSoportes.textContent = filtro
      ? items.length + " de " + soportesActuales.length + " soportes"
      : soportesActuales.length + " soportes";
    paginaTextoSoportes.textContent = "Página " + paginaSoportes + " de " + paginas;
    anteriorSoportes.disabled = paginaSoportes <= 1;
    siguienteSoportes.disabled = paginaSoportes >= paginas;
  }
  filtroSoportes.addEventListener("input", () => { paginaSoportes = 1; renderSoportes(); });
  tamanoSoportes.addEventListener("change", () => { paginaSoportes = 1; renderSoportes(); });
  anteriorSoportes.addEventListener("click", () => { paginaSoportes--; renderSoportes(); });
  siguienteSoportes.addEventListener("click", () => { paginaSoportes++; renderSoportes(); });

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
    ++consultaSoporte;
    byId("cartera-drive-refrescar").disabled = true;
    mensaje.textContent = "Consultando el índice documental…";
    vaciarConMensaje(body, 5, "Consultando…");
    soportePanel.hidden = true;
    const qs = new URLSearchParams({
      buscar: campo.value.trim(),
      orden: orden.value,
      limit: String(limite),
      offset: String(offset),
    });
    try {
      const data = await obtenerJson("/api/v1/cartera/ocs/drive/ordenes?" + qs);
      if (version !== consultaActual || panel.hidden) return;
      total = data.total;
      // Si cambió el índice mientras se navegaba, evitar página vacía huérfana.
      if (offset > 0 && data.items.length === 0 && total > 0) {
        offset = Math.max(0, Math.ceil(total / limite) - 1) * limite;
        cargar();
        return;
      }
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
      siguiente.disabled = offset + limite >= total;
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
    const solicitudSoporte = ++consultaSoporte;
    soportePanel.hidden = false;
    soportesActuales = [];
    paginaSoportes = 1;
    filtroSoportes.value = "";
    byId("cartera-drive-titulo").textContent = "Soportes · " + oc + " (referencia sin validar)";
    soporteEstado.textContent = "Consultando soportes…";
    vaciarConMensaje(soporteBody, 4, "Consultando…");
    try {
      const data = await obtenerJson(
        "/api/v1/cartera/ocs/drive/ordenes/" + encodeURIComponent(oc) + "/soportes"
      );
      if (version !== consultaActual || solicitudSoporte !== consultaSoporte || panel.hidden) return;
      soportesActuales = Array.isArray(data.items) ? data.items : [];
      renderSoportes();
      soporteEstado.textContent = data.total + " soporte(s) indexado(s), revisión más reciente por archivo.";
    } catch (error) {
      if (version !== consultaActual || solicitudSoporte !== consultaSoporte || panel.hidden) return;
      vaciarConMensaje(soporteBody, 4, error.message);
      soporteEstado.textContent = error.message;
    }
  }

  window.configurarCarteraDrive = function (sesion) {
    const global = sesion?.permisos?.["cartera.ver"] === "TODAS";
    panel.hidden = !global;
    ++consultaActual;
    ++consultaSoporte;
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
    offset = Math.max(0, offset - limite);
    cargar();
  });
  siguiente.addEventListener("click", () => {
    if (offset + limite < total) {
      offset += limite;
      cargar();
    }
  });
})();
