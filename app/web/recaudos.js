/* Ingresos reportados: no son abonos verificados ni pagos aplicados a Cartera. */
(function () {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const nuevo = $("#recaudos-nuevo");
  const filtros = $("#recaudos-filtros");
  const filas = $("#recaudos-filas");
  const detallePanel = $("#recaudos-detalle-panel");
  const limite = 25;
  let desplazamiento = 0;
  let total = 0;
  let empresaCargada = null;
  let secuencia = 0;

  function notificar(mensaje, error = false) {
    const elemento = $("#recaudos-estado");
    elemento.textContent = mensaje;
    elemento.className = error ? "status error" : "status ok";
  }

  function parametros() {
    const p = new URLSearchParams({ empresa_id: String(empresaId()), desde: String(desplazamiento), limite: String(limite) });
    ["buscar", "moneda", "desde_fecha", "hasta_fecha"].forEach((clave) => {
      const valor = String(filtros.elements.namedItem(clave).value || "").trim();
      if (valor) p.set(clave, valor);
    });
    return p;
  }

  function pintarFilas(registros) {
    filas.replaceChildren();
    if (!registros.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 7;
      td.className = "empty";
      td.textContent = "No hay ingresos reportados con estos filtros.";
      tr.append(td);
      filas.append(tr);
      return;
    }
    registros.forEach((x) => {
      const tr = document.createElement("tr");
      const datos = [
        x.fecha_reportada, x.referencia_origen, x.cuenta_receptora,
        x.pagador_reportado || "—", formatearDecimal(x.monto_reportado) + " " + x.moneda,
        "Pendiente de verificación",
      ];
      datos.forEach((valor) => {
        const td = document.createElement("td");
        td.textContent = valor;
        tr.append(td);
      });
      const accion = document.createElement("td");
      const boton = document.createElement("button");
      boton.type = "button";
      boton.className = "secondary-button";
      boton.textContent = "Abrir";
      boton.dataset.ingresoId = String(x.id);
      accion.append(boton);
      tr.append(accion);
      filas.append(tr);
    });
  }

  async function cargarBandeja() {
    const turno = ++secuencia;
    const empresaSolicitada = empresaId();
    if (!Number.isSafeInteger(empresaSolicitada) || empresaSolicitada < 1) {
      filas.replaceChildren();
      notificar("Selecciona una empresa para consultar.", true);
      return;
    }
    const respuesta = await api("/api/v1/recaudos/ingresos?" + parametros());
    if (turno !== secuencia || empresaId() !== empresaSolicitada) return;
    total = respuesta.total;
    pintarFilas(respuesta.items);
    const inicio = total ? desplazamiento + 1 : 0;
    $("#recaudos-pagina-info").textContent =
      inicio + "–" + (desplazamiento + respuesta.items.length) + " de " + total + " ingresos reportados";
    $("#recaudos-anterior").disabled = desplazamiento <= 0;
    $("#recaudos-siguiente").disabled = desplazamiento + respuesta.items.length >= total;
    notificar("Consulta completada. Ningún ingreso se considera conciliado.");
  }

  async function cargarTodo() {
    if (empresaCargada !== empresaId()) {
      filtros.reset();
      nuevo.reset();
      empresaCargada = empresaId();
    }
    desplazamiento = 0;
    detallePanel.hidden = true;
    nuevo.hidden = !window.recaudosPuedeRegistrar;
    $("#recaudos-sin-permiso").hidden = Boolean(window.recaudosPuedeRegistrar);
    try {
      await cargarBandeja();
    } catch (error) {
      notificar(error.message, true);
    }
  }

  async function abrir(id) {
    const empresaSolicitada = empresaId();
    try {
      const x = await api("/api/v1/recaudos/ingresos/" + id);
      if (empresaSolicitada !== empresaId()) return;
      detallePanel.hidden = false;
      $("#recaudos-detalle-titulo").textContent = "Ingreso reportado #" + x.id;
      const dl = $("#recaudos-detalle-contenido");
      dl.replaceChildren();
      const campos = [
        ["Estado", "Pendiente de verificación"],
        ["Fecha informada", x.fecha_reportada],
        ["Monto informado", formatearDecimal(x.monto_reportado) + " " + x.moneda],
        ["Referencia", x.referencia_origen],
        ["Cuenta receptora", x.cuenta_receptora],
        ["Pagador informado", x.pagador_reportado || "—"],
        ["Descripción", x.descripcion || "—"],
        ["Origen", "Captura manual"],
        ["Aplicación a Cartera", "No aplicada"],
        ["Validación bancaria", "No realizada"],
        ["Registro en sistema", x.registrado_at || "—"],
      ];
      campos.forEach(([etiqueta, valor]) => {
        const dt = document.createElement("dt");
        const dd = document.createElement("dd");
        dt.textContent = etiqueta;
        dd.textContent = valor;
        dl.append(dt, dd);
      });
    } catch (error) {
      notificar(error.message, true);
    }
  }

  nuevo.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!window.recaudosPuedeRegistrar) return;
    const empresaSolicitada = empresaId();
    const datos = Object.fromEntries(new FormData(nuevo).entries());
    datos.empresa_id = empresaSolicitada;
    datos.pagador_reportado = datos.pagador_reportado || null;
    datos.descripcion = datos.descripcion || null;
    try {
      const ingreso = await api("/api/v1/recaudos/ingresos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      });
      nuevo.reset();
      if (empresaSolicitada !== empresaId()) return;
      desplazamiento = 0;
      await cargarBandeja();
      await abrir(ingreso.id);
      notificar("Ingreso reportado guardado; no verificado ni aplicado a Cartera.");
    } catch (error) {
      notificar(error.message, true);
    }
  });

  filtros.addEventListener("submit", async (event) => {
    event.preventDefault();
    desplazamiento = 0;
    try { await cargarBandeja(); } catch (error) { notificar(error.message, true); }
  });
  $("#recaudos-limpiar").addEventListener("click", async () => {
    filtros.reset();
    desplazamiento = 0;
    try { await cargarBandeja(); } catch (error) { notificar(error.message, true); }
  });
  $("#recaudos-actualizar").addEventListener("click", async () => {
    try { await cargarBandeja(); } catch (error) { notificar(error.message, true); }
  });
  $("#recaudos-anterior").addEventListener("click", async () => {
    desplazamiento = Math.max(0, desplazamiento - limite);
    try { await cargarBandeja(); } catch (error) { notificar(error.message, true); }
  });
  $("#recaudos-siguiente").addEventListener("click", async () => {
    if (desplazamiento + limite >= total) return;
    desplazamiento += limite;
    try { await cargarBandeja(); } catch (error) { notificar(error.message, true); }
  });
  filas.addEventListener("click", (event) => {
    const boton = event.target.closest("button[data-ingreso-id]");
    if (boton && filas.contains(boton)) abrir(Number(boton.dataset.ingresoId));
  });
  window.cargarRecaudosTodo = cargarTodo;
})();
