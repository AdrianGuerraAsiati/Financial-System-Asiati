/* Cartera · aportes PROGRAMADOS por OC (Google Sheets PROYECCIONES).
 * No se atribuyen ingresos de Recaudos ni se infieren pagos efectivos.
 * Los totales monetarios se suman en centavos enteros (BigInt).
 */
(() => {
  "use strict";
  const raiz = document.getElementById("cartera-aportes");
  if (!raiz) return;
  const porId = (id) => document.getElementById("cartera-aportes-" + id);
  const lista = porId("lista");
  const detalle = porId("detalle-contenido");
  const titulo = porId("detalle-titulo");
  const estado = porId("estado");
  const fuente = porId("fuente");
  const totalOcs = porId("ocs");
  const totalRegistros = porId("registros");
  const totalMonto = porId("monto");
  const buscar = porId("buscar");
  const comercial = porId("comercial");
  const desde = porId("desde");
  const hasta = porId("hasta");
  const limpiar = porId("limpiar");
  const anterior = porId("anterior");
  const siguiente = porId("siguiente");
  const paginaTexto = porId("pagina");
  const formatoConteo = new Intl.NumberFormat("es-CO", {maximumFractionDigits: 0});
  const LIMITE = 8;
  let registros = [];
  let empresa = null;
  let listaActual = [];
  let seleccionado = "";
  let pagina = 1;
  let cargado = false;

  function texto(valor) { return String(valor ?? "").trim(); }
  function normal(valor) {
    return texto(valor).normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("es-CO");
  }
  function centavos(valor) {
    const m = /^(\d+)(?:\.(\d{1,2}))?$/.exec(texto(valor));
    if (!m) return null;
    return BigInt(m[1]) * 100n + BigInt((m[2] || "").padEnd(2, "0"));
  }
  function moneda(cantidad) {
    const positivo = cantidad < 0n ? -cantidad : cantidad;
    const euros = positivo / 100n;
    const centimos = String(positivo % 100n).padStart(2, "0");
    const grupo = euros.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return (cantidad < 0n ? "-" : "") + "USD " + grupo + "," + centimos;
  }
  function fechaLegible(valor) {
    const partes = texto(valor).slice(0, 10).split("-");
    return partes.length === 3 ? partes.reverse().join("/") : texto(valor);
  }
  function nodo(tag, css, contenido) {
    const elemento = document.createElement(tag);
    if (css) elemento.className = css;
    if (contenido !== undefined) elemento.textContent = contenido;
    return elemento;
  }

  function agrupar(filas, filtros = {}) {
    const porOC = new Map();
    let sinOC = 0, omitidos = 0;
    const termino = normal(filtros.buscar || "");
    for (const fila of Array.isArray(filas) ? filas : []) {
      const fecha = texto(fila.fecha).slice(0, 10);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha) ||
          (filtros.desde && fecha < filtros.desde) ||
          (filtros.hasta && fecha > filtros.hasta)) continue;
      const comerciante = texto(fila.comercial).toLocaleUpperCase("es-CO") || "SIN ASIGNAR";
      if (filtros.comercial && comerciante !== filtros.comercial) continue;
      const oc = texto(fila.oc).toLocaleUpperCase("es-CO");
      const cliente = texto(fila.cliente);
      if (termino && !normal(oc).includes(termino) && !normal(cliente).includes(termino)) {
        continue;
      }
      const monto = centavos(fila.monto);
      if (monto === null || monto <= 0n) {omitidos++;continue;}
      if (!oc) {sinOC++;continue;}
      if (!porOC.has(oc)) porOC.set(oc, {
        oc, clientes: new Set(), comerciales: new Set(),
        monto: 0n, filas: 0, porFecha: new Map()
      });
      const item = porOC.get(oc);
      if (cliente) item.clientes.add(cliente);
      item.comerciales.add(comerciante);
      item.monto += monto;
      item.filas++;
      if (!item.porFecha.has(fecha)) {
        item.porFecha.set(fecha, {fecha, monto: 0n, filas: 0});
      }
      const aporte = item.porFecha.get(fecha);
      aporte.monto += monto;
      aporte.filas++;
    }
    const items = [...porOC.values()].map((oc) => ({
      oc: oc.oc,
      clientes: [...oc.clientes].sort((a,b)=>a.localeCompare(b,"es")),
      comerciales: [...oc.comerciales].sort((a,b)=>a.localeCompare(b,"es")),
      monto: oc.monto,
      filas: oc.filas,
      aportes: [...oc.porFecha.values()].sort((a,b)=>a.fecha.localeCompare(b.fecha))
    })).sort((a,b) => a.monto === b.monto
      ? a.oc.localeCompare(b.oc, "es") : (a.monto > b.monto ? -1 : 1));
    return {items, sinOC, omitidos, total: items.reduce((sum,i)=>sum+i.monto,0n)};
  }

  function pintarDetalle(oc) {
    detalle.replaceChildren();
    const actual = listaActual.find((i) => i.oc === oc);
    if (!actual) {
      titulo.textContent = "Detalle de la OC";
      detalle.appendChild(nodo("p","empty","Selecciona una OC para ver sus aportes."));
      return;
    }
    titulo.textContent = actual.oc;
    detalle.appendChild(nodo("p","cartera-aportes-identidad",
      (actual.clientes.join(", ") || "Cliente no informado") + " · " +
      actual.comerciales.join(", ")));
    detalle.appendChild(nodo("strong","cartera-aportes-total-oc",
      moneda(actual.monto) + " proyectados"));
    detalle.appendChild(nodo("p","table-footnote",
      formatoConteo.format(actual.filas) + " registros agrupados en " +
      formatoConteo.format(actual.aportes.length) + " fechas previstas."));

    const tabla = nodo("table","cartera-aportes-fechas");
    tabla.setAttribute("aria-label","Aportes proyectados por fecha para " + actual.oc);
    const head = nodo("thead"); const encabezado = nodo("tr");
    for (const col of ["Fecha prevista","Monto USD","Acumulado"]) {
      const th = nodo("th",null,col); th.scope = "col"; encabezado.appendChild(th);
    }
    head.appendChild(encabezado); tabla.appendChild(head);
    const body = nodo("tbody");
    let acumulado = 0n;
    for (const aporte of actual.aportes) {
      acumulado += aporte.monto;
      const tr = nodo("tr");
      const cFecha = nodo("td",null,fechaLegible(aporte.fecha));
      const cMonto = nodo("td");
      cMonto.appendChild(nodo("strong",null,moneda(aporte.monto)));
      if (aporte.filas > 1) cMonto.appendChild(nodo(
        "small","cartera-aportes-filas",aporte.filas + " registros"
      ));
      const cAcumulado = nodo("td",null,moneda(acumulado));
      tr.append(cFecha,cMonto,cAcumulado);body.appendChild(tr);
    }
    tabla.appendChild(body);
    const scroller = nodo("div","table-wrap");scroller.appendChild(tabla);
    detalle.appendChild(scroller);
    detalle.appendChild(nodo("p","table-footnote",
      "Acumulado proyectado, no abonado real. Sin conciliación bancaria por OC."));
  }

  function pintarLista() {
    lista.replaceChildren();
    const paginas = Math.max(1,Math.ceil(listaActual.length / LIMITE));
    pagina = Math.min(Math.max(1,pagina),paginas);
    paginaTexto.textContent = "Página " + pagina + " de " + paginas +
      " · " + listaActual.length + " OC";
    anterior.disabled = pagina <= 1;
    siguiente.disabled = pagina >= paginas;
    const visibles = listaActual.slice((pagina-1)*LIMITE,pagina*LIMITE);
    if (!visibles.length) {
      lista.appendChild(nodo("p","empty",
        cargado ? "No se encontraron OC con proyecciones para estos filtros." :
        "No hay proyecciones consultadas."));
    }
    const mayor = listaActual.length ? listaActual[0].monto : 1n;
    for (const oc of visibles) {
      const boton = nodo("button","cartera-aportes-oc");
      boton.type = "button";
      boton.setAttribute("aria-pressed",String(oc.oc === seleccionado));
      if (oc.oc === seleccionado) boton.classList.add("is-selected");
      const linea = nodo("span","cartera-aportes-oc-titular");
      linea.append(nodo("strong",null,oc.oc),nodo("span",null,moneda(oc.monto)));
      const subtitulo = nodo("small",null,
        (oc.clientes.join(", ") || "Cliente no informado") + " · " +
        oc.aportes.length + (oc.aportes.length === 1 ? " fecha" : " fechas") +
        " · " + oc.filas + " registros");
      const pista = nodo("span","cartera-aportes-pista");
      const barra = nodo("span","cartera-aportes-barra");
      barra.style.width = String(Number(oc.monto * 10000n / (mayor || 1n)) / 100) + "%";
      const paleta = ["#2196ca","#60b1ea","#93c5fd","#bcdafa","#0f6b95"];
      for (const [idx,aporte] of oc.aportes.entries()) {
        const segmento = nodo("span","cartera-aportes-segmento");
        segmento.style.width = String(Number(aporte.monto * 10000n / oc.monto) / 100) + "%";
        segmento.style.background = paleta[idx % paleta.length];
        segmento.title = fechaLegible(aporte.fecha) + " · " + moneda(aporte.monto);
        barra.appendChild(segmento);
      }
      pista.appendChild(barra);
      boton.append(linea,subtitulo,pista);
      boton.addEventListener("click",()=>seleccionar(oc.oc));
      lista.appendChild(boton);
    }
  }

  function seleccionar(oc) {
    seleccionado = oc;
    for(const b of lista.querySelectorAll(".cartera-aportes-oc")){
      const activo = b.querySelector("strong")?.textContent === oc;
      b.classList.toggle("is-selected",activo);
      b.setAttribute("aria-pressed",String(activo));
    }
    pintarDetalle(oc);
  }

  function refrescar() {
    if (desde.value && hasta.value && desde.value > hasta.value) {
      listaActual = [];
      estado.textContent = "La fecha inicial no puede ser posterior a la final.";
      totalOcs.textContent="—";totalRegistros.textContent="—";totalMonto.textContent="—";
      pintarLista();seleccionar("");return;
    }
    if (!cargado) {
      listaActual = [];
      estado.textContent = "Esperando datos de PROYECCIONES.";
      totalOcs.textContent="—";totalRegistros.textContent="—";totalMonto.textContent="—";
      pintarLista();seleccionar("");return;
    }
    const {items,sinOC,omitidos,total} = agrupar(registros,{
      buscar:buscar.value,comercial:comercial.value,
      desde:desde.value,hasta:hasta.value
    });
    listaActual=items;
    totalOcs.textContent=formatoConteo.format(items.length);
    totalRegistros.textContent=formatoConteo.format(
      items.reduce((a,b)=>a+b.filas,0));
    totalMonto.textContent=moneda(total).replace(/^USD /,"");
    estado.textContent=items.length + " OC con pagos esperados" +
      (sinOC ? " · " + sinOC + " registros sin OC excluidos de la agrupación" : "") +
      (omitidos ? " · " + omitidos + " importes inválidos omitidos" : "") + ".";
    if (!items.some((oc)=>oc.oc===seleccionado)) seleccionado=items[0]?.oc || "";
    pintarLista();seleccionar(seleccionado);
  }

  function setData(rows, contexto = {}) {
    registros=Array.isArray(rows)?rows:[];
    empresa=contexto.empresaId ?? null;
    cargado=true;seleccionado="";pagina=1;
    const nombres=[...new Set(registros.map((r)=>
      texto(r.comercial).toLocaleUpperCase("es-CO") || "SIN ASIGNAR"
    ))].sort((a,b)=>a.localeCompare(b,"es"));
    const previo=comercial.value;
    comercial.replaceChildren(new Option("Todos",""));
    nombres.forEach((nombre)=>comercial.add(new Option(nombre,nombre)));
    if(nombres.includes(previo)) comercial.value=previo;
    fuente.textContent="Fuente: PROYECCIONES · empresa " + (empresa ?? "seleccionada") +
      " · fechas e importes esperados, sin pagos confirmados.";
    refrescar();
  }

  function limpiarDatos(mensaje="Esperando proyecciones…") {
    registros=[];empresa=null;cargado=false;seleccionado="";pagina=1;
    comercial.replaceChildren(new Option("Todos",""));
    fuente.textContent="Fuente: PROYECCIONES · sin datos disponibles.";
    refrescar();
    estado.textContent=mensaje;
  }

  for (const input of [buscar,comercial,desde,hasta]) {
    input.addEventListener(input===buscar?"input":"change",()=>{pagina=1;seleccionado="";refrescar();});
  }
  limpiar.addEventListener("click",()=>{
    buscar.value="";comercial.value="";desde.value="";hasta.value="";
    pagina=1;seleccionado="";refrescar();
  });
  anterior.addEventListener("click",()=>{pagina=Math.max(1,pagina-1);pintarLista();});
  siguiente.addEventListener("click",()=>{
    pagina=Math.min(Math.ceil(listaActual.length/LIMITE),pagina+1);
    pintarLista();
  });
  window.ASIATI_APORTES = Object.freeze({setData,limpiarDatos,agrupar});
  limpiarDatos();
})();