'use strict';
/* Read-only probe: prints the numbers FEATURES.md leans on and runs the defect checks it cites.
   Never writes state or files. Run: node _bench.js
   Each probe starts from a fresh seeded game, because step() halts on gameOver. */
const fs=require('fs'),vm=require('vm');
const src=fs.readFileSync('NIGHTLEDGER.html','utf8');
const js=src.slice(src.indexOf('<script>')+8,src.indexOf('</script>'));
const doc={getElementById:()=>null,querySelector:()=>null,querySelectorAll:()=>[],addEventListener:()=>{}};
const G={console,Math,JSON,Date,document:doc,setTimeout:()=>0,requestAnimationFrame:()=>0,addEventListener:()=>{},
  performance:{now:()=>Date.now()},localStorage:{getItem:()=>null,setItem:()=>{},removeItem:()=>{}}};
vm.runInNewContext(js,G,{filename:'nightledger.js'});
const NL=G.NL;
const fresh=seed=>{NL.newGame(seed,{settings:{autosave:false,autopause:false,sound:false}});return NL.getState();};
const run=(S,n)=>{NL.step(n);return S;};

/* 1. tick budget */
let S=fresh(12345);
run(S,200);
const t0=process.hrtime.bigint();
run(S,1000);
const msPerTick=Number(process.hrtime.bigint()-t0)/1e6/1000;

/* 2. how long does an idle player last? */
S=fresh(12345);
let hoursToRuin=null;
for(let h=1;h<=4000;h++){run(S,1);if(S.gameOver){hoursToRuin=h;break;}}
const ruined={hours:hoursToRuin,days:hoursToRuin&&+(hoursToRuin/24).toFixed(1),cause:S.gameOver||null,
  cash:Math.round(S.cash),debt:Math.round(S.debt),worth:Math.round(NL.netWorth(S))};

/* 3. offers: volume and who they come from */
S=fresh(12345);run(S,50);
let seen=0,own=0;
for(let h=0;h<600;h++){run(S,1);for(const o of S.offers){const c=S.clients.find(x=>x.id===o.client);if(!c)continue;seen++;if(o.cid===c.district)own++;}}
const offers={visibleHours:seen,shareInBuyersOwnDistrict:seen?+(own/seen).toFixed(2):null,trackedAfter600h:S.clients.length};

/* 4. bounded arrays + dead memory */
S=fresh(12345);run(S,400);
const memory={written:S.world.clients.some(q=>q.memory.length>0),dossierThreads:S.world.dossier.threads.length,
  worldLots:Object.keys(S.world.lots||{}).length,lots:S.lots.length};

/* 5. forecast */
S=fresh(12345);run(S,120);
const f1=S.forecast;const pathsAlways=f1&&f1.paths;
run(S,12);
const refreshed=JSON.stringify(S.forecast)===JSON.stringify(f1);
const auditRiskUses=/>S\.mods\.auditThreshold/.test(js)?'strict >':/>=\S*auditThreshold/.test(js)?'>=':'?';
const engineUses=/S\.heat>=S\.mods\.auditThreshold/.test(js)?'engine: >=':'engine: ?';
const uiRefreshRunsForecast=/case'forecast':NL\.computeForecast\(\)/.test(js);

/* 6. what a grade is worth at settlement */
const puritySlope=/sold\*L\.ask\*\(\.90\+\.10\*purity\)/.exec(js)?'gross = sold × ask × (0.90 + 0.10 × purity)':'?';
const gradeValue={at60:+(0.90+0.10*0.60).toFixed(3),at95:+(0.90+0.10*0.95).toFixed(3),
  _note:'a 35-point grade gap is worth this fraction of revenue'};

console.log(JSON.stringify({
  tick:{ms:+msPerTick.toFixed(3),hoursPer16msFrame:+(16.6/msPerTick).toFixed(1)},
  save:{jsonBytes:JSON.stringify(S).length},
  scale:{clients:S.clients.length,worldClients:S.world.clients.length,couriers:S.couriers.length,
    districts:NL.ND,products:NL.NP,mods:S.world.mods.length,historyCap:720,
    witnessReportsPerHourCap:5},
  idleRun:ruined,
  offers,
  memory,
  forecast:{pathsAlways,reranAfter12h:!refreshed,auditRiskUses,engineUses,uiRefreshRunsForecast},
  purity:{puritySlope,gradeValue}
},null,2));
