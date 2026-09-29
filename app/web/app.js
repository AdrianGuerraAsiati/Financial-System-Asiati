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

const navCartera = document.querySelector('[data-view="cartera"]');
const navCompras = document.querySelector("#nav-compras");
const vistaCartera = document.querySelector("#vista-cartera");
const vistaCompras = document.querySelector("#vista-compras");
const estadoCompras = document.querySelector("#estado-compras");
const comprasFuenteEstado = document.querySelector("#compras-fuente-estado");
const comprasFuenteLineas = document.querySelector("#compras-fuente-lineas");
const comprasFuenteCache = document.querySelector("#compras-fuente-cache");
const comprasHojas = document.querySelector("#compras-hojas");
const comprasOcsBody = document.querySelector("#compras-ocs-body");
const comprasOcsTotal = document.querySelector("#compras-ocs-total");
const comprasLineasBody = document.querySelector("#compras-lineas-body");
const comprasLineasTitulo = document.querySelector("#compras-lineas-titulo");
const comprasCalidadLista = document.querySelector("#compras-calidad-lista");
const comprasCatalogosContenido = document.querySelector("#compras-catalogos-contenido");
const comprasFiltroPais = document.querySelector("#compras-filtro-pais");
const comprasFiltroQ = document.querySelector("#compras-filtro-q");
const comprasFiltroMixtas = document.querySelector("#compras-filtro-mixtas");

let moduloActivo = "cartera";

empresaInput.addEventListener("change", () => {
  localStorage.setItem("asiati_empresa_id", empresaInput.value);
  if (moduloActivo === "compras") {
    cargarComprasTodo();
  }
});

function empresaId() {
  return Number(empresaInput.value);
}

function setEstado(mensaje, tipo = "") {
  estado.textContent = mensaje;
  estado.className = `status ${tipo}`.trim();
}

function setEstadoCompras(mensaje, tipo = "") {
  estadoCompras.textContent = mensaje;
  estadoCompras.className = `status ${tipo}`.trim();
}

function mostrarModulo(modulo) {
  moduloActivo = modulo;
  const compras = modulo === "compras";
  vistaCartera.hidden = compras;
  vistaCompras.hidden = !compras;
  navCartera.classList.toggle("active", !compras);
  navCompras.classList.toggle("active", compras);

  if (compras) {
    cargarComprasTodo();
  }
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

  const puedeVerCompras = Boolean(sesion.permisos?.["compras.ver"]);
  navCompras.hidden = !puedeVerCompras;
  if (!puedeVerCompras && moduloActivo === "compras") {
    mostrarModulo("cartera");
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


function listaEtiquetas(valores) {
  if (!valores?.length) return '<span class="muted">—</span>';
  return valores.map((valor) => `<span class="tag">${escapar(valor)}</span>`).join(" ");
}

function renderDiagnosticoHoja(hoja) {
  const faltantes = hoja.campos_criticos_faltantes || [];
  const duplicados = hoja.encabezados_duplicados || [];
  const advertencias = [
    faltantes.length ? `Críticos faltantes: ${faltantes.join(", ")}` : "",
    duplicados.length ? `Duplicados: ${duplicados.join(", ")}` : "",
    hoja.campos_esperados_faltantes?.length
      ? `Esperados no disponibles: ${hoja.campos_esperados_faltantes.join(", ")}`
      : "",
  ].filter(Boolean);

  return `
    <article class="diagnostic-card ${hoja.valido ? "ok-card" : "error-card"}">
      <div class="diagnostic-title">
        <strong>${escapar(hoja.pais)}</strong>
        <span class="tag">${hoja.valido ? "Esquema OK" : "Revisar esquema"}</span>
      </div>
      <p>${Number(hoja.filas_datos || 0).toLocaleString("es-CO")} filas · ${hoja.campos_reconocidos.length} campos consumidos</p>
      <p class="muted">${escapar(hoja.rango)}</p>
      ${advertencias.length
        ? `<div class="notice compact">${advertencias.map(escapar).join("<br>")}</div>`
        : '<p class="ok-text">Sin drift crítico detectado.</p>'}
      <details>
        <summary>Ver contrato</summary>
        <p><strong>Consumidos:</strong> ${escapar(hoja.campos_reconocidos.join(", ") || "Ninguno")}</p>
        <p><strong>No consumidos:</strong> ${escapar(hoja.encabezados_no_consumidos.join(", ") || "Ninguno")}</p>
      </details>
    </article>
  `;
}

async function cargarComprasDiagnostico(forzar = false) {
  setEstadoCompras(forzar ? "Releyendo Google Sheet…" : "Consultando fuente…");
  const params = new URLSearchParams({
    empresa_id: String(empresaId()),
    forzar_lectura: String(Boolean(forzar)),
  });

  try {
    const data = await api(`/api/v1/compras/fuente/estado?${params}`);
    comprasFuenteEstado.textContent = data.estado;
    comprasFuenteEstado.className = data.estado === "OK" ? "metric-ok" : "metric-error";
    comprasFuenteLineas.textContent = Number(data.lineas || 0).toLocaleString("es-CO");
    comprasFuenteCache.textContent = data.cache?.tiene_snapshot
      ? `${Math.round(data.cache.edad_segundos || 0)}s / ${data.cache.ttl_segundos}s`
      : "Sin snapshot";
    comprasHojas.innerHTML = data.hojas.map(renderDiagnosticoHoja).join("");
    setEstadoCompras(
      data.estado === "OK" ? "Fuente validada" : "Fuente con cambios de esquema",
      data.estado === "OK" ? "ok" : "error"
    );
    return data;
  } catch (error) {
    comprasFuenteEstado.textContent = "ERROR";
    comprasFuenteEstado.className = "metric-error";
    comprasHojas.innerHTML = `<p class="empty">${escapar(error.message)}</p>`;
    setEstadoCompras(error.message, "error");
    throw error;
  }
}

function parametrosOcs() {
  const params = new URLSearchParams({empresa_id: String(empresaId()), limit: "200"});
  if (comprasFiltroPais.value) params.set("pais", comprasFiltroPais.value);
  if (comprasFiltroQ.value.trim()) params.set("q", comprasFiltroQ.value.trim());
  if (comprasFiltroMixtas.value) params.set("mixtas", comprasFiltroMixtas.value);
  return params;
}

async function cargarComprasOCs() {
  comprasOcsBody.innerHTML = '<tr><td colspan="9" class="empty">Consultando…</td></tr>';
  try {
    const data = await api(`/api/v1/compras/ocs?${parametrosOcs()}`);
    comprasOcsTotal.textContent = `${Number(data.total || 0).toLocaleString("es-CO")} agrupaciones encontradas`;
    comprasOcsBody.innerHTML = data.items.length
      ? data.items.map((oc) => {
          const mixta = oc.estado_mixto || oc.proveedor_mixto || oc.transporte_mixto;
          const composicion = !oc.oc_identificada
            ? '<span class="tag warning-tag">Sin OC</span>'
            : mixta
              ? '<span class="tag warning-tag">Mixta</span>'
              : '<span class="tag">Simple</span>';
          return `
            <tr>
              <td>${escapar(oc.pais)}</td>
              <td>${escapar(oc.numero_oc || "Sin OC")}</td>
              <td>${Number(oc.lineas || 0).toLocaleString("es-CO")}</td>
              <td>${listaEtiquetas(oc.proveedores)}</td>
              <td>${listaEtiquetas(oc.estados)}</td>
              <td>${listaEtiquetas(oc.etapas_logisticas)}</td>
              <td>${listaEtiquetas(oc.modos_transporte)}</td>
              <td>${composicion}</td>
              <td>${oc.oc_identificada
                ? `<button type="button" data-compras-oc="${escapar(oc.numero_oc)}" data-compras-pais="${escapar(oc.pais)}">Ver líneas</button>`
                : ""}</td>
            </tr>
          `;
        }).join("")
      : '<tr><td colspan="9" class="empty">No hay OCs con esos filtros.</td></tr>';

    comprasOcsBody.querySelectorAll("[data-compras-oc]").forEach((button) => {
      button.addEventListener("click", () => {
        cargarComprasLineas(button.dataset.comprasPais, button.dataset.comprasOc);
      });
    });
  } catch (error) {
    comprasOcsBody.innerHTML = `<tr><td colspan="9" class="empty">${escapar(error.message)}</td></tr>`;
    comprasOcsTotal.textContent = "";
    setEstadoCompras(error.message, "error");
    throw error;
  }
}


async function cargarComprasLineas(pais, oc) {
  comprasLineasTitulo.textContent = `${pais} · ${oc}`;
  comprasLineasBody.innerHTML = '<tr><td colspan="9" class="empty">Consultando líneas…</td></tr>';

  const params = new URLSearchParams({
    empresa_id: String(empresaId()),
    pais,
    oc,
    limit: "500",
  });

  try {
    const data = await api(`/api/v1/compras/lineas?${params}`);
    comprasLineasBody.innerHTML = data.items.length
      ? data.items.map((linea) => `
          <tr>
            <td>${Number(linea.fila_fuente || 0).toLocaleString("es-CO")}</td>
            <td>${escapar(linea.sku)}</td>
            <td>${escapar(linea.proveedor)}</td>
            <td>${escapar(linea.estado_origen)}</td>
            <td>${escapar(linea.etapa_logistica)}</td>
            <td>${escapar(linea.modo_transporte_origen)}</td>
            <td>${escapar(linea.eta)}</td>
            <td>${escapar(linea.valor_total_compra_usd_origen)}</td>
            <td>${escapar(linea.valor_oci_ddp_origen)}</td>
          </tr>
        `).join("")
      : '<tr><td colspan="9" class="empty">No se encontraron líneas para esta OC.</td></tr>';
  } catch (error) {
    comprasLineasBody.innerHTML = `<tr><td colspan="9" class="empty">${escapar(error.message)}</td></tr>`;
    setEstadoCompras(error.message, "error");
  }
}

async function cargarComprasCalidad() {
  comprasCalidadLista.innerHTML = '<p class="empty">Consultando…</p>';
  try {
    const data = await api(`/api/v1/compras/calidad?empresa_id=${empresaId()}`);
    comprasCalidadLista.innerHTML = data.observaciones.length
      ? data.observaciones.map((item) => `
          <article class="quality-card">
            <div class="quality-card-title">
              <strong>${escapar(item.codigo)}</strong>
              <span class="tag">${Number(item.cantidad || 0).toLocaleString("es-CO")}</span>
            </div>
            <p>${escapar(item.descripcion)}</p>
            <small>${escapar(item.categoria)}</small>
            ${item.muestras?.length
              ? `<details><summary>Ejemplos</summary>${item.muestras.map((m) =>
                  `<p class="muted">${escapar(m.pais)} · fila ${m.fila_fuente} · ${escapar(m.numero_oc || "sin OC")}</p>`
                ).join("")}</details>`
              : ""}
          </article>
        `).join("")
      : '<p class="empty">No se encontraron observaciones con las reglas actuales.</p>';
  } catch (error) {
    comprasCalidadLista.innerHTML = `<p class="empty">${escapar(error.message)}</p>`;
    setEstadoCompras(error.message, "error");
    throw error;
  }
}

function listaConteos(titulo, valores) {
  const entradas = Object.entries(valores || {});
  return `
    <article class="catalog-card">
      <strong>${escapar(titulo)}</strong>
      ${entradas.length
        ? entradas.map(([nombre, cantidad]) =>
            `<div class="catalog-row"><span>${escapar(nombre)}</span><b>${Number(cantidad).toLocaleString("es-CO")}</b></div>`
          ).join("")
        : '<p class="muted">Sin valores</p>'}
    </article>
  `;
}

async function cargarComprasCatalogos() {
  comprasCatalogosContenido.innerHTML = '<p class="empty">Consultando…</p>';
  try {
    const data = await api(`/api/v1/compras/catalogos?empresa_id=${empresaId()}`);
    comprasCatalogosContenido.innerHTML = [
      listaConteos("Estados por definir", data.estados_por_definir),
      listaConteos("Etapas logísticas", data.etapas_logisticas),
      listaConteos("Modos de transporte", data.modos_transporte),
    ].join("");
  } catch (error) {
    comprasCatalogosContenido.innerHTML = `<p class="empty">${escapar(error.message)}</p>`;
    setEstadoCompras(error.message, "error");
    throw error;
  }
}

async function cargarComprasTodo(forzar = false) {
  try {
    const diagnostico = await cargarComprasDiagnostico(forzar);
    if (diagnostico.estado !== "OK") {
      comprasOcsBody.innerHTML = '<tr><td colspan="9" class="empty">Lectura bloqueada hasta resolver el drift crítico de esquema.</td></tr>';
      comprasLineasBody.innerHTML = '<tr><td colspan="9" class="empty">Lectura bloqueada hasta resolver el drift crítico de esquema.</td></tr>';
      comprasLineasTitulo.textContent = "Esquema degradado";
      comprasCalidadLista.innerHTML = '<p class="empty">Calidad no calculada con esquema degradado.</p>';
      comprasCatalogosContenido.innerHTML = '<p class="empty">Catálogos no calculados con esquema degradado.</p>';
      return;
    }
    await Promise.all([
      cargarComprasOCs(),
      cargarComprasCalidad(),
      cargarComprasCatalogos(),
    ]);
    setEstadoCompras("Compras actualizadas", "ok");
  } catch (_) {
    // Cada bloque deja visible su propio error.
  }
}


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

navCartera.addEventListener("click", () => mostrarModulo("cartera"));
navCompras.addEventListener("click", () => mostrarModulo("compras"));
document.querySelector("#compras-refrescar-fuente").addEventListener("click", () => cargarComprasTodo(true));
document.querySelector("#compras-cargar-ocs").addEventListener("click", cargarComprasOCs);
document.querySelector("#compras-cargar-calidad").addEventListener("click", cargarComprasCalidad);
document.querySelector("#compras-cargar-catalogos").addEventListener("click", cargarComprasCatalogos);
comprasFiltroPais.addEventListener("change", cargarComprasOCs);
comprasFiltroMixtas.addEventListener("change", cargarComprasOCs);
comprasFiltroQ.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    cargarComprasOCs();
  }
});

cargarSesion();
