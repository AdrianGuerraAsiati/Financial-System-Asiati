/* Se carga únicamente en una pestaña iniciada por un enlace target=_blank.
 * El POST protegido sigue siendo mismo-origen y usa la cookie de sesión Strict.
 */
(() => {
  "use strict";
  const estado = document.getElementById("oauth-launch-estado");
  const query = new URLSearchParams(window.location.search);
  const empresaId = Number(query.get("empresa_id"));
  const mensaje = texto => { if (estado) estado.textContent = texto; };
  const canal = typeof BroadcastChannel === "function"
    ? new BroadcastChannel("asiati-google-sheets-oauth") : null;

  async function iniciar() {
    if (!Number.isSafeInteger(empresaId) || empresaId <= 0) {
      mensaje("Empresa inválida. Regresa a ASIATI e inicia de nuevo la conexión.");
      return;
    }
    try {
      const respuesta = await fetch(
        "/api/v1/integrations/google-sheets/conexion/iniciar?empresa_id=" + empresaId,
        {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json"}}
      );
      const datos = await respuesta.json().catch(() => ({}));
      if (!respuesta.ok) throw new Error(datos.detail || "No fue posible iniciar la autorización.");
      const target = new URL(datos.url);
      if (target.origin !== "https://accounts.google.com" ||
          target.pathname !== "/o/oauth2/v2/auth" ||
          target.searchParams.get("response_type") !== "code") {
        throw new Error("Google devolvió una dirección de autorización inesperada.");
      }
      mensaje("Redirigiendo a Google para autorizar el acceso de solo lectura…");
      // replace elimina del historial la URL de lanzamiento; no abre más ventanas.
      window.location.replace(target.href);
    } catch (error) {
      mensaje("No fue posible iniciar la conexión: " + error.message +
        " Vuelve a ASIATI, comprueba tu sesión e inténtalo nuevamente.");
      canal?.postMessage({tipo: "google_sheets_oauth", resultado: "error"});
    }
  }

  void iniciar();
})();
