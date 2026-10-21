/* Modal único reutilizable: detalle, soportes, proyecciones y comprobantes. */
(() => {
  "use strict";
  let node=null, heading=null, subtitle=null, body=null, returnFocus=null, callback=null;
  let epoch=0;
  function ensure() {
    if(node)return;
    node=document.createElement("dialog");
    node.id="asiati-modal";
    node.className="asiati-modal";
    node.setAttribute("aria-labelledby","asiati-modal-title");
    const container=document.createElement("div");
    container.className="asiati-modal-layout";
    const top=document.createElement("header");
    top.className="asiati-modal-header";
    const names=document.createElement("div");
    heading=document.createElement("h2");heading.id="asiati-modal-title";
    subtitle=document.createElement("p");subtitle.id="asiati-modal-subtitle";
    names.append(heading,subtitle);
    const close=document.createElement("button");
    close.type="button";close.className="asiati-modal-close";
    close.textContent="Cerrar ×";close.setAttribute("aria-label","Cerrar detalle");
    close.addEventListener("click",()=>node.close());
    top.append(names,close);
    body=document.createElement("div");body.id="asiati-modal-body";
    body.className="asiati-modal-body";
    container.append(top,body);node.appendChild(container);
    document.body.appendChild(node);
    // No cerrar si el clic sucede dentro del área de contenido.
    node.addEventListener("click",event=>{
      if(event.target===node)node.close();
    });
    node.addEventListener("close",()=>{
      ++epoch;
      const done=callback;callback=null;
      body.replaceChildren();
      node.classList.remove("asiati-modal-wide");
      document.body.classList.remove("asiati-modal-open");
      if(typeof done==="function")done();
      if(returnFocus?.isConnected && typeof returnFocus.focus==="function"){
        returnFocus.focus({preventScroll:true});
      }
      returnFocus=null;
    });
  }
  function open({title="Detalle",subtitle:description="",content=null,size="wide",onClose}={}) {
    ensure();
    if(node.open)node.close();
    returnFocus=document.activeElement;
    callback=onClose||null;
    heading.textContent=title;
    subtitle.textContent=description;
    body.replaceChildren();
    if(content instanceof Node) {
      // El dueño de la vista conserva su referencia al nodo original.
      body.appendChild(content);
      content.hidden=false;
    } else if(typeof content==="string") {
      const p=document.createElement("p");p.textContent=content;body.appendChild(p);
    }
    if(size==="wide")node.classList.add("asiati-modal-wide");
    node.showModal();
    document.body.classList.add("asiati-modal-open");
    return ++epoch;
  }
  function close() {if(node?.open)node.close();}
  function isOpen(){return Boolean(node?.open);}
  function current(){return epoch;}
  window.ASIATI_MODAL=Object.freeze({open,close,isOpen,current});
})();