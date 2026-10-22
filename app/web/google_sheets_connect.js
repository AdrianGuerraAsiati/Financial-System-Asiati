/* Conexión Google Sheets: OAuth gestionado en backend, para superadministración y soporte TI. */
(() => {
  "use strict";
  const boton = document.getElementById("cartera-google-conectar");
  const probar = document.getElementById("cartera-google-probar");
  const estado = document.getElementById("cartera-google-estado");
  const empresa = document.getElementById("empresa-id");
  const nav = document.getElementById("nav-cartera");
  if (!boton || !probar || !estado || !empresa || !nav) return;

  let generacion = 0;
  const CANAL = "asiati-google-sheets-oauth";
  const canal = typeof BroadcastChannel === "function" ? new BroadcastChannel(CANAL) : null;
  const idEmpresa = () => Number(empresa.value);
  const admin = () => Boolean(window.ASIATI_SESION?.permisos?.["google_sheets.conectar"]);
  const mensaje = texto => { estado.textContent = texto; };

  async function json(url, opciones = {}) {
    const res = await fetch(url, {credentials: "same-origin", ...opciones});
    let datos = {};
    try { datos = await res.json(); } catch (_) {}
    if (!res.ok) throw new Error(datos.detail || "No fue posible conectar Google Sheets.");
    return datos;
  }

  async function refrescar() {
    const token = ++generacion;
    const id = idEmpresa();
    if (!id || !window.ASIATI_SESION?.permisos?.["cartera.ver"]) {
      boton.hidden = true; probar.hidden = true; mensaje(""); return;
    }
    boton.hidden = !admin();
    boton.setAttribute("aria-disabled", "true");
    boton.tabIndex = -1;
    boton.href = "/static/google_sheets_oauth_launch.html?empresa_id=" + encodeURIComponent(id);
    probar.hidden = true;
    mensaje("Consultando conexión Google Sheets…");
    try {
      const datos = await json("/api/v1/integrations/google-sheets/conexion?empresa_id=" + id);
      if (token !== generacion || id !== idEmpresa()) return;
      boton.setAttribute("aria-disabled", String(!datos.oauth_configurado));
      boton.tabIndex = datos.oauth_configurado ? 0 : -1;
      boton.textContent = datos.conectada ? "Reconectar Google Sheets" : "Conectar Google Sheets";
      probar.hidden = !admin() || !datos.conectada;
      if (!datos.oauth_configurado) {
        mensaje("TI debe activar una vez la aplicación OAuth de Google. Después podrás reconectar sin terminal.");
      } else if (datos.conectada) {
        mensaje("Cuenta de Google autorizada (solo lectura). Comprueba el acceso vigente con «Probar conexión».");
      } else {
        mensaje("Google Sheets aún no está autorizado. Un administrador puede conectarlo desde aquí.");
      }
    } catch (e) {
      if (token !== generacion || id !== idEmpresa()) return;
      boton.setAttribute("aria-disabled", "true"); boton.tabIndex = -1; mensaje(e.message);
    }
  }

  // Enlace nativo target=_blank: evita bloqueos de ventanas emergentes tras un fetch
  // asíncrono. La nueva pestaña inicia OAuth con POST bajo la misma sesión Strict.
  boton.addEventListener("click", (event) => {
    if (!admin() || boton.getAttribute("aria-disabled") === "true") {
      event.preventDefault();
      return;
    }
    mensaje("Abriendo autorización Google en otra pestaña. ASIATI seguirá disponible aquí.");
  });

  probar.addEventListener("click", async () => {
    if (!admin()) return;
    const id = idEmpresa();
    probar.disabled = true;
    mensaje("Verificando el acceso a la hoja configurada…");
    try {
      const r = await json("/api/v1/integrations/google-sheets/conexion/probar?empresa_id=" + id);
      if (id === idEmpresa() && r.ok)
        mensaje("Google Sheets verificado. Ya puedes actualizar Cartera.");
    } catch (e) {
      if (id === idEmpresa())
        mensaje(e.message + " Utiliza «Reconectar Google Sheets».");
    } finally { probar.disabled = false; }
  });

  if (canal) {
    canal.onmessage = (event) => {
      if (event.data?.tipo !== "google_sheets_oauth" || !admin()) return;
      if (event.data.resultado === "conectada") {
        const id = idEmpresa();
        mensaje("Google Sheets autorizado. Actualizando el estado de Cartera…");
        void refrescar().then(() => {
          if (id === idEmpresa()) document.getElementById("cartera-refrescar-fuente")?.click();
        });
      } else {
        mensaje("Google devolvió un resultado de autorización. Revisa la pestaña de conexión.");
        void refrescar();
      }
    };
  }

  nav.addEventListener("click", () => { void refrescar(); });
  empresa.addEventListener("change", () => { void refrescar(); });
  const resultado = new URLSearchParams(window.location.search).get("google_sheets");
  if (resultado) {
    const avisos = {
      conectada: "Cuenta de Google conectada. Abre Cartera para probar el acceso.",
      denegada: "Se canceló la autorización a Google Sheets.",
      error: "Google no completó la autorización. Inténtalo nuevamente desde Cartera.",
      permisos: "Google no concedió permiso de lectura.",
      sin_refresh: "Google no entregó una credencial renovable. Intenta reconectar.",
      sin_hoja: "TI debe asociar la hoja de Cartera a la empresa.",
      sin_acceso: "La cuenta Google seleccionada no puede abrir la hoja configurada."
    };
    if (canal) canal.postMessage({tipo: "google_sheets_oauth", resultado});
    const global = document.getElementById("estado-global");
    if (global) global.textContent = avisos[resultado] || "Respuesta de Google recibida.";
    window.history.replaceState({}, "", window.location.pathname + window.location.hash);
  }
})();
