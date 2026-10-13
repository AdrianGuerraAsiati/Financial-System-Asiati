/* Vista operativa de Tesorería V1: facturas de compra y soportes manuales. */
(function () {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const nueva = $("#tesoreria-nueva");
  const edicion = $("#tesoreria-editar");
  const pago = $("#tesoreria-pagar");
  const filas = $("#tesoreria-filas");
  const estado = $("#tesoreria-estado");
  const panelDetalle = $("#tesoreria-detalle-panel");
  let catalogos = {};
  let facturaActiva = null;

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
  }
  async function cargarTodo() {
    panelDetalle.hidden = true;
    facturaActiva = null;
    nueva.hidden = !window.tesoreriaPuedeEditar;
    edicion.hidden = !window.tesoreriaPuedeEditar;
    pago.hidden = !window.tesoreriaPuedePagar;
    try {
      await cargarCatalogos();
      const facturas = await api("/api/v1/tesoreria/facturas?empresa_id=" + empresaId());
      filas.innerHTML = facturas.length ? facturas.map((f) => `
        <tr>
          <td>${celda(f.numero)}</td><td>${celda(f.proveedor)}</td>
          <td>${celda(f.fecha_pago_oportuno)}</td>
          <td>${celda(moneda(f))}</td><td>${celda(formatearDecimal(f.saldo))}</td>
          <td>${celda(f.estado)}${f.alerta ? " · " + celda(f.alerta) : ""}</td>
          <td><button type="button" data-factura="${Number(f.id)}" class="secondary-button">Abrir</button></td>
        </tr>`).join("") : '<tr><td colspan="7" class="empty">No hay facturas registradas.</td></tr>';
      notificar(facturas.length + " facturas consultadas");
    } catch (error) {
      filas.innerHTML = '<tr><td colspan="7" class="empty">No fue posible consultar las facturas.</td></tr>';
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
    try {
      const f = await api("/api/v1/tesoreria/facturas/" + id);
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
      pago.hidden = !window.tesoreriaPuedePagar || f.estado === "PAGADA";
      notificar("Factura " + f.numero + " cargada");
    } catch (error) {
      notificar(error.message, true);
    }
  }

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
    const datos = new FormData(nueva);
    datos.append("empresa_id", String(empresaId()));
    try {
      const f = await api("/api/v1/tesoreria/facturas", {method: "POST", body: datos});
      nueva.reset();
      await cargarTodo();
      await abrir(f.id);
      notificar("Factura " + f.numero + " guardada, pendiente de pago.");
    } catch (error) { notificar(error.message, true); }
  });

  filas.addEventListener("click", (event) => {
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
    if (!facturaActiva) return;
    if (!confirm("¿Confirmas que el desembolso se realizó y el soporte corresponde a este pago?")) return;
    const id = facturaActiva.id;
    try {
      await api("/api/v1/tesoreria/facturas/" + id + "/pagos", {
        method: "POST", body: new FormData(pago)
      });
      pago.reset();
      await cargarTodo();
      await abrir(id);
      notificar("Pago registrado con su comprobante.");
    } catch (error) { notificar(error.message, true); }
  });
  $("#tesoreria-actualizar").addEventListener("click", cargarTodo);
  window.cargarTesoreriaTodo = cargarTodo;
})();
