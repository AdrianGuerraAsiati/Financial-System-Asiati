/* ASIATI 360 · Gráficas financieras v1
 * Lecturas únicamente de GET /dashboard/principal. Cero datos demo en producción.
 * Todos los valores mostrados son conteos observados por empresa y permiso.
 */
(() => {
  "use strict";
  const numero = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });

  function entero(valor) {
    return typeof valor === "number" && Number.isSafeInteger(valor) && valor >= 0
      ? valor : null;
  }

  function elemento(tag, clase, texto) {
    const node = document.createElement(tag);
    if (clase) node.className = clase;
    if (texto !== undefined) node.textContent = String(texto);
    return node;
  }

  function fechaSegura(iso) {
    if (!iso) return null;
    const d = new Date(iso);
    return Number.isFinite(d.getTime())
      ? d.toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" })
      : null;
  }

  function crearGrafica({ titulo, subtitulo, fuente, sello, filas, sinDatos, unidad = "registros" }) {
    const card = elemento("article", "finance-chart-card");
    const header = elemento("div", "finance-chart-header");
    const name = elemento("div");
    name.appendChild(elemento("h4", "", titulo));
    name.appendChild(elemento("p", "finance-chart-provenance", subtitulo));
    header.appendChild(name);
    header.appendChild(elemento("span", "finance-chart-meta", sello));
    card.appendChild(header);

    const observados = filas.filter((f) => f.valor !== null);
    if (!observados.length) {
      card.appendChild(elemento("p", "finance-chart-empty", sinDatos));
      card.appendChild(elemento("p", "finance-chart-source", fuente));
      return card;
    }

    const maximo = Math.max(1, ...observados.map((f) => f.valor));
    const foco = elemento("p", "finance-chart-focus", "Selecciona una barra para consultar el valor exacto.");
    foco.setAttribute("aria-live", "polite");
    const barras = elemento("div", "finance-chart-bars");
    const botones = [];
    for (const fila of filas) {
      if (fila.valor === null) continue;
      const row = elemento("div", "finance-bar-row");
      row.appendChild(elemento("span", "finance-bar-label", fila.etiqueta));
      const control = elemento("button", "finance-bar-track");
      control.type = "button";
      control.setAttribute("aria-label", fila.etiqueta + ": " + numero.format(fila.valor) + " " + unidad);
      control.setAttribute("aria-pressed", "false");
      control.title = fila.etiqueta + " · " + numero.format(fila.valor);
      const relleno = elemento("span", "finance-bar-fill");
      relleno.style.width = (fila.valor === 0 ? 0 : Math.max(1, fila.valor / maximo * 100)) + "%";
      control.appendChild(relleno);
      control.addEventListener("click", () => {
        botones.forEach((b) => b.setAttribute("aria-pressed", "false"));
        control.setAttribute("aria-pressed", "true");
        foco.textContent = fila.etiqueta + ": " + numero.format(fila.valor) + " " + unidad + ". " + (fila.nota || "");
      });
      botones.push(control);
      row.appendChild(control);
      row.appendChild(elemento("strong", "finance-bar-value", numero.format(fila.valor)));
      barras.appendChild(row);
    }
    card.appendChild(barras);
    card.appendChild(foco);

    const desplegable = elemento("details", "finance-chart-table");
    desplegable.appendChild(elemento("summary", "", "Ver tabla de datos"));
    const tabla = elemento("table");
    const head = elemento("thead");
    const headFila = elemento("tr");
    for (const encabezado of ["Categoría", "Cantidad"]) {
      headFila.appendChild(elemento("th", "", encabezado));
    }
    head.appendChild(headFila);
    tabla.appendChild(head);
    const body = elemento("tbody");
    for (const fila of filas) {
      const tr = elemento("tr");
      tr.appendChild(elemento("td", "", fila.etiqueta));
      tr.appendChild(elemento("td", "", fila.valor === null ? "Sin dato" : numero.format(fila.valor)));
      body.appendChild(tr);
    }
    tabla.appendChild(body);
    desplegable.appendChild(tabla);
    card.appendChild(desplegable);
    card.appendChild(elemento("p", "finance-chart-source", fuente));
    return card;
  }

  function renderDashboard(respuesta) {
    const contenedor = document.getElementById("inicio-analitica");
    if (!contenedor) return;
    contenedor.replaceChildren();
    const modulos = Array.isArray(respuesta?.modulos) ? respuesta.modulos : [];
    if (!modulos.length) {
      contenedor.appendChild(elemento("p", "finance-chart-empty", "No hay módulos disponibles para construir gráficas con los permisos actuales."));
      return;
    }
    const encabezado = elemento("div", "finance-section-heading");
    const texto = elemento("div");
    texto.appendChild(elemento("h3", "", "Lecturas financieras"));
    texto.appendChild(elemento("p", "", "Conteos por fuente y período. No se combinan importes ni se infieren saldos."));
    encabezado.appendChild(texto);
    contenedor.appendChild(encabezado);

    const grid = elemento("div", "finance-chart-grid");
    const cartera = modulos.find((m) => m.codigo === "cartera");
    if (cartera) {
      const s = cartera.resumen || {};
      const fecha = fechaSegura(cartera.actualizado_en);
      grid.appendChild(crearGrafica({
        titulo: "Registros por fuente · Cartera",
        subtitulo: "Recuento de filas capturadas en cada fuente; no corresponde a valores monetarios.",
        sello: "Conteos",
        fuente: "Origen: último snapshot de Cartera" + (fecha ? " · " + fecha : " · sin snapshot"),
        filas: [
          { etiqueta: "Operaciones", valor: entero(s.operaciones) },
          { etiqueta: "Registros mora", valor: entero(s.registros_mora) },
          { etiqueta: "Proyecciones", valor: entero(s.proyecciones) },
        ],
        sinDatos: "Sin snapshot de Cartera. No hay una serie verificable para mostrar.",
      }));
    }
    const conciliacion = modulos.find((m) => m.codigo === "conciliacion");
    if (conciliacion) {
      const s = conciliacion.resumen || {};
      const periodo = s.ultimo_periodo;
      grid.appendChild(crearGrafica({
        titulo: "Hallazgos · Conciliación",
        unidad: "hallazgos",
        subtitulo: "Críticos abiertos es un subconjunto de hallazgos abiertos; no sumar las barras.",
        sello: "Último período",
        fuente: "Origen: hallazgos de conciliación" +
          (periodo ? " · " + periodo.fecha_inicio + " a " + periodo.fecha_fin : " · sin período"),
        filas: periodo ? [
          { etiqueta: "Abiertos", valor: entero(s.hallazgos_abiertos) },
          { etiqueta: "Críticos abiertos", valor: entero(s.hallazgos_criticos_abiertos) },
        ] : [],
        sinDatos: "No existe un período de conciliación consultable para esta empresa.",
      }));
    }

    /* La disponibilidad compara solo módulos VISIBLES (no empresas ni permisos ocultos). */
    const visibles = modulos.filter((m) => typeof m.disponible === "boolean");
    grid.appendChild(crearGrafica({
      titulo: "Cobertura de información",
      unidad: "módulos",
      subtitulo: "Módulos permitidos para esta sesión, separados por disponibilidad de datos.",
      sello: "Acceso actual",
      fuente: "Origen: dashboard/principal · empresa seleccionada · consulta actual",
      filas: [
        { etiqueta: "Con datos", valor: visibles.filter((m) => m.disponible).length },
        { etiqueta: "Sin datos", valor: visibles.filter((m) => !m.disponible).length },
      ],
      sinDatos: "No hay módulos consultables.",
    }));
    contenedor.appendChild(grid);
  }

  window.ASIATI_FINANCIAL_CHARTS = Object.freeze({ renderDashboard });
})();