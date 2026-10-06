(function () {
  "use strict";

  // Listas de categorización (docs/nucleo/DIMENSIONES.md). Solo con dimensiones.gestionar.
  const $ = (selector) => document.querySelector(selector);
  const estado = $("#estado-parametros");
  const dimension = $("#parametros-dimension");
  const form = $("#parametros-form");
  const nuevo = $("#parametros-nuevo");
  const body = $("#parametros-body");

  let valores = [];

  function escapar(valor) {
    const div = document.createElement("div");
    div.textContent = valor === null || valor === undefined ? "" : String(valor);
    return div.innerHTML;
  }

  function puedeGestionar() {
    const permisos = (window.ASIATI_SESION && window.ASIATI_SESION.permisos) || {};
    return Boolean(permisos["dimensiones.gestionar"]);
  }

  function setEstado(texto, clase) {
    estado.textContent = texto;
    estado.className = ("status " + (clase || "")).trim();
  }

  async function api(url, options) {
    const response = await fetch(url, options || {});
    let datos = null;
    try {
      datos = await response.json();
    } catch (_) {}
    if (!response.ok) {
      if (response.status === 401 && typeof window.mostrarLogin === "function") window.mostrarLogin();
      throw new Error((datos && datos.detail) || ("Error HTTP " + response.status));
    }
    return datos;
  }

  function json(method, payload) {
    return {method: method, headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)};
  }

  function render() {
    if (!valores.length) {
      body.innerHTML = '<tr><td colspan="3" class="empty">La lista está vacía. Agrega el primer valor.</td></tr>';
      return;
    }
    body.innerHTML = valores.map((v) =>
      '<tr data-id="' + escapar(v.id) + '">' +
        '<td class="parametros-valor">' + escapar(v.valor) + "</td>" +
        '<td><span class="wallet-pill">' + (v.activo ? "ACTIVO" : "DESACTIVADO") + "</span></td>" +
        '<td class="parametros-acciones">' +
          '<button type="button" class="secondary-button" data-accion="renombrar">Renombrar</button>' +
          '<button type="button" class="secondary-button" data-accion="' + (v.activo ? "desactivar" : "activar") + '">' +
            (v.activo ? "Desactivar" : "Activar") + "</button>" +
        "</td>" +
      "</tr>"
    ).join("");
  }

  async function cargar() {
    if (!puedeGestionar()) return;
    setEstado("Cargando…", "");
    try {
      valores = await api("/api/v1/dimensiones?dimension=" + encodeURIComponent(dimension.value) + "&incluir_inactivos=true");
      render();
      setEstado("Listo", "");
    } catch (error) {
      setEstado(error.message, "error");
    }
  }

  async function actualizar(id, cambios, mensaje) {
    try {
      await api("/api/v1/dimensiones/" + id, json("PATCH", cambios));
      await cargar();
      setEstado(mensaje, "success");
    } catch (error) {
      setEstado(error.message, "error");
    }
  }

  function editarNombre(fila) {
    const celda = fila.querySelector(".parametros-valor");
    const actual = celda.textContent;
    celda.innerHTML = '<input maxlength="120" value="' + escapar(actual) + '"> ' +
      '<button type="button" data-accion="guardar-nombre">Guardar</button>';
    celda.querySelector("input").focus();
  }

  body.addEventListener("click", (event) => {
    const boton = event.target.closest("button[data-accion]");
    if (!boton) return;
    const fila = boton.closest("tr");
    const id = fila.dataset.id;
    const accion = boton.dataset.accion;
    if (accion === "renombrar") editarNombre(fila);
    if (accion === "guardar-nombre") {
      actualizar(id, {valor: fila.querySelector(".parametros-valor input").value}, "Valor renombrado.");
    }
    if (accion === "desactivar") actualizar(id, {activo: false}, "Valor desactivado: ya no se puede elegir, pero lo categorizado lo conserva.");
    if (accion === "activar") actualizar(id, {activo: true}, "Valor activado.");
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/v1/dimensiones", json("POST", {dimension: dimension.value, valor: nuevo.value}));
      nuevo.value = "";
      await cargar();
      setEstado("Valor agregado.", "success");
    } catch (error) {
      setEstado(error.message, "error");
    }
  });

  dimension.addEventListener("change", cargar);
  window.cargarParametrosTodo = cargar;
})();
