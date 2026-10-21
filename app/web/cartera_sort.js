/* Ordenamiento exacto de Operaciones Cartera: filtrar -> ordenar -> paginar. */
(() => {
  "use strict";
  const collator = new Intl.Collator("es-CO", {numeric:true,sensitivity:"base"});
  const CAMPOS = Object.freeze(["oc","cliente","estado","valor"]);
  function dineroCentavos(value) {
    if(value === null || value === undefined || value === "") return null;
    const raw=String(value).trim().replace(/^(?:USD|US\$|\$)\s*/i,"").replace(/\s/g,"");
    let v=raw;
    if(v.includes(",") && v.includes(".")) {
      v=v.lastIndexOf(",")>v.lastIndexOf(".")
        ? v.replace(/\./g,"").replace(",",".") : v.replace(/,/g,"");
    } else if(v.includes(",")) v=v.replace(",",".");
    if(!/^-?\d+(?:\.\d{1,2})?$/.test(v))return null;
    const neg=v[0]==="-";
    if(neg)v=v.slice(1);
    const [entero,decimales=""]=v.split(".");
    const cents=BigInt(entero)*100n+BigInt(decimales.padEnd(2,"0"));
    return neg?-cents:cents;
  }
  function ordenar(rows,campo="oc",direccion="asc") {
    if(!Array.isArray(rows))return [];
    if(!CAMPOS.includes(campo)) campo="oc";
    const factor=direccion==="desc"?-1:1;
    return rows.map((row,index)=>({row,index})).sort((a,b)=>{
      let comparison=0;
      if(campo==="valor") {
        const x=dineroCentavos(a.row.valor), y=dineroCentavos(b.row.valor);
        if(x===null||y===null){
          if(x===null&&y!==null)return 1; // Nulos al final, en ambos sentidos.
          if(y===null&&x!==null)return -1;
        } else comparison=x===y?0:(x>y?1:-1);
      } else {
        comparison=collator.compare(String(a.row[campo]??""),String(b.row[campo]??""));
      }
      return comparison?comparison*factor:
        collator.compare(String(a.row.oc??""),String(b.row.oc??""))||a.index-b.index;
    }).map(x=>x.row);
  }
  window.ASIATI_CARTERA_SORT=Object.freeze({ordenar,dineroCentavos,CAMPOS});
})();