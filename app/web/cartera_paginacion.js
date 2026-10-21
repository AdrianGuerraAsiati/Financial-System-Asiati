/* Controles compartidos de consulta para los listados de Cartera.
   El cliente pagina datos ya autorizados; el historial consulta páginas en API.
   No calcula indicadores ni modifica fuentes o permisos. */
(() => {
  "use strict";
  const numero = (n) => Number(n).toLocaleString("es-CO");
  const normalizar = (v) => String(v ?? "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es-CO");

  function crear({id, destino, textoVacio, columnas = 0, campos, plantilla,
                  estado, remoto, consulta, contexto, tamaño = 20}) {
    const target = document.querySelector(destino);
    if (!target) throw new Error("Contenedor de Cartera ausente: " + destino);
    const anteriorAl = target.closest(".table-wrap") || target;
    const controls = document.createElement("div");
    controls.className = "cartera-list-toolbar";
    controls.dataset.listado = id;
    const labelBusqueda = document.createElement("label");
    labelBusqueda.textContent = "Buscar";
    const busqueda = document.createElement("input");
    busqueda.type = "search";
    busqueda.id = "cartera-" + id + "-buscar";
    busqueda.placeholder = "Buscar en " + id;
    busqueda.autocomplete = "off";
    labelBusqueda.htmlFor = busqueda.id;
    labelBusqueda.appendChild(busqueda);
    controls.appendChild(labelBusqueda);

    let selectorEstado = null;
    if (estado && !remoto) {
      const labelEstado = document.createElement("label");
      labelEstado.textContent = "Estado";
      selectorEstado = document.createElement("select");
      selectorEstado.id = "cartera-" + id + "-estado";
      labelEstado.htmlFor = selectorEstado.id;
      selectorEstado.add(new Option("Todos", ""));
      labelEstado.appendChild(selectorEstado);
      controls.appendChild(labelEstado);
    }

    const labelTamano = document.createElement("label");
    labelTamano.textContent = "Filas por página";
    const tamano = document.createElement("select");
    tamano.id = "cartera-" + id + "-por-pagina";
    labelTamano.htmlFor = tamano.id;
    for (const cantidad of [10, 20, 50, 100]) {
      tamano.add(new Option(String(cantidad), String(cantidad), false, cantidad === tamaño));
    }
    labelTamano.appendChild(tamano);
    controls.appendChild(labelTamano);
    anteriorAl.parentNode.insertBefore(controls, anteriorAl);

    const footer = document.createElement("div");
    footer.className = "cartera-list-footer";
    const cuenta = document.createElement("p");
    cuenta.id = "cartera-" + id + "-total";
    cuenta.className = "table-footnote";
    cuenta.setAttribute("role", "status");
    cuenta.setAttribute("aria-live", "polite");
    const nav = document.createElement("div");
    nav.className = "pagination";
    nav.setAttribute("aria-label", "Paginación de " + id);
    const antes = document.createElement("button");
    antes.type = "button"; antes.className = "secondary-button";
    antes.textContent = "Anterior"; antes.disabled = true;
    antes.id = "cartera-" + id + "-anterior";
    const paginaTexto = document.createElement("span");
    paginaTexto.className = "table-footnote"; paginaTexto.setAttribute("aria-live", "polite");
    paginaTexto.id = "cartera-" + id + "-pagina";
    const despues = document.createElement("button");
    despues.type = "button"; despues.className = "secondary-button";
    despues.textContent = "Siguiente"; despues.disabled = true;
    despues.id = "cartera-" + id + "-siguiente";
    nav.append(antes, paginaTexto, despues);
    footer.append(cuenta, nav);
    anteriorAl.parentNode.insertBefore(footer, anteriorAl.nextSibling);

    let rows = [];
    let pagina = 1;
    let totalServidor = 0;
    let iniciado = false;
    let peticion = 0;
    let temporizador = null;

    const limite = () => Number(tamano.value) || tamaño;
    function mensaje(texto) {
      const par = document.createElement(columnas ? "tr" : "p");
      const nodo = columnas ? document.createElement("td") : par;
      nodo.className = "empty";
      nodo.textContent = texto;
      if (columnas) {
        nodo.colSpan = columnas;
        par.appendChild(nodo);
      }
      target.replaceChildren(par);
    }
    function pintar(filas, total, filtrados) {
      if (filas.length) {
        // Todas las plantillas provienen del código confiable app.js,
        // que escapa cada valor obtenido de la API.
        target.innerHTML = filas.map(plantilla).join("");
      } else {
        mensaje(total === 0 && !busqueda.value.trim() ? textoVacio : "No se encontraron registros con estos filtros.");
      }
      const paginas = Math.max(1, Math.ceil(total / limite()));
      pagina = Math.min(pagina, paginas);
      antes.disabled = pagina <= 1;
      despues.disabled = pagina >= paginas;
      paginaTexto.textContent = "Página " + pagina + " de " + paginas;
      cuenta.textContent = filtrados
        ? numero(total) + " de " + numero(rows.length) + " registros"
        : numero(total) + " registros";
    }
    function refrescarEstados() {
      if (!selectorEstado) return;
      const anterior = selectorEstado.value;
      const valores = [...new Set(rows.map(estado).filter(Boolean).map(String))]
        .sort((a, b) => a.localeCompare(b, "es"));
      selectorEstado.replaceChildren(new Option("Todos", ""));
      valores.forEach((v) => selectorEstado.add(new Option(v, v)));
      if (valores.includes(anterior)) selectorEstado.value = anterior;
    }
    function renderLocal() {
      if (!iniciado) return;
      const q = normalizar(busqueda.value.trim());
      const filtroEstado = selectorEstado?.value ?? "";
      const filtradas = rows.filter((row) => {
        if (filtroEstado && String(estado(row) ?? "") !== filtroEstado) return false;
        return !q || (campos(row) || []).some((v) => normalizar(v).includes(q));
      });
      const paginas = Math.max(1, Math.ceil(filtradas.length / limite()));
      pagina = Math.min(Math.max(1, pagina), paginas);
      const desde = (pagina - 1) * limite();
      pintar(filtradas.slice(desde, desde + limite()), filtradas.length,
        Boolean(q || filtroEstado));
    }

    async function cargarRemoto() {
      if (!consulta) return;
      const version = ++peticion;
      const scope = contexto?.();
      iniciado = true;
      mensaje("Consultando…");
      antes.disabled = true; despues.disabled = true;
      cuenta.textContent = "Consultando registros…";
      try {
        const respuesta = await consulta({
          limit: limite(), offset: (pagina - 1) * limite(), buscar: busqueda.value.trim()
        });
        if (version !== peticion || (contexto && scope !== contexto())) return;
        rows = Array.isArray(respuesta.items) ? respuesta.items : [];
        totalServidor = Number(respuesta.total) || 0;
        const paginas = Math.max(1, Math.ceil(totalServidor / limite()));
        if (pagina > paginas) {
          pagina = paginas;
          return cargarRemoto();
        }
        pintar(rows, totalServidor, false);
      } catch (error) {
        if (version !== peticion || (contexto && scope !== contexto())) return;
        mensaje(error.message || "No se pudo consultar el listado.");
        cuenta.textContent = "Error al consultar";
        paginaTexto.textContent = "Página 1 de 1";
        antes.disabled = true; despues.disabled = true;
      }
    }
    function actualizar(nuevasFilas) {
      ++peticion;
      rows = Array.isArray(nuevasFilas) ? nuevasFilas : [];
      pagina = 1;
      iniciado = true;
      refrescarEstados();
      renderLocal();
    }
    function fallo(texto) {
      ++peticion;
      rows = [];
      pagina = 1;
      iniciado = false;
      mensaje(texto);
      cuenta.textContent = "Sin registros disponibles";
      paginaTexto.textContent = "Página 1 de 1";
      antes.disabled = true; despues.disabled = true;
      refrescarEstados();
    }
    function activarConsulta(reset) {
      if (reset) pagina = 1;
      if (remoto) return cargarRemoto();
      renderLocal();
    }
    busqueda.addEventListener("input", () => {
      if (temporizador) clearTimeout(temporizador);
      temporizador = setTimeout(() => activarConsulta(true), remoto ? 300 : 100);
    });
    tamano.addEventListener("change", () => activarConsulta(true));
    selectorEstado?.addEventListener("change", () => activarConsulta(true));
    antes.addEventListener("click", () => {
      pagina = Math.max(1, pagina - 1);
      activarConsulta(false);
    });
    despues.addEventListener("click", () => {
      const total = remoto ? totalServidor : rows.length;
      if (pagina * limite() < total || (!remoto && iniciado)) {
        pagina += 1;
        activarConsulta(false);
      }
    });
    return Object.freeze({
      actualizar, fallo,
      cargar: () => activarConsulta(false),
      primera: () => activarConsulta(true)
    });
  }
  window.CarteraPaginacion = Object.freeze({crear});
})();