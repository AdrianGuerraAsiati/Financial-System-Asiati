const loginView = document.querySelector("#login-view");
const loginForm = document.querySelector("#login-form");
const loginError = document.querySelector("#login-error");
const passwordForm = document.querySelector("#password-form");
const passwordError = document.querySelector("#password-error");
const appShell = document.querySelector("#app-shell");
const usuarioNombre = document.querySelector("#usuario-nombre");
const logoutButton = document.querySelector("#logout");
const empresaInput = document.querySelector("#empresa-id");
const estado = document.querySelector("#estado-global");
const operacionesBody = document.querySelector("#operaciones-body");
const moraBody = document.querySelector("#mora-body");
const proyeccionBody = document.querySelector("#proyeccion-body");
const detalleTitulo = document.querySelector("#detalle-titulo");
const detalleContenido = document.querySelector("#detalle-contenido");
const pendientesLista = document.querySelector("#pendientes-lista");
const formComprobante = document.querySelector("#form-comprobante");

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

function mostrarLogin() {
  appShell.hidden = true;
  passwordForm.hidden = true;
  loginForm.hidden = false;
  loginView.hidden = false;
}

function mostrarCambioPassword() {
  appShell.hidden = true;
  loginForm.hidden = true;
  passwordForm.hidden = false;
  loginView.hidden = false;
}

function mostrarApp(sesion) {
  loginView.hidden = true;
  appShell.hidden = false;
  usuarioNombre.textContent = sesion.usuario.nombre;

  const savedEmpresa = localStorage.getItem("asiati_empresa_id");
  empresaInput.innerHTML = sesion.empresas.map((empresa) =>
    `<option value="${empresa.id}">${escapar(empresa.nombre)}</option>`
  ).join("");

  if (savedEmpresa && sesion.empresas.some((empresa) => String(empresa.id) === savedEmpresa)) {
    empresaInput.value = savedEmpresa;
  }
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  let body = null;
  try { body = await response.json(); } catch (_) {}
  if (!response.ok) {
    if (response.status === 401 && !url.endsWith("/auth/login")) {
      mostrarLogin();
    }
    const detail = body?.detail || `Error HTTP ${response.status}`;
    throw new Error(detail);
  }
  return body;
}

async function cargarSesion() {
  const response = await fetch("/api/v1/auth/me");
  if (response.status === 401) {
    mostrarLogin();
    return;
  }
  const sesion = await response.json();
  if (!response.ok) {
    loginError.textContent = sesion?.detail || "No se pudo consultar la sesión.";
    loginError.hidden = false;
    mostrarLogin();
    return;
  }
  if (sesion.usuario.debe_cambiar_password) {
    mostrarCambioPassword();
    return;
  }
  mostrarApp(sesion);
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.hidden = true;
  const data = new FormData(loginForm);
  try {
    const resultado = await api("/api/v1/auth/login", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        email: data.get("email"),
        password: data.get("password"),
      }),
    });
    if (resultado.debe_cambiar_password) {
      passwordForm.elements.password_actual.value = data.get("password");
      mostrarCambioPassword();
      return;
    }
    await cargarSesion();
  } catch (error) {
    loginError.textContent = error.message;
    loginError.hidden = false;
  }
});

passwordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  passwordError.hidden = true;
  const data = new FormData(passwordForm);
  try {
    await api("/api/v1/auth/cambiar-password", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        password_actual: data.get("password_actual"),
        password_nueva: data.get("password_nueva"),
      }),
    });
    passwordForm.reset();
    await cargarSesion();
  } catch (error) {
    passwordError.textContent = error.message;
    passwordError.hidden = false;
  }
});

logoutButton.addEventListener("click", async () => {
  try {
    await fetch("/api/v1/auth/logout", {method: "POST"});
  } finally {
    mostrarLogin();
  }
});

async function cargarOperaciones() {
  setEstado("Consultando operaciones…");
  operacionesBody.innerHTML = '<tr><td colspan="7" class="empty">Consultando…</td></tr>';
  try {
    const rows = await api(`/api/v1/cartera/operaciones?empresa_id=${empresaId()}`);
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
    const rows = await api(`/api/v1/cartera/mora?empresa_id=${empresaId()}`);
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

async function cargarProyeccion() {
  setEstado("Consultando proyección…");
  proyeccionBody.innerHTML = '<tr><td colspan="7" class="empty">Consultando…</td></tr>';
  try {
    const rows = await api(`/api/v1/cartera/proyeccion?empresa_id=${empresaId()}`);
    proyeccionBody.innerHTML = rows.length
      ? rows.map((row) => `
          <tr>
            <td>${escapar(row.fecha)}</td>
            <td>${escapar(row.oc)}</td>
            <td>${escapar(row.cliente)}</td>
            <td>${escapar(row.pais)}</td>
            <td>${Number(row.monto || 0).toLocaleString("es-CO")}</td>
            <td>${escapar(row.comercial)}</td>
            <td>${escapar(row.estado)}</td>
          </tr>
        `).join("")
      : '<tr><td colspan="7" class="empty">No hay proyecciones.</td></tr>';
    setEstado("Proyección actualizada", "ok");
  } catch (error) {
    proyeccionBody.innerHTML = `<tr><td colspan="7" class="empty">${escapar(error.message)}</td></tr>`;
    setEstado(error.message, "error");
  }
}

async function cargarDetalle(oc) {
  detalleTitulo.textContent = oc;
  detalleContenido.textContent = "Consultando…";
  try {
    const detalle = await api(
      `/api/v1/cartera/operaciones/${encodeURIComponent(oc)}?empresa_id=${empresaId()}`
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
      `/api/v1/cartera/comprobantes/pendientes?empresa_id=${empresaId()}`
    );
    pendientesLista.innerHTML = rows.length
      ? rows.map((item) => `
          <article class="proof-card">
            <strong>${escapar(item.oc)} · ${escapar(item.cliente)}</strong>
            <p>${escapar(item.nombre_archivo)}</p>
            <p>USD ${Number(item.monto_esperado || 0).toLocaleString("es-CO")} · ${escapar(item.estado_auditoria)}</p>
            <p><a href="/api/v1/cartera/comprobantes/${item.id}/archivo?empresa_id=${empresaId()}" target="_blank" rel="noopener">Ver soporte</a></p>
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
    const resultado = await api("/api/v1/cartera/comprobantes", {
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
document.querySelector("#cargar-proyeccion").addEventListener("click", cargarProyeccion);
document.querySelector("#cargar-pendientes").addEventListener("click", cargarPendientes);


cargarSesion();
