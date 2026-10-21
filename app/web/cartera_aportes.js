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
  const detallePanel = porId("detalle");
  let modalAportesAbierto = false;
  const titulo = porId("detalle-titulo");
  const estado = porId("estado");
  const fuente = porId("fuente");
  const totalOcs = porId("ocs");
  const totalRegistros = porId("registros");
  const totalMonto = porId("monto");
  const meses = porId("meses");
  const orden = porId("orden");
  const multiples = porId("multiples");
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
  function porcentaje(parte, total) {
    return total > 0n ? Number(parte * 1000n / total) / 10 : 0;
  }
  function porcentajeTexto(parte, total) {
    return porcentaje(parte, total).toLocaleString("es-CO", {
      minimumFractionDigits: 1, maximumFractionDigits: 1
    }) + " %";
  }
  function mesLegible(valor) {
    const partes = texto(valor).split("-");
    const nombre = ["ene", "feb", "mar", "abr", "may", "jun",
      "jul", "ago", "sep", "oct", "nov", "dic"][Number(partes[1]) - 1];
    return nombre ? nombre + " " + partes[0] : valor;
  }
  function resumirMeses(items) {
    const resumen = new Map();
    for (const item of items) {
      for (const aporte of item.aportes) {
        const mes = aporte.fecha.slice(0, 7);
        if (!resumen.has(mes)) resumen.set(mes, {
          mes, monto: 0n, ocs: new Set(), registros: 0
        });
        const entrada = resumen.get(mes);
        entrada.monto += aporte.monto;
        entrada.ocs.add(item.oc);
        entrada.registros += aporte.filas;
      }
    }
    return [...resumen.values()].sort((a, b) => a.mes.localeCompare(b.mes))
      .map((m) => ({
        mes: m.mes, monto: m.monto, ocs: m.ocs.size, registros: m.registros
      }));
  }
  function ordenarOcs(items, criterio) {
    const resultado = [...items];
    if (criterio === "fecha_asc") {
      resultado.sort((a,b)=> a.aportes[0].fecha.localeCompare(b.aportes[0].fecha) ||
        a.oc.localeCompare(b.oc,"es"));
    } else if (criterio === "fecha_desc") {
      resultado.sort((a,b)=> b.aportes[b.aportes.length - 1].fecha.localeCompare(
        a.aportes[a.aportes.length - 1].fecha) || a.oc.localeCompare(b.oc,"es"));
    } else if (criterio === "aportes_desc") {
      resultado.sort((a,b)=> b.aportes.length - a.aportes.length ||
        a.oc.localeCompare(b.oc,"es"));
    }
    // monto_desc es el orden de origen de agrupar (BigInt exacto).
    return resultado;
  }
  function pintarMeses(items) {
    meses.replaceChildren();
    const resumen = resumirMeses(items);
    if (!resumen.length) {
      meses.appendChild(nodo("p", "empty", "No hay meses previstos con estos filtros."));
      return;
    }
    const maximo = resumen.reduce((m,r)=>r.monto > m ? r.monto : m, 1n);
    const totalMensual = resumen.reduce((acum,r)=>acum+r.monto,0n);
    const contenedor = nodo("div","cartera-aportes-meses-lista");
    for (const mes of resumen) {
      const fila = nodo("div","cartera-aportes-mes");
      const encabezado = nodo("div","cartera-aportes-mes-encabezado");
      encabezado.append(nodo("strong",null,mesLegible(mes.mes)),
        nodo("strong",null,moneda(mes.monto)));
      const texto = nodo("small",null,mes.ocs + " OC · " +
        mes.registros + (mes.registros === 1 ? " registro" : " registros") +
        " · " + porcentajeTexto(mes.monto,totalMensual) + " del total filtrado");
      const pista = nodo("span","cartera-aportes-mes-pista");
      const barra = nodo("span","cartera-aportes-mes-barra");
      barra.style.width = porcentaje(mes.monto,maximo) + "%";
      pista.appendChild(barra);
      fila.append(encabezado,pista,texto);
      contenedor.appendChild(fila);
    }
    meses.appendChild(contenedor);
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
      moneda(actual.monto) + " previstos"));
    const metadatos = nodo("div","cartera-aportes-detalle-metricas");
    const metrica = (titulo, valor) => {
      const ficha = nodo("div","cartera-aportes-detalle-metrica");
      ficha.append(nodo("span",null,titulo),nodo("strong",null,valor));
      return ficha;
    };
    metadatos.append(
      metrica("Primera fecha prevista",fechaLegible(actual.aportes[0].fecha)),
      metrica("Última fecha prevista",fechaLegible(
        actual.aportes[actual.aportes.length - 1].fecha)),
      metrica("Participación en el total filtrado",
        porcentajeTexto(actual.monto,listaActual.reduce((n,i)=>n+i.monto,0n))),
      metrica("Fechas / registros",actual.aportes.length + " / " + actual.filas)
    );
    detalle.appendChild(metadatos);

    detalle.appendChild(nodo("h5","cartera-aportes-detalle-subtitulo",
      "Cronograma previsto por fecha"));
    detalle.appendChild(nodo("p","table-footnote",
      "Cada barra representa la proporción de esa fecha sobre el importe esperado de esta OC."));

    const tabla = nodo("table","cartera-aportes-fechas");
    tabla.setAttribute("aria-label","Aportes proyectados por fecha para " + actual.oc);
    const head = nodo("thead"); const encabezado = nodo("tr");
    for (const col of ["Fecha prevista","Monto USD","Parte de OC","Acumulado"]) {
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
        "small","cartera-aportes-filas",aporte.filas + " registros de origen"
      ));
      const cPorcentaje = nodo("td","cartera-aportes-proporcion");
      cPorcentaje.appendChild(nodo("span",null,porcentajeTexto(aporte.monto,actual.monto)));
      const carril = nodo("span","cartera-aportes-fecha-pista");
      const barra = nodo("span","cartera-aportes-fecha-barra");
      barra.style.width = porcentaje(aporte.monto,actual.monto) + "%";
      carril.appendChild(barra);
      cPorcentaje.appendChild(carril);
      const cAcumulado = nodo("td",null,moneda(acumulado));
      tr.append(cFecha,cMonto,cPorcentaje,cAcumulado);
      body.appendChild(tr);
    }
    tabla.appendChild(body);
    const scroller = nodo("div","table-wrap");scroller.appendChild(tabla);
    detalle.appendChild(scroller);
    detalle.appendChild(nodo("p","table-footnote",
      "El acumulado suma previsiones, no abonos confirmados. Una fecha con varias filas puede corresponder a líneas de una misma operación."));
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
    const totalFiltrado = listaActual.reduce((acum,oc)=>acum+oc.monto,0n);
    for (const oc of visibles) {
      const boton = nodo("button","cartera-aportes-oc");
      boton.type = "button";
      boton.setAttribute("aria-pressed",String(oc.oc === seleccionado));
      if (oc.oc === seleccionado) boton.classList.add("is-selected");
      const linea = nodo("span","cartera-aportes-oc-titular");
      linea.append(nodo("strong",null,oc.oc),nodo("span",null,moneda(oc.monto)));
      const subtitulo = nodo("small",null,
        (oc.clientes.join(", ") || "Cliente no informado") + " · " +
        oc.filas + (oc.filas === 1 ? " registro de origen" : " registros de origen"));
      const cronograma = nodo("span","cartera-aportes-oc-cronograma");
      cronograma.append(nodo("span",null,
        "Primera fecha: " + fechaLegible(oc.aportes[0].fecha)),
        nodo("span",null,oc.aportes.length + (oc.aportes.length === 1 ?
          " fecha programada" : " fechas programadas")),
        nodo("span",null,porcentajeTexto(oc.monto,totalFiltrado) +
          " del importe filtrado"));
      const progreso = nodo("span","cartera-avance-sin-conciliar");
      progreso.append(
        nodo("span",null,"Pagado confirmado: sin verificar"),
        nodo("span",null,"Faltante real: no calculable")
      );
      const pista = nodo("span","cartera-avance-pista");
      pista.setAttribute("role","img");
      pista.setAttribute("aria-label","Avance de pago no disponible: esta GM aún no tiene recaudos confirmados y aplicados");
      pista.title="Sin conciliación por GM · no equivale a un avance del 0 %";
      boton.append(linea,subtitulo,cronograma,progreso,pista);
      boton.addEventListener("click",()=>seleccionar(oc.oc,true));
      lista.appendChild(boton);
    }
  }

  function seleccionar(oc, abrir = false) {
    seleccionado = oc;
    for(const b of lista.querySelectorAll(".cartera-aportes-oc")){
      const activo = b.querySelector("strong")?.textContent === oc;
      b.classList.toggle("is-selected",activo);
      b.setAttribute("aria-pressed",String(activo));
    }
    pintarDetalle(oc);
    if(abrir && oc && window.ASIATI_MODAL) {
      modalAportesAbierto = true;
      window.ASIATI_MODAL.open({
        title: "Seguimiento de aportes · " + oc,
        subtitle: "Importes programados; el avance real necesita recaudos verificados y aplicados a esta GM.",
        content: detallePanel,
        size: "wide",
        onClose: () => {
          modalAportesAbierto = false;
          detallePanel.hidden = true;
        }
      });
    }
  }

  function refrescar() {
    if (desde.value && hasta.value && desde.value > hasta.value) {
      listaActual = [];
      pintarMeses([]);
      estado.textContent = "La fecha inicial no puede ser posterior a la final.";
      totalOcs.textContent="—";totalRegistros.textContent="—";totalMonto.textContent="—";
      pintarLista();seleccionar("");return;
    }
    if (!cargado) {
      listaActual = [];
      pintarMeses([]);
      estado.textContent = "Esperando datos de PROYECCIONES.";
      totalOcs.textContent="—";totalRegistros.textContent="—";totalMonto.textContent="—";
      pintarLista();seleccionar("");return;
    }
    const {items,sinOC,omitidos} = agrupar(registros,{
      buscar:buscar.value,comercial:comercial.value,
      desde:desde.value,hasta:hasta.value
    });
    const elegibles = multiples.checked
      ? items.filter((item)=>item.aportes.length > 1) : items;
    listaActual = ordenarOcs(elegibles,orden.value);
    const total = listaActual.reduce((acum,item)=>acum+item.monto,0n);
    totalOcs.textContent=formatoConteo.format(listaActual.length);
    totalRegistros.textContent=formatoConteo.format(
      listaActual.reduce((a,b)=>a+b.filas,0));
    totalMonto.textContent=moneda(total).replace(/^USD /,"");
    pintarMeses(listaActual);
    estado.textContent=listaActual.length + " OC con importes esperados" +
      (multiples.checked ? " en varias fechas" : "") +
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
    if(modalAportesAbierto) window.ASIATI_MODAL?.close();
    registros=[];empresa=null;cargado=false;seleccionado="";pagina=1;
    comercial.replaceChildren(new Option("Todos",""));
    fuente.textContent="Fuente: PROYECCIONES · sin datos disponibles.";
    refrescar();
    estado.textContent=mensaje;
  }

  for (const input of [buscar,comercial,desde,hasta,orden,multiples]) {
    input.addEventListener(input===buscar?"input":"change",()=>{
      pagina=1;seleccionado="";refrescar();
    });
  }
  limpiar.addEventListener("click",()=>{
    buscar.value="";comercial.value="";desde.value="";hasta.value="";
    orden.value="monto_desc";multiples.checked=false;
    pagina=1;seleccionado="";refrescar();
  });
  anterior.addEventListener("click",()=>{pagina=Math.max(1,pagina-1);pintarLista();});
  siguiente.addEventListener("click",()=>{
    pagina=Math.min(Math.ceil(listaActual.length/LIMITE),pagina+1);
    pintarLista();
  });
  window.ASIATI_APORTES = Object.freeze({
    setData,limpiarDatos,agrupar,resumirMeses,ordenarOcs
  });
  limpiarDatos();
})();