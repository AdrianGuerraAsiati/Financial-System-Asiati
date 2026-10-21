/* ASIATI · Cartera: navegación por tareas en lugar de una página infinita.
 * Reorganiza los nodos originales sin clonarlos: mantiene los mismos IDs,
 * consultas, validaciones, formularios, permisos y listeners.
 */
(() => {
  "use strict";
  const root = document.getElementById("vista-cartera");
  if (!root) return;

  const gruposDefinidos = [
    {
      id: "operaciones", titulo: "Operaciones", descripcion:
        "Busca una OC, revisa sus líneas y conserva el contexto de la operación.",
      nodos: ["operaciones", "detalle-operacion"]
    },
    {
      id: "proyeccion", titulo: "Pagos previstos", descripcion:
        "Consulta aportes por OC, fechas esperadas, proyecciones y análisis comercial.",
      nodos: ["cartera-proyeccion", "cartera-aportes", "cartera-dispersion"]
    },
    {
      id: "mora", titulo: "Mora", descripcion:
        "Revisa los registros de la hoja MORA con sus filtros y paginación.",
      nodos: ["cartera-mora"]
    },
    {
      id: "documentos", titulo: "Documentos Drive", descripcion:
        "Consulta el inventario documental global y los soportes de una OC candidata.",
      nodos: ["cartera-drive-panel"], global: true
    },
    {
      id: "comprobantes", titulo: "Comprobantes", descripcion:
        "Radica un soporte con OC y archivo, o consulta los pendientes de auditoría.",
      nodos: ["comprobantes-pendientes"]
    },
    {
      id: "fuentes", titulo: "Fuentes y calidad", descripcion:
        "Estado de Sheets, observaciones de calidad e histórico de capturas.",
      nodos: ["cartera-fuente", "cartera-snapshots", "cartera-calidad"]
    }
  ];
  const tabs = new Map();
  const vistas = new Map();
  const subtabs = new Map();
  const subvistas = new Map();
  let activa = "operaciones";
  let subactiva = "aportes";
  let puedeVerGlobal = false;

  function crear(tag, clase, contenido) {
    const item = document.createElement(tag);
    if (clase) item.className = clase;
    if (contenido !== undefined) item.textContent = contenido;
    return item;
  }

  // Respetar la estructura existente de la bandeja y el formulario en un
  // mismo grid, sin crear un formulario nuevo ni alterar permisos del backend.
  const comprobantes = document.getElementById("comprobantes-pendientes");
  const gridComprobantes = comprobantes?.parentElement;
  if (gridComprobantes?.classList.contains("grid-two")) {
    gridComprobantes.id = "cartera-comprobantes-grid";
    gruposDefinidos.find((item) => item.id === "comprobantes").nodos = [
      "cartera-comprobantes-grid"
    ];
  }

  const intro = root.querySelector(".intro");
  const barra = crear("div", "cartera-vistas-barra");
  barra.id = "cartera-vistas-barra";
  const navegacion = crear("nav", "cartera-vistas-nav");
  navegacion.setAttribute("aria-label", "Secciones de Cartera");
  navegacion.setAttribute("role", "tablist");
  const contexto = crear("p", "cartera-vistas-contexto");
  contexto.id = "cartera-vistas-contexto";
  barra.append(navegacion, contexto);
  intro.insertAdjacentElement("afterend", barra);

  for (const grupo of gruposDefinidos) {
    const button = crear("button", "cartera-vistas-tab", grupo.titulo);
    button.id = "cartera-tab-" + grupo.id;
    button.type = "button";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", "cartera-vista-" + grupo.id);
    button.setAttribute("aria-selected", "false");
    button.tabIndex = -1;
    navegacion.appendChild(button);
    tabs.set(grupo.id, button);

    const panel = crear("div", "cartera-vistas-panel");
    panel.id = "cartera-vista-" + grupo.id;
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", button.id);
    panel.hidden = true;
    root.appendChild(panel);
    vistas.set(grupo.id, panel);

    if (grupo.id === "proyeccion") {
      const subnav = crear("div", "cartera-vistas-subnav");
      subnav.setAttribute("role", "tablist");
      subnav.setAttribute("aria-label", "Vistas de proyección");
      const subdef = [
        ["aportes", "Aportes por OC", "cartera-aportes"],
        ["tabla", "Registros de proyección", "cartera-proyeccion"],
        ["comerciales", "Comparación comercial", "cartera-dispersion"]
      ];
      panel.appendChild(subnav);
      for (const [key, texto, id] of subdef) {
        const subboton = crear("button", "cartera-vistas-subtab", texto);
        subboton.type = "button";
        subboton.id = "cartera-subtab-" + key;
        subboton.setAttribute("role", "tab");
        subboton.setAttribute("aria-selected", "false");
        subboton.setAttribute("aria-controls", "cartera-subvista-" + key);
        subboton.tabIndex = -1;
        const contenedor = crear("div", "cartera-vistas-subpanel");
        contenedor.id = "cartera-subvista-" + key;
        contenedor.setAttribute("role", "tabpanel");
        contenedor.setAttribute("aria-labelledby", subboton.id);
        contenedor.hidden = true;
        const elemento = document.getElementById(id);
        if (elemento) contenedor.appendChild(elemento);
        panel.appendChild(contenedor);
        subnav.appendChild(subboton);
        subtabs.set(key, subboton);
        subvistas.set(key, contenedor);
      }
    } else {
      for (const id of grupo.nodos) {
        const elemento = document.getElementById(id);
        if (elemento) panel.appendChild(elemento);
      }
    }
    button.addEventListener("click", () => activar(grupo.id, true));
  }

  function activarSubvista(key, manual = false) {
    if (!subtabs.has(key)) return;
    subactiva = key;
    for (const [id, boton] of subtabs) {
      const seleccionada = id === key;
      boton.setAttribute("aria-selected", String(seleccionada));
      boton.tabIndex = seleccionada ? 0 : -1;
      boton.classList.toggle("is-active", seleccionada);
      subvistas.get(id).hidden = !seleccionada;
    }
    if (manual) subtabs.get(key).focus();
  }

  function activar(id, manual = false) {
    if (!vistas.has(id)) return;
    if (id === "documentos" && !puedeVerGlobal) return;
    activa = id;
    for (const [key, tab] of tabs) {
      const seleccionado = id === key;
      tab.setAttribute("aria-selected", String(seleccionado));
      tab.tabIndex = seleccionado ? 0 : -1;
      tab.classList.toggle("is-active", seleccionado);
      vistas.get(key).hidden = !seleccionado;
    }
    const grupo = gruposDefinidos.find((item) => item.id === id);
    contexto.textContent = grupo.descripcion;
    if (id === "proyeccion") activarSubvista(subactiva);
    if (manual) {
      barra.scrollIntoView({block:"start",behavior:"auto"});
    }
  }

  function teclas(tab, listado, actual, event, activarSeleccion) {
    const validos = [...listado.entries()].filter(([, b]) => !b.hidden).map(([id]) => id);
    const indice = validos.indexOf(actual);
    if (indice < 0) return;
    let siguiente = indice;
    if (event.key === "ArrowRight") siguiente = (indice + 1) % validos.length;
    else if (event.key === "ArrowLeft") siguiente = (indice - 1 + validos.length) % validos.length;
    else if (event.key === "Home") siguiente = 0;
    else if (event.key === "End") siguiente = validos.length - 1;
    else return;
    event.preventDefault();
    activarSeleccion(validos[siguiente]);
    listado.get(validos[siguiente]).focus();
  }

  for (const [id, tab] of tabs) {
    tab.addEventListener("keydown", (event) =>
      teclas(tab, tabs, id, event, (key) => activar(key)));
  }
  for (const [id, tab] of subtabs) {
    tab.addEventListener("click", () => activarSubvista(id));
    tab.addEventListener("keydown", (event) =>
      teclas(tab, subtabs, id, event, (key) => activarSubvista(key)));
  }

  function navegarA(id) {
    const elemento = document.getElementById(id);
    if (!elemento) return false;
    if (["cartera-aportes", "cartera-dispersion", "cartera-proyeccion"].includes(id)) {
      activar("proyeccion");
      const tipo = id === "cartera-aportes" ? "aportes" :
        id === "cartera-dispersion" ? "comerciales" : "tabla";
      activarSubvista(tipo);
    } else {
      for (const grupo of gruposDefinidos) {
        if (grupo.nodos.includes(id)) {
          activar(grupo.id);
          break;
        }
      }
    }
    if (!elemento.closest("[hidden]")) {
      elemento.scrollIntoView({block:"start",behavior:"auto"});
      return true;
    }
    return false;
  }

  // Anclas existentes, como "Ver gráfica por comercial", también deben
  // funcionar aunque la subvista no esté visible en ese momento.
  root.addEventListener("click", (event) => {
    const enlace = event.target.closest('a[href^="#"]');
    if (!enlace) return;
    const id = decodeURIComponent(enlace.getAttribute("href").slice(1));
    if (["cartera-dispersion", "cartera-aportes", "cartera-proyeccion"].includes(id)) {
      event.preventDefault();
      navegarA(id);
    }
  });
  window.addEventListener("hashchange", () => {
    const id = decodeURIComponent(location.hash.replace(/^#/, ""));
    if (id && !root.hidden) navegarA(id);
  });

  function configurarAcceso(sesion) {
    puedeVerGlobal = sesion?.permisos?.["cartera.ver"] === "TODAS";
    const docs = tabs.get("documentos");
    docs.hidden = !puedeVerGlobal;
    if (!puedeVerGlobal && activa === "documentos") activar("operaciones");
  }

  activarSubvista("aportes");
  activar("operaciones");
  window.ASIATI_CARTERA_NAV = Object.freeze({
    activar,
    activarSubvista,
    configurarAcceso,
    navegarA
  });
})();