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

const navInicio = document.querySelector("#nav-inicio");
const navCartera = document.querySelector("#nav-cartera");
const navCompras = document.querySelector("#nav-compras");
const vistaInicio = document.querySelector("#vista-inicio");
const vistaCartera = document.querySelector("#vista-cartera");
const vistaCompras = document.querySelector("#vista-compras");
const inicioSubtitulo = document.querySelector("#inicio-subtitulo");
const inicioActualizado = document.querySelector("#inicio-actualizado");
const inicioModulos = document.querySelector("#inicio-modulos");
const inicioAtencion = document.querySelector("#inicio-atencion");
const inicioEstadoDatos = document.querySelector("#inicio-estado-datos");
const estadoCompras = document.querySelector("#estado-compras");
const comprasFuenteEstado = document.querySelector("#compras-fuente-estado");
const comprasFuenteLineas = document.querySelector("#compras-fuente-lineas");
const comprasFuenteCache = document.querySelector("#compras-fuente-cache");
const comprasResumenOcs = document.querySelector("#compras-resumen-ocs");
const comprasResumenMixtas = document.querySelector("#compras-resumen-mixtas");
const comprasResumenPendientes = document.querySelector("#compras-resumen-pendientes");
const comprasEjecutivoCosto = document.querySelector("#compras-ejecutivo-costo");
const comprasEjecutivoDdp = document.querySelector("#compras-ejecutivo-ddp");
const comprasEjecutivoOcs = document.querySelector("#compras-ejecutivo-ocs");
const comprasEjecutivoAtencion = document.querySelector("#compras-ejecutivo-atencion");
const comprasGraficoEstados = document.querySelector("#compras-grafico-estados");
const comprasGraficoTransporte = document.querySelector("#compras-grafico-transporte");
const comprasAtencionLista = document.querySelector("#compras-atencion-lista");
const comprasValidacionEstado = document.querySelector("#compras-validacion-estado");
const comprasValidacionDetalle = document.querySelector("#compras-validacion-detalle");
const comprasValidacionBody = document.querySelector("#compras-validacion-body");
const comprasExportar = document.querySelector("#compras-exportar");
const comprasKpiCosto = document.querySelector("#compras-kpi-costo");
const comprasKpiDdp = document.querySelector("#compras-kpi-ddp");
const comprasKpiCostoCalidad = document.querySelector("#compras-kpi-costo-calidad");
const comprasKpiDdpCalidad = document.querySelector("#compras-kpi-ddp-calidad");
const comprasKpisEstadosBody = document.querySelector("#compras-kpis-estados-body");
const comprasKpisNota = document.querySelector("#compras-kpis-nota");
const comprasHojas = document.querySelector("#compras-hojas");
const comprasOcsBody = document.querySelector("#compras-ocs-body");
const comprasOcsTotal = document.querySelector("#compras-ocs-total");
const comprasOcsPagina = document.querySelector("#compras-ocs-pagina");
const comprasOcsAnterior = document.querySelector("#compras-ocs-anterior");
const comprasOcsSiguiente = document.querySelector("#compras-ocs-siguiente");
const comprasLineasBody = document.querySelector("#compras-lineas-body");
const comprasLineasTitulo = document.querySelector("#compras-lineas-titulo");
const comprasCalidadLista = document.querySelector("#compras-calidad-lista");
const comprasCatalogosContenido = document.querySelector("#compras-catalogos-contenido");
const comprasCoberturaContenido = document.querySelector("#compras-cobertura-contenido");
const comprasLlegadasBody = document.querySelector("#compras-llegadas-body");
const comprasTimelineTitulo = document.querySelector("#compras-timeline-titulo");
const comprasTimelineLista = document.querySelector("#compras-timeline-lista");
const comprasSnapshotsLista = document.querySelector("#compras-snapshots-lista");
const comprasFiltroPais = document.querySelector("#compras-filtro-pais");
const comprasFiltroQ = document.querySelector("#compras-filtro-q");
const comprasFiltroMixtas = document.querySelector("#compras-filtro-mixtas");

let moduloActivo = "inicio";
let comprasOcsOffset = 0;
const COMPRAS_OCS_LIMIT = 100;

empresaInput.addEventListener("change", () => {
  localStorage.setItem("asiati_empresa_id", empresaInput.value);
  if (moduloActivo === "inicio") {
    cargarDashboardPrincipal();
  } else if (moduloActivo === "compras") {
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
  const inicio = modulo === "inicio";
  const cartera = modulo === "cartera";
  const compras = modulo === "compras";

  vistaInicio.hidden = !inicio;
  vistaCartera.hidden = !cartera;
  vistaCompras.hidden = !compras;

  navInicio.classList.toggle("active", inicio);
  navCartera.classList.toggle("active", cartera);
  navCompras.classList.toggle("active", compras);

  if (inicio) {
    cargarDashboardPrincipal();
  } else if (compras) {
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

  const puedeVerCartera = Boolean(sesion.permisos?.["cartera.ver"]);
  const puedeVerCompras = Boolean(sesion.permisos?.["compras.ver"]);
  navCartera.hidden = !puedeVerCartera;
  navCompras.hidden = !puedeVerCompras;

  mostrarModulo("inicio");
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


function numeroInicio(valor) {
  if (valor === null || valor === undefined) return "—";
  return Number(valor).toLocaleString("es-CO");
}

function moduloEstadoDisponible(modulo) {
  return modulo.disponible
    ? '<span class="home-status-pill home-status-ok">Disponible</span>'
    : '<span class="home-status-pill home-status-muted">No disponible</span>';
}

function renderModuloInicio(modulo) {
  const resumen = modulo.resumen || {};
  let metricas = "";

  if (modulo.codigo === "cartera") {
    metricas = `
      <div class="home-module-metrics">
        <div><span>Operaciones</span><strong>${numeroInicio(resumen.operaciones)}</strong></div>
        <div><span>Registros mora</span><strong>${numeroInicio(resumen.registros_mora)}</strong></div>
        <div><span>Proyecciones</span><strong>${numeroInicio(resumen.proyecciones)}</strong></div>
        <div><span>Comprobantes pendientes</span><strong>${numeroInicio(resumen.comprobantes_pendientes)}</strong></div>
      </div>
    `;
  } else if (modulo.codigo === "compras") {
    metricas = `
      <div class="home-module-metrics">
        <div><span>Costo compra</span><strong>${formatearUSD(resumen.costo_compra_usd)}</strong></div>
        <div><span>Valor DDP</span><strong>${formatearUSD(resumen.valor_comercial_ddp_usd)}</strong></div>
        <div><span>OCs población actual</span><strong>${numeroInicio(resumen.ocs_poblacion_actual)}</strong></div>
        <div><span>Observaciones</span><strong>${numeroInicio(resumen.puntos_atencion)}</strong></div>
      </div>
    `;
  } else if (modulo.codigo === "conciliacion") {
    const periodo = resumen.ultimo_periodo;
    metricas = `
      <div class="home-module-metrics">
        <div><span>Hallazgos abiertos</span><strong>${numeroInicio(resumen.hallazgos_abiertos)}</strong></div>
        <div><span>Críticos abiertos</span><strong>${numeroInicio(resumen.hallazgos_criticos_abiertos)}</strong></div>
        <div class="span-home-two"><span>Último período</span><strong class="home-period">${periodo ? `${escapar(periodo.fecha_inicio)} → ${escapar(periodo.fecha_fin)}` : "Sin ejecuciones"}</strong></div>
      </div>
    `;
  }

  const accion = modulo.accion
    ? `<button type="button" class="secondary-button" data-home-view="${escapar(modulo.accion.vista)}">${escapar(modulo.accion.texto)}</button>`
    : '<span class="muted home-no-action">Vista dedicada pendiente</span>';

  return `
    <article class="home-module-card" data-home-module="${escapar(modulo.codigo)}">
      <div class="home-module-heading">
        <div>
          <span class="home-module-kicker">${escapar(modulo.codigo)}</span>
          <h3>${escapar(modulo.titulo)}</h3>
        </div>
        ${moduloEstadoDisponible(modulo)}
      </div>
      ${metricas}
      <div class="home-module-footer">${accion}</div>
    </article>
  `;
}

function estadoFuenteTexto(estado) {
  if (!estado) return "Sin información";
  if (estado.estado) return estado.estado.replaceAll("_", " ");
  return "Sin información";
}

function renderEstadoModulo(modulo) {
  const estado = modulo.estado_datos || {};

  if (modulo.codigo === "cartera") {
    return `
      <article class="home-data-card">
        <strong>Cartera</strong>
        ${Object.entries(estado).map(([fuente, detalle]) => `
          <div class="home-data-row">
            <span>${escapar(fuente)}</span>
            <b class="${detalle.estado === "DISPONIBLE" ? "ok-text" : "muted"}">${escapar(estadoFuenteTexto(detalle))}</b>
          </div>
        `).join("")}
      </article>
    `;
  }

  if (modulo.codigo === "compras") {
    const modo = estado.modo_fuente ? ` · ${estado.modo_fuente}` : "";
    return `
      <article class="home-data-card">
        <strong>Compras</strong>
        <div class="home-data-row"><span>Fuente</span><b>${escapar(estadoFuenteTexto(estado))}${escapar(modo)}</b></div>
        <div class="home-data-row"><span>Esquema</span><b>${estado.esquema_valido === false ? "Revisar" : "OK"}</b></div>
        <small class="muted">${estado.cargado_en ? `Lectura: ${new Date(estado.cargado_en).toLocaleString("es-CO")}` : escapar(estado.detalle || "")}</small>
      </article>
    `;
  }

  const periodo = modulo.resumen?.ultimo_periodo;
  return `
    <article class="home-data-card">
      <strong>Conciliación</strong>
      <div class="home-data-row"><span>Estado</span><b>${escapar(estadoFuenteTexto(estado))}</b></div>
      <small class="muted">${periodo ? `Período ${escapar(periodo.fecha_inicio)} → ${escapar(periodo.fecha_fin)}${periodo.cerrado ? " · cerrado" : " · abierto"}` : escapar(estado.detalle || "")}</small>
    </article>
  `;
}

function renderAtencionInicio(item) {
  const accion = item.url_destino
    ? `<button type="button" class="secondary-button" data-home-view="${escapar(item.url_destino)}">Abrir</button>`
    : "";
  return `
    <article class="home-attention-item">
      <div class="home-attention-copy">
        <div class="home-attention-meta">
          <span class="tag">${escapar(item.modulo)}</span>
          <span class="muted">${escapar(item.categoria)}</span>
        </div>
        <strong>${escapar(item.titulo)}</strong>
        <p>${escapar(item.descripcion)}</p>
        ${item.referencia ? `<small>Referencia: ${escapar(item.referencia)}</small>` : ""}
      </div>
      ${accion}
    </article>
  `;
}

function enlazarAccionesInicio() {
  document.querySelectorAll("[data-home-view]").forEach((button) => {
    button.addEventListener("click", () => mostrarModulo(button.dataset.homeView));
  });
}

async function cargarDashboardPrincipal() {
  inicioModulos.innerHTML = '<article class="home-module-card"><p class="empty">Cargando módulos visibles…</p></article>';
  inicioAtencion.innerHTML = '<p class="empty">Cargando…</p>';
  inicioEstadoDatos.innerHTML = '<p class="empty">Cargando…</p>';
  inicioActualizado.textContent = "Actualizando…";

  try {
    const data = await api(`/api/v1/dashboard/principal?empresa_id=${empresaId()}`);
    inicioSubtitulo.textContent =
      `${data.empresa.nombre} · Resumen de módulos visibles y elementos que requieren revisión.`;

    inicioModulos.innerHTML = data.modulos?.length
      ? data.modulos.map(renderModuloInicio).join("")
      : '<article class="home-module-card"><p class="empty">Tu rol todavía no tiene módulos de consulta habilitados.</p></article>';

    inicioAtencion.innerHTML = data.atencion?.length
      ? data.atencion.map(renderAtencionInicio).join("")
      : '<p class="empty">No hay elementos de atención disponibles para los módulos visibles.</p>';

    inicioEstadoDatos.innerHTML = data.modulos?.length
      ? data.modulos.map(renderEstadoModulo).join("")
      : '<p class="empty">Sin módulos visibles.</p>';

    inicioActualizado.textContent =
      `Actualizado ${new Date(data.generado_en).toLocaleString("es-CO")}`;
    enlazarAccionesInicio();
  } catch (error) {
    inicioModulos.innerHTML = `<article class="home-module-card"><p class="empty">${escapar(error.message)}</p></article>`;
    inicioAtencion.innerHTML = '<p class="empty">No se pudo cargar la bandeja transversal.</p>';
    inicioEstadoDatos.innerHTML = '<p class="empty">No se pudo consultar el estado de datos.</p>';
    inicioActualizado.textContent = "Error al actualizar";
  }
}

function formatearUSD(valor) {
  if (valor === null || valor === undefined || valor === "") return "—";
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return escapar(valor);
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numero);
}

function descripcionCalidadMonetaria(familia) {
  if (!familia?.disponible) {
    const hojas = familia?.hojas_sin_campo?.join(", ") || "fuente";
    return `No disponible: falta el campo en ${hojas}`;
  }
  const activo = familia.activo || {};
  const problemas =
    Number(activo.lineas_sin_valor || 0) +
    Number(activo.lineas_valor_invalido || 0);
  return problemas
    ? `${problemas} líneas activas sin valor utilizable`
    : `${Number(activo.lineas_con_valor || 0).toLocaleString("es-CO")} líneas activas con valor`;
}

function parametrosPais() {
  const params = new URLSearchParams({empresa_id: String(empresaId())});
  if (comprasFiltroPais.value) params.set("pais", comprasFiltroPais.value);
  return params;
}

function renderBarras(conteos) {
  const entradas = Object.entries(conteos || {});
  if (!entradas.length) return '<p class="empty">Sin datos para este alcance.</p>';
  const maximo = Math.max(...entradas.map(([, valor]) => Number(valor || 0)), 1);
  return entradas
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .map(([nombre, valor]) => {
      const numero = Number(valor || 0);
      const ancho = Math.max(4, Math.round((numero / maximo) * 100));
      return `
        <div class="bar-row">
          <div class="bar-label"><span>${escapar(nombre)}</span><strong>${numero.toLocaleString("es-CO")}</strong></div>
          <div class="bar-track"><span style="width:${ancho}%"></span></div>
        </div>
      `;
    })
    .join("");
}

async function cargarComprasDashboard() {
  try {
    const data = await api(`/api/v1/compras/dashboard?${parametrosPais()}`);
    const familias = Object.fromEntries(
      (data.familias_monetarias || []).map((familia) => [familia.codigo, familia])
    );
    const costo = familias.costo_compra;
    const ddp = familias.valor_comercial_ddp;
    const estructural = data.estructural || {};

    comprasEjecutivoCosto.textContent = costo?.disponible
      ? formatearUSD(costo.activo?.monto_usd)
      : "No disponible";
    comprasEjecutivoDdp.textContent = ddp?.disponible
      ? formatearUSD(ddp.activo?.monto_usd)
      : "No disponible";
    comprasEjecutivoOcs.textContent = Number(
      estructural.ocs_con_al_menos_una_linea_en_poblacion_actual || 0
    ).toLocaleString("es-CO");
    comprasEjecutivoAtencion.textContent = Number(
      estructural.puntos_atencion_total || 0
    ).toLocaleString("es-CO");

    comprasGraficoEstados.innerHTML = renderBarras(
      estructural.lineas_activas_por_estado
    );
    comprasGraficoTransporte.innerHTML = renderBarras(
      estructural.lineas_activas_por_transporte
    );
  } catch (error) {
    comprasEjecutivoCosto.textContent = "—";
    comprasEjecutivoDdp.textContent = "—";
    comprasEjecutivoOcs.textContent = "—";
    comprasEjecutivoAtencion.textContent = "—";
    comprasGraficoEstados.innerHTML = `<p class="empty">${escapar(error.message)}</p>`;
    comprasGraficoTransporte.innerHTML = `<p class="empty">${escapar(error.message)}</p>`;
    setEstadoCompras(error.message, "error");
    throw error;
  }
}

function renderPuntoAtencion(item) {
  return `
    <article class="attention-card">
      <div class="quality-card-title">
        <div>
          <span class="eyebrow">${escapar(item.categoria)}</span>
          <strong>${escapar(item.titulo)}</strong>
        </div>
        <span class="attention-count">${Number(item.cantidad || 0).toLocaleString("es-CO")}</span>
      </div>
      <p>${escapar(item.descripcion)}</p>
      ${item.muestras?.length
        ? `<details><summary>Ver ejemplos</summary>${item.muestras.map((muestra) =>
            `<p class="attention-evidence"><b>${escapar(muestra.pais)}</b> · ${escapar(muestra.numero_oc || "sin OC")} · ${escapar(muestra.evidencia)}</p>`
          ).join("")}</details>`
        : ""}
    </article>
  `;
}

async function cargarComprasAtencion() {
  comprasAtencionLista.innerHTML = '<p class="empty">Consultando…</p>';
  try {
    const data = await api(`/api/v1/compras/atencion?${parametrosPais()}`);
    comprasAtencionLista.innerHTML = data.items?.length
      ? data.items.map(renderPuntoAtencion).join("")
      : '<p class="empty">No hay observaciones con las reglas objetivas actuales.</p>';
    comprasEjecutivoAtencion.textContent = Number(
      data.total_observaciones || 0
    ).toLocaleString("es-CO");
  } catch (error) {
    comprasAtencionLista.innerHTML = `<p class="empty">${escapar(error.message)}</p>`;
    setEstadoCompras(error.message, "error");
    throw error;
  }
}

async function cargarComprasValidacion(forzar = false) {
  comprasValidacionEstado.textContent = "Comparando…";
  comprasValidacionDetalle.textContent = "";
  comprasValidacionBody.innerHTML = '<tr><td colspan="6" class="empty">Consultando vista derivada…</td></tr>';

  const params = new URLSearchParams({
    empresa_id: String(empresaId()),
    forzar_lectura: String(Boolean(forzar)),
  });

  try {
    const data = await api(`/api/v1/compras/validacion/tablero?${params}`);
    if (!data.disponible) {
      comprasValidacionEstado.textContent = "Comparación no disponible";
      comprasValidacionEstado.className = "validation-neutral";
      comprasValidacionDetalle.textContent = data.motivo || "";
      comprasValidacionBody.innerHTML = '<tr><td colspan="6" class="empty">No hay una referencia comparable todavía.</td></tr>';
      return;
    }

    const filtroPais = comprasFiltroPais.value;
    const filas = (data.comparaciones || []).filter(
      (item) => !filtroPais || item.pais === filtroPais
    );
    const diferencias = filas.filter((item) => item.resultado !== "COINCIDE").length;
    comprasValidacionEstado.textContent = diferencias
      ? `${diferencias} diferencias para revisar`
      : "Detalle y tablero coinciden";
    comprasValidacionEstado.className = diferencias ? "validation-warning" : "validation-ok";
    comprasValidacionDetalle.textContent =
      `${filas.length} comparaciones DDP por estado · ${data.rango || "Supply Chain"}`;

    comprasValidacionBody.innerHTML = filas.length
      ? filas.map((item) => `
          <tr>
            <td>${escapar(item.pais)}</td>
            <td>${escapar(item.estado)}</td>
            <td>${formatearUSD(item.detalle_ddp)}</td>
            <td>${formatearUSD(item.tablero_ddp)}</td>
            <td>${item.diferencia === null ? "—" : formatearUSD(item.diferencia)}</td>
            <td><span class="tag ${item.resultado === "COINCIDE" ? "ok-tag" : "warning-tag"}">${escapar(item.resultado)}</span></td>
          </tr>
        `).join("")
      : '<tr><td colspan="6" class="empty">No hay comparaciones para este país.</td></tr>';
  } catch (error) {
    comprasValidacionEstado.textContent = "Error de comparación";
    comprasValidacionEstado.className = "validation-warning";
    comprasValidacionDetalle.textContent = error.message;
    comprasValidacionBody.innerHTML = `<tr><td colspan="6" class="empty">${escapar(error.message)}</td></tr>`;
    setEstadoCompras(error.message, "error");
    throw error;
  }
}

function exportarCompras() {
  const params = new URLSearchParams({empresa_id: String(empresaId())});
  window.location.href = `/api/v1/compras/export.zip?${params}`;
}

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
    const etiquetaFuente = data.modo_fuente === "DEMO_LOCAL"
      ? `${data.estado} · DEMO LOCAL`
      : data.estado;
    comprasFuenteEstado.textContent = etiquetaFuente;
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
  const params = new URLSearchParams({
    empresa_id: String(empresaId()),
    limit: String(COMPRAS_OCS_LIMIT),
    offset: String(comprasOcsOffset),
  });
  if (comprasFiltroPais.value) params.set("pais", comprasFiltroPais.value);
  if (comprasFiltroQ.value.trim()) params.set("q", comprasFiltroQ.value.trim());
  if (comprasFiltroMixtas.value) params.set("mixtas", comprasFiltroMixtas.value);
  return params;
}

async function cargarComprasOCs() {
  comprasOcsBody.innerHTML = '<tr><td colspan="9" class="empty">Consultando…</td></tr>';
  try {
    const data = await api(`/api/v1/compras/ocs?${parametrosOcs()}`);
    const total = Number(data.total || 0);
    const pagina = Math.floor(comprasOcsOffset / COMPRAS_OCS_LIMIT) + 1;
    const paginas = Math.max(1, Math.ceil(total / COMPRAS_OCS_LIMIT));
    comprasOcsTotal.textContent = `${total.toLocaleString("es-CO")} agrupaciones encontradas`;
    comprasOcsPagina.textContent = `Página ${pagina} de ${paginas}`;
    comprasOcsAnterior.disabled = comprasOcsOffset <= 0;
    comprasOcsSiguiente.disabled = comprasOcsOffset + COMPRAS_OCS_LIMIT >= total;
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
        Promise.all([
          cargarComprasLineas(button.dataset.comprasPais, button.dataset.comprasOc),
          cargarComprasTimeline(button.dataset.comprasPais, button.dataset.comprasOc),
        ]).catch(() => {});
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

async function cargarComprasKpis() {
  const params = new URLSearchParams({empresa_id: String(empresaId())});
  if (comprasFiltroPais.value) params.set("pais", comprasFiltroPais.value);

  comprasKpisEstadosBody.innerHTML = '<tr><td colspan="4" class="empty">Calculando…</td></tr>';

  try {
    const data = await api(`/api/v1/compras/kpis?${params}`);
    const porCodigo = Object.fromEntries(
      (data.familias || []).map((familia) => [familia.codigo, familia])
    );
    const costo = porCodigo.costo_compra;
    const ddp = porCodigo.valor_comercial_ddp;

    comprasKpiCosto.textContent = costo?.disponible
      ? formatearUSD(costo.activo?.monto_usd)
      : "No disponible";
    comprasKpiDdp.textContent = ddp?.disponible
      ? formatearUSD(ddp.activo?.monto_usd)
      : "No disponible";
    comprasKpiCostoCalidad.textContent = descripcionCalidadMonetaria(costo);
    comprasKpiDdpCalidad.textContent = descripcionCalidadMonetaria(ddp);

    const costoEstados = Object.fromEntries(
      (costo?.por_estado || []).map((item) => [item.estado, item])
    );
    const ddpEstados = Object.fromEntries(
      (ddp?.por_estado || []).map((item) => [item.estado, item])
    );
    const estados = data.poblacion_supply_chain_actual?.estados_incluidos || [];

    comprasKpisEstadosBody.innerHTML = estados.length
      ? estados.map((estadoFuente) => {
          const costoEstado = costoEstados[estadoFuente];
          const ddpEstado = ddpEstados[estadoFuente];
          const lineas = costoEstado?.lineas ?? ddpEstado?.lineas ?? 0;
          return `
            <tr>
              <td>${escapar(estadoFuente)}</td>
              <td>${Number(lineas).toLocaleString("es-CO")}</td>
              <td>${costo?.disponible ? formatearUSD(costoEstado?.monto_usd || "0") : "—"}</td>
              <td>${ddp?.disponible ? formatearUSD(ddpEstado?.monto_usd || "0") : "—"}</td>
            </tr>
          `;
        }).join("")
      : '<tr><td colspan="4" class="empty">No hay estados en la población configurada.</td></tr>';

    const alcance = data.pais ? ` · ${data.pais}` : " · CO + EC + CL";
    comprasKpisNota.textContent =
      `Población: estados del pivote Supply Chain actual${alcance}. ` +
      "Las dos familias responden preguntas distintas; no se ha definido todavía el KPI ejecutivo de “en tránsito / en el mar”.";
  } catch (error) {
    comprasKpiCosto.textContent = "—";
    comprasKpiDdp.textContent = "—";
    comprasKpiCostoCalidad.textContent = error.message;
    comprasKpiDdpCalidad.textContent = error.message;
    comprasKpisEstadosBody.innerHTML = `<tr><td colspan="4" class="empty">${escapar(error.message)}</td></tr>`;
    comprasKpisNota.textContent = "";
    setEstadoCompras(error.message, "error");
    throw error;
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


async function cargarComprasResumen() {
  try {
    const data = await api(`/api/v1/compras/resumen?empresa_id=${empresaId()}`);
    comprasResumenOcs.textContent = Number(data.ocs_identificadas || 0).toLocaleString("es-CO");
    comprasResumenMixtas.textContent = Number(data.ocs_mixtas || 0).toLocaleString("es-CO");
    comprasResumenPendientes.textContent = Number(data.lineas_estado_por_definir || 0).toLocaleString("es-CO");
  } catch (error) {
    comprasResumenOcs.textContent = "—";
    comprasResumenMixtas.textContent = "—";
    comprasResumenPendientes.textContent = "—";
    setEstadoCompras(error.message, "error");
    throw error;
  }
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


function renderCoberturaSegmento(titulo, segmento) {
  const campos = Object.entries(segmento?.campos || {});
  const conFaltantes = campos
    .filter(([, valor]) => Number(valor.faltantes || 0) > 0)
    .sort((a, b) => Number(b[1].faltantes || 0) - Number(a[1].faltantes || 0));

  return `
    <article class="catalog-card">
      <strong>${escapar(titulo)} · ${Number(segmento?.lineas || 0).toLocaleString("es-CO")} líneas</strong>
      ${conFaltantes.length
        ? conFaltantes.map(([, valor]) => `
            <div class="catalog-row">
              <span>${escapar(valor.nombre)}</span>
              <b>${Number(valor.faltantes || 0).toLocaleString("es-CO")} vacías · ${escapar(valor.cobertura_pct)}%</b>
            </div>
          `).join("")
        : '<p class="muted">Sin faltantes en los campos medidos.</p>'}
    </article>
  `;
}

async function cargarComprasCobertura() {
  comprasCoberturaContenido.innerHTML = '<p class="empty">Calculando cobertura…</p>';
  const params = new URLSearchParams({empresa_id: String(empresaId())});
  if (comprasFiltroPais.value) params.set("pais", comprasFiltroPais.value);

  try {
    const data = await api(`/api/v1/compras/cobertura?${params}`);
    comprasCoberturaContenido.innerHTML = [
      renderCoberturaSegmento("General", data.general),
      renderCoberturaSegmento("Población actual", data.poblacion_actual),
      renderCoberturaSegmento("Entregado", data.entregado),
    ].join("");
  } catch (error) {
    comprasCoberturaContenido.innerHTML = `<p class="empty">${escapar(error.message)}</p>`;
    setEstadoCompras(error.message, "error");
    throw error;
  }
}

async function cargarComprasLlegadas() {
  comprasLlegadasBody.innerHTML = '<tr><td colspan="7" class="empty">Consultando próximas ETA…</td></tr>';
  const params = new URLSearchParams({
    empresa_id: String(empresaId()),
    dias: "30",
  });
  if (comprasFiltroPais.value) params.set("pais", comprasFiltroPais.value);

  try {
    const data = await api(`/api/v1/compras/llegadas?${params}`);
    comprasLlegadasBody.innerHTML = data.items?.length
      ? data.items.map((item) => `
          <tr>
            <td>${escapar(item.pais)}</td>
            <td>${escapar(item.numero_oc)}</td>
            <td>${escapar(item.eta)}</td>
            <td>${Number(item.dias_hasta_eta || 0).toLocaleString("es-CO")}</td>
            <td>${escapar(item.proveedor)}</td>
            <td>${escapar(item.estado)}</td>
            <td>${escapar(item.valor_oci_ddp_origen)}</td>
          </tr>
        `).join("")
      : '<tr><td colspan="7" class="empty">No hay ETA interpretables en los próximos 30 días.</td></tr>';
  } catch (error) {
    comprasLlegadasBody.innerHTML = `<tr><td colspan="7" class="empty">${escapar(error.message)}</td></tr>`;
    setEstadoCompras(error.message, "error");
    throw error;
  }
}

async function cargarComprasTimeline(pais, oc) {
  comprasTimelineTitulo.textContent = `${pais} · ${oc}`;
  comprasTimelineLista.innerHTML = '<p class="empty">Consultando trazabilidad…</p>';
  const params = new URLSearchParams({
    empresa_id: String(empresaId()),
    pais,
    oc,
  });

  try {
    const data = await api(`/api/v1/compras/timeline?${params}`);
    comprasTimelineLista.innerHTML = data.items?.length
      ? data.items.map((item) => `
          <article class="quality-card">
            <div class="quality-card-title">
              <strong>Fila ${Number(item.fila_fuente || 0).toLocaleString("es-CO")} · ${escapar(item.sku || "Sin SKU")}</strong>
              <span class="tag">${escapar(item.estado)}</span>
            </div>
            <p>${escapar(item.proveedor || "Sin proveedor")} · ${escapar(item.modo_transporte || "Sin transporte")}</p>
            ${item.hitos?.length
              ? item.hitos.map((hito) => `
                  <div class="catalog-row">
                    <span>${escapar(hito.nombre)}</span>
                    <b>${escapar(hito.fecha_origen)}</b>
                  </div>
                `).join("")
              : '<p class="muted">Sin hitos fechados en los campos consumidos.</p>'}
          </article>
        `).join("")
      : '<p class="empty">No se encontraron líneas para esta OC.</p>';
  } catch (error) {
    comprasTimelineLista.innerHTML = `<p class="empty">${escapar(error.message)}</p>`;
    setEstadoCompras(error.message, "error");
    throw error;
  }
}

async function cargarComprasSnapshots() {
  comprasSnapshotsLista.innerHTML = '<p class="empty">Consultando capturas…</p>';
  try {
    const data = await api(`/api/v1/compras/snapshots?empresa_id=${empresaId()}&limit=10`);
    comprasSnapshotsLista.innerHTML = data.items?.length
      ? data.items.map((item) => `
          <article class="quality-card">
            <div class="quality-card-title">
              <strong>Snapshot #${Number(item.id).toLocaleString("es-CO")}</strong>
              <span class="tag">${item.esquema_valido ? "Esquema OK" : "Esquema degradado"}</span>
            </div>
            <p>${escapar(item.cargado_en)} · ${Number(item.lineas || 0).toLocaleString("es-CO")} líneas</p>
            <small>SHA-256 ${escapar(String(item.contenido_hash || "").slice(0, 16))}…</small>
          </article>
        `).join("")
      : '<p class="empty">Todavía no hay capturas persistidas.</p>';
  } catch (error) {
    comprasSnapshotsLista.innerHTML = `<p class="empty">${escapar(error.message)}</p>`;
    setEstadoCompras(error.message, "error");
    throw error;
  }
}

async function guardarComprasSnapshot() {
  setEstadoCompras("Guardando captura auditable…");
  try {
    const data = await api(
      `/api/v1/compras/snapshots?empresa_id=${empresaId()}`,
      {method: "POST"}
    );
    setEstadoCompras(
      data.creado ? "Captura auditable guardada" : "El contenido ya estaba capturado",
      "ok"
    );
    await cargarComprasSnapshots();
  } catch (error) {
    setEstadoCompras(error.message, "error");
    throw error;
  }
}

async function cargarComprasTodo(forzar = false) {
  try {
    const diagnostico = await cargarComprasDiagnostico(forzar);
    cargarComprasSnapshots().catch(() => {});
    if (diagnostico.estado !== "OK") {
      comprasOcsBody.innerHTML = '<tr><td colspan="9" class="empty">Lectura bloqueada hasta resolver el drift crítico de esquema.</td></tr>';
      comprasLineasBody.innerHTML = '<tr><td colspan="9" class="empty">Lectura bloqueada hasta resolver el drift crítico de esquema.</td></tr>';
      comprasLineasTitulo.textContent = "Esquema degradado";
      comprasAtencionLista.innerHTML = '<p class="empty">Puntos de atención no calculados con esquema degradado.</p>';
      comprasCalidadLista.innerHTML = '<p class="empty">Calidad no calculada con esquema degradado.</p>';
      comprasCatalogosContenido.innerHTML = '<p class="empty">Catálogos no calculados con esquema degradado.</p>';
      comprasCoberturaContenido.innerHTML = '<p class="empty">Cobertura no calculada con esquema degradado.</p>';
      comprasLlegadasBody.innerHTML = '<tr><td colspan="7" class="empty">Llegadas no calculadas con esquema degradado.</td></tr>';
      comprasGraficoEstados.innerHTML = '<p class="empty">Dashboard bloqueado por esquema degradado.</p>';
      comprasGraficoTransporte.innerHTML = '<p class="empty">Dashboard bloqueado por esquema degradado.</p>';
      return;
    }
    await Promise.all([
      cargarComprasDashboard(),
      cargarComprasResumen(),
      cargarComprasKpis(),
      cargarComprasOCs(),
      cargarComprasAtencion(),
      cargarComprasCalidad(),
      cargarComprasCatalogos(),
      cargarComprasCobertura(),
      cargarComprasLlegadas(),
      cargarComprasValidacion(forzar),
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

navInicio.addEventListener("click", () => mostrarModulo("inicio"));
navCartera.addEventListener("click", () => mostrarModulo("cartera"));
navCompras.addEventListener("click", () => mostrarModulo("compras"));
document.querySelector("#inicio-actualizar").addEventListener("click", cargarDashboardPrincipal);
document.querySelector("#compras-refrescar-fuente").addEventListener("click", () => cargarComprasTodo(true));
document.querySelector("#compras-cargar-kpis").addEventListener("click", cargarComprasKpis);
document.querySelector("#compras-cargar-atencion").addEventListener("click", cargarComprasAtencion);
document.querySelector("#compras-validar-tablero").addEventListener("click", () => cargarComprasValidacion(true));
comprasExportar.addEventListener("click", exportarCompras);
document.querySelector("#compras-cargar-ocs").addEventListener("click", cargarComprasOCs);
document.querySelector("#compras-cargar-calidad").addEventListener("click", cargarComprasCalidad);
document.querySelector("#compras-cargar-catalogos").addEventListener("click", cargarComprasCatalogos);
document.querySelector("#compras-cargar-cobertura").addEventListener("click", cargarComprasCobertura);
document.querySelector("#compras-cargar-llegadas").addEventListener("click", cargarComprasLlegadas);
document.querySelector("#compras-guardar-snapshot").addEventListener("click", guardarComprasSnapshot);
comprasFiltroPais.addEventListener("change", () => {
  comprasOcsOffset = 0;
  Promise.all([
    cargarComprasDashboard(),
    cargarComprasKpis(),
    cargarComprasOCs(),
    cargarComprasAtencion(),
    cargarComprasCobertura(),
    cargarComprasLlegadas(),
    cargarComprasValidacion(false),
  ]).catch(() => {});
});
comprasFiltroMixtas.addEventListener("change", () => {
  comprasOcsOffset = 0;
  cargarComprasOCs();
});
comprasOcsAnterior.addEventListener("click", () => {
  comprasOcsOffset = Math.max(0, comprasOcsOffset - COMPRAS_OCS_LIMIT);
  cargarComprasOCs();
});
comprasOcsSiguiente.addEventListener("click", () => {
  comprasOcsOffset += COMPRAS_OCS_LIMIT;
  cargarComprasOCs();
});
comprasFiltroQ.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    comprasOcsOffset = 0;
    cargarComprasOCs();
  }
});

cargarSesion();
