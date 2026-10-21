/* ASIATI · Dispersión descriptiva de PROYECCIONES por comercial.
 * No carga fuentes adicionales ni infiere ventas, pagos aplicados o saldos.
 * Suma los importes decimales como enteros BigInt escalados para evitar
 * errores de redondeo binario al agrupar dinero.
 */
(() => {
  "use strict";

  const root = document.getElementById("cartera-dispersion");
  if (!root) return;
  const grafica = document.getElementById("cartera-dispersion-grafica");
  const estado = document.getElementById("cartera-dispersion-estado");
  const origen = document.getElementById("cartera-dispersion-origen");
  const seleccion = document.getElementById("cartera-dispersion-seleccion");
  const tabla = document.getElementById("cartera-dispersion-tabla-body");
  const tablaTamano = document.getElementById("cartera-dispersion-tamano");
  const tablaAnterior = document.getElementById("cartera-dispersion-prev");
  const tablaSiguiente = document.getElementById("cartera-dispersion-next");
  const tablaPagina = document.getElementById("cartera-dispersion-pagina");
  const desde = document.getElementById("cartera-dispersion-desde");
  const hasta = document.getElementById("cartera-dispersion-hasta");
  const buscar = document.getElementById("cartera-dispersion-buscar");
  const limpiar = document.getElementById("cartera-dispersion-limpiar");
  const ns = "http://www.w3.org/2000/svg";
  const formatoEntero = new Intl.NumberFormat("es-CO", {maximumFractionDigits: 0});
  const formatoCompacto = new Intl.NumberFormat("es-CO", {
    notation: "compact", maximumFractionDigits: 1
  });
  let datos = [];
  let cargados = false;
  let empresaVisible = null;
  let comercialElegido = null;
  let puntosVisibles = [];
  let paginaTabla = 1;

  function texto(v) {
    return String(v ?? "").trim();
  }

  function normalizar(v) {
    return texto(v).normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("es-CO");
  }

  function decimal(valor) {
    const resultado = /^(\d+)(?:\.(\d+))?$/.exec(texto(valor));
    if (!resultado) return null;
    const fraccion = resultado[2] || "";
    return {
      entero: BigInt(resultado[1] + fraccion),
      escala: fraccion.length
    };
  }

  function sumar(a, b) {
    const escala = Math.max(a.escala, b.escala);
    const ajusteA = 10n ** BigInt(escala - a.escala);
    const ajusteB = 10n ** BigInt(escala - b.escala);
    return {entero: a.entero * ajusteA + b.entero * ajusteB, escala};
  }

  function decimalTexto(valor) {
    const bruto = valor.entero.toString().padStart(valor.escala + 1, "0");
    if (!valor.escala) return bruto;
    return bruto.slice(0, -valor.escala) + "." + bruto.slice(-valor.escala);
  }

  function usdExacto(valor) {
    const partes = decimalTexto(valor).split(".");
    const entero = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    const centavos = (partes[1] || "").replace(/0+$/, "");
    return "USD " + entero + "," + (centavos ? centavos.padEnd(2, "0") : "00");
  }

  function agruparFilas(filas, filtros = {}) {
    const desdeMes = filtros.desde || "";
    const hastaMes = filtros.hasta || "";
    const termino = normalizar(filtros.buscar || "");
    const grupos = new Map();
    let registrosExcluidos = 0;
    for (const fila of (Array.isArray(filas) ? filas : [])) {
      const mes = texto(fila.mes);
      if (!/^\d{4}-\d{2}$/.test(mes) ||
          (desdeMes && mes < desdeMes) || (hastaMes && mes > hastaMes)) continue;
      const nombre = texto(fila.comercial).toLocaleUpperCase("es-CO") || "SIN ASIGNAR";
      if (termino && !normalizar(nombre).includes(termino)) continue;
      const valor = decimal(fila.monto);
      if (valor === null || valor.entero <= 0n) {
        registrosExcluidos += 1;
        continue;
      }
      if (!grupos.has(nombre)) {
        grupos.set(nombre, {
          comercial: nombre,
          ocs: new Set(),
          monto: {entero: 0n, escala: 0},
          registros: 0,
          sinOc: 0
        });
      }
      const grupo = grupos.get(nombre);
      // La OC se identifica por el texto que aporta Sheets.
      // No se reconcilian documentos de distintas empresas ni se colapsan
      // referencias jurídicamente distintas.
      const oc = texto(fila.oc).toLocaleUpperCase("es-CO");
      if (oc) grupo.ocs.add(oc);
      else grupo.sinOc++;
      grupo.registros++;
      grupo.monto = sumar(grupo.monto, valor);
    }
    return {
      puntos: [...grupos.values()].map((g) => ({
        comercial: g.comercial,
        ocs: g.ocs.size,
        registros: g.registros,
        sinOc: g.sinOc,
        monto: decimalTexto(g.monto),
        montoExacto: usdExacto(g.monto),
        montoNumerico: Number(decimalTexto(g.monto))
      })).sort((a, b) => b.montoNumerico - a.montoNumerico ||
        a.comercial.localeCompare(b.comercial, "es")),
      registrosExcluidos
    };
  }

  function svgEl(tag, atributos = {}, textoNodo) {
    const node = document.createElementNS(ns, tag);
    for (const [clave, valor] of Object.entries(atributos)) {
      node.setAttribute(clave, String(valor));
    }
    if (textoNodo !== undefined) node.textContent = String(textoNodo);
    return node;
  }

  function monedaEje(valor) {
    return valor === 0 ? "0" : formatoCompacto.format(valor);
  }

  function pasoMonto(maximo) {
    if (maximo <= 0) return 1;
    const base = 10 ** Math.floor(Math.log10(maximo / 4));
    for (const multiplo of [1, 2, 5, 10]) {
      if (multiplo * base * 5 >= maximo) return multiplo * base;
    }
    return 10 * base;
  }

  function marcarSeleccion() {
    for (const node of grafica.querySelectorAll("[data-comercial]")) {
      const activo = node.getAttribute("data-comercial") === comercialElegido;
      node.setAttribute("aria-pressed", String(activo));
      node.classList.toggle("is-selected", activo);
    }
    for (const button of tabla.querySelectorAll("[data-seleccionar]")) {
      const activo = button.getAttribute("data-seleccionar") === comercialElegido;
      button.setAttribute("aria-pressed", String(activo));
      button.textContent = activo ? "Seleccionado" : "Seleccionar";
    }
    const p = puntosVisibles.find((item) => item.comercial === comercialElegido);
    if (!p) {
      seleccion.textContent = "Selecciona un punto o una fila para consultar su detalle.";
      return;
    }
    seleccion.textContent = p.comercial + " · " + formatoEntero.format(p.ocs) +
      " OC distintas · " + p.montoExacto + " en pagos esperados · " +
      formatoEntero.format(p.registros) + " registros" +
      (p.sinOc ? " · " + p.sinOc + " registros sin número de OC" : "") + ".";
  }

  function seleccionar(nombre) {
    comercialElegido = nombre;
    marcarSeleccion();
  }

  function renderTabla(puntos) {
    tabla.replaceChildren();
    const porPagina = Number(tablaTamano.value) || 20;
    const paginas = Math.max(1, Math.ceil(puntos.length / porPagina));
    paginaTabla = Math.min(Math.max(1, paginaTabla), paginas);
    tablaPagina.textContent = "Página " + paginaTabla + " de " + paginas;
    tablaAnterior.disabled = paginaTabla <= 1;
    tablaSiguiente.disabled = paginaTabla >= paginas;
    if (!puntos.length) {
      const fila = document.createElement("tr");
      const celda = document.createElement("td");
      celda.colSpan = 6;
      celda.className = "empty";
      celda.textContent = "No existen registros para los filtros seleccionados.";
      fila.appendChild(celda);
      tabla.appendChild(fila);
      return;
    }
    const visibles = puntos.slice((paginaTabla - 1) * porPagina, paginaTabla * porPagina);
    for (const punto of visibles) {
      const tr = document.createElement("tr");
      for (const valor of [
        punto.comercial,
        formatoEntero.format(punto.ocs),
        punto.montoExacto,
        formatoEntero.format(punto.registros),
        formatoEntero.format(punto.sinOc)
      ]) {
        const td = document.createElement("td");
        td.textContent = valor;
        tr.appendChild(td);
      }
      const td = document.createElement("td");
      const boton = document.createElement("button");
      boton.className = "secondary-button";
      boton.type = "button";
      boton.setAttribute("data-seleccionar", punto.comercial);
      boton.addEventListener("click", () => seleccionar(punto.comercial));
      td.appendChild(boton);
      tr.appendChild(td);
      tabla.appendChild(tr);
    }
  }

  function renderGrafica(puntos) {
    grafica.replaceChildren();
    if (!puntos.length) {
      const aviso = document.createElement("p");
      aviso.className = "finance-chart-empty";
      aviso.textContent = cargados
        ? "No hay puntos disponibles para los filtros seleccionados."
        : "No hay datos de PROYECCIONES disponibles para graficar.";
      grafica.appendChild(aviso);
      return;
    }
    // SVG escalable sin dependencias ni fuentes externas.
    const width = 960, height = 390, left = 98, right = 36, top = 25, bottom = 76;
    const plotWidth = width - left - right, plotHeight = height - top - bottom;
    const maxOcs = Math.max(1, ...puntos.map((p) => p.ocs));
    const xStep = Math.max(1, Math.ceil(maxOcs / 6));
    const xMax = Math.max(1, Math.ceil(maxOcs / xStep) * xStep);
    const maxMonto = Math.max(1, ...puntos.map((p) => p.montoNumerico));
    const yStep = pasoMonto(maxMonto);
    const yMax = 5 * yStep;
    const xCoord = (v) => left + v / xMax * plotWidth;
    const yCoord = (v) => top + plotHeight - v / yMax * plotHeight;
    const svg = svgEl("svg", {
      viewBox: "0 0 " + width + " " + height,
      role: "group",
      "aria-label": "Dispersión por comercial. Eje horizontal: OC distintas. Eje vertical: monto esperado en USD."
    });
    const desc = svgEl("desc", {}, "Cada círculo es un comercial. Usa Tab y Enter para seleccionar un punto. También hay una tabla con los mismos datos.");
    svg.appendChild(desc);
    for (let tick = 0; tick <= 5; tick++) {
      const valor = tick * yStep;
      const y = yCoord(valor);
      svg.appendChild(svgEl("line", {
        x1: left, x2: width - right, y1: y, y2: y, class: "cartera-scatter-grid"
      }));
      svg.appendChild(svgEl("text", {
        x: left - 12, y: y + 5, "text-anchor": "end", class: "cartera-scatter-tick"
      }, monedaEje(valor)));
    }
    for (let tick = 0; tick <= xMax; tick += xStep) {
      const x = xCoord(tick);
      svg.appendChild(svgEl("line", {
        x1: x, x2: x, y1: top, y2: top + plotHeight, class: "cartera-scatter-grid-vertical"
      }));
      svg.appendChild(svgEl("text", {
        x, y: top + plotHeight + 22, "text-anchor": "middle", class: "cartera-scatter-tick"
      }, tick));
    }
    svg.appendChild(svgEl("text", {
      x: left + plotWidth / 2, y: height - 20, "text-anchor": "middle",
      class: "cartera-scatter-axis"
    }, "Cantidad de OC distintas por comercial"));
    svg.appendChild(svgEl("text", {
      transform: "translate(22," + (top + plotHeight / 2) + ") rotate(-90)",
      "text-anchor": "middle", class: "cartera-scatter-axis"
    }, "Monto total de pagos esperados (USD)"));

    const coincidencias = new Map();
    for (const p of puntos) {
      if (!Number.isFinite(p.montoNumerico)) continue;
      const x = xCoord(p.ocs), y = yCoord(p.montoNumerico);
      const clave = x.toFixed(3) + ":" + y.toFixed(3);
      coincidencias.set(clave, (coincidencias.get(clave) || 0) + 1);
      const circle = svgEl("circle", {
        cx: x, cy: y, r: 8, tabindex: 0, role: "button",
        "data-comercial": p.comercial,
        "aria-label": p.comercial + ": " + p.ocs + " OC distintas y " + p.montoExacto +
          " esperados. Seleccionar para ver detalle.",
        class: "cartera-scatter-punto" + (p.comercial === "SIN ASIGNAR" ? " is-unassigned" : "")
      });
      circle.appendChild(svgEl("title", {}, p.comercial + " · " +
        p.ocs + " OC distintas · " + p.montoExacto));
      circle.addEventListener("click", () => seleccionar(p.comercial));
      circle.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          seleccionar(p.comercial);
        }
      });
      svg.appendChild(circle);
    }
    // Las coordenadas coincidentes no se alteran artificialmente.
    // La tabla permite seleccionar cada comercial incluso si comparte punto.
    for (const [clave, cantidad] of coincidencias) {
      if (cantidad <= 1) continue;
      const [x, y] = clave.split(":").map(Number);
      svg.appendChild(svgEl("text", {
        x: x + 12, y: y - 9, class: "cartera-scatter-colision"
      }, "×" + cantidad));
    }
    grafica.appendChild(svg);
  }

  function dibujar() {
    if (desde.value && hasta.value && desde.value > hasta.value) {
      puntosVisibles = [];
      estado.textContent = "El mes inicial no puede ser posterior al mes final.";
      renderGrafica([]);
      renderTabla([]);
      comercialElegido = null;
      marcarSeleccion();
      return;
    }
    if (!cargados) {
      puntosVisibles = [];
      renderGrafica([]);
      renderTabla([]);
      comercialElegido = null;
      marcarSeleccion();
      return;
    }
    const resumen = agruparFilas(datos, {
      desde: desde.value, hasta: hasta.value, buscar: buscar.value
    });
    puntosVisibles = resumen.puntos;
    const ocSinReferencia = resumen.puntos.reduce((n, p) => n + p.sinOc, 0);
    estado.textContent = formatoEntero.format(resumen.puntos.length) +
      " comerciales representados · " +
      formatoEntero.format(resumen.puntos.reduce((n, p) => n + p.registros, 0)) +
      " registros de proyección" +
      (ocSinReferencia ? " · " + formatoEntero.format(ocSinReferencia) +
       " sin número de OC" : "") +
      (resumen.registrosExcluidos ? " · " + resumen.registrosExcluidos +
       " montos no interpretables excluidos" : "") + ".";
    if (!puntosVisibles.some((p) => p.comercial === comercialElegido)) comercialElegido = null;
    renderGrafica(puntosVisibles);
    renderTabla(puntosVisibles);
    marcarSeleccion();
  }

  function setData(filas, contexto = {}) {
    // Quien entrega los registros es cargarProyeccion(), que utiliza la
    // API autenticada y descarta respuestas de otra empresa.
    datos = Array.isArray(filas) ? filas : [];
    paginaTabla = 1;
    empresaVisible = contexto.empresaId ?? null;
    cargados = true;
    comercialElegido = null;
    origen.textContent = "Fuente: Google Sheets · PROYECCIONES · empresa " +
      String(empresaVisible ?? "seleccionada") +
      " · fecha de pago esperada · monto USD · última consulta en esta sesión.";
    dibujar();
  }

  function limpiarDatos(mensaje = "Esperando fuente PROYECCIONES…") {
    datos = [];
    paginaTabla = 1;
    cargados = false;
    empresaVisible = null;
    comercialElegido = null;
    origen.textContent = "Fuente: Google Sheets · PROYECCIONES · sin resultados consultables.";
    estado.textContent = mensaje;
    dibujar();
  }

  for (const control of [desde, hasta, buscar]) {
    control.addEventListener(control === buscar ? "input" : "change", () => {
      paginaTabla = 1;
      dibujar();
    });
  }
  tablaTamano.addEventListener("change", () => {
    paginaTabla = 1;
    renderTabla(puntosVisibles);
    marcarSeleccion();
  });
  tablaAnterior.addEventListener("click", () => {
    paginaTabla = Math.max(1, paginaTabla - 1);
    renderTabla(puntosVisibles);
    marcarSeleccion();
  });
  tablaSiguiente.addEventListener("click", () => {
    paginaTabla++;
    renderTabla(puntosVisibles);
    marcarSeleccion();
  });
  limpiar.addEventListener("click", () => {
    desde.value = ""; hasta.value = ""; buscar.value = "";
    dibujar();
  });
  window.ASIATI_SCATTER = Object.freeze({setData, limpiarDatos, agruparFilas});
  limpiarDatos("La gráfica se activa con la fuente PROYECCIONES de Cartera.");
})();