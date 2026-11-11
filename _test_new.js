const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync('NIGHTLEDGER.html','utf8');
const js=src.slice(src.indexOf('<script>')+8,src.indexOf('</script>'));
const bodyHTML=src.slice(src.indexOf('<body>')+6,src.indexOf('<script>')).replace(/<\/body>\s*$/,'');

const VOID=new Set(['INPUT','BR','HR','IMG','META','LINK','AREA','BASE','COL','EMBED','SOURCE','TRACK','WBR','PATH','CIRCLE','RECT','LINE','POLYGON','STOP']);
const ALL=[];const ids=new Map();
const docListeners={},winListeners={};
function parseAttrs(str,node){
  const re=/([:\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;let m;
  while((m=re.exec(str))){
    const name=m[1],val=m[2]!==undefined?m[2]:m[3]!==undefined?m[3]:m[4]!==undefined?m[4]:'';
    node.setAttribute(name,val);
  }
}
function parseHTML(node,html){
  node.children=[];node._html=html;node._text='';
  const stack=[node];let i=0;
  while(i<html.length){
    if(html[i]==='<'){
      if(html.startsWith('<!--',i)){const e=html.indexOf('-->',i+4);i=e<0?html.length:e+3;continue;}
      if(html.startsWith('</',i)){const e=html.indexOf('>',i);if(e<0)break;i=e+1;if(stack.length>1)stack.pop();continue;}
      let j=i+1,quote=null;
      while(j<html.length){const ch=html[j];if(quote){if(ch===quote)quote=null;}else if(ch==='"'||ch==="'")quote=ch;else if(ch==='>')break;j++;}
      if(j>=html.length)break;
      let tagStr=html.slice(i+1,j).trim();i=j+1;
      if(tagStr.startsWith('!')||tagStr.startsWith('?'))continue;
      let self=tagStr.endsWith('/');if(self)tagStr=tagStr.slice(0,-1).trim();
      const tm=/^([A-Za-z0-9]+)([\s\S]*)$/.exec(tagStr);if(!tm)continue;
      const tag=tm[1].toUpperCase(),attrs=tm[2];
      if(tag==='BR'||tag==='INPUT'||tag==='IMG'||tag==='META'||tag==='LINK'||tag==='HR')self=true;
      const child=new Node(tag);parseAttrs(attrs,child);
      stack[stack.length-1].appendChild(child);
      if(!self&&!VOID.has(tag))stack.push(child);
    }else{
      const j=html.indexOf('<',i);const t=html.slice(i,j<0?html.length:j);
      stack[stack.length-1]._text=(stack[stack.length-1]._text||'')+t;
      i=j<0?html.length:j;
    }
  }
}
function matchSimple(node,s){
  s=s.trim();if(!s)return false;let rest=s,m;
  const tag=/^[A-Za-z0-9]+/.exec(rest);
  if(tag){if(node.tagName!==tag[0].toUpperCase())return false;rest=rest.slice(tag[0].length);}
  while(rest){
    if(rest[0]==='#'){m=/^#([\w-]+)/.exec(rest);if(!m||node.id!==m[1])return false;rest=rest.slice(m[0].length);}
    else if(rest[0]==='.'){m=/^\.([\w-]+)/.exec(rest);if(!m||!node._classes.has(m[1]))return false;rest=rest.slice(m[0].length);}
    else if(rest[0]==='['){
      m=/^\[([:\w-]+)(?:\s*(\^?=)\s*"?([^"'\]]*)"?)?\]/.exec(rest);
      if(!m)return false;const v=node.getAttribute(m[1]);
      if(v===null)return false;
      if(m[2]==='='&&String(v)!==m[3])return false;
      if(m[2]==='^='&&!String(v).startsWith(m[3]))return false;
      rest=rest.slice(m[0].length);
    }
    else if(/^[A-Za-z0-9]/.test(rest)){m=/^([A-Za-z0-9]+)/.exec(rest);if(node.tagName!==m[1].toUpperCase())return false;rest=rest.slice(m[0].length);}
    else return false;
  }
  return true;
}
function matches(node,sel){
  for(const part of String(sel).split(',')){
    const pieces=part.trim().split(/\s+/).filter(Boolean);if(!pieces.length)continue;
    if(!matchSimple(node,pieces[pieces.length-1]))continue;
    let p=node.parentNode,idx=pieces.length-2,ok=true;
    while(idx>=0){
      let found=false;
      while(p){if(matchSimple(p,pieces[idx])){found=true;p=p.parentNode;break;}p=p.parentNode;}
      if(!found){ok=false;break;}idx--;
    }
    if(ok)return true;
  }
  return false;
}
function connected(node){
  if(node===doc.body)return true;
  let n=node;while(n){if(n===doc.body)return !n._removed;if(n._removed)return false;n=n.parentNode;}
  return false;
}
function descendants(node){const out=[];const walk=n=>{for(const c of n.children){out.push(c);walk(c);}};walk(node);return out;}
class Node{
  constructor(tag){this.tagName=String(tag||'DIV').toUpperCase();this.nodeName=this.tagName;this._attrs={};this._classes=new Set();this._listeners={};this.children=[];this.parentNode=null;this._text='';this._html='';this._removed=false;this._id='';this._className='';this.value='';this.disabled=false;this.checked=false;this.scrollTop=0;this.offsetWidth=100;this.clientWidth=300;this.clientHeight=150;this.width=300;this.height=150;this._hover=null;
    this.style=new Proxy({_css:'',setProperty(k,v){this[k]=v;},removeProperty(k){delete this[k];},get cssText(){return this._css;},set cssText(v){this._css=v;}},{set(o,k,v){o[k]=v;return true;}});
    const self=this;this.classList={add(...c){c.forEach(x=>self._classes.add(x));self._syncClass();},remove(...c){c.forEach(x=>self._classes.delete(x));self._syncClass();},toggle(c,f){const has=self._classes.has(c);const on=f===undefined?!has:!!f;if(on)self._classes.add(c);else self._classes.delete(c);self._syncClass();return on;},contains(c){return self._classes.has(c);},toString(){return self._className;}};
    ALL.push(this);
  }
  _syncClass(){this._className=[...this._classes].join(' ');}
  get id(){return this._id;}set id(v){if(this._id&&ids.get(this._id)===this)ids.delete(this._id);this._id=String(v||'');if(this._id)ids.set(this._id,this);this.setAttribute('id',this._id);}
  get className(){return this._className;}set className(v){this._className=String(v||'');this._classes=new Set(this._className.split(/\s+/).filter(Boolean));this.setAttribute('class',this._className);}
  get firstChild(){return this.children[0]||null;}
  get lastChild(){return this.children[this.children.length-1]||null;}
  get parentElement(){return this.parentNode;}
  get textContent(){return this._text;}set textContent(v){this._text=String(v==null?'':v);this.children=[];}
  get innerHTML(){return this._html;}set innerHTML(v){parseHTML(this,String(v==null?'':v));}
  get outerHTML(){return '<'+this.tagName.toLowerCase()+'>'+this._html+'</'+this.tagName.toLowerCase()+'>';}
  setAttribute(k,v){k=String(k);v=String(v==null?'':v);this._attrs[k]=v;if(k==='id'){this._id=v;if(v)ids.set(v,this);}else if(k==='class'){this._className=v;this._classes=new Set(v.split(/\s+/).filter(Boolean));}else if(k==='value')this.value=v;else if(k==='disabled')this.disabled=true;else if(k==='checked')this.checked=true;else if(k==='style')this.style.cssText=v;}
  getAttribute(k){return Object.prototype.hasOwnProperty.call(this._attrs,String(k))?this._attrs[String(k)]:null;}
  removeAttribute(k){delete this._attrs[String(k)];}
  hasAttribute(k){return Object.prototype.hasOwnProperty.call(this._attrs,String(k));}
  appendChild(c){if(c.parentNode&&c.parentNode!==this)c.parentNode.removeChild(c);c.parentNode=this;this.children.push(c);c._removed=false;return c;}
  removeChild(c){const i=this.children.indexOf(c);if(i>=0)this.children.splice(i,1);c.parentNode=null;c._removed=true;return c;}
  remove(){if(this.parentNode)this.parentNode.removeChild(this);else this._removed=true;}
  insertBefore(c,ref){const i=this.children.indexOf(ref);if(c.parentNode)c.parentNode.removeChild(c);c.parentNode=this;if(i<0)this.children.push(c);else this.children.splice(i,0,c);return c;}
  contains(n){if(n===this)return true;for(const c of this.children)if(c.contains(n))return true;return false;}
  focus(){doc.activeElement=this;}
  getBoundingClientRect(){return{left:10,top:10,right:110,bottom:60,width:100,height:50,x:10,y:10};}
  getContext(){if(!this._ctx)this._ctx=makeCtx();return this._ctx;}
  addEventListener(t,fn,cap){const a=this._listeners[t]||(this._listeners[t]=[]);a.push({fn,cap:!!cap});}
  removeEventListener(t,fn){const a=this._listeners[t]||[];const i=a.findIndex(x=>x.fn===fn);if(i>=0)a.splice(i,1);}
  matches(sel){return matches(this,sel);}
  closest(sel){let n=this;while(n){if(n.matches&&n.matches(sel))return n;n=n.parentNode;}return null;}
  querySelector(sel){return this.querySelectorAll(sel)[0]||null;}
  querySelectorAll(sel){return descendants(this).filter(n=>!n._removed&&matches(n,sel));}
}
function makeCtx(){
  const grad={addColorStop(){}};
  const c={canvas:null,fillStyle:'#000',strokeStyle:'#000',lineWidth:1,globalAlpha:1,font:'',textAlign:'',textBaseline:'',lineCap:'',lineJoin:'',shadowBlur:0,shadowColor:'',globalCompositeOperation:'',
    setTransform(){},clearRect(){},fillRect(){},strokeRect(){},beginPath(){},closePath(){},moveTo(){},lineTo(){},arc(){},rect(){},fill(){},stroke(){},fillText(){},strokeText(){},save(){},restore(){},setLineDash(){},translate(){},scale(){},rotate(){},clip(){},drawImage(){},quadraticCurveTo(){},bezierCurveTo(){},arcTo(){},ellipse(){},putImageData(){},getImageData(){return{data:[]}},createLinearGradient(){return grad;},createRadialGradient(){return grad;},createPattern(){return null;},measureText(){return{width:10};}};
  return c;
}
const doc={
  readyState:'complete',activeElement:null,defaultView:null,documentElement:new Node('HTML'),
  body:new Node('BODY'),
  listeners:docListeners,
  addEventListener(t,fn,cap){const a=docListeners[t]||(docListeners[t]=[]);a.push({fn,cap:!!cap});},
  removeEventListener(t,fn){const a=docListeners[t]||[];const i=a.findIndex(x=>x.fn===fn);if(i>=0)a.splice(i,1);},
  createElement(t){return new Node(t);},
  createTextNode(t){const n=new Node('#TEXT');n.textContent=t;return n;},
  createComment(){return new Node('#COMMENT');},
  getElementById(id){if(ids.has(id))return ids.get(id);const n=new Node('DIV');n.id=id;doc.body.appendChild(n);return n;},
  querySelector(sel){return doc.querySelectorAll(sel)[0]||null;},
  querySelectorAll(sel){return ALL.filter(n=>!n._removed&&connected(n)&&matches(n,sel));},
  createEvent(){return{};},
  dispatchEvent(){return true;}
};
doc.body.innerHTML=bodyHTML;
doc.activeElement=doc.body;doc.documentElement.appendChild(doc.body);
ALL.push(doc.documentElement);
const lsData=new Map();
const localStorage={getItem(k){return lsData.has(k)?lsData.get(k):null;},setItem(k,v){lsData.set(k,String(v));},removeItem(k){lsData.delete(k);},clear(){lsData.clear();},key(i){return[...lsData.keys()][i]||null;},get length(){return lsData.size;}};
const win={innerWidth:1440,innerHeight:900,devicePixelRatio:1,document:doc,localStorage,performance:{now:()=>Date.now()},
  addEventListener(t,fn,cap){const a=winListeners[t]||(winListeners[t]=[]);a.push({fn,cap:!!cap});},
  removeEventListener(t,fn){const a=winListeners[t]||[];const i=a.findIndex(x=>x.fn===fn);if(i>=0)a.splice(i,1);},
  requestAnimationFrame:()=>0,cancelAnimationFrame:()=>{},setTimeout:()=>0,clearTimeout:()=>{},setInterval:()=>0,clearInterval:()=>{},
  matchMedia:undefined,AudioContext:undefined,webkitAudioContext:undefined,location:{},navigator:{},console};
win.self=win;win.window=win;doc.defaultView=win;
const sandbox={console,document:doc,window:win,globalThis:null,innerWidth:1440,innerHeight:900,devicePixelRatio:1,
  requestAnimationFrame:()=>0,cancelAnimationFrame:()=>{},setTimeout:()=>0,clearTimeout:()=>{},setInterval:()=>0,clearInterval:()=>{},
  performance:{now:()=>Date.now()},localStorage,Blob:class{},URL:{createObjectURL:()=>'blob:x',revokeObjectURL:()=>{}},navigator:{},
  AudioContext:undefined,webkitAudioContext:undefined,location:{},self:null};
sandbox.globalThis=sandbox;sandbox.self=sandbox;win.globalThis=sandbox;
function dispatch(target,type,props){
  const ev=Object.assign({type,target,clientX:100,clientY:100,button:0,key:'',ctrlKey:false,metaKey:false,shiftKey:false,
    defaultPrevented:false,propStop:false,immediateStop:false,
    preventDefault(){this.defaultPrevented=true;},stopPropagation(){this.propStop=true;},stopImmediatePropagation(){this.immediateStop=true;this.propStop=true;}},props||{});
  const path=[];let n=target;while(n){path.unshift(n);n=n.parentNode;}path.unshift(doc);
  for(const node of path){
    const list=node===doc?docListeners:(node._listeners||{});
    for(const l of (list[type]||[])){if(l.capture&&!ev.immediateStop)l.fn.call(node,ev);}
    if(ev.propStop)break;
  }
  if(!ev.propStop){
    for(let i=path.length-1;i>=0;i--){
      const node=path[i];const list=node===doc?docListeners:(node._listeners||{});
      for(const l of (list[type]||[])){if(!l.capture&&!ev.immediateStop)l.fn.call(node,ev);}
      if(ev.propStop)break;
    }
  }
  return ev;
}

const errors=[];
function T(name,fn){try{fn();console.log('PASS',name);}catch(e){errors.push(name+': '+e.stack);console.log('FAIL',name,e.message);}}
vm.runInNewContext(js,sandbox,{filename:'nightledger.js'});
const NL=sandbox.NL,UI=sandbox.NLUI;
NL.DEBUG_CHARTS=true;
T('exports',()=>{if(!NL||!UI||!NL.newGame)throw new Error('missing exports');});
let S;
T('newGame+setState',()=>{S=NL.newGame(12345,{cash:3200,settings:{density:'clean',sound:false,autopause:false,autosave:false,showRoutes:true}});NL._setState(S);UI.applyDensity();});
T('step 160h',()=>{for(let i=0;i<160;i++)NL.step(1);UI.render(true);});
T('7 views clean',()=>{for(const v of ['overview','market','operations','network','ledger','intel','systems'])UI.setView(v);});
T('7 views analyst',()=>{S.settings.density='analyst';UI.applyDensity();for(const v of ['overview','market','operations','network','ledger','intel','systems'])UI.setView(v);S.settings.density='clean';UI.applyDensity();UI.render(true);});
T('charts draw',()=>{let n=0;for(const v of ['overview','market','network','ledger','intel']){UI.setView(v);n+=doc.querySelectorAll('canvas[data-chart]').length;}if(n<5)throw new Error('too few canvases '+n);});
T('layered modals',()=>{
  UI.closeAllModals();doc.getElementById('boot').classList.add('hidden');
  UI.settings();UI.closeAllModals();
  UI.manual();UI.closeAllModals();
  UI.loadScreen();UI.closeAllModals();
  UI.newGameModal();UI.closeAllModals();
  UI.pauseMenu();UI.closeAllModals();
  UI.worldLens();UI.closeAllModals();
  UI.districtSheet(0);UI.closeAllModals();
  UI.confirm('Test','Body','Go',()=>{});UI.closeAllModals();
  UI.exportSave();UI.closeAllModals();
  UI.importSave();UI.closeAllModals();
  UI.openPalette();UI.renderPalette();UI.closePalette();
});
T('offers modal',()=>{if(!S.offers.length)throw new Error('no offers generated');UI.offerModal(S.offers[0].id);UI.closeAllModals();});
T('tutorial',()=>{UI.tutorial();UI.closeAllModals();});
T('save/load',()=>{UI.save(true);if(!UI.hasSave())throw new Error('no save');if(!UI.load(true))throw new Error('load failed');});
T('toggles',()=>{UI.togglePause();UI.togglePause();UI.toggleDensity();UI.toggleDensity();UI.toggleFocus();UI.toggleFocus();UI.toggleMinimize();UI.toggleMinimize();});
T('actions coverage',()=>{
  const acts=[...new Set([...src.matchAll(/data-act="([^"]+)"/g)].map(m=>m[1]))];
  const parent=new Node('DIV');
  for(const a of acts){
    const n=new Node('BUTTON');n.setAttribute('data-act',a);n.setAttribute('data-id','1');n.setAttribute('data-p','0');n.setAttribute('data-d','0');n.setAttribute('data-v','1');n.parentNode=parent;
    UI.handleAction(a,n,{});
  }
});
T('world actions',()=>{UI.act(NL.actions.serviceGear());UI.act(NL.actions.seedRumor());});
T('key Q radial',()=>{
  UI.closeAllModals();doc.getElementById('palette').classList.remove('show');
  dispatch(doc,'keydown',{key:'q'});
  if(doc.getElementById('radial-wrap').classList.contains('hidden'))throw new Error('radial did not open');
  dispatch(doc,'keydown',{key:'q'});
  if(!doc.getElementById('radial-wrap').classList.contains('hidden'))throw new Error('radial did not close');
});
T('context menu',()=>{
  dispatch(doc.body,'contextmenu',{clientX:100,clientY:100});
  if(!doc.getElementById('ctx').classList.contains('show'))throw new Error('ctx did not show');
  dispatch(doc.body,'click',{clientX:400,clientY:400});
  if(doc.getElementById('ctx').classList.contains('show'))throw new Error('ctx did not hide');
});
T('boot menu + journal button',()=>{
  dispatch(doc.getElementById('boot-new'),'click');
  const before=doc.querySelectorAll('.modal-scrim').length;
  UI.closeAllModals();
  dispatch(doc.getElementById('tbar-journal'),'click');
  UI.closeAllModals();
  if(before<1)throw new Error('boot-new did not open a modal');
});
T('data-sk dispatcher',()=>{
  const btn=new Node('BUTTON');btn.setAttribute('data-sk','misc:density');doc.body.appendChild(btn);
  const before=S.settings.density;
  const ev=dispatch(btn,'click',{clientX:100,clientY:100});
  const after=sandbox.NL.getState().settings.density;
  if(after===before)throw new Error('density not toggled');
  S=sandbox.NL.getState();S.settings.density='clean';UI.applyDensity();
});
T('static checks',()=>{
  if(src.indexOf('http')>=0)throw new Error('http ref');
  if((src.match(/<script>/g)||[]).length!==1)throw new Error('script count');
  if((src.match(/<style>/g)||[]).length!==1)throw new Error('style count');
  if(src.indexOf('// RUNTIME DIAGNOSTICS')>=0)throw new Error('old boot copy');
  if(src.indexOf('ENGINE TELEMETRY')>=0)throw new Error('telemetry copy');
  if(src.indexOf('Shadow Market Protocol')>=0)throw new Error('old title');
});
console.log('\nERRORS',errors.length);
if(errors.length){console.log(errors.join('\n---\n'));process.exit(1);}
