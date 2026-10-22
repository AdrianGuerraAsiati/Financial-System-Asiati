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
    probar.hidden = true;
    mensaje("Consultando conexión Google Sheets…");
    try {
      const datos = await json("/api/v1/integrations/google-sheets/conexion?empresa_id=" + id);
      if (token !== generacion || id !== idEmpresa()) return;
      boton.disabled = !datos.oauth_configurado;
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
      boton.disabled = true; mensaje(e.message);
    }
  }

  boton.addEventListener("click", async () => {
    if (!admin()) return;
    const id = idEmpresa();
    boton.disabled = true;
    mensaje("Preparando autorización segura de Google…");
    try {
      const r = await json(
        "/api/v1/integrations/google-sheets/conexion/iniciar?empresa_id=" + id,
        {method: "POST", headers: {"Content-Type": "application/json"}}
      );
      if (id !== idEmpresa()) return;
      if (!r.url?.startsWith("https://accounts.google.com/o/oauth2/v2/auth?"))
        throw new Error("Google devolvió una URL inesperada.");
      window.location.assign(r.url);
    } catch (e) {
      mensaje(e.message); boton.disabled = false;
    }
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
    const global = document.getElementById("estado-global");
    if (global) global.textContent = avisos[resultado] || "Respuesta de Google recibida.";
    window.history.replaceState({}, "", window.location.pathname + window.location.hash);
  }
})();
