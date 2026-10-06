
(function () {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const estado = $("#estado-wallets");
  const panelConciliar = $("#wallets-conciliar-panel");
  const form = $("#wallets-form");
  const periodo = $("#wallets-periodo");
  const tipo = $("#wallets-tipo");
  const identidadWrap = $("#wallets-identidad-wrap");
  const identidad = $("#wallets-identidad");
  const fuenteWallet = $("#wallets-fuente-wallet");
  const fuenteOrdenesWrap = $("#wallets-fuente-ordenes-wrap");
  const fuenteOrdenes = $("#wallets-fuente-ordenes");
  const corteWrap = $("#wallets-corte-wrap");
  const corte = $("#wallets-corte");
  const archivoWallet = $("#wallets-archivo-wallet");
  const archivoOrdenesWrap = $("#wallets-archivo-ordenes-wrap");
  const archivoOrdenes = $("#wallets-archivo-ordenes");
  const avisoForm = $("#wallets-form-aviso");
  const conciliar = $("#wallets-conciliar");

  const c0Panel = $("#wallets-c0-panel");
  const c0Estado = $("#wallets-c0-estado");
  const c0Inicial = $("#wallets-c0-inicial");
  const c0Entradas = $("#wallets-c0-entradas");
  const c0Salidas = $("#wallets-c0-salidas");
  const c0Final = $("#wallets-c0-final");
  const c0Mensaje = $("#wallets-c0-mensaje");
  const c0Cobertura = $("#wallets-c0-cobertura");
  const c0Corte = $("#wallets-c0-corte");

  const resumenPanel = $("#wallets-resumen-panel");
  const resumen = $("#wallets-resumen");
  const hallazgosPanel = $("#wallets-hallazgos-panel");
  const hallazgosBody = $("#wallets-hallazgos-body");
  const filtroGravedad = $("#wallets-filtro-gravedad");
  const filtroEstado = $("#wallets-filtro-estado");
  const todasCargas = $("#wallets-todas-cargas");
  const recargarHallazgos = $("#wallets-recargar-hallazgos");
  const dialog = $("#wallets-hallazgo-dialog");
  const detalle = $("#wallets-hallazgo-detalle");
  const acciones = $("#wallets-hallazgo-acciones");

  let catalogo = {wiilog: false, tiendas: [], pagos: []};
  let periodos = [];
  let fuentes = [];
  let hallazgos = [];
  let cargandoContexto = false;

  const SIGNIFICADOS = {
    ganancia_por_estado: "T1 · Ganancia. Neto = pagos − correcciones de guía. Ventana: 2 días desde la entrega. Tolerancia: 1 peso.",
    sin_recaudo_cobro: "T2 · Orden sin recaudo. Cobro al crear la orden = PRECIO PROVEEDOR X CANTIDAD + PRECIO FLETE, una vez.",
    sin_recaudo_reembolso: "T2 · Reembolso: CANCELADO o RECHAZADO = todo lo cobrado; DEVOLUCION = solo el producto (el flete se pierde).",
    devolucion_por_estado: "T3 · Devolución con recaudo. Un solo cobro por devolución y es el mismo flete, pero sin la comisión de recaudo.",
    fulfillment_por_estado: "T4 · Fulfillment al proveedor. Tarifa de la bodega una vez por orden; Dropi la reparte entre líneas.",
    fuera_del_reporte: "Movimientos de órdenes que no son de la tienda en el reporte, con motivo.",
    movimientos: "Cada movimiento recibe un concepto por el texto de Dropi y de ahí: ingreso/egreso, unidad de negocio, categoría y requiere revisión.",
    por_revisar: "Los movimientos con requiere_revision quedan para confirmación del conciliador con observación obligatoria."
  };

  function empresaIdWallets() {
    return Number($("#empresa-id").value);
  }

  function permisos() {
    return (window.ASIATI_SESION && window.ASIATI_SESION.permisos) || {};
  }

  function puede(codigo) {
    return Boolean(permisos()[codigo]);
  }

  function setEstadoWallets(texto, clase) {
    estado.textContent = texto;
    estado.className = ("status " + (clase || "")).trim();
  }

  function escapar(valor) {
    const div = document.createElement("div");
    div.textContent = valor === null || valor === undefined ? "" : String(valor);
    return div.innerHTML;
  }

  async function walletApi(url, options) {
    const response = await fetch(url, options || {});
    let body = null;
    try {
      body = await response.json();
    } catch (_) {}
    if (!response.ok) {
      if (response.status === 401 && typeof window.mostrarLogin === "function") {
        window.mostrarLogin();
      }
      throw new Error((body && body.detail) || ("Error HTTP " + response.status));
    }
    return body;
  }

  function periodoActual() {
    return periodos.find((item) => String(item.id) === periodo.value) || null;
  }

  function contextoKey() {
    return [
      "asiati_wallets_result",
      empresaIdWallets(),
      periodo.value || "sin-periodo",
      tipo.value || "sin-tipo",
      identidad.value || "-"
    ].join(":");
  }

  function llenarSelect(select, items, valueKey, labelFn, placeholder) {
    const previo = select.value;
    let html = placeholder ? '<option value="">' + escapar(placeholder) + "</option>" : "";
    html += items.map((item) =>
      '<option value="' + escapar(item[valueKey]) + '">' + escapar(labelFn(item)) + "</option>"
    ).join("");
    select.innerHTML = html;
    if (items.some((item) => String(item[valueKey]) === previo)) {
      select.value = previo;
    }
  }

  function renderPeriodos() {
    llenarSelect(
      periodo,
      periodos,
      "id",
      (item) => item.fecha_inicio + " → " + item.fecha_fin + (item.cerrado ? " · Cerrado" : " · Abierto"),
      periodos.length ? null : "No hay períodos"
    );
  }

  function preseleccionarUnica(select, items, valueKey) {
    if (items.length === 1 && !select.value) select.value = String(items[0][valueKey]);
  }

  function renderFuentes() {
    llenarSelect(fuenteWallet, fuentes, "id", (item) => item.nombre, "Selecciona una fuente");
    llenarSelect(fuenteOrdenes, fuentes, "id", (item) => item.nombre, "Selecciona una fuente");
    preseleccionarUnica(fuenteWallet, fuentes, "id");
    preseleccionarUnica(fuenteOrdenes, fuentes, "id");
  }

  function renderTipos() {
    const opciones = [];
    if (catalogo.wiilog) opciones.push({id: "wiilog", nombre: "Wiilog marca blanca"});
    if (catalogo.tiendas && catalogo.tiendas.length) opciones.push({id: "tienda", nombre: "Tienda"});
    if (catalogo.pagos && catalogo.pagos.length) opciones.push({id: "pagos", nombre: "Pagos"});
    llenarSelect(tipo, opciones, "id", (item) => item.nombre, opciones.length ? null : "Sin wallets configuradas");
  }

  function actualizarTipo() {
    const valor = tipo.value;
    const esTienda = valor === "tienda";
    const esPagos = valor === "pagos";
    const usaOrdenes = valor === "wiilog" || esTienda;

    identidadWrap.hidden = !(esTienda || esPagos);
    fuenteOrdenesWrap.hidden = !usaOrdenes;
    archivoOrdenesWrap.hidden = !usaOrdenes;
    corteWrap.hidden = !esTienda;
    fuenteOrdenes.required = usaOrdenes;
    archivoOrdenes.required = usaOrdenes;

    const lista = esTienda ? catalogo.tiendas : esPagos ? catalogo.pagos : [];
    llenarSelect(
      identidad,
      lista,
      "usuario_email",
      (item) => item.nombre + " · " + item.usuario_email,
      lista.length ? null : "No hay opciones para esta empresa"
    );

    actualizarDisponibilidadConciliacion();
  }

  function actualizarDisponibilidadConciliacion() {
    const actual = periodoActual();
    const ejecuta = puede("conciliacion.ejecutar");
    const cerrado = Boolean(actual && actual.cerrado);
    const disponible = Boolean(actual && tipo.value);

    conciliar.hidden = !ejecuta;
    fuenteWallet.closest("label").hidden = !ejecuta;
    archivoWallet.closest("label").hidden = !ejecuta;
    fuenteOrdenesWrap.hidden = !ejecuta || !(tipo.value === "wiilog" || tipo.value === "tienda");
    archivoOrdenesWrap.hidden = !ejecuta || !(tipo.value === "wiilog" || tipo.value === "tienda");
    corteWrap.hidden = !ejecuta || tipo.value !== "tienda";

    conciliar.disabled = !ejecuta || cerrado || !disponible;
    avisoForm.hidden = false;
    if (!ejecuta) {
      avisoForm.textContent = "Tu rol puede consultar conciliaciones y hallazgos, pero no ejecutar nuevas conciliaciones.";
    } else if (!actual) {
      avisoForm.textContent = "No hay un período disponible para esta empresa.";
    } else if (cerrado) {
      avisoForm.textContent = "Este período está cerrado. Reábrelo antes de ejecutar una conciliación.";
    } else if (!tipo.value) {
      avisoForm.textContent = "La empresa no tiene wallets configuradas en el catálogo del motor.";
    } else {
      avisoForm.hidden = true;
      avisoForm.textContent = "";
    }
  }

  function fechaDesdeNombre(nombre) {
    const match = String(nombre || "").match(/_(\d{8})_(\d{6})(?:\D|$)/);
    if (!match) return "";
    const f = match[1];
    const h = match[2];
    return f.slice(0, 4) + "-" + f.slice(4, 6) + "-" + f.slice(6, 8) +
      "T" + h.slice(0, 2) + ":" + h.slice(2, 4) + ":" + h.slice(4, 6);
  }

  function gravedadDe(hallazgo) {
    const explicita = hallazgo.gravedad || (hallazgo.evidencia && hallazgo.evidencia.gravedad);
    if (explicita) return String(explicita).toUpperCase();
    return hallazgo.critico ? "CRITICO" : "MEDIO";
  }

  function textoGravedad(valor) {
    const mapa = {
      CRITICO: "CRÍTICO",
      MEDIO: "MEDIO",
      INFORMATIVO: "INFORMATIVO",
      REVISAR: "REVISAR"
    };
    return mapa[valor] || valor;
  }

  function estadoDe(hallazgo) {
    if (hallazgo.estado) return hallazgo.estado;
    return hallazgo.resuelto ? "resuelto" : "detectado";
  }

  function textoEstado(valor) {
    const mapa = {
      detectado: "DETECTADO",
      en_gestion: "EN GESTIÓN",
      escalado: "ESCALADO",
      resuelto: "RESUELTO"
    };
    return mapa[valor] || String(valor || "DETECTADO").replaceAll("_", " ").toUpperCase();
  }

  function esRevisarMovimiento(h) {
    return Boolean(h.evidencia && h.evidencia.tipo === "REVISAR_MOVIMIENTO");
  }

  function textoEstadoDe(h) {
    const texto = textoEstado(estadoDe(h));
    return h.resuelto_por_sistema ? texto + " · SISTEMA" : texto;
  }

  function referenciaDe(h) {
    const e = h.evidencia || {};
    if (esRevisarMovimiento(h)) {
      return String(e.fecha || "").slice(0, 16) + " · Mov. " + e.mov_id;
    }
    return e.orden_id || e.mov_id || e.wallet || "—";
  }

  function montoDe(h) {
    const e = h.evidencia || {};
    const valor = e.monto_en_juego || e.monto || e.neto || (e.detalle && e.detalle.monto_en_juego);
    if (!valor) return "—";
    const texto = /^-?\d+(\.\d+)?$/.test(String(valor)) ? pesos(valor) : String(valor);
    return esRevisarMovimiento(h) && e.entrada_salida ? e.entrada_salida + " " + texto : texto;
  }

  function dimensionesTexto(datos) {
    return [datos.categoria, datos.unidad_negocio, datos.ingreso_egreso].map((v) => v || "sin definir").join(" · ");
  }

  function descripcionHtml(h) {
    const e = h.evidencia || {};
    if (!esRevisarMovimiento(h)) return escapar(h.descripcion);
    const categorizacion = e.categorizacion;
    const linea = categorizacion
      ? "Categorizado: " + dimensionesTexto(categorizacion)
      : "Propuesta del motor: " + dimensionesTexto(e);
    return (e.texto_nuevo ? '<span class="wallet-pill wallet-gravedad-revisar">TEXTO NUEVO DE DROPI</span> ' : "") +
      escapar(e.texto_dropi || h.descripcion) +
      "<br><small>Tercero: " + escapar(e.tercero || "—") + " · " + escapar(linea) + "</small>";
  }

  function renderHallazgos() {
    const gravedad = filtroGravedad.value;
    const estadoFiltro = filtroEstado.value;
    const visibles = hallazgos.filter((h) =>
      (!gravedad || gravedadDe(h) === gravedad) &&
      (!estadoFiltro || estadoDe(h) === estadoFiltro)
    );

    if (!visibles.length) {
      hallazgosBody.innerHTML = '<tr><td colspan="6" class="empty">No hay hallazgos para estos filtros.</td></tr>';
      return;
    }

    hallazgosBody.innerHTML = visibles.map((h) => {
      const g = gravedadDe(h);
      const est = estadoDe(h);
      return "<tr>" +
        '<td><span class="wallet-pill wallet-gravedad-' + escapar(g.toLowerCase()) + '">' + escapar(textoGravedad(g)) + "</span></td>" +
        "<td>" + escapar(referenciaDe(h)) + "</td>" +
        "<td>" + descripcionHtml(h) + "</td>" +
        "<td>" + escapar(montoDe(h)) + "</td>" +
        '<td><span class="wallet-pill wallet-estado-' + escapar(est) + '">' + escapar(textoEstadoDe(h)) + "</span></td>" +
        '<td><button type="button" class="secondary-button wallet-detalle" data-hallazgo-id="' + escapar(h.id) + '">Detalle</button></td>' +
        "</tr>";
    }).join("");

    hallazgosBody.querySelectorAll(".wallet-detalle").forEach((button) => {
      button.addEventListener("click", () => abrirHallazgo(Number(button.dataset.hallazgoId)));
    });
  }

  function endpointHallazgos() {
    const base = "/api/v1/wallets/";
    if (tipo.value === "wiilog") return base + "wiilog/hallazgos";
    if (tipo.value === "tienda") return base + "tiendas/hallazgos";
    if (tipo.value === "pagos") return base + "pagos/hallazgos";
    return null;
  }

  async function cargarHallazgos() {
    const endpoint = endpointHallazgos();
    if (!endpoint || !periodo.value) {
      hallazgos = [];
      renderHallazgos();
      return;
    }
    hallazgosBody.innerHTML = '<tr><td colspan="6" class="empty">Cargando hallazgos…</td></tr>';
    const params = new URLSearchParams({
      empresa_id: String(empresaIdWallets()),
      periodo_id: periodo.value
    });
    if (tipo.value === "tienda" && identidad.value) params.set("tienda", identidad.value);
    if (tipo.value === "pagos" && identidad.value) params.set("wallet_pagos", identidad.value);
    if (todasCargas.checked) params.set("todas_las_cargas", "true");

    try {
      hallazgos = await walletApi(endpoint + "?" + params.toString());
      renderHallazgos();
    } catch (error) {
      hallazgos = [];
      hallazgosBody.innerHTML = '<tr><td colspan="6" class="empty">' + escapar(error.message) + "</td></tr>";
    }
  }

  const ORIGEN_CORTE = {
    formulario: "hora escrita en el formulario",
    nombre_archivo: "tomada del nombre del archivo",
    fecha_de_reporte: "fin del día de FECHA DE REPORTE"
  };

  function pesos(valor) {
    // Los montos llegan como texto decimal; formatearDecimal (app.js) no pasa por float.
    if (valor === null || valor === undefined || valor === "") return "—";
    const texto = String(valor).trim();
    if (texto.startsWith("-")) return "-$ " + formatearDecimal(texto.slice(1));
    return "$ " + formatearDecimal(texto);
  }

  function mensajeNoCuadra(quiebres) {
    const puntos = Number(quiebres) === 1 ? "1 punto" : String(quiebres ?? "varios") + " puntos";
    return "El saldo no cuadra en " + puntos + ". " +
      "El archivo puede estar incompleto: descárgalo de nuevo de Dropi y vuelve a conciliar.";
  }

  function mostrarC0(data) {
    if (!data || !data.c0) {
      c0Panel.hidden = true;
      return;
    }
    const c0 = data.c0;
    c0Panel.hidden = false;
    c0Estado.textContent = c0.cuadra ? "CUADRA" : "NO CUADRA";
    c0Estado.className = "wallet-pill " + (c0.cuadra ? "wallet-pill-ok" : "wallet-pill-danger");
    c0Inicial.textContent = pesos(c0.saldo_inicial);
    c0Entradas.textContent = pesos(c0.entradas);
    c0Salidas.textContent = pesos(c0.salidas);
    c0Final.textContent = pesos(c0.saldo_final);
    c0Mensaje.textContent = c0.cuadra ? (c0.mensaje || "") : mensajeNoCuadra(c0.quiebres);
    const cobertura = c0.cobertura;
    c0Cobertura.hidden = !cobertura || cobertura.estado === "EN_ORDEN";
    c0Cobertura.textContent = cobertura && cobertura.estado !== "EN_ORDEN"
      ? "Cobertura: " + cobertura.mensaje
      : "";
    const corteUsado = data.corte_ordenes_usado;
    c0Corte.hidden = !corteUsado;
    c0Corte.textContent = corteUsado
      ? "Corte del reporte de órdenes: " + corteUsado.valor + " · " + (ORIGEN_CORTE[corteUsado.origen] || corteUsado.origen)
      : "";
  }

  function valorResumen(valor) {
    if (valor === null || valor === undefined) return "—";
    if (typeof valor !== "object") return escapar(valor);
    if (Array.isArray(valor)) return escapar(valor.join(", "));
    const filas = Object.entries(valor);
    if (!filas.length) return '<span class="muted">Sin registros</span>';
    return '<div class="wallet-summary-rows">' + filas.map(([clave, dato]) => {
      const texto = typeof dato === "object" && dato !== null
        ? Object.entries(dato).map(([k, v]) => escapar(k) + ": " + escapar(v)).join(" · ")
        : escapar(dato);
      return "<div><span>" + escapar(clave) + "</span><strong>" + texto + "</strong></div>";
    }).join("") + "</div>";
  }

  function mostrarResumen(data) {
    if (!data || data.bloqueado || !data.resumen) {
      resumenPanel.hidden = true;
      return;
    }
    resumenPanel.hidden = false;
    resumen.innerHTML = Object.entries(data.resumen).map(([clave, valor]) => {
      const significado = SIGNIFICADOS[clave];
      return '<article class="wallet-summary-card">' +
        "<h4>" + escapar(clave.replaceAll("_", " ")) + "</h4>" +
        (significado ? "<p>" + escapar(significado) + "</p>" : "") +
        valorResumen(valor) +
        "</article>";
    }).join("");
  }

  function guardarResultado(data) {
    sessionStorage.setItem(contextoKey(), JSON.stringify({
      guardado_en: new Date().toISOString(),
      resultado: data
    }));
  }

  function restaurarResultado() {
    c0Panel.hidden = true;
    resumenPanel.hidden = true;
    hallazgosPanel.hidden = false;
    const crudo = sessionStorage.getItem(contextoKey());
    if (!crudo) return;
    try {
      const guardado = JSON.parse(crudo);
      mostrarC0(guardado.resultado);
      mostrarResumen(guardado.resultado);
      hallazgosPanel.hidden = Boolean(guardado.resultado && guardado.resultado.bloqueado);
    } catch (_) {
      sessionStorage.removeItem(contextoKey());
    }
  }

  function endpointConciliar() {
    if (tipo.value === "wiilog") return "/api/v1/wallets/wiilog/conciliar";
    if (tipo.value === "tienda") return "/api/v1/wallets/tiendas/conciliar";
    if (tipo.value === "pagos") return "/api/v1/wallets/pagos/conciliar";
    return null;
  }

  async function enviarConciliacion(event) {
    event.preventDefault();
    const actual = periodoActual();
    if (!puede("conciliacion.ejecutar")) return;
    if (!actual || actual.cerrado) {
      setEstadoWallets("El período está cerrado. Reábrelo antes de conciliar.", "error");
      return;
    }

    const endpoint = endpointConciliar();
    if (!endpoint) {
      setEstadoWallets("Selecciona un tipo de wallet.", "error");
      return;
    }

    const data = new FormData();
    data.set("empresa_id", String(empresaIdWallets()));
    data.set("periodo_id", periodo.value);
    data.set("fuente_wallet_id", fuenteWallet.value);
    data.set("wallet", archivoWallet.files[0]);

    if (tipo.value === "wiilog" || tipo.value === "tienda") {
      data.set("fuente_ordenes_id", fuenteOrdenes.value);
      data.set("ordenes", archivoOrdenes.files[0]);
    }
    if (tipo.value === "tienda") {
      data.set("tienda", identidad.value);
      if (corte.value) data.set("corte_ordenes", corte.value);
    }
    if (tipo.value === "pagos") {
      data.set("wallet_pagos", identidad.value);
    }

    const textoOriginal = conciliar.textContent;
    conciliar.disabled = true;
    conciliar.textContent = "Conciliando…";
    setEstadoWallets("Procesando archivos…", "");

    try {
      const resultado = await walletApi(endpoint, {method: "POST", body: data});
      guardarResultado(resultado);
      mostrarC0(resultado);
      mostrarResumen(resultado);
      hallazgosPanel.hidden = Boolean(resultado.bloqueado);
      setEstadoWallets(
        resultado.bloqueado ? "C0 bloqueado. Corrige el archivo antes de continuar." : textoSincronizacion(resultado.sincronizacion),
        resultado.bloqueado ? "error" : "success"
      );
      if (!resultado.bloqueado) await cargarHallazgos();
    } catch (error) {
      setEstadoWallets(error.message, "error");
    } finally {
      conciliar.textContent = textoOriginal;
      actualizarDisponibilidadConciliacion();
    }
  }

  function renderMensajes(mensajes) {
    if (!mensajes || !mensajes.length) return '<p class="empty">Todavía no hay mensajes en este hallazgo.</p>';
    return '<div class="wallet-thread">' + mensajes.map((m) =>
      "<article><strong>" + escapar(String(m.tipo || "").replaceAll("_", " ").toUpperCase()) + "</strong>" +
      "<p>" + escapar(m.texto) + "</p><small>" + escapar(new Date(m.creado_at).toLocaleString("es-CO")) + "</small></article>"
    ).join("") + "</div>";
  }

  function textoSincronizacion(s) {
    if (!s) return "Conciliación terminada.";
    return "Conciliación terminada: " + s.creados + " hallazgos nuevos, " + s.actualizados +
      " actualizados (se conserva lo que ya revisaste), " + s.resueltos_por_sistema +
      " resueltos por el sistema y " + s.reabiertos + " reabiertos.";
  }

  // Listas de categorización (docs/nucleo/DIMENSIONES.md): solo valores activos.
  const DIMENSIONES_FORM = [
    ["ingreso_egreso", "Ingreso/egreso"],
    ["unidad_negocio", "Unidad de negocio"],
    ["categoria", "Categoría"],
    ["fijo_variable", "Fijo/variable"]
  ];
  let listasCache = null;

  function normalizar(valor) {
    return String(valor || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase().split(/\s+/).filter(Boolean).join(" ");
  }

  async function listasCategorizacion() {
    if (!listasCache) {
      const valores = await walletApi("/api/v1/dimensiones");
      listasCache = {};
      valores.forEach((v) => { (listasCache[v.dimension] = listasCache[v.dimension] || []).push(v.valor); });
    }
    return listasCache;
  }

  function empresaActualNombre() {
    const select = $("#empresa-id");
    return select && select.selectedOptions[0] ? select.selectedOptions[0].textContent.trim() : "";
  }

  function selectDimension(nombre, etiqueta, opciones, preferido) {
    const elegido = opciones.find((o) => normalizar(o) === normalizar(preferido)) || "";
    return "<label>" + escapar(etiqueta) + '<select data-dimension="' + nombre + '"><option value="">Elige…</option>' +
      opciones.map((o) => '<option value="' + escapar(o) + '"' + (o === elegido ? " selected" : "") + ">" + escapar(o) + "</option>").join("") +
      "</select></label>";
  }

  async function formularioCategorizacion(h) {
    const e = h.evidencia || {};
    const base = e.categorizacion || {
      ingreso_egreso: e.ingreso_egreso,
      unidad_negocio: e.unidad_negocio,
      categoria: e.categoria,
      fijo_variable: "VARIABLE",
      tercero: e.tercero
    };
    const listas = await listasCategorizacion();
    return '<div class="wallet-categorizacion form-grid">' +
      (e.texto_nuevo ? '<p class="notice compact">Texto nuevo de Dropi: el motor no tiene propuesta. Elige cada dimensión.</p>' : "") +
      DIMENSIONES_FORM.map(([nombre, etiqueta]) => selectDimension(nombre, etiqueta, listas[nombre] || [], base[nombre])).join("") +
      '<label>Empresa<input data-dimension="empresa" value="' + escapar(empresaActualNombre()) + '" disabled></label>' +
      '<label>Modalidad<input data-dimension="modalidad" value="WALLET" disabled></label>' +
      '<label>Tercero<input data-dimension="tercero" maxlength="200" value="' + escapar(base.tercero || "") + '"></label>' +
      "</div>";
  }

  function leerCategorizacion() {
    const datos = {};
    acciones.querySelectorAll("[data-dimension]").forEach((campo) => { datos[campo.dataset.dimension] = campo.value; });
    const falta = DIMENSIONES_FORM.find(([nombre]) => !datos[nombre]);
    if (falta) throw new Error("Elige un valor de " + falta[1] + ". Si ninguno sirve, escala al coordinador.");
    return datos;
  }

  async function renderAccionesHallazgo(h) {
    const gestionar = puede("hallazgos.gestionar") && estadoDe(h) !== "escalado" && estadoDe(h) !== "resuelto";
    const escalar = puede("hallazgos.escalar") && estadoDe(h) !== "escalado" && estadoDe(h) !== "resuelto";
    const responder = puede("hallazgos.responder_escalado") && estadoDe(h) === "escalado";
    // Un hallazgo resuelto o cerrado no admite acciones para nadie: no es por el rol.
    if (estadoDe(h) === "resuelto" || estadoDe(h) === "cerrado") {
      const texto = estadoDe(h) === "cerrado"
        ? "Este hallazgo está cerrado. Solo se puede consultar."
        : "Este hallazgo ya está resuelto. Solo se puede consultar.";
      acciones.innerHTML = '<p class="notice compact">' + texto + "</p>";
      return;
    }
    if (!gestionar && !escalar && !responder) {
      acciones.innerHTML = '<p class="notice compact">Tu rol tiene acceso de lectura para este hallazgo.</p>';
      return;
    }
    const categorizar = gestionar && esRevisarMovimiento(h) && puede("movimientos.categorizar");
    let formulario = "";
    if (categorizar) {
      try {
        formulario = await formularioCategorizacion(h);
      } catch (fallo) {
        formulario = '<p class="status error">' + escapar(fallo.message) + "</p>";
      }
    }

    acciones.innerHTML =
      '<div class="wallet-action-box">' + formulario +
      '<label>Observación / mensaje<textarea id="wallets-accion-texto" rows="4" placeholder="Escribe el contexto necesario para la acción."></textarea></label>' +
      '<p id="wallets-accion-error" class="status error" hidden></p>' +
      '<div class="wallet-action-buttons">' +
      (categorizar
        ? '<button type="button" data-wallet-action="observar">Guardar</button><button type="button" data-wallet-action="resolver" class="secondary-button">Guardar y resolver</button>'
        : (gestionar ? '<button type="button" data-wallet-action="observar">Guardar observación</button><button type="button" data-wallet-action="resolver" class="secondary-button">Observar y marcar resuelto</button>' : "")) +
      (escalar ? '<button type="button" data-wallet-action="escalar" class="secondary-button">Escalar</button>' : "") +
      (responder ? '<button type="button" data-wallet-action="responder">Responder</button><button type="button" data-wallet-action="responder-resolver" class="secondary-button">Responder y resolver</button>' : "") +
      "</div></div>";

    acciones.querySelectorAll("[data-wallet-action]").forEach((button) => {
      button.addEventListener("click", () => ejecutarAccionHallazgo(h.id, button.dataset.walletAction, categorizar));
    });
  }

  async function abrirHallazgo(id) {
    detalle.innerHTML = '<p class="empty">Cargando detalle…</p>';
    acciones.innerHTML = "";
    if (!dialog.open && typeof dialog.showModal === "function") dialog.showModal();
    else if (!dialog.open) dialog.setAttribute("open", "");
    try {
      const h = await walletApi("/api/v1/hallazgos/" + id);
      detalle.innerHTML =
        '<div class="wallet-dialog-heading"><div><span class="wallet-pill">' + escapar(textoGravedad(gravedadDe(h))) + "</span>" +
        '<h3>' + escapar(h.codigo_regla) + '</h3></div><span class="wallet-pill">' + escapar(textoEstado(estadoDe(h))) + '</span></div>' +
        "<p>" + descripcionHtml(h) + "</p>" +
        (h.resuelto_por_sistema ? '<p class="notice compact">Resuelto por el sistema: ya no aparece en la carga más reciente.</p>' : "") +
        "<h4>Hilo de mensajes</h4>" + renderMensajes(h.mensajes);
      await renderAccionesHallazgo(h);
    } catch (error) {
      detalle.innerHTML = '<p class="status error">' + escapar(error.message) + "</p>";
    }
  }

  async function ejecutarAccionHallazgo(id, accion, categorizar) {
    const campo = $("#wallets-accion-texto");
    const error = $("#wallets-accion-error");
    const texto = (campo && campo.value || "").trim();
    error.hidden = true;
    if (!texto) {
      error.textContent = "Escribe la observación: es obligatoria.";
      error.hidden = false;
      campo.focus();
      return;
    }

    let url = "";
    let body = {};
    if (accion === "observar" || accion === "resolver") {
      url = "/api/v1/hallazgos/" + id + "/observar";
      body = {observacion: texto, resolver: accion === "resolver"};
      if (categorizar) {
        try {
          body.categorizacion = leerCategorizacion();
        } catch (falta) {
          error.textContent = falta.message;
          error.hidden = false;
          return;
        }
      }
    } else if (accion === "escalar") {
      url = "/api/v1/hallazgos/" + id + "/escalar";
      body = {pregunta: texto};
    } else {
      url = "/api/v1/hallazgos/" + id + "/responder";
      body = {respuesta: texto, resolver: accion === "responder-resolver"};
    }

    try {
      await walletApi(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body)
      });
      await cargarHallazgos();
      await abrirHallazgo(id);
    } catch (fallo) {
      error.textContent = fallo.message;
      error.hidden = false;
    }
  }

  async function cargarWalletsTodo() {
    if (cargandoContexto || !empresaIdWallets()) return;
    cargandoContexto = true;
    setEstadoWallets("Cargando catálogos…", "");
    try {
      const empresa = empresaIdWallets();
      const consultas = [
        {nombre: "Períodos", url: "/api/v1/periodos?empresa_id=" + empresa},
        {nombre: "Fuentes", url: "/api/v1/fuentes?empresa_id=" + empresa},
        {nombre: "Catálogo Wallets", url: "/api/v1/wallets/catalogo?empresa_id=" + empresa}
      ];
      const resultados = await Promise.allSettled(
        consultas.map((consulta) => walletApi(consulta.url))
      );

      periodos = resultados[0].status === "fulfilled" ? resultados[0].value : [];
      fuentes = resultados[1].status === "fulfilled" ? resultados[1].value : [];
      catalogo = resultados[2].status === "fulfilled"
        ? resultados[2].value
        : {wiilog: false, tiendas: [], pagos: []};

      renderPeriodos();
      renderFuentes();
      renderTipos();
      actualizarTipo();
      restaurarResultado();
      if (!hallazgosPanel.hidden) await cargarHallazgos();

      const errores = resultados
        .map((resultado, indice) => resultado.status === "rejected"
          ? consultas[indice].nombre + ": " + resultado.reason.message
          : null)
        .filter(Boolean);

      setEstadoWallets(
        errores.length ? errores.join(" · ") : "Listo",
        errores.length ? "error" : ""
      );
      if (errores.length) {
        hallazgosBody.innerHTML =
          '<tr><td colspan="6" class="empty">' + escapar(errores.join(" · ")) + "</td></tr>";
      }
    } catch (error) {
      setEstadoWallets(error.message, "error");
      hallazgosBody.innerHTML =
        '<tr><td colspan="6" class="empty">' + escapar(error.message) + "</td></tr>";
    } finally {
      cargandoContexto = false;
    }
  }

  tipo.addEventListener("change", async () => {
    actualizarTipo();
    restaurarResultado();
    if (!hallazgosPanel.hidden) await cargarHallazgos();
  });
  identidad.addEventListener("change", async () => {
    restaurarResultado();
    if (!hallazgosPanel.hidden) await cargarHallazgos();
  });
  periodo.addEventListener("change", async () => {
    actualizarDisponibilidadConciliacion();
    restaurarResultado();
    if (!hallazgosPanel.hidden) await cargarHallazgos();
  });
  archivoOrdenes.addEventListener("change", () => {
    if (tipo.value !== "tienda" || corte.value || !archivoOrdenes.files[0]) return;
    const inferida = fechaDesdeNombre(archivoOrdenes.files[0].name);
    if (inferida) corte.value = inferida;
  });
  filtroGravedad.addEventListener("change", renderHallazgos);
  filtroEstado.addEventListener("change", renderHallazgos);
  todasCargas.addEventListener("change", cargarHallazgos);
  recargarHallazgos.addEventListener("click", cargarHallazgos);
  form.addEventListener("submit", enviarConciliacion);

  window.cargarWalletsTodo = cargarWalletsTodo;
})();