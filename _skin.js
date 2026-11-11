/* =====================================================================================
   Presentation layer — cinematic shell, layered sheets and interaction polish.
   Adds no simulation state and touches no engine hooks.
   ===================================================================================== */
const SKIN={};
SKIN.motionOK=true;
SKIN.lastAlerts=0;
SKIN.sweepT=null;
SKIN.ctxOpen=false;
SKIN.radialOpen=false;
SKIN.listening=null;
SKIN.pauseCtx=null;
SKIN.settingsCtx=null;
SKIN.notesCtx=null;
SKIN.journalCtx=null;
SKIN.loadCtx=null;
SKIN.startCtx=null;

function skEl(id){return typeof document!=='undefined'&&document.getElementById?document.getElementById(id):null;}
function skText(id,t){const n=skEl(id);if(n)n.textContent=t;}
function skAttr(n,k,d){return n&&n.getAttribute?n.getAttribute(k):d;}
function skEach(nodes,fn){if(!nodes)return;if(typeof nodes.forEach==='function')nodes.forEach(fn);else for(let i=0;i<nodes.length;i++)fn(nodes[i],i);}
function skClose(name){if(name==='settingsCtx')SKIN.listening=null;const c=SKIN[name];if(c&&c.close){try{c.close();}catch(e){}}SKIN[name]=null;}
function skQS(n,sel){return n&&n.querySelector?n.querySelector(sel):null;}
function skQSA(n,sel){return n&&n.querySelectorAll?n.querySelectorAll(sel):[];}
function skPage(node){if(!node)return;try{node.classList.remove('turn');void node.offsetWidth;node.classList.add('turn');}catch(e){}}
function skPrettyTime(t){t=Math.max(0,+t||0);return'Day '+(Math.floor(t/24)+1)+', '+fmtHour(t%24);}
function skPrettyKey(k){if(k===' ')return'Space';if(k==='Escape')return'Esc';if(k==='Ctrl+S'||k==='Ctrl+K')return k;if(k&&k.length===1)return k.toUpperCase();return k||'—';}
function skCfg(){
  let c={};try{c=UI.readStoredSettings?UI.readStoredSettings():{};}catch(e){}
  if(!c||typeof c!=='object')c={};
  return Object.assign({density:'clean',sound:true,autopause:true,autosave:true,showRoutes:true,motion:true,ambient:true,softCursor:true,cinematic:true,tutorialDone:false},c,S&&S.settings?S.settings:{});
}
SKIN.applyPrefs=function(){
  if(typeof document==='undefined'||!document.body)return;
  const c=skCfg();
  let reduce=c.motion===false||c.cinematic===false;
  try{if(!reduce&&typeof window!=='undefined'&&window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches)reduce=true;}catch(e){}
  document.body.classList.toggle('no-motion',!!reduce);
  document.body.classList.toggle('soft-cursor',c.softCursor!==false);
  document.body.classList.toggle('ambient-off',c.ambient===false);
  SKIN.motionOK=!reduce;
};
SKIN.persistCfg=function(cfg){
  if(!cfg)return;
  if(S&&S.settings)Object.assign(S.settings,cfg);
  try{localStorage.setItem('nightledger.settings',JSON.stringify(S&&S.settings?S.settings:cfg));}catch(e){}
  SKIN.applyPrefs();
};
SKIN.ambient=function(){
  const n=skEl('ambient');if(!n||!S)return;
  const h=S.hour||0,w=(WEATHER[S.weather]||WEATHER[0]).key;
  let top='rgba(201,162,95,.16)',bottom='rgba(127,155,181,.03)',op='.17';
  if(h>=6&&h<11){top='rgba(217,161,91,.20)';bottom='rgba(127,155,181,.05)';op='.20';}
  else if(h>=11&&h<17){top='rgba(127,155,181,.10)';bottom='rgba(255,255,255,.01)';op='.12';}
  else if(h>=17&&h<22){top='rgba(207,139,92,.20)';bottom='rgba(30,34,40,.12)';op='.22';}
  else{top='rgba(155,143,176,.13)';bottom='rgba(10,12,16,.24)';op='.24';}
  if(w==='Rain'||w==='Storm'){top='rgba(127,155,181,.18)';op='.27';}
  else if(w==='Fog'){top='rgba(155,143,176,.16)';op='.25';}
  n.style.background='linear-gradient(180deg,'+top+','+bottom+')';
  n.style.opacity=op;
};
SKIN.sweep=function(){
  if(!SKIN.motionOK)return;
  const n=skEl('wipe');if(!n)return;
  try{n.classList.remove('run');void n.offsetWidth;n.classList.add('run');}catch(e){}
  if(SKIN.sweepT)clearTimeout(SKIN.sweepT);
  SKIN.sweepT=setTimeout(()=>{try{n.classList.remove('run');}catch(e){}},620);
};
SKIN.updateAlertBadge=function(){
  const n=skEl('alert-badge');if(!n)return;
  const c=S?S.offers.length:0;
  n.textContent=c;n.classList.toggle('hidden',c===0);
  if(c!==SKIN.lastAlerts){SKIN.lastAlerts=c;n.classList.remove('pulse-badge');void n.offsetWidth;n.classList.add('pulse-badge');}
};
SKIN.decorate=function(){
  const host=skEl('view');if(!host||!host.querySelectorAll)return;
  const nodes=host.querySelectorAll('.panel,.kpi,.card,.tbl tbody tr,.feed-item');
  const count=Math.min(nodes.length,90);
  for(let i=0;i<count;i++){
    const d=Math.min(260,Math.floor(i/5)*26);
    if(nodes[i].style)nodes[i].style.animationDelay=d+'ms';
  }
  SKIN.updateAlertBadge();
};
SKIN.afterRender=function(){SKIN.applyPrefs();SKIN.ambient();SKIN.decorate();};

/* ---------- save slots ---------- */
SKIN.slotKey=i=>i===0?'nightledger.save':'nightledger.slot'+i;
SKIN.slotLabel=i=>i===0?'Autosave':'Manual ' + i;
SKIN.metaKey='nightledger.slotMeta';
SKIN.readSlot=function(i){try{return localStorage.getItem(SKIN.slotKey(i));}catch(e){return null;}};
SKIN.meta=function(){try{return JSON.parse(localStorage.getItem(SKIN.metaKey)||'{}')||{};}catch(e){return{};}};
SKIN.setMeta=function(i,obj){try{const m=SKIN.meta();m[i]=obj;localStorage.setItem(SKIN.metaKey,JSON.stringify(m));}catch(e){}};
SKIN.hasAnySave=function(){for(let i=0;i<3;i++)if(SKIN.readSlot(i))return true;return false;};
SKIN.slotInfo=function(i){
  const raw=SKIN.readSlot(i);if(!raw)return null;
  let o={};try{o=JSON.parse(raw)||{};}catch(e){}
  const meta=SKIN.meta()[i]||{};
  const age=meta.savedAt?Date.now()-meta.savedAt:null;
  const when=age===null?'Saved earlier':age<90000?'Saved just now':age<86400000?'Saved today':'Saved earlier';
  return{tick:o.tick||0,seed:o.seed||0,cash:o.cash||0,del:o.stats&&o.stats.deliveries||0,when:when,whenShort:when,raw:raw};
};
SKIN.saveSlot=function(i){
  if(!S){UI.toast('Nothing to save','Begin a story first.','warn');return;}
  if(i===0){UI.save(true);}
  else{
    try{localStorage.setItem(SKIN.slotKey(i),NL.serialize());SKIN.setMeta(i,{savedAt:Date.now(),tick:S.tick});UI.toast('Story saved',SKIN.slotLabel(i)+' is up to date.','good');}
    catch(e){UI.toast('Could not save','Local storage is unavailable.','bad');}
  }
  SKIN.updateBootInfo();SKIN.loadRender();
};
SKIN.loadSlot=function(i){
  const raw=SKIN.readSlot(i);
  if(!raw){UI.toast('Empty slot','There is no story here yet.','warn');return;}
  try{
    NL.deserialize(raw);
    const b=skEl('boot');if(b)b.classList.add('hidden');
    UI.applyDensity();UI.closeAllModals();UI.render(true);
    if(S)S.paused=false;UI.renderTop();
    SKIN.sweep();SKIN.updateBootInfo();skClose('loadCtx');
    UI.toast('Story restored','Picked up at '+skPrettyTime(S.tick)+'.','good');
  }catch(e){UI.toast('Could not load',esc(e.message),'bad');}
};
SKIN.loadHTML=function(){
  const cards=[];
  for(let i=0;i<3;i++){
    const q=SKIN.slotInfo(i);
    const art=i===0?'':i===1?' alt2':' alt3';
    const body=q?
      '<div class="sn">'+SKIN.slotLabel(i)+'</div><div class="sm">'+skPrettyTime(q.tick)+' · '+fmtC(q.cash)+' · '+fmtN(q.del)+' deliveries</div><div class="slot-meta">Seed '+hashStr(String(q.seed)).slice(0,6).toUpperCase()+' · '+q.when+'</div>':
      '<div class="sn">'+SKIN.slotLabel(i)+'</div><div class="empty-slot">Empty. A place for a turning point.</div>';
    cards.push('<div class="slot"><div class="slot-art'+art+'"><span class="sun"></span><span class="sky-lines"></span></div><div class="slot-body">'+body+
      '<div class="slot-actions"><button class="btn sm primary" data-sk="load:slot" data-i="'+i+'" data-op="load"'+(q?'':' disabled')+'>Continue</button>'+
      '<button class="btn sm" data-sk="load:slot" data-i="'+i+'" data-op="save"'+(S?'':' disabled')+'>Save here</button></div></div></div>');
  }
  return'<div class="tip-card"><div class="th">Three places to keep a story</div><div class="tb">The autosave writes itself every in-game day. The other two are yours — use one before a risky decision and one for a run you want to return to.</div></div>'+
    '<div class="slot-grid">'+cards.join('')+'</div>';
};
SKIN.loadRender=function(){
  const c=SKIN.loadCtx;if(!c)return;
  const host=skQS(c.m,'.drawer-body');if(!host)return;
  host.innerHTML=SKIN.loadHTML();skPage(host);
};
SKIN.loadScreen=function(){
  SKIN.hideCtx();SKIN.hideRadial();
  UI.openModal({title:'Saved stories',sub:'Pick up where you left off',wide:true,
    body:'<div class="drawer-body"></div>',
    footer:'<span class="tiny dim" style="flex:1">Saves live on this machine only.</span><button class="btn primary" data-mclose>Close</button>',
    onMount:(m,close)=>{
      m.classList.add('load-sheet');SKIN.loadCtx={m:m,close:close};SKIN.loadRender();
    }});
};

/* ---------- key bindings ---------- */
SKIN.keyStore='nightledger.keys';
SKIN.defaultKeys={pause:' ',density:'F2',world:'F3',quick:'q',help:'?',rest:'r',step:'.',menu:'Escape',journal:'j',save:'Ctrl+S'};
SKIN.bindings={};SKIN.customKeys={};
SKIN.loadBindings=function(){
  let o={};try{o=JSON.parse(localStorage.getItem(SKIN.keyStore)||'{}')||{};}catch(e){o={};}
  SKIN.bindings=o||{};SKIN.customKeys={};
  for(const a in SKIN.bindings){if(Object.prototype.hasOwnProperty.call(SKIN.bindings,a))SKIN.customKeys[String(SKIN.bindings[a]).toLowerCase()]=a;}
};
SKIN.saveBindings=function(){try{localStorage.setItem(SKIN.keyStore,JSON.stringify(SKIN.bindings));}catch(e){}};
SKIN.setBinding=function(action,key){
  const old=SKIN.bindings[action];if(old)delete SKIN.customKeys[String(old).toLowerCase()];
  SKIN.bindings[action]=key;SKIN.customKeys[String(key).toLowerCase()]=action;SKIN.saveBindings();
};
SKIN.resetBindings=function(){SKIN.bindings={};SKIN.customKeys={};SKIN.saveBindings();};
SKIN.keyFor=function(a){return SKIN.bindings[a]||SKIN.defaultKeys[a]||'—';};
SKIN.defaultActions={' ':'pause','1':'view1','2':'view2','3':'view3','4':'view4','5':'view5','6':'view6','7':'view7',
  'f2':'density','f3':'world','f9':'minimize','f10':'focus','f1':'help','?':'help','/':'help','r':'rest','.':'step',
  '+':'speedUp','=':'speedUp','-':'speedDown','_':'speedDown','q':'quick','j':'journal'};
SKIN.actionForKey=function(key){
  if(!key)return null;
  const k=String(key).toLowerCase();
  if(SKIN.customKeys[k])return SKIN.customKeys[k];
  return SKIN.defaultActions[k]||null;
};
SKIN.runBound=function(action,e){
  const views=['overview','market','operations','network','ledger','intel','systems'];
  if(/^view[1-7]$/.test(action)){UI.setView(views[+action.slice(4)-1]);return;}
  switch(action){
    case'pause':UI.togglePause();break;
    case'density':UI.toggleDensity();break;
    case'world':if(S)UI.worldLens();break;
    case'minimize':UI.toggleMinimize();break;
    case'focus':UI.toggleFocus();break;
    case'help':UI.manual();break;
    case'rest':UI.rest();break;
    case'step':if(S){NL.step(e&&e.shiftKey?24:1);UI.render(true);}break;
    case'speedUp':if(S){S.speed=Math.min(8,S.speed*2);S.paused=false;UI.renderTop();}break;
    case'speedDown':if(S){S.speed=Math.max(1,Math.round(S.speed/2));UI.renderTop();}break;
    case'quick':SKIN.toggleRadial();break;
    case'menu':UI.pauseMenu();break;
    case'journal':SKIN.journal();break;
    case'save':UI.save(true);break;
    default:break;
  }
};
SKIN.keyCapture=function(e){
  if(!e)return;
  const stop=()=>{if(e.preventDefault)e.preventDefault();if(e.stopImmediatePropagation)e.stopImmediatePropagation();else if(e.stopPropagation)e.stopPropagation();};
  const key=e.key;
  if(SKIN.listening){
    stop();
    if(key==='Escape'){SKIN.listening=null;SKIN.settingsRender();return;}
    if(['Control','Shift','Alt','Meta','Escape','Tab'].indexOf(key)>=0)return;
    if(key){SKIN.setBinding(SKIN.listening,key);UI.toast('Key set',skPrettyKey(key)+' now opens '+SKIN.listening+'.','good');}
    SKIN.listening=null;SKIN.settingsRender();return;
  }
  const quickKey=String(SKIN.keyFor('quick')||'q').toLowerCase();
  const k=String(key||'').toLowerCase();
  if(key==='Escape'){
    if(SKIN.radialOpen){SKIN.hideRadial();stop();return;}
    if(SKIN.ctxOpen){SKIN.hideCtx();stop();return;}
    return;
  }
  if(SKIN.radialOpen){
    if(k===quickKey){SKIN.hideRadial();stop();return;}
    return;
  }
  if(SKIN.ctxOpen&&k===quickKey){SKIN.hideCtx();SKIN.toggleRadial();stop();return;}
  if(SKIN.ctxOpen)return;
  if((e.ctrlKey||e.metaKey)||!key)return;
  const tag=(e.target&&e.target.tagName)||'';
  if(tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT')return;
  if(UI.modalOpen())return;
  const pal=skEl('palette');if(pal&&pal.classList.contains('show'))return;
  if(SKIN.radialOpen||SKIN.ctxOpen)return;
  const action=SKIN.actionForKey(key);
  if(!action)return;
  stop();SKIN.runBound(action,e);
};
SKIN.loadBindings();

/* ---------- context menu + quick wheel ---------- */
SKIN.hideCtx=function(){const n=skEl('ctx');if(n)n.classList.remove('show');SKIN.ctxOpen=false;};
SKIN.showCtx=function(e){
  if(!e||typeof document==='undefined')return;
  if(e.target&&e.target.closest&&e.target.closest('input,textarea,select'))return;
  if(e.preventDefault)e.preventDefault();
  const n=skEl('ctx');if(!n)return;
  const items=[
    ['ctx:market','↗','Open the market'],['ctx:save','▤','Save this story'],['ctx:detail','◫','Show more detail'],
    ['sep','',''],['ctx:notes','?','Field notes'],['ctx:world','☾','Look behind the ledger'],['ctx:journal','✎','Open the journal'],
    ['sep','',''],['ctx:wheel','◈','Quick wheel'],['ctx:options','⚙','Options'],['ctx:pause','❚❚','Pause']
  ];
  n.innerHTML='<div class="ctx-h">Right-click menu</div>'+items.map(q=>q[0]==='sep'?'<div class="ctx-sep"></div>':'<button class="ci" data-sk="'+q[0]+'"><i>'+q[1]+'</i><b>'+q[2]+'</b></button>').join('');
  const ww=(typeof window!=='undefined'&&window.innerWidth)||1280,wh=(typeof window!=='undefined'&&window.innerHeight)||720;
  const x=Math.min((e.clientX||0),ww-220),y=Math.min((e.clientY||0),wh-330);
  n.style.left=Math.max(8,x)+'px';n.style.top=Math.max(8,y)+'px';
  n.classList.add('show');SKIN.ctxOpen=true;SKIN.hideRadial();
};
SKIN.hideRadial=function(){const n=skEl('radial-wrap');if(n){n.classList.add('hidden');n.innerHTML='';}SKIN.radialOpen=false;};
SKIN.toggleRadial=function(){
  const wrap=skEl('radial-wrap');if(!wrap)return;
  if(!wrap.classList.contains('hidden')){SKIN.hideRadial();return;}
  SKIN.hideCtx();
  const items=[
    {a:'radial:desk',i:'◈',n:'The desk',k:'1'},
    {a:'radial:market',i:'↗',n:'Market',k:'2'},
    {a:'radial:ops',i:'▣',n:'Operations',k:'3'},
    {a:'radial:save',i:'▤',n:'Save',k:'S'},
    {a:'radial:city',i:'☾',n:'Behind it',k:'F3'},
    {a:'radial:notes',i:'?',n:'Field notes',k:'?'}
  ];
  const C=215,R=152;
  const html=items.map((q,i)=>{
    const ang=-Math.PI/2+i*2*Math.PI/items.length;
    const left=C+Math.cos(ang)*R-52,top=C+Math.sin(ang)*R-52;
    return'<button class="radial-item" data-sk="'+q.a+'" style="left:'+left.toFixed(1)+'px;top:'+top.toFixed(1)+'px;animation-delay:'+(i*45)+'ms"><span class="ri">'+q.i+'</span><span class="rn">'+q.n+'</span><span class="rk">'+q.k+'</span></button>';
  }).join('');
  wrap.innerHTML='<div class="radial-scrim" data-sk="radial:close"><div class="radial"><div class="radial-core">Quick wheel<small>Q to close</small></div>'+html+'</div></div>';
  wrap.classList.remove('hidden');SKIN.radialOpen=true;
};

/* ---------- layered settings ---------- */
SKIN.settingToggle=function(k,label,desc,cfg){
  const on=k==='density'?cfg[k]==='analyst':!!cfg[k];
  return'<div class="setting-row"><div class="sr-label"><b>'+label+'</b><span>'+desc+'</span></div>'+
    '<div class="sr-val">'+(k==='density'?(on?'Detail':'Clean'):(on?'On':'Off'))+'</div>'+
    '<div class="switch '+(on?'on':'')+'" data-sk="settings:toggle" data-k="'+k+'"><span class="knob"></span></div></div>';
};
SKIN.keyRow=function(a,label,desc){
  return'<div class="keyrow"><div class="kn">'+label+'<small>'+desc+'</small></div><div class="kb '+(SKIN.listening===a?'listening':'')+'" data-sk="settings:bind" data-bind="'+a+'">'+(SKIN.listening===a?'Press a key…':skPrettyKey(SKIN.keyFor(a)))+'</div></div>';
};
SKIN.settingsHTML=function(tab,cfg){
  if(tab==='Game'){
    return SKIN.settingToggle('sound','Sound effects','Small interface cues, generated on this machine.',cfg)+
      SKIN.settingToggle('autopause','Pause on surprises','Stop when an inspection or a big shift needs a decision.',cfg)+
      SKIN.settingToggle('autosave','Autosave each day','Keep a rolling save at every in-game daybreak.',cfg)+
      SKIN.settingToggle('showRoutes','Draw courier routes','Show stock moving across the city map.',cfg)+
      SKIN.settingToggle('density','Detail level','Clean for the essentials; detail for extra columns and notes.',cfg)+
      '<div class="divider"></div><div class="setting-row"><div class="sr-label"><b>City speed</b><span>How many in-game hours pass each second.</span></div><div class="row wrap" style="gap:5px">'+
      [1,2,4,8].map(v=>'<button class="chip '+(S&&S.speed===v?'on':'')+'" data-sk="settings:speed" data-v="'+v+'">'+v+'×</button>').join('')+'</div></div>'+
      '<div class="notice" style="margin-top:12px">The clean interface shows only what helps you decide. Press <span class="kbd">F2</span> whenever you want the deeper numbers.</div>';
  }
  if(tab==='Presentation'){
    return SKIN.settingToggle('motion','Motion & transitions','Sweeps, staggered panels and soft press feedback.',cfg)+
      SKIN.settingToggle('cinematic','Living title screen','Slow drifting light behind the main menu.',cfg)+
      SKIN.settingToggle('ambient','Time-of-day light','A subtle warm tint that follows the city clock.',cfg)+
      SKIN.settingToggle('softCursor','Cursor ring','A quiet brass ring that follows the pointer.',cfg)+
      '<div class="tip-card" style="margin-top:12px"><div class="th">Your pace, your room</div><div class="tb">Turn motion off for still, immediate screens. The game automatically respects your system’s reduced-motion preference.</div></div>';
  }
  if(tab==='Controls'){
    return'<div class="tip-card"><div class="th">Make the keys yours</div><div class="tb">Click a key, then press a new one. Esc cancels. The defaults stay in the field notes.</div></div>'+
      SKIN.keyRow('pause','Pause / resume','Freeze or start the city clock')+
      SKIN.keyRow('density','Detail level','Clean or deeper interface')+
      SKIN.keyRow('world','Behind the ledger','A glimpse of the living city')+
      SKIN.keyRow('quick','Quick wheel','Radial menu at your cursor')+
      SKIN.keyRow('help','Field notes','Open the guide')+
      SKIN.keyRow('rest','Rest eight hours','Move time forward safely')+
      SKIN.keyRow('step','Step one hour','Advance a single hour')+
      SKIN.keyRow('journal','Journal','Recent street talk')+
      SKIN.keyRow('save','Save story','Write the rolling save')+
      '<div class="row" style="margin-top:12px;gap:7px"><button class="btn sm" data-sk="settings:defaults">Restore default keys</button><span class="tiny dim">Ctrl+K opens quick actions · Ctrl+S saves · 1–7 switch views</span></div>';
  }
  return'<div class="tip-card"><div class="th">Your stories stay here</div><div class="tb">Everything is stored locally in this browser. Copy a save file if you want to keep a run elsewhere.</div></div>'+
    '<div class="grid g2" style="gap:7px">'+
    [['settings:save','Save story'],['settings:load','Saved stories'],['settings:export','Copy save file'],['settings:import','Paste a save'],['settings:new','Begin a new story'],['settings:reset','Erase everything']].map(q=>'<button class="btn" data-sk="'+q[0]+'">'+q[1]+'</button>').join('')+'</div>'+
    '<div class="divider"></div><div class="statline"><span>Storage</span><b>local · offline</b></div><div class="statline"><span>Rolling save</span><b>'+(SKIN.readSlot(0)?'present':'empty')+'</b></div>';
};
SKIN.settingsRender=function(){
  const c=SKIN.settingsCtx;if(!c)return;
  const host=skQS(c.m,'.drawer-body');if(!host)return;
  host.innerHTML=SKIN.settingsHTML(c.tab,c.cfg);
  skEach(skQSA(c.m,'[data-tab]'),b=>b.classList.toggle('on',skAttr(b,'data-tab','')===c.tab));
  skPage(host);
};
SKIN.settings=function(){
  SKIN.hideCtx();SKIN.hideRadial();
  const cfg=skCfg();
  const tabs=['Game','Presentation','Controls','Data'];
  UI.openModal({title:'Options',sub:'Make it yours',wide:true,
    body:'<div class="settings-shell"><div class="settings-tabs">'+tabs.map((t,i)=>'<button data-sk="settings:tab" data-tab="'+t+'" class="'+(i===0?'on':'')+'">'+t+'</button>').join('')+'</div><div class="drawer-body"></div></div>',
    footer:'<button class="btn" data-sk="settings:defaults">Reset keys</button><span class="spacer"></span><button class="btn primary" data-sk="settings:done">Done</button>',
    onMount:(m,close)=>{
      m.classList.add('settings-sheet');SKIN.settingsCtx={m:m,close:close,cfg:cfg,tab:'Game'};SKIN.settingsRender();
    }});
};

/* ---------- field notes ---------- */
SKIN.notesHTML=function(tab){
  if(tab==='The loop'){
    const steps=[
      ['01','Read the room','The desk shows five live numbers and three suggested next steps. Everything else waits until you ask for it.'],
      ['02','Buy & prepare','Purchase wholesale stock, queue a workshop run, then send the finished lot to a district with an idle courier.'],
      ['03','Choose a price','Post a retail price, or let the suggested price do it. Buyers also arrive with requests you can accept or counter.'],
      ['04','Mind the attention','Busy streets draw notice. Lay low for a while when things get warm; an inspection costs cash, stock and standing.'],
      ['05','Settle & grow','Sales arrive as unsettled money. Settle it, repay debt, improve the workshop and follow new leads.'],
      ['06','Keep your rhythm','Space pauses, 1–7 switch views, R rests eight hours, Q opens the quick wheel and Ctrl+K finds anything.']
    ];
    return'<div class="notes-grid">'+steps.map(s=>'<div class="note-card"><div class="nn">'+s[0]+'</div><div class="nt">'+s[1]+'</div><div class="nb">'+s[2]+'</div></div>').join('')+'</div>';
  }
  if(tab==='The city'){
    return'<div class="tip-card"><div class="th">Most of the city never reaches the ledger</div><div class="tb">Every contact keeps a daily routine, energy, mood and memory. Weather shifts, patrols rotate, paydays arrive, rumours travel between districts, gear wears down and witnesses compare notes. Those private lives quietly bend prices, requests, attention and yield. You do not need to track any of it to play — it simply makes the place feel lived in.</div></div>'+
      '<div class="notes-grid">'+[
        ['People','Buyers sleep, work, meet friends and change their minds. A tired contact is less likely to ask for anything.'],
        ['Weather','Rain slows the streets; fog hides movement; a storm changes what people want and how quickly stock moves.'],
        ['Rumours','A story started in one district can reach a neighbour by evening and lift or depress a price for a while.'],
        ['Wear','Rigs, vehicles and packaging degrade with use. A quiet workshop visit restores what the hours took away.']
      ].map(q=>'<div class="note-card"><div class="nt">'+q[0]+'</div><div class="nb">'+q[1]+'</div></div>').join('')+'</div>'+
      '<div class="row" style="margin-top:12px;gap:7px"><button class="btn primary" data-sk="notes:world">Look behind the ledger</button><span class="tiny dim">F3 at any time · F2 reveals the deeper state</span></div>';
  }
  if(tab==='Glossary'){
    const g=[
      ['Attention','How much notice the city is taking. Volume raises it; quiet hours lower it.'],
      ['Appetite','Hidden local desire for a good. It drifts with the hour, weather, mood and repeat sales.'],
      ['Saturation','Buyer fatigue after too much of the same thing. It fades with time.'],
      ['Grade','The quality of a lot. Better grade lifts value and opens premium requests.'],
      ['Settling up','Turning unsettled sales into spendable cash, within a hourly limit and a small fee.'],
      ['Influence','Your share of a district. Sales build it; other crews erode it.'],
      ['Leads','Insight earned over time and spent on lasting contacts and improvements.'],
      ['Outlook','A range of possible tomorrows, drawn from many quiet trial runs.']
    ];
    return'<div class="glossary-grid">'+g.map(q=>'<div class="card"><div class="t">'+q[0]+'</div><div class="s" style="margin-top:5px">'+q[1]+'</div></div>').join('')+'</div>';
  }
  const keys=[['Space','Pause or resume'],['1–7','Switch views'],['F2','Clean / detail'],['F3','Behind the ledger'],['Q','Quick wheel'],['R','Rest 8h'],['.','Step 1h'],['Ctrl+K','Quick actions'],['Ctrl+S','Save'],['?','Field notes'],['Esc','Pause menu']];
  return'<div class="tip-card"><div class="th">Keys, at a glance</div><div class="tb">You can change several of these in Options → Controls. Right-click anywhere for a small context menu.</div></div>'+
    keys.map(k=>'<div class="keyrow"><div class="kn">'+k[1]+'</div><div class="kb" style="cursor:default">'+k[0]+'</div></div>').join('');
};
SKIN.notesRender=function(){
  const c=SKIN.notesCtx;if(!c)return;
  const host=skQS(c.m,'.drawer-body');if(!host)return;
  host.innerHTML=SKIN.notesHTML(c.tab);
  skEach(skQSA(c.m,'[data-tab]'),b=>b.classList.toggle('on',skAttr(b,'data-tab','')===c.tab));
  skPage(host);
};
SKIN.manual=function(){
  SKIN.hideCtx();SKIN.hideRadial();
  const tabs=['The loop','The city','Glossary','Keys'];
  UI.openModal({title:'Field notes',sub:'A quiet guide to the city',wide:true,
    body:'<div class="settings-shell"><div class="settings-tabs">'+tabs.map((t,i)=>'<button data-sk="notes:tab" data-tab="'+t+'" class="'+(i===0?'on':'')+'">'+t+'</button>').join('')+'</div><div class="drawer-body"></div></div>',
    footer:'<span class="tiny dim" style="flex:1">This is a work of fiction. All goods, places and crews are invented.</span><button class="btn" data-sk="notes:tour">Guided tour</button><button class="btn primary" data-mclose>Got it</button>',
    onMount:(m,close)=>{m.classList.add('notes-sheet');SKIN.notesCtx={m:m,close:close,tab:'The loop'};SKIN.notesRender();}});
};

/* ---------- journal ---------- */
SKIN.journalHTML=function(tab){
  if(!S)return'<div class="journal-empty">Begin a story and the city will start keeping notes.</div>';
  const line=(t,tag,text)=>'<div class="journal-entry"><div class="je-t">'+fmtTick(t)+(tag?' · '+esc(tag):'')+'</div><div class="je-b">'+esc(text)+'</div></div>';
  if(tab==='Street talk'){
    const a=(S.news||[]).slice(0,18).map(n=>line(n.t,n.tag,n.text));
    return(a.length?a.join(''):'<div class="journal-empty">Nothing on the wire yet.</div>')+'<div class="city-quote">“A city is mostly things that happened while nobody was writing them down.”<small>— a note left on the desk</small></div>';
  }
  if(tab==='Ledger'){
    const a=(S.log||[]).slice(0,24).map(n=>line(n.t,n.type,n.text));
    return a.length?a.join(''):'<div class="journal-empty">No transactions recorded yet.</div>';
  }
  const W=S.world;
  const a=W&&W.log?W.log.slice(0,24).map(n=>line(n.t,n.kind,n.text)):[];
  return (a.length?a.join(''):'<div class="journal-empty">The city is keeping its own counsel.</div>')+
    '<div class="tip-card" style="margin-top:12px"><div class="th">Behind the ledger</div><div class="tb">These are quiet things the simulation tracks every hour. Most players never need to read them; they only make the world behave like a place with its own memory.</div></div>';
};
SKIN.journalRender=function(){
  const c=SKIN.journalCtx;if(!c)return;
  const host=skQS(c.m,'.drawer-body');if(!host)return;
  host.innerHTML=SKIN.journalHTML(c.tab);
  skEach(skQSA(c.m,'[data-tab]'),b=>b.classList.toggle('on',skAttr(b,'data-tab','')===c.tab));
  skPage(host);
};
SKIN.journal=function(){
  SKIN.hideCtx();SKIN.hideRadial();
  const tabs=['Street talk','Ledger','City notes'];
  UI.openModal({title:'Journal',sub:'What the city has been saying',wide:true,
    body:'<div class="journal-shell"><div class="drawer-tabs">'+tabs.map((t,i)=>'<button data-sk="journal:tab" data-tab="'+t+'" class="'+(i===0?'on':'')+'">'+t+'</button>').join('')+'</div><div class="drawer-body"></div></div>',
    footer:'<span class="tiny dim" style="flex:1">Recent only. The full ledger lives in its own view.</span><button class="btn primary" data-mclose>Close</button>',
    onMount:(m,close)=>{m.classList.add('journal-sheet');SKIN.journalCtx={m:m,close:close,tab:'Street talk'};SKIN.journalRender();}});
};

/* ---------- pause sheet ---------- */
SKIN.pauseStats=function(){
  const q=[
    ['In-game time',skPrettyTime(S.tick)],['Net worth',fmtC(netWorth())],
    ['Attention',fmtN(S.heat,1)],['Story seed',hashStr(String(S.seed)).slice(0,6).toUpperCase()],
    ['Deliveries',fmtN(S.stats.deliveries)],['Units moved',fmtN(S.stats.unitsSold,1)+'u']
  ];
  return'<div class="pause-stats">'+q.map(x=>'<div class="card"><div class="cap">'+x[0]+'</div><div class="num" style="font-size:14px;margin-top:4px">'+x[1]+'</div></div>').join('')+'</div>';
};
SKIN.pauseDetail=function(tab){
  const c=SKIN.pauseCtx;if(!c||!S)return;
  const map={
    resume:['The evening is on hold','The city is frozen. Nothing moves until you say so.','<button class="btn primary" data-sk="pause:resume">Resume</button><button class="btn" data-sk="pause:save">Save story</button>'],
    save:['Save this story','Write the current hour to the rolling autosave, or choose a manual slot.','<button class="btn primary" data-sk="pause:save">Save now</button><button class="btn" data-sk="pause:load">Saved stories</button>'],
    load:['Saved stories','Three places to keep a turning point. Loading replaces the current hour.','<button class="btn primary" data-sk="pause:load">Browse saves</button>'],
    settings:['Options','Sound, motion, keys and saved data. Changes are kept on this machine.','<button class="btn primary" data-sk="pause:settings">Open options</button>'],
    notes:['Field notes','The loop, the city, the words and the keys — without the noise.','<button class="btn primary" data-sk="pause:notes">Open field notes</button>'],
    world:['Behind the ledger','A glimpse of the private lives moving under the visible numbers.','<button class="btn primary" data-sk="pause:world">Look closer</button>'],
    journal:['Journal','Street talk, money in and out, and the city’s quieter notes.','<button class="btn primary" data-sk="pause:journal">Open journal</button>'],
    new:['A new story','A fresh seed grows a fresh city. The current run stays in its save slots.','<button class="btn primary" data-sk="pause:new">Begin fresh</button>'],
    title:['Title screen','Step away from the desk. Your autosave waits here.','<button class="btn primary" data-sk="pause:title">Return to title</button>']
  };
  const q=map[tab]||map.resume;
  const host=skQS(c.m,'.pause-detail');if(!host)return;
  host.innerHTML='<div class="pd-title">'+q[0]+'</div><div class="pd-sub">'+q[1]+'</div>'+SKIN.pauseStats()+'<div class="pd-actions">'+q[2]+'</div>'+
    '<div class="city-quote">“Every hour is a small decision. The rest is just weather.”<small>— the ledger, margin note</small></div>';
  skEach(skQSA(c.m,'[data-sk^="pause:tab"]'),b=>b.classList.toggle('primary',skAttr(b,'data-tab','')===tab));
  skPage(host);c.tab=tab;
};
SKIN.pauseMenu=function(){
  if(!S||!skEl('boot')||!skEl('boot').classList.contains('hidden'))return;
  S.paused=true;UI.renderTop();SKIN.hideCtx();SKIN.hideRadial();
  const nav=[['resume','Resume','Space'],['save','Save story','S'],['load','Saved stories',''],['settings','Options',''],['notes','Field notes','?'],['world','Behind the ledger','F3'],['journal','Journal','J'],['new','New story',''],['title','Title screen','']];
  UI.openModal({title:'The evening is on hold',sub:'Paused · '+skPrettyTime(S.tick),wide:true,
    body:'<div class="pause-nav">'+nav.map(q=>'<button class="pn '+(q[0]==='resume'?'primary':'')+'" data-sk="pause:tab" data-tab="'+q[0]+'">'+q[1]+'<small>'+q[2]+'</small></button>').join('')+'</div><div class="pause-detail"></div>',
    footer:'<button class="btn" data-sk="pause:notes">Field notes</button><span class="spacer"></span><button class="btn primary" data-sk="pause:resume">Resume</button>',
    onMount:(m,close)=>{
      m.classList.add('pause');if(m.parentNode)m.parentNode.classList.add('game-overlay');
      SKIN.pauseCtx={m:m,close:close,tab:'resume'};SKIN.pauseDetail('resume');
    }});
};

/* ---------- new story sheet ---------- */
SKIN.startHTML=function(){
  const opts=[['4200','Comfortable','A little room to make mistakes.'],['3200','Standard','The intended opening hand.'],['1800','Lean','Every early choice matters.'],['900','Bare start','For players who like a hard first week.']];
  return'<div class="start-grid"><div>'+
    '<div class="field" style="margin-bottom:12px"><label>World seed · leave blank for a new city</label><input class="inp" id="ng-seed" placeholder="A word, a number, a date…"></div>'+
    '<div class="field"><label>Starting hand</label><select id="ng-cash">'+opts.map(o=>'<option value="'+o[0]+'"'+(o[0]==='3200'?' selected':'')+'>'+o[1]+' · '+fmtC(+o[0])+'</option>').join('')+'</select></div>'+
    '<div class="diff-grid">'+opts.map(o=>'<button class="diff-card '+(o[0]==='3200'?'on':'')+'" data-sk="start:diff" data-v="'+o[0]+'"><div class="dt">'+o[1]+'</div><div class="ds">'+fmtC(+o[0])+' · '+o[2]+'</div></button>').join('')+'</div>'+
    '</div><div class="start-side"><div class="ss-t">One seed, one city</div><div class="ss-b">The same opening choice always grows into the same streets, people and weather. Change the seed and you change the whole story.</div><div class="ss-r"></div><div class="ss-f">Seven districts · eight invented goods · people with their own routines.<br><br>Everything runs offline. Nothing here describes a real-world procedure.</div></div></div>'+
    '<div class="notice" style="margin-top:12px">Your first evening begins paused. Read the desk, then press Space when you are ready.</div>';
};
SKIN.startRender=function(){
  const c=SKIN.startCtx;if(!c)return;
  const host=skQS(c.m,'.drawer-body');if(!host)return;
  host.innerHTML=SKIN.startHTML();skPage(host);
};
SKIN.newGame=function(){
  SKIN.hideCtx();SKIN.hideRadial();
  UI.openModal({title:'Begin a new story',sub:'Choose the city you want to meet',wide:true,
    body:'<div class="drawer-body"></div>',
    footer:'<button class="btn" data-sk="start:cancel">Back</button><span class="spacer"></span><button class="btn primary" data-sk="start:begin">Begin the story</button>',
    onMount:(m,close)=>{
      m.classList.add('start-sheet');SKIN.startCtx={m:m,close:close};SKIN.startRender();
      if(m.addEventListener)m.addEventListener('change',e=>{
        if(e.target&&e.target.id==='ng-cash'){
          skEach(skQSA(m,'[data-sk="start:diff"]'),b=>b.classList.toggle('on',skAttr(b,'data-v','')===String(e.target.value)));
        }
      });
    }});
};

/* ---------- clean archive intro ---------- */
SKIN.systemsIntro=function(){
  const W=S&&S.world?S.world:null;
  const hours=W&&W.stats?W.stats.hours:0;
  const acts=W&&W.stats?W.stats.npcActions:0;
  return'<div class="sys-intro"><section class="panel" style="margin-bottom:12px"><div class="panel-h"><span class="cap">The city today</span><span class="spacer"></span><span class="idx">a quiet place with a long memory</span></div><div class="panel-b">'+
    '<div class="clean-intro">'+
    '<div class="card"><div class="ci-num">7</div><div><div class="ci-t">Districts</div><div class="ci-s">Each has its own mood, wealth and appetite.</div></div></div>'+
    '<div class="card"><div class="ci-num">24h</div><div><div class="ci-t">Private routines</div><div class="ci-s">People sleep, work, meet and remember.</div></div></div>'+
    '<div class="card"><div class="ci-num">'+fmtN(acts)+'</div><div><div class="ci-t">Small choices</div><div class="ci-s">Quiet decisions made behind the ledger over '+fmtN(hours)+' hours.</div></div></div>'+
    '</div><div class="city-quote">“You will never see most of this city. That is rather the point.”<small>— from the field notes</small></div>'+
    '<div class="row wrap" style="margin-top:12px;gap:7px"><button class="btn primary" data-sk="misc:world">Look behind the ledger</button><button class="btn" data-sk="misc:density">Show the deeper numbers</button><button class="btn ghost" data-sk="misc:journal">Read the journal</button></div>'+
    '</div></section></div>';
};

/* ---------- action dispatcher ---------- */
SKIN.handleSk=function(act,n,e){
  const i=parseInt(skAttr(n,'data-i','0'),10)||0;
  const op=skAttr(n,'data-op','');
  const tab=skAttr(n,'data-tab','');
  const k=skAttr(n,'data-k','');
  const v=skAttr(n,'data-v','');
  const bind=skAttr(n,'data-bind','');
  switch(act){
    /* radial */
    case'radial:close':SKIN.hideRadial();break;
    case'radial:desk':SKIN.hideRadial();UI.setView('overview');break;
    case'radial:market':SKIN.hideRadial();UI.setView('market');break;
    case'radial:ops':SKIN.hideRadial();UI.setView('operations');break;
    case'radial:save':SKIN.hideRadial();if(S)UI.save(true);break;
    case'radial:city':SKIN.hideRadial();if(S)UI.worldLens();break;
    case'radial:notes':SKIN.hideRadial();UI.manual();break;
    /* context */
    case'ctx:market':SKIN.hideCtx();UI.setView('market');break;
    case'ctx:save':SKIN.hideCtx();if(S)UI.save(true);else UI.toast('Nothing to save','Begin a story first.','warn');break;
    case'ctx:detail':SKIN.hideCtx();UI.toggleDensity();break;
    case'ctx:notes':SKIN.hideCtx();UI.manual();break;
    case'ctx:world':SKIN.hideCtx();if(S)UI.worldLens();break;
    case'ctx:journal':SKIN.hideCtx();SKIN.journal();break;
    case'ctx:wheel':SKIN.hideCtx();SKIN.toggleRadial();break;
    case'ctx:options':SKIN.hideCtx();UI.settings();break;
    case'ctx:pause':SKIN.hideCtx();UI.pauseMenu();break;
    /* pause */
    case'pause:tab':SKIN.pauseDetail(tab);break;
    case'pause:resume':skClose('pauseCtx');if(S){S.paused=false;UI.renderTop();UI.sfx('click');}break;
    case'pause:save':if(S)UI.save(true);SKIN.pauseDetail('save');break;
    case'pause:load':skClose('pauseCtx');SKIN.loadScreen();break;
    case'pause:settings':skClose('pauseCtx');UI.settings();break;
    case'pause:notes':skClose('pauseCtx');UI.manual();break;
    case'pause:world':skClose('pauseCtx');if(S)UI.worldLens();break;
    case'pause:journal':skClose('pauseCtx');SKIN.journal();break;
    case'pause:new':skClose('pauseCtx');UI.newGameModal();break;
    case'pause:title':skClose('pauseCtx');UI.toTitle();break;
    /* settings */
    case'settings:tab':if(SKIN.settingsCtx){SKIN.settingsCtx.tab=tab;SKIN.settingsRender();}break;
    case'settings:toggle':if(SKIN.settingsCtx){const c=SKIN.settingsCtx.cfg;c[k]=k==='density'?(c[k]==='clean'?'analyst':'clean'):!c[k];SKIN.persistCfg(c);if(k==='density'&&S)UI.applyDensity();if(S)UI.render(true);SKIN.settingsRender();}break;
    case'settings:speed':if(S){S.speed=+v;S.paused=false;UI.renderTop();}if(SKIN.settingsCtx)SKIN.settingsRender();break;
    case'settings:bind':SKIN.listening=bind;if(SKIN.settingsCtx)SKIN.settingsRender();break;
    case'settings:defaults':SKIN.resetBindings();SKIN.listening=null;if(SKIN.settingsCtx)SKIN.settingsRender();UI.toast('Defaults restored','Keys are back to their original places.','good');break;
    case'settings:done':skClose('settingsCtx');UI.toast('Options saved','Preferences are kept on this machine.','good');break;
    case'settings:save':skClose('settingsCtx');if(S)UI.save(true);else UI.toast('Nothing to save','Begin a story first.','warn');break;
    case'settings:load':skClose('settingsCtx');SKIN.loadScreen();break;
    case'settings:export':skClose('settingsCtx');if(S)UI.exportSave();else UI.toast('Nothing to copy','Begin a story first.','warn');break;
    case'settings:import':skClose('settingsCtx');UI.importSave();break;
    case'settings:new':skClose('settingsCtx');UI.newGameModal();break;
    case'settings:reset':skClose('settingsCtx');UI.confirm('Erase everything?','This removes the rolling save, all manual slots and your preferences. Copies you made elsewhere are untouched.','Erase',()=>{
      try{localStorage.removeItem('nightledger.save');localStorage.removeItem('nightledger.settings');for(let q=1;q<3;q++)localStorage.removeItem('nightledger.slot'+q);localStorage.removeItem(SKIN.metaKey);}catch(e){}
      SKIN.updateBootInfo();UI.toast('Local data erased','Returning to the title screen.','warn');setTimeout(()=>UI.toTitle(),350);
    },'Keep my stories');break;
    /* notes */
    case'notes:tab':if(SKIN.notesCtx){SKIN.notesCtx.tab=tab;SKIN.notesRender();}break;
    case'notes:tour':skClose('notesCtx');UI.tutorial();break;
    case'notes:world':skClose('notesCtx');if(S)UI.worldLens();break;
    /* journal */
    case'journal:tab':if(SKIN.journalCtx){SKIN.journalCtx.tab=tab;SKIN.journalRender();}break;
    /* load */
    case'load:slot':if(op==='load')SKIN.loadSlot(i);else SKIN.saveSlot(i);break;
    /* start */
    case'start:diff':if(SKIN.startCtx){const sel=skQS(SKIN.startCtx.m,'#ng-cash');if(sel)sel.value=v;skEach(skQSA(SKIN.startCtx.m,'[data-sk="start:diff"]'),b=>b.classList.toggle('on',skAttr(b,'data-v','')===v));}break;
    case'start:cancel':skClose('startCtx');break;
    case'start:begin':{
      const c=SKIN.startCtx;if(!c)break;
      const seedEl=skQS(c.m,'#ng-seed'),cashEl=skQS(c.m,'#ng-cash');
      const raw=seedEl?String(seedEl.value||'').trim():'';
      let seed=raw?(/^\d+$/.test(raw)?(+raw>>>0):parseInt(hashStr(raw).slice(0,8),16)):undefined;
      if(!Number.isFinite(seed))seed=undefined;
      const cash=cashEl?+cashEl.value:3200;
      const settings=UI.readStoredSettings();
      S=NL.newGame(seed,{cash:cash,settings:settings});
      S.lastSaveTick=0;
      skClose('startCtx');
      const b=skEl('boot');if(b)b.classList.add('hidden');
      UI.applyDensity();UI.closeAllModals();UI.render(true);UI.save();SKIN.sweep();SKIN.updateBootInfo();
      UI.toast('A new story begins','Seed '+hashStr(String(S.seed)).slice(0,6).toUpperCase()+' · '+fmtC(cash)+' to start.','good');
      if(!S.settings.tutorialDone&&typeof setTimeout!=='undefined')setTimeout(()=>UI.tutorial(),700);
      break;
    }
    /* misc */
    case'misc:world':if(S)UI.worldLens();break;
    case'misc:density':UI.toggleDensity();break;
    case'misc:journal':SKIN.journal();break;
    case'misc:options':UI.settings();break;
    case'misc:pause':UI.pauseMenu();break;
    case'misc:save':if(S)UI.save(true);break;
    case'misc:load':SKIN.loadScreen();break;
    case'misc:new':UI.newGameModal();break;
    default:break;
  }
};

/* ---------- boot visuals ---------- */
SKIN.bootAnim=function(){
  const c=skEl('bootbg');if(!c||!c.getContext)return;
  let x;try{x=c.getContext('2d');}catch(e){return;}if(!x)return;
  let W=1280,H=720,buildings=[],dust=[];
  const cfg=skCfg();
  const resize=()=>{
    W=(typeof window!=='undefined'&&window.innerWidth)||c.clientWidth||1280;
    H=(typeof window!=='undefined'&&window.innerHeight)||c.clientHeight||720;
    c.width=W;c.height=H;c.style.width=W+'px';c.style.height=H+'px';
    buildings=[];let px=-20;
    while(px<W+40){const w=28+Math.random()*70,h=60+Math.random()*Math.min(260,H*.42);buildings.push({x:px,y:H-h-70,w:w,h:h,seed:Math.random()});px+=w+3+Math.random()*12;}
    dust=Array.from({length:70},()=>({x:Math.random()*W,y:Math.random()*H,s:.4+Math.random()*1.3,v:.05+Math.random()*.18,a:.05+Math.random()*.12}));
  };
  resize();
  if(typeof window!=='undefined'&&window.addEventListener)window.addEventListener('resize',resize);
  const can=k=>typeof x[k]==='function';
  const draw=t=>{
    try{
      if(can('clearRect'))x.clearRect(0,0,W,H);
      let sky;
      if(can('createLinearGradient')){sky=x.createLinearGradient(0,0,0,H);sky.addColorStop(0,'#2b2a29');sky.addColorStop(.55,'#1c2025');sky.addColorStop(1,'#121418');}
      x.fillStyle=sky||'#1a1d21';if(can('fillRect'))x.fillRect(0,0,W,H);
      if(can('createRadialGradient')){
        const g=x.createRadialGradient(W*.78,H*.25,10,W*.78,H*.25,Math.min(W,H)*.42);
        g.addColorStop(0,'rgba(217,161,91,.30)');g.addColorStop(.45,'rgba(207,139,92,.09)');g.addColorStop(1,'rgba(217,161,91,0)');
        x.fillStyle=g;x.fillRect(0,0,W,H);
      }
      if(can('beginPath')&&can('arc')&&can('fill')){
        x.beginPath();x.arc(W*.78,H*.23,26,0,7);x.fillStyle='rgba(232,199,145,.62)';x.fill();
        x.beginPath();x.arc(W*.78+9,H*.23-6,26,0,7);x.fillStyle='#252629';x.fill();
      }
      /* horizon glow */
      if(can('createLinearGradient')){const hg=x.createLinearGradient(0,H*.55,0,H*.88);hg.addColorStop(0,'rgba(201,162,95,0)');hg.addColorStop(1,'rgba(201,162,95,.10)');x.fillStyle=hg;x.fillRect(0,H*.55,W,H*.33);}
      /* skyline */
      for(const b of buildings){
        x.fillStyle='#16191d';if(can('fillRect'))x.fillRect(b.x,b.y,b.w,b.h);
        x.fillStyle='rgba(255,255,255,.025)';if(can('fillRect'))x.fillRect(b.x,b.y,b.w,1);
        for(let wy=b.y+9;wy<b.y+b.h-6;wy+=11){
          for(let wx=b.x+6;wx<b.x+b.w-6;wx+=10){
            const r=(Math.sin(b.seed*999+wx*13+wy*7)+1)/2;
            if(r>.63){x.fillStyle='rgba(217,161,91,'+(.10+r*.22)+')';if(can('fillRect'))x.fillRect(wx,wy,3,4);}
          }
        }
      }
      /* street */
      x.fillStyle='#101215';if(can('fillRect'))x.fillRect(0,H-70,W,70);
      if(can('stroke')){x.strokeStyle='rgba(201,162,95,.07)';x.lineWidth=1;for(let yy=H-62;yy<H;yy+=14){x.beginPath();x.moveTo(0,yy);x.lineTo(W,yy);x.stroke();}}
      /* drifting mist */
      if(can('fillRect')){
        for(let j=0;j<4;j++){
          const yy=H*.55+j*44+Math.sin(t*.12+j)*8;
          x.fillStyle='rgba(190,180,165,'+(.018+j*.006)+')';x.fillRect(0,yy,W,28);
        }
      }
      /* dust */
      for(const p of dust){
        p.y-=p.v;if(p.y<0){p.y=H;p.x=Math.random()*W;}
        x.fillStyle='rgba(232,199,145,'+p.a+')';if(can('fillRect'))x.fillRect(p.x,p.y,p.s,p.s);
      }
    }catch(e){}
  };
  if(typeof requestAnimationFrame==='function'&&SKIN.motionOK&&cfg.cinematic!==false){
    const start=Date.now();
    const frame=()=>{
      requestAnimationFrame(frame);
      const b=skEl('boot');if(b&&b.classList.contains('hidden'))return;
      draw((Date.now()-start)/1000);
    };
    frame();
  }else draw(0);
};
SKIN.bootLog=function(){
  const out=skEl('bootlog');if(!out||typeof document==='undefined'||!document.createElement)return;
  const lines=[
    'Lantern Row is closing early tonight.',
    'A thin rain is drifting over Meridian Quay.',
    'Two crews have changed shifts.',
    'Someone in Lowlight is telling a story.',
    'The night patrol turns at midnight.',
    'Vesper Hill is quiet after ten.',
    'The ledger is open and waiting.',
    'Your story can begin whenever you like.'
  ];
  let i=0;
  const add=()=>{
    if(i>=lines.length)return;
    if(!document.createElement)return;
    const d=document.createElement('div');d.textContent=lines[i++];out.appendChild(d);
    while(out.children&&out.children.length>8&&out.firstChild){
      const f=out.firstChild;
      if(f.parentNode&&f.parentNode.removeChild)f.parentNode.removeChild(f);else if(f.remove)f.remove();else break;
    }
    if(typeof setTimeout!=='undefined')setTimeout(add,150+Math.random()*170);
  };
  add();
};
SKIN.updateBootInfo=function(){
  const info=skEl('boot-saveinfo'),cont=skEl('boot-continue'),load=skEl('boot-load');
  let raw=null;try{raw=localStorage.getItem('nightledger.save');}catch(e){}
  if(raw){
    let o={};try{o=JSON.parse(raw)||{};}catch(e){}
    if(info)info.textContent=skPrettyTime(o.tick||0)+' · '+hashStr(String(o.seed||'')).slice(0,6).toUpperCase();
    if(cont)cont.disabled=false;
  }else{
    if(info)info.textContent='No saved story';if(cont)cont.disabled=true;
  }
  if(load)load.disabled=!SKIN.hasAnySave();
};

/* ---------- wrappers ---------- */
const _skinRenderTop=UI.renderTop;
UI.renderTop=function(){
  const ids=['s-cash','s-worth','s-heat','s-rep','s-terr'],before={};
  for(const id of ids){const n=skEl(id);if(n)before[id]=n.textContent;}
  const r=_skinRenderTop.apply(this,arguments);
  if(S){
    const w=WEATHER[S.weather]||WEATHER[0];
    const pretty=w.key.charAt(0)+w.key.slice(1).toLowerCase();
    skText('weatherchip',pretty);
    const c=skEl('weatherchip');if(c&&c.style)c.style.color=w.col;
    skText('clockday','Day '+String(S.day).padStart(2,'0')+' · '+(S.paused?'Paused':S.hour>=20||S.hour<6?'Evening':S.hour<12?'Morning':'Afternoon'));
    skText('s-heat-d',S.heat>70?'Too much notice':S.heat>45?'Getting warm':S.heat>20?'Worth watching':'Quiet');
    skText('s-rep-d','Standing '+Math.min(5,Math.floor(S.rep/20)+1));
    skText('s-terr-d',S.control.filter(q=>q>=.35).length+' districts on side');
    skText('crumb',({overview:'The desk',market:'Market',operations:'Operations',network:'Network',ledger:'Ledger',intel:'Outlook',systems:'Archive'})[UI.sel.view]||'The desk');
    skText('seedtag','Story '+hashStr(String(S.seed)).slice(0,6).toUpperCase());
    if(S.world)skText('st-world',(S.world.stats?S.world.stats.hours:0)+'h · '+(S.world.mods?S.world.mods.length:0)+' quiet effects');
    SKIN.ambient();SKIN.updateAlertBadge();
  }
  for(const id of ids){
    const n=skEl(id);if(n&&before[id]!==undefined&&n.textContent!==before[id]&&SKIN.motionOK){
      try{n.classList.remove('val-flash');void n.offsetWidth;n.classList.add('val-flash');}catch(e){}
    }
  }
  return r;
};
const _skinAutosave=UI.autosave;
UI.autosave=function(){
  const r=_skinAutosave.apply(this,arguments);
  const n=skEl('st-save');
  if(n&&S&&n.textContent.indexOf('FAILED')<0){n.textContent='Saved '+skPrettyTime(S.tick);n.style.color='var(--cy)';}
  return r;
};
const _skinRender=UI.render;
UI.render=function(force){const r=_skinRender.apply(this,arguments);SKIN.afterRender();return r;};
const _skinSetView=UI.setView;
UI.setView=function(v){const r=_skinSetView.apply(this,arguments);if(V[v]){SKIN.sweep();SKIN.hideCtx();SKIN.hideRadial();}return r;};
const _skinApplyDensity=UI.applyDensity;
UI.applyDensity=function(){const r=_skinApplyDensity.apply(this,arguments);SKIN.applyPrefs();return r;};
const _skinToTitle=UI.toTitle;
UI.toTitle=function(){const r=_skinToTitle.apply(this,arguments);SKIN.sweep();SKIN.hideRadial();SKIN.hideCtx();SKIN.updateBootInfo();return r;};
const _skinToggleFocus=UI.toggleFocus;
UI.toggleFocus=function(){const r=_skinToggleFocus.apply(this,arguments);const m=skEl('main');if(m&&m.style)m.style.gridTemplateColumns=UI.focusMode?'74px minmax(0,1fr)':'';SKIN.afterRender();return r;};
const _skinToggleMinimize=UI.toggleMinimize;
UI.toggleMinimize=function(){const r=_skinToggleMinimize.apply(this,arguments);const a=skEl('app');if(a&&a.style&&UI.minimized)a.style.gridTemplateRows='44px';return r;};
const _skinSystems=V.systems;
V.systems=function(){const out=_skinSystems();if(!S||S.settings.density==='analyst')return out;return'<div class="clean-systems">'+SKIN.systemsIntro()+out+'</div>';};

UI.pauseMenu=SKIN.pauseMenu;
UI.settings=SKIN.settings;
UI.manual=SKIN.manual;
UI.newGameModal=SKIN.newGame;
UI.loadScreen=SKIN.loadScreen;
UI.bootAnim=SKIN.bootAnim;
UI.bootLog=SKIN.bootLog;
UI.updateBootInfo=SKIN.updateBootInfo;

/* ---------- install DOM interactions ---------- */
SKIN.install=function(){
  if(typeof document==='undefined'||!document.getElementById||!document.addEventListener)return;
  SKIN.applyPrefs();SKIN.updateBootInfo();SKIN.ambient();
  const wire=(id,fn)=>{const n=skEl(id);if(n&&n.addEventListener)n.addEventListener('click',e=>{if(e.stopPropagation)e.stopPropagation();fn(e);});};
  wire('boot-load',()=>SKIN.loadScreen());
  wire('tbar-menu',()=>UI.pauseMenu());
  wire('tbar-journal',()=>SKIN.journal());
  document.addEventListener('keydown',SKIN.keyCapture,true);
  document.addEventListener('contextmenu',SKIN.showCtx);
  document.addEventListener('click',e=>{
    const target=e.target||null;
    const sk=target&&target.closest?target.closest('[data-sk]'):null;
    if(sk){
      if(e.stopImmediatePropagation)e.stopImmediatePropagation();
      SKIN.handleSk(skAttr(sk,'data-sk',''),sk,e);
    }
    if(SKIN.ctxOpen&&!(target&&target.closest&&target.closest('#ctx')))SKIN.hideCtx();
    if(SKIN.radialOpen&&!(target&&target.closest&&target.closest('#radial-wrap')))SKIN.hideRadial();
    if(SKIN.motionOK&&typeof e.clientX==='number'&&typeof e.clientY==='number'){
      const fx=skEl('click-fx');
      if(fx&&document.createElement){
        const dot=document.createElement('div');dot.className='click-dot';dot.style.left=e.clientX+'px';dot.style.top=e.clientY+'px';fx.appendChild(dot);
        setTimeout(()=>{if(dot.parentNode)dot.parentNode.removeChild(dot);else if(dot.remove)dot.remove();},580);
      }
      const btn=target&&target.closest?target.closest('.btn,.chip,.menu-item,.railbtn,.speedbtn,.winbtn,.tbar-btn'):null;
      if(btn&&btn.appendChild&&document.createElement){
        const rip=document.createElement('span');rip.className='ripple';
        const r=btn.getBoundingClientRect?btn.getBoundingClientRect():{left:0,top:0,width:60,height:30};
        const size=Math.max(r.width,r.height)*1.2;
        rip.style.width=size+'px';rip.style.height=size+'px';
        rip.style.left=(e.clientX-r.left-size/2)+'px';rip.style.top=(e.clientY-r.top-size/2)+'px';
        btn.appendChild(rip);setTimeout(()=>{if(rip.parentNode)rip.parentNode.removeChild(rip);else if(rip.remove)rip.remove();},580);
      }
    }
  },true);
  document.addEventListener('mousemove',e=>{
    if(typeof e.clientX!=='number'||typeof e.clientY!=='number')return;
    const ring=skEl('cursor-ring');
    if(ring&&ring.style){ring.style.transform='translate('+e.clientX+'px,'+e.clientY+'px)';ring.classList.add('live');}
    const n=e.target&&e.target.closest?e.target.closest('.panel,.card,.kpi'):null;
    if(n&&n.getBoundingClientRect&&n.style&&n.style.setProperty){
      const r=n.getBoundingClientRect();
      n.style.setProperty('--mx',((e.clientX-r.left)/r.width*100).toFixed(1)+'%');
      n.style.setProperty('--my',((e.clientY-r.top)/r.height*100).toFixed(1)+'%');
    }
  });
  if(document.addEventListener)document.addEventListener('mouseleave',()=>{const r=skEl('cursor-ring');if(r)r.classList.remove('live');});
  if(typeof window!=='undefined'&&window.addEventListener)window.addEventListener('blur',()=>{SKIN.hideCtx();SKIN.hideRadial();});
};
if(typeof document!=='undefined'&&document.getElementById&&document.getElementById('app')){
  try{SKIN.install();}catch(e){}
}
