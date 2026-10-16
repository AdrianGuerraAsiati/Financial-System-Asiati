/* Facturación CxP: captura y cierre de facturas, soportes y avisos internos por empresa. */
(function () {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const nueva = $("#tesoreria-nueva");
  const dialogoNueva = $("#tesoreria-dialogo-nueva");
  const dialogoPago = $("#tesoreria-dialogo-pago");
  const abrirNueva = $("#tesoreria-abrir-nueva");
  const abrirPago = $("#tesoreria-abrir-pago");
  const edicion = $("#tesoreria-editar");
  const pago = $("#tesoreria-pagar");
  const filas = $("#tesoreria-filas");
  const estado = $("#tesoreria-estado");
  const panelDetalle = $("#tesoreria-detalle-panel");
  let catalogos = {};
  let facturaActiva = null;
  let paginaDesde = 0;
  let paginaTotal = 0;
  const paginaLimite = 25;
  const filtros = $("#tesoreria-filtros");
  let fechaCorte = null;
  function cerrarDialogos() {
    for (const dialogo of [dialogoNueva, dialogoPago]) {
      if (dialogo.open) dialogo.close();
    }
  }
  document.querySelectorAll("[data-cerrar-facturacion]").forEach((boton) => {
    boton.addEventListener("click", () => {
      const dialogo = document.getElementById(boton.dataset.cerrarFacturacion);
      if (dialogo?.open) dialogo.close();
    });
  });
  // Un modal de factura no debe sobrevivir a un cambio de empresa o módulo.
  $("#empresa-id").addEventListener("change", cerrarDialogos);
  document.querySelectorAll(".nav-item[data-view]").forEach((item) => {
    if (item.dataset.view !== "tesoreria") item.addEventListener("click", cerrarDialogos);
  });

  function parametrosBandeja() {
    const params = new URLSearchParams({
      empresa_id: String(empresaId()),
      moneda: filtros.elements.namedItem("moneda").value,
    });
    ["buscar", "estado", "categoria", "vencimiento_desde", "vencimiento_hasta"].forEach((campo) => {
      const valor = filtros.elements.namedItem(campo).value.trim();
      if (valor) params.set(campo, valor);
    });
    return params;
  }
  function parametrosIndicadores() {
    const params = new URLSearchParams({
      empresa_id: String(empresaId()),
      moneda: filtros.elements.namedItem("moneda").value,
    });
    ["pago_desde", "pago_hasta"].forEach((campo) => {
      const valor = filtros.elements.namedItem(campo).value;
      if (valor) params.set(campo, valor);
    });
    return params;
  }
  function pintarIndicadores(info) {
    fechaCorte = String(info.fecha_corte);
    const cantidad = (valor) => Number(valor).toLocaleString("es-CO");
    [
      ["#tesoreria-kpi-pendiente", info.total_pendiente],
      ["#tesoreria-kpi-vencido", info.total_vencido],
      ["#tesoreria-kpi-proximo", info.total_por_vencer_7d],
      ["#tesoreria-kpi-pagado", info.total_pagado_periodo],
    ].forEach(([selector, monto]) => {
      $(selector).textContent = formatearDecimal(monto) + " " + info.moneda;
    });
    $("#tesoreria-kpi-vencidas-cantidad").textContent = cantidad(info.cantidad_vencidas) + " facturas vencidas";
    $("#tesoreria-kpi-proximas-cantidad").textContent = cantidad(info.cantidad_por_vencer_7d) + " facturas en los próximos 7 días";
    $("#tesoreria-kpi-sinfecha").textContent = cantidad(info.sin_vencimiento);
    $("#tesoreria-kpi-periodo").textContent = String(info.pago_desde) + " a " + String(info.pago_hasta);
  }
  async function descargarExcel() {
    const boton = $("#tesoreria-exportar");
    boton.disabled = true;
    try {
      const respuesta = await fetch("/api/v1/tesoreria/exportacion-facturas?" + parametrosBandeja(), {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!respuesta.ok) {
        const error = await respuesta.json().catch(() => ({}));
        throw new Error(typeof error.detail === "string" ? error.detail : "No fue posible exportar el archivo.");
      }
      const blob = await respuesta.blob();
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = "Facturas_Tesoreria_" + empresaId() + ".xlsx";
      document.body.append(enlace);
      enlace.click();
      enlace.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1500);
      notificar("Exportación Excel preparada con los filtros actuales.");
    } catch (error) {
      notificar(error.message, true);
    } finally {
      boton.disabled = false;
    }
  }

  function notificar(texto, error = false) {
    estado.textContent = texto;
    estado.className = error ? "status error" : "status ok";
  }
  function moneda(f) {
    return formatearDecimal(f.monto) + " " + f.moneda;
  }
  function celda(valor) {
    return escapar(valor == null || valor === "" ? "—" : String(valor));
  }
  function avisoTabla(factura) {
    if (Number(factura.saldo) <= 0) return "—";
    if (!factura.fecha_pago_oportuno) return "Sin vencimiento";
    if (fechaCorte && factura.fecha_pago_oportuno < fechaCorte) return "Vencida";
    if (fechaCorte && factura.fecha_pago_oportuno >= fechaCorte) {
      // Comparar fechas ISO completas en UTC, sin depender de la zona horaria del navegador.
      const diferencia = (Date.parse(factura.fecha_pago_oportuno + "T00:00:00Z") -
        Date.parse(fechaCorte + "T00:00:00Z")) / 86400000;
      if (diferencia === 0) return "Vence hoy";
      if (diferencia > 0 && diferencia <= 7) return "Por vencer";
    }
    return factura.alerta ? factura.alerta.replaceAll("_", " ") : "—";
  }

  async function cargarAvisos() {
    const empresa = empresaId();
    const respuesta = await api("/api/v1/tesoreria/notificaciones?empresa_id=" + empresa);
    if (empresa !== empresaId()) return;
    const contador = $("#tesoreria-nav-alertas");
    contador.textContent = String(respuesta.total);
    contador.hidden = respuesta.total === 0;
    $("#tesoreria-avisos-total").textContent = String(respuesta.total);
    const resumen = $("#tesoreria-avisos-resumen");
    const lista = $("#tesoreria-avisos-lista");
    resumen.textContent = respuesta.total
      ? respuesta.vencidas + " vencidas · " + respuesta.por_vencer +
        " por vencer (incluido hoy). Fecha de corte: " + respuesta.fecha_corte + "."
      : "No hay facturas vencidas ni próximas a vencer para esta empresa.";
    lista.innerHTML = respuesta.items.map((f) => {
      const plazo = f.dias_para_vencer < 0 ? "Venció hace " + Math.abs(f.dias_para_vencer) + " días" :
        f.dias_para_vencer === 0 ? "Vence hoy" : "Vence en " + f.dias_para_vencer + " días";
      return '<article class="facturacion-aviso" data-tipo="' + celda(f.tipo) + '">' +
        '<div><strong>' + celda(f.numero) + " · " + celda(f.proveedor) + '</strong>' +
        '<p>' + celda(plazo) + " · Saldo " + celda(formatearDecimal(f.saldo)) +
        " " + celda(f.moneda) + '</p></div>' +
        '<button type="button" class="secondary-button" data-aviso-factura="' +
        Number(f.id) + '">Ver factura</button></article>';
    }).join("");
    if (respuesta.hay_mas) {
      lista.insertAdjacentHTML("beforeend",
        '<p class="muted">Hay más avisos. Usa la bandeja y sus filtros para consultar todas las facturas.</p>');
    }
  }

  function opciones(select, valores) {
    const seleccionado = select.value;
    select.replaceChildren(new Option("Sin asignar", ""));
    valores.forEach((valor) => select.add(new Option(valor, valor)));
    if ([...select.options].some((o) => o.value === seleccionado)) select.value = seleccionado;
  }
  async function cargarCatalogos() {
    catalogos = await api("/api/v1/tesoreria/catalogos?empresa_id=" + empresaId());
    document.querySelectorAll('#vista-tesoreria [data-catalogo]').forEach((select) => {
      opciones(select, catalogos[select.dataset.catalogo] || []);
    });
    const categoria = $("#tesoreria-filtro-categoria");
    const seleccion = categoria.value;
    categoria.replaceChildren(new Option("Todas", ""));
    (catalogos.categoria || []).forEach((valor) => categoria.add(new Option(valor, valor)));
    if ([...categoria.options].some((o) => o.value === seleccion)) categoria.value = seleccion;
  }
  async function cargarBandeja() {
    const parametros = parametrosBandeja();
    parametros.set("desde", String(paginaDesde));
    parametros.set("limite", String(paginaLimite));
    const [pagina, indicadores] = await Promise.all([
      api("/api/v1/tesoreria/consulta-facturas?" + parametros),
      api("/api/v1/tesoreria/indicadores?" + parametrosIndicadores()),
    ]);
    pintarIndicadores(indicadores);
    paginaTotal = pagina.total;
    filas.innerHTML = pagina.items.length ? pagina.items.map((f) => `
      <tr>
        <td>${celda(f.numero)}</td><td>${celda(f.proveedor)}</td>
        <td>${celda(f.fecha_pago_oportuno)}</td>
        <td>${celda(moneda(f))}</td><td>${celda(formatearDecimal(f.pagado))}</td>
        <td>${celda(formatearDecimal(f.saldo))}</td>
        <td><span class="facturacion-estado" data-estado="${celda(f.estado)}">${celda(f.estado)}</span></td>
        <td><span class="facturacion-alerta">${celda(avisoTabla(f))}</span></td>
        <td class="facturacion-acciones-fila"><button type="button" data-factura="${Number(f.id)}" class="secondary-button">Ver</button>
          ${window.tesoreriaPuedePagar && Number(f.saldo) > 0 ? '<button type="button" data-pago-factura="' + Number(f.id) + '">Registrar pago</button>' : ''}</td>
      </tr>`).join("") : '<tr><td colspan="9" class="empty">No hay facturas con esos filtros.</td></tr>';
    const inicio = pagina.total ? paginaDesde + 1 : 0;
    const fin = paginaDesde + pagina.items.length;
    $("#tesoreria-pagina-info").textContent = inicio + "–" + fin + " de " + pagina.total + " facturas";
    $("#tesoreria-anterior").disabled = paginaDesde === 0;
    $("#tesoreria-siguiente").disabled = fin >= pagina.total;
    notificar(pagina.total + " facturas encontradas");
  }
  async function cargarTodo() {
    cerrarDialogos();
    panelDetalle.hidden = true;
    facturaActiva = null;
    paginaDesde = 0;
    abrirNueva.hidden = !window.tesoreriaPuedeEditar;
    $("#tesoreria-solo-consulta").hidden = window.tesoreriaPuedeEditar || window.tesoreriaPuedePagar;
    edicion.hidden = !window.tesoreriaPuedeEditar;
    abrirPago.hidden = !window.tesoreriaPuedePagar;
    try {
      await cargarCatalogos();
      await cargarBandeja();
      try {
        await cargarAvisos();
      } catch (error) {
        $("#tesoreria-avisos-resumen").textContent = "No se pudieron cargar los avisos: " + error.message;
        $("#tesoreria-avisos-lista").replaceChildren();
        $("#tesoreria-nav-alertas").hidden = true;
      }
    } catch (error) {
      filas.innerHTML = '<tr><td colspan="9" class="empty">No fue posible consultar las facturas.</td></tr>';
      notificar(error.message, true);
    }
  }

  function rellenar(formulario, f) {
    ["fecha_vencimiento", "descripcion", "ciudad", "unidad_negocio", "categoria",
      "fijo_variable", "cuenta_pago", "documento_contable"].forEach((campo) => {
      formulario.elements.namedItem(campo).value =
        (campo === "fecha_vencimiento" ? f.fecha_pago_oportuno : f[campo]) || "";
    });
  }
  async function abrir(id) {
    const empresa = empresaId();
    facturaActiva = null;
    try {
      const f = await api("/api/v1/tesoreria/facturas/" + id);
      if (empresa !== empresaId() || Number(f.empresa_id) !== empresa) return false;
      facturaActiva = f;
      panelDetalle.hidden = false;
      $("#tesoreria-detalle-titulo").textContent = f.numero + " · " + f.proveedor;
      $("#tesoreria-detalle-resumen").textContent =
        "Monto " + moneda(f) + " · Pagado " + formatearDecimal(f.pagado) +
        " · Saldo " + formatearDecimal(f.saldo) + " · " + f.estado;
      $("#tesoreria-documentos").innerHTML =
        '<p><a href="/api/v1/tesoreria/facturas/' + Number(f.id) +
        '/documento">Consultar factura original (' + celda(f.archivo_nombre) + ')</a></p>';
      rellenar(edicion, f);
      $("#tesoreria-pagos").innerHTML = f.pagos.length
        ? '<div class="table-wrap"><table><thead><tr><th>Fecha real</th><th>Monto</th><th>Referencia</th><th>Soporte</th></tr></thead><tbody>' +
          f.pagos.map((p) => '<tr><td>' + celda(p.fecha) + '</td><td>' + celda(formatearDecimal(p.monto)) +
            '</td><td>' + celda(p.referencia) + '</td><td><a href="/api/v1/tesoreria/facturas/' +
            Number(f.id) + '/pagos/' + Number(p.id) + '/soporte">' + celda(p.soporte_nombre) +
            '</a></td></tr>').join("") + '</tbody></table></div>'
        : '<p class="empty">La factura aún no tiene pagos. Fecha real y comprobante pendientes.</p>';
      pago.querySelector('input[name="monto"]').value = f.saldo === "0.00" ? "" : f.saldo;
      abrirPago.hidden = !window.tesoreriaPuedePagar || f.estado === "PAGADA";
      notificar("Factura " + f.numero + " cargada");
      return true;
    } catch (error) {
      notificar(error.message, true);
      return false;
    }
  }

  function mostrarPago() {
    if (!window.tesoreriaPuedePagar || !facturaActiva ||
        Number(facturaActiva.saldo) <= 0 || facturaActiva.empresa_id !== empresaId()) return;
    pago.reset();
    pago.elements.namedItem("monto").value = facturaActiva.saldo;
    $("#tesoreria-pago-resumen").textContent = "Factura " + facturaActiva.numero +
      " · " + facturaActiva.proveedor + " · Saldo " +
      formatearDecimal(facturaActiva.saldo) + " " + facturaActiva.moneda;
    dialogoPago.showModal();
  }

  abrirNueva.addEventListener("click", () => {
    if (!window.tesoreriaPuedeEditar) return;
    nueva.reset();
    $("#tesoreria-extraccion-aviso").textContent = "PDF e imágenes requieren captura manual en V1.";
    dialogoNueva.showModal();
  });
  abrirPago.addEventListener("click", mostrarPago);
  $("#tesoreria-avisos-lista").addEventListener("click", async (event) => {
    const boton = event.target.closest("button[data-aviso-factura]");
    if (boton && await abrir(Number(boton.dataset.avisoFactura))) {
      panelDetalle.scrollIntoView({behavior: "smooth", block: "start"});
    }
  });
  $("#tesoreria-actualizar-avisos").addEventListener("click", () => {
    cargarAvisos().catch((error) => {
      $("#tesoreria-avisos-resumen").textContent = "No se pudieron actualizar los avisos: " + error.message;
    });
  });

  $("#tesoreria-extraer").addEventListener("click", async () => {
    const archivo = nueva.elements.namedItem("archivo").files[0];
    if (!archivo) { notificar("Primero selecciona una factura.", true); return; }
    const datos = new FormData();
    datos.append("archivo", archivo);
    try {
      const respuesta = await api("/api/v1/tesoreria/extraer", {method: "POST", body: datos});
      for (const [campo, valor] of Object.entries(respuesta.campos || {})) {
        const input = nueva.elements.namedItem(campo);
        if (input && typeof valor === "string") input.value = valor;
      }
      $("#tesoreria-extraccion-aviso").textContent = (respuesta.advertencias || []).join(" ");
      notificar("Verifica los datos prellenados contra la factura.");
    } catch (error) {
      notificar(error.message, true);
    }
  });

  nueva.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!window.tesoreriaPuedeEditar) return;
    const boton = nueva.querySelector('button[type="submit"]');
    const empresa = empresaId();
    const datos = new FormData(nueva);
    datos.append("empresa_id", String(empresa));
    boton.disabled = true;
    try {
      const f = await api("/api/v1/tesoreria/facturas", {method: "POST", body: datos});
      nueva.reset();
      dialogoNueva.close();
      if (empresa !== empresaId()) return;
      await cargarTodo();
      await abrir(f.id);
      notificar("Factura " + f.numero + " guardada, pendiente de pago.");
    } catch (error) { notificar(error.message, true); }
    finally { boton.disabled = false; }
  });

  filas.addEventListener("click", async (event) => {
    const botonPago = event.target.closest("button[data-pago-factura]");
    if (botonPago) {
      if (await abrir(Number(botonPago.dataset.pagoFactura))) mostrarPago();
      return;
    }
    const boton = event.target.closest("button[data-factura]");
    if (boton) abrir(Number(boton.dataset.factura));
  });

  edicion.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!facturaActiva) return;
    const datos = {};
    new FormData(edicion).forEach((valor, clave) => { datos[clave] = valor || null; });
    try {
      const id = facturaActiva.id;
      await api("/api/v1/tesoreria/facturas/" + id, {
        method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify(datos)
      });
      await cargarTodo();
      await abrir(id);
      notificar("Campos actualizados con auditoría.");
    } catch (error) { notificar(error.message, true); }
  });

  pago.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!window.tesoreriaPuedePagar || !facturaActiva) return;
    if (!confirm("¿Confirmas que el desembolso se realizó y el soporte corresponde a este pago?")) return;
    const id = facturaActiva.id;
    const empresa = empresaId();
    const boton = pago.querySelector('button[type="submit"]');
    boton.disabled = true;
    try {
      await api("/api/v1/tesoreria/facturas/" + id + "/pagos", {
        method: "POST", body: new FormData(pago)
      });
      pago.reset();
      dialogoPago.close();
      if (empresa !== empresaId()) return;
      await cargarTodo();
      await abrir(id);
      notificar("Pago registrado con su comprobante.");
    } catch (error) { notificar(error.message, true); }
    finally { boton.disabled = false; }
  });
  filtros.addEventListener("submit", async (event) => {
    event.preventDefault();
    paginaDesde = 0;
    try { await cargarBandeja(); } catch (error) { notificar(error.message, true); }
  });
  $("#tesoreria-limpiar").addEventListener("click", () => {
    filtros.reset();
    paginaDesde = 0;
    cargarBandeja().catch((error) => notificar(error.message, true));
  });
  $("#tesoreria-anterior").addEventListener("click", () => {
    paginaDesde = Math.max(0, paginaDesde - paginaLimite);
    cargarBandeja().catch((error) => notificar(error.message, true));
  });
  $("#tesoreria-siguiente").addEventListener("click", () => {
    if (paginaDesde + paginaLimite >= paginaTotal) return;
    paginaDesde += paginaLimite;
    cargarBandeja().catch((error) => notificar(error.message, true));
  });
  $("#tesoreria-exportar").addEventListener("click", descargarExcel);
  $("#tesoreria-actualizar").addEventListener("click", cargarTodo);
  window.actualizarAvisosFacturacion = () => {
    if ($("#nav-tesoreria").hidden) return Promise.resolve();
    return cargarAvisos();
  };
  window.cargarTesoreriaTodo = cargarTodo;
})();
