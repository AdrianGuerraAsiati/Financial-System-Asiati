const empresaInput = document.querySelector("#empresa-id");
const estado = document.querySelector("#estado-global");
const operacionesBody = document.querySelector("#operaciones-body");
const moraBody = document.querySelector("#mora-body");
const detalleTitulo = document.querySelector("#detalle-titulo");
const detalleContenido = document.querySelector("#detalle-contenido");
const pendientesLista = document.querySelector("#pendientes-lista");
const formComprobante = document.querySelector("#form-comprobante");

const savedEmpresa = localStorage.getItem("asiati_empresa_id");
if (savedEmpresa) empresaInput.value = savedEmpresa;
empresaInput.addEventListener("change", () => {
  localStorage.setItem("asiati_empresa_id", empresaInput.value);
});

function empresaId() {
  return Number(empresaInput.value);
}

function setEstado(mensaje, tipo = "") {
  estado.textContent = mensaje;
  estado.className = `status ${tipo}`.trim();
}

function escapar(valor) {
  const div = document.createElement("div");
  div.textContent = valor ?? "";
  return div.innerHTML;
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  let body = null;
  try { body = await response.json(); } catch (_) {}
  if (!response.ok) {
    const detail = body?.detail || `Error HTTP ${response.status}`;
    throw new Error(detail);
  }
  return body;
}

async function cargarOperaciones() {
  setEstado("Consultando operaciones…");
  operacionesBody.innerHTML = '<tr><td colspan="7" class="empty">Consultando…</td></tr>';
  try {
    const rows = await api(`/cartera/operaciones?empresa_id=${empresaId()}`);
    if (!rows.length) {
      operacionesBody.innerHTML = '<tr><td colspan="7" class="empty">No hay operaciones.</td></tr>';
    } else {
      operacionesBody.innerHTML = rows.map((row) => `
        <tr>
          <td>${escapar(row.oc)}</td>
          <td>${escapar(row.cliente)}</td>
          <td>${escapar(row.sku)}</td>
          <td>${escapar(row.estado)}</td>
          <td>${escapar(row.etapa)}</td>
          <td>${Number(row.valor || 0).toLocaleString("es-CO")}</td>
          <td><button type="button" data-oc="${escapar(row.oc)}">Ver</button></td>
        </tr>
      `).join("");
      operacionesBody.querySelectorAll("[data-oc]").forEach((button) => {
        button.addEventListener("click", () => cargarDetalle(button.dataset.oc));
      });
    }
    setEstado("Operaciones actualizadas", "ok");
  } catch (error) {
    operacionesBody.innerHTML = `<tr><td colspan="7" class="empty">${escapar(error.message)}</td></tr>`;
    setEstado(error.message, "error");
  }
}

async function cargarMora() {
  setEstado("Consultando mora…");
  moraBody.innerHTML = '<tr><td colspan="5" class="empty">Consultando…</td></tr>';
  try {
    const rows = await api(`/cartera/mora?empresa_id=${empresaId()}`);
    moraBody.innerHTML = rows.length
      ? rows.map((row) => `
          <tr>
            <td>${escapar(row.cliente)}</td>
            <td>${escapar(row.empresa)}</td>
            <td>${Number(row.monto || 0).toLocaleString("es-CO")}</td>
            <td>${escapar(row.estado)}</td>
            <td>${escapar(row.observacion)}</td>
          </tr>
        `).join("")
      : '<tr><td colspan="5" class="empty">No hay registros de mora.</td></tr>';
    setEstado("Mora actualizada", "ok");
  } catch (error) {
    moraBody.innerHTML = `<tr><td colspan="5" class="empty">${escapar(error.message)}</td></tr>`;
    setEstado(error.message, "error");
  }
}

async function cargarDetalle(oc) {
  detalleTitulo.textContent = oc;
  detalleContenido.textContent = "Consultando…";
  try {
    const detalle = await api(
      `/cartera/operaciones/${encodeURIComponent(oc)}?empresa_id=${empresaId()}`
    );
    detalleContenido.className = "detail-grid";
    detalleContenido.innerHTML = detalle.lineas.map((linea) => `
      <article class="detail-card">
        <strong>${escapar(linea.sku || "Sin SKU")}</strong>
        <div>${escapar(linea.producto)}</div>
        <div>Cliente: ${escapar(linea.cliente)}</div>
        <div>Valor: ${Number(linea.valor || 0).toLocaleString("es-CO")}</div>
        <div>Estado: ${escapar(linea.estado)}</div>
      </article>
    `).join("");

    const primera = detalle.lineas[0];
    if (primera) {
      formComprobante.elements.oc.value = primera.oc || "";
      formComprobante.elements.cliente.value = primera.cliente || "";
      formComprobante.elements.valor_ddp.value = primera.valor || "";
      formComprobante.elements.tipo_negociacion.value = primera.negociacion || "";
    }
    setEstado(`Detalle ${oc} cargado`, "ok");
  } catch (error) {
    detalleContenido.className = "empty-block";
    detalleContenido.textContent = error.message;
    setEstado(error.message, "error");
  }
}

async function cargarPendientes() {
  pendientesLista.innerHTML = '<p class="empty">Consultando…</p>';
  try {
    const rows = await api(
      `/cartera/comprobantes/pendientes?empresa_id=${empresaId()}`
    );
    pendientesLista.innerHTML = rows.length
      ? rows.map((item) => `
          <article class="proof-card">
            <strong>${escapar(item.oc)} · ${escapar(item.cliente)}</strong>
            <p>${escapar(item.nombre_archivo)}</p>
            <p>USD ${Number(item.monto_esperado || 0).toLocaleString("es-CO")} · ${escapar(item.estado_auditoria)}</p>
            <p><a href="/cartera/comprobantes/${item.id}/archivo?empresa_id=${empresaId()}" target="_blank" rel="noopener">Ver soporte</a></p>
          </article>
        `).join("")
      : '<p class="empty">No hay comprobantes pendientes.</p>';
    setEstado("Bandeja actualizada", "ok");
  } catch (error) {
    pendientesLista.innerHTML = `<p class="empty">${escapar(error.message)}</p>`;
    setEstado(error.message, "error");
  }
}

formComprobante.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(formComprobante);
  data.set("empresa_id", String(empresaId()));
  setEstado("Radicando comprobante…");

  try {
    const resultado = await api("/cartera/comprobantes", {
      method: "POST",
      body: data,
    });
    setEstado(`Comprobante ${resultado.id} radicado como PENDIENTE`, "ok");
    formComprobante.elements.archivo.value = "";
    await cargarPendientes();
  } catch (error) {
    setEstado(error.message, "error");
  }
});

document.querySelector("#cargar-operaciones").addEventListener("click", cargarOperaciones);
document.querySelector("#cargar-mora").addEventListener("click", cargarMora);
document.querySelector("#cargar-pendientes").addEventListener("click", cargarPendientes);
