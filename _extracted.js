/* PALETTE_NORMALIZED */
















'use strict';
/* =====================================================================================
   NIGHTLEDGER — ENGINE
   Deterministic, tick-driven (1 tick = 1 in-game hour) person/economy simulation.
   Everything below is pure data + math; the renderer never mutates state directly.
   ===================================================================================== */
(function(){
const G = globalThis;
const NL = {}; G.NL = NL;

/* ------------------------------ math / util ------------------------------ */
const PI=Math.PI;
const clamp=(v,a,b)=>v<a?a:(v>b?b:v);
const lerp=(a,b,t)=>a+(b-a)*t;
const r2=v=>Math.round(v*100)/100;
const r3=v=>Math.round(v*1000)/1000;
const sig=x=>1/(1+Math.exp(-clamp(x,-30,30)));
const mean=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:0;
const std=a=>{if(a.length<2)return 0;const m=mean(a);return Math.sqrt(a.reduce((s,v)=>s+(v-m)*(v-m),0)/(a.length-1));};
function fmtN(n,d){d=d===undefined?0:d;if(!isFinite(n))return'—';let s=Math.abs(n).toFixed(d);const p=s.split('.');p[0]=p[0].replace(/\B(?=(\d{3})+(?!\d))/g,',');return(n<0?'−':'')+p.join('.');}
const fmtC=(n,d)=>'¤'+fmtN(n,d===undefined?0:d);
const fmtP=(n,d)=>fmtN(n*100,d===undefined?0:d)+'%';
const fmtU=n=>fmtN(n,1)+'u';
function hashStr(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return(h>>>0).toString(16).padStart(8,'0');}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
const pick=a=>a[Math.floor(rnd()*a.length)];
const chance=p=>rnd()<p;
function fmtHour(h){return String(h).padStart(2,'0')+':00';}
function fmtTick(t){return'D'+String(Math.floor(t/24)+1).padStart(2,'0')+' '+String(t%24).padStart(2,'0')+'H';}

/* ------------------------------ static world ----------------------------- */
/* All compounds, organisations and places below are fictional game constructs. */
const PRODUCTS=[
 {key:'CINDER',code:'CDR',tier:1,base:34,vol:.105,decay:.0032,stick:.24,elast:1.35,color:'#c9a25f',blurb:'Entry-tier synthetic. High volume, thin margin, fast saturation.'},
 {key:'VELLUM',code:'VLM',tier:1,base:52,vol:.085,decay:.0026,stick:.30,elast:1.20,color:'#d9a15b',blurb:'Steady mid-low demand. Popular in dense residential blocks.'},
 {key:'Halo',code:'HLO',tier:2,base:96,vol:.130,decay:.0041,stick:.38,elast:1.05,color:'#c9a25f',blurb:'Premium grade. Price sensitive to reputation and purity.'},
 {key:'Kite',code:'KTE',tier:2,base:128,vol:.165,decay:.0050,stick:.33,elast:.95,color:'#c6766e',blurb:'Volatile, fashion-driven. Spikes during nightlife windows.'},
 {key:'Still',code:'STC',tier:2,base:78,vol:.190,decay:.0060,stick:.20,elast:1.45,color:'#c9a25f',blurb:'Erratic street commodity. Fast decay, strong word-of-mouth effect.'},
 {key:'LUMEN',code:'LMN',tier:3,base:212,vol:.120,decay:.0030,stick:.46,elast:.80,color:'#7f9c72',blurb:'High-purity boutique good. Wealthy districts only.'},
 {key:'Onyx',code:'ONX',tier:3,base:305,vol:.145,decay:.0024,stick:.52,elast:.72,color:'#7f9bb5',blurb:'Rare, high-margin. Requires grade-A refining and discreet channels.'},
 {key:'Mirror',code:'MRR',tier:4,base:470,vol:.210,decay:.0018,stick:.58,elast:.65,color:'#c9a25f',blurb:'Experimental tier. Tiny market, extreme volatility, huge spreads.'}
];
const NP=PRODUCTS.length;
const MARKET_SCALE=14; /* converts the latent demand index into tradeable units/hour */
const DISTRICTS=[
 {key:'Docklands',short:'Docks',x:.11,y:.70,pop:1.18,wealth:.70,risk:.58,bias:[1.32,.95,.55,.44,1.18,.28,.18,.08]},
 {key:'Lantern Row',short:'Lantern',x:.27,y:.41,pop:.96,wealth:.58,risk:.44,bias:[1.05,1.30,.72,.62,1.05,.36,.20,.07]},
 {key:'Grid North',short:'Grid North',x:.47,y:.16,pop:1.26,wealth:.90,risk:.31,bias:[.78,.92,1.18,1.32,.86,.82,.48,.20]},
 {key:'Vesper Hill',short:'Vesper',x:.74,y:.20,pop:.76,wealth:1.48,risk:.24,bias:[.38,.52,1.28,.98,.42,1.52,1.30,.62]},
 {key:'The Spine',short:'Spine',x:.53,y:.53,pop:1.42,wealth:1.02,risk:.48,bias:[1.00,1.00,1.00,1.10,1.12,.90,.62,.28]},
 {key:'Lowlight',short:'Lowlight',x:.20,y:.86,pop:1.08,wealth:.44,risk:.70,bias:[1.48,1.22,.48,.36,1.42,.22,.10,.04]},
 {key:'Meridian Quay',short:'Meridian',x:.84,y:.70,pop:.92,wealth:1.22,risk:.38,bias:[.62,.78,1.12,1.24,.66,1.26,1.08,.48]}
];
const ND=DISTRICTS.length;
const EDGES=[[0,1],[0,5],[0,6],[1,2],[1,4],[1,5],[2,3],[2,4],[3,4],[3,6],[4,5],[4,6],[5,6],[1,0]];
const WEATHER=[
 {key:'Clear',dem:1.00,risk:1.00,speed:1.00,col:'#c6766e'},
 {key:'Overcast',dem:1.04,risk:.92,speed:1.00,col:'#d9a15b'},
 {key:'Rain',dem:.88,risk:.82,speed:1.22,col:'#c9a25f'},
 {key:'Fog',dem:.94,risk:.74,speed:1.30,col:'#c9a25f'},
 {key:'Storm',dem:.72,risk:.65,speed:1.55,col:'#c9a25f'}
];
const WTRANS=[
 [.72,.16,.07,.04,.01],[.30,.48,.15,.06,.01],[.18,.28,.38,.13,.03],[.22,.24,.20,.30,.04],[.10,.22,.28,.24,.16]
];
const TOD=[.44,.34,.28,.24,.26,.38,.62,.88,1.02,.94,.88,.92,1.00,1.04,1.00,1.02,1.08,1.18,1.34,1.48,1.52,1.38,1.10,.72];
const TRAITS={
 cautious:{key:'Cautious',wtp:.94,haggle:.7,qty:.85,patience:1.3,heat:.75,loyalty:1.15,col:'#c6766e'},
 impulsive:{key:'Impulsive',wtp:1.16,haggle:.4,qty:1.05,patience:.65,heat:1.25,loyalty:.85,col:'#c9a25f'},
 loyal:{key:'Loyal',wtp:1.00,haggle:.8,qty:1.10,patience:1.2,heat:.85,loyalty:1.45,col:'#7f9c72'},
 haggler:{key:'Haggler',wtp:.88,haggle:1.6,qty:1.15,patience:1.4,heat:.9,loyalty:.9,col:'#d9a15b'},
 volume:{key:'Volume',wtp:.96,haggle:1.0,qty:2.10,patience:1.0,heat:1.35,loyalty:1.0,col:'#c9a25f'},
 discreet:{key:'Discreet',wtp:1.08,haggle:.6,qty:.70,patience:1.1,heat:.55,loyalty:1.2,col:'#c9a25f'}
};
const FIRST=['Arlo','Sable','Nix','Mira','Corin','Vale','Dessa','Kev','Orin','Talia','Bram','Suri','Halden','Jun','Rook','Esme','Pell','Wren','Ada','Cass','Ivo','Lux','Maren','Teo','Fenn','Zola','Basil','Nell','Odis','Rue'];
const LAST=['Vance','Kestrel','Dorne','Ashby','Quill','Marlow','Sable','Fen','Redd','Okonkwo','Voss','Lind','Merek','Shaw','Pike','Hallow','Cray','Noor','Vega','Black','Ives','Sato','Wilder','Moss','Dell','Kane','Frost','Arden'];
const UPGRADES=[
 {id:'lab',key:'Refining Rig',max:5,base:1300,mult:1.85,desc:'Raises max purity, throughput and yield for every refining job.',col:'#c9a25f'},
 {id:'vault',key:'Safehouse',max:5,base:900,mult:1.70,desc:'Warehouse capacity, stock protection and slower lot decay.',col:'#c6766e'},
 {id:'intel',key:'Intel Desk',max:5,base:1000,mult:1.75,desc:'Sharper price signals, better offers, more analysis points per hour.',col:'#c9a25f'},
 {id:'cover',key:'Front Company',max:5,base:1500,mult:1.90,desc:'Hourly reconciliation capacity and a lower effective fee.',col:'#7f9c72'},
 {id:'logistics',key:'Logistics',max:5,base:1100,mult:1.80,desc:'Courier speed, payload and lower travel complications.',col:'#d9a15b'},
 {id:'counsel',key:'Compliance Desk',max:5,base:1400,mult:1.85,desc:'Faster heat decay and reduced audit severity.',col:'#c9a25f'}
];
const RESEARCH=[
 {id:'r1',key:'Elasticity Models',cost:18,points:0,req:[],desc:'Reveal true demand elasticity in market curves; +3% passive sales.'},
 {id:'r2',key:'Process Control',cost:34,points:0,req:['r1'],desc:'+8% refining yield, +0.03 purity ceiling.'},
 {id:'r3',key:'Signal Filtering',cost:42,points:0,req:['r1'],desc:'Intel noise halved; forecast bands tighten by 20%.'},
 {id:'r4',key:'Cold Chain',cost:56,points:0,req:['r2'],desc:'Lot decay reduced 45%; high grades stay viable longer.'},
 {id:'r5',key:'Route Optimisation',cost:64,points:0,req:['r2'],desc:'Dijkstra routing with live congestion; courier ETA −20%.'},
 {id:'r6',key:'Behavioural Pricing',cost:78,points:0,req:['r3'],desc:'Better counter-offer odds; +6% willingness-to-pay estimate.'},
 {id:'r7',key:'Distributed Ledger',cost:96,points:0,req:['r3'],desc:'Settling up capacity +60%, fee −2%.'},
 {id:'r8',key:'Deep Cover',cost:120,points:0,req:['r6','r7'],desc:'Attention generation −25%, audit threshold +8.'}
];
const Happenings=[
 {key:'Demand surge',w:12,type:'demand',mag:[1.25,1.70],dur:[6,16],tone:'good',text:'A local craze pushes street demand sharply higher.'},
 {key:'Supply glut',w:9,type:'supply',mag:[1.30,1.90],dur:[8,20],tone:'bad',text:'Rival flooding depresses the clearing price.'},
 {key:'Scrutiny sweep',w:8,type:'heat',mag:[4,11],dur:[8,18],tone:'bad',text:'Increased oversight in the district. Attention decays slower.'},
 {key:'Night festival',w:7,type:'demand',mag:[1.20,1.55],dur:[5,12],tone:'good',text:'Crowds, music and long hours: nightlife goods spike.'},
 {key:'Feedstock shortage',w:7,type:'feed',mag:[1.25,1.85],dur:[10,24],tone:'bad',text:'Wholesale inputs become scarce and expensive.'},
 {key:'Market correction',w:8,type:'price',mag:[.76,.92],dur:[6,14],tone:'bad',text:'Speculative positions unwind; prices correct downward.'},
 {key:'Client referral',w:9,type:'rep',mag:[2,6],dur:[1,1],tone:'good',text:'Word of mouth brings a new contact into the network.'},
 {key:'Price war',w:6,type:'rival',mag:[1.0,1.6],dur:[10,22],tone:'bad',text:'A syndicate undercuts the street price aggressively.'},
 {key:'Blackout',w:5,type:'demand',mag:[1.15,1.45],dur:[3,8],tone:'good',text:'Grid failure drives discreet, cash-only commerce.'},
 {key:'Customs delay',w:5,type:'supply',mag:[.55,.80],dur:[8,18],tone:'good',text:'Rival shipments stall; local supply tightens.'},
 {key:'Quiet tip',w:6,type:'intel',mag:[1,3],dur:[1,1],tone:'good',text:'An informant reveals a profitable pricing gap.'},
 {key:'Inspection notice',w:5,type:'heat',mag:[8,16],dur:[4,10],tone:'bad',text:'A formal notice raises district scrutiny immediately.'}
];
const OBJECTIVES=[
 {id:'o1',key:'First drop',desc:'Complete your first courier delivery.',reward:400,check:s=>s.stats.deliveries>=1},
 {id:'o2',key:'Clean twelve',desc:'Reach ¤12,000 net worth.',reward:700,check:s=>netWorth(s)>=12000},
 {id:'o3',key:'Grade A',desc:'Refine a lot above 92% purity.',reward:900,check:s=>s.lots.some(l=>l.purity>=.92)},
 {id:'o4',key:'Three flags',desc:'Hold 35%+ influence in three districts.',reward:1400,check:s=>s.control.filter(c=>c>=.35).length>=3},
 {id:'o5',key:'Quiet week',desc:'Keep global heat under 18 for 48 consecutive hours.',reward:1200,check:s=>s.stats.quietStreak>=48},
 {id:'o6',key:'Inner circle',desc:'Have 8 clients above 70% loyalty.',reward:1600,check:s=>s.clients.filter(c=>c.loyalty>=.7).length>=8},
 {id:'o7',key:'Forty grand',desc:'Reach ¤40,000 net worth.',reward:2500,check:s=>netWorth(s)>=40000},
 {id:'o8',key:'The long game',desc:'Build four lasting contacts and hold sway across the city.',reward:6000,check:s=>Object.keys(s.research).length>=4&&mean(s.control)>=.50}
];

/* ------------------------------ chance thread (mulberry32) ------------------------ */
let S=null;
function seedRng(seed){S.rs=seed>>>0;S.spare=null;}
function rnd(){S.rs=(S.rs+0x6D2B79F5)|0;let t=S.rs;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;}
function nrm(){if(S.spare!==null&&S.spare!==undefined){const v=S.spare;S.spare=null;return v;}let u=0,v=0;while(u===0)u=rnd();while(v===0)v=rnd();const m=Math.sqrt(-2*Math.log(u));S.spare=m*Math.sin(2*PI*v);return m*Math.cos(2*PI*v);}
function poisson(l){if(l>30)return Math.max(0,Math.round(l+Math.sqrt(l)*nrm()));const L=Math.exp(-l);let k=0,p=1;do{k++;p*=rnd();}while(p>L);return k-1;}
function rr(a,b){return a+(b-a)*rnd();}
function ri(a,b){return Math.floor(rr(a,b+1));}
/* Isolated chance for forecasts (does not touch world state) */
function makeRng(seed){let s=seed>>>0,sp=null;const f=()=>{s=(s+0x6D2B79F5)|0;let t=s;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};return{next:f,norm:()=>{if(sp!==null){const v=sp;sp=null;return v;}let u=1e-9+f(),v=1e-9+f();const m=Math.sqrt(-2*Math.log(u));sp=m*Math.sin(2*PI*v);return m*Math.cos(2*PI*v);}};}

/* ------------------------------ world creation --------------------------- */
function newGame(seed,opts){
  opts=opts||{};
  seed=(seed===undefined||seed===null)?(Math.floor(Math.random()*4294967295)>>>0):(seed>>>0);
  S={
    version:2411,seed,rs:seed,spare:null,tick:0,hour:8,day:1,speed:1,paused:true,
    weather:0,wTimer:0,season:0,macro:1,macroTarget:1,mood:1,scrutiny:.18,
    cash:opts.cash||3200,debt:0,dirty:0,rep:12,heat:8,control:Array(ND).fill(.09),
    settings:Object.assign({density:'clean',sound:true,autopause:true,autosave:true,tutorialDone:false,showRoutes:true,showAttention:false},opts.settings||{}),
    upgrades:{lab:1,vault:1,intel:1,cover:1,logistics:1,counsel:1},
    mods:{},research:{},points:0,pointsRate:.42,
    prod:PRODUCTS.map(()=>({volState:0,shock:1,shockT:0})),
    districts:DISTRICTS.map((d,i)=>({
      demand:Array(NP).fill(0),price:Array(NP).fill(0),lastPrice:Array(NP).fill(0),
      rival:Array(NP).fill(0),sat:Array(NP).fill(0),heat:4+i,loyalty:.18+i*.012,
      scrutiny:.2+spr(i),volume:Array(NP).fill(0),lastSale:Array(NP).fill(0),events:[]
    })),
    depot:Array.from({length:ND},()=>Array.from({length:NP},()=>({qty:0,purity:.70,cost:0}))),
    listings:Array.from({length:ND},()=>Array.from({length:NP},()=>({qty:0,ask:0,mode:'manual',enabled:false}))),
    lots:[],jobs:[],couriers:[],clients:[],rivals:[],offers:[],contracts:[],feed:{base:180,additive:90,packs:120},
    feedPrice:{base:7.2,additive:11.0,packs:1.4},feedTarget:{base:7.2,additive:11.0,packs:1.4},
    ledger:[],log:[],news:[],objectives:{},achievements:[],activeEvents:[],
    history:{cash:[],worth:[],heat:[],rep:[],dirty:[],volume:[],price:[],demand:[]},
    forecast:null,forecastAt:-999,
    stats:{deliveries:0,completedJobs:0,sales:0,unitsSold:0,revenue:0,costs:0,fines:0,audits:0,offersAccepted:0,offersFailed:0,quietStreak:0,maxWorth:3200,ticks:0,seizures:0},
    diag:{solverIter:0,agentUpdates:0,eventQueue:0,entropy:0,hash:'—',lastMs:0,audits:0},
    nextId:1,cooldown:0,auditCd:0,contractCd:12,eventBus:[],gameOver:null,won:false,tickVolume:0,activity:0,
    pnls:Array.from({length:NP},()=>({rev:0,cost:0,units:0})),
    districtPnl:Array(ND).fill(0),autoRecon:true,autoPrice:{},lastSaveTick:0
  };
  function spr(i){return((i*2654435761)%17)/100;}
  seedRng(seed);
  /* initial market equilibrium */
  for(let d=0;d<ND;d++){
    const D=S.districts[d],base=DISTRICTS[d];
    for(let p=0;p<NP;p++){
      D.demand[p]=base.pop*base.bias[p]*rr(.85,1.15);
      D.rival[p]=Math.max(.4,D.demand[p]*rr(.6,1.25));
      D.price[p]=equilibrium(d,p,D.demand[p],D.rival[p]);
      D.lastPrice[p]=D.price[p];
    }
  }
  /* starting stock: three heterogeneous lots */
  S.lots=[
    mkLot(0,42,.71,22,.0),mkLot(1,26,.78,38,.0),mkLot(4,14,.66,52,.0)
  ];
  /* starting crews */
  S.couriers=[mkCourier(),mkCourier()];
  /* starting network */
  for(let i=0;i<15;i++)S.clients.push(mkClient(i));
  /* rivals */
  S.rivals=[
    {id:'Vantage',name:'Vantage Crew',strength:.78,aggression:.62,stance:-.18,truce:0,col:'#c9a25f',territory:[.30,.18,.22,.28,.20,.34,.24]},
    {id:'Hollow',name:'Hollow Crew',strength:.54,aggression:.78,stance:-.30,truce:0,col:'#c9a25f',territory:[.24,.32,.16,.10,.26,.30,.18]},
    {id:'Mirror',name:'Mirror & Co',strength:.66,aggression:.34,stance:.05,truce:0,col:'#d9a15b',territory:[.16,.20,.30,.38,.24,.14,.36]}
  ];
  for(let i=0;i<OBJECTIVES.length;i++)S.objectives[OBJECTIVES[i].id]=false;
  pushLog('sys','A new story begins. Seed '+hashStr(String(seed)).toUpperCase()+'.');
  pushNews('City','Welcome to the city. Markets are live; build your network deliberately.');
  pushLedger('open','Opening balance',S.cash,S.cash);
  initWorld(S);
  recomputeMods();
  for(let i=0;i<24;i++)snapshot();
  return S;
}
function nid(){return S.nextId++;}
function mkLot(p,qty,purity,cost,age){return{id:nid(),p,qty,purity,cost,age:age||0,tag:'L'+String(S.nextId).padStart(3,'0'),born:S.tick,locked:0};}
function mkCourier(){return{id:nid(),name:pick(FIRST)+' '+pick(LAST),skill:rr(.34,.62),stealth:rr(.36,.66),stamina:rr(.55,.85),precision:rr(.35,.65),wage:ri(90,150),loyalty:rr(.45,.7),morale:rr(.62,.85),fatigue:rr(.02,.2),xp:0,status:'Idle',eta:0,dest:-1,payload:null,runs:0,earned:0,restT:0,trainT:0};}
/* ---------- the operator: a person on the same clock as the crew ---------- */
function mkYou(){return{tired:.2,hunger:.45,stress:.2,hours:12,downtime:0,cause:'',meals:0};}
function you(){if(!S.you)S.you=mkYou();return S.you;}
/* 1 = sharp, .45 = wrecked. Every social roll scales with it. */
function youSharp(){const Y=you();return clamp(1-Y.tired*.25-Y.hunger*.18-Y.stress*.15,.45,1);}
function blocked(){const Y=you();return Y.downtime>0?{ok:false,msg:'Out of action for '+Y.downtime+'h — '+Y.cause+'.'}:null;}
function updateYou(){
  const Y=you();Y.hours++;
  Y.hunger=clamp(Y.hunger+.021,0,1);
  Y.tired=clamp(Y.tired+.019+(Y.hours>18?.012:0),0,1);
  Y.stress=clamp(Y.stress+.004-(Y.hunger>.8?.008:0)+nrm()*.002,0,1);
  if(Y.downtime>0&&--Y.downtime===0){Y.tired=clamp(Y.tired-.34,0,1);pushLog('you','Back on your feet after '+Y.cause+'.');Y.cause='';}
}
/* every tier has named buyers: weight the district's own bias across all eight goods */
function weightedPref(d){
  const B=DISTRICTS[clamp(d||0,0,ND-1)].bias;let tot=0;
  for(let p=0;p<NP;p++)tot+=B[p];
  let r=rnd()*tot;
  for(let p=0;p<NP;p++){r-=B[p];if(r<=0)return p;}
  return NP-1;
}
function mkClient(i){const d=i%ND,keys=Object.keys(TRAITS);return{id:nid(),name:pick(FIRST)+' '+pick(LAST),district:d,trait:pick(keys),pref:weightedPref(d),alt:weightedPref(d),mem:[],budget:rr(180,900)*(1+DISTRICTS[d].wealth*.4),loyalty:rr(.08,.32),mood:rr(.55,.9),patience:rr(.6,1.3),cooldown:ri(2,20),deals:0,spent:0,churn:0,lastSeen:S.tick};}

/* ------------------------------ derived values --------------------------- */
function up(id){return S.upgrades[id]||1;}
function has(id){return !!S.research[id];}
function recomputeMods(){
  const m=S.mods;
  m.maxGrade=clamp(.62+up('lab')*.065+has('r2')*.03,.4,.99);
  m.yield=clamp(.62+up('lab')*.055+has('r2')*.08,.5,1.0);
  m.throughput=1+up('lab')*.28;
  m.capacity=220+up('vault')*190;
  m.decay=1-Math.min(.72,(up('vault')-1)*.10+has('r4')*.45);
  m.intel=.45+up('intel')*.13+(has('r3')?.2:0);
  m.pointsRate=.45+up('intel')*.22+(has('r3')?.25:0);
  m.reconCap=2400+up('cover')*2200+(has('r7')?5000:0);
  m.reconFee=clamp(.095-up('cover')*.009-(has('r7')?.02:0),.02,.12);
  m.speed=1+up('logistics')*.13+(has('r5')?.2:0);
  m.payload=1+up('logistics')*.22;
  m.complication=clamp(.055-up('logistics')*.006,.012,.06);
  m.heatDecay=1+up('counsel')*.20+(has('r8')?.25:0);
  m.heatGen=has('r8')?.75:1;
  m.auditThreshold=66+(has('r8')?8:0)+up('counsel')*2;
  m.auditSeverity=clamp(1-up('counsel')*.11,.4,1);
  m.salesBonus=1+(has('r1')?.03:0);
  m.wtpBonus=has('r6')?1.06:1;
  m.negotiate=has('r6')?.9:0;
  m.forecastTight=has('r3')?.8:1;
  m.labSlots=1+Math.floor(up('lab')/2);
  m.maxCouriers=3+Math.floor(up('logistics')*.8);
}
function netWorth(s){
  s=s||S;let v=s.cash+s.dirty-s.debt;
  for(const l of s.lots)v+=l.qty*markPrice(l.p,l.purity)*.72;
  for(let d=0;d<ND;d++)for(let p=0;p<NP;p++){const x=s.depot[d][p];if(x.qty>0)v+=x.qty*markPrice(p,x.purity)*.65;}
  v+=Object.values(s.upgrades).reduce((a,l)=>a+l*200,0);
  return v;
}
/* what a lot's grade is worth relative to street grade (.70) — the spread the market already quotes */
function gradeValue(p,purity){return markPrice(p,purity)/markPrice(p,.70);}
/* bounded deal memory: what you charged, what grade you delivered, whether you refused */
function remember(c,rec){if(!c)return;c.mem=c.mem||[];c.mem.push(rec);if(c.mem.length>8)c.mem.shift();}
function memScore(c){
  if(!c||!c.mem||!c.mem.length)return 0;
  let v=0;for(const m of c.mem){v+=m.k==='price'?clamp(m.v,-1,1):m.k==='grade'?clamp(m.v,-1,1):m.k==='refuse'?-.3:m.k==='deal'?.1:0;}
  return clamp(v/Math.max(3,c.mem.length),-1,1);
}
function markPrice(p,purity){
  const b=PRODUCTS[p].base;return b*clamp(.45+purity*.72,.5,1.35);
}
function equilibrium(d,p,dem,sup){
  const def=PRODUCTS[p],base=DISTRICTS[d];
  const ratio=clamp(dem/Math.max(.25,sup),.35,2.9);
  return def.base*Math.pow(ratio,1/def.elast)*Math.pow(base.wealth,.32)*S.macro*newsMult(d,p,'price');
}
function newsMult(d,p,type){
  let m=1;
  for(const e of S.activeEvents){
    if(e.d!==-1&&e.d!==d)continue;
    if(e.p!==-1&&e.p!==p)continue;
    if(e.type==='demand'&&type==='demand')m*=e.mag;
    if(e.type==='price'&&type==='price')m*=e.mag;
    if(e.type==='supply'&&type==='supply')m*=e.mag;
  }
  if(S.world&&S.world.mods)for(const e of S.world.mods){
    if(e.d!==-1&&e.d!==d)continue;
    if(e.p!==-1&&e.p!==p)continue;
    if(e.type==='demand'&&type==='demand')m*=e.mag;
    if(e.type==='price'&&type==='price')m*=e.mag;
    if(e.type==='supply'&&type==='supply')m*=e.mag;
  }
  return m;
}
function distTravel(a,b){ /* Dijkstra over the district graph, hours */
  const axy=DISTRICTS[0]?DISTRICTS[a]:null;
  const adj=Array.from({length:ND},()=>[]);
  for(const e of EDGES){const w=Math.hypot(DISTRICTS[e[0]].x-DISTRICTS[e[1]].x,DISTRICTS[e[0]].y-DISTRICTS[e[1]].y)*3.4;adj[e[0]].push([e[1],w]);adj[e[1]].push([e[0],w]);}
  const dist=Array(ND).fill(1e9),seen=Array(ND).fill(false);dist[a]=0;
  for(let k=0;k<ND;k++){let u=-1,best=1e9;for(let i=0;i<ND;i++)if(!seen[i]&&dist[i]<best){best=dist[i];u=i;}
    if(u<0)break;seen[u]=true;for(const[v,w]of adj[u])if(dist[u]+w<dist[v])dist[v]=dist[u]+w;}
  const congest=1+S.districts[b].heat/190+(S.weather===4?.25:0);
  return clamp((.8+(dist[b]||1)*1.0)*congest/ S.mods.speed / WEATHER[S.weather].speed,.5,7);
}
function stockTotal(){return S.lots.reduce((a,l)=>a+l.qty,0);}
function depotTotal(d){let t=0;for(let p=0;p<NP;p++)t+=S.depot[d][p].qty;return t;}
function capacityUsed(){return stockTotal();}
function available(d,p){return Math.max(0,S.depot[d][p].qty-S.listings[d][p].qty);}
function pushLog(type,text,meta){S.log.unshift({t:S.tick,type,text,meta:meta||null});if(S.log.length>420)S.log.length=420;}
function pushNews(tag,text,tone){S.news.unshift({t:S.tick,tag,text,tone:tone||'info'});if(S.news.length>90)S.news.length=90;}
function pushLedger(type,note,amount,bal){S.ledger.unshift({t:S.tick,type,note,amount,bal});if(S.ledger.length>600)S.ledger.length=600;}
function credit(amount,note,type){S.dirty+=amount;S.stats.revenue+=amount;pushLedger(type||'sale',note,amount,S.cash+S.dirty);}
function spend(amount,note,type){S.cash-=amount;S.stats.costs+=amount;pushLedger(type||'cost',note,-amount,S.cash+S.dirty);}
function toast(a,b,c){if(G.NLUI&&NLUI.toast)NLUI.toast(a,b,c);}
function logEvent(type,payload){S.eventBus.push({t:S.tick,type,payload});if(S.eventBus.length>60)S.eventBus.shift();}

/* ------------------------------ tick pipeline ---------------------------- */
function step(n){
  n=n||1;
  for(let k=0;k<n;k++){
    if(S.gameOver)break;
    const t0=(typeof performance!=='undefined'?performance.now():Date.now());
    S.tick++;S.stats.ticks++;S.hour=S.tick%24;S.day=Math.floor(S.tick/24)+1;
    S.diag.solverIter=0;S.diag.agentUpdates=0;
    advanceTime();
    updateYou();
    updateMacro();
    updateWEATHER();
    worldTick();
    updateEvents();
    updateFeedMarket();
    for(let d=0;d<ND;d++)solveDistrict(d);
    updateRivals();
    updateClients();
    updateOffers();
    updateListings();
    updateCouriers();
    updateJobs();
    updateContracts();
    updateAttention();
    updateFinance();
    updateResearch();
    updateObjectives();
    if(S.tick%12===0)computeForecast();
    worldPostTick();
    snapshot();
    S.diag.eventQueue=S.eventBus.length;
    S.diag.entropy=shannon(S.districts.map(d=>mean(d.demand)));
    S.diag.hash=hashStr(JSON.stringify([S.rs,S.cash,S.heat,S.rep,S.tick,S.districts.map(d=>d.price.map(v=>Math.round(v))),S.world?[S.world.stats.hours,Math.round(S.world.climate.temp*10),Math.round(S.world.dossier.evidence*10),Math.round(S.world.honor.code*100),Math.round(S.world.gear.rigWear*1000),S.world.mods.length]:0]));
    S.diag.lastMs=((typeof performance!=='undefined'?performance.now():Date.now())-t0);
    if(S.tick%24===0&&S.settings.autosave&&G.NLUI&&NLUI.autosave)NLUI.autosave();
  }
  return S;
}
function advanceTime(){
  S.season=Math.sin((S.tick/(24*30))*2*PI)*.09+Math.sin((S.tick/(24*7))*2*PI+.7)*.04;
  if(S.cooldown>0)S.cooldown--;
  if(S.auditCd>0)S.auditCd--;
  for(const l of S.lots){l.age+=PRODUCTS[l.p].decay*S.mods.decay*(1+ (l.purity<.6?.4:0));if(l.age>1){const loss=l.qty*l.age*.035;l.qty=Math.max(0,l.qty-loss);l.age=1;}}
  S.lots=S.lots.filter(l=>l.qty>.05);
}
function updateMacro(){
  S.macroTarget=clamp(1+S.season+nrm()*.012+.5*(S.mood-1),.82,1.24);
  S.macro=lerp(S.macro,S.macroTarget,.06);
  S.mood=clamp(S.mood+(1-S.mood)*.035+nrm()*.018,.72,1.32);
  S.scrutiny=clamp(.18+Math.sin(S.tick/(24*9)+1.2)*.09+(S.heat/100)*.22+nrm()*.008,.05,.6);
  S.diag.solverIter+=12;
}
function updateWEATHER(){
  if(--S.wTimer>0)return;
  const row=WTRANS[S.weather];let r=rnd(),acc=0,next=S.weather;
  for(let i=0;i<row.length;i++){acc+=row[i];if(r<=acc){next=i;break;}}
  if(next!==S.weather){pushNews('Weather','Conditions shifting to '+WEATHER[next].key.toLowerCase()+'.','info');}
  S.weather=next;S.wTimer=ri(7,22);
}
function updateEvents(){
  for(let i=S.activeEvents.length-1;i>=0;i--){if(--S.activeEvents[i].ttl<=0)S.activeEvents.splice(i,1);}
  for(let d=0;d<ND;d++){const ev=S.districts[d].events;for(let i=ev.length-1;i>=0;i--)if(ev[i].ttl<=S.tick)ev.splice(i,1);}
  const lambda=.055+ (S.heat/100)*.035;
  const n=poisson(lambda);
  for(let i=0;i<n;i++)fireEvent();
  if(S.tick%6===0){S.macroTarget=clamp(S.macroTarget+rr(-.02,.02),.8,1.25);}
}
function fireEvent(forced){
  let def=forced;
  if(!def){let tot=Happenings.reduce((a,e)=>a+e.w,0),r=rnd()*tot;for(const e of Happenings){r-=e.w;if(r<=0){def=e;break;}}if(!def)def=Happenings[0];}
  const d=ri(0,ND-1),p=ri(0,NP-1),dur=ri(def.dur[0],def.dur[1]),mag=rr(def.mag[0],def.mag[1]);
  const ev={id:nid(),key:def.key,type:def.type,d,p,mag,ttl:dur,tone:def.tone,t:S.tick};
  if(def.type==='rep'){
    S.rep=clamp(S.rep+mag,0,100);
    S.clients.push(mkClient(S.clients.length));
    pushNews('Referral','A new contact entered the network: '+S.clients[S.clients.length-1].name+'.','good');
  }else if(def.type==='intel'){
    S.points+=mag*2;S.districts[d].price[p]*=1.02;
    pushNews('Intel','Signal from '+DISTRICTS[d].short+': '+PRODUCTS[p].key+' is undervalued.','good');
  }else if(def.type==='feed'){
    S.feedTarget.base*=mag;S.feedTarget.additive*=mag;
    S.activeEvents.push(Object.assign({},ev,{d:-1,p:-1,ttl:dur}));
    pushNews('Supply',def.text+' ['+DISTRICTS[d].short+']','bad');
  }else if(def.type==='heat'){
    S.districts[d].heat=clamp(S.districts[d].heat+mag,0,100);
    pushNews('Attention',def.text+' ['+DISTRICTS[d].short+']','bad');
  }else if(def.type==='rival'){
    const rival=S.rivals[ri(0,S.rivals.length-1)];
    rival.aggression=clamp(rival.aggression+.12,0,1);
    S.activeEvents.push(Object.assign({},ev,{p:-1,ttl:dur}));
    pushNews('Crew',rival.name+': '+def.text,'bad');
  }else{
    S.activeEvents.push(Object.assign({},ev,{ttl:dur}));
    pushNews('MarkET',def.text+' ['+DISTRICTS[d].short+' · '+PRODUCTS[p].key+']',def.tone);
  }
  logEvent('event',ev);
  if(def.tone==='bad'&&mag>1.4&&S.settings.autopause&&G.NLUI&&NLUI.autopause)NLUI.autopause('Market shock: '+def.key);
}
function solveDistrict(d){
  const D=S.districts[d],B=DISTRICTS[d],W=WEATHER[S.weather];
  const tod=TOD[S.hour],season=1+S.season;
  for(let p=0;p<NP;p++){
    const def=PRODUCTS[p];
    /* --- latent demand: Ornstein–Uhlenbeck around a structural target --- */
    const wealthTerm=.58+.42*B.wealth;
    const saturation=1-clamp(D.sat[p],0,1)*.46;
    const eventMult=newsMult(d,p,'demand');
    const wordOfMouth=1+clamp(D.loyalty,0,1)*.22+clamp(S.rep/100,0,1)*.16;
    const target=B.pop*B.bias[p]*wealthTerm*tod*W.dem*season*S.mood*wordOfMouth*saturation*eventMult;
    D.demand[p]=clamp(D.demand[p]+.24*(target-D.demand[p])+Math.sqrt(def.vol)*.075*nrm()*target,.05,target*3.2);
    D.diagIter=(D.diagIter||0)+1;S.diag.solverIter+=3;
    /* --- rival supply mean reversion + shocks --- */
    const rTarget=Math.max(.25,target*rr(.72,1.28)*newsMult(d,p,'supply'));
    D.rival[p]=clamp(D.rival[p]+.13*(rTarget-D.rival[p])+nrm()*.045*target,.12,target*3);
    /* --- saturation decays; sales replenish it --- */
    D.sat[p]=clamp(D.sat[p]*(1-def.decay*31)+D.volume[p]*.0018,0,1);
    D.volume[p]*=.82;
    /* --- price discovery: inverse demand with smoothing --- */
    S.prod[p].volState=clamp(S.prod[p].volState*.86+nrm()*def.vol*.32,-.35,.35);
    if(S.prod[p].shockT>0)S.prod[p].shockT--;else S.prod[p].shock=lerp(S.prod[p].shock,1,.08);
    const localSupply=D.rival[p]+S.depot[d][p].qty*.35;
    let fair=equilibrium(d,p,D.demand[p],localSupply);
    fair*=1+S.prod[p].volState+S.prod[p].shock-1;
    fair*=1+ (S.districts[d].heat/100)*.035;
    D.lastPrice[p]=D.price[p];
    D.price[p]=clamp(lerp(D.price[p],fair,.34),def.base*.28,def.base*3.4);
    if(S.listings[d][p].mode==='auto')S.listings[d][p].ask=r2(D.price[p]*optimalAsk(d,p));
  }
  /* --- local scrutiny & loyalty drift --- */
  const decay=.022*S.mods.heatDecay*(1+S.scrutiny*.4);
  D.heat=clamp(D.heat-decay+Math.abs(nrm())*.05*S.scrutiny,0,100);
  D.loyalty=clamp(D.loyalty+(S.control[d]-D.loyalty)*.012+nrm()*.0015,0,1);
  D.scrutiny=clamp(S.scrutiny+B.risk*.32+D.heat/260,.02,1);
  S.diag.agentUpdates+=ND*NP;
}
function updateFeedMarket(){
  for(const k of Object.keys(S.feedPrice)){
    S.feedTarget[k]=clamp(S.feedTarget[k]*(1+Math.sin(S.tick/37+k.length)*.0008)+nrm()*.008*S.feedTarget[k],S.feedPrice[k]*.45,S.feedPrice[k]*2.4);
    S.feedPrice[k]=clamp(lerp(S.feedPrice[k],S.feedTarget[k],.09)*(1+nrm()*.012),.4,999);
  }
}
function updateRivals(){
  if(S.tick%6!==0)return;
  for(const r of S.rivals){
    r.stance=clamp(r.stance+nrm()*.012,-1,1);
    r.aggression=clamp(r.aggression+(S.heat/100-0.4)*.008+nrm()*.015,.05,1);
    if(r.truce>0)r.truce--;
    const hostile=r.stance<-.15&&r.truce<=0;
    for(let d=0;d<ND;d++){
      const pressure=hostile?(.006+r.aggression*.012)*(r.strength):(-.002);
      S.control[d]=clamp(S.control[d]-pressure+.0006*S.districts[d].loyalty,0,1);
      r.territory[d]=clamp(r.territory[d]+pressure*.4+nrm()*.002,.02,.85);
      S.diag.solverIter++;
    }
    if(hostile&&chance(.035*r.aggression)){
      const d=ri(0,ND-1);S.districts[d].heat=clamp(S.districts[d].heat+rr(2,6),0,100);
      pushNews('Crew',r.name+' applies pressure in '+DISTRICTS[d].short+'.','bad');
    }
  }
}
function updateClients(){
  for(const c of S.clients){
    c.budget=clamp(c.budget+rr(3,11)*(1+DISTRICTS[c.district].wealth*.5),60,4200);
    c.mood=clamp(c.mood+(.72-c.mood)*.03+nrm()*.012,.1,1);
    c.churn=clamp(c.churn+(c.mood<.35?.008:-.004),0,1);
    if(c.churn>.98){
      S.clients=S.clients.filter(x=>x!==c);pushNews('NETWork',c.name+' left the network.','bad');
      if(chance(.55)){const nc=mkClient(S.clients.length);S.clients.push(nc);pushNews('NETWork','A quiet introduction: '+nc.name+' came in through '+c.name+"'s circle.",'info');}
      continue;
    }
    if(c.cooldown>0){c.cooldown--;continue;}
    const D=S.districts[c.district];
    const pref=chance(.22)&&c.alt!=null&&c.alt<NP?c.alt:(c.pref<NP?c.pref:0);
    const mem=memScore(c);
    const pull=D.demand[pref]*(.5+c.loyalty*.6)*(1+S.rep/220)*(1/S.macro);
    const rate=.075*pull*(c.mood+.2);
    if(S.offers.length<14&&chance(clamp(rate,0,.42))){
      const trait=TRAITS[c.trait];
      const market=D.price[pref];
      const qty=clamp(Math.round(rr(2,9)*trait.qty*(1+c.loyalty*.5)*(1+DISTRICTS[c.district].wealth*.35)),1,44);
      const wtp=market*rr(.92,1.24)*trait.wtp*(1+c.loyalty*.22)*S.mods.wtpBonus*rr(.9,1.1)*(1+mem*.07);
      const minGrade=clamp(.48+trait.haggle*.06+rr(-.08,.14),.3,.9);
      const offered=r2(wtp*rr(.72,.88));
      S.offers.push({id:nid(),client:c.id,cid:c.district,p:pref,qty,offer:offered,wtp:r2(wtp),
        minGrade,ttl:Math.max(3,ri(5,13)+(mem<-.2?-3:0)),expires:S.tick+ri(5,13),trait:c.trait,t:S.tick,mem});
      c.cooldown=ri(6,16);c.lastSeen=S.tick;
      S.diag.agentUpdates++;
    }
  }
}
function updateOffers(){
  for(let i=S.offers.length-1;i>=0;i--){
    const o=S.offers[i];
    if(o.ttl--<=0){S.offers.splice(i,1);const c=S.clients.find(x=>x.id===o.client);if(c)c.mood=clamp(c.mood-.03,0,1);}
  }
}
function updateListings(){
  /* passive retail clearing: price -> quantity via constant-elasticity demand */
  for(let d=0;d<ND;d++)for(let p=0;p<NP;p++){
    const L=S.listings[d][p],D=S.districts[d];
    if(!L.enabled||L.qty<=0)continue;
    if(L.mode==='auto'){L.ask=r2(D.price[p]*optimalAsk(d,p));}
    const ratio=clamp(L.ask/Math.max(1,D.price[p]),.45,2.6);
    const el=PRODUCTS[p].elast;
    const take=clamp(D.demand[p]*.052*MARKET_SCALE*Math.pow(ratio,-el)*(.45+S.control[d]*.9)*(.7+S.rep/90)*S.mods.salesBonus*(S.cooldown>0?.35:1),0,L.qty);
    if(take<.02)continue;
    const sold=Math.min(take,L.qty);
    const dep=S.depot[d][p];
    const purity=dep.purity;
    if(purity<.35)continue;
    const gross=r2(sold*L.ask*clamp(gradeValue(p,purity),.85,1.18));
    L.qty=r2(Math.max(0,L.qty-sold));dep.qty=r2(Math.max(0,dep.qty-sold));
    if(L.qty<=0){L.enabled=false;}
    credit(gross,PRODUCTS[p].code+' retail · '+DISTRICTS[d].short,'retail');
    S.pnls[p].rev+=gross;S.pnls[p].units+=sold;S.districtPnl[d]+=gross;
    S.stats.sales++;S.stats.unitsSold+=sold;
    D.sat[p]=clamp(D.sat[p]+sold*.0025,0,1);D.volume[p]+=sold;D.lastSale[p]=S.tick;S.tickVolume+=sold;
    S.control[d]=clamp(S.control[d]+sold*.00075,0,1);
    const heatGain=sold*.020*(1+B_Risk(d))*(1+ (p>=5?.25:0))*S.mods.heatGen;
    D.heat=clamp(D.heat+heatGain,0,100);
    S.diag.solverIter+=5;
    if(chance(.055))pushLog('sale','Retail · '+fmtU(sold)+' '+PRODUCTS[p].code+' @ '+DISTRICTS[d].short+' → '+fmtC(gross),{d,p});
  }
}
function B_Risk(d){return DISTRICTS[d].risk;}
function updateCouriers(){
  for(const c of S.couriers){
    c.earned+=c.wage/24;
    if(c.status==='Idle'){
      c.fatigue=clamp(c.fatigue-.012,0,1);
      c.morale=clamp(c.morale+.0018-(c.fatigue*.0006),0,1);
    }else if(c.status==='Rest'){
      c.fatigue=clamp(c.fatigue-.055,0,1);c.morale=clamp(c.morale+.007,0,1);
      if(--c.restT<=0){c.status='Idle';pushLog('crew',c.name+' back on roster.');}
    }else if(c.status==='Train'){
      c.skill=clamp(c.skill+.004,0,1);c.stealth=clamp(c.stealth+.003,0,1);c.precision=clamp(c.precision+.004,0,1);
      c.morale=clamp(c.morale-.001,0,1);c.fatigue=clamp(c.fatigue+.008,0,1);
      if(--c.trainT<=0){c.status='Idle';pushLog('crew',c.name+' completed precision training.');}
    }else{
      c.eta-=1;c.fatigue=clamp(c.fatigue+.017,0,1);
      c.morale=clamp(c.morale-.0009,0,1);
      if(c.eta>0)continue;
      if(c.status==='Outbound'){
        const risk=S.mods.complication*(1+S.districts[c.dest].heat/55)*(1+c.fatigue*.9)*(1-c.stealth*.55)*WEATHER[S.weather].risk*(S.world?(1+S.world.district[c.dest].patrol*.55+(1-S.world.climate.visibility)*.30):1);
        if(chance(risk)){
          const loss=c.payload.qty*rr(.18,.55);
          c.payload.qty-=loss;c.eta=ri(2,5);
          S.districts[c.dest].heat=clamp(S.districts[c.dest].heat+rr(3,8),0,100);
          pushLog('alert','Complication: '+c.name+' delayed near '+DISTRICTS[c.dest].short+'; '+fmtU(loss)+' lost.',{d:c.dest});
          toast('Route complication',c.name+' lost '+fmtU(loss)+' in transit.','bad');
          continue;
        }
        const dep=S.depot[c.dest][c.payload.p];
        const oldQ=dep.qty;
        dep.purity=(oldQ*dep.purity+c.payload.qty*c.payload.purity)/Math.max(.001,oldQ+c.payload.qty);
        dep.cost=(oldQ*dep.cost+c.payload.qty*c.payload.cost)/Math.max(.001,oldQ+c.payload.qty);
        dep.qty=r2(oldQ+c.payload.qty);
        S.stats.deliveries++;c.runs++;c.xp+=c.payload.qty*.09;
        c.loyalty=clamp(c.loyalty+.006,0,1);
        pushLog('ops','Delivered '+fmtU(c.payload.qty)+' '+PRODUCTS[c.payload.p].code+' → '+DISTRICTS[c.dest].short+' by '+c.name+'.',{d:c.dest,p:c.payload.p});
        toast('Delivery complete',fmtU(c.payload.qty)+' '+PRODUCTS[c.payload.p].key+' stocked in '+DISTRICTS[c.dest].short+' (Try posting a price).','good');
        c.payload=null;c.status='Returning';c.eta=Math.max(1,Math.round(distTravel(c.dest,0)*.7));
      }else if(c.status==='Returning'){
        c.status='Idle';c.dest=-1;c.morale=clamp(c.morale+.01,0,1);
      }
    }
    /* camp morale is now the crew's collective patience: it decides resignations, not a badge */
    const camp=mean(S.couriers.map(q=>q.morale));
    if((c.morale<.12||camp<.22)&&c.status==='Idle'&&chance(.006+(camp<.22?.012:0))){
      S.couriers=S.couriers.filter(x=>x!==c);
      pushNews('Crew',c.name+' resigned. Morale had collapsed.','bad');
      toast('Crew resignation',c.name+' left the outfit.','bad');
    }
    S.diag.agentUpdates++;
  }
}
function updateJobs(){
  for(let i=S.jobs.length-1;i>=0;i--){
    const j=S.jobs[i];
    j.progress+=S.mods.throughput*(.8+S.mods.yield*.2);
    if(j.progress<j.hours)continue;
    const yieldQ=r2(j.qty*S.mods.yield*rr(.88,1.10));
    const purity=clamp(S.mods.maxGrade*rr(.82,1.0)+nrm()*.045+j.boost,.28,.995);
    const lot=mkLot(j.p,yieldQ,purity,r2(j.cost/Math.max(1,yieldQ)),0);
    S.lots.push(lot);
    S.jobs.splice(i,1);S.stats.completedJobs++;
    pushLog('lab','Job '+j.tag+' complete · '+fmtU(yieldQ)+' '+PRODUCTS[j.p].code+' @ '+fmtP(purity,1)+'.',{p:j.p});
    toast('Refining complete',PRODUCTS[j.p].key+' · '+fmtU(yieldQ)+' at '+fmtP(purity,1)+' purity.','good');
    if(purity>=.92)pushNews('Lab','Grade-A batch '+j.tag+' produced.','good');
  }
}
function updateContracts(){
  if(--S.contractCd<=0){
    S.contractCd=ri(26,46);
    if(S.contracts.filter(c=>!c.done).length<4){
      const d=ri(0,ND-1),p=ri(0,NP-1),qty=ri(14,52)*(1+Math.floor(S.rep/25));
      S.contracts.unshift({id:nid(),d,p,qty:0,need:qty,reward:r2(qty*S.districts[d].price[p]*1.22),penalty:r2(qty*S.districts[d].price[p]*.28),deadline:S.tick+ri(30,58),done:false,t:S.tick});
      pushNews('Order','New standing order: '+fmtU(qty)+' '+PRODUCTS[p].key+' → '+DISTRICTS[d].short+'.','info');
    }
  }
  for(const c of S.contracts){
    if(c.done)continue;
    if(S.tick>=c.deadline){
      c.done=true;
      if(c.qty>=c.need){S.cash+=c.reward;S.rep=clamp(S.rep+2.5,0,100);pushLedger('contract','Standing order fulfilled',c.reward,S.cash+S.dirty);pushNews('Order','Order settled: +'+fmtC(c.reward),'good');toast('Contract fulfilled','+'+fmtC(c.reward)+' and +2.5 reputation.','good');}
      else{const f=c.penalty*(1-c.qty/c.need);spend(f,'Standing order penalty');S.rep=clamp(S.rep-1.8,0,100);pushNews('Order','Order missed: −'+fmtC(f),'bad');toast('Contract missed',fmtC(f)+' penalty applied.','bad');}
    }
  }
  if(S.contracts.length>30)S.contracts.length=30;
}
function updateAttention(){
  let w=0,sum=0;
  for(let d=0;d<ND;d++){const wd=DISTRICTS[d].pop;sum+=S.districts[d].heat*wd;w+=wd;}
  S.activity=clamp(S.activity*(S.cooldown>0?.82:.93)+S.tickVolume*.10*S.mods.heatGen,0,100);
  S.tickVolume=0;
  const target=clamp(sum/w*.84+S.scrutiny*8+S.activity+(S.cooldown>0?-8:0)+(S.world?S.world.dossier.evidence*.22+mean(S.world.district.map(x=>x.patrol))*6:0),0,100);
  S.heat=clamp(lerp(S.heat,target,.30),0,100);
  if(S.heat<18)S.stats.quietStreak++;else S.stats.quietStreak=0;
  if(S.heat>=S.mods.auditThreshold&&S.auditCd<=0)runAudit();
}
function runAudit(){
  S.auditCd=ri(60,96);S.stats.audits++;S.diag.audits++;
  const fine=r2((420+S.cash*.075+netWorth(S)*.012)*S.mods.auditSeverity*(S.world?1+S.world.dossier.evidence*.008:1));
  spend(fine,'Compliance assessment','fine');S.stats.fines+=fine;
  S.rep=clamp(S.rep-5.5,0,100);
  let seized=0;
  for(let d=0;d<ND;d++)for(let p=0;p<NP;p++){
    const dep=S.depot[d][p];if(dep.qty<=0)continue;
    const amount=dep.qty*rr(.12,.36);seized+=amount;dep.qty=r2(dep.qty-amount);
    S.listings[d][p].qty=Math.min(S.listings[d][p].qty,dep.qty);
  }
  S.stats.seizures+=seized;S.cooldown=ri(12,22);S.heat=clamp(S.heat-30,0,100);S.activity=0;
  for(let d=0;d<ND;d++)S.districts[d].heat=clamp(S.districts[d].heat*.60,0,100);
  if(S.world){S.world.dossier.evidence*=.35;S.world.dossier.reports=[];S.world.dossier.threads=[];S.world.honor.discretion=clamp(S.world.honor.discretion-.02,0,1);wlog('dossier','Assessment closed several evidence threads.');}
  pushLog('alert','Inspection · '+fmtC(fine)+' assessed, '+fmtU(seized)+' impounded, '+S.cooldown+'h cooldown.',null);
  pushNews('Inspection','Formal assessment: '+fmtC(fine)+' levied; '+fmtU(seized)+' impounded.','bad');
  toast('An inspection',fmtC(fine)+' assessed · '+fmtU(seized)+' impounded · '+S.cooldown+'h cool-down.','bad');
  if(S.settings.autopause&&G.NLUI&&NLUI.autopause)NLUI.autopause('An inspection needs your attention');
}
function updateFinance(){
  const wages=S.couriers.reduce((a,c)=>a+c.wage/24,0)*(S.world?S.world.economy.wageIndex:1);
  const rent=4+Object.values(S.upgrades).reduce((a,v)=>a+v*.8,0)*(S.world?S.world.economy.rentIndex:1);
  const upkeep=1.5+up('lab')*.8+S.jobs.length*.9+(S.world&&S.world.gear.maintenanceDue?1.2:0);
  const overhead=wages+rent+upkeep;
  S.cash=r2(S.cash-overhead);S.stats.costs+=overhead;
  S.overheadAcc=r2((S.overheadAcc||0)+overhead);
  if(S.tick%6===0){pushLedger('overhead','Crew wages, lease & upkeep (6h)',-S.overheadAcc,S.cash+S.dirty);S.overheadAcc=0;}
  /* reconciliation: converts unsettled revenue into spendable cash, capped & fee'd */
  if(S.autoRecon&&S.dirty>0){
    const amount=Math.min(S.dirty,S.mods.reconCap/24*4);
    const fee=amount*S.mods.reconFee;
    S.dirty=r2(S.dirty-amount);S.cash=r2(S.cash+amount-fee);
    S.reconAcc=r2((S.reconAcc||0)+amount);S.reconFeeAcc=r2((S.reconFeeAcc||0)+fee);
    if(S.tick%6===0){pushLedger('recon','Reconciled '+fmtC(S.reconAcc)+' over 6h (fee '+fmtC(S.reconFeeAcc)+')',-S.reconFeeAcc,S.cash+S.dirty);S.reconAcc=0;S.reconFeeAcc=0;}
  }
  if(S.cash<0){S.debt=r2(S.debt-S.cash);S.cash=0;}
  if(S.debt>0){
    const interest=r2(S.debt*.0012);S.debt=r2(S.debt+interest);
    if(S.cash>200){const pay=Math.min(S.cash*.12,S.debt);S.cash=r2(S.cash-pay);S.debt=r2(S.debt-pay);}
  }
  if(netWorth(S)<-18000||S.debt>28000){S.gameOver='The ledger closed';S.paused=true;pushNews('City','The outfit is insolvent. The ledger is closed.','bad');}
}
function updateResearch(){
  S.points=r2(S.points+S.mods.pointsRate);
}
function updateObjectives(){
  let all=true;
  for(const o of OBJECTIVES){
    if(!S.objectives[o.id]&&o.check(S)){
      S.objectives[o.id]=true;S.cash=r2(S.cash+o.reward);S.rep=clamp(S.rep+1.5,0,100);S.points+=6;
      pushNews('OBJECTIVE','✓ '+o.key+' · +'+fmtC(o.reward),'good');
      toast('Objective complete',o.key+' · +'+fmtC(o.reward),'good');
      if(G.NLUI&&NLUI.sfx)NLUI.sfx('good');
    }
    if(!S.objectives[o.id])all=false;
  }
  if(all&&!S.won){S.won=true;pushNews('City','The long game is complete — every milestone reached.','good');toast('Plan complete','You control the city. Continue in free-play or start a new seed.','good');}
}
function snapshot(){
  const h=S.history,cap=720;
  const push=(k,v)=>{h[k].push(r2(v));if(h[k].length>cap)h[k].shift();};
  push('cash',S.cash);push('worth',netWorth(S));push('heat',S.heat);push('rep',S.rep);
  push('dirty',S.dirty);push('volume',S.stats.unitsSold);
  push('price',mean(S.districts.map(d=>mean(d.price))));
  push('demand',mean(S.districts.map(d=>mean(d.demand))));
}
function shannon(a){const t=a.reduce((x,y)=>x+Math.max(0,y),0)||1;let h=0;for(const v of a){const p=Math.max(0,v)/t;if(p>0)h-=p*Math.log2(p);}return r3(h/Math.log2(Math.max(2,a.length)));}

/* ------------------------------ analytics -------------------------------- */
function optimalAsk(d,p){
  /* Grid search over expected-profit surface: (ask − marginal cost) × quantity(ask) × close-rate */
  let best=1,bestV=-1e9;
  const curve=[];
  const cost=S.depot[d][p].cost||PRODUCTS[p].base*.45;
  const dep=S.depot[d][p];
  for(let m=.62;m<=1.92;m+=.04){
    const ask=S.districts[d].price[p]*m;
    const q=Math.min(Math.max(0,(dep.qty||8)),S.districts[d].demand[p]*.052*MARKET_SCALE*Math.pow(m,-PRODUCTS[p].elast)*(.45+S.control[d]*.9)*1.1);
    const close=sig((1.08-m)*4.2+S.rep/160+S.control[d]*.6);
    const v=(ask-cost)*q*close;
    curve.push([r2(m),r2(v)]);
    if(v>bestV){bestV=v;best=m;}
  }
  return best;
}
function priceOptimiser(d,p){
  const cost=S.depot[d][p].cost||PRODUCTS[p].base*.45;
  const curve=[];let best=.9,bestV=-1e9,bestQ=0;
  for(let m=.55;m<=2.0;m+=.025){
    const ask=S.districts[d].price[p]*m;
    const q=S.districts[d].demand[p]*.052*MARKET_SCALE*Math.pow(m,-PRODUCTS[p].elast)*(.45+S.control[d]*.9)*1.1;
    const close=sig((1.08-m)*4.2);
    const v=(ask-cost)*q*close;
    curve.push([r2(m),r2(v)]);
    if(v>bestV){bestV=v;best=m;bestQ=q;}
  }
  return{curve,best:bestV,m:best,q:bestQ,ask:r2(S.districts[d].price[p]*best),cost:r2(cost)};
}
function offerOdds(o,ask){
  const c=S.clients.find(x=>x.id===o.client)||{loyalty:.3};
  const t=TRAITS[o.trait]||TRAITS.cautious;
  const z=(o.wtp-ask)/Math.max(1,o.wtp*.085)*2.1+c.loyalty*1.5-t.haggle*.85+S.rep/190+S.mods.negotiate;
  return clamp(sig(z),.02,.98);
}
function computeForecast(paths){
  paths=paths||150;const H=48;
  const fan=Array.from({length:H},()=>[]),heatFan=Array.from({length:H},()=>[]);
  const base=netWorth(S),avgPrice=mean(S.districts.map(d=>mean(d.price)));
  const turnover=Math.max(.4,mean(S.history.volume.slice(-48).map((v,i,a)=>i?v-a[i-1]:0))||1.2);
  const listed=S.listings.reduce((a,row)=>a+row.reduce((x,l)=>x+(l.enabled?l.qty:0),0),0);
  for(let k=0;k<paths;k++){
    const R=makeRng((S.rs^Math.imul(k+1,2654435761))>>>0);
    let worth=base,heat=S.heat,cash=S.cash,dirty=S.dirty,price=avgPrice,demand=1,audit=0;
    for(let h=0;h<H;h++){
      demand=clamp(demand+.12*(1-demand)+R.norm()*.055,0.5,1.7);
      price=clamp(price+.15*(avgPrice*demand-price)+R.norm()*avgPrice*.045,avgPrice*.45,avgPrice*2);
      const rev=turnover*price*.30*demand*(listed>0?1:.25)*(.7+R.next()*.6);
      const cost=(S.couriers.reduce((a,c)=>a+c.wage/24,0)+22);
      dirty+=rev;cash-=cost;
      const recon=Math.min(dirty,S.mods.reconCap/24*4);dirty-=recon;cash+=recon*(1-S.mods.reconFee);
      heat=clamp(heat+(mean(S.districts.map(d=>d.heat))*.82+S.scrutiny*8+S.activity-heat)*.30+rev*.0009*S.mods.heatGen-.35*S.mods.heatDecay+R.norm()*.35,0,100);
      /* the world layer moves inside the path too, so a curfew or a case can show up in the band */
      if(S.world){const ev=S.world.dossier.evidence*.004+(S.world.events.curfewLike||0);heat=clamp(heat+ev+R.norm()*.2,0,100);}
      if(heat>=S.mods.auditThreshold&&R.next()<.03){audit++;cash-=600*S.mods.auditSeverity;heat-=26;}
      worth=cash+dirty-S.debt;
      fan[h].push(worth);heatFan[h].push(heat);
    }
  }
  const q=(a,p)=>{a=a.slice().sort((x,y)=>x-y);return a[Math.min(a.length-1,Math.floor(a.length*p))]||0;};
  S.forecast={
    at:S.tick,paths,H,ran:paths,
    p10:fan.map(a=>q(a,.10)),p50:fan.map(a=>q(a,.50)),p90:fan.map(a=>q(a,.90)),
    heat:heatFan.map(a=>q(a,.50)),
    endWorth:fan[H-1].slice().sort((a,b)=>a-b),
    auditRisk:r2(fan[H-1].filter((_,i)=>heatFan[H-1][i]>S.mods.auditThreshold).length/paths),
    upProb:r2(fan[H-1].filter(v=>v>base).length/paths),
    expected:r2(mean(fan[H-1])),vars:r2(q(fan[H-1],.05))
  };
  S.forecastAt=S.tick;
  return S.forecast;
}

/* ------------------------------ player actions --------------------------- */
const A={};
A.setSpeed=v=>{S.speed=v;S.paused=false;};
A.sleep=h=>{
  const b=blocked();if(b)return b;
  h=clamp(Math.round(h||8),4,12);
  const Y=you();Y.downtime=h;Y.cause='sleeping';Y.hours=0;
  pushLog('you','Sleeping for '+h+'h. The city keeps moving.');
  return{ok:true,msg:'Asleep for '+h+'h. Nothing trades while you are under.'};
};
A.eat=()=>{
  const b=blocked();if(b)return b;
  if(S.cash<6)return{ok:false,msg:'A hot meal costs ¤6.'};
  spend(6,'A meal','living');
  const Y=you();Y.hunger=clamp(Y.hunger-.5,0,1);Y.stress=clamp(Y.stress-.06,0,1);Y.meals++;
  if(Y.downtime<1){Y.downtime=1;Y.cause='a meal';}
  pushLog('you','Ate. Hunger '+fmtP(Y.hunger,0)+'.');
  return{ok:true,msg:'Fed. Hunger now '+fmtP(Y.hunger,0)+'.'};
};
A.togglePause=()=>{S.paused=!S.paused;};
A.buyFeed=(kind,qty)=>{const b=blocked();if(b)return b;const cost=r2(S.feedPrice[kind]*qty);
  if(cost>S.cash)return{ok:false,msg:'Insufficient liquid cash.'};
  if(S.feed[kind]+qty>9000)return{ok:false,msg:'Feedstock silo at capacity.'};
  spend(cost,'Bought '+fmtN(qty)+' '+kind+' feedstock','procure');S.feed[kind]+=qty;
  pushLog('ops','Procured '+fmtN(qty)+' '+kind+' for '+fmtC(cost)+'.');
  return{ok:true,msg:'Procured '+fmtN(qty)+' units.'};
};
A.startJob=(p,qty,target)=>{const b=blocked();if(b)return b;target=clamp(target,.4,S.mods.maxGrade);
  if(S.jobs.length>=S.mods.labSlots)return{ok:false,msg:'All lab slots occupied.'};
  const needB=Math.ceil(qty*(1.15+target*.45)),needA=Math.ceil(qty*(.42+target*.75)),needK=Math.ceil(qty/8);
  if(S.feed.base<needB||S.feed.additive<needA||S.feed.packs<needK)return{ok:false,msg:'Missing inputs: '+fmtN(needB)+' base / '+fmtN(needA)+' additive / '+fmtN(needK)+' packs.'};
  const cost=needB*S.feedPrice.base+needA*S.feedPrice.additive+needK*S.feedPrice.packs+qty*1.2;
  if(cost>S.cash)return{ok:false,msg:'Refining run needs '+fmtC(cost)+' liquid cash.'};
  spend(cost,'Refining run '+PRODUCTS[p].key,'refine');
  S.feed.base-=needB;S.feed.additive-=needA;S.feed.packs-=needK;
  const boost=clamp((target-.62)*.10,0,.05);
  S.jobs.push({id:nid(),tag:'J'+String(S.nextId).padStart(3,'0'),p,qty,target,cost,progress:0,hours:Math.ceil(3+qty/18+target*4),boost,t:S.tick});
  pushLog('lab','Queued '+PRODUCTS[p].key+' · '+fmtU(qty)+' · target '+fmtP(target)+'.',{p});
  return{ok:true,msg:'Job queued · '+(3+qty/18+target*4).toFixed(1)+'h.'};
};
A.dispatch=(lotId,qty,d,courierId)=>{const b=blocked();if(b)return b;qty=Math.max(.5,Math.round(qty*10)/10);
  const lot=S.lots.find(l=>l.id===lotId);if(!lot)return{ok:false,msg:'Lot no longer exists.'};
  if(qty>lot.qty+.001)return{ok:false,msg:'Not enough units in that lot.'};
  const c=S.couriers.find(x=>x.id===courierId);if(!c||c.status!=='Idle')return{ok:false,msg:'Courier unavailable.'};
  const cap=Math.round(38*c.stamina*S.mods.payload);
  if(qty>cap)return{ok:false,msg:'Payload exceeds '+c.name.split(' ')[0]+'\'s capacity ('+fmtU(cap)+').'};
  const eta=Math.max(1,Math.round(distTravel(0,d)*(1+.18*(1-c.skill))));
  lot.qty=r2(lot.qty-qty);if(lot.qty<=.05)S.lots=S.lots.filter(l=>l!==lot);
  c.status='Outbound';c.dest=d;c.eta=eta;
  c.payload={p:lot.p,qty,purity:lot.purity,cost:lot.cost,lot:lot.tag};
  pushLog('ops','Dispatch '+c.name+' → '+DISTRICTS[d].short+' · '+fmtU(qty)+' '+PRODUCTS[lot.p].code+' · ETA '+eta+'h.',{d,p:lot.p});
  return{ok:true,msg:c.name+' outbound · ETA '+eta+'h.'};
};
A.postListing=(d,p,qty,ask,mode)=>{const b=blocked();if(b)return b;const dep=S.depot[d][p],L=S.listings[d][p];
  qty=Math.max(0,Math.round(qty*10)/10);
  if(qty>dep.qty+.001)return{ok:false,msg:'Only '+fmtU(dep.qty)+' available at this depot.'};
  L.qty=qty;L.ask=r2(ask);L.mode=mode||'manual';L.enabled=qty>0&&ask>0;
  pushLog('ops','Listing '+fmtU(qty)+' '+PRODUCTS[p].code+' @ '+fmtC(ask,2)+' · '+DISTRICTS[d].short+'.');
  return{ok:true,msg:'Listing updated.'};
};
A.acceptOffer=(id,ask,mode)=>{
  const i=S.offers.findIndex(o=>o.id===id);if(i<0)return{ok:false,msg:'Offer expired.'};
  const o=S.offers[i],c=S.clients.find(x=>x.id===o.client);
  ask=ask||o.offer;
  const dep=S.depot[o.cid][o.p];
  /* position: take the buyer's own price but deliver only what clears their floor */
  if(mode==='grade'){
    if(dep.qty+1e-6<o.qty)return{ok:false,msg:'Need '+fmtU(o.qty)+' at '+DISTRICTS[o.cid].short+' to hold this position.'};
    if(dep.purity<o.minGrade)return{ok:false,msg:'Your stock is '+fmtP(dep.purity,0)+'; their floor is '+fmtP(o.minGrade,0)+'.'};
    ask=o.offer;
  }
  /* position: fill half now at the ask, leave the rest for the next window */
  if(mode==='split')o.qty=Math.max(1,Math.round(o.qty*.5));
  if(dep.qty+1e-6<o.qty)return{ok:false,msg:'Need '+fmtU(o.qty)+' '+PRODUCTS[o.p].code+' at '+DISTRICTS[o.cid].short+'. Dispatch stock first.'};
  if(dep.purity<o.minGrade)return{ok:false,msg:'Buyer requires '+fmtP(o.minGrade)+' purity; depot is '+fmtP(dep.purity)+'.'};
  let p=1;
  if(mode==='counter')p=offerOdds(o,ask)*youSharp();
  if(o.ttl<=2)p*=.7;                            /* a late answer is a worse answer */
  const success=rnd()<p;
  S.offers.splice(i,1);
  if(!success){
    S.stats.offersFailed++;
    if(c){c.mood=clamp(c.mood-.10,0,1);c.loyalty=clamp(c.loyalty-.035,0,1);c.cooldown=ri(14,30);}
    S.rep=clamp(S.rep-.35,0,100);
    pushLog('deal','Counter refused by '+(c?c.name:'client')+' at '+fmtC(ask,2)+'.',{d:o.cid,p:o.p});
    return{ok:true,success:false,msg:'Buyer walked away. Relationship damaged.'};
  }
  /* the buyer pays for the grade they asked for; above spec pays a premium, below spec is not possible */
  const purity=clamp(dep.purity,0,1);
  const gFactor=clamp(gradeValue(o.p,purity)/gradeValue(o.p,o.minGrade),.8,1.25);
  const gross=r2(ask*o.qty*gFactor);
  dep.qty=r2(Math.max(0,dep.qty-o.qty));
  const L=S.listings[o.cid][o.p];L.qty=Math.min(L.qty,dep.qty);if(L.qty<=0)L.enabled=false;
  credit(gross,'Direct deal · '+PRODUCTS[o.p].code+' · '+DISTRICTS[o.cid].short,'deal');
  S.pnls[o.p].rev+=gross;S.pnls[o.p].units+=o.qty;S.districtPnl[o.cid]+=gross;
  S.stats.unitsSold+=o.qty;S.stats.offersAccepted++;S.stats.sales++;S.tickVolume+=o.qty;
  const D=S.districts[o.cid];
  D.sat[o.p]=clamp(D.sat[o.p]+o.qty*.012,0,1);D.volume[o.p]+=o.qty;D.lastSale[o.p]=S.tick;
  S.control[o.cid]=clamp(S.control[o.cid]+o.qty*.0011,0,1);
  S.rep=clamp(S.rep+.18+o.qty*.002,0,100);
  const t=TRAITS[o.trait]||TRAITS.cautious;
  D.heat=clamp(D.heat+o.qty*.055*(1+B_Risk(o.cid))*t.heat*S.mods.heatGen,0,100);
  if(c){
    c.deals++;c.spent+=gross;c.budget=Math.max(40,c.budget-gross);c.loyalty=clamp(c.loyalty+.055+o.qty*.001,0,1);c.mood=clamp(c.mood+.09,0,1);c.cooldown=ri(8,25);c.lastSeen=S.tick;
    /* memory is written here and priced into the next offer */
    remember(c,{t:S.tick,k:'price',v:(o.wtp*.86-ask)/Math.max(1,o.wtp*.14),p:o.p,qty:o.qty});
    remember(c,{t:S.tick,k:'deal'});
    if(purity<o.minGrade+.04)remember(c,{t:S.tick,k:'grade',v:-.45,p:o.p});
    else if(purity>o.minGrade+.14)remember(c,{t:S.tick,k:'grade',v:.4,p:o.p});
  }
  for(const ct of S.contracts)if(!ct.done&&ct.d===o.cid&&ct.p===o.p)ct.qty+=o.qty;
  pushLog('deal','Deal closed · '+fmtU(o.qty)+' '+PRODUCTS[o.p].code+' @ '+fmtC(ask,2)+' → '+fmtC(gross),{d:o.cid,p:o.p});
  return{ok:true,success:true,msg:'Settled '+fmtC(gross)+' (unreconciled).'};
};
A.declineOffer=id=>{
  const o=S.offers.find(x=>x.id===id);if(!o)return;
  S.offers=S.offers.filter(x=>x!==o);
  const c=S.clients.find(x=>x.id===o.client);
  if(c){const mem=memScore(c);c.mood=clamp(c.mood-.02,0,1);c.cooldown=ri(6,16);
    remember(c,{t:S.tick,k:'refuse',p:o.p});
    if(mem>.3)c.loyalty=clamp(c.loyalty+.004,0,1);   /* a good relationship survives a no */
  }
};
A.hireCourier=()=>{const b=blocked();if(b)return b;if(S.couriers.length>=S.mods.maxCouriers)return{ok:false,msg:'Roster cap reached. Upgrade Logistics.'};
  if(S.cash<600)return{ok:false,msg:'Recruiting fee is ¤600.'};
  spend(600,'Recruitment fee','hire');S.couriers.push(mkCourier());
  pushNews('Crew',S.couriers[S.couriers.length-1].name+' joined the roster.','good');
  return{ok:true,msg:S.couriers[S.couriers.length-1].name+' hired.'};
};
A.fireCourier=id=>{const c=S.couriers.find(x=>x.id===id);if(!c||c.status!=='Idle')return{ok:false,msg:'Courier must be idle.'};S.couriers=S.couriers.filter(x=>x!==c);pushLog('crew',c.name+' released from the roster.');return{ok:true,msg:c.name+' released.'};};
A.courierAction=(id,act,val)=>{
  const c=S.couriers.find(x=>x.id===id);if(!c)return{ok:false,msg:'Unknown courier.'};
  if(act==='rest'){if(c.status!=='Idle')return{ok:false,msg:'Courier is busy.'};c.status='Rest';c.restT=10;return{ok:true,msg:'Resting 10h.'};}
  if(act==='train'){if(c.status!=='Idle')return{ok:false,msg:'Courier is busy.'};if(S.cash<450)return{ok:false,msg:'Training costs ¤450.'};spend(450,'Precision training','train');c.status='Train';c.trainT=14;return{ok:true,msg:'Training for 14h.'};}
  if(act==='wage'){c.wage=clamp(Math.round(val),60,600);c.morale=clamp(c.morale+.04,0,1);return{ok:true,msg:'Daily wage set to '+fmtC(c.wage)+'.'};}
  return{ok:false,msg:'Unknown action.'};
};
A.buyUpgrade=id=>{const b=blocked();if(b)return b;const u=UPGRADES.find(x=>x.id===id);if(!u)return{ok:false,msg:'Unknown upgrade.'};
  const lv=S.upgrades[id];if(lv>=u.max)return{ok:false,msg:'Already at maximum tier.'};
  const cost=Math.round(u.base*Math.pow(u.mult,lv));
  if(S.cash<cost)return{ok:false,msg:'Requires '+fmtC(cost)+' liquid cash.'};
  spend(cost,u.key+' tier '+(lv+1),'asset');S.upgrades[id]=lv+1;recomputeMods();
  pushNews('Asset',u.key+' upgraded to tier '+(lv+1)+'.','good');
  return{ok:true,msg:u.key+' → tier '+(lv+1)+'.'};
};
A.research=id=>{const b=blocked();if(b)return b;const r=RESEARCH.find(x=>x.id===id);if(!r)return{ok:false,msg:'Unknown node.'};
  if(S.research[id])return{ok:false,msg:'Already unlocked.'};
  for(const q of r.req)if(!S.research[q])return{ok:false,msg:'Prerequisite missing: '+RESEARCH.find(x=>x.id===q).key+'.'};
  if(S.points<r.cost)return{ok:false,msg:'Needs '+r.cost+' analysis points (you have '+Math.floor(S.points)+').'};
  const cash=r.cost*22;if(S.cash<cash)return{ok:false,msg:'Needs '+fmtC(cash)+' funding.'};
  S.points=r2(S.points-r.cost);spend(cash,'Research · '+r.key,'research');S.research[id]=true;recomputeMods();
  pushNews('Leads','✓ '+r.key+' — '+r.desc,'good');
  return{ok:true,msg:r.key+' unlocked.'};
};
A.diplomacy=(rid,act)=>{
  const r=S.rivals.find(x=>x.id===rid);if(!r)return{ok:false,msg:'Unknown syndicate.'};
  if(act==='parley'){
    const cost=Math.round(500+r.strength*700);
    if(S.cash<cost)return{ok:false,msg:'Tribute requires '+fmtC(cost)+'.'};
    spend(cost,'Tribute · '+r.name,'diplomacy');r.stance=clamp(r.stance+.28,-1,1);r.aggression=clamp(r.aggression-.10,0,1);
    pushNews('Crew',r.name+' accepts a parley. Tension reduced.','good');
    return{ok:true,msg:'Stance improved.'};
  }
  if(act==='contest'){
    const cost=900;if(S.cash<cost)return{ok:false,msg:'Contest requires '+fmtC(cost)+'.'};
    spend(cost,'Territory contest · '+r.name,'diplomacy');
    const power=clamp(.35+S.rep/220+mean(S.control)*.7+rr(-.2,.2),0,1.4);
    if(power>r.strength*rr(.8,1.2)){
      r.strength=clamp(r.strength-.09,.1,1);r.stance=clamp(r.stance-.15,-1,1);
      for(let d=0;d<ND;d++)S.control[d]=clamp(S.control[d]+rr(.015,.04),0,1);
      pushNews('Crew','Contest won: '+r.name+' loses ground in several districts.','good');
      return{ok:true,msg:'Territory gained.'};
    }else{
      r.stance=clamp(r.stance-.22,-1,1);S.heat=clamp(S.heat+7,0,100);
      for(let d=0;d<ND;d++)S.control[d]=clamp(S.control[d]-rr(.01,.03),0,1);
      pushNews('Crew','Contest failed: '+r.name+' holds. Attention rises.','bad');
      return{ok:true,success:false,msg:'Contest lost; heat increased.'};
    }
  }
  if(act==='truce'){
    if(r.stance<.1)return{ok:false,msg:'Stance too hostile for a truce.'};
    r.truce=72;r.aggression=clamp(r.aggression-.2,0,1);
    pushNews('Crew','72h truce agreed with '+r.name+'.','good');
    return{ok:true,msg:'Truce active for 72h.'};
  }
  return{ok:false,msg:'Unknown action.'};
};
A.layLow=()=>{const b=blocked();if(b)return b;if(S.cooldown>0)return{ok:false,msg:'Already lying low.'};
  S.cooldown=12;S.heat=clamp(S.heat-9,0,100);
  for(const L of S.listings)for(const l of L)l.enabled=false;
  for(let d=0;d<ND;d++)S.districts[d].heat=clamp(S.districts[d].heat*.82,0,100);
  pushNews('City','Voluntary 12h cool-down. Listings paused, scrutiny falling.','info');
  return{ok:true,msg:'Cool-down engaged (12h).'};
};
A.reconcile=amount=>{
  amount=Math.min(S.dirty,amount||S.dirty,S.mods.reconCap);
  if(amount<=0)return{ok:false,msg:'Nothing to reconcile.'};
  const fee=r2(amount*S.mods.reconFee);
  S.dirty=r2(S.dirty-amount);S.cash=r2(S.cash+amount-fee);
  pushLedger('recon','Manual reconciliation '+fmtC(amount),-fee,S.cash+S.dirty);
  return{ok:true,msg:fmtC(amount-fee)+' cleared after '+fmtC(fee)+' fee.'};
};
A.repayDebt=amount=>{
  amount=Math.min(S.debt,S.cash,amount||S.debt);
  if(amount<=0)return{ok:false,msg:'No debt or no cash.'};
  S.cash=r2(S.cash-amount);S.debt=r2(S.debt-amount);
  pushLedger('debt','Debt repayment',-amount,S.cash+S.dirty);
  return{ok:true,msg:fmtC(amount)+' repaid.'};
};
A.acceptContract=id=>{const c=S.contracts.find(x=>x.id===id);if(!c)return{ok:false,msg:'Not found.'};c.accepted=true;pushLog('contract','Standing order '+c.id+' tracked as priority.');return{ok:true,msg:'Order pinned to advisor.'};};
A.fireEvent=key=>{const d=Happenings.find(e=>e.key.toLowerCase()===String(key).toLowerCase());fireEvent(d||null);return{ok:true,msg:'Injected: '+(d?d.key:'random')};};

/* ------------------------------ persistence ------------------------------ */
function serialize(){const copy=JSON.parse(JSON.stringify(S));copy.settings=Object.assign({},S.settings);return JSON.stringify(copy);}
function deserialize(json){
  const o=JSON.parse(json);
  if(!o||o.version!==2411)throw new Error('Incompatible save version');
  S=o;S.spare=null;S.paused=true;S.eventBus=[];recomputeMods();
  if(!S.world)initWorld(S);
  if(!S.forecast)computeForecast();
  return S;
}
function serializeSettings(){return JSON.stringify(S?S.settings:{});}

/* ------------------------------ exports ---------------------------------- */
Object.assign(NL,{
  PRODUCTS,DISTRICTS,EDGES,WEATHER,TOD,TRAITS,UPGRADES,RESEARCH,Happenings,OBJECTIVES,
  newGame,step,serialize,deserialize,serializeSettings,computeForecast,priceOptimiser,optimalAsk,offerOdds,
  netWorth,markPrice,gradeValue,memScore,youSharp,you,distTravel,available,stockTotal,depotTotal,capacityUsed,fmtN,fmtC,fmtP,fmtU,fmtHour,fmtTick,
  esc,clamp,lerp,mean,std,hashStr,r2,r3,up,has,recomputeMods,pushLog,pushNews,poisson,
  getState:()=>S,actions:A,NP,ND,
  _setState:o=>{S=o;recomputeMods();}
});

/* UI layer continues in the same closure below. */

/* =====================================================================================
   Nightledger — UI INFRASTRUCTURE + Charts RENDERER
   ===================================================================================== */
const UI={};NL.UI=UI;G.NLUI=UI;
const $=s=>document.querySelector(s);
const $$=s=>Array.prototype.slice.call(document.querySelectorAll(s));
const el=(id)=>document.getElementById(id);
const chartSpecs={};
let modalStack=[];
UI.sel={view:'overview',p:0,d:4,mode:'price',offerId:null,density:'clean'};
UI.focusMode=false;UI.minimized=false;UI.lastRender=0;UI.renderCount=0;UI.logFilter='all';UI.consoleLines=[];
UI.cmdHistory=[];UI.cmdIndex=0;

/* ------------------------------ formatting helpers ----------------------- */
function delta(a,b,digits){if(b===undefined||b===null)return'<span class="dim">—</span>';const v=a-b;const c=v>=0?'up':'down';return'<span class="'+c+'">'+(v>=0?'▲':'▼')+' '+fmtN(Math.abs(v),digits===undefined?0:digits)+'</span>';}
function barHTML(v,cls,mark){return'<div class="bar '+(cls||'')+(mark!==undefined?'':'')+'"><i style="width:'+clamp(v*100,0,100).toFixed(1)+'%"></i>'+(mark!==undefined?'<span class="mark" style="left:'+clamp(mark*100,0,100)+'%"></span>':'')+'</div>';}
function tip(title,body){return' data-tip="'+esc(title)+'|'+esc(body)+'"';}
function kpi(lab,val,sub,spark,color,glyph,alert){
  return'<div class="kpi '+(alert?'alert':'')+'"'+(tip(lab,'Rolling 72-hour history. Hover any labelled value for a definition.'))+'>'+
    '<div class="lab">'+lab+'</div><div class="val" style="color:'+(color||'var(--txt)')+'">'+val+'</div>'+
    '<div class="delta">'+sub+'</div><div class="glyph">'+(glyph||'')+'</div>'+
    '<canvas data-chart="spark" data-id="'+spark.id+'"></canvas></div>';
}
function panel(title,body,extra,idx){
  return'<section class="panel '+(extra||'')+'"><div class="panel-h"><span class="cap">'+title+'</span><span class="spacer"></span><span class="idx">'+(idx||'')+'</span></div><div class="panel-b">'+body+'</div></section>';
}
function spec(id,type,data){chartSpecs[id]={type,data};return' id="'+id+'" data-chart="'+type+'" data-id="'+id+'"';}

/* ------------------------------ tooltips --------------------------------- */
UI.initTooltips=function(){
  const t=el('tooltip');
  document.addEventListener('mouseover',e=>{
    const n=e.target.closest?e.target.closest('[data-tip]'):null;
    if(!n){t.classList.remove('show');return;}
    const raw=n.getAttribute('data-tip')||'';const i=raw.indexOf('|');
    const title=i<0?'':raw.slice(0,i),body=i<0?raw:raw.slice(i+1);
    t.innerHTML='<b>'+esc(title)+'</b>'+body.replace(/\[k\](.*?)\[\/k\]/g,'<span class="k">$1</span>');
    t.classList.add('show');
    const r=n.getBoundingClientRect();
    let x=r.left,y=r.bottom+8;
    if(x+300>innerWidth)x=Math.max(8,innerWidth-300);
    if(y+130>innerHeight)y=Math.max(8,r.top-130);
    t.style.left=x+'px';t.style.top=y+'px';
  });
  document.addEventListener('mouseout',e=>{if(e.target.closest&&e.target.closest('[data-tip]'))t.classList.remove('show');});
  window.addEventListener('scroll',()=>t.classList.remove('show'),true);
};

/* ------------------------------ toasts ----------------------------------- */
UI.toast=function(title,msg,kind){
  if(typeof document==='undefined'||!el('toasts'))return;
  const d=document.createElement('div');d.className='toast '+(kind||'');
  d.innerHTML='<div class="t">'+esc(title)+'</div><div class="m">'+msg+'</div>';
  el('toasts').appendChild(d);
  UI.sfx(kind==='bad'?'bad':kind==='good'?'good':'click');
  setTimeout(()=>{d.style.opacity='0';d.style.transform='translateX(20px)';d.style.transition='.3s';setTimeout(()=>d.remove(),320);},4200);
  while(el('toasts').children.length>5)el('toasts').firstChild.remove();
};

/* ------------------------------ audio (WebAudio, synth only) ------------- */
let actx=null;
UI.sfx=function(kind){
  if(!S||!S.settings.sound||typeof window==='undefined'||!(window.AudioContext||window.webkitAudioContext))return;
  try{
    if(!actx)actx=new(window.AudioContext||window.webkitAudioContext)();
    const t=actx.currentTime,o=actx.createOscillator(),g=actx.createGain();
    const map={click:[520,.035,'square',.022],good:[740,.13,'sine',.05],bad:[190,.20,'sawtooth',.035],alert:[330,.16,'triangle',.04],tick:[90,.025,'sine',.012]};
    const m=map[kind]||map.click;
    o.type=m[2];o.frequency.setValueAtTime(m[0],t);o.frequency.exponentialRampToValueAtTime(m[0]*(kind==='bad'?.6:1.25),t+m[1]);
    g.gain.setValueAtTime(m[3],t);g.gain.exponentialRampToValueAtTime(.0001,t+m[1]);
    o.connect(g);g.connect(actx.destination);o.start(t);o.stop(t+m[1]+.01);
  }catch(e){}
};

/* ------------------------------ modal engine ----------------------------- */
UI.openModal=function(cfg){
  const scrim=document.createElement('div');scrim.className='modal-scrim';
  const m=document.createElement('div');m.className='modal '+(cfg.wide?'wide':cfg.slim?'slim':'');
  m.innerHTML='<div class="modal-h"><span class="ttl">'+esc(cfg.title||'')+'</span><span class="sub">'+esc(cfg.sub||'')+'</span><span class="spacer"></span><button class="btn ghost sm" data-mclose>✕ ESC</button></div>'+
    '<div class="modal-b">'+cfg.body+'</div>'+
    '<div class="modal-f"><span class="tiny dim" style="flex:1">'+(cfg.hint||'')+'</span>'+(cfg.footer!==null?(cfg.footer||'<button class="btn" data-mclose>Close</button>'):'')+'</div>';
  scrim.appendChild(m);el('modals').appendChild(scrim);
  modalStack.push({scrim,m,cfg});
  const close=()=>UI.closeModal(scrim);
  m.querySelectorAll('[data-mclose]').forEach(b=>b.addEventListener('click',close));
  scrim.addEventListener('mousedown',e=>{if(e.target===scrim)close();});
  if(cfg.onMount)cfg.onMount(m,close);
  UI.drawAllCharts();
  return{node:m,close};
};
UI.closeModal=function(scrim){
  if(!scrim){const last=modalStack[modalStack.length-1];if(last)scrim=last.scrim;}
  const i=modalStack.findIndex(x=>x.scrim===scrim);
  if(i>=0){modalStack[i].scrim.remove();modalStack.splice(i,1);}
};
UI.closeAllModals=function(){modalStack.slice().forEach(x=>UI.closeModal(x.scrim));};
UI.modalOpen=()=>modalStack.length>0;

/* ------------------------------ command palette -------------------------- */
UI.commands=[];
UI.registerCommands=function(){
  UI.commands=[
    {n:'Open the desk',k:'1',g:'View',f:()=>UI.setView('overview')},
    {n:'Open the market',k:'2',g:'View',f:()=>UI.setView('market')},
    {n:'Open operations',k:'3',g:'View',f:()=>UI.setView('operations')},
    {n:'Open the network',k:'4',g:'View',f:()=>UI.setView('network')},
    {n:'Open the ledger',k:'5',g:'View',f:()=>UI.setView('ledger')},
    {n:'Open the outlook',k:'6',g:'View',f:()=>UI.setView('intel')},
    {n:'Open the archive',k:'7',g:'View',f:()=>UI.setView('systems')},
    {n:'Look behind the ledger',k:'F3',g:'City',f:()=>UI.worldLens()},
    {n:'Service refining rig & gear',k:'',g:'City',f:()=>UI.act(A.serviceGear())},
    {n:'Seed a street rumour',k:'',g:'City',f:()=>UI.act(A.seedRumor())},
    {n:'See the deeper state',k:'',g:'City',f:()=>{if(S.settings.density!=='analyst')UI.toggleDensity();UI.setView('systems');}},
    {n:'Pause or resume the city',k:'Space',g:'Time',f:()=>UI.togglePause()},
    {n:'Rest eight hours',k:'R',g:'Time',f:()=>UI.rest()},
    {n:'Move one hour',k:'.',g:'Time',f:()=>{NL.step(1);UI.render(true);}},
    {n:'Let a day pass',k:'Shift+.',g:'Time',f:()=>{NL.step(24);UI.render(true);}},
    {n:'Show more or less detail',k:'F2',g:'Interface',f:()=>UI.toggleDensity()},
    {n:'Widen the desk',k:'F10',g:'Interface',f:()=>UI.toggleFocus()},
    {n:'Lay low for twelve hours',k:'',g:'Action',f:()=>UI.act(A.layLow())},
    {n:'Settle everything waiting',k:'',g:'Action',f:()=>UI.act(A.reconcile())},
    {n:'Clear the debt',k:'',g:'Action',f:()=>UI.act(A.repayDebt())},
    {n:'Run Looking ahead',k:'',g:'Action',f:()=>{NL.computeForecast();UI.toast('Outlook refreshed','A fresh 48-hour outlook is ready.','good');UI.render(true);}},
    {n:'Open field notes',k:'?',g:'Interface',f:()=>UI.manual()},
    {n:'Open options',k:'',g:'Interface',f:()=>UI.settings()},
    {n:'Save story',k:'Ctrl+S',g:'Interface',f:()=>UI.save(true)},
    {n:'Open district notes',k:'',g:'View',f:()=>UI.districtSheet(UI.sel.d)},
    {n:'Return to the title',k:'Esc',g:'Interface',f:()=>UI.toTitle()},
    {n:'Buy feedstock · base ×100',k:'',g:'Action',f:()=>UI.act(A.buyFeed('base',100))},
    {n:'Buy feedstock · additive ×100',k:'',g:'Action',f:()=>UI.act(A.buyFeed('additive',100))},
    {n:'Buy feedstock · packs ×100',k:'',g:'Action',f:()=>UI.act(A.buyFeed('packs',100))},
    {n:'Hire a courier',k:'',g:'Action',f:()=>UI.act(A.hireCourier())}
  ];
  for(let p=0;p<NP;p++)UI.commands.push({n:'Market · '+PRODUCTS[p].key,k:'',g:'Filter',f:()=>{UI.sel.p=p;UI.setView('market');}});
  for(let d=0;d<ND;d++)UI.commands.push({n:'Dossier · '+DISTRICTS[d].key,k:'',g:'View',f:()=>UI.districtSheet(d)});
};
UI.openPalette=function(){
  if(!el('palette'))return;
  el('palette').classList.add('show');UI.paletteSel=0;
  const inp=el('palette-input');inp.value='';inp.focus();UI.renderPalette();
  UI.sfx('click');
};
UI.closePalette=function(){el('palette').classList.remove('show');};
UI.filteredCommands=function(){
  const q=(el('palette-input').value||'').toLowerCase().trim();
  const list=UI.commands.filter(c=>!q||c.n.toLowerCase().includes(q)||c.g.toLowerCase().includes(q));
  return list.slice(0,40);
};
UI.renderPalette=function(){
  const list=UI.filteredCommands();UI.paletteList=list;
  if(UI.paletteSel>=list.length)UI.paletteSel=0;
  el('palette-list').innerHTML=list.length?list.map((c,i)=>'<div class="pitem '+(i===UI.paletteSel?'sel':'')+'" data-pi="'+i+'"><span class="ic">▸</span><span>'+esc(c.n)+'</span><span class="k">'+esc(c.k||c.g)+'</span></div>').join(''):'<div class="empty">Nothing matches.</div>';
};
UI.runPalette=function(i){
  const c=(UI.paletteList||[])[i];if(!c)return;
  UI.closePalette();try{c.f();}catch(e){UI.toast('That did not work',esc(e.message),'bad');}
};

/* ------------------------------ canvas plumbing -------------------------- */
function setupCanvas(c){
  if(!c||!c.getContext)return null;
  const dpr=Math.min(2,window.devicePixelRatio||1);
  const w=Math.max(40,c.clientWidth||c.parentElement.clientWidth||300),h=Math.max(30,c.clientHeight||c.parentElement.clientHeight||100);
  if(c.width!==Math.round(w*dpr)||c.height!==Math.round(h*dpr)){c.width=Math.round(w*dpr);c.height=Math.round(h*dpr);}
  const x=c.getContext('2d');x.setTransform(dpr,0,0,dpr,0,0);x.clearRect(0,0,w,h);
  return{x,w,h};
}
function grid(x,w,h,pad,rows,cols){
  x.strokeStyle='rgba(51,47,41,.09)';x.lineWidth=1;x.beginPath();
  for(let i=0;i<=rows;i++){const y=pad.t+(h-pad.t-pad.b)*i/rows;x.moveTo(pad.l,y+.5);x.lineTo(w-pad.r,y+.5);}
  for(let i=0;i<=cols;i++){const px=pad.l+(w-pad.l-pad.r)*i/cols;x.moveTo(px+.5,pad.t);x.lineTo(px+.5,h-pad.b);}
  x.stroke();
}
function hexA(hex,a){
  const h=hex.replace('#','');const n=parseInt(h.length===3?h.split('').map(c=>c+c).join(''):h,16);
  return'rgba('+((n>>16)&255)+','+((n>>8)&255)+','+(n&255)+','+a+')';
}
function drawSpark(c,data,color,opts){
  const C=setupCanvas(c);if(!C)return;const{x,w,h}=C;opts=opts||{};
  const a=(data&&data.length)?data.slice(-(opts.n||72)):[0,0];
  const mn=Math.min.apply(null,a),mx=Math.max.apply(null,a),rg=(mx-mn)||1;
  const px=i=>i/Math.max(1,a.length-1)*w,py=v=>h-2-((v-mn)/rg)*(h-5);
  x.beginPath();x.moveTo(0,h);
  a.forEach((v,i)=>x.lineTo(px(i),py(v)));
  x.lineTo(w,h);x.closePath();x.fillStyle=hexA(color||'#c9a25f',.12);x.fill();
  x.beginPath();a.forEach((v,i)=>i?x.lineTo(px(i),py(v)):x.moveTo(px(i),py(v)));
  x.strokeStyle=color||'#c9a25f';x.lineWidth=1.4;x.stroke();
  x.fillStyle=color||'#c9a25f';x.beginPath();x.arc(px(a.length-1),py(a[a.length-1]),2,0,7);x.fill();
}
function drawLine(c,series,opts){
  const C=setupCanvas(c);if(!C)return;const{x,w,h}=C;opts=opts||{};
  const pad={l:opts.padL||44,r:10,t:10,b:20};
  grid(x,w,h,pad,4,6);
  const all=series.reduce((a,s)=>a.concat(s.data.filter(v=>isFinite(v))),[]);
  let mn=opts.min!==undefined?opts.min:Math.min.apply(null,all),mx=opts.max!==undefined?opts.max:Math.max.apply(null,all);
  if(!isFinite(mn)||!isFinite(mx)){mn=0;mx=1;}
  if(mx-mn<.0001)mx=mn+1;
  const pad2=(mx-mn)*.08;mn-=pad2;mx+=pad2;
  const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
  const X=i=>pad.l+i/Math.max(1,(opts.len||Math.max.apply(null,series.map(s=>s.data.length)))-1)*pw;
  const Y=v=>pad.t+ph-(v-mn)/(mx-mn)*ph;
  x.font='9px Segoe UI, sans-serif';x.fillStyle='#b5b0a9';x.textAlign='right';
  for(let i=0;i<=4;i++){const v=mx-(mx-mn)*i/4;x.fillText(fmtN(v,opts.dec===undefined?0:opts.dec),pad.l-5,pad.t+ph*i/4+3);}
  x.textAlign='center';x.fillStyle='#8f8d87';
  for(let i=0;i<=6;i++)x.fillText((opts.xLabel?opts.xLabel(i/6):''),pad.l+pw*i/6,h-5);
  for(const s of series){
    x.beginPath();s.data.forEach((v,i)=>i?x.lineTo(X(i),Y(v)):x.moveTo(X(i),Y(v)));
    x.strokeStyle=s.color;x.lineWidth=s.width||1.7;x.globalAlpha=s.alpha||1;x.stroke();x.globalAlpha=1;
    if(s.fill){x.lineTo(X(s.data.length-1),pad.t+ph);x.lineTo(X(0),pad.t+ph);x.closePath();x.fillStyle=hexA(s.color,.08);x.fill();}
  }
  if(opts.hline!==undefined){x.setLineDash([4,4]);x.strokeStyle='rgba(52,48,42,.55)';x.beginPath();x.moveTo(pad.l,Y(opts.hline));x.lineTo(w-pad.r,Y(opts.hline));x.stroke();x.setLineDash([]);}
  /* crosshair */
  if(c._hover&&c._hover.x>=pad.l&&c._hover.x<=w-pad.r){
    const i=Math.round((c._hover.x-pad.l)/pw*((opts.len||series[0].data.length)-1));
    x.strokeStyle='rgba(58,53,47,.28)';x.setLineDash([3,3]);x.beginPath();x.moveTo(c._hover.x,pad.t);x.lineTo(c._hover.x,h-pad.b);x.stroke();x.setLineDash([]);
    let ty=pad.t+6;
    x.textAlign='left';x.font='9px Segoe UI, sans-serif';
    for(const s of series){const v=s.data[Math.min(i,s.data.length-1)];if(v===undefined)continue;x.fillStyle=s.color;x.fillText(s.name+': '+fmtN(v,1),Math.min(w-pad.r-90,c._hover.x+6),ty);ty+=11;}
  }
}
function drawFan(c,f){
  const C=setupCanvas(c);if(!C)return;const{x,w,h}=C;
  if(!f){x.fillStyle='#8f8d87';x.font='10px Segoe UI, sans-serif';x.fillText('No outlook yet',12,20);return;}
  const pad={l:48,r:12,t:12,b:22};grid(x,w,h,pad,4,6);
  const all=f.p10.concat(f.p90);let mn=Math.min.apply(null,all),mx=Math.max.apply(null,all);const pd=(mx-mn)*.12||1;mn-=pd;mx+=pd;
  const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
  const X=i=>pad.l+i/(f.H-1)*pw,Y=v=>pad.t+ph-(v-mn)/(mx-mn)*ph;
  x.beginPath();f.p90.forEach((v,i)=>i?x.lineTo(X(i),Y(v)):x.moveTo(X(i),Y(v)));
  for(let i=f.p10.length-1;i>=0;i--)x.lineTo(X(i),Y(f.p10[i]));
  x.closePath();x.fillStyle='rgba(54,50,45,.10)';x.fill();
  x.beginPath();f.p50.forEach((v,i)=>i?x.lineTo(X(i),Y(v)):x.moveTo(X(i),Y(v)));
  x.strokeStyle='#c9a25f';x.lineWidth=2;x.stroke();
  x.setLineDash([3,3]);x.strokeStyle='rgba(54,50,45,.6)';
  x.beginPath();f.p10.forEach((v,i)=>i?x.lineTo(X(i),Y(v)):x.moveTo(X(i),Y(v)));x.stroke();
  x.beginPath();f.p90.forEach((v,i)=>i?x.lineTo(X(i),Y(v)):x.moveTo(X(i),Y(v)));x.stroke();x.setLineDash([]);
  x.fillStyle='#b5b0a9';x.font='9px Segoe UI, sans-serif';x.textAlign='right';
  for(let i=0;i<=4;i++)x.fillText(fmtC(mx-(mx-mn)*i/4),pad.l-5,pad.t+ph*i/4+3);
  x.textAlign='center';x.fillText('Now',pad.l,h-5);x.fillText('+48H',w-pad.r,h-5);
}
function drawAttentionmap(c,matrix,rows,cols,opts){
  const C=setupCanvas(c);if(!C)return;const{x,w,h}=C;opts=opts||{};
  const pad={l:86,r:8,t:22,b:8},cw=(w-pad.l-pad.r)/cols.length,ch=(h-pad.t-pad.b)/rows.length;
  x.font='8px Segoe UI, sans-serif';x.textAlign='center';x.fillStyle='#b5b0a9';
  for(let j=0;j<cols.length;j++)x.fillText(cols[j],pad.l+cw*(j+.5),14);
  for(let i=0;i<rows.length;i++){
    x.textAlign='right';x.fillStyle='#c9a25f';x.font='9px Segoe UI, sans-serif';
    x.fillText(rows[i],pad.l-6,pad.t+ch*(i+.5)+3);
    for(let j=0;j<cols.length;j++){
      const v=matrix[i][j],n=clamp((v-.6)/.9,0,1);
      const col=v>1?'rgba(201,162,95,'+(0.12+n*.55)+')':'rgba(198,118,110,'+(0.10+(1-n)*.5)+')';
      x.fillStyle=col;x.fillRect(pad.l+cw*j+1,pad.t+ch*i+1,cw-2,ch-2);
      x.strokeStyle='rgba(10,9,8,.25)';x.strokeRect(pad.l+cw*j+1.5,pad.t+ch*i+1.5,cw-2,ch-2);
      if(opts.values){x.fillStyle='#7f9bb5';x.font='9px Segoe UI, sans-serif';x.textAlign='center';x.fillText(fmtN(v*100,0),pad.l+cw*(j+.5),pad.t+ch*(i+.5)+3);}
      if(c._hover&&c._hover.x>pad.l+cw*j&&c._hover.x<pad.l+cw*(j+1)&&c._hover.y>pad.t+ch*i&&c._hover.y<pad.t+ch*(i+1)){
        x.strokeStyle='#c9a25f';x.lineWidth=1.5;x.strokeRect(pad.l+cw*j+1,pad.t+ch*i+1,cw-2,ch-2);
      }
    }
  }
}
function drawCurve(c,curve,bm,opts){
  const C=setupCanvas(c);if(!C)return;const{x,w,h}=C;opts=opts||{};
  const pad={l:44,r:10,t:10,b:20};grid(x,w,h,pad,3,5);
  const vs=curve.map(v=>v[1]);let mn=Math.min.apply(null,vs),mx=Math.max.apply(null,vs);
  if(mx-mn<1){mx=mn+1;}const pd=(mx-mn)*.1;mn-=pd;mx+=pd;
  const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
  const X=m=>pad.l+(m-.55)/(2-.55)*pw,Y=v=>pad.t+ph-(v-mn)/(mx-mn)*ph;
  x.beginPath();curve.forEach((q,i)=>i?x.lineTo(X(q[0]),Y(q[1])):x.moveTo(X(q[0]),Y(q[1])));
  x.lineTo(X(2),Y(0));x.lineTo(X(.55),Y(0));x.closePath();x.fillStyle='rgba(54,50,45,.10)';x.fill();
  x.beginPath();curve.forEach((q,i)=>i?x.lineTo(X(q[0]),Y(q[1])):x.moveTo(X(q[0]),Y(q[1])));
  x.strokeStyle='#c9a25f';x.lineWidth=1.8;x.stroke();
  x.setLineDash([3,3]);x.strokeStyle='#d9a15b';x.beginPath();x.moveTo(X(bm),pad.t);x.lineTo(X(bm),h-pad.b);x.stroke();x.setLineDash([]);
  x.fillStyle='#b5b0a9';x.font='9px Segoe UI, sans-serif';x.textAlign='right';
  for(let i=0;i<=3;i++)x.fillText(fmtN(mx-(mx-mn)*i/3),pad.l-5,pad.t+ph*i/3+3);
  x.textAlign='center';for(let m=.6;m<=2;m+=.35)x.fillText(m.toFixed(2)+'×',X(m),h-5);
  x.fillStyle='#d9a15b';x.textAlign='left';x.fillText('Suggested '+bm.toFixed(2)+'×',Math.min(w-90,X(bm)+4),pad.t+10);
}
function drawBars(c,items,opts){
  const C=setupCanvas(c);if(!C)return;const{x,w,h}=C;opts=opts||{};
  const pad={l:opts.padL||70,r:12,t:8,b:18},n=items.length,gap=4;
  const bh=(h-pad.t-pad.b)/n, mx=Math.max.apply(null,items.map(i=>Math.abs(i.v)).concat([1]));
  x.font='9px Segoe UI, sans-serif';
  for(let i=0;i<n;i++){
    const it=items[i],y=pad.t+i*bh,bw=Math.max(1,(Math.abs(it.v)/mx)*(w-pad.l-pad.r));
    x.fillStyle='#c9a25f';x.textAlign='right';x.fillText(it.k,pad.l-6,y+bh/2+3);
    x.fillStyle='#8f8d87';x.fillRect(pad.l,y+gap,w-pad.l-pad.r,bh-gap*2);
    x.fillStyle=it.c||'#c9a25f';x.fillRect(pad.l,y+gap,bw,bh-gap*2);
    if(opts.values){x.fillStyle='#7f9bb5';x.textAlign='left';x.fillText(it.t||fmtN(it.v,1),pad.l+bw+4,y+bh/2+3);}
  }
}
function drawMap(c,opts){
  const C=setupCanvas(c);if(!C)return;const{x,w,h}=C;opts=opts||{};
  const pad=26,px=(v)=>pad+v*(w-pad*2),py=(v)=>pad+v*(h-pad*2);
  /* faint district boundaries */
  x.save();x.strokeStyle='rgba(54,50,45,.045)';x.lineWidth=1;
  for(let i=0;i<8;i++){x.beginPath();x.arc(w*.5,h*.48,(i+1)*40,0,7);x.stroke();}
  x.restore();
  /* links */
  for(const e of EDGES){
    const a=DISTRICTS[e[0]],b=DISTRICTS[e[1]];
    x.beginPath();x.moveTo(px(a.x),py(a.y));x.lineTo(px(b.x),py(b.y));
    x.strokeStyle='rgba(55,51,45,.14)';x.lineWidth=1;x.stroke();
  }
  /* courier routes */
  if(opts.routes!==false){
    for(const cr of S.couriers){
      if(cr.dest<0)continue;
      const t=1-clamp(cr.eta/6,0,1);
      const ax=px(.5),ay=py(.5),bx=px(DISTRICTS[cr.dest].x),by=py(DISTRICTS[cr.dest].y);
      x.beginPath();x.moveTo(ax,ay);x.lineTo(bx,by);x.setLineDash([4,5]);x.strokeStyle='rgba(52,48,42,.45)';x.lineWidth=1.2;x.stroke();x.setLineDash([]);
      const cx=lerp(ax,bx,t),cy=lerp(ay,by,t);
      x.fillStyle='#d9a15b';x.beginPath();x.arc(cx,cy,3.2,0,7);x.fill();
      x.fillStyle='rgba(52,48,42,.18)';x.beginPath();x.arc(cx,cy,7,0,7);x.fill();
    }
  }
  /* HQ */
  x.strokeStyle='rgba(54,50,45,.55)';x.lineWidth=1;x.strokeRect(px(.5)-5,py(.5)-5,10,10);
  x.fillStyle='#c9a25f';x.font='8px Segoe UI, sans-serif';x.textAlign='center';x.fillText('HQ',px(.5),py(.5)-9);
  /* districts */
  const t=Date.now()/1000;
  for(let d=0;d<ND;d++){
    const B=DISTRICTS[d],D=S.districts[d],cx=px(B.x),cy=py(B.y);
    const demand=mean(D.demand),ctrl=S.control[d];
    const heat=D.heat/100;
    const rad=10+clamp(demand*1.8,0,12)+Math.sin(t*1.6+d)*.9;
    const col=opts.heat?hexA('#c9a25f',.18+heat*.5):hexA('#c9a25f',.10+ctrl*.35);
    x.beginPath();x.arc(cx,cy,rad+8,0,7);x.fillStyle=col;x.fill();
    x.beginPath();x.arc(cx,cy,rad,0,7);
    x.fillStyle='#171513';x.fill();
    x.strokeStyle=opts.heat?hexA('#c9a25f',.4+heat*.6):hexA('#c9a25f',.35+ctrl*.6);x.lineWidth=1.6;x.stroke();
    /* influence arc */
    x.beginPath();x.arc(cx,cy,rad+3,-PI/2,-PI/2+2*PI*clamp(ctrl,0,1));
    x.strokeStyle='#c9a25f';x.lineWidth=2.4;x.stroke();
    /* core dot */
    x.fillStyle=heat>.65?'#c9a25f':heat>.35?'#d9a15b':'#c9a25f';
    x.beginPath();x.arc(cx,cy,3,0,7);x.fill();
    x.fillStyle='#b5b0a9';x.font='9px Segoe UI, sans-serif';x.textAlign='center';
    x.fillText(B.short,cx,cy+rad+15);
    x.fillStyle='#8f8d87';x.font='8px Segoe UI, sans-serif';
    x.fillText(fmtP(ctrl,0)+' · '+fmtN(D.heat,0)+'°',cx,cy+rad+25);
    if(c._hover&&Math.hypot(c._hover.x-cx,c._hover.y-cy)<rad+8){
      x.strokeStyle='#c9a25f';x.lineWidth=1.5;x.beginPath();x.arc(cx,cy,rad+11,0,7);x.stroke();
    }
  }
  /* scan sweep */
  const sy=(t*22)%h;const g=x.createLinearGradient(0,sy-30,0,sy+30);
  g.addColorStop(0,'rgba(54,50,45,0)');g.addColorStop(.5,'rgba(54,50,45,.035)');g.addColorStop(1,'rgba(54,50,45,0)');
  x.fillStyle=g;x.fillRect(0,sy-30,w,60);
}
function drawNetwork(c){
  const C=setupCanvas(c);if(!C)return;const{x,w,h}=C;
  const pad=24,px=v=>pad+v*(w-pad*2),py=v=>pad+v*(h-pad*2);
  for(const e of EDGES){const a=DISTRICTS[e[0]],b=DISTRICTS[e[1]];x.beginPath();x.moveTo(px(a.x),py(a.y));x.lineTo(px(b.x),py(b.y));x.strokeStyle='rgba(55,51,45,.10)';x.stroke();}
  for(const cl of S.clients){
    const B=DISTRICTS[cl.district],ang=cl.id*2.399,r=13+((cl.id*7)%13);
    const cx=px(B.x)+Math.cos(ang)*r,cy=py(B.y)+Math.sin(ang)*r;
    x.beginPath();x.arc(cx,cy,cl.loyalty>.65?3:1.8,0,7);
    x.fillStyle=TRAITS[cl.trait].col;x.globalAlpha=.35+cl.loyalty*.65;x.fill();x.globalAlpha=1;
    if(c._hover&&Math.hypot(c._hover.x-cx,c._hover.y-cy)<5){x.strokeStyle='#fff';x.lineWidth=1;x.beginPath();x.arc(cx,cy,5,0,7);x.stroke();}
  }
  for(let d=0;d<ND;d++){
    const B=DISTRICTS[d];x.beginPath();x.arc(px(B.x),py(B.y),6,0,7);x.fillStyle='#1a1816';x.fill();x.strokeStyle='rgba(54,50,45,.4)';x.stroke();
    x.fillStyle='#d9a15b';x.font='9px Segoe UI, sans-serif';x.textAlign='center';x.fillText(B.short,px(B.x),py(B.y)+19);
  }
}
UI.drawAllCharts=function(root){
  const scope=root||document;
  scope.querySelectorAll('canvas[data-chart]').forEach(c=>{
    const id=c.getAttribute('data-id'),sp=chartSpecs[id];if(!sp)return;
    try{
      const t=sp.type,d=sp.data;
      if(t==='spark')drawSpark(c,d.a,d.color,d.opts);
      else if(t==='line')drawLine(c,d.series,d.opts);
      else if(t==='fan')drawFan(c,d);
      else if(t==='heat')drawAttentionmap(c,d.matrix,d.rows,d.cols,d.opts);
      else if(t==='curve')drawCurve(c,d.curve,d.bm,d.opts);
      else if(t==='bars')drawBars(c,d.items,d.opts);
      else if(t==='map')drawMap(c,d.opts);
      else if(t==='net')drawNetwork(c,d);
    }catch(e){if(NL.DEBUG_CHARTS)throw e;/* keep the frame alive if a chart spec is stale */}
  });
};
UI.initCanvasHover=function(){
  document.addEventListener('mousemove',e=>{
    const c=e.target.closest?e.target.closest('canvas'):null;
    if(!c)return;const r=c.getBoundingClientRect();c._hover={x:e.clientX-r.left,y:e.clientY-r.top};
    if(c.getAttribute('data-chart')&&UI.focusMode===false&&Math.random()<.35)UI.drawAllCharts();
  });
  document.addEventListener('mouseout',e=>{if(e.target.tagName==='Charts')e.target._hover=null;});
};

/* ------------------------------ chrome / ledger ----------------------------- */
UI.renderTop=function(){
  if(!S)return;
  const hist=S.history;
  el('clockface').textContent=fmtHour(S.hour);
  el('clockday').textContent='Day '+String(S.day).padStart(2,'0')+' · '+(S.paused?'❚❚ The evening is on hold':S.hour>=20||S.hour<6?'Evening':S.hour<12?'Morning':'Afternoon');
  const W=WEATHER[S.weather];el('weatherchip').textContent=W.key;el('weatherchip').style.color=W.col;
  el('s-cash').textContent=fmtC(S.cash);
  el('s-cash-d').innerHTML=delta(S.cash,hist.cash.length>24?hist.cash[hist.cash.length-25]:null)+' / 24h';
  const nw=netWorth();el('s-worth').textContent=fmtC(nw);
  el('s-worth-d').innerHTML=delta(nw,hist.worth.length>24?hist.worth[hist.worth.length-25]:null)+' / 24h';
  const heatC=S.heat>70?'var(--rd)':S.heat>40?'var(--am)':'var(--cy)';
  el('s-heat').textContent=fmtN(S.heat,1);el('s-heat').style.color=heatC;
  el('s-heat-d').textContent=S.heat>70?'Too much notice':S.heat>45?'Getting warm':S.heat>20?'Worth watching':'Quiet';
  el('s-rep').textContent=fmtN(S.rep,1);
  el('s-rep-d').textContent='Standing '+Math.min(5,Math.floor(S.rep/20)+1);
  el('s-terr').textContent=fmtP(mean(S.control),0);
  el('s-terr-d').textContent=S.control.filter(c=>c>=.35).length+' districts on side';
  el('crumb').textContent=({overview:'The desk',market:'Market',operations:'Operations',network:'Network',ledger:'Ledger',intel:'Outlook',systems:'Archive'})[UI.sel.view];
  el('seedtag').textContent='Story '+hashStr(String(S.seed)).slice(0,6).toUpperCase();
  el('st-tick').textContent=fmtN(S.tick);
  el('st-agents').textContent=fmtN(S.clients.length+S.couriers.length+S.rivals.length+ND*NP);
  el('st-events').textContent=S.eventBus.length;
  el('st-solver').textContent=fmtN(S.diag.solverIter);
  el('st-entropy').textContent=r3(S.diag.entropy);
  el('st-rng').textContent=(S.rs>>>0).toString(16).slice(0,6).toUpperCase();
  el('st-hash').textContent=S.diag.hash;
  if(el('st-world'))el('st-world').textContent=S.world?(S.world.stats.hours+'H / '+S.world.mods.length+' quiet effects'):'—';
  $$('.speedbtn[data-speed]').forEach(b=>b.classList.toggle('on',+b.getAttribute('data-speed')===S.speed&&!S.paused));
  el('btn-pause').classList.toggle('on',S.paused);
  el('btn-pause').textContent=S.paused?'▶':'❚❚';
  el('badge-offers').textContent=S.offers.length;el('badge-offers').classList.toggle('hidden',S.offers.length===0);
  const ops=S.jobs.length+S.couriers.filter(c=>c.status!=='Idle').length;
  el('badge-ops').textContent=ops;el('badge-ops').classList.toggle('hidden',ops===0);
};
UI.renderSide=function(){
  if(!S)return;
  const adv=UI.advisor();
  el('advisor').innerHTML=adv.slice(0,4).map((a,i)=>'<div class="advisor-card" data-advisor="'+i+'"'+tip(a.t,a.d)+'><div class="t">'+a.t+'</div><div class="d">'+a.d+'</div><div class="pr">'+a.pr+'</div></div>').join('')||'<div class="empty">Nothing urgent. The evening is steady.</div>';
  el('advisor-count').textContent=Math.min(4,adv.length);
  UI.advisorList=adv;
  const ops=[];
  for(const j of S.jobs)ops.push({n:'Workshop · '+PRODUCTS[j.p].key+' '+j.tag,p:fmtP(j.progress/j.hours,0)});
  for(const c of S.couriers)if(c.status!=='Idle'&&c.dest>=0)ops.push({n:c.name.split(' ')[0]+' → '+DISTRICTS[c.dest].short,p:c.eta+'H'});
  for(const c of S.couriers)if(c.status==='Rest'||c.status==='Train')ops.push({n:c.name.split(' ')[0]+' · '+c.status,p:c.restT||c.trainT+'H'});
  el('side-ops').innerHTML=ops.length?ops.map(o=>'<div class="op-row"><span class="tag c">●</span><span class="n">'+esc(o.n)+'</span><span class="p">'+o.p+'</span></div>').join(''):'<div class="empty">No active operations.<br>Queue a refining run or dispatch a courier.</div>';
  el('ops-count').textContent=ops.length;
  const f=S.log.slice(0,22).filter(l=>UI.logFilter==='all'||l.type===UI.logFilter);
  el('side-feed').innerHTML=f.length?f.map(l=>{
    const c={alert:'var(--rd)',deal:'var(--gr)',sale:'var(--cy)',lab:'var(--vi)',ops:'var(--bl)',sys:'var(--dim)',crew:'var(--am)',contract:'var(--gr)'}[l.type]||'var(--dim)';
    return'<div class="feed-item"><span class="ft">'+fmtTick(l.t).slice(1)+'</span><span class="fx" style="border-left:2px solid '+c+';padding-left:6px">'+esc(l.text)+'</span></div>';
  }).join(''):'<div class="empty">No activity recorded.</div>';
};
UI.advisor=function(){
  if(!S)return[];
  const a=[];
  const hot=S.heat>58;
  if(hot)a.push({t:'Reduce exposure',d:'Global heat is '+fmtN(S.heat,0)+'. Pause listings and take a 12h cool-down.',pr:'Too much notice · needs attention',go:()=>UI.confirm('Engage cool-down?','All active listings will pause for 12 hours. Scrutiny will fall.','Lay low',()=>UI.act(A.layLow()))});
  const exp=S.offers.filter(o=>o.ttl<=3).length;
  if(exp)a.push({t:'Buyers waiting',d:exp+' buyer '+(exp===1?'request is':'requests are')+' about to lapse.',pr:'Before it lapses',go:()=>UI.setView('market')});
  const idle=S.couriers.filter(c=>c.status==='Idle').length;
  const unlisted=[];
  for(let d=0;d<ND;d++)for(let p=0;p<NP;p++)if(S.depot[d][p].qty>2&&!S.listings[d][p].enabled)unlisted.push([d,p,S.depot[d][p].qty]);
  if(unlisted.length)a.push({t:'Stock sitting still',d:fmtU(unlisted.reduce((s,u)=>s+u[2],0))+' across '+unlisted.length+' depots is not listed for retail.',pr:'Money sitting still',go:()=>{UI.sel.d=unlisted[0][0];UI.sel.p=unlisted[0][1];UI.setView('market');}});
  if(S.feed.base<80||S.feed.additive<50)a.push({t:'Wholesale stock low',d:'The workshop will stall without wholesale stock.',pr:'Wholesale',go:()=>UI.setView('operations')});
  if(S.dirty>400)a.push({t:'Unsettled revenue',d:fmtC(S.dirty)+' is waiting on reconciliation capacity.',pr:'Cashflow',go:()=>UI.act(A.reconcile())});
  if(S.debt>0)a.push({t:'Debt outstanding',d:fmtC(S.debt)+' accrues hourly interest.',pr:'Worth a look',go:()=>UI.setView('ledger')});
  if(idle>0&&S.lots.length)a.push({t:'A courier is free',d:idle+' crew idle at HQ with warehouse lots ready to move.',pr:'Stock could move',go:()=>UI.setView('operations')});
  if(S.points>RESEARCH.filter(r=>!S.research[r.id]).reduce((m,r)=>Math.min(m,r.cost),1e9))a.push({t:'A new lead is open',d:'You have enough leads for a new contact.',pr:'A longer view',go:()=>UI.setView('intel')});
  const soon=S.contracts.filter(c=>!c.done&&c.deadline-S.tick<14&&c.qty<c.need);
  if(soon.length)a.push({t:'An order is nearly due',d:soon.length+' standing order '+(soon.length===1?'is':'are')+' short with under 14h left.',pr:'A promise is due',go:()=>UI.setView('network')});
  if(S.world){
    const W=S.world;
    if(W.gear.maintenanceDue)a.push({t:'Workshop service due',d:'Rig wear '+fmtP(W.gear.rigWear,1)+' is depressing yield and purity ceilings.',pr:'Wear and tear',go:()=>UI.act(A.serviceGear())});
    if(W.calendar.monthDay===4||W.calendar.monthDay===19)a.push({t:'Payday tomorrow',d:'Consumer power rises ~10% tomorrow. Stock premium goods in wealthy districts tonight.',pr:'The calendar',go:()=>UI.setView('operations')});
    if(W.dossier.evidence>18)a.push({t:'Dossier building',d:W.dossier.reports.length+' witness reports and '+W.dossier.threads.length+' evidence chains are raising audit severity.',pr:'Attention on you',go:()=>UI.act(A.layLow())});
    const hotRumor=W.rumors.nodes.reduce((x,y)=>y.strength>x.strength?y:x,{strength:0});
    if(hotRumor.strength>.5)a.push({t:'A rumour is moving',d:'"'+hotRumor.topic+'" is moving prices. Check the market surface before posting asks.',pr:'Word on the street',go:()=>UI.setView('market')});
  }
  if(!a.length)a.push({t:'Check the outlook',d:'See the next two days before committing cash.',pr:'Before you commit',go:()=>{NL.computeForecast();UI.setView('intel');}});
  return a;
};

/* =====================================================================================
   Nightledger — VIEWS
   Each view is a pure HTML builder; charts are registered and drawn after mounting.
   ===================================================================================== */
const V={};UI.views=V;
function regSpark(id,a,color,opts){chartSpecs[id]={type:'spark',data:{a:a.slice(-90),color:color||'#c9a25f',opts:opts||{}}};return{id};}
function sectionHead(t,right){return'<div class="row" style="margin-bottom:9px"><span class="cap" style="font-size:10px;color:var(--txt)">'+t+'</span><span class="spacer"></span>'+(right||'')+'</div>';}
function priceChange(d,p){
  const cur=S.districts[d].price[p],base=PRODUCTS[p].base*Math.pow(DISTRICTS[d].wealth,.32);
  return r2((cur/base-1)*100);
}
function topGap(){
  const gaps=[];
  for(let p=0;p<NP;p++){
    let lo=0,hi=0;
    for(let d=1;d<ND;d++){if(S.districts[d].price[p]<S.districts[lo].price[p])lo=d;if(S.districts[d].price[p]>S.districts[hi].price[p])hi=d;}
    const spread=S.districts[hi].price[p]-S.districts[lo].price[p];
    gaps.push({p,lo,hi,spread,pct:spread/Math.max(1,S.districts[lo].price[p])});
  }
  return gaps.sort((a,b)=>b.pct-a.pct);
}

/* -------------------------------- OVERVIEW -------------------------------- */
V.overview=function(){
  const h=S.history,nw=netWorth();
  const kpis=
    kpi('Liquid cash',fmtC(S.cash),delta(S.cash,h.cash.length>24?h.cash[h.cash.length-25]:null)+' <span class="dim">/24h</span>',regSpark('sp-cash',h.cash,'#c9a25f'),'var(--cy)','Balance',false)+
    kpi('Net worth',fmtC(nw),delta(nw,h.worth.length>24?h.worth[h.worth.length-25]:null)+' <span class="dim">/24h</span>',regSpark('sp-worth',h.worth,'#7f9c72'),'var(--gr)','Mark',false)+
    kpi('Global heat',fmtN(S.heat,1),(S.heat>60?'<span class="down">Too much notice</span>':S.heat>35?'<span class="warnc">Getting warm</span>':'<span class="up">Contained</span>')+' <span class="dim">· '+fmtP(S.heat/S.mods.auditThreshold,0)+' to audit</span>',regSpark('sp-heat',h.heat,'#c9a25f'),S.heat>60?'var(--rd)':'var(--am)','Risk',S.heat>70)+
    kpi('Reputation',fmtN(S.rep,1),'<span class="dim">Standing '+Math.min(5,Math.floor(S.rep/20)+1)+' · '+S.clients.length+' contacts</span>',regSpark('sp-rep',h.rep,'#c9a25f'),'var(--vi)','Social',false)+
    kpi('Influence',fmtP(mean(S.control),0),'<span class="dim">'+S.control.filter(c=>c>=.35).length+' / '+ND+' districts held</span>',regSpark('sp-terr',h.price,'#d9a15b'),'var(--am)','Territory',false);

  chartSpecs['map-main']={type:'map',data:{opts:{heat:UI.sel.showAttention,routes:S.settings.showRoutes}}};
  const mapHTML='<div class="row" style="margin-bottom:8px;gap:6px">'+
    '<button class="btn sm '+(UI.sel.showAttention?'':'on')+'" data-act="mapmode" data-v="demand">Demand</button>'+
    '<button class="btn sm '+(UI.sel.showAttention?'on':'')+'" data-act="mapmode" data-v="heat">Attention Overlay</button>'+
    '<span class="spacer"></span><span class="tiny dim">CLICK A NODE FOR Notes</span></div>'+
    '<div class="canvas-wrap" style="height:318px"><canvas style="width:100%;height:100%" id="map-main" data-chart="map" data-id="map-main" data-act="mapclick" data-tip="City graph|Node radius = aggregate demand, ring = your influence, core colour = local scrutiny. Couriers are shown as amber dots on their route."></canvas></div>'+
    '<div class="legend"><span><i style="background:#c9a25f"></i>Influence ring</span><span><i style="background:#d9a15b"></i>Courier in transit</span><span><i style="background:#c9a25f"></i>High scrutiny</span><span class="adv"><i style="background:#c6766e"></i>Logistics edges (Dijkstra-weighted)</span></div>'+
    '<div class="divider"></div><div class="grid g4" style="gap:7px">'+
    S.control.map((c,d)=>'<button class="card" style="text-align:left;padding:7px" data-act="district" data-d="'+d+'"><div class="row" style="gap:5px"><span class="tiny mono" style="color:var(--txt)">'+DISTRICTS[d].short+'</span><span class="spacer"></span><span class="tiny mono '+(S.districts[d].heat>55?'down':'dim')+'">'+fmtN(S.districts[d].heat,0)+'°</span></div>'+barHTML(c,'',null)+'<div class="tiny dim" style="margin-top:4px">'+fmtP(c,0)+' control</div></button>').join('')+'</div>';

  const pulse='<div class="grid" style="gap:0">'+
    PRODUCTS.map((pr,p)=>{
      const avg=mean(S.districts.map(d=>d.price[p])),ch=mean(S.districts.map((d,i)=>priceChange(i,p)));
      return'<div class="row" style="padding:5px 0;border-bottom:1px solid #191715;gap:8px">'+
        '<span style="width:8px;height:8px;border-radius:1px;background:'+pr.color+'"></span>'+
        '<span class="mono" style="width:64px;color:var(--txt);font-size:10px">'+pr.key+'</span>'+
        '<span class="spacer"></span><span class="num" style="font-size:11px;color:var(--txt)">'+fmtC(avg,2)+'</span>'+
        '<span class="num '+(ch>=0?'up':'down')+'" style="width:52px;text-align:right;font-size:10px">'+(ch>=0?'+':'')+fmtN(ch,0)+'%</span>'+
        '<button class="btn ghost sm" data-act="setp" data-p="'+p+'" title="Open market for '+pr.key+'">▸</button></div>';
    }).join('')+'</div>'+
    '<div class="divider"></div><div class="statline"><span>Macro index</span><b>'+r3(S.macro)+'</b></div>'+
    '<div class="statline"><span>Consumer mood</span><b>'+r3(S.mood)+'</b></div>'+
    '<div class="statline"><span>Scrutiny cycle</span><b>'+fmtP(S.scrutiny,1)+'</b></div>'+
    '<div class="statline"><span>Active market events</span><b>'+S.activeEvents.length+'</b></div>'+
    '<div class="statline adv"><span>Seasonal component</span><b>'+r3(S.season)+'</b></div>'+
    '<div class="statline adv"><span>Aggregate latent demand</span><b>'+fmtN(mean(S.districts.map(d=>mean(d.demand))),2)+'</b></div>';

  const feed=['base','additive','packs'].map(k=>{
    const cap=k==='packs'?6000:9000;
    return'<div style="margin-bottom:7px"><div class="row" style="font-size:10px"><span class="cap">'+k+'</span><span class="spacer"></span><b class="num">'+fmtN(S.feed[k])+'</b><span class="dim num">/'+fmtN(cap)+'</span></div>'+barHTML(S.feed[k]/cap,'b')+'</div>';
  }).join('');
  const supply='<div class="row" style="margin-bottom:9px"><div style="flex:1"><div class="cap">Warehouse capacity</div><div class="num" style="font-size:15px">'+fmtU(stockTotal())+' <span class="dim" style="font-size:10px">/ '+fmtU(S.mods.capacity)+'</span></div></div>'+
    '<div style="flex:1"><div class="cap">Lots / jobs</div><div class="num" style="font-size:15px">'+S.lots.length+' <span class="dim">/</span> '+S.jobs.length+'</div></div></div>'+
    barHTML(stockTotal()/S.mods.capacity,'v')+feed+
    '<div class="divider"></div><div class="statline"><span>Crew on roster</span><b>'+S.couriers.length+' / '+S.mods.maxCouriers+'</b></div>'+
    '<div class="statline"><span>Total deliveries</span><b>'+S.stats.deliveries+'</b></div>'+
    '<div class="statline"><span>Units sold (lifetime)</span><b>'+fmtU(S.stats.unitsSold)+'</b></div>'+
    '<button class="btn sm" style="width:100%;margin-top:9px" data-act="go" data-v="operations">Open operations ▸</button>';

  const pressure='<div class="statline"><span>Global heat</span><b style="color:'+(S.heat>60?'var(--rd)':'var(--cy)')+'">'+fmtN(S.heat,1)+' / '+fmtN(S.mods.auditThreshold,0)+'</b></div>'+
    barHTML(S.heat/S.mods.auditThreshold, S.heat>60?'r':'a')+
    '<div class="divider"></div>'+S.districts.map((D,d)=>'<div style="margin-bottom:6px"><div class="row" style="font-size:10px"><span class="tiny mono" style="width:70px;color:var(--txt2)">'+DISTRICTS[d].short+'</span>'+
      '<span class="spacer"></span><span class="tiny dim">risk '+fmtP(DISTRICTS[d].risk,0)+'</span><span class="num tiny" style="width:34px;text-align:right">'+fmtN(D.heat,0)+'°</span></div>'+barHTML(D.heat/100,D.heat>60?'r':'a')+'</div>').join('')+
    '<div class="notice '+(S.heat>60?'r':'c')+'" style="margin-top:8px">'+(S.cooldown>0?'Cool-down active · '+S.cooldown+'h remaining':S.heat>60?'Audit risk is elevated. Consider pausing listings.':'Exposure within tolerance.')+'</div>'+
    '<button class="btn sm warn" style="width:100%;margin-top:8px" data-act="laylow">Lay low for 12h</button>';

  const done=OBJECTIVES.filter(o=>S.objectives[o.id]).length;
  const milestones='<div class="row" style="margin-bottom:9px"><span class="cap">Campaign progress</span><span class="spacer"></span><span class="tag c">'+done+' / '+OBJECTIVES.length+'</span></div>'+
    barHTML(done/OBJECTIVES.length,'g')+'<div class="divider"></div>'+
    OBJECTIVES.slice(0,6).map(o=>'<div class="row" style="padding:4px 0;border-bottom:1px dashed #1b1916;font-size:10px;gap:6px"><span style="color:'+(S.objectives[o.id]?'var(--gr)':'var(--mute)')+'">'+(S.objectives[o.id]?'✓':'○')+'</span><span style="color:'+(S.objectives[o.id]?'var(--dim)':'var(--txt2)')+'">'+o.key+'</span><span class="spacer"></span><span class="tiny dim">'+fmtC(o.reward)+'</span></div>').join('')+
    '<button class="btn sm" style="width:100%;margin-top:9px" data-act="go" data-v="intel">Open outlook ▸</button>';

  return'<div class="grid g5">'+kpis+'</div>'+UI.worldTicker()+
    '<div class="grid g32" style="margin-top:11px">'+panel('City map · current conditions',mapHTML,'','01 · map')+panel('Market at a glance',pulse,'','02 · prices')+'</div>'+
    '<div class="grid g3" style="margin-top:11px">'+panel('Wholesale',supply,'','03 · ops')+panel('Attention on you',pressure,'','04 · attention')+panel('Milestones',milestones,'','05 · goals')+'</div>'+
    '<div class="grid g2 adv" style="margin-top:11px">'+panel('Behind the ledger · detail',
      '<div class="grid g4">'+['Tick '+S.tick,'Market '+S.diag.solverIter+' it/h','Variation '+r3(S.diag.entropy),'People '+fmtN(S.clients.length+S.couriers.length+ND*NP)].map(t=>'<div class="card"><div class="t num">'+t+'</div></div>').join('')+'</div>'+
      '<div class="divider"></div><div class="statline"><span>Last tick compute</span><b>'+r3(S.diag.lastMs)+' ms</b></div><div class="statline"><span>State hash</span><b>'+S.diag.hash+'</b></div><div class="statline"><span>chance thread cursor</span><b>0x'+(S.rs>>>0).toString(16).toUpperCase()+'</b></div>','','06 · notes')+
      panel('A few things you can do',
        UI.youStrip()+
    '<div class="row wrap" style="gap:6px"><button class="btn sm" data-act="rest8">Rest 8h</button><button class="btn sm" data-act="forecast">Refresh outlook</button><button class="btn sm" data-act="recon">Settle</button><button class="btn sm" data-act="gounlock">RESEARCH</button><button class="btn sm" data-act="save">Save</button></div>'+
        '<div class="notice" style="margin-top:10px">Tip: press <span class="kbd">Ctrl</span>+<span class="kbd">K</span> for the command palette. <span class="kbd">F2</span> reveals the analyst layer with raw market figures.</div>','','07 · actions')+'</div>';
};

/* --------------------------------- MarkET --------------------------------- */
V.market=function(){
  const p=UI.sel.p,d=UI.sel.d,pr=PRODUCTS[p],D=S.districts[d];
  const chips=PRODUCTS.map((q,i)=>'<button class="chip '+(i===p?'on':'')+'" data-act="setp" data-p="'+i+'"'+tip(q.key,q.blurb+' Elasticity '+q.elast.toFixed(2)+', volatility '+fmtP(q.vol,0)+'.')+'>'+q.code+'</button>').join('');
  const matrix=S.districts.map(D=>D.price.map((v,j)=>v/Math.max(1,PRODUCTS[j].base)));
  chartSpecs['mkt-heat']={type:'heat',data:{matrix,rows:DISTRICTS.map(x=>x.short),cols:PRODUCTS.map(x=>x.code),opts:{values:true}}};
  const matrixHTML='<div class="row" style="margin-bottom:8px;gap:5px">'+chips+'</div>'+
    '<div class="canvas-wrap" style="height:246px"><canvas style="width:100%;height:100%" id="mkt-heat" data-chart="heat" data-id="mkt-heat" data-act="heatclick" data-tip="Price surface|Cell value = district clearing price ÷ commodity baseline. Green = premium, red = discount. Click a cell to inspect that pair."></canvas></div>'+
    '<div class="legend"><span><i style="background:rgba(54,50,45,.6)"></i>Premium</span><span><i style="background:rgba(54,50,45,.5)"></i>Discount</span><span class="tiny dim">Values = index × 100</span></div>'+
    '<div class="divider"></div>'+sectionHead('Price differences','<span class="tiny dim">Price differences</span>')+
    '<div class="grid" style="gap:0">'+topGap().slice(0,5).map(g=>'<div class="row" style="font-size:10px;padding:4px 0;border-bottom:1px dashed #1b1916;gap:6px">'+
      '<span style="width:8px;height:8px;background:'+PRODUCTS[g.p].color+';border-radius:1px"></span><span class="mono" style="width:52px">'+PRODUCTS[g.p].code+'</span>'+
      '<span class="tiny dim">'+DISTRICTS[g.lo].short+' → '+DISTRICTS[g.hi].short+'</span><span class="spacer"></span>'+
      '<span class="num up">+'+fmtP(g.pct,0)+'</span><button class="btn ghost sm" data-act="setpd" data-p="'+g.p+'" data-d="'+g.hi+'">▸</button></div>').join('')+'</div>';

  const opt=priceOptimiser(d,p),dep=S.depot[d][p],L=S.listings[d][p];
  chartSpecs['mkt-curve']={type:'curve',data:{curve:opt.curve,bm:opt.m}};
  const book='<div class="row" style="margin-bottom:8px;gap:5px">'+DISTRICTS.map((b,i)=>'<button class="chip '+(i===d?'on':'')+'" data-act="setd" data-d="'+i+'">'+b.short+'</button>').join('')+'</div>'+
    '<div class="row" style="gap:10px;margin-bottom:9px"><div><div class="cap">Clearing price</div><div class="num" style="font-size:19px;color:'+pr.color+'">'+fmtC(D.price[p],2)+'</div></div>'+
    '<div><div class="cap">Hidden appetite</div><div class="num" style="font-size:19px">'+fmtN(D.demand[p],1)+'</div></div>'+
    '<div><div class="cap">Depot stock</div><div class="num" style="font-size:19px">'+fmtU(dep.qty)+'</div></div><span class="spacer"></span>'+
    '<button class="btn sm" data-act="district" data-d="'+d+'">Notes ▸</button></div>'+
    '<div class="canvas-wrap" style="height:124px"><canvas style="width:100%;height:100%" id="mkt-curve" data-chart="curve" data-id="mkt-curve" data-tip="Expected-profit surface|Grid search over ask multipliers: (ask − marginal cost) × elastic quantity × close probability. Amber marker = optimum."></canvas></div>'+
    '<div class="grid g4" style="margin-top:9px;gap:6px">'+
      [['Suggested ask',fmtC(opt.ask,2)],['Optimum ×',r2(opt.m)+'×'],['Marginal cost',fmtC(opt.cost,2)],['Expected units',fmtU(opt.q)]].map(q=>'<div class="card" style="padding:6px"><div class="cap" style="font-size:8px">'+q[0]+'</div><div class="num" style="font-size:12px;margin-top:2px">'+q[1]+'</div></div>').join('')+'</div>'+
    '<div class="divider"></div>'+sectionHead('Post or update a price','<span class="tag '+(L.enabled?'g':'')+'">'+(L.enabled?'Active':'Idle')+'</span>')+
    '<div class="grid g3" style="gap:7px"><div class="field"><label>Quantity (max '+fmtU(dep.qty)+')</label><input class="inp" id="mk-qty" type="number" min="0" step="0.5" value="'+(L.qty||Math.min(10,dep.qty)).toFixed(1)+'"></div>'+
    '<div class="field"><label>Ask per unit</label><input class="inp" id="mk-ask" type="number" min="1" step="0.5" value="'+(L.ask||opt.ask).toFixed(2)+'"></div>'+
    '<div class="field"><label>Pricing policy</label><select id="mk-mode"><option value="manual"'+(L.mode==='manual'?' selected':'')+'>Manual</option><option value="auto"'+(L.mode==='auto'?' selected':'')+'>Auto-optimiser</option></select></div></div>'+
    '<div class="row" style="margin-top:9px;gap:6px"><button class="btn primary" data-act="post">Post a price</button><button class="btn sm" data-act="autofill">Use suggested price</button><button class="btn sm ghost" data-act="clearlisting">Clear</button><span class="spacer"></span><span class="tiny dim">Retail clears hourly</span></div>'+
    '<div class="divider"></div><div class="statline adv"><span>Elasticity ε</span><b>'+pr.elast.toFixed(2)+'</b></div>'+
    '<div class="statline adv"><span>Rival supply</span><b>'+fmtN(D.rival[p],2)+'</b></div>'+
    '<div class="statline adv"><span>Buyer fatigue</span><b>'+fmtP(D.sat[p],1)+'</b></div>'+
    '<div class="statline adv"><span>Local loyalty</span><b>'+fmtP(D.loyalty,1)+'</b></div>'+
    '<div class="statline adv"><span>Vol state</span><b>'+r3(S.prod[p].volState)+'</b></div>'+
    '<div class="statline adv"><span>Price smoothing α</span><b>0.34</b></div>';

  const offers=S.offers.slice().sort((a,b)=>a.ttl-b.ttl);
  const offersHTML=offers.length?'<div class="scrollbox"><table class="tbl zebra"><thead><tr><th>Buyer</th><th>District</th><th>Good</th><th class="r">QTY</th><th class="r">Offer</th><th class="r adv cell">Likely budget.</th><th class="r">MIN Pure</th><th class="r">TTL</th><th class="r">Odds</th><th></th></tr></thead><tbody>'+
    offers.map(o=>{
      const c=S.clients.find(x=>x.id===o.client),t=TRAITS[o.trait],odd=offerOdds(o,o.offer);
      const stock=S.depot[o.cid][o.p].qty>=o.qty&&S.depot[o.cid][o.p].purity>=o.minGrade;
      return'<tr><td class="strong">'+esc(c?c.name:'—')+' <span class="tag" style="color:'+t.col+'">'+t.key+'</span></td>'+
        '<td>'+DISTRICTS[o.cid].short+'</td><td style="color:'+PRODUCTS[o.p].color+'">'+PRODUCTS[o.p].code+'</td>'+
        '<td class="r">'+fmtU(o.qty)+'</td><td class="r strong">'+fmtC(o.offer,2)+'</td>'+
        '<td class="r adv cell">'+fmtC(o.wtp,2)+'</td><td class="r">'+fmtP(o.minGrade,0)+'</td>'+
        '<td class="r '+(o.ttl<=3?'down':'')+'">'+o.ttl+'h</td><td class="r '+(odd>.7?'up':odd<.4?'down':'warnc')+'">'+fmtP(odd,0)+'</td>'+
        '<td class="r"><button class="btn sm '+(stock?'primary':'')+'" data-act="offer" data-id="'+o.id+'">'+(stock?'Deal':'No stock')+'</button> <button class="btn ghost sm" data-act="decline" data-id="'+o.id+'">✕</button></td></tr>';
    }).join('')+'</tbody></table></div>':'<div class="empty">No live buyer requests.<br>Offers arrive as client mood, loyalty and district demand align.</div>';

  return'<div class="grid g32">'+panel('Prices across the city',matrixHTML,'','08 · prices')+panel('Buyer requests · '+DISTRICTS[d].short+' · '+pr.key,book,'','09 · buyers')+'</div>'+
    '<div class="grid g32" style="margin-top:11px">'+panel('People asking to buy',offersHTML,'','10 · requests')+
    panel('Goods · '+pr.key,'<div class="row" style="gap:10px;margin-bottom:10px"><div style="width:34px;height:34px;background:'+hexA(pr.color,.18)+';border:1px solid '+pr.color+';border-radius:3px;display:flex;align-items:center;justify-content:center;color:'+pr.color+';font-family:var(--mono);font-size:11px">'+pr.code+'</div><div><div class="t" style="font-size:13px;color:var(--txt)">'+pr.key+'</div><div class="tiny dim">Standing '+pr.tier+' · baseline '+fmtC(pr.base)+'</div></div></div>'+
      '<div class="notice c">'+pr.blurb+'</div><div class="divider"></div>'+
      '<div class="statline"><span>Demand elasticity</span><b>'+pr.elast.toFixed(2)+'</b></div>'+
      '<div class="statline"><span>Volatility σ</span><b>'+fmtP(pr.vol,1)+'</b></div>'+
      '<div class="statline"><span>Buyer fatigue decay</span><b>'+fmtP(pr.decay,2)+'</b></div>'+
      '<div class="statline"><span>Repeat-purchase stickiness</span><b>'+fmtP(pr.stick,0)+'</b></div>'+
      '<div class="statline"><span>Lifetime revenue</span><b>'+fmtC(S.pnls[p].rev)+'</b></div>'+
      '<div class="statline"><span>Units moved</span><b>'+fmtU(S.pnls[p].units)+'</b></div>'+
      '<div class="divider"></div>'+sectionHead('Prices today')+
      S.districts.map((D,i)=>'<div style="margin-bottom:5px"><div class="row" style="font-size:10px"><span class="tiny mono" style="width:70px">'+DISTRICTS[i].short+'</span><span class="spacer"></span><span class="num">'+fmtC(D.price[p],2)+'</span></div>'+barHTML(D.price[p]/(pr.base*2),'b')+'</div>').join('')+
      '<div class="adv"><div class="divider"></div><div class="notice">Market: <span class="mono">P = base · (D/S)^(1/ε) · wealth^0.32 · macro · shock</span>, smoothed with α=.34 toward fair value each hour.</div></div>','','11 · assets')+'</div>';
};

/* ------------------------------- Operations ------------------------------- */
V.operations=function(){
  const cap=S.mods.capacity,used=stockTotal();
  const feedRows=[['base','Base stock',9000],['additive','Additive',9000],['packs','Packaging',6000]].map(([k,label,mx])=>{
    const fp=S.feedPrice[k],drift=(fp/({base:7.2,additive:11,packs:1.4}[k])-1)*100;
    return'<div class="row" style="gap:8px;padding:6px 0;border-bottom:1px solid #191715">'+
      '<div style="flex:1"><div class="row" style="font-size:10px"><span style="color:var(--txt)">'+label+'</span><span class="spacer"></span><span class="num">'+fmtN(S.feed[k])+' u</span></div>'+barHTML(S.feed[k]/mx,'b')+'</div>'+
      '<div style="width:74px;text-align:right"><div class="num" style="font-size:12px">'+fmtC(fp,2)+'</div><div class="tiny '+(drift>=0?'down':'up')+'">'+(drift>=0?'+':'')+fmtN(drift,1)+'%</div></div>'+
      '<input class="inp" style="width:68px" type="number" min="1" value="100" id="feed-'+k+'">'+
      '<button class="btn sm" data-act="buyfeed" data-kind="'+k+'">Buy</button></div>';
  }).join('');
  const procure=panel('Buy wholesale',feedRows+
    '<div class="divider"></div><div class="row"><div style="flex:1"><div class="cap">Warehouse</div><div class="num" style="font-size:16px">'+fmtU(used)+' / '+fmtU(cap)+'</div></div><div style="flex:1"><div class="cap">Refining slots</div><div class="num" style="font-size:16px">'+S.jobs.length+' / '+S.mods.labSlots+'</div></div></div>'+barHTML(used/cap,'v')+
    '<div class="notice" style="margin-top:9px">Wholesale prices follow their own mean-reverting walk with supply-shock events. Buying into a glut is cheap but ties up cash.</div>','','12 · wholesale');

  const lots=S.lots.slice().sort((a,b)=>b.qty-a.qty);
  const lotsHTML=lots.length?'<div class="scrollbox"><table class="tbl zebra"><thead><tr><th>LOT</th><th>Good</th><th class="r">QTY</th><th class="r">Grade</th><th class="r">Unit Cost</th><th class="r">Mark</th><th class="r adv cell">AGE</th><th></th></tr></thead><tbody>'+
    lots.map(l=>{const mk=markPrice(l.p,l.purity),gain=(mk-l.cost)/Math.max(1,l.cost);
      return'<tr><td class="mono strong">'+l.tag+'</td><td style="color:'+PRODUCTS[l.p].color+'">'+PRODUCTS[l.p].key+'</td>'+
        '<td class="r strong">'+fmtU(l.qty)+'</td><td class="r"><span class="tag '+(l.purity>.9?'g':l.purity>.7?'c':'a')+'">'+fmtP(l.purity,1)+'</span></td>'+
        '<td class="r">'+fmtC(l.cost,2)+'</td><td class="r '+(gain>=0?'up':'down')+'">'+fmtC(mk,2)+'</td>'+
        '<td class="r adv cell">'+fmtP(l.age,1)+'</td>'+
        '<td class="r"><button class="btn sm primary" data-act="dispatch" data-id="'+l.id+'">Send ▸</button></td></tr>';}).join('')+
    '</tbody></table></div>':'<div class="empty">Warehouse empty.<br>Queue a refining job to create a lot.</div>';
  const inventory=panel('Warehouse & lots',lotsHTML+
    '<div class="divider"></div><div class="statline"><span>Mark-to-market inventory</span><b>'+fmtC(S.lots.reduce((a,l)=>a+l.qty*markPrice(l.p,l.purity)*.72,0))+'</b></div>'+
    '<div class="statline adv"><span>Effective decay multiplier</span><b>'+r2(S.mods.decay)+'</b></div>','','13 · stock');

  const jobs=S.jobs.length?S.jobs.map(j=>'<div class="card" style="margin-bottom:7px"><div class="row"><span class="mono" style="color:var(--txt)">'+j.tag+'</span><span class="spacer"></span><span class="tiny dim">'+PRODUCTS[j.p].key+' · target '+fmtP(j.target,0)+'</span></div>'+
    '<div style="margin:6px 0">'+barHTML(j.progress/j.hours,'v')+'</div><div class="row tiny dim"><span>'+fmtU(j.qty)+' input</span><span class="spacer"></span><span>'+fmtP(j.progress/j.hours,0)+' · '+(j.hours-j.progress).toFixed(1)+'h left</span></div></div>').join(''):'<div class="empty">No active refining runs.</div>';
  const refinery=panel('Workshop queue',jobs+'<div class="divider"></div>'+sectionHead('Schedule a run')+
    '<div class="grid g3" style="gap:7px"><div class="field"><label>Output commodity</label><select id="job-p">'+PRODUCTS.map((q,i)=>'<option value="'+i+'" '+(i===UI.sel.p?'selected':'')+'>'+q.key+' · T'+q.tier+'</option>').join('')+'</select></div>'+
    '<div class="field"><label>INPUT units</label><input class="inp" id="job-q" type="number" min="1" max="200" value="30"></div>'+
    '<div class="field"><label>Target purity <span id="job-t-val" class="cyc">'+fmtP(clamp(S.mods.maxGrade*.9,.4,.99),0)+'</span></label><input type="range" id="job-t" min="40" max="99" value="'+Math.round(clamp(S.mods.maxGrade*.9,.4,.99)*100)+'"></div></div>'+
    '<div class="row" style="margin-top:9px;gap:6px"><button class="btn primary" data-act="startjob">Queue a run</button><span class="spacer"></span><span class="tiny dim">cap '+fmtP(S.mods.maxGrade,0)+' · yield '+fmtP(S.mods.yield,0)+'</span></div>'+
    '<div class="notice adv" style="margin-top:9px">Yield = input × (rig tier + process control) × N(1,.05). Grade = ceiling × U(.82,1) + N(0,.045) + operator boost. Feedstock demand scales with target grade.</div>','','14 · workshop');

  const couriers=S.couriers.map(c=>{
    const st={Idle:['Idle','g'],Outbound:['On the move','a'],Returning:['Returning','a'],Rest:['Resting','c'],Train:['Training','v']}[c.status];
    return'<div class="card" style="margin-bottom:8px"><div class="row"><div style="width:26px;height:26px;border-radius:2px;background:#1f1c19;border:1px solid var(--line2);display:flex;align-items:center;justify-content:center;font-family:var(--mono);color:var(--cy)">'+c.name[0]+'</div>'+
      '<div><div class="t">'+esc(c.name)+'</div><div class="s">'+c.runs+' runs · '+fmtN(c.xp,0)+' XP</div></div><span class="spacer"></span><span class="tag '+st[1]+'">'+st[0]+(c.eta?' '+c.eta+'H':'')+'</span></div>'+
      '<div class="grid g2" style="gap:5px;margin-top:8px">'+
      [['Skill',c.skill,'b'],['Stealth',c.stealth,'v'],['Stamina',c.stamina,'g'],['Precision',c.precision,'']].map(q=>'<div><div class="row tiny dim"><span>'+q[0]+'</span><span class="spacer"></span><span class="num">'+fmtP(q[1],0)+'</span></div>'+barHTML(q[1],q[2])+'</div>').join('')+'</div>'+
      '<div class="grid g2" style="gap:5px;margin-top:6px">'+
      [['Morale',c.morale,c.morale<.3?'r':'g'],['Fatigue',c.fatigue,c.fatigue>.7?'r':'a'],['Loyalty',c.loyalty,'v'],['Wage',c.wage/600,'b']].map(q=>'<div><div class="row tiny dim"><span>'+q[0]+'</span><span class="spacer"></span><span class="num">'+(q[0]==='Wage'?fmtC(c.wage)+'/d':fmtP(q[1],0))+'</span></div>'+barHTML(q[1],q[2])+'</div>').join('')+'</div>'+
      '<div class="row" style="margin-top:8px;gap:5px"><button class="btn sm" data-act="crew" data-id="'+c.id+'" data-v="rest"'+(c.status!=='Idle'?' disabled':'')+'>Rest 10h</button>'+
      '<button class="btn sm" data-act="crew" data-id="'+c.id+'" data-v="train"'+(c.status!=='Idle'?' disabled':'')+'>Train 14h</button>'+
      '<input class="inp" style="width:64px" type="number" min="60" max="600" step="10" value="'+c.wage+'" data-wage="'+c.id+'">'+
      '<button class="btn ghost sm" data-act="setwage" data-id="'+c.id+'">SET</button><span class="spacer"></span>'+
      '<button class="btn ghost sm danger" data-act="fire" data-id="'+c.id+'">✕</button></div></div>';
  }).join('');
  const crew=panel('Your crew',couriers+'<button class="btn" style="width:100%;margin-top:4px" data-act="hire">+ Hire a courier · '+fmtC(600)+'</button>'+
    '<div class="notice adv" style="margin-top:8px">Travel time = Dijkstra shortest path × congestion(heat, weather) ÷ logistics tier. Complication probability = base × (1 + heat/55) × (1 + fatigue) × (1 − stealth·.55). Wages and fatigue are charged hourly.</div>','','15 · crew');

  return'<div class="grid g2">'+procure+inventory+'</div><div class="grid g23" style="margin-top:11px">'+refinery+crew+'</div>';
};

/* -------------------------------- NETWork --------------------------------- */
V.network=function(){
  chartSpecs['net-graph']={type:'net',data:{}};
  const graph='<div class="canvas-wrap" style="height:250px"><canvas style="width:100%;height:100%" id="net-graph" data-chart="net" data-id="net-graph" data-tip="Relationship graph|Each dot is a contact orbiting its home district. Brightness = loyalty. Colour = behavioural trait."></canvas></div>'+
    '<div class="legend">'+Object.keys(TRAITS).map(k=>'<span><i style="background:'+TRAITS[k].col+'"></i>'+TRAITS[k].key+'</span>').join('')+'</div>'+
    '<div class="divider"></div>'+sectionHead('Where you have a foothold')+
    S.control.map((c,d)=>'<div style="margin-bottom:5px"><div class="row" style="font-size:10px"><span class="tiny mono" style="width:74px">'+DISTRICTS[d].short+'</span><span class="spacer"></span><span class="tiny dim">rival '+fmtP(mean(S.rivals.map(r=>r.territory[d])),0)+'</span><span class="num" style="width:38px;text-align:right">'+fmtP(c,0)+'</span></div>'+barHTML(c,'')+'</div>').join('');
  const clients=S.clients.slice().sort((a,b)=>b.loyalty-a.loyalty);
  const clientHTML='<div class="scrollbox" style="max-height:430px"><table class="tbl zebra"><thead><tr><th>Contact</th><th>District</th><th>Trait</th><th>Pref</th><th class="r">Loyalty</th><th class="r">Mood</th><th class="r adv cell">Budget</th><th class="r">Deals</th><th class="r">Last</th></tr></thead><tbody>'+
    clients.map(c=>'<tr><td class="strong">'+esc(c.name)+'</td><td>'+DISTRICTS[c.district].short+'</td>'+
      '<td><span class="tag" style="color:'+TRAITS[c.trait].col+'">'+TRAITS[c.trait].key+'</span></td>'+
      '<td style="color:'+PRODUCTS[c.pref].color+'">'+PRODUCTS[c.pref].code+'</td>'+
      '<td class="r"><span class="num">'+fmtP(c.loyalty,0)+'</span><div style="margin-top:3px">'+barHTML(c.loyalty,'g')+'</div></td>'+
      '<td class="r">'+fmtP(c.mood,0)+'</td><td class="r adv cell">'+fmtC(c.budget)+'</td>'+
      '<td class="r">'+c.deals+'</td><td class="r dim">'+(S.tick-c.lastSeen)+'h</td></tr>').join('')+'</tbody></table></div>'+
    '<div class="statline"><span>Contacts above 70% loyalty</span><b>'+S.clients.filter(c=>c.loyalty>=.7).length+' / 8 needed</b></div>';

  const rivals=S.rivals.map(r=>'<div class="card" style="margin-bottom:8px;border-left:2px solid '+r.col+'"><div class="row"><span class="t" style="color:'+r.col+'">'+r.name+'</span><span class="spacer"></span><span class="tag '+(r.truce>0?'g':r.stance<-.2?'r':'a')+'">'+(r.truce>0?'Truce '+r.truce+'H':r.stance<-.2?'Hostile':r.stance>.3?'Cooperative':'Neutral')+'</span></div>'+
    '<div class="grid g3" style="gap:5px;margin:8px 0">'+[['Strength',r.strength,'r'],['Aggression',r.aggression,'a'],['Stance',(r.stance+1)/2,'v']].map(q=>'<div><div class="row tiny dim"><span>'+q[0]+'</span><span class="spacer"></span><span class="num">'+(q[0]==='Stance'?r2(r.stance):fmtP(q[1],0))+'</span></div>'+barHTML(q[1],q[2])+'</div>').join('')+'</div>'+
    '<div class="row" style="gap:5px"><button class="btn sm" data-act="dip" data-r="'+r.id+'" data-v="parley">Talk '+fmtC(500+r.strength*700)+'</button>'+
    '<button class="btn sm warn" data-act="dip" data-r="'+r.id+'" data-v="contest">Push back '+fmtC(900)+'</button>'+
    '<button class="btn sm" data-act="dip" data-r="'+r.id+'" data-v="truce">Truce</button></div></div>').join('');
  const contracts=S.contracts.filter(c=>!c.done).map(c=>'<div class="card" style="margin-bottom:7px"><div class="row"><span class="mono strong">ORDER #'+c.id+'</span><span class="spacer"></span><span class="tag '+(c.deadline-S.tick<12?'r':'c')+'">'+(c.deadline-S.tick)+'H LEFT</span></div>'+
    '<div class="tiny dim" style="margin:5px 0">'+fmtU(c.need)+' '+PRODUCTS[c.p].key+' → '+DISTRICTS[c.d].short+' · reward '+fmtC(c.reward)+' · penalty '+fmtC(c.penalty)+'</div>'+
    barHTML(c.qty/c.need,'g')+'<div class="row tiny dim" style="margin-top:4px"><span>'+fmtU(c.qty)+' / '+fmtU(c.need)+' delivered</span><span class="spacer"></span><button class="btn ghost sm" data-act="pin" data-id="'+c.id+'">PIN</button></div></div>').join('')||'<div class="empty">No standing orders.<br>New contracts arrive every 26–46 hours.</div>';

  return'<div class="grid g32">'+panel('Territory & relationships',graph,'','16 · network')+
    panel('Other crews',rivals+'<div class="divider"></div>'+sectionHead('Standing orders')+contracts,'','17 · crews')+'</div>'+
    '<div style="margin-top:11px">'+panel('Contacts · '+S.clients.length+' Active',clientHTML,'','18 · contacts')+'</div>';
};

/* -------------------------------- LEDGER ---------------------------------- */
V.ledger=function(){
  const rev=S.stats.revenue,cost=S.stats.costs,net=rev-cost;
  chartSpecs['led-chart']={type:'line',data:{series:[{name:'Cash',data:S.history.cash.slice(-180),color:'#c9a25f',fill:true},{name:'What you are worth',data:S.history.worth.slice(-180),color:'#7f9c72'},{name:'Attention ×100',data:S.history.heat.slice(-180).map(v=>v*30),color:'#c9a25f',width:1}],opts:{xLabel:t=>'-'+Math.round((1-t)*180)+'h',dec:0}}};
  const chart='<div class="canvas-wrap" style="height:216px"><canvas style="width:100%;height:100%" id="led-chart" data-chart="line" data-id="led-chart" data-tip="Balance history|Cash, mark-to-market net worth, and a scaled heat trace. Hover for values."></canvas></div>'+
    '<div class="legend"><span><i style="background:#c9a25f"></i>Liquid cash</span><span><i style="background:#7f9c72"></i>Net worth</span><span><i style="background:#c9a25f"></i>Attention (scaled)</span></div>'+
    '<div class="divider"></div><div class="grid g4" style="gap:7px">'+
    [['Lifetime revenue',fmtC(rev),'up'],['Lifetime costs',fmtC(cost),'down'],['Net flow',fmtC(net),net>=0?'up':'down'],['Assessments paid',fmtC(S.stats.fines),'down']].map(q=>'<div class="card" style="padding:7px"><div class="cap" style="font-size:8px">'+q[0]+'</div><div class="num '+q[2]+'" style="font-size:14px;margin-top:3px">'+q[1]+'</div></div>').join('')+'</div>';
  const recon='<div class="row" style="gap:10px"><div style="flex:1"><div class="cap">Unsettled revenue</div><div class="num" style="font-size:20px;color:var(--am)">'+fmtC(S.dirty)+'</div></div>'+
    '<div style="flex:1"><div class="cap">Debt</div><div class="num" style="font-size:20px;color:'+(S.debt>0?'var(--rd)':'var(--txt)')+'">'+fmtC(S.debt)+'</div></div></div>'+
    '<div class="divider"></div><div class="statline"><span>Hourly reconciliation cap</span><b>'+fmtC(S.mods.reconCap/6)+'</b></div>'+
    '<div class="statline"><span>Effective fee</span><b>'+fmtP(S.mods.reconFee,1)+'</b></div>'+
    '<div class="statline"><span>Auto-reconciliation</span><b>'+(S.autoRecon?'On':'Off')+'</b></div>'+
    '<div class="row" style="margin-top:9px;gap:6px"><button class="btn primary" data-act="recon">Settle Now</button>'+
    '<button class="btn sm" data-act="togglerecon">'+(S.autoRecon?'Turn off auto':'Turn on auto')+'</button>'+
    '<button class="btn sm" data-act="repay">Repay debt</button></div>'+
    '<div class="notice" style="margin-top:9px">Sales settle into an unsettled balance. Settling up converts it to spendable cash, capped by your front-company tier and charged a fee. Upgrade to move more per hour.</div>'+
    '<div class="divider"></div>'+sectionHead('Equipment & premises')+
    UPGRADES.map(u=>{const lv=S.upgrades[u.id],c=Math.round(u.base*Math.pow(u.mult,lv));
      return'<div class="row" style="padding:5px 0;border-bottom:1px dashed #1b1916;gap:7px"><span style="width:6px;height:6px;background:'+u.col+';border-radius:1px"></span>'+
      '<div style="flex:1"><div class="tiny" style="color:var(--txt)">'+u.key+' <span class="tag">T'+lv+'</span></div><div class="tiny dim">'+u.desc+'</div></div>'+
      '<button class="btn sm" data-act="upgrade" data-id="'+u.id+'"'+(lv>=u.max?' disabled':'')+'>'+(lv>=u.max?'Full':fmtC(c))+'</button></div>';}).join('');
  const pnl='<div class="scrollbox"><table class="tbl zebra"><thead><tr><th>Commodity</th><th class="r">Units</th><th class="r">Revenue</th><th class="r">AVG / Unit</th><th class="r">Share</th></tr></thead><tbody>'+
    PRODUCTS.map((q,p)=>{const o=S.pnls[p];return'<tr><td style="color:'+q.color+'" class="strong">'+q.key+'</td><td class="r">'+fmtU(o.units)+'</td><td class="r">'+fmtC(o.rev)+'</td><td class="r">'+(o.units?fmtC(o.rev/o.units,2):'—')+'</td><td class="r">'+fmtP(o.rev/Math.max(1,rev),0)+'</td></tr>';}).join('')+'</tbody></table></div>'+
    '<div class="divider"></div>'+sectionHead('Where the money comes from')+
    S.districtPnl.map((v,d)=>'<div style="margin-bottom:4px"><div class="row tiny"><span class="mono" style="width:74px">'+DISTRICTS[d].short+'</span><span class="spacer"></span><span class="num">'+fmtC(v)+'</span></div>'+barHTML(v/Math.max(1,...S.districtPnl),'b')+'</div>').join('');
  const tx='<div class="scrollbox" style="max-height:300px"><table class="tbl zebra"><thead><tr><th>Time</th><th>Type</th><th>Note</th><th class="r">Amount</th><th class="r adv cell">Balance</th></tr></thead><tbody>'+
    S.ledger.slice(0,40).map(l=>'<tr><td class="mono dim">'+fmtTick(l.t)+'</td><td><span class="tag '+(l.amount>=0?'g':'r')+'">'+l.type+'</span></td><td>'+esc(l.note)+'</td><td class="r '+(l.amount>=0?'up':'down')+'">'+fmtC(l.amount,2)+'</td><td class="r adv cell">'+fmtC(l.bal)+'</td></tr>').join('')+'</tbody></table></div>';
  return'<div class="grid g32">'+panel('Balance · last 180 hours',chart,'','19 · money')+panel('Settling up',recon,'','20 · equipment')+'</div>'+
    '<div class="grid g2" style="margin-top:11px">'+panel('What each good earns',pnl,'','21 · earnings')+panel('Money in, money out',tx,'','22 · journal')+'</div>';
};

/* --------------------------------- INTEL ---------------------------------- */
V.intel=function(){
  if(!S.forecast||S.tick-S.forecastAt>12)computeForecast();
  const f=S.forecast;
  chartSpecs['int-fan']={type:'fan',data:f};
  const fan='<div class="canvas-wrap" style="height:220px"><canvas style="width:100%;height:100%" id="int-fan" data-chart="fan" data-id="int-fan" data-tip="Looking ahead|'+f.paths+' independent 48-hour paths from a separate chance thread stream. Band = 10th–90th percentile of net worth."></canvas></div>'+
    '<div class="legend"><span><i style="background:#c9a25f"></i>Median path</span><span><i style="background:rgba(54,50,45,.25)"></i>P10–P90 band</span><span><i style="background:#c9a25f"></i>Bounds</span></div>'+
    '<div class="divider"></div><div class="grid g4" style="gap:7px">'+
    [['Expected worth',fmtC(f.expected),'var(--cy)'],['Upside probability',fmtP(f.upProb,0),'var(--gr)'],['5% downside (VaR)',fmtC(f.vars),'var(--rd)'],['Audit-path risk',fmtP(f.auditRisk,0),'var(--am)']].map(q=>'<div class="card" style="padding:7px"><div class="cap" style="font-size:8px">'+q[0]+'</div><div class="num" style="font-size:13px;color:'+q[2]+';margin-top:3px">'+q[1]+'</div></div>').join('')+'</div>'+
    '<div class="row" style="margin-top:9px;gap:6px"><button class="btn sm" data-act="forecast">Refresh outlook</button><span class="spacer"></span><span class="tiny dim">last run '+fmtTick(f.at)+'</span></div>'+
    '<div class="notice adv" style="margin-top:9px">Each path evolves a reduced-order model: OU demand, mean-reverting price, elastic turnover, overhead, capped reconciliation and heat diffusion with probabilistic audits. Deterministic given seed 0x'+(S.rs>>>0).toString(16).toUpperCase()+'.</div>';

  const research='<div class="grid g2" style="gap:7px">'+RESEARCH.map(r=>{
    const done=S.research[r.id],ok=r.req.every(q=>S.research[q]),aff=S.points>=r.cost&&S.cash>=r.cost*22;
    return'<div class="card" style="border-left:2px solid '+(done?'var(--gr)':ok?'var(--cy2)':'var(--line2)')+';opacity:'+(done?.65:ok?1:.6)+'"><div class="row"><span class="t">'+r.key+'</span><span class="spacer"></span><span class="tag '+(done?'g':!ok?'r':'c')+'">'+(done?'Unlocked':!ok?'Locked':r.cost+' Leads')+'</span></div>'+
      '<div class="s" style="margin:5px 0">'+r.desc+'</div>'+
      '<div class="row tiny dim"><span>req: '+(r.req.length?r.req.map(q=>RESEARCH.find(x=>x.id===q).key).join(', '):'none')+'</span><span class="spacer"></span>'+(done?'':'<button class="btn sm" data-act="research" data-id="'+r.id+'"'+(!ok||!aff?' disabled':'')+'>Learn '+fmtC(r.cost*22)+'</button>')+'</div></div>';}).join('')+'</div>'+
    '<div class="row" style="margin-top:9px"><span class="cap">Analysis points</span><span class="spacer"></span><span class="num" style="color:var(--vi)">'+fmtN(S.points,1)+' RESEARCH</span><span class="tiny dim">+'+r2(S.mods.pointsRate)+'/h</span></div>'+barHTML(S.points/120,'v');

  const objectives=OBJECTIVES.map(o=>'<div class="row" style="padding:6px 0;border-bottom:1px dashed #1b1916;gap:8px"><span style="color:'+(S.objectives[o.id]?'var(--gr)':'var(--mute)')+';font-family:var(--mono)">'+(S.objectives[o.id]?'✓':'○')+'</span>'+
    '<div style="flex:1"><div class="tiny" style="color:'+(S.objectives[o.id]?'var(--dim)':'var(--txt)')+'">'+o.key+'</div><div class="tiny dim">'+o.desc+'</div></div><span class="tag '+(S.objectives[o.id]?'g':'')+'">'+fmtC(o.reward)+'</span></div>').join('')+
    (S.won?'<div class="notice c" style="margin-top:9px">The campaign is complete. You can keep playing.</div>':'');
  const news=S.news.slice(0,22).map(n=>'<div class="feed-item"><span class="ft">'+fmtTick(n.t)+'</span><span class="tag '+(n.tone==='good'?'g':n.tone==='bad'?'r':'')+'" style="height:16px">'+n.tag+'</span><span class="fx">'+esc(n.text)+'</span></div>').join('');
  const active=S.activeEvents.length?S.activeEvents.map(e=>'<div class="row" style="font-size:10px;padding:4px 0;border-bottom:1px dashed #1b1916"><span class="tag '+(e.tone==='good'?'g':'r')+'">'+e.key+'</span><span class="spacer"></span><span class="tiny dim">'+(e.d>=0?DISTRICTS[e.d].short:'All districts')+' · ×'+r2(e.mag)+' · '+e.ttl+'h</span></div>').join(''):'<div class="empty">No active market modifiers.</div>';
  return'<div class="grid g32">'+panel('Outlook · next 48 hours',fan,'','23 · outlook')+
    panel('Where the story is going',objectives+'<div class="divider"></div><div class="statline"><span>Objectives complete</span><b>'+OBJECTIVES.filter(o=>S.objectives[o.id]).length+' / '+OBJECTIVES.length+'</b></div>','','24 · milestones')+'</div>'+
    '<div class="grid g23" style="margin-top:11px">'+panel('Leads & contacts',research,'','25 · leads')+
    panel('Street talk','<div class="scrollbox" style="max-height:190px">'+news+'</div><div class="divider"></div>'+sectionHead('What is affecting trade')+active,'','26 · street talk')+'</div>';
};

/* -------------------------------- Archive --------------------------------- */
V.systems=function(){
  const d=S.diag;
  const tel=[['Hour',S.tick,'var(--cy)'],['Story thread','0x'+(S.rs>>>0).toString(16).toUpperCase().slice(0,8),'var(--vi)'],['Story fingerprint',d.hash,'var(--am)'],['Variation (norm)',r3(d.entropy),'var(--bl)'],
    ['Market steps / h',fmtN(d.solverIter),'var(--gr)'],['People updated / h',fmtN(d.agentUpdates),'var(--gr)'],['Happenings queued',S.eventBus.length,'var(--am)'],['Last hour',r3(d.lastMs)+' ms','var(--cy)'],
    ['Story seed',hashStr(String(S.seed)).toUpperCase(),'var(--vi)'],['Last saved',fmtTick(S.lastSaveTick),'var(--dim)'],['Inspections',d.audits,'var(--rd)'],['Possible futures',S.forecast?S.forecast.paths:0,'var(--bl)']];
  const readout='<div class="grid g4" style="gap:7px">'+tel.map(t=>'<div class="card" style="padding:8px"><div class="cap" style="font-size:8px">'+t[0]+'</div><div class="num" style="font-size:12px;color:'+t[2]+';margin-top:4px">'+t[1]+'</div></div>').join('')+'</div>'+
    '<div class="divider"></div>'+sectionHead('What the city is doing')+
    [['Market',.62],['People',.38],['Happenings',clamp(S.activeEvents.length/8,0,1)],['Attention spreading',clamp(S.heat/100,0,1)],['Money',.24],['Outlook',(S.forecast ? 0.24 : 0)],['Interface',clamp(UI.renderCount%60/60,0,1)]].map(q=>'<div style="margin-bottom:5px"><div class="row tiny dim"><span>'+q[0]+'</span><span class="spacer"></span><span class="num">'+fmtP(q[1],0)+'</span></div>'+barHTML(q[1],q[1]>.75?'r':'b')+'</div>').join('')+
    '<div class="divider"></div><div class="notice c">The same seed and the same choices always lead to the same city. Everything moves one hour at a time; the interface only reports it.</div>';

  const codex=[
    ['One story, one seed','The same opening choice always grows into the same city. Chance is drawn from one saved thread, so a story can be replayed exactly. Looking ahead never changes what actually happens.'],
    ['Appetite drifts','<code>D[t+1] = D[t] + θ(T − D[t]) + σ√vol·N(0,1)·T</code>, θ=.24. Target <code>T</code> = population × commodity bias × wealth × diurnal curve × weather × season × mood × word-of-mouth × (1 − saturation). District saturation decays at the commodity’s stickiness rate and rebuilds with sales.'],
    ['How prices settle','Inverse-demand clearing: <code>P* = base · (D/S)^(1/ε) · wealth^0.32 · macro · event multipliers</code>. The observed price relaxes toward P* with α=.34, then receives a per-commodity AR(1) volatility state and transient shocks. Listings use the same elasticity to convert an ask into a quantity.'],
    ['Finding a good price','Grid search m ∈ [0.55, 2.00] over <code>(m·P − marginal cost) · D·.052·m^(−ε) · σ((1.08−m)·4.2)</code>. The best multiplier is the amber marker in the order book; auto-pricing recomputes it hourly.'],
    ['What buyers will pay','Hidden willingness-to-pay <code>W = P · U(.92,1.24) · trait · (1 + loyalty·.22) · intel bonus</code>. Counter-offer success is logistic: <code>σ(2.1(W−ask)/(.085W) + 1.5·loyalty − .85·haggle + rep/190 + research)</code>. Detail level reveals the WTP estimate.'],
    ['People on schedules','Clients: budget regeneration, mood mean-reversion, churn accumulation, cooldown, offer emission with rate λ ∝ latent demand. Couriers: Idle → Outbound → Returning, plus Rest and Train. Fatigue, morale, loyalty, XP and wage accrual are integrated every hour.'],
    ['Streets & travel','The shortest routes across fourteen two-way streets weighted by Euclidean distance. Travel time multiplies by congestion from local heat and weather, and divides by logistics tier (and route-optimisation research). Complications apply a probabilistic payload loss and ETA extension.'],
    ['The workshop','Fictional industrial abstraction only: feedstock demand = f(input units, target grade). Yield = input × (rig + research) × N(1,.05). Grade = grade ceiling × U(.82,1) + N(0,.045) + boost. Lots carry unit cost, purity and age; age drives decay.'],
    ['Attention & consequences','Local heat is injected by volume × district risk × trait visibility × equipment tier, and decays by <code>.055 · counsel · (1 + scrutiny·.4)</code>. Global heat is a population-weighted relaxation. Crossing the audit threshold levies a scaled assessment, seizes depot stock, cuts reputation and forces a cool-down.'],
    ['Money in, money out','Sales settle into an unsettled balance; reconciliation converts it at a capped hourly rate with a tier-dependent fee. Wages, lease and upkeep are charged hourly. Negative cash becomes debt with compounding interest. Net worth = cash + unsettled + marked inventory + asset basis − debt.'],
    ['Looking ahead','many possible tomorrows on a reduced-order model (OU demand, mean-reverting price, elastic turnover, overhead, capped reconciliation, heat diffusion, probabilistic audits). The shaded fan shows the likely range; the lower edge is the cautious case.'],
    ['Happenings around town','Hourly Poisson(λ≈.055 + heat) arrivals sample 12 weighted event definitions. Events mutate active modifier lists, feed targets, local scrutiny, reputation, or research points, and expire after a sampled duration. The news wire is a projection of the event bus.'],
    ['Why saves stay honest','World state is plain JSON with no functions or references. A rolling FNV-1a hash over chance thread cursor, balances and price matrix is shown as Story fingerprint, so you can verify determinism across reloads.']
  ,['Private lives','Every contact owns a 24-hour schedule (sleep, home, work, social, nightlife, errands) with individual phase offsets and weekend behaviour. Energy, stress, need, suspicion and a decaying memory list evolve hourly. Sleeping clients cannot generate offers; physiology bleeds into visible mood and loyalty.'],
  ['Weather & the calendar','Temperature follows an OU process with diurnal and seasonal forcing; humidity, pressure, wind, rain accumulation and ground wetness feed visibility, flooding and street lighting. The calendar drives weekdays, two monthly paydays, civic holidays, moonlight and patrol shift rotation. Climate can override the visible weather state with hysteresis.'],
  ['Witnesses & memory','Each hour of commercial activity can generate bystander reports with strength and a 26–110h lifetime. Reports in one district mature into evidence chains; chain pressure raises scrutiny, audit severity and the heat target. An assessment clears most threads but never the institutional memory.'],
  ['Condition & wear','Every lot and every depot parcel carries independent integrity, moisture, exposure and seal states. Humidity, rain, heat index and flooding degrade them hourly; degraded goods slowly lose purity. Gear wear lowers the refining yield ceiling, purity ceiling, transit speed and sealant reliability until a workshop service is paid for.'],
  ['Rumours & money','Rumours are born from the news wire and diffuse across the 14-edge district graph with a 0.56 transfer coefficient and decay. Topics feed hidden demand/price/supply modifiers. A parallel macro layer tracks CPI, liquidity, wage index, credit tightness, wholesale lead times and per-district purchasing power.'],
  ['What people think of you','Reputation is an aggregate of five hidden facets — reliability, discretion, fairness, generosity, ruthlessness — each drifting toward baseline and reacting to deals, refusals, cool-downs and audits. The composite code nudges visible reputation and appears as a qualitative "standing" signal.']
  ].map((q,i)=>'<div class="accordion" data-acc="'+i+'"><button class="accordion-h" data-act="acc"><span class="caret">▸</span><span>'+q[0]+'</span></button><div class="accordion-b">'+q[1]+'</div></div>').join('');
  const consoleHTML='<div class="card" style="background:#0d0c0b;padding:0;border-color:var(--line2)"><div style="padding:7px 10px;border-bottom:1px solid var(--line);font-family:var(--mono);font-size:9px;color:var(--cy);letter-spacing:.12em">Scratchpad · detail view</div>'+
    '<div id="console-out" style="height:190px;overflow:auto;padding:8px 10px;font-family:var(--mono);font-size:10px;line-height:1.6;color:var(--txt2)">'+
    (UI.consoleLines.length?UI.consoleLines.map(l=>'<div style="color:'+(l.c||'var(--txt2)')+'">'+esc(l.t)+'</div>').join(''):'<div class="mute">type <span style="color:var(--cy)">help</span> for ideas</div>')+'</div>'+
    '<div class="row" style="padding:6px 8px;border-top:1px solid var(--line);gap:6px"><span class="mono dim">·</span><input class="inp" id="console-in" style="background:transparent;border:0;padding:2px 0" placeholder="help · tick 24 · cash 5000 · heat 0 · event · dump · seed · pause"></div></div>'+
    '<div class="notice adv" style="margin-top:9px">Commands: <span class="mono">tick N</span>, <span class="mono">cash ±N</span>, <span class="mono">heat N</span>, <span class="mono">rep N</span>, <span class="mono">event [name]</span>, <span class="mono">forecast</span>, <span class="mono">dump</span>, <span class="mono">seed</span>, <span class="mono">pause</span>, <span class="mono">clear</span>.</div>';
  const saves='<div class="row wrap" style="gap:6px"><button class="btn sm" data-act="save">Save story</button><button class="btn sm" data-act="load">Saved stories</button>'+
    '<button class="btn sm" data-act="export">Copy save file</button><button class="btn sm" data-act="import">Paste a save</button>'+
    '<button class="btn sm danger" data-act="newgame">Begin a new story</button><button class="btn sm danger" data-act="reset">Erase everything</button></div>'+
    '<div class="divider"></div><div class="statline"><span>Autosave</span><b>'+(S.settings.autosave?'Each day':'Off')+'</b></div>'+
    '<div class="statline"><span>Last save</span><b>'+fmtTick(S.lastSaveTick)+'</b></div>'+
    '<div class="statline"><span>Storage</span><b>localStorage · offline</b></div>'+
    '<div class="statline adv"><span>Serialised size</span><b>'+fmtN(NL.serialize().length/1024,1)+' KB</b></div>';
  return'<div class="grid g2">'+panel('Behind the ledger',readout,'','27 · notes')+
    panel('Field notes · '+(codex.split('data-acc').length-1)+' notes','<div style="max-height:430px;overflow:auto;padding-right:4px">'+codex+'</div>','','28 · notes')+'</div>'+
    '<div class="grid g2" style="margin-top:11px">'+panel('Scratchpad',consoleHTML,'adv','29 · scratchpad')+panel('Saved stories',saves,'','30 · saves')+'</div>'+
    '<div style="margin-top:11px">'+panel('The city today',UI.worldSummary(),'','31 · the city')+'</div>'+
    '<div class="adv" style="margin-top:11px">'+panel('The city under the surface',UI.worldPanelHTML(),'','32 · under the surface')+'</div>';
};

/* =====================================================================================
   Nightledger — Action ROUTER, MODALS, Saved stories
   ===================================================================================== */
UI.act=function(res){
  if(!res)return;
  UI.render(true);
  UI.toast(res.ok?(res.success===false?'The buyer walked away':'Done'):'Not possible',esc(res.msg),res.ok?(res.success===false?'warn':'good'):'bad');
  return res;
};
UI.setView=function(v){
  if(!V[v])return;
  UI.sel.view=v;
  $$('#rail .railbtn[data-view]').forEach(b=>b.classList.toggle('on',b.getAttribute('data-view')===v));
  el('content').scrollTop=0;
  UI.render(true);UI.sfx('click');
};
UI.render=function(force){
  if(!S||!el('view'))return;
  UI.renderTop();UI.renderSide();
  const ae=document.activeElement;
  const typing=ae&&(ae.tagName==='INPUT'||ae.tagName==='SELECT'||ae.tagName==='TEXTAREA')&&el('view').contains(ae);
  if(force||!typing){
    const host=el('view');
    host.innerHTML=V[UI.sel.view]();
    host.classList.remove('view');void host.offsetWidth;host.classList.add('view');
  }
  UI.drawAllCharts(document);
  UI.renderCount++;
};
UI.togglePause=function(){
  if(!S)return;S.paused=!S.paused;UI.renderTop();UI.sfx('click');
  UI.toast(S.paused?'The city is paused':'The city is moving',S.paused?'Nothing moves until you are ready.':'Time is moving at '+S.speed+'×.','');
};
UI.rest=function(){
  if(!S)return;
  S.paused=false;let n=0;
  for(let i=0;i<8;i++){
    NL.step(1);n++;
    if((S.heat>70&&S.settings.autopause)||S.gameOver){S.paused=true;break;}
  }
  UI.render(true);
  UI.toast('Moved '+n+' hours',S.paused?'Stopped early: something needs you.':'The city moved on.',S.paused?'warn':'good');
};
UI.toggleDensity=function(){
  if(!S)return;
  S.settings.density=S.settings.density==='clean'?'analyst':'clean';
  UI.applyDensity();UI.render(true);
  UI.toast('Level of detail',S.settings.density==='analyst'?'More detail is visible: extra columns, field notes and a scratchpad.':'Back to the essentials.','');
};
UI.applyDensity=function(){
  const an=S&&S.settings.density==='analyst';
  document.body.classList.toggle('analyst',!!an);
  if(el('win-density'))el('win-density').style.color=an?'var(--cy)':'var(--dim)';
};
UI.toggleFocus=function(){
  UI.focusMode=!UI.focusMode;
  const side=el('side'),rail=el('rail');
  side.classList.toggle('hidden',UI.focusMode);
  rail.classList.toggle('hidden',UI.focusMode&&false);
  UI.render(true);
  UI.toast(UI.focusMode?'A wider desk':'Everything back',UI.focusMode?'The side column is tucked away. Press F10 to bring it back.':'All panels restored.','');
};
UI.toggleMinimize=function(){
  UI.minimized=!UI.minimized;
  el('main').style.display=UI.minimized?'none':'';
  el('statusbar').style.display=UI.minimized?'none':'';
  el('app').style.gridTemplateRows=UI.minimized?'32px':'';
  if(UI.minimized)UI.toast('Interface tucked away','Press F9 to bring it back.','');
};
UI.autosave=function(){
  if(typeof document==='undefined')return;
  try{localStorage.setItem('nightledger.save',NL.serialize());localStorage.setItem('nightledger.settings',NL.serializeSettings());
    S.lastSaveTick=S.tick;
    const st=el('st-save');if(st){st.textContent='Saved '+fmtTick(S.tick);st.style.color='var(--cy2)';}
  }catch(e){const st=el('st-save');if(st)st.textContent='Save failed';}
};
UI.autopause=function(reason){
  if(!S||S.paused)return;
  S.paused=true;
  if(typeof document==='undefined')return;
  UI.renderTop();
  UI.toast('Stopped for you',esc(reason)+' — the city is waiting on your decision.','warn');
};
UI.save=function(manual){
  if(!S)return;UI.autosave();
  if(manual)UI.toast('Story saved','Saved at '+fmtTick(S.tick)+'.','good');
};
UI.load=function(silent){
  try{
    const raw=localStorage.getItem('nightledger.save');
    if(!raw){if(!silent)UI.toast('No saved story','Begin a story first.','bad');return false;}
    NL.deserialize(raw);
    el('boot').classList.add('hidden');
    UI.applyDensity();UI.closeAllModals();UI.render(true);
    if(!silent)UI.toast('Story restored','Picked up at '+fmtTick(S.tick)+' · story '+hashStr(String(S.seed)).slice(0,6).toUpperCase()+'.','good');
    return true;
  }catch(e){UI.toast('Could not load',esc(e.message),'bad');return false;}
};
UI.hasSave=function(){try{return !!localStorage.getItem('nightledger.save');}catch(e){return false;}};

/* ------------------------------ generic confirmation --------------------- */
UI.confirm=function(title,body,label,fn,cancelLabel){
  UI.openModal({title:title,sub:'Before you go on',slim:true,
    body:'<div class="notice">'+body+'</div>',
    footer:'<button class="btn" data-mclose>'+(cancelLabel||'Cancel')+'</button><button class="btn primary" data-m="ok">'+esc(label||'Confirm')+'</button>',
    onMount:(m,close)=>{m.querySelector('[data-m="ok"]').addEventListener('click',()=>{close();fn();});}});
};

/* ------------------------------ district dossier ------------------------- */
UI.districtSheet=function(d){
  UI.sel.d=d;
  const B=DISTRICTS[d],D=S.districts[d];
  const rows=PRODUCTS.map((pr,p)=>{
    const dep=S.depot[d][p],L=S.listings[d][p],o=priceOptimiser(d,p);
    return'<tr><td style="color:'+pr.color+'" class="strong">'+pr.key+'</td><td class="r">'+fmtC(D.price[p],2)+'</td>'+
      '<td class="r '+(priceChange(d,p)>0?'up':'down')+'">'+(priceChange(d,p)>0?'+':'')+fmtN(priceChange(d,p),0)+'%</td>'+
      '<td class="r adv cell">'+fmtN(D.demand[p],2)+'</td><td class="r adv cell">'+fmtN(D.rival[p],2)+'</td>'+
      '<td class="r">'+fmtP(D.sat[p],0)+'</td><td class="r">'+fmtU(dep.qty)+'</td>'+
      '<td class="r">'+(L.enabled?'<span class="tag g">'+fmtU(L.qty)+' @ '+fmtC(L.ask,2)+'</span>':'<span class="dim">—</span>')+'</td>'+
      '<td class="r"><button class="btn sm" data-m="pair" data-p="'+p+'">'+fmtC(o.ask,2)+' ▸</button></td></tr>';
  }).join('');
  const ev=D.events.length?D.events.map(e=>'<div class="notice '+(e.tone==='good'?'c':'r')+'" style="margin-bottom:5px">'+esc(e.key)+' · '+e.ttl+'h</div>').join(''):'<div class="empty">No local modifiers.</div>';
  const body='<div class="grid g4" style="gap:7px;margin-bottom:12px">'+
    [['Population index',fmtN(B.pop,2)],['Wealth index',fmtN(B.wealth,2)],['Base risk',fmtP(B.risk,0)],['Your influence',fmtP(S.control[d],0)]].map(q=>'<div class="card" style="padding:7px"><div class="cap" style="font-size:8px">'+q[0]+'</div><div class="num" style="font-size:14px;margin-top:3px">'+q[1]+'</div></div>').join('')+'</div>'+
    '<div class="grid g2" style="gap:10px;margin-bottom:12px"><div><div class="statline"><span>Local scrutiny</span><b>'+fmtN(D.heat,1)+' / 100</b></div>'+barHTML(D.heat/100,D.heat>60?'r':'a')+
      '<div class="statline" style="margin-top:6px"><span>District loyalty</span><b>'+fmtP(D.loyalty,1)+'</b></div>'+barHTML(D.loyalty,'g')+
      '<div class="statline adv" style="margin-top:6px"><span>Scrutiny coefficient</span><b>'+r3(D.scrutiny)+'</b></div>'+
      '<div class="statline adv"><span>Diurnal multiplier</span><b>'+TOD[S.hour].toFixed(2)+'</b></div></div>'+
      '<div><div class="cap" style="margin-bottom:6px">Rival footprint</div>'+S.rivals.map(r=>'<div style="margin-bottom:5px"><div class="row tiny dim"><span>'+r.name+'</span><span class="spacer"></span><span class="num">'+fmtP(r.territory[d],0)+'</span></div>'+barHTML(r.territory[d],'r')+'</div>').join('')+'</div></div>'+
    '<h4>Commodity clearing sheet</h4><div class="scrollbox" style="max-height:280px"><table class="tbl zebra"><thead><tr><th>Good</th><th class="r">Price</th><th class="r">Δ Base</th><th class="r adv cell">Demand</th><th class="r adv cell">Rival SUP</th><th class="r">Sat</th><th class="r">Depot</th><th class="r">Listing</th><th class="r">OPT</th></tr></thead><tbody>'+rows+'</tbody></table></div>'+
    '<h4>Local modifiers</h4>'+ev;
  UI.openModal({title:B.key,sub:'District notes · '+fmtTick(S.tick),wide:true,body:body,
    hint:'Click an optimised ask to jump into the order book for that pair.',
    footer:'<button class="btn" data-mclose>Close</button><button class="btn" data-m="dispatch">Dispatch Stock</button><button class="btn primary" data-m="market">Open Order Book</button>',
    onMount:(m,close)=>{
      m.querySelectorAll('[data-m="pair"]').forEach(b=>b.addEventListener('click',()=>{UI.sel.p=+b.getAttribute('data-p');UI.sel.d=d;close();UI.setView('market');}));
      m.querySelector('[data-m="market"]').addEventListener('click',()=>{UI.sel.d=d;close();UI.setView('market');});
      m.querySelector('[data-m="dispatch"]').addEventListener('click',()=>{close();UI.setView('operations');UI.toast('SELECT a lot','Click Send on any warehouse lot, then select '+B.short+'.','');});
    }});
};

/* ------------------------------ negotiation ------------------------------ */
/* the operator's own state, on the screen where hours are spent */
UI.youStrip=function(){
  const Y=you(),sh=youSharp();
  const tag=(k,v,warn)=>'<span class="chip" style="font-size:9px;padding:2px 7px'+(warn?';color:var(--rd)':'')+'">'+k+' '+fmtP(v,0)+'</span>';
  const body=Y.downtime>0
    ?'<span class="tag r">Out of action · '+Y.downtime+'h · '+esc(Y.cause)+'</span><span class="spacer"></span><span class="tiny dim">Actions are refused until you are on your feet.</span>'
    :tag('Tired',Y.tired,Y.tired>.65)+tag('Hunger',Y.hunger,Y.hunger>.7)+tag('Stress',Y.stress,Y.stress>.6)+
     '<span class="chip" style="font-size:9px;padding:2px 7px;color:var(--cy)">Sharp '+fmtP(sh,0)+'</span>'+
     '<span class="spacer"></span>'+
     '<button class="btn ghost sm" data-act="eat" style="font-size:8px">Eat ¤6 · 1h</button>'+
     '<button class="btn ghost sm" data-act="sleep4" style="font-size:8px">Sleep 4h</button>'+
     '<button class="btn ghost sm" data-act="sleep8" style="font-size:8px">Sleep 8h</button>';
  return'<div class="row wrap" style="gap:5px;margin-bottom:8px;padding:6px 8px;background:#171513;border:1px solid var(--line);border-left:2px solid var(--cy2);border-radius:2px"'+''+'>'+
    '<span class="cap" style="font-size:8px;margin-right:3px">You</span>'+body+'</div>';
};

UI.offerModal=function(id){
  const o=S.offers.find(x=>x.id===id);if(!o){UI.toast('Offer expired','That request has lapsed.','warn');return;}
  const c=S.clients.find(x=>x.id===o.client)||{name:'Unknown',loyalty:.2,mood:.5,budget:0,deals:0};
  const t=TRAITS[o.trait],dep=S.depot[o.cid][o.p],pr=PRODUCTS[o.p];
  const stockOK=dep.qty>=o.qty&&dep.purity>=o.minGrade;
  const maxAsk=r2(o.wtp*1.42),minAsk=r2(o.offer*.95);
  const odds0=offerOdds(o,o.offer);
  const oddsLabel=v=>v>.82?'Very likely':v>.62?'Likely':v>.42?'Even':v>.22?'Risky':'Unlikely';
  const body='<div class="grid g2" style="gap:12px"><div>'+
    '<h4>Buyer dossier</h4><div class="card"><div class="t" style="font-size:13px">'+esc(c.name)+'</div>'+
    '<div class="s" style="margin:4px 0 4px">'+DISTRICTS[o.cid].key+' · <span class="tag" style="color:'+t.col+'">'+t.key+'</span></div>'+
    '<div class="s" style="margin:0 0 8px">'+UI.clientAvailability(o.client)+'</div>'+
    '<div class="statline"><span>Loyalty</span><b>'+fmtP(c.loyalty,1)+'</b></div>'+barHTML(c.loyalty,'g')+
    '<div class="statline"><span>Mood</span><b>'+fmtP(c.mood,1)+'</b></div>'+barHTML(c.mood,'b')+
    '<div class="statline"><span>Budget</span><b>'+fmtC(c.budget)+'</b></div>'+
    '<div class="statline"><span>Prior deals</span><b>'+c.deals+'</b></div>'+
    '<div class="statline adv"><span>Hidden WTP estimate</span><b>'+fmtC(o.wtp,2)+'</b></div>'+
    '<div class="statline adv"><span>Haggle coefficient</span><b>'+t.haggle.toFixed(2)+'</b></div>'+
    '<div class="statline adv"><span>Patience</span><b>'+t.patience.toFixed(2)+'</b></div>'+
    '<div class="divider"></div>'+
    '<div class="statline"><span>What they remember</span><b class="'+(o.mem<-.15?'down':o.mem>.15?'up':'')+'">'+(o.mem<-.15?'Wary':o.mem>.15?'Favourable':'No history')+'</b></div>'+
    (c.mem&&c.mem.length?'<div class="tiny dim" style="margin-top:4px">'+c.mem.slice(-3).reverse().map(m=>fmtTick(m.t)+' · '+(m.k==='price'?(m.v>0?'you charged above their read':'you left money on the table'):m.k==='grade'?(m.v>0?'above the grade they asked':'only just made grade'):m.k==='refuse'?'you said no':'settled clean')).join('<br>')+'</div>':'<div class="tiny dim" style="margin-top:4px">First time at your door.</div>')+'</div>'+
    '<div class="notice adv" style="margin-top:9px">Success = σ( 2.1·(WTP−ask)/(.085·WTP) + 1.5·loyalty − .85·haggle + rep/190 + research ). Your analyst desk estimates WTP with noise.</div></div>'+
    '<div><h4>Offer terms</h4><div class="card">'+
    '<div class="statline"><span>Commodity</span><b style="color:'+pr.color+'">'+pr.key+'</b></div>'+
    '<div class="statline"><span>Quantity</span><b>'+fmtU(o.qty)+'</b></div>'+
    '<div class="statline"><span>Buyer offer / unit</span><b>'+fmtC(o.offer,2)+'</b></div>'+
    '<div class="statline"><span>Offer total</span><b>'+fmtC(o.offer*o.qty)+'</b></div>'+
    '<div class="statline"><span>Minimum purity</span><b>'+fmtP(o.minGrade,0)+'</b></div>'+
    '<div class="statline"><span>Grade premium at '+fmtP(dep.purity,0)+'</span><b class="'+(dep.purity>o.minGrade+.14?'up':dep.purity<o.minGrade+.04?'down':'')+'">×'+r3(clamp(gradeValue(o.p,dep.purity)/gradeValue(o.p,o.minGrade),.8,1.25))+'</b></div>'+
    '<div class="statline"><span>Expires in</span><b class="'+(o.ttl<=3?'down':'')+'">'+o.ttl+'h</b></div>'+
    '<div class="divider"></div><div class="statline"><span>Depot stock</span><b>'+fmtU(dep.qty)+'</b></div>'+
    '<div class="statline"><span>Depot purity</span><b>'+fmtP(dep.purity,1)+'</b></div>'+
    '<div class="notice '+(stockOK?'c':'r')+'">'+(stockOK?'Stock and grade satisfy the buyer.':dep.qty<o.qty?'Insufficient stock at '+DISTRICTS[o.cid].short+'. Dispatch a lot first.':'Grade too low for this buyer. Refine a higher-purity lot.')+'</div></div>'+
    '<h4 style="margin-top:12px">Counter-offer</h4><div class="card">'+
    '<div class="row"><span class="cap">Ask / unit</span><span class="spacer"></span><span class="num" id="nego-ask" style="font-size:15px;color:var(--cy)">'+fmtC(o.offer,2)+'</span></div>'+
    '<input type="range" id="nego-range" min="'+minAsk+'" max="'+maxAsk+'" step="0.5" value="'+o.offer+'" style="margin:10px 0">'+
    '<div class="row"><span class="cap">Close probability</span><span class="spacer"></span><span class="tag c" id="nego-odds">'+oddsLabel(odds0)+(S.settings.density==='analyst'?' · '+fmtP(odds0,0):'')+'</span></div>'+
    '<div class="bar g"><i id="nego-bar" style="width:'+clamp(odds0*100,0,100).toFixed(1)+'%"></i></div>'+
    '<div class="statline" style="margin-top:6px"><span>Expected value</span><b id="nego-ev">'+fmtC(o.offer*o.qty*odds0)+'</b></div></div></div></div>';
  UI.openModal({title:'A conversation with '+esc(c.name),sub:pr.key+' · '+DISTRICTS[o.cid].key+' · Request #'+o.id,wide:true,body:body,
    hint:'Accepting settles instantly. A failed counter damages mood and loyalty.',
    footer:'<button class="btn danger" data-m="decline">Decline</button><span class="spacer"></span>'+
      '<button class="btn" data-m="accept" '+(stockOK?'':'disabled')+'>ACCEPT '+fmtC(o.offer*o.qty)+'</button>'+
      '<button class="btn" data-m="grade" '+(stockOK?'':'disabled')+'>TAKE THEIR PRICE, KEEP THE GRADE</button>'+
      '<button class="btn" data-m="split" '+(stockOK?'':'disabled')+'>SPLIT THE ORDER</button>'+
      '<button class="btn primary" data-m="counter" '+(stockOK?'':'disabled')+'>COUNTER-Offer</button>',
    onMount:(m,close)=>{
      const range=m.querySelector('#nego-range');
      const upd=()=>{
        const ask=+range.value,p=offerOdds(o,ask);
        m.querySelector('#nego-ask').textContent=fmtC(ask,2);
        const od=m.querySelector('#nego-odds');od.textContent=oddsLabel(p)+(S.settings.density==='analyst'?' · '+fmtP(p,0):'');
        od.className='tag '+(p>.62?'g':p>.35?'a':'r');
        m.querySelector('#nego-ev').textContent=fmtC(ask*o.qty*p);
        m.querySelector('#nego-bar').style.width=clamp(p*100,0,100)+'%';
      };
      range.addEventListener('input',upd);upd();
      m.querySelector('[data-m="accept"]').addEventListener('click',()=>{close();UI.act(A.acceptOffer(o.id,o.offer,'accept'));});
      m.querySelector('[data-m="counter"]').addEventListener('click',()=>{const ask=+range.value;close();UI.act(A.acceptOffer(o.id,ask,'counter'));});
      m.querySelector('[data-m="grade"]').addEventListener('click',()=>{close();UI.act(A.acceptOffer(o.id,o.offer,'grade'));});
      m.querySelector('[data-m="split"]').addEventListener('click',()=>{close();UI.act(A.acceptOffer(o.id,o.offer,'split'));});
      m.querySelector('[data-m="decline"]').addEventListener('click',()=>{close();A.declineOffer(o.id);UI.render(true);UI.toast('Request declined','The buyer has gone.','','');});
    }});
};

/* ------------------------------ dispatch ---------------------------------- */
UI.dispatchModal=function(lotId){
  const lot=S.lots.find(l=>l.id===lotId);if(!lot)return;
  const idle=S.couriers.filter(c=>c.status==='Idle');
  const pr=PRODUCTS[lot.p];
  const body='<div class="grid g2" style="gap:12px"><div><h4>Source lot</h4><div class="card">'+
    '<div class="statline"><span>Lot</span><b>'+lot.tag+'</b></div>'+
    '<div class="statline"><span>Commodity</span><b style="color:'+pr.color+'">'+pr.key+'</b></div>'+
    '<div class="statline"><span>Available</span><b>'+fmtU(lot.qty)+'</b></div>'+
    '<div class="statline"><span>Grade</span><b>'+fmtP(lot.purity,1)+'</b></div>'+
    '<div class="statline"><span>Unit cost</span><b>'+fmtC(lot.cost,2)+'</b></div>'+
    '<div class="statline"><span>Mark / unit</span><b>'+fmtC(markPrice(lot.p,lot.purity),2)+'</b></div></div>'+
    '<div class="notice" style="margin-top:10px">Stock is deposited into the district depot on arrival. Post a listing from the Market view to begin passive retail; buyer requests also draw from the depot.</div></div>'+
    '<div><h4>Routing</h4><div class="field" style="margin-bottom:9px"><label>Destination district</label><select id="dp-d">'+DISTRICTS.map((b,i)=>'<option value="'+i+'" '+(i===UI.sel.d?'selected':'')+'>'+b.key+' · risk '+fmtP(b.risk,0)+' · '+fmtC(S.districts[i].price[lot.p],2)+'</option>').join('')+'</select></div>'+
    '<div class="field" style="margin-bottom:9px"><label>Quantity (max '+fmtU(lot.qty)+')</label><input class="inp" id="dp-q" type="number" min="0.5" max="'+lot.qty+'" step="0.5" value="'+r2(Math.min(lot.qty,20))+'"></div>'+
    '<div class="field"><label>Courier</label><select id="dp-c">'+(idle.length?idle.map(c=>'<option value="'+c.id+'">'+esc(c.name)+' · cap '+fmtU(38*c.stamina*S.mods.payload)+' · stealth '+fmtP(c.stealth,0)+'</option>').join(''):'<option value="-1">NO Idle COURIERS</option>')+'</select></div>'+
    '<div class="divider"></div><div class="statline"><span>Estimated transit</span><b id="dp-eta">—</b></div>'+
    '<div class="statline"><span>WEATHER factor</span><b>'+WEATHER[S.weather].speed.toFixed(2)+'×</b></div>'+
    '<div class="statline adv"><span>Complication base</span><b>'+fmtP(S.mods.complication,2)+'</b></div>'+
    '<div class="notice adv" style="margin-top:9px">ETA from Dijkstra shortest path × local congestion ÷ logistics tier. Higher heat and fatigue raise the chance of a delayed, partially lost payload.</div></div></div>';
  UI.openModal({title:'Sending · '+lot.tag,sub:'Sending stock',body:body,
    hint:'Courier returns to HQ automatically after depositing stock.',
    footer:'<button class="btn" data-mclose>Cancel</button><button class="btn primary" data-m="go">Confirm DISPATCH</button>',
    onMount:(m,close)=>{
      const dsel=m.querySelector('#dp-d'),csel=m.querySelector('#dp-c'),q=m.querySelector('#dp-q'),eta=m.querySelector('#dp-eta');
      const upd=()=>{const c=S.couriers.find(x=>x.id===+csel.value);const t=distTravel(0,+dsel.value)*(1+(c?.18*(1-c.skill):0));eta.textContent=Math.max(1,Math.round(t))+'h · '+DISTRICTS[+dsel.value].short;};
      dsel.addEventListener('change',upd);csel.addEventListener('change',upd);upd();
      m.querySelector('[data-m="go"]').addEventListener('click',()=>{
        const res=A.dispatch(lot.id,+q.value,+dsel.value,+csel.value);
        if(res.ok)close();UI.act(res);
      });
    }});
};

/* ------------------------------ settings / manual ------------------------ */
function settingsBody(){
  const s=S?S.settings:{density:'clean',sound:true,autopause:true,autosave:true,showRoutes:true};
  const rows=[
    ['sound','Sound effects','Small interface cues, generated on this machine.'],
    ['autopause','Pause on surprises','Stop when an inspection or a big shift needs a decision.'],
    ['autosave','Autosave each day','Keep a rolling save at every in-game daybreak.'],
    ['showRoutes','Draw courier routes','Show stock moving across the city map.'],
    ['density','Detail level','Reveal extra columns, quiet estimates and a scratchpad.']
  ];
  return'<div class="grid" style="gap:4px">'+rows.map(r=>'<div class="row" style="padding:8px;border-bottom:1px solid var(--line);gap:10px"><div style="flex:1"><div class="t">'+r[1]+'</div><div class="s">'+r[2]+'</div></div><div class="switch '+(s[r[0]]&&s[r[0]]!=='clean'?'on':'')+'" data-s="'+r[0]+'"><span class="knob"></span></div></div>').join('')+'</div>'+
    '<div class="divider"></div><div class="row"><span class="cap">City speed</span><span class="spacer"></span>'+[1,2,4,8].map(v=>'<button class="chip '+(S&&S.speed===v?'on':'')+'" data-speedset="'+v+'">'+v+'×</button>').join('')+'</div>'+
    '<div class="notice" style="margin-top:10px">Options are kept with your story. <span class="kbd">F2</span> toggles density at any time; <span class="kbd">F10</span> toggles focus mode.</div>';
}
UI.settings=function(){
  UI.openModal({title:'Options',sub:'Make it yours',slim:true,body:settingsBody(),
    footer:'<button class="btn" data-mclose>Discard</button><button class="btn primary" data-m="apply">RESEARCHPLY</button>',
    onMount:(m,close)=>{
      m.querySelectorAll('[data-s]').forEach(sw=>sw.addEventListener('click',()=>{
        const k=sw.getAttribute('data-s');
        if(!S)return;
        S.settings[k]=k==='density'?(S.settings.density==='clean'?'analyst':'clean'):!S.settings[k];
        sw.classList.toggle('on',k==='density'?S.settings.density==='analyst':S.settings[k]);
        if(k==='density')UI.applyDensity();
      }));
      m.querySelectorAll('[data-speedset]').forEach(b=>b.addEventListener('click',()=>{if(S)S.speed=+b.getAttribute('data-speedset');m.querySelectorAll('[data-speedset]').forEach(z=>z.classList.toggle('on',z===b));}));
      m.querySelector('[data-m="apply"]').addEventListener('click',()=>{close();try{localStorage.setItem('nightledger.settings',NL.serializeSettings());}catch(e){}UI.render(true);UI.toast('Options saved','Kept on this machine.','good');});
    }});
};
UI.manual=function(){
  const steps=[
    ['01 · Read the room','The The desk shows five live metrics, the city graph and three condensed panels. Everything else is detail you can open when you need it. Press <span class="kbd">F2</span> to reveal the analyst layer.'],
    ['02 · Buy & prepare','In Operations, buy wholesale feedstock, queue a refining run, wait for the lot, then <b>Dispatch</b> it to a district with an idle courier. Stock only earns once it reaches a depot.'],
    ['03 · SELECT a price','In Market, post a retail listing (or enable the auto-optimiser). Passive sales clear every hour. Inbound buyer requests can be accepted or countered — the negotiation screen shows the odds.'],
    ['04 · Mind the attention','Volume raises scrutiny. Keep an eye on the exposure gauge; a cool-down pauses listings and bleeds heat. An audit costs cash, stock and reputation.'],
    ['05 · Settle & grow','Sales land as unsettled revenue. Reconcile it into spendable cash, repay debt, buy capital assets and unlock research. Objectives in Intel track the campaign.'],
    ['06 · Keep your rhythm','<span class="kbd">Space</span> pauses, <span class="kbd">1</span>–<span class="kbd">7</span> switch views, <span class="kbd">R</span> advances eight hours, <span class="kbd">Ctrl</span>+<span class="kbd">K</span> opens the command palette. Save with <span class="kbd">Ctrl</span>+<span class="kbd">S</span>.']
  ];
  const glossary=[
    ['Attention','Aggregate scrutiny. Generated by sales volume and district risk; decays with time and the compliance desk.'],
    ['Hidden appetite','Hidden hourly demand potential per district × commodity. Drives both price and offer arrival rate.'],
    ['Buyer fatigue','Repeat-sale fatigue. High saturation suppresses demand until it decays.'],
    ['Grade','Lot grade. Buyers set minimums; higher purity lifts retail value and enables premium goods.'],
    ['Settling up','Converts unsettled revenue into spendable cash, capped per hour and charged a fee.'],
    ['Influence','Your share of a district. Raised by sales, eroded by hostile syndicates.'],
    ['Leads','Analysis points. Accumulate hourly from the intel desk; spent on research nodes.'],
    ['Outlook','Many quiet trial runs used to sketch a range of tomorrows.']
  ];
  UI.openModal({title:'Field notes',sub:'A quiet guide to the loop',wide:true,
    body:'<h4>The core loop</h4>'+steps.map(s=>'<div class="card" style="margin-bottom:6px"><div class="t" style="color:var(--cy)">'+s[0]+'</div><div class="s" style="margin-top:4px">'+s[1]+'</div></div>').join('')+
      '<h4>Glossary</h4><div class="grid g2" style="gap:6px">'+glossary.map(g=>'<div class="card" style="padding:7px"><div class="t" style="font-size:10px">'+g[0]+'</div><div class="s">'+g[1]+'</div></div>').join('')+'</div>'+
      '<h4>Hotkeys</h4><div class="row wrap" style="gap:6px">'+[['Space','Pause'],['1–7','Views'],['F2','Analyst layer'],['F9','Minimise'],['F10','Focus'],['R','Rest 8h'],['.','Step 1h'],['Ctrl+K','Palette'],['Ctrl+S','Save'],['?','Manual']].map(k=>'<span class="chip"><span class="kbd">'+k[0]+'</span> '+k[1]+'</span>').join('')+'</div>'+
      '<h4>The city, mostly unseen</h4><div class="card" style="margin-bottom:8px"><div class="t" style="color:var(--cy)">Most of the city never reaches the ledger</div><div class="s" style="margin-top:4px">Every contact keeps a daily routine, energy and memory. WEATHER, patrol shifts, paydays, roadworks, rumours, witness reports and worn equipment all move each hour and quietly bend prices, requests, attention and yield. The clean interface shows only a one-line note; <span class="kbd">F3</span> looks closer and <span class="kbd">F2</span> opens the deeper state.</div></div>'+
      '<div class="notice" style="margin-top:12px">This is a work of fiction. All goods, places and crews are invented game abstractions — nothing here describes a real-world procedure.</div>',
    hint:'Tip: the side column always lists the three most useful next steps.',
    footer:'<button class="btn" data-m="tutorial">Guided tour</button><button class="btn primary" data-mclose>Got it</button>',
    onMount:(m,close)=>{m.querySelector('[data-m="tutorial"]').addEventListener('click',()=>{close();UI.tutorial();});}});
};

/* ------------------------------ new game / import ------------------------ */
UI.newGameModal=function(){
  UI.openModal({title:'Begin a new story',sub:'SELECT the city you want to meet',slim:true,
    body:'<div class="field" style="margin-bottom:10px"><label>World seed (blank = random)</label><input class="inp" id="ng-seed" placeholder="e.g. 424242"></div>'+
      '<div class="field" style="margin-bottom:10px"><label>Starting capital</label><select id="ng-cash"><option value="4200">BOOTSTRRESEARCH · ¤4,200</option><option value="3200" selected>Standard · ¤3,200</option><option value="1800">Lean · ¤1,800</option><option value="900">Hardcore · ¤900</option></select></div>'+
      '<div class="notice">A fresh seed grows fresh districts, people, crews and happenings. The same seed always produces the same city.</div>',
    footer:'<button class="btn" data-mclose>Cancel</button><button class="btn primary" data-m="start">Begin</button>',
    onMount:(m,close)=>{m.querySelector('[data-m="start"]').addEventListener('click',()=>{
      const raw=m.querySelector('#ng-seed').value.trim();
      let seed=raw?(/^\d+$/.test(raw)?(+raw>>>0):parseInt(hashStr(raw).slice(0,8),16)):undefined;
      if(!Number.isFinite(seed))seed=undefined;
      const cash=+m.querySelector('#ng-cash').value;
      const settings=UI.readStoredSettings();
      S=NL.newGame(seed,{cash:cash,settings:settings});
      S.lastSaveTick=0;
      close();el('boot').classList.add('hidden');UI.applyDensity();UI.closeAllModals();UI.render(true);UI.save();
      UI.toast('A new story begins','Seed '+hashStr(String(S.seed)).toUpperCase()+' · '+fmtC(cash)+' starting capital.','good');
      if(!S.settings.tutorialDone)setTimeout(()=>UI.tutorial(),700);
    });}});
};
UI.readStoredSettings=function(){
  try{return JSON.parse(localStorage.getItem('nightledger.settings')||'{}');}catch(e){return{};}
};
UI.exportSave=function(){
  const json=NL.serialize();
  UI.openModal({title:'Copy save file',sub:'A copy of your story',slim:true,
    body:'<div class="tiny dim" style="margin-bottom:6px">'+fmtN(json.length/1024,1)+' KB · copy this text to keep your story elsewhere.</div><textarea class="inp" id="exp-text" style="height:190px;font-size:9px;resize:vertical">'+esc(json)+'</textarea>',
    footer:'<button class="btn" data-m="download">Download file</button><button class="btn primary" data-mclose>Done</button>',
    onMount:(m)=>{m.querySelector('[data-m="download"]').addEventListener('click',()=>{
      const blob=new Blob([json],{type:'application/json'}),a=document.createElement('a');
      a.href=URL.createObjectURL(blob);a.download='nightledger-'+S.seed+'-'+S.tick+'.json';document.body.appendChild(a);a.click();a.remove();
      UI.toast('Copy ready','File downloaded.','good');
    });}});
};
UI.importSave=function(){
  UI.openModal({title:'Paste a save',sub:'Paste a save file',slim:true,
    body:'<textarea class="inp" id="imp-text" style="height:190px;font-size:9px" placeholder="{ ... nightledger save JSON ... }"></textarea><div class="notice" style="margin-top:8px">Pasting replaces the current hour. Save it to a manual slot first if you want to come back.</div>',
    footer:'<button class="btn" data-mclose>Cancel</button><button class="btn primary" data-m="load">LOAD SNRESEARCHSHOT</button>',
    onMount:(m,close)=>{m.querySelector('[data-m="load"]').addEventListener('click',()=>{
      try{NL.deserialize(m.querySelector('#imp-text').value);close();el('boot').classList.add('hidden');UI.applyDensity();UI.render(true);UI.save();UI.toast('Story restored','Restored from the pasted save.','good');}
      catch(e){UI.toast('Could not read that save',esc(e.message),'bad');}
    });}});
};
UI.toTitle=function(){
  if(S)S.paused=true;
  el('boot').classList.remove('hidden');
  UI.updateBootInfo();
};
UI.updateBootInfo=function(){
  if(!el('boot-saveinfo'))return;
  try{
    const raw=localStorage.getItem('nightledger.save');
    if(raw){const o=JSON.parse(raw);el('boot-saveinfo').textContent=fmtTick(o.tick||0)+' · '+hashStr(String(o.seed)).toUpperCase();el('boot-continue').disabled=false;}
    else{el('boot-saveinfo').textContent='No saved story';el('boot-continue').disabled=true;}
  }catch(e){el('boot-saveinfo').textContent='No saved story';el('boot-continue').disabled=true;}
};

/* ------------------------------ guided tutorial -------------------------- */
UI.tutorial=function(){
  const steps=[
    {sel:'#topstrip',t:'01 · The clock',b:'Time, cash, worth, attention and standing live here. Use the speed buttons or Space to pause. Nothing moves until you are ready.'},
    {sel:'#rail',t:'02 · The views',b:'Seven places, never more than one click away. Each starts with the essentials; press F2 when you want the deeper numbers.'},
    {sel:'#map-main',t:'03 · The city map',b:'Seven districts. The ring is your influence, the core is local attention, and the size is appetite. Click any one for its notes.'},
    {sel:'#advisor',t:'04 · What matters now',b:'Three suggested next steps, reconsidered as the city changes. Click one to go straight there.'},
    {sel:'#side-feed',t:'05 · Street talk',b:'Sales, deliveries, inspections and happenings collect here. You are ready — start with Operations.'}
  ];
  let i=0;const box=el('tutbox');let prev=null;
  const cleanup=()=>{if(prev)prev.classList.remove('tut-hl');box.classList.add('hidden');document.removeEventListener('keydown',key,true);};
  const key=e=>{if(e.key==='Escape'){cleanup();}};
  const show=()=>{
    if(prev)prev.classList.remove('tut-hl');
    if(i>=steps.length){cleanup();if(S){S.settings.tutorialDone=true;}UI.toast('Tour complete','Press Ctrl+K any time to find anything.','good');return;}
    const s=steps[i],n=document.querySelector(s.sel);
    if(n){n.classList.add('tut-hl');prev=n;}
    const r=n?n.getBoundingClientRect():{left:innerWidth/2,top:innerHeight/2,width:0,bottom:innerHeight/2};
    box.innerHTML='<div class="t">'+s.t+'</div><div>'+s.b+'</div><div class="f"><span class="tiny dim">'+(i+1)+' / '+steps.length+'</span><span class="spacer"></span>'+
      '<button class="btn ghost sm" data-t="skip">Skip</button><button class="btn primary sm" data-t="next">'+(i===steps.length-1?'Finish':'Next ▸')+'</button></div>';
    box.classList.remove('hidden');
    let x=r.left+r.width+16,y=r.top;
    if(x+300>innerWidth)x=Math.max(10,r.left-300);
    if(y+150>innerHeight)y=Math.max(10,innerHeight-170);
    box.style.left=x+'px';box.style.top=y+'px';
    box.querySelectorAll('[data-t]').forEach(b=>b.addEventListener('click',()=>{
      if(b.getAttribute('data-t')==='skip'){cleanup();if(S)S.settings.tutorialDone=true;return;}
      i++;show();
    }));
  };
  document.addEventListener('keydown',key,true);
  show();
};

/* ------------------------------ engine console --------------------------- */
UI.console=function(cmd){
  const out=el('console-out');if(!out)return;
  const line=(t,c)=>{UI.consoleLines.push({t:t,c:c});if(UI.consoleLines.length>60)UI.consoleLines.shift();};
  line(cmd,'var(--cy)');
  const parts=cmd.trim().split(/\s+/),c=parts[0].toLowerCase();
  try{
    if(c==='help')line('Try: tick, cash, heat, rep, points, event, forecast, dump, seed, pause, world, service, rumor, evidence, clear');
    else if(c==='tick'){const n=clamp(parseInt(parts[1])||1,1,240);NL.step(n);line('moved '+n+' hours → '+fmtTick(S.tick),'var(--gr)');UI.render(true);}
    else if(c==='cash'){const v=parseFloat(parts[1])||0;S.cash=r2(S.cash+v);line('cash → '+fmtC(S.cash),'var(--gr)');}
    else if(c==='heat'){S.heat=clamp(parseFloat(parts[1])||0,0,100);for(let d=0;d<ND;d++)S.districts[d].heat=S.heat;line('heat → '+r2(S.heat),'var(--am)');}
    else if(c==='rep'){S.rep=clamp(parseFloat(parts[1])||0,0,100);line('rep → '+r2(S.rep),'var(--gr)');}
    else if(c==='points'){S.points=clamp(parseFloat(parts[1])||0,0,1e6);line('Leads → '+r2(S.points),'var(--vi)');}
    else if(c==='event'){const r=A.fireEvent(parts.slice(1).join(' '));line(r.msg,'var(--am)');}
    else if(c==='forecast'){const f=NL.computeForecast();line('outlook, expected worth '+fmtC(f.expected)+' · audit risk '+fmtP(f.auditRisk,0),'var(--cy)');UI.render(true);}
    else if(c==='dump'){line('seed='+S.seed+' rs='+(S.rs>>>0)+' tick='+S.tick+' cash='+r2(S.cash)+' dirty='+r2(S.dirty)+' debt='+r2(S.debt)+' worth='+r2(netWorth())+' hash='+S.diag.hash,'var(--txt)');}
    else if(c==='seed'){line('story seed '+hashStr(String(S.seed)).toUpperCase()+' · cursor 0x'+(S.rs>>>0).toString(16).toUpperCase(),'var(--vi)');}
    else if(c==='pause'){S.paused=!S.paused;line('paused='+S.paused,'var(--am)');}
    else if(c==='clear'){UI.consoleLines=[];}
    else if(c==='world')line('City '+fmtTick(S.tick)+' · '+S.world.mods.length+' modifiers · dossier '+r2(S.world.dossier.evidence)+' · honor '+r2(S.world.honor.code)+' · '+r2(S.world.climate.temp)+'C · '+fmtN(S.world.stats.npcActions)+' small choices','var(--vi)');
    else if(c==='service'){const r=A.serviceGear();line(r.msg,r.ok?'var(--gr)':'var(--rd)');}
    else if(c==='rumor'){const r=A.seedRumor(parts[1]?parts.slice(1).join(' ').toUpperCase():undefined);line(r.msg,'var(--vi)');}
    else if(c==='evidence'){S.world.dossier.reports.push({t:S.tick,d:ri(0,ND-1),p:ri(0,NP-1),strength:1,ttl:70});line('witness report injected','var(--am)');}
    else line('not sure about: '+c,'var(--rd)');
  }catch(e){line('Could not: '+e.message,'var(--rd)');}
  if(out)out.innerHTML=UI.consoleLines.map(l=>'<div style="color:'+(l.c||'var(--txt2)')+'">'+esc(l.t)+'</div>').join('');
};

/* ------------------------------ action router ---------------------------- */
UI.handleAction=function(act,n,e){
  const at=(k,def)=>n.getAttribute(k)===null?def:n.getAttribute(k);
  const id=+at('data-id',0),p=+at('data-p',0),d=+at('data-d',0),v=at('data-v','');
  switch(act){
    case'go':UI.setView(v);break;
    case'gounlock':UI.setView('intel');break;
    case'worldlens':UI.worldLens();break;
    case'service':UI.act(A.serviceGear());break;
    case'seedrumor':UI.act(A.seedRumor());break;
    case'setp':UI.sel.p=p;UI.render(true);break;
    case'setd':UI.sel.d=d;UI.render(true);break;
    case'setpd':UI.sel.p=p;UI.sel.d=d;UI.setView('market');break;
    case'district':UI.districtSheet(d);break;
    case'mapmode':UI.sel.showAttention=v==='heat';UI.render(true);break;
    case'mapclick':{
      const r=n.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
      let best=-1,bd=1e9;
      for(let i=0;i<ND;i++){const px=26+DISTRICTS[i].x*(r.width-52),py=26+DISTRICTS[i].y*(r.height-52),dd=Math.hypot(mx-px,my-py);if(dd<bd){bd=dd;best=i;}}
      if(best>=0&&bd<48)UI.districtSheet(best);break;
    }
    case'heatclick':{
      const r=n.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
      const cw=(r.width-86-8)/NP,ch=(r.height-22-8)/ND;
      const col=Math.floor((mx-86)/cw),row=Math.floor((my-22)/ch);
      if(col>=0&&col<NP&&row>=0&&row<ND){UI.sel.p=col;UI.sel.d=row;UI.render(true);}
      break;
    }
    case'post':{
      const qty=+el('mk-qty').value,ask=+el('mk-ask').value,mode=el('mk-mode').value;
      UI.act(A.postListing(UI.sel.d,UI.sel.p,qty,ask,mode));break;
    }
    case'autofill':{
      const o=priceOptimiser(UI.sel.d,UI.sel.p);
      el('mk-ask').value=o.ask;el('mk-qty').value=Math.min(+el('mk-qty').value,S.depot[UI.sel.d][UI.sel.p].qty).toFixed(1);
      UI.toast('Optimiser applied','Ask '+fmtC(o.ask,2)+' · '+r2(o.m)+'× clearing price.','');break;
    }
    case'clearlisting':UI.act(A.postListing(UI.sel.d,UI.sel.p,0,0,'manual'));break;
    case'offer':UI.offerModal(id);break;
    case'decline':A.declineOffer(id);UI.render(true);UI.sfx('click');break;
    case'buyfeed':{
      const kind=at('data-kind','base'),inp=el('feed-'+kind);
      UI.act(A.buyFeed(kind,inp?+inp.value:100));break;
    }
    case'startjob':{
      const pp=+el('job-p').value,q=+el('job-q').value,t=+el('job-t').value/100;
      UI.act(A.startJob(pp,q,t));break;
    }
    case'dispatch':UI.dispatchModal(id);break;
    case'crew':UI.act(A.courierAction(id,v));break;
    case'setwage':{
      const inp=document.querySelector('[data-wage="'+id+'"]');
      UI.act(A.courierAction(id,'wage',inp?+inp.value:100));break;
    }
    case'fire':UI.confirm('Release courier?','They will leave the roster immediately. This cannot be undone.','Release',()=>UI.act(A.fireCourier(id)));break;
    case'hire':UI.act(A.hireCourier());break;
    case'dip':UI.act(A.diplomacy(at('data-r',''),v));break;
    case'pin':UI.act(A.acceptContract(id));break;
    case'recon':UI.act(A.reconcile());break;
    case'togglerecon':S.autoRecon=!S.autoRecon;UI.render(true);UI.toast('Auto-reconciliation',S.autoRecon?'Enabled.':'On hold.','');break;
    case'repay':UI.act(A.repayDebt());break;
    case'upgrade':UI.act(A.buyUpgrade(at('data-id','')));break;
    case'forecast':NL.computeForecast();UI.render(true);UI.toast('Outlook refreshed','Outlook · '+fmtC(S.forecast.expected)+' expected worth.','good');break;
    case'research':UI.act(A.research(at('data-id','')));break;
    case'laylow':UI.act(A.layLow());break;
    case'rest8':UI.rest();break;
    case'eat':UI.act(A.eat());break;
    case'sleep4':UI.act(A.sleep(4));break;
    case'sleep8':UI.act(A.sleep(8));break;
    case'save':UI.save(true);break;
    case'load':UI.confirm('Return to a saved story?','The current hour will be replaced.','Continue',()=>UI.load());break;
    case'export':UI.exportSave();break;
    case'import':UI.importSave();break;
    case'newgame':UI.confirm('Begin a new story?','The current hour will be replaced. Save it to a manual slot first if you want to come back.','Begin a new story',()=>UI.newGameModal());break;
    case'reset':UI.confirm('Erase everything on this machine?','This removes the rolling save, every manual slot and your preferences.','Erase everything',()=>{
      try{localStorage.removeItem('nightledger.save');localStorage.removeItem('nightledger.settings');}catch(e){}
      UI.toast('Local stories erased','Back to the title screen.','warn');setTimeout(()=>UI.toTitle(),400);
    });break;
    case'acc':n.parentNode.classList.toggle('open');break;
    default:break;
  }
};

/* =====================================================================================
   Nightledger — BOOT, INPUT, MAIN LOOP
   ===================================================================================== */
UI.init=function(){
  UI.registerCommands();UI.initTooltips();UI.initCanvasHover();UI.updateBootInfo();
  UI.applyDensity();

  /* rail + chrome */
  document.addEventListener('click',e=>{
    const rail=e.target.closest?e.target.closest('#rail .railbtn[data-view]'):null;
    if(rail){UI.setView(rail.getAttribute('data-view'));return;}
    const act=e.target.closest?e.target.closest('[data-act]'):null;
    if(act){UI.handleAction(act.getAttribute('data-act'),act,e);return;}
    const pi=e.target.closest?e.target.closest('[data-pi]'):null;
    if(pi){UI.runPalette(+pi.getAttribute('data-pi'));return;}
    const ad=e.target.closest?e.target.closest('[data-advisor]'):null;
    if(ad){const a=(UI.advisorList||[])[+ad.getAttribute('data-advisor')];if(a&&a.go){a.go();UI.sfx('click');}return;}
    if(e.target.closest&&e.target.closest('#btn-palette')){UI.openPalette();return;}
  });
  el('rail-help').addEventListener('click',()=>UI.manual());
  el('rail-settings').addEventListener('click',()=>UI.settings());
  el('btn-pause').addEventListener('click',()=>UI.togglePause());
  el('btn-sleep').addEventListener('click',()=>UI.rest());
  el('btn-palette').addEventListener('click',e=>{e.stopPropagation();UI.openPalette();});
  $$('.speedbtn[data-speed]').forEach(b=>b.addEventListener('click',()=>{if(!S)return;S.speed=+b.getAttribute('data-speed');S.paused=false;UI.renderTop();UI.sfx('click');}));
  el('win-density').addEventListener('click',()=>UI.toggleDensity());
  el('win-min').addEventListener('click',()=>UI.toggleMinimize());
  el('win-max').addEventListener('click',()=>UI.toggleFocus());
  el('win-close').addEventListener('click',()=>UI.pauseMenu());
  el('feed-clear').addEventListener('click',()=>{if(S){S.log=[];UI.renderSide();}});
  el('side-save').addEventListener('click',()=>UI.save(true));
  el('side-codex').addEventListener('click',()=>UI.setView('systems'));
  el('side-focus').addEventListener('click',()=>UI.toggleFocus());

  /* boot menu */
  el('boot-new').addEventListener('click',()=>UI.newGameModal());
  el('boot-continue').addEventListener('click',()=>UI.load());
  el('boot-seed').addEventListener('click',()=>UI.newGameModal());
  el('boot-manual').addEventListener('click',()=>UI.manual());
  el('boot-settings').addEventListener('click',()=>UI.settings());

  /* palette */
  const pin=el('palette-input');
  pin.addEventListener('input',()=>{UI.paletteSel=0;UI.renderPalette();});
  pin.addEventListener('focus',()=>{});
  el('palette-list').addEventListener('mousemove',e=>{
    const it=e.target.closest('[data-pi]');if(!it)return;
    const i=+it.getAttribute('data-pi');if(i!==UI.paletteSel){UI.paletteSel=i;UI.renderPalette();}
  });

  /* input-driven controls */
  document.addEventListener('input',e=>{
    if(e.target.id==='job-t'){const v=el('job-t-val');if(v)v.textContent=fmtP(+e.target.value/100,0);}
  });
  document.addEventListener('change',e=>{
    if(e.target.id==='mk-mode'){/* policy applied on POST */}
  });

  /* keyboard */
  document.addEventListener('keydown',e=>{
    const tag=(e.target&&e.target.tagName)||'';
    const typing=tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT';
    const key=e.key;
    if(key==='Escape'){
      if(el('palette').classList.contains('show')){UI.closePalette();e.preventDefault();return;}
      if(UI.modalOpen()){UI.closeModal();e.preventDefault();return;}
      UI.pauseMenu();e.preventDefault();return;
    }
    if((e.ctrlKey||e.metaKey)&&key.toLowerCase()==='k'){e.preventDefault();UI.openPalette();return;}
    if((e.ctrlKey||e.metaKey)&&key.toLowerCase()==='s'){e.preventDefault();UI.save(true);return;}
    if(el('palette').classList.contains('show')){
      if(key==='ArrowDown'){UI.paletteSel=Math.min(UI.paletteSel+1,UI.filteredCommands().length-1);UI.renderPalette();e.preventDefault();return;}
      if(key==='ArrowUp'){UI.paletteSel=Math.max(0,UI.paletteSel-1);UI.renderPalette();e.preventDefault();return;}
      if(key==='Enter'){UI.runPalette(UI.paletteSel);e.preventDefault();return;}
    }
    if(typing){
      if(key==='Enter'&&e.target.id==='console-in'){
        const v=e.target.value;if(v.trim()){UI.console(v);e.target.value='';}
        e.preventDefault();
      }
      if(key==='ArrowUp'&&e.target.id==='console-in'&&UI.cmdHistory.length){e.target.value=UI.cmdHistory[UI.cmdHistory.length-1];}
      return;
    }
    if(UI.modalOpen())return;
    const views=['overview','market','operations','network','ledger','intel','systems'];
    if(/^[1-7]$/.test(key)){UI.setView(views[+key-1]);e.preventDefault();return;}
    if(key===' '){UI.togglePause();e.preventDefault();return;}
    if(key==='F2'){UI.toggleDensity();e.preventDefault();return;}
    if(key==='F3'){UI.worldLens();e.preventDefault();return;}
    if(key==='F9'){UI.toggleMinimize();e.preventDefault();return;}
    if(key==='F10'){UI.toggleFocus();e.preventDefault();return;}
    if(key==='F1'||key==='?'||key==='/'){UI.manual();e.preventDefault();return;}
    if(key.toLowerCase()==='r'){UI.rest();e.preventDefault();return;}
    if(key==='.'){NL.step(e.shiftKey?24:1);UI.render(true);e.preventDefault();return;}
    if(key==='+'||key==='='){if(S){S.speed=Math.min(8,S.speed*2);S.paused=false;UI.renderTop();}e.preventDefault();return;}
    if(key==='-'||key==='_'){if(S){S.speed=Math.max(1,Math.round(S.speed/2));UI.renderTop();}e.preventDefault();return;}
  });
  window.addEventListener('resize',()=>UI.drawAllCharts());

  /* boot ambience */
  UI.bootAnim();UI.bootLog();
  UI.loop();
};

UI.pauseMenu=function(){
  if(!S||!el('boot').classList.contains('hidden'))return;
  S.paused=true;UI.renderTop();
  UI.openModal({title:'The evening is on hold',sub:'On hold',slim:true,
    body:'<div class="grid g2" style="gap:7px;margin-bottom:12px">'+
      [['In-game time',fmtTick(S.tick)],['Net worth',fmtC(netWorth())],['Global heat',fmtN(S.heat,1)],['Seed',hashStr(String(S.seed)).toUpperCase()]].map(q=>'<div class="card" style="padding:8px"><div class="cap" style="font-size:8px">'+q[0]+'</div><div class="num" style="font-size:13px;margin-top:3px">'+q[1]+'</div></div>').join('')+'</div>'+
      '<div class="notice">The city is frozen. Resume, save, or step away for a while.</div>',
    footer:'<button class="btn" data-m="manual">Field notes</button><span class="spacer"></span><button class="btn" data-m="title">Title</button><button class="btn primary" data-m="resume">Resume ▸</button>',
    onMount:(m,close)=>{
      m.querySelector('[data-m="resume"]').addEventListener('click',()=>{close();S.paused=false;UI.renderTop();});
      m.querySelector('[data-m="manual"]').addEventListener('click',()=>{close();UI.manual();});
      m.querySelector('[data-m="title"]').addEventListener('click',()=>{close();UI.toTitle();});
    }});
};

/* ------------------------------ boot visuals ----------------------------- */
UI.bootAnim=function(){
  const c=el('bootbg');if(!c||!c.getContext)return;
  const x=c.getContext('2d');let W=innerWidth,H=innerHeight,dust=[];
  const resize=()=>{W=innerWidth;H=innerHeight;c.width=W;c.height=H;c.style.width=W+'px';c.style.height=H+'px';
    dust=Array.from({length:70},()=>({x:Math.random()*W,y:Math.random()*H,s:Math.random()*1.3+.4,v:Math.random()*.16+.04}));};
  resize();window.addEventListener('resize',resize);
  function frame(){
    requestAnimationFrame(frame);
    if(el('boot').classList.contains('hidden'))return;
    x.clearRect(0,0,W,H);
    const g=x.createLinearGradient(0,0,0,H);
    g.addColorStop(0,'#292622');g.addColorStop(.6,'#1f1d1a');g.addColorStop(1,'#171513');
    x.fillStyle=g;x.fillRect(0,0,W,H);
    const halo=x.createRadialGradient(W*.78,H*.24,10,W*.78,H*.24,Math.min(W,H)*.45);
    halo.addColorStop(0,'rgba(140,95,43,.26)');halo.addColorStop(1,'rgba(140,95,43,0)');
    x.fillStyle=halo;x.fillRect(0,0,W,H);
    for(const p of dust){p.y-=p.v;if(p.y<0){p.y=H;p.x=Math.random()*W;}
      x.fillStyle='rgba(232,199,145,'+(.04+p.s*.05)+')';x.fillRect(p.x,p.y,p.s,p.s);}
  }
  frame();
};
UI.bootLog=function(){
  const out=el('bootlog');if(!out)return;
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
  let i=0;const add=()=>{if(i>=lines.length)return;const d=document.createElement('div');d.textContent=lines[i++];out.appendChild(d);while(out.children.length>8&&out.firstChild)out.firstChild.remove();setTimeout(add,150+Math.random()*170);};
  add();
};

/* ------------------------------ main loop --------------------------------- */
UI.loop=function(){
  let last=performance.now(),acc=0,anim=0,fps=0,fpsT=last,gameOverShown=false;
  function frame(now){
    requestAnimationFrame(frame);
    const dt=Math.min(.25,(now-last)/1000);last=now;
    fps++;if(now-fpsT>=1000){el('st-fps').textContent=fps;fps=0;fpsT=now;}
    const bootVisible=!el('boot').classList.contains('hidden');
    if(S&&!bootVisible&&!S.paused&&!UI.modalOpen()&&!S.gameOver){
      acc+=dt*S.speed;let n=0;
      while(acc>=1&&n<10){NL.step(1);acc-=1;n++;if(S.paused||S.gameOver)break;}
      if(n)UI.render(false);
      if(n&&S.settings.sound&&Math.random()<.10)UI.sfx('tick');
    }else acc=0;
    if(now-anim>220){anim=now;if(S&&!bootVisible)UI.drawAllCharts();}
    if(S&&S.gameOver&&!gameOverShown){
      gameOverShown=true;S.paused=true;
      UI.openModal({title:'The story ends here',sub:'The last page',slim:true,
        body:'<div class="notice r">'+esc(S.gameOver)+' · this run is finished.</div><div class="divider"></div>'+
          '<div class="statline"><span>Final worth</span><b>'+fmtC(netWorth())+'</b></div>'+
          '<div class="statline"><span>Hours played</span><b>'+S.tick+'</b></div>'+
          '<div class="statline"><span>Deliveries</span><b>'+S.stats.deliveries+'</b></div>'+
          '<div class="statline"><span>Units moved</span><b>'+fmtU(S.stats.unitsSold)+'</b></div>'+
          '<div class="statline"><span>Inspections</span><b>'+S.stats.audits+'</b></div>',
        footer:'<button class="btn" data-mclose>Look around</button><button class="btn primary" data-m="new">Begin a new story</button>',
        onMount:(m,close)=>{m.querySelector('[data-m="new"]').addEventListener('click',()=>{close();gameOverShown=false;UI.newGameModal();});}});
    }
  }
  requestAnimationFrame(frame);
};

/* ------------------------------ settings (no-state safe) ----------------- */
const _origSettings=UI.settings;
UI.settings=function(){
  if(S){_origSettings();return;}
  const cfg=Object.assign({density:'clean',sound:true,autopause:true,autosave:true,showRoutes:true,tutorialDone:false},UI.readStoredSettings());
  const rows=[['sound','Sound effects','Synthesised UI blips and alerts.'],['autopause','Pause on surprises','Halt on audits and major market shocks.'],['autosave','Autosave each day','Write state to local storage each in-game day.'],['showRoutes','Draw courier routes','Draw transit vectors on the city graph.'],['density','Detail level','Reveal raw market numbers and the engine console.']];
  UI.openModal({title:'Options',sub:'Make it yours',slim:true,
    body:'<div class="grid" style="gap:4px">'+rows.map(r=>'<div class="row" style="padding:8px;border-bottom:1px solid var(--line);gap:10px"><div style="flex:1"><div class="t">'+r[1]+'</div><div class="s">'+r[2]+'</div></div><div class="switch '+((cfg[r[0]]&&cfg[r[0]]!=='clean')?'on':'')+'" data-bs="'+r[0]+'"><span class="knob"></span></div></div>').join('')+'</div><div class="notice" style="margin-top:10px">These defaults will be applied to newly created operations.</div>',
    footer:'<button class="btn" data-mclose>Cancel</button><button class="btn primary" data-m="ok">Save Defaults</button>',
    onMount:(m,close)=>{
      m.querySelectorAll('[data-bs]').forEach(sw=>sw.addEventListener('click',()=>{const k=sw.getAttribute('data-bs');cfg[k]=k==='density'?(cfg.density==='clean'?'analyst':'clean'):!cfg[k];sw.classList.toggle('on',k==='density'?cfg.density==='analyst':cfg[k]);}));
      m.querySelector('[data-m="ok"]').addEventListener('click',()=>{try{localStorage.setItem('nightledger.settings',JSON.stringify(cfg));}catch(e){}close();UI.toast('Options saved','Used for the next story.','good');});
    }});
};

/* ------------------------------ patch: focus / tutorial ------------------ */
UI.toggleFocus=function(){
  UI.focusMode=!UI.focusMode;
  el('side').classList.toggle('hidden',UI.focusMode);
  el('main').style.gridTemplateColumns=UI.focusMode?'58px minmax(0,1fr)':'';
  UI.render(true);
  UI.toast(UI.focusMode?'A wider desk':'Everything back',UI.focusMode?'The side column is tucked away. Press F10 to bring it back.':'All panels restored.','');
};
const _origTutorial=UI.tutorial;
UI.tutorial=function(){if(S&&UI.sel.view!=='overview')UI.setView('overview');setTimeout(()=>_origTutorial(),120);};


/* =====================================================================================
   Nightledger — LIVING WORLD LAYER  (RDR2-style persistent hidden simulation)
   ---------------------------------------------------------------------------------
   Every structure below is plain JSON inside S.world, so it survives save/load and is
   covered by the deterministic state hash. No subsystem here renders by default:
   the clean UI only sees a handful of qualitative signals. The Analyst layer (F2)
   and the Systems view expose the raw machinery.
   ===================================================================================== */
const WDAYS=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
const WSHIFTS=['A · Dawn','B · Day','C · Night'];
const WROUTINE=['Sleep','Home','Work','Social','Night','Errand'];
const WROUTINE_COL=['#2a2722','#a595bb','#c6766e','#d9a15b','#c9a25f','#c9a25f'];
const WRUMORS=['Price rise','Shortage','Crackdown','New supplier','Festival','Patrol change','Quality drop'];
const Standing=['reliability','discretion','fairness','generosity','ruthlessness'];

function wlog(kind,text,meta){
  if(!S||!S.world)return;
  S.world.log.unshift({t:S.tick,kind:kind,text:text,meta:meta||null});
  if(S.world.log.length>140)S.world.log.length=140;
}
function makeWClient(c){
  const off=ri(-1,1),nightowl=(TRAITS[c.trait]&&(c.trait==='impulsive'||c.trait==='volume'))?1:0;
  const sch=[];
  for(let h=0;h<24;h++){
    let r;
    if(h<6-nightowl)r=0;else if(h<8)r=1;else if(h<17)r=2;else if(h<21)r=3;else if(h<23)r=4;else r=nightowl?4:0;
    if(c.district%3===0&&h>=12&&h<14)r=5;
    sch.push(clamp(r+((h+off+c.id)%11===0?1:0),0,5));
  }
  return{id:c.id,sch:sch,awake:true,loc:c.district,energy:rr(.62,.95),stress:rr(.04,.3),
    need:rr(.2,.6),suspicion:rr(0,.18),fairness:rr(.4,.6),memory:[],lastDeal:-999,
    meals:0,social:rr(.3,.7),routine:rr(0,1)>.5?'Regular':'Irregular'};
}
function makeWCourier(c){
  return{id:c.id,hydration:rr(.76,.95),sleepDebt:rr(0,.18),injury:0,stress:rr(.04,.24),
    bond:rr(.1,.4),gear:rr(.9,.99),shift:ri(0,2),meals:0,home:ri(0,ND-1),lastMeal:-99,shiftsRun:0};
}
function initWorld(s){
  const W={
    v:2,
    calendar:{dow:0,monthDay:1,payday:false,holiday:'',daylight:0},
    climate:{temp:13+rr(-3,3),humidity:rr(.45,.7),rain:0,groundWet:0,
      visibility:.92,heatIndex:0},
    district:[],clients:[],couriers:[],rivals:[],
    crew:{affinity:[],incidents:0},
    economy:{cpi:1,liquidity:1,wageIndex:1,consumerPower:[],wholesaleLead:0,credit:.12,
      rentIndex:1},
    dossier:{threads:[],reports:[],evidence:0,witnesses:0,lastInspection:-999},
    honor:{reliability:.5,discretion:.55,fairness:.5,generosity:.35,ruthlessness:.2,code:.5},
    gear:{rigWear:.02,vehicle:.96,sealant:.94,packaging:.96,maintenanceDue:0,lastService:0},
    rumors:{nodes:[],born:0},
    events:{blackout:0,strike:0,festival:0,garbageStrike:0},
    mods:[],lots:{},depotCond:[],
    stats:{hours:0,witnessReports:0,rumorsBorn:0,evidenceChains:0,npcActions:0,
      sleepHours:0,services:0,meals:0,rumorHops:0,dossierChains:0},
    log:[],prevSales:0,prevUnits:0,prevInspections:0,prevDeals:0,tickVolume:0
  };
  for(let d=0;d<ND;d++){
    W.district.push({patrol:rr(.25,.5),patrolShift:0,footfall:1,noise:rr(.1,.3),lighting:.85,
      streetLight:.9,garbage:rr(.1,.35),complaints:rr(0,.2),mood:rr(.45,.65),
      construction:0,curfew:0,flooding:0,
      demandBias:rr(.97,1.03),riskBias:rr(.95,1.05),lastFestival:-999});
    W.rumors.nodes.push({topic:'Quiet',strength:0,ttl:0,origin:d});
    W.economy.consumerPower.push(rr(.9,1.1));
  }
  W.clients=s.clients.map(makeWClient);
  W.couriers=s.couriers.map(makeWCourier);
  W.crew.affinity=s.couriers.map((a,i)=>s.couriers.map((b,j)=>i===j?1:rr(.3,.7)));
  W.rivals=s.rivals.map(r=>({bossMood:rr(.35,.7),shipmentEta:ri(8,40),pipeline:[],
    meetT:ri(12,60),accountant:rr(.4,.8),lastShipment:-999}));
  W.depotCond=Array.from({length:ND},()=>Array.from({length:NP},()=>({integrity:rr(.9,1),moisture:rr(.02,.1),seal:rr(.92,1)})));
  s.world=W;
  wlog('sys','Living world generated · '+ND+' districts · '+s.clients.length+' scheduled NPCs · '+s.couriers.length+' crew.');
  return W;
}
function ensureWorld(){
  if(!S)return null;
  if(!S.world||S.world.v!==2)initWorld(S);
  const W=S.world;
  if(!W.district||W.district.length!==ND)initWorld(S);
  return S.world;
}
function wMod(W,type,d,p,mag,why){W.mods.push({type:type,d:d,p:p,mag:mag,why:why});}

/* ------------------------------- PRE-SOLVER Hour ------------------------------- */
function worldTick(){
  const W=ensureWorld();if(!W)return;
  const h=S.hour,cal=W.calendar,cl=W.climate;
  W.stats.hours++;
  /* --- 1. calendar: weekday, pay cycles, civic holidays, daylight, moon --- */
  cal.dow=Math.floor(S.tick/24)%7;
  cal.monthDay=(S.day-1)%30+1;
  cal.payday=(cal.monthDay===5||cal.monthDay===20);
  cal.holiday=cal.monthDay===1?'Local holiday':cal.monthDay===15?'Mid-month fair':cal.monthDay===28?'Founders day':'';
  cal.daylight=clamp(Math.sin((h-6)/12*PI),0,1);
  if(cal.payday&&h===9)wlog('calendar','Payday: district purchasing power rises.');
  if(cal.holiday&&h===8)wlog('calendar',cal.holiday+' begins; footfall up, scrutiny relaxed.');
  /* --- 2. climate: OU temperature, humidity, pressure, wind, rain, wet ground --- */
  const seasonal=Math.sin((S.tick/(24*30))*2*PI)*8;
  const tempTarget=12+seasonal+cal.daylight*7;
  cl.temp=clamp(cl.temp+.22*(tempTarget-cl.temp)+nrm()*.32,-9,39);
  cl.humidity=clamp(cl.humidity+.08*(.60+(S.weather===2||S.weather===4?.14:0)-cl.humidity)+nrm()*.012,.16,.99);
  cl.rain=clamp(cl.rain*(S.weather===2||S.weather===4?.94:.80)+(S.weather===2?.10:S.weather===4?.19:0)+rr(0,.006),0,1);
  cl.groundWet=clamp(cl.groundWet*.984+cl.rain*.022,0,1);
  cl.visibility=clamp(1-cl.rain*.40-(S.weather===3?.34:0)-(1-cal.daylight)*.10-(1-cl.humidity)*.02,.10,1);
  cl.heatIndex=clamp((cl.temp-18)/22+cl.humidity*.25,-.5,1.2);
  /* climate can override the visible weather state with hysteresis */
  const oldW=S.weather;
  if(cl.rain>.82&&S.weather!==4&&chance(.22))S.weather=4;
  else if(cl.rain>.44&&S.weather!==2&&S.weather!==4&&chance(.16))S.weather=2;
  else if(cl.humidity>.90&&cl.temp<17&&S.weather!==3&&chance(.14))S.weather=3;
  else if(cl.rain<.10&&cl.humidity<.52&&S.weather!==0&&chance(.10))S.weather=0;
  if(oldW!==S.weather){S.wTimer=ri(4,11);pushNews('Weather','Barometric shift → '+WEATHER[S.weather].key.toLowerCase()+'.','info');wlog('climate','Weather shifted by the climate model: '+WEATHER[S.weather].key+'.');}
  /* --- 3. district ecology: patrol shifts, footfall, noise, light, flood, works --- */
  let patrolAvg=0,cityMood=0,constrAvg=0;
  for(let d=0;d<ND;d++){
    const wd=W.district[d],B=DISTRICTS[d],D=S.districts[d];
    wd.patrolShift=Math.floor(h/8);
    const shiftBase=[.40,.29,.57][wd.patrolShift];
    wd.patrol=clamp(shiftBase*.55+B.risk*.34+D.heat/280+wd.complaints*.24+
      (cal.holiday?-.07:.02)+nrm()*.018,.05,1);
    wd.footfall=clamp(TOD[h]*(.72+cal.daylight*.28)*(S.weather===4?.70:S.weather===2?.86:1)*
      (cal.payday?1.16:1)*(cal.holiday?1.20:1)*(1-wd.curfew*.34)*(1-wd.construction*.18)+nrm()*.028,.08,2.3);
    wd.noise=clamp((h>=19||h<2?.48:.10)+wd.footfall*.11+wd.garbage*.08+nrm()*.018,0,1);
    wd.streetLight=clamp(.94-(1-cal.daylight)*.10-(W.events.blackout>0?.65:0)+nrm()*.01,.05,1);
    wd.lighting=clamp(cal.daylight*.75+wd.streetLight*.32,0,1);
    wd.flooding=clamp(wd.flooding*.965+((B.key==='Lowlight'||B.key==='Docklands')?cl.groundWet*.014:0),0,1);
    wd.garbage=clamp(wd.garbage*.995+(W.events.garbageStrike>0?.004:.0006),0,1);
    wd.complaints=clamp(wd.complaints*.996+wd.noise*.0009+D.heat*.000015,0,1);
    wd.mood=clamp(wd.mood+(.55-wd.mood)*.018+(cal.payday?.008:0)+(cal.holiday?.006:0)+nrm()*.005,0,1);
    wd.construction=Math.max(0,wd.construction-1);
    wd.curfew=Math.max(0,wd.curfew-1);
    if(wd.construction===0&&chance(.0022)){wd.construction=ri(8,34);wlog('street','Roadworks in '+B.short+': transit slowed ~'+ri(8,34)+'h.');}
    if(D.heat>68&&wd.curfew===0&&chance(.004)){wd.curfew=ri(8,18);pushNews('City','Curfew declared in '+B.short+'.','bad');wlog('street','Curfew in '+B.short+'.');}
    patrolAvg+=wd.patrol;cityMood+=wd.mood;constrAvg+=wd.construction>0?1:0;
    /* hidden → visible: patrol perturbs local scrutiny, mood bleeds into loyalty */
    D.heat=clamp(D.heat+wd.patrol*.0035+wd.complaints*.0028-.0018,0,100);
    D.loyalty=clamp(D.loyalty+(wd.mood-.5)*.0005,0,1);
  }
  patrolAvg/=ND;cityMood/=ND;constrAvg/=ND;
  /* --- 4. global city events --- */
  for(const k of Object.keys(W.events))if(W.events[k]>0)W.events[k]--;
  if(chance(.0016)){W.events.blackout=ri(2,7);pushNews('City','Grid fault: street lighting degraded citywide.','bad');wlog('city','Blackout for '+W.events.blackout+'h.');}
  if(chance(.0012)){W.events.strike=ri(10,28);wlog('city','Transit strike declared.');}
  if(chance(.0010)){W.events.festival=ri(8,20);pushNews('City','Street festival: nightlife demand surges.','good');wlog('city','Festival window opened.');}
  if(chance(.0014)){W.events.garbageStrike=ri(20,60);wlog('city','Refuse collection suspended.');}
  /* --- 5. NPC daily routines, energy, stress, need, memory decay --- */
  const weekend=(cal.dow>=5);
  const wcOld=W.clients;
  W.clients=S.clients.map(c=>{
    let q=wcOld.find(x=>x.id===c.id);if(!q)q=makeWClient(c);
    const act=q.sch[h];
    q.awake=(act!==0);
    q.loc=act===2?clamp(c.district+((h+q.id)%3)-1,0,ND-1):(act===3||act===4?clamp(c.district+((h*7+q.id)%3)-1,0,ND-1):c.district);
    if(!q.awake){q.energy=clamp(q.energy+.026,0,1);q.stress=clamp(q.stress-.012,0,1);W.stats.sleepHours++;}
    else{q.energy=clamp(q.energy-.007-(act===2?.004:0)+nrm()*.002,0,1);q.stress=clamp(q.stress+.003+(act===2?.002:0)-q.social*.001+nrm()*.002,0,1);}
    q.need=clamp(q.need+.008-(h===8||h===13||h===20?.10:0),0,1);
    q.suspicion=clamp(q.suspicion*.992+(W.district[c.district].patrol*.0006),0,1);
    for(const m of q.memory)m.val*=.986;
    q.memory=q.memory.filter(m=>m.val>.02).slice(-10);
    /* hidden → visible: sleeping clients cannot be reached; physiology shapes mood */
    if(!q.awake)c.cooldown=Math.max(c.cooldown,2);
    c.mood=clamp(c.mood+(q.energy-.65)*.004-(q.stress-.35)*.003-(q.suspicion*.001),.1,1);
    c.loyalty=clamp(c.loyalty+(q.fairness-.5)*.0006,0,1);
    if(cal.payday&&h===9)c.budget=clamp(c.budget+rr(25,90)*(1+DISTRICTS[c.district].wealth*.5),60,4200);
    W.stats.npcActions++;
    return q;
  });
  /* --- 6. courier physiology: hydration, sleep debt, injury, stress, bond, gear --- */
  const wqOld=W.couriers;
  W.couriers=S.couriers.map(c=>{
    let q=wqOld.find(x=>x.id===c.id);if(!q)q=makeWCourier(c);
    const busy=c.status==='Outbound'||c.status==='Returning';
    q.hydration=clamp(q.hydration-(busy?.010:.004)+(h===8||h===13||h===20?.055:0),0,1);
    q.sleepDebt=clamp(q.sleepDebt+(busy?.010:.001)-(c.status==='Rest'?.035:.006),0,1);
    q.injury=clamp(q.injury*.994-(c.status==='Rest'?.012:0)+(busy&&chance(.0015)?.12:0),0,1);
    q.stress=clamp(q.stress+(busy?.006:-.002)+(q.sleepDebt*.003)-(c.status==='Rest'?.010:0)+nrm()*.002,0,1);
    q.bond=clamp(q.bond+(busy?.0012:0)+(c.wage>160?.0004:0)-q.stress*.0004,0,1);
    q.gear=clamp(q.gear-(busy?.0009:.0002),0,1);
    if(h===8||h===13||h===20){q.meals++;W.stats.meals++;}
    /* hidden → visible */
    c.fatigue=clamp(c.fatigue*.86+(1-q.hydration)*.10+q.sleepDebt*.10+q.injury*.08,0,1);
    c.morale=clamp(c.morale*.93+(1-q.stress)*.05+q.bond*.03+(c.status==='Rest'?.02:0),0,1);
    c.stealth=clamp(c.stealth*.995+q.gear*.005,0,1);
    W.stats.npcActions++;
    return q;
  });
  /* --- 7. crew affinity matrix + camp morale --- */
  const n=S.couriers.length;
  if(!W.crew.affinity||W.crew.affinity.length!==n){
    W.crew.affinity=S.couriers.map((a,i)=>S.couriers.map((b,j)=>i===j?1:rr(.3,.7)));
  }
  for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){
    const shared=(S.couriers[i].status===S.couriers[j].status)?1:0;
    W.crew.affinity[i][j]=clamp(W.crew.affinity[i][j]+(shared?.0008:-.0004)+nrm()*.0006,.05,1);
    W.crew.affinity[j][i]=W.crew.affinity[i][j];
  }
  /* --- 8. rival logistics: shipments with lead times, boss mood, meets --- */
  for(let i=0;i<S.rivals.length;i++){
    const r=S.rivals[i];W.rivals[i]=W.rivals[i]||{bossMood:.5,shipmentEta:20,pipeline:[],meetT:30,accountant:.6,lastShipment:-999};
    const q=W.rivals[i];
    q.bossMood=clamp(q.bossMood+(.5-q.bossMood)*.02+nrm()*.012,0,1);
    q.meetT--;if(q.meetT<=0){q.meetT=ri(30,80);r.stance=clamp(r.stance+nrm()*.05,-1,1);wlog('rival',r.name+' leadership met; stance adjusted.');}
    if(--q.shipmentEta<=0){
      q.shipmentEta=ri(22,60);q.lastShipment=S.tick;r.strength=clamp(r.strength+.012,0,1);
      const strong=r.territory.map((v,d)=>[v,d]).sort((a,b)=>b[0]-a[0]).slice(0,2);
      for(const [,d]of strong)wMod(W,'supply',d,-1,1.14,'rival shipment');
      wlog('rival',r.name+' shipment landed; local supply eases.');
    }
  }
  /* --- 9. shadow macro-economy --- */
  const e=W.economy;
  e.cpi=clamp(e.cpi+(1-e.cpi)*.002+nrm()*.0007,.90,1.16);
  e.liquidity=clamp(e.liquidity+(1-e.liquidity)*.006+nrm()*.004,.55,1.4);
  e.wageIndex=clamp(e.wageIndex+(1-e.wageIndex)*.003+nrm()*.002,.85,1.3);
  e.credit=clamp(e.credit+(.12-e.credit)*.01+nrm()*.003,.02,.4);
  e.rentIndex=clamp(e.rentIndex+(e.cpi-e.rentIndex)*.004,.9,1.2);
  e.wholesaleLead=Math.max(0,e.wholesaleLead-1);
  if(chance(.002)){e.wholesaleLead=ri(6,20);wlog('economy','Wholesale lead times extend '+e.wholesaleLead+'h.');}
  for(let d=0;d<ND;d++){
    const t=e.consumerPower[d],target=1+DISTRICTS[d].wealth*.08+(cal.payday?.10:0)-(1-W.district[d].mood)*.10;
    e.consumerPower[d]=clamp(t+(target-t)*.02+nrm()*.003,.65,1.45);
  }
  S.feedTarget.base=clamp(7.2*e.cpi*(1+(1-e.liquidity)*.16),3.5,20);
  S.feedTarget.additive=clamp(11*e.cpi*(1+e.wholesaleLead*.004),5,30);
  S.feedTarget.packs=clamp(1.4*e.cpi,0.6,4);
  /* --- 10. rumor diffusion across the district graph --- */
  const nodes=W.rumors.nodes;
  for(let d=0;d<ND;d++){
    const q=nodes[d]||{topic:'Quiet',strength:0,ttl:0,origin:d};
    q.strength=clamp(q.strength*.972,0,1);q.ttl=Math.max(0,q.ttl-1);
    if(q.ttl===0||q.strength<.05){q.topic='Quiet';q.strength=0;}
    nodes[d]=q;
  }
  /* snapshot strengths so a rumour can only travel One hop per simulated hour;
     edges are visited on a 3-hour rotation, so citywide saturation takes days */
  const snap=nodes.map(n=>({topic:n.topic,strength:n.strength,ttl:n.ttl,origin:n.origin}));
  for(let ei=0;ei<EDGES.length;ei++){
    const ed=EDGES[ei];
    if((S.tick+ed[0]*7+ed[1]*3)%3!==0)continue;
    const a=snap[ed[0]],b=snap[ed[1]],na=nodes[ed[0]],nb=nodes[ed[1]];
    if(a.topic!=='Quiet'&&a.strength>b.strength+.20){
      nb.topic=a.topic;nb.origin=a.origin;nb.strength=clamp(a.strength*.38,0,1);nb.ttl=Math.max(nb.ttl,Math.floor(a.ttl*.70));W.stats.rumorHops++;
    }else if(b.topic!=='Quiet'&&b.strength>a.strength+.20){
      na.topic=b.topic;na.origin=b.origin;na.strength=clamp(b.strength*.38,0,1);na.ttl=Math.max(na.ttl,Math.floor(b.ttl*.70));W.stats.rumorHops++;
    }
  }
  /* --- 11. investigative dossier: witness reports mature into evidence threads --- */
  const dossier=W.dossier;
  for(let i=dossier.reports.length-1;i>=0;i--){
    const r=dossier.reports[i];r.ttl--;r.strength=clamp(r.strength*.994,0,1.5);
    if(r.ttl<=0)dossier.reports.splice(i,1);
  }
  if(dossier.reports.length>70)dossier.reports.length=70;
  for(let i=dossier.threads.length-1;i>=0;i--){
    const t=dossier.threads[i];t.ttl--;t.strength=clamp(t.strength*.997,0,20);
    if(t.ttl<=0)dossier.threads.splice(i,1);
  }
  const byD={};for(const r of dossier.reports)byD[r.d]=(byD[r.d]||0)+r.strength;
  for(const key of Object.keys(byD)){
    const d=+key;
    if(byD[d]>3.2&&!dossier.threads.some(t=>t.d===d&&t.ttl>0)){
      dossier.threads.push({id:nid(),d:d,p:ri(0,NP-1),strength:byD[d],ttl:ri(50,140),firstT:S.tick,lastT:S.tick});
      if(dossier.threads.length>24)dossier.threads.splice(0,dossier.threads.length-24);
      W.stats.evidenceChains++;W.stats.dossierChains++;
      wlog('dossier','Evidence chain opened for '+DISTRICTS[d].short+'.');
    }
  }
  const repSum=dossier.reports.reduce((a,r)=>a+r.strength,0);
  const thrSum=dossier.threads.reduce((a,t)=>a+t.strength,0);
  dossier.evidence=clamp(repSum*.20+thrSum*.12,0,100);
  dossier.witnesses=dossier.reports.length;
  /* --- 12. gear wear and item-level condition (lots + depot parcels) --- */
  const g=W.gear;
  g.rigWear=clamp(g.rigWear+.00016+S.jobs.length*.0007,0,1);
  g.vehicle=clamp(g.vehicle-.00010*S.couriers.filter(c=>c.status==='Outbound'||c.status==='Returning').length,0,1);
  g.sealant=clamp(g.sealant-.00007*(1+cl.humidity),0,1);
  g.packaging=clamp(g.packaging-.00006*(1+cl.rain),0,1);
  g.maintenanceDue=(g.rigWear>.32||g.vehicle<.66||g.sealant<.72)?1:0;
  if(g.maintenanceDue&&S.tick-g.lastService>90&&chance(.01))wlog('gear','Rig service overdue; yield ceiling degrading.');
  const lotMap={};
  for(const l of S.lots){
    let q=W.lots[l.id];
    if(!q)q={integrity:rr(.88,.99),moisture:rr(.02,.12),exposure:0,seal:rr(.90,1)};
    q.moisture=clamp(q.moisture+cl.humidity*.00025-(1-q.seal)*.0004,0,1);
    q.exposure=clamp(q.exposure+.00018*(1+cl.heatIndex),0,1);
    q.integrity=clamp(q.integrity-q.moisture*.00012-q.exposure*.00008,0,1);
    l.cond=q;
    lotMap[l.id]=q;
    if(q.integrity<.96)l.purity=clamp(l.purity-.00002,0,1);
  }
  const liveLots={};for(const l of S.lots)if(lotMap[l.id])liveLots[l.id]=lotMap[l.id];
  W.lots=liveLots;
  for(let d=0;d<ND;d++)for(let p=0;p<NP;p++){
    const q=W.depotCond[d][p],dep=S.depot[d][p];
    q.moisture=clamp(q.moisture+cl.humidity*.00022+W.district[d].flooding*.0004,0,1);
    q.integrity=clamp(q.integrity-q.moisture*.00009,0,1);
    if(dep.qty>0&&q.integrity<.97)dep.purity=clamp(dep.purity-.000015,.2,1);
  }
  /* --- 13. reputation facets ("honor") drift toward baseline --- */
  const H=W.honor;
  for(const k of Standing)H[k]=clamp(H[k]+(.5-H[k])*.00035+nrm()*.0004,0,1);
  H.code=clamp(H.reliability*.25+H.discretion*.28+H.fairness*.22+H.generosity*.13+(1-H.ruthlessness)*.12,0,1);
  S.rep=clamp(S.rep+(H.code-.5)*.008,0,100);
  /* --- 14. rebuild the hidden modifier set consumed by newsMult() --- */
  W.mods=[];
  const calDemand=1+(cal.payday?.09:0)+(cal.holiday?.11:0)-(cl.rain>.5?.05:0)+(W.events.festival>0?.10:0);
  wMod(W,'demand',-1,-1,clamp(calDemand,.80,1.35),'calendar / weather');
  wMod(W,'price',-1,-1,clamp(1+(e.cpi-1)*.55,.90,1.12),'inflation');
  if(W.events.strike>0)wMod(W,'demand',-1,-1,.94,'transit strike');
  if(W.events.blackout>0)wMod(W,'demand',-1,-1,1.05,'blackout');
  if(cl.rain>.55)wMod(W,'supply',-1,-1,clamp(1-cl.rain*.12,.85,1),'wet logistics');
  for(let d=0;d<ND;d++){
    const wd=W.district[d];
    if(wd.construction>0)wMod(W,'demand',d,-1,.87,'roadworks');
    if(wd.curfew>0)wMod(W,'demand',d,-1,.74,'curfew');
    if(wd.flooding>.35)wMod(W,'demand',d,-1,.85,'flooding');
    if(wd.patrol>.68)wMod(W,'demand',d,-1,.93,'patrol saturation');
    if(cal.payday)wMod(W,'demand',d,5,1.14,'payday premium');
    if(cal.payday)wMod(W,'demand',d,6,1.12,'payday premium');
    const rum=nodes[d];
    if(rum.strength>.28){
      if(rum.topic==='Price rise')wMod(W,'price',d,-1,1+rum.strength*.08,'rumor');
      else if(rum.topic==='Shortage')wMod(W,'supply',d,-1,1-rum.strength*.24,'rumor');
      else if(rum.topic==='Crackdown')wMod(W,'demand',d,-1,1-rum.strength*.15,'rumor');
      else if(rum.topic==='Festival')wMod(W,'demand',d,-1,1+rum.strength*.14,'rumor');
      else if(rum.topic==='Quality drop')wMod(W,'price',d,-1,1-rum.strength*.10,'rumor');
    }
    wMod(W,'demand',d,-1,wd.demandBias*W.economy.consumerPower[d],'local purchasing power');
  }
  if(W.mods.length>40)W.mods.length=40;
  /* --- 15. hidden → visible couplings before the market market runs --- */
  S.scrutiny=clamp(S.scrutiny+patrolAvg*.030+dossier.evidence*.0012,.05,.9);
  S.mood=clamp(S.mood+(cityMood-.5)*.016,.72,1.32);
  S.macro=clamp(S.macro*(1+(e.cpi-1)*.04),.82,1.24);
  S.macroTarget=clamp(S.macroTarget+(e.cpi-1)*.018,.8,1.25);
  const baseYield=clamp(.62+up('lab')*.055+has('r2')*.08,.5,1.0);
  S.mods.yield=clamp(baseYield*(1-g.rigWear*.34),.25,1);
  S.mods.maxGrade=clamp((.62+up('lab')*.065+has('r2')*.03)*(1-g.rigWear*.16),.3,.99);
  S.mods.speed=clamp((1+up('logistics')*.13+(has('r5')?.2:0))*(1-constrAvg*.10-cl.rain*.06),.5,2.2);
  S.mods.complication=clamp(.055-up('logistics')*.006,.012,.06)*(1+patrolAvg*.42+(1-cl.visibility)*.30)*(1.1-g.sealant*.12);
  S.mods.auditSeverity=clamp(1-up('counsel')*.11,.4,1)*(1+dossier.evidence*.010);
  S.mods.reconFee=clamp(.095-up('cover')*.009-(has('r7')?.02:0),.02,.12)*(1+e.credit*.22);
  S.mods.heatDecay=(1+up('counsel')*.20+(has('r8')?.25:0))*(1-cl.rain*.08);
  S.diag.hiddenPersons=W.clients.length+W.couriers.length+ND+S.rivals.length;
  S.diag.worldLoad=clamp(patrolAvg*.4+dossier.evidence/200+g.rigWear*.3,0,1);
  S.diag.solverIter+=28+W.mods.length+W.clients.length;
}

/* ------------------------------- POST-SOLVER Hour ------------------------------ */
function worldPostTick(){
  const W=ensureWorld();if(!W)return;
  const ds=Math.max(0,S.stats.sales-W.prevSales);
  const du=Math.max(0,S.stats.unitsSold-W.prevUnits);
  W.prevSales=S.stats.sales;W.prevUnits=S.stats.unitsSold;
  W.tickVolume=du;
  /* rumour seeding from the news wire */
  for(const n of S.news){
    if(n.t!==S.tick)break;
    if(n.tone==='good'||n.tone==='bad'){
      const d=ri(0,ND-1),topic=pick(WRUMORS);
      W.rumors.nodes[d]={topic:topic,strength:rr(.55,.95),ttl:ri(9,32),origin:d};
      W.rumors.born++;W.stats.rumorsBorn++;
      wlog('rumor','"'+topic+'" starts in '+DISTRICTS[d].short+'.');
    }
  }
  /* witness reports from this hour's commercial activity */
  if(du>0||ds>0){
    const tries=Math.min(5,Math.floor(du*.05)+1);
    for(let i=0;i<tries;i++){
      const d=ri(0,ND-1),wd=W.district[d];
      const p=clamp(.10+wd.patrol*.34+wd.noise*.12+(1-W.climate.visibility)*.22+(1-wd.lighting)*.14,.02,.85);
      if(!chance(p))continue;
      W.dossier.reports.push({t:S.tick,d:d,p:ri(0,NP-1),strength:rr(.25,.95),ttl:ri(26,110)});
      W.stats.witnessReports++;
      if(chance(.12))wlog('dossier','Bystander report filed near '+DISTRICTS[d].short+'.');
    }
  }
  /* honor facets react to how the player behaved */
  const H=W.honor;
  if(ds>0){H.reliability=clamp(H.reliability+.0035*Math.min(ds,4),0,1);H.fairness=clamp(H.fairness+.0007,0,1);}
  if(S.stats.audits>W.prevInspections){H.discretion=clamp(H.discretion-.035,0,1);wlog('honor','Audit damaged your standing for discretion.');}
  W.prevInspections=S.stats.audits;
  if(S.cooldown>0)H.discretion=clamp(H.discretion+.0008,0,1);
  H.code=clamp(H.reliability*.25+H.discretion*.28+H.fairness*.22+H.generosity*.13+(1-H.ruthlessness)*.12,0,1);
  /* crew rapport from completed runs */
  for(const c of S.couriers){
    const q=W.couriers.find(x=>x.id===c.id);if(!q)continue;
    if(c.status==='Returning')q.bond=clamp(q.bond+.004,0,1);
  }
  /* diagnostics */
  S.diag.agentUpdates+=W.clients.length+W.couriers.length;
  if(S.tick%24===0)wlog('sys','Day '+S.day+' closed · '+fmtN(W.stats.npcActions)+' small choices · '+W.dossier.reports.length+' live reports.');
}

/* ------------------------------- player action ------------------------------- */
A.serviceGear=()=>{const b=blocked();if(b)return b;const W=ensureWorld();if(!W)return{ok:false,msg:'No world state.'};
  const cost=Math.round(180+W.gear.rigWear*900+(1-W.gear.vehicle)*520+(1-W.gear.sealant)*260);
  if(S.cash<cost)return{ok:false,msg:'Full service requires '+fmtC(cost)+' liquid cash.'};
  spend(cost,'Workshop service & re-sealing','maintenance');
  W.gear.rigWear=.01;W.gear.vehicle=.98;W.gear.sealant=.98;W.gear.packaging=.98;
  W.gear.maintenanceDue=0;W.gear.lastService=S.tick;
  W.stats.services++;
  for(const q of W.couriers)q.gear=.98;
  pushNews('WORLD','Workshop completed a full service: rig wear reset, parcels re-sealed.','good');
  wlog('gear','Full service at '+fmtTick(S.tick)+' for '+fmtC(cost)+'.');
  return{ok:true,msg:'Rig serviced for '+fmtC(cost)+'. Yield, purity ceiling and transit reliability restored.'};
};
A.seedRumor=function(topic,d){
  const W=ensureWorld();
  const t=topic||pick(WRUMORS),dd=d===undefined?ri(0,ND-1):clamp(d,0,ND-1);
  W.rumors.nodes[dd]={topic:t,strength:.9,ttl:30,origin:dd};
  W.rumors.born++;W.stats.rumorsBorn++;
  wlog('rumor','Planted "'+t+'" in '+DISTRICTS[dd].short+'.');
  return{ok:true,msg:'Rumour planted in '+DISTRICTS[dd].short+'.'};
};

/* -------------------------------- UI: signals -------------------------------- */
UI.clientAvailability=function(id){
  const W=ensureWorld();if(!W)return'';
  const q=W.clients.find(x=>x.id===id);
  if(!q)return'<span class="dim">No routine data.</span>';
  const act=WROUTINE[q.sch[S.hour]]||'Home';
  const disc=q.suspicion<.3?'Discretion GOOD':q.suspicion<.6?'Discretion FAIR':'Wary';
  const base='<span class="tag '+(q.awake?'g':'a')+'">'+(q.awake?'Available':'Asleep')+'</span> '+act+' · '+disc;
  const raw=S.settings.density==='analyst'?' <span class="tiny dim">energy '+fmtP(q.energy,0)+' · stress '+fmtP(q.stress,0)+' · suspicion '+fmtP(q.suspicion,0)+' · '+q.memory.length+' memories</span>':'';
  return base+raw;
};
UI.worldTicker=function(){
  const W=ensureWorld();if(!W)return'';
  const cal=W.calendar,cl=W.climate;
  const shift=WSHIFTS[W.district[0].patrolShift];
  const rum=W.rumors.nodes.reduce((a,b)=>b.strength>a.strength?b:a,{topic:'Quiet',strength:0});
  const honor=W.honor.code>.68?'Trusted':W.honor.code>.55?'Respected':W.honor.code>.42?'Mixed':'Notorious';
  const chip=(t,c)=>'<span class="chip" style="font-size:9px;padding:2px 7px'+(c?';color:'+c:'')+'">'+t+'</span>';
  const bits=[
    chip(WDAYS[cal.dow]+' '+fmtHour(S.hour),'var(--txt2)'),
    chip(WEATHER[S.weather].key+' '+fmtN(cl.temp,0)+'°C',WEATHER[S.weather].col),
    chip('Patrol '+shift,'var(--am)'),
    chip(cal.payday?'Payday':cal.holiday?cal.holiday:'An ordinary day',cal.payday?'var(--gr)':''),
    chip(rum.strength>.28?'Rumour · '+rum.topic:'The street is quiet',rum.strength>.28?'var(--vi)':''),
    chip('Standing · '+honor,'var(--cy)'),
    chip(W.dossier.reports.length+' witness notes · '+W.mods.length+' quiet effects','var(--dim)')
  ];
  return'<div class="row wrap" style="gap:5px;margin-top:9px;padding:7px 9px;background:linear-gradient(90deg,#171513,#12100f);border:1px solid var(--line);border-left:2px solid var(--cy2);border-radius:2px"'+
    tip('The city today','A few signs from the private life of the city. Press F3 for a closer look, F2 for the deeper state.')+'>'+
    '<span class="cap" style="font-size:8px;margin-right:4px">Tonight</span>'+bits.join('')+'<span class="spacer"></span>'+
    '<button class="btn ghost sm" data-act="worldlens" style="font-size:8px">F3 · Look closer ▸</button></div>';
};
UI.worldSummary=function(){
  const W=ensureWorld();if(!W)return'';
  const cal=W.calendar,cl=W.climate,H=W.honor;
  const patrol=mean(W.district.map(x=>x.patrol));
  const rum=W.rumors.nodes.reduce((a,b)=>b.strength>a.strength?b:a,{topic:'Quiet',strength:0});
  const lines=[
    ['Date',WDAYS[cal.dow]+' · day '+cal.monthDay+(cal.payday?' · Payday':cal.holiday?' · '+cal.holiday:'')],
    ['Conditions',WEATHER[S.weather].key+' · '+fmtN(cl.temp,1)+'°C · humidity '+fmtP(cl.humidity,0)+' · visibility '+fmtP(cl.visibility,0)+' · transit '+WEATHER[S.weather].speed.toFixed(2)+'×'],
    ['Streets','patrol '+fmtP(patrol,0)+' · footfall '+fmtN(mean(W.district.map(x=>x.footfall)),2)+' · complaints '+fmtP(mean(W.district.map(x=>x.complaints)),1)],
    ['Word on the street',rum.strength>.2?rum.topic+' (strength '+fmtP(rum.strength,0)+', seeded in '+DISTRICTS[rum.origin].short+')':'nothing significant'],
    ['Your standing',(H.code>.6?'trusted':H.code>.45?'mixed':'notorious')+' · reliability '+fmtP(H.reliability,0)+' · discretion '+fmtP(H.discretion,0)],
    ['Exposure',W.dossier.reports.length+' live witness reports · '+W.dossier.threads.length+' evidence chains · '+fmtN(W.dossier.evidence,1)+' dossier pressure'],
    ['Workshop','rig wear '+fmtP(W.gear.rigWear,1)+' · vehicle '+fmtP(W.gear.vehicle,0)+(W.gear.maintenanceDue?' · service due':' · nominal')]
  ];
  return'<div class="grid g2" style="gap:6px">'+lines.map(q=>'<div class="card" style="padding:7px"><div class="cap" style="font-size:8px">'+q[0]+'</div><div class="s" style="margin-top:3px;color:var(--txt2)">'+q[1]+'</div></div>').join('')+'</div>'+
    '<div class="row" style="margin-top:9px;gap:6px"><button class="btn sm" data-act="service">Service the rig</button><button class="btn sm" data-act="seedrumor">Start a rumour</button><span class="spacer"></span><span class="tiny dim">'+W.stats.hours+' quiet hours · '+fmtN(W.stats.npcActions)+' small choices</span></div>';
};
UI.worldPanelHTML=function(){
  const W=ensureWorld();if(!W)return'';
  const cal=W.calendar,cl=W.climate,e=W.economy,g=W.gear,H=W.honor,Ds=W.dossier;
  const cards=[
    ['City hour',W.stats.hours,'var(--cy)'],['NPC ActionS',fmtN(W.stats.npcActions),'var(--gr)'],
    ['Temp',fmtN(cl.temp,1)+'°C','var(--bl)'],['Visibility',fmtP(cl.visibility,0),'var(--am)'],
    ['Patrol AVG',fmtP(mean(W.district.map(x=>x.patrol)),0),'var(--rd)'],['Notes',fmtN(Ds.evidence,1),'var(--rd)'],
    ['Standing',fmtP(H.code,0),'var(--vi)'],['Rig wear',fmtP(g.rigWear,1),'var(--am)'],
    ['CPI',r3(e.cpi),'var(--cy)'],['Wage index',r3(e.wageIndex),'var(--bl)'],
    ['Rumour hops',fmtN(W.stats.rumorHops),'var(--vi)'],['Witness notes',fmtN(W.stats.witnessReports),'var(--rd)']
  ];
  const readout='<div class="grid g4" style="gap:6px">'+cards.map(q=>'<div class="card" style="padding:6px"><div class="cap" style="font-size:8px">'+q[0]+'</div><div class="num" style="font-size:12px;color:'+q[2]+';margin-top:3px">'+q[1]+'</div></div>').join('')+'</div>';
  const acc=[];
  /* NPC schedules */
  acc.push(['NPC daily routines ('+W.clients.length+' scheduled persons)',
    '<div class="scrollbox" style="max-height:210px"><table class="tbl zebra"><thead><tr><th>Contact</th><th>Routine 00→23</th><th>Now</th><th class="r">Energy</th><th class="r">Stress</th><th class="r">Susp.</th><th class="r">MEM</th></tr></thead><tbody>'+
    W.clients.slice(0,12).map(q=>{const c=S.clients.find(x=>x.id===q.id)||{name:'—'};
      return'<tr><td class="strong">'+esc(c.name.slice(0,14))+'</td><td>'+q.sch.map(v=>'<span style="display:inline-block;width:5px;height:9px;background:'+WROUTINE_COL[v]+';margin-right:1px" title="'+WROUTINE[v]+'"></span>').join('')+'</td>'+
      '<td>'+WROUTINE[q.sch[S.hour]]+'</td><td class="r">'+fmtP(q.energy,0)+'</td><td class="r">'+fmtP(q.stress,0)+'</td><td class="r">'+fmtP(q.suspicion,0)+'</td><td class="r">'+q.memory.length+'</td></tr>';}).join('')+
    '</tbody></table></div><div class="tiny dim" style="margin-top:5px">Legend: '+WROUTINE.map((r,i)=>'<span style="color:'+WROUTINE_COL[i]+'">■</span> '+r).join(' · ')+'</div>']);
  /* dossier */
  acc.push(['Witnesses & memory / witness chains',
    '<div class="grid g4" style="gap:6px;margin-bottom:7px">'+[['Notes',Ds.reports.length],['Threads',Ds.threads.length],['Memory',fmtN(Ds.evidence,1)],['Witnesses',Ds.witnesses]].map(q=>'<div class="card" style="padding:5px"><div class="cap" style="font-size:8px">'+q[0]+'</div><div class="num">'+q[1]+'</div></div>').join('')+'</div>'+
    '<div class="scrollbox" style="max-height:150px"><table class="tbl zebra"><thead><tr><th>Filed</th><th>District</th><th class="r">Strength</th><th class="r">TTL</th></tr></thead><tbody>'+
    (Ds.reports.length?Ds.reports.slice(0,14).map(r=>'<tr><td class="mono dim">'+fmtTick(r.t)+'</td><td>'+DISTRICTS[r.d].short+'</td><td class="r">'+r2(r.strength)+'</td><td class="r">'+r.ttl+'h</td></tr>').join(''):'<tr><td colspan="4" class="dim">No live reports.</td></tr>')+
    '</tbody></table></div>']);
  /* courier physiology */
  acc.push(['Tired hands & gear',
    '<table class="tbl zebra"><thead><tr><th>Crew</th><th class="r">Hydration</th><th class="r">Sleep DEBT</th><th class="r">Injury</th><th class="r">Stress</th><th class="r">Bond</th><th class="r">Gear</th></tr></thead><tbody>'+
    W.couriers.map(q=>{const c=S.couriers.find(x=>x.id===q.id)||{name:'—'};return'<tr><td class="strong">'+esc(c.name.slice(0,14))+'</td>'+
      [q.hydration,q.sleepDebt,q.injury,q.stress,q.bond,q.gear].map(v=>'<td class="r">'+fmtP(v,0)+'</td>').join('')+'</tr>';}).join('')+
    '</tbody></table><div class="statline" style="margin-top:6px"><span>Camp morale</span><b>'+fmtP(W.crew.campMorale,1)+'</b></div>'+
    barHTML(W.crew.campMorale,'g')+'<div class="statline"><span>Rig wear</span><b>'+fmtP(g.rigWear,2)+'</b></div>'+barHTML(g.rigWear,'a')+
    '<div class="statline"><span>Vehicle</span><b>'+fmtP(g.vehicle,1)+'</b></div>'+barHTML(g.vehicle,'b')+
    '<div class="statline"><span>Sealant / packaging</span><b>'+fmtP(g.sealant,1)+' / '+fmtP(g.packaging,1)+'</b></div>']);
  /* item condition */
  acc.push(['Condition of every parcel',
    '<div class="scrollbox" style="max-height:170px"><table class="tbl zebra"><thead><tr><th>LOT</th><th class="r">Integrity</th><th class="r">Moisture</th><th class="r">Exposure</th><th class="r">Seal</th><th class="r">Grade</th></tr></thead><tbody>'+
    (S.lots.length?S.lots.slice(0,10).map(l=>{const q=W.lots[l.id]||{integrity:1,moisture:0,exposure:0,seal:1};
      return'<tr><td class="mono strong">'+l.tag+'</td><td class="r">'+fmtP(q.integrity,1)+'</td><td class="r">'+fmtP(q.moisture,1)+'</td><td class="r">'+fmtP(q.exposure,1)+'</td><td class="r">'+fmtP(q.seal,1)+'</td><td class="r">'+fmtP(l.purity,1)+'</td></tr>';}).join(''):'<tr><td colspan="6" class="dim">Warehouse empty.</td></tr>')+
    '</tbody></table></div><div class="tiny dim" style="margin-top:5px">Depot parcels carry independent moisture/seal states; humidity and flooding degrade them hourly.</div>']);
  /* rumors + districts */
  acc.push(['Rumours & streets',
    '<table class="tbl zebra"><thead><tr><th>District</th><th>Rumour</th><th class="r">STR</th><th class="r">Patrol</th><th class="r">Footfall</th><th class="r">Light</th><th class="r">Flood</th><th class="r">Works</th><th class="r">Curfew</th></tr></thead><tbody>'+
    W.district.map((q,d)=>'<tr><td class="strong">'+DISTRICTS[d].short+'</td><td style="color:var(--vi)">'+W.rumors.nodes[d].topic+'</td>'+
      '<td class="r">'+fmtP(W.rumors.nodes[d].strength,0)+'</td><td class="r">'+fmtP(q.patrol,0)+'</td><td class="r">'+r2(q.footfall)+'</td>'+
      '<td class="r">'+fmtP(q.lighting,0)+'</td><td class="r">'+fmtP(q.flooding,0)+'</td><td class="r">'+q.construction+'h</td><td class="r">'+q.curfew+'h</td></tr>').join('')+
    '</tbody></table>']);
  /* economy + honor + climate */
  acc.push(['Money, weather & standing',
    '<div class="grid g2" style="gap:9px"><div>'+
    [['CPI',r3(e.cpi)],['Liquidity',r3(e.liquidity)],['Wage index',r3(e.wageIndex)],['Credit tightness',fmtP(e.credit,1)],['Wholesale lead',e.wholesaleLead+'h'],['Visibility',fmtP(cl.visibility,0)],['Transit factor',WEATHER[S.weather].speed.toFixed(2)+'×'],['Snow load',fmtP(cl.rain,0)],['Ground wetness',fmtP(cl.groundWet,0)],['Your sharpness',fmtP(youSharp(),0)]].map(q=>'<div class="statline"><span>'+q[0]+'</span><b>'+q[1]+'</b></div>').join('')+'</div><div>'+
    Standing.map(k=>'<div style="margin-bottom:4px"><div class="row tiny dim"><span>'+k+'</span><span class="spacer"></span><span class="num">'+fmtP(H[k],0)+'</span></div>'+barHTML(H[k],'v')+'</div>').join('')+
    '<div class="statline" style="margin-top:5px"><span>Composite code</span><b>'+fmtP(H.code,1)+'</b></div>'+barHTML(H.code,'g')+'</div></div>'+
    '<div class="divider"></div><div class="cap">Quiet effects ('+W.mods.length+')</div><div class="row wrap" style="gap:4px;margin-top:5px">'+
    W.mods.slice(0,18).map(m=>'<span class="tag '+(m.mag>1?'g':'r')+'">'+m.why+' ×'+r2(m.mag)+'</span>').join('')+'</div>']);
  /* crew affinity */
  acc.push(['Who works well together',
    '<div class="scrollbox" style="max-height:150px"><table class="tbl zebra"><thead><tr><th></th>'+S.couriers.map(c=>'<th>'+esc(c.name.split(' ')[0].slice(0,6))+'</th>').join('')+'</tr></thead><tbody>'+
    S.couriers.map((c,i)=>'<tr><td class="strong">'+esc(c.name.split(' ')[0].slice(0,8))+'</td>'+
      S.couriers.map((_,j)=>'<td class="r">'+fmtP(W.crew.affinity[i]&&W.crew.affinity[i][j]||0,0)+'</td>').join('')+'</tr>').join('')+
    '</tbody></table></div>']);
  const accordions=acc.map((q,i)=>'<div class="accordion" data-acc="w'+i+'"><button class="accordion-h" data-act="acc"><span class="caret">▸</span><span>'+q[0]+'</span></button><div class="accordion-b">'+q[1]+'</div></div>').join('');
  const wlogHTML=W.log.slice(0,12).map(l=>'<div class="feed-item"><span class="ft">'+fmtTick(l.t)+'</span><span class="tag '+(l.kind==='dossier'?'r':l.kind==='rumor'?'v':'c')+'">'+l.kind+'</span><span class="fx">'+esc(l.text)+'</span></div>').join('');
  return readout+'<div class="divider"></div>'+accordions+'<h4 style="margin-top:10px">The city’s quiet journal</h4><div style="max-height:190px;overflow:auto">'+wlogHTML+'</div>'+
    '<div class="notice" style="margin-top:9px">'+W.mods.length+' quiet effects shape trade each hour. You never need to read them; they only make the city feel like a place that carries on without you.</div>';
};
UI.worldLens=function(){
  const W=ensureWorld();if(!W)return;
  const raw=S.settings.density==='analyst'?'<h4>The deeper state</h4>'+UI.worldPanelHTML():'';
  UI.openModal({title:'Behind the ledger',sub:'The city · '+fmtTick(S.tick),wide:S.settings.density==='analyst',
    body:'<div class="notice c">Most of the city never reaches the interface. These are the signs it is giving off tonight. Press <span class="kbd">F2</span> for the deeper state.</div>'+
      '<h4 style="margin-top:12px">Tonight</h4>'+UI.worldSummary()+raw,
    hint:'F3 at any time · all of this is kept with your save.',
    footer:'<button class="btn" data-m="advance">Let a day pass</button><button class="btn" data-m="service">Service the rig</button><button class="btn primary" data-mclose>Close</button>',
    onMount:(m,close)=>{
      m.querySelector('[data-m="advance"]').addEventListener('click',()=>{close();NL.step(24);UI.render(true);UI.toast('A day passed','The city kept moving while you looked away.','good');});
      m.querySelector('[data-m="service"]').addEventListener('click',()=>{close();UI.act(A.serviceGear());});
    }});
};

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
      if(can('createLinearGradient')){sky=x.createLinearGradient(0,0,0,H);sky.addColorStop(0,'#b08a5a');sky.addColorStop(.55,'#1c2025');sky.addColorStop(1,'#121418');}
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


if(typeof document!=='undefined'&&document.getElementById('app')){
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',UI.init);
  else UI.init();
}

})();
