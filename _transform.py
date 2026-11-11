import re, colorsys, html

src=open('NIGHTLEDGER.html',encoding='utf-8').read()
style_start=src.index('<style>')
style_end=src.index('</style>')+len('</style>')
script_start=src.index('<script>')
script_end=src.index('</script>')
head=src[:style_start]
body=src[style_end:script_start]
js=src[script_start+len('<script>'):script_end]
tail=src[script_end:]

new_css=open('_style.css',encoding='utf-8').read()
new_body=open('_newbody.html',encoding='utf-8').read()
skin=open('_skin.js',encoding='utf-8').read()

# ---------- colour transform (hex + rgba literals in JS only) ----------
def transform_rgb(r,g,b):
    h,l,s=colorsys.rgb_to_hls(r/255,g/255,b/255)
    hd=h*360
    if l<.22:
        nh,ns,nl=35,.10,max(.035,l*.98)
    elif l>.70 and s<.26:
        nh,ns,nl=38,.07,min(.94,l*.97)
    elif l>.70 and s>.48 and 235<=hd<=325:
        nh,ns,nl=265,.22,.66
    elif s<.16:
        nh,ns,nl=35,.07,l
    elif 160<=hd<=200:
        nh,ns,nl=38,.46,min(.66,l*.90)
    elif hd<20 or hd>=335:
        nh,ns,nl=6,.44,min(.66,l*.88)
    elif 20<=hd<55:
        nh,ns,nl=32,.53,min(.68,l*.90)
    elif 55<=hd<160:
        nh,ns,nl=125,.20,min(.70,l*.92)
    elif 200<=hd<260:
        nh,ns,nl=210,.22,min(.68,l*.90)
    else:
        nh,ns,nl=265,.20,min(.68,l*.90)
    rr,gg,bb=colorsys.hls_to_rgb(nh/360,nl,ns)
    return tuple(int(round(v*255)) for v in (rr,gg,bb))

def hex_repl(m):
    h=m.group(1)
    r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    r,g,b=transform_rgb(r,g,b)
    return '#'+''.join(f'{v:02x}' for v in (r,g,b))

def rgba_repl(m):
    r,g,b=int(m.group(1)),int(m.group(2)),int(m.group(3))
    a=m.group(4)
    r,g,b=transform_rgb(r,g,b)
    return f'rgba({r},{g},{b},{a})'

if '/* PALETTE_NORMALIZED */' not in js:
    js=re.sub(r'#([0-9a-fA-F]{6})\b',hex_repl,js)
    js=re.sub(r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([^)]+)\)',rgba_repl,js)
    js='/* PALETTE_NORMALIZED */\n'+js
js=js.replace('ui-monospace,monospace','Segoe UI, sans-serif')

# ---------- copy replacements ----------
D=[
# head
('NIGHTLEDGER · Shadow Market Protocol','Nightledger — a quiet trade, after dark'),
# panel titles / headers
('CITY GRAPH // LIVE TELEMETRY','City map · current conditions'),
('MARKET PULSE // INDEX','Market at a glance'),
('EXPOSURE & SCRUTINY','Attention on you'),
('STRATEGIC MILESTONES','Milestones'),
('ENGINE TELEMETRY (ANALYST)','Behind the ledger · detail'),
('QUICK ACTIONS','A few things you can do'),
('PRICE SURFACE // DISTRICTS × COMMODITIES','Prices across the city'),
('SPREAD BETWEEN DISTRICTS','Price differences'),
('ORDER BOOK // ','Buyer requests · '),
('INBOUND BUYER REQUESTS','People asking to buy'),
('COMMODITY DOSSIER // ','Goods · '),
('24H PRICE BY DISTRICT','Prices today'),
('WAREHOUSE // LOT LEDGER','Warehouse & lots'),
('SYNDICATE RELATIONS','Other crews'),
('STANDING ORDERS','Standing orders'),
('CONTACT BOOK // ','Contacts · '),
('NET WORTH','What you are worth'),
('RECONCILIATION & ASSETS','Settling up'),
('PROFIT & LOSS BY COMMODITY','What each good earns'),
('TRANSACTION JOURNAL','Money in, money out'),
('CAMPAIGN OBJECTIVES','Where the story is going'),
('RESEARCH PROTOCOL TREE','Leads & contacts'),
('NEWS WIRE // ACTIVE MODIFIERS','Street talk'),
('ACTIVE MODIFIERS',"What is affecting trade"),
('BALANCE HISTORY // 180H','Balance · last 180 hours'),
('MONTE CARLO // 48H NET WORTH','Outlook · next 48 hours'),
('RELATIONSHIP GRAPH // TERRITORY','Territory & relationships'),
('LIVING CITY // QUALITATIVE SIGNALS','The city today'),
('ENGINE TELEMETRY // LIVE','Behind the ledger'),
('ALGORITHM CODEX // ','Field notes · '),
(' SUBSYSTEMS',' notes'),
('DEBUG CONSOLE','Scratchpad'),
('PERSISTENCE','Saved stories'),
('HIDDEN WORLD STATE // RAW TELEMETRY','The city under the surface'),
('SUBSYSTEM LOAD','What the city is doing'),
('SUPPLY CHAIN','Wholesale'),
('WHOLESALE PROCUREMENT','Buy wholesale'),
('CREW ROSTER','Your crew'),
('REFINING QUEUE','Workshop queue'),
('STRATEGIC MILESTONES','Milestones'),
('CAPITAL ASSETS','Equipment & premises'),
('TERRITORY INFLUENCE','Where you have a foothold'),
('ARBITRAGE SCAN','Price differences'),
('DISTRICT CONTRIBUTION','Where the money comes from'),
('HEAT×100','Attention ×100'),
('WTP EST','Likely budget'),
('OPT ','Suggested '),
('POST / UPDATE LISTING','Post or update a price'),
('SCHEDULE NEW RUN','Schedule a run'),
('REFINE · ','Workshop · '),
# modal titles / subtitles
('BEHIND THE HUD','Behind the ledger'),
('LIVING WORLD · ','The city · '),
('EXPORT STATE','Copy save file'),
('PORTABLE JSON SNAPSHOT','A copy of your story'),
('IMPORT STATE','Paste a save'),
('PASTE A PREVIOUS SNAPSHOT','Paste a save file'),
('FIELD MANUAL','Field notes'),
('HOW THE OPERATION WORKS','A quiet guide to the loop'),
('NEW OPERATION','Begin a new story'),
('INITIALISE WORLD STATE','Choose the city you want to meet'),
('OPERATION CLOSED','The story ends here'),
('FINAL LEDGER','The last page'),
('PAUSED','The evening is on hold'),
('SETTINGS','Options'),
('RUNTIME PREFERENCES','Make it yours'),
('OPERATION CONTROL','Paused'),
('CONFIRM ACTION','Before you go on'),
('DISTRICT DOSSIER · ','District notes · '),
('NEGOTIATION // ','A conversation with '),
(' · REQUEST #',' · Request #'),
('DISPATCH // ','Sending · '),
('LOGISTICS ORDER','Sending stock'),
# index chips
('01 / MAP','01 · map'),('02 / PRICE','02 · prices'),('03 / OPS','03 · ops'),('04 / RISK','04 · attention'),
('05 / GOALS','05 · goals'),('06 / DIAG','06 · notes'),('07 / CMD','07 · actions'),('08 / MATRIX','08 · prices'),
('09 / BOOK','09 · buyers'),('10 / OFFERS','10 · requests'),('11 / ASSET','11 · assets'),('12 / BUY','12 · wholesale'),
('13 / STOCK','13 · stock'),('14 / REFINE','14 · workshop'),('15 / CREW','15 · crew'),('16 / GRAPH','16 · network'),
('17 / DIPLOMACY','17 · crews'),('18 / CRM','18 · contacts'),('19 / FLOW','19 · money'),('20 / CAPITAL','20 · equipment'),
('21 / P&L','21 · earnings'),('22 / JOURNAL','22 · journal'),('23 / FORECAST','23 · outlook'),('24 / GOALS','24 · milestones'),
('25 / R&D','25 · leads'),('26 / WIRE','26 · street talk'),('27 / DIAG','27 · notes'),('28 / CODEX','28 · notes'),
('29 / CONSOLE','29 · scratchpad'),('30 / SAVE','30 · saves'),('31 / WORLD','31 · the city'),('32 / HIDDEN','32 · under the surface'),
# telemetry labels
('PRNG CURSOR','Story thread'),('STATE HASH','Story fingerprint'),('SOLVER ITER / H','Market steps / h'),
('AGENT UPDATES / H','People updated / h'),('EVENT QUEUE','Happenings queued'),('LAST TICK','Last hour'),
('DETERMINISTIC SEED','Story seed'),('SAVE EPOCH','Last saved'),('AUDITS PROCESSED','Inspections'),('FORECAST PATHS','Possible futures'),
('MARKET SOLVER','Market'),('AGENT SCHEDULER','People'),('EVENT BUS','Happenings'),('HEAT DIFFUSION','Attention spreading'),
('FINANCE LOOP','Money'),('FORECAST WORKER','Outlook'),('RENDER LAYER','Interface'),
('The engine is fully deterministic: identical seed + identical action sequence = identical world. Every subsystem runs on the same fixed hourly timestep; the renderer is read-only.',
 'The same seed and the same choices always lead to the same city. Everything moves one hour at a time; the interface only reports it.'),
('◆ ENGINE CONSOLE // ANALYST ONLY','Scratchpad · detail view'),
('type <span style="color:var(--cy)">help</span> for commands','type <span style="color:var(--cy)">help</span> for ideas'),
('COMMANDS: tick N | cash ±N | heat N | rep N | points N | event | forecast | dump | seed | pause | world | service | rumor | evidence | clear',
 'Try: tick, cash, heat, rep, points, event, forecast, dump, seed, pause, world, service, rumor, evidence, clear'),
('advanced \'+n+\' ticks → \'+fmtTick(S.tick)','moved \'+n+\' hours → \'+fmtTick(S.tick)'),
('deterministic seed ','story seed '),('unknown command: ','not sure about: '),("'ERROR '","'Could not: '"),
('WORLD \'+fmtTick(S.tick)','City \'+fmtTick(S.tick)+'),(' NPC actions',' small choices'),
('forecast E[worth]=','outlook, expected worth '),
# codex titles
('Deterministic PRNG','One story, one seed'),
('Latent demand (OU process)','Appetite drifts'),
('Price discovery','How prices settle'),
('Ask optimiser','Finding a good price'),
('Client utility & negotiation','What buyers will pay'),
('Agent state machines','People on schedules'),
('Logistics graph','Streets & travel'),
('Refining queue','The workshop'),
('Heat & scrutiny','Attention & consequences'),
('Finance loop','Money in, money out'),
('Monte Carlo forecast','Looking ahead'),
('Events & news','Happenings around town'),
('Save integrity','Why saves stay honest'),
('Living world: NPC routines','Private lives'),
('Living world: climate & calendar','Weather & the calendar'),
('Living world: witnesses & dossier','Witnesses & memory'),
('Living world: item condition','Condition & wear'),
('Living world: rumours & shadow economy','Rumours & money'),
('Living world: honour facets','What people think of you'),
('NPC routines & daily life','People & their days'),
('Investigative dossier','Witnesses & memory'),
('Crew affinity & camp morale','Your crew'),
('Courier physiology','Tired hands'),
('Item-level condition (lots & depot parcels)','Condition of every parcel'),
('Rumour diffusion & district ecology','Rumours & streets'),
('Shadow economy, climate & honour facets','Money, weather & standing'),
('Crew affinity matrix','Who works well together'),
('World event journal','The city’s quiet journal'),
('Active hidden modifiers (','Quiet effects ('),
('hidden modifiers feed the market solver each hour. None of this is required to play — it only makes the city behave like a place that exists when you are not looking.',
 'quiet effects shape trade each hour. You never need to read them; they only make the city feel like a place that carries on without you.'),
('All stochastic draws come from a single 32-bit <code>mulberry32</code> cursor stored in the save. Normal deviates use a cached Box–Muller pair; Poisson arrivals use Knuth’s product method. Forecasts use an isolated stream so modelling never perturbs the world.',
 'The same opening choice always grows into the same city. Chance is drawn from one saved thread, so a story can be replayed exactly. Looking ahead never changes what actually happens.'),
('<code>Dijkstra</code> over 14 bidirectional district edges','The shortest routes across fourteen two-way streets'),
('150 independent 48-hour paths','many possible tomorrows'),
('Percentiles P10/P50/P90 form the fan; the 5th percentile is reported as downside risk.',
 'The shaded fan shows the likely range; the lower edge is the cautious case.'),
('A rolling FNV-1a hash over PRNG cursor, balances and price matrix is shown as STATE HASH, so you can verify determinism across reloads.',
 'A short fingerprint of the saved hour lets you confirm that a replay really is the same story.'),
# objectives / protocol
('FULL PROTOCOL','The long game'),
('Unlock four research nodes and hold majority influence in the city.','Build four lasting contacts and hold sway across the city.'),
('PROTOCOL COMPLETE — every strategic objective achieved.','The long game is complete — every milestone reached.'),
('PROTOCOL COMPLETE. You may continue in free-play.','The campaign is complete. You can keep playing.'),
('Analysis points can unlock a new protocol node.','You have enough leads for a new contact.'),
# commands palette
('Go to Command Deck','Open the desk'),('Go to Market','Open the market'),('Go to Operations','Open operations'),
('Go to Network','Open the network'),('Go to Ledger','Open the ledger'),('Go to Intel','Open the outlook'),
('Go to Systems','Open the archive'),('Peek behind the HUD (living world)','Look behind the ledger'),
('Open hidden world telemetry','See the deeper state'),('Pause / resume simulation','Pause or resume the city'),
('Advance 8 hours (rest)','Rest eight hours'),('Advance 1 hour','Move one hour'),('Advance 24 hours','Let a day pass'),
('Toggle analyst density','Show more or less detail'),('Toggle focus mode','Widen the desk'),
('Run Monte Carlo forecast','Refresh the outlook'),('Open field manual','Open field notes'),
('Open settings','Open options'),('Save game','Save story'),('Open district dossier','Open district notes'),
('Return to title screen','Return to the title'),('Lay low for 12 hours','Lay low for twelve hours'),
('Reconcile all unsettled revenue','Settle everything waiting'),('Repay all debt','Clear the debt'),
("g:'VIEW'","g:'View'"),("g:'WORLD'","g:'City'"),("g:'SIM'","g:'Time'"),("g:'UI'","g:'Interface'"),
("g:'ACTION'","g:'Action'"),("g:'FILTER'","g:'Filter'"),("k:'SPACE'","k:'Space'"),
("k:'CTRL+S'","k:'Ctrl+S'"),("k:'SHIFT+.'","k:'Shift+.'"),("k:'ESC'","k:'Esc'"),
('No matching command.','Nothing matches.'),('Command error','That did not work'),
('150 simulated 48-hour paths recomputed.','A fresh 48-hour outlook is ready.'),
# toasts / HUD
('Interface density','Level of detail'),
('Analyst layer enabled: raw solver figures, advanced columns and the engine console are now visible.','More detail is visible: extra columns, field notes and a scratchpad.'),
('Clean layer enabled: only decision-relevant information is shown.','Back to the essentials.'),
('HUD minimized','Interface tucked away'),('Press F9 to restore the command deck.','Press F9 to bring it back.'),
('Focus mode','A wider desk'),('Full HUD','Everything back'),
('Sidebar hidden. Press F10 to restore.','The side column is tucked away. Press F10 to bring it back.'),
('Simulation paused','The city is paused'),('Simulation running','The city is moving'),
('The city is frozen. Press Space to resume.','Nothing moves until you are ready.'),
('City time is advancing at \'+S.speed+\'×.','Time is moving at \'+S.speed+\'×.'),
('Advanced \'+n+\' hours','Moved \'+n+\' hours'),('Stopped early: attention required.','Stopped early: something needs you.'),
('City state advanced.','The city moved on.'),
('command deck','The desk'),('market exchange','Market'),('operations / supply','Operations'),
('network / relations','Network'),('ledger / finance','Ledger'),('intelligence','Outlook'),('engine systems','Archive'),
('SEED \'+hashStr(String(S.seed)).toUpperCase()','Story \'+hashStr(String(S.seed)).slice(0,6).toUpperCase()'),
('CRITICAL','Too much notice'),('ELEVATED','Getting warm'),('WATCH','Worth watching'),('LOW','Quiet'),
('TIER ','Standing '),(' DISTRICTS HELD',' districts on side'),
('DAY CYCLE','Afternoon'),('NIGHT CYCLE','Evening'),('MORNING','Morning'),
('● SAVE FAILED','Save failed'),
# advisor priorities + copy
("pr:'CASHFLOW'","pr:'Money is tight'"),("pr:'CRITICAL · PRESSURE'","pr:'This needs you now'"),
("pr:'FINANCE'","pr:'Worth a look'"),("pr:'FORESIGHT'","pr:'Before you commit'"),
("pr:'LOGISTICS'","pr:'Stock could move'"),("pr:'OBLIGATION'","pr:'A promise is due'"),
("pr:'REVENUE'","pr:'Money sitting still'"),("pr:'STRATEGY'","pr:'A longer view'"),
("pr:'SUPPLY CHAIN'","pr:'Running low'"),("pr:'TIME SENSITIVE'","pr:'Before it lapses'"),
("pr:'WORLD · CALENDAR'","pr:'The calendar'"),("pr:'WORLD · EXPOSURE'","pr:'Attention on you'"),
("pr:'WORLD · RUMOUR'","pr:'Word on the street'"),("pr:'WORLD · UPKEEP'","pr:'Wear and tear'"),
('Offers expiring','Buyers waiting'),('Stock sitting idle','Stock sitting still'),('Feedstock running low','Wholesale stock low'),
('Refining will stall without wholesale inputs.','The workshop will stall without wholesale stock.'),
('Outstanding debt','Debt outstanding'),('Courier available','A courier is free'),('Research ready','A new lead is open'),
('Contract deadline near','An order is nearly due'),('Street rumour in play','A rumour is moving'),
('Run a forecast','Check the outlook'),('Model the next 48 hours before committing capital.','See the next two days before committing cash.'),
('No pressing priorities. The operation is stable.','Nothing urgent. The evening is steady.'),
('Request declined','Request declined'),('The buyer was released.','The buyer has gone.'),
('Choose a lot','Choose a lot'),('Click DISPATCH on any warehouse lot','Click Send on any warehouse lot'),
('(Advisor: post a listing)','(Try posting a price)'),
('Analysis points can unlock a new protocol node.','You have enough leads for a new contact.'),
# buttons / actions
('POST LISTING','Post a price'),('USE OPTIMUM','Use suggested price'),('QUEUE JOB','Queue a run'),
('DISPATCH ▸','Send ▸'),('DOSSIER ▸','Notes ▸'),('OPEN OPERATIONS ▸','Open operations ▸'),
('OPEN INTEL ▸','Open outlook ▸'),('ENGAGE 12H COOL-DOWN','Lay low for 12h'),('REST 8H','Rest 8h'),
('RUN FORECAST','Refresh outlook'),('RECONCILE','Settle'),('RESEARCH','Leads'),
('RE-RUN 150 PATHS','Refresh outlook'),('UNLOCK ','Learn '),('SAVE GAME','Save story'),
('LOAD SAVE','Saved stories'),('EXPORT JSON','Copy save file'),('IMPORT','Paste a save'),
('RESET ALL DATA','Erase everything'),('SERVICE RIG','Service the rig'),('SEED A RUMOUR','Start a rumour'),
('F3 · PEEK ▸','F3 · Look closer ▸'),('REST 10H','Rest 10h'),('TRAIN 14H','Train 14h'),
('+ RECRUIT COURIER · ','+ Hire a courier · '),('PARLEY ','Talk '),('CONTEST ','Push back '),
('RECONCILE NOW','Settle now'),('DISABLE AUTO','Turn off auto'),('ENABLE AUTO','Turn on auto'),
('REPAY DEBT','Repay debt'),('NO STOCK','No stock'),('DEAL','Deal'),('BUY','Buy'),('CLEAR','Clear'),
('ENGAGE COOL-DOWN','Lay low'),('NO FORECAST','No outlook yet'),
('150 paths · ','Outlook · '),(' expected net worth.',' expected worth.'),
('Forecast refreshed','Outlook refreshed'),('Action complete','Done'),('Action blocked','Not possible'),
('Deal lost','The buyer walked away'),
('Start a new operation?','Begin a new story?'),
('Current progress will be overwritten. Export a snapshot first if you want to keep it.','The current hour will be replaced. Save it to a manual slot first if you want to come back.'),
('Erase all local data?','Erase everything on this machine?'),
('This removes the save, settings and every deterministic state snapshot.','This removes the rolling save, every manual slot and your preferences.'),
('ERASE ALL','Erase everything'),('Local data erased','Local stories erased'),('Returning to title.','Back to the title screen.'),
('Load saved operation?','Return to a saved story?'),('Current unsaved progress will be replaced.','The current hour will be replaced.'),
("'LOAD'","'Continue'"),
# manual / tutorial / modals
('01 · CLOCK & CONTROLS','01 · The clock'),
('This is your live status strip: in-game time, cash, net worth, heat and reputation. Use the speed buttons or Space to pause. Nothing moves while paused.',
 'Time, cash, worth, attention and standing live here. Use the speed buttons or Space to pause. Nothing moves until you are ready.'),
('02 · VIEW RAIL','02 · The views'),
('Seven views, never more than one click away. Each view starts clean; press F2 when you want the raw numbers behind it.',
 'Seven places, never more than one click away. Each starts with the essentials; press F2 when you want the deeper numbers.'),
('03 · CITY GRAPH','03 · The city map'),
('Seven districts. Ring = your influence, core colour = scrutiny, radius = demand. Click any node for its full dossier.',
 'Seven districts. The ring is your influence, the core is local attention, and the size is appetite. Click any one for its notes.'),
('04 · ADVISOR','04 · What matters now'),
('Three ranked next actions, recomputed from the live simulation. Click one to jump straight to the relevant control.',
 'Three suggested next steps, reconsidered as the city changes. Click one to go straight there.'),
('05 · ACTIVITY WIRE','05 · Street talk'),
('Every sale, delivery, audit and market event is logged here and in the ledger. You are ready — start with Operations.',
 'Sales, deliveries, inspections and happenings collect here. You are ready — start with Operations.'),
('Press Ctrl+K any time to search every action.','Press Ctrl+K any time to find anything.'),
('01 · READ THE DECK','01 · Read the room'),('02 · PROCURE & REFINE','02 · Buy & prepare'),
('03 · LIST & DEAL','03 · Choose a price'),('04 · MANAGE HEAT','04 · Mind the attention'),
('05 · SETTLE & GROW','05 · Settle & grow'),('06 · CONTROL THE LOOP','06 · Keep your rhythm'),
('How the operation works','A quiet guide to the loop'),
('Monte Carlo','Outlook'),('AP','Leads'),('Saturation','Buyer fatigue'),('Purity','Grade'),
('Reconciliation','Settling up'),('Influence','Influence'),('Heat','Attention'),
('Latent demand','Hidden appetite'),('150 simulated futures used to estimate net-worth bands and audit risk.','Many quiet trial runs used to sketch a range of tomorrows.'),
('The living world (mostly hidden)','The city, mostly unseen'),
('The city runs when you are not looking','Most of the city never reaches the HUD'),
('Every contact keeps a 24-hour routine, energy, stress and a decaying memory. Climate, patrol shifts, paydays, roadworks, curfews, rumours, witness reports, gear wear, per-parcel condition and a shadow economy all advance each hour and quietly bend prices, offers, scrutiny and yield. The clean HUD shows only a one-line "city state" ticker; <span class="kbd">F3</span> peeks behind it and <span class="kbd">F2</span> exposes the raw state in Systems → Hidden World State.',
 'Every contact keeps a daily routine, energy and memory. Weather, patrol shifts, paydays, roadworks, rumours, witness reports and worn equipment all move each hour and quietly bend prices, requests, attention and yield. The clean interface shows only a one-line note; <span class="kbd">F3</span> looks closer and <span class="kbd">F2</span> opens the deeper state.'),
('This is a work of fiction. All commodities, compounds, organisations and procedures are invented game abstractions — no real-world chemistry, sourcing or logistics is depicted.',
 'This is a work of fiction. All goods, places and crews are invented game abstractions — nothing here describes a real-world procedure.'),
('Tip: the advisor on the right always lists the three highest-value next actions.','Tip: the side column always lists the three most useful next steps.'),
('START GUIDED TOUR','Guided tour'),('GOT IT','Got it'),
('INITIALISE','Begin'),('Operation initialised','A new story begins'),
('A fresh seed regenerates districts, clients, couriers and the entire event stream. Deterministic: the same seed always produces the same city.',
 'A fresh seed grows fresh districts, people, crews and happenings. The same seed always produces the same city.'),
(' KB · copy this text to back up your operation.',' KB · copy this text to keep your story elsewhere.'),
('DOWNLOAD .JSON','Download file'),('DONE','Done'),('LOAD SNAPSHOT','Load story'),
('Importing replaces the current operation. Save first if you want to keep it.','Pasting replaces the current hour. Save it to a manual slot first if you want to come back.'),
('Snapshot loaded','Story restored'),('Operation restored from imported state.','Restored from the pasted save.'),
('Import failed','Could not read that save'),('Export ready','Copy ready'),('Snapshot downloaded.','File downloaded.'),
('State written to local storage at \'+fmtTick(S.tick)+\'.','Saved at \'+fmtTick(S.tick)+\'.'),
('Game saved','Story saved'),('No save found','No saved story'),('Start a new operation first.','Begin a story first.'),
('Operation restored','Story restored'),('Loaded \'+fmtTick(S.tick)+\' · seed \'+hashStr(String(S.seed)).toUpperCase()+\'.','Picked up at \'+fmtTick(S.tick)+\' · story \'+hashStr(String(S.seed)).slice(0,6).toUpperCase()+\'.'),
('Load failed','Could not load'),('Defaults saved','Options saved'),('Applied to the next operation.','Used for the next story.'),
('Settings applied','Options saved'),('Preferences saved.','Kept on this machine.'),
('Simulation speed','City speed'),('Settings are stored with your save.','Options are kept with your story.'),
('Reveal raw solver numbers, hidden estimates and the engine console.','Reveal extra columns, quiet estimates and a scratchpad.'),
('Synthesised UI blips and alerts (WebAudio).','Small interface cues, generated on this machine.'),
('Halt the simulation when an audit or major market shock occurs.','Stop when an inspection or a big shift needs a decision.'),
('Write state to local storage at each in-game day boundary.','Keep a rolling save at every in-game daybreak.'),
('Draw live transit vectors on the city graph.','Show stock moving across the city map.'),
('Analyst density','Detail level'),('Sound effects','Sound effects'),('Auto-pause on shocks','Pause on surprises'),
('Autosave every 24h','Autosave each day'),('Show courier routes','Draw courier routes'),
('RUNTIME PREFERENCES','Make it yours'),('DISPATCH // ','Sending · '),
('Paused','On hold'),('The world is frozen. Resume, save, or return to the title screen.','The city is frozen. Resume, save, or step away for a while.'),
('MANUAL','Field notes'),('TITLE','Title'),('RESUME ▸','Resume ▸'),('REVIEW WORLD','Look around'),
(' · the ledger is closed.',' · this run is finished.'),('Final net worth','Final worth'),
('Hours survived','Hours played'),('Units moved','Units moved'),('Audits','Inspections'),
('NEW OPERATION','Begin a new story'),('CANCEL','Cancel'),('CLOSE','Close'),
# world lens / summary / hidden
('BEHIND THE HUD','Behind the ledger'),('LIVING WORLD · ','The city · '),
('Most of the simulation never reaches the interface. These are the qualitative signals the city is currently emitting. Press <span class="kbd">F2</span> for the raw state.',
 'Most of the city never reaches the interface. These are the signs it is giving off tonight. Press <span class="kbd">F2</span> for the deeper state.'),
('Current conditions','Tonight'),('Raw telemetry','The deeper state'),
('F3 at any time · hidden systems persist in your save and are covered by the state hash.','F3 at any time · all of this is kept with your save.'),
('ADVANCE 24H','Let a day pass'),('SERVICE RIG','Service the rig'),
('World advanced','A day passed'),('24 hidden hours simulated across every subsystem.','The city kept moving while you looked away.'),
('CITY STATE','Tonight'),('Living city','The city today'),
('A qualitative readout of hidden systems: calendar, climate, patrol shifts, rumour diffusion, witness dossiers and reputation facets. Press F3 to peek behind the HUD, F2 for raw state.',
 'A few signs from the private life of the city. Press F3 for a closer look, F2 for the deeper state.'),
('PATROL ','Patrol '),('PAYDAY','Payday'),('ROUTINE DAY','An ordinary day'),('RUMOR · ','Rumour · '),
('STREET QUIET','The street is quiet'),('STANDING · ','Standing · '),(' REPORTS · ',' witness notes · '),
(' HIDDEN MODIFIERS',' quiet effects'),('F3 · PEEK ▸','F3 · Look closer ▸'),
('hidden hours simulated · ','quiet hours · '),(' NPC actions',' small choices'),
('SERVICE RIG','Service the rig'),('SEED A RUMOUR','Start a rumour'),
('HIDDEN WORLD STATE // RAW TELEMETRY','The city under the surface'),
('World event journal','The city’s quiet journal'),
('NPC actions','small choices'),('HIDDEN MODIFIERS','quiet effects'),
('Dossier pressure','Witness pressure'),('RIG WEAR','Rig wear'),('WAGE INDEX','Wage index'),
('RUMOUR HOPS','Rumour hops'),('WITNESS REPORTS','Witness notes'),('HONOR CODE','Standing'),
('PATROL AVG','Patrol average'),
# misc
('AUDIT · ','Inspection · '),('NEW SUPPLIER','New supplier'),('POLICE SHIFT','Patrol change'),
('QUALITY DROP','Quality drop'),('CIVIC HOLIDAY','Local holiday'),('MID-MONTH FAIR','Mid-month fair'),
('FOUNDERS DAY',"Founders day"),(' · SERVICE DUE',' · service due'),
('PRICE HIKE','Price rise'),('SHORTAGE','Shortage'),('CRACKDOWN','Crackdown'),
('ACTIVE','Active'),('AVAILABLE','Available'),('ASLEEP','Asleep'),('IDLE','Idle'),
('OUTBOUND','Outbound'),('IN TRANSIT','On the move'),('RETURN','Returning'),('RESTING','Resting'),
('TRAINING','Training'),('RETURNING','Returning'),('NOW','Now'),('STATIC','Still'),
('VERY LIKELY','Very likely'),('UNLIKELY','Unlikely'),('LIKELY','Likely'),('EVEN','Even'),
('CANCEL','Cancel'),('CONFIRM','Confirm'),('MAX','Full'),('LOCKED','Locked'),('UNLOCKED','Learned'),
('SELECT','Choose'),('RELEASE','Release'),('TRUCE ','Truce '),('REPORTS','Notes'),('CHAINS','Threads'),
('EVIDENCE','Memory'),('WITNESSES','Witnesses'),('WORLD HOUR','City hour'),('TICK','Hour'),
('CANVAS','Charts'),('SYSTEM','City'),('RISK','Risk'),('VOLUME','Volume'),('TEMP','Temp'),
('WEATHER','Weather'),('TERR','Territory'),('BAL','Balance'),('MARK','Mark'),
('NO SAVE','No saved story'),('EVERY 24H','Each day'),('OFF','Off'),('ON','On'),
('INPUT','Input'),('TEXTAREA','Textarea'),('GLOBAL','All districts'),('DOSSIER','Notes'),
('ASSET','Asset'),('CONTRACT','Order'),('CREW','Crew'),('SYNDICATE','Crew'),('SCRUTINY','Attention'),
('VISIBILITY','Visibility'),('REPORTS','Notes'),('WORK','Work'),('HOME','Home'),('SLEEP','Sleep'),
('SOCIAL','Social'),('ERRAND','Errand'),('NIGHT','Night'),('REST','Rest'),('TRAIN','Train'),
('INSOLVENT','Closed'),('RISKY','Risky'),('IRREGULAR','Irregular'),('REGULAR','Regular'),
('COOPERATIVE','Cooperative'),('HOSTILE','Hostile'),('NEUTRAL','Neutral'),('WARY','Wary'),
('DISCREET','Discreet'),('HAGGLER','Haggler'),('LOYAL','Loyal'),('CAUTIOUS','Cautious'),
('IMPULSIVE','Impulsive'),('TRUSTED','Trusted'),('RESPECTED','Respected'),('MIXED','Mixed'),
('NOTORIOUS','Notorious'),('QUIET','Quiet'),('HALO','Halo'),('KITE','Kite'),('LAB','Lab'),
('DOCKS','Docks'),('DOCKLANDS','Docklands'),('SPINE','Spine'),('LANTERN','Lantern'),
('MERIDIAN','Meridian'),('VESPER','Vesper'),('LOWLIGHT','Lowlight'),('HOLLOW','Hollow'),
('MIRROR','Mirror'),('VANTAGE','Vantage'),('GRID N','Grid north'),
]
for a,b in D:
    js=js.replace(a,b)

# ---------- title-case plain uppercase HTML text inside string literals ----------
exceptions={'NPC','PRNG','JSON','P10','P50','P90','WTP','ETA','HQ','AP','CPI','RNG','AR','OU','CTRL','SHIFT','ESC','SPACE','F1','F2','F3','F9','F10','CDR','VLM','LMN','HLO','ONX','KTE','MRR','STC','SOC','BAL','TERR','TEMP','MARK','SYS','OK','ID','AP'}
def tc_word(w):
    if len(w)<=3 or any(ch.isdigit() for ch in w) or w in exceptions:return w
    if not re.fullmatch(r'[A-Z][A-Z0-9×·\-/]*',w):return w
    return w[0]+w[1:].lower()
def tc_text(t):
    if any(c.islower() for c in t):return t
    if any(x in t for x in ['${','+','//','&','\\','"',"'",'`','var(','data-','=','<','>']):return t
    return re.sub(r'[A-Z][A-Z0-9×·\-/]*',lambda m:tc_word(m.group(0)),t)
def tc_literal(m):
    q=m.group(0)
    if q.startswith('`') and '${' in q:return q
    quote=q[0]
    inner=q[1:-1]
    if quote=='`' and '${' in inner:return q
    inner2=re.sub(r'>([^<>]+)<',lambda mm:'>'+tc_text(mm.group(1))+'<',inner)
    return quote+inner2+quote
js=re.sub(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|`(?:[^`\\]|\\.)*`",tc_literal,js,flags=re.S)

# ---------- canonicalise code identifiers, then naturalise copy ----------
# The broad copy map also mangled a handful of identifiers. Fix those globally
# first. All later replacements are either multi-word phrases or quoted tokens,
# so they cannot touch bare variable names such as WEATHER or RESEARCH.
code_fixes={
 # 1) identifiers mangled by the broad copy map
 'JSOn':'JSON','Weather':'WEATHER','Leads':'RESEARCH','EvenT_DEFS':'EVENT_DEFS','WHOnOR':'WHONOR',
 'MarkET_SCALE':'MARKET_SCALE','QuietLIGHT':'LOWLIGHT','OnYX':'ONYX','OnX':'ONX','MOn':'MON',
 'MOnTE':'MONTE','COnTRACT':'CONTRACT','COnTACT':'CONTACT','COnTAINED':'CONTAINED',
 'BuyER':'BUYER','OffER':'OFFER','LoyalTY':'LOYALTY','DealS':'DEALS','REvenUE':'REVENUE',
 'BalanceANCE':'BALANCE','WorkS':'WORKS','RiskY':'RISKY','ACTIOn':'ACTION','ACTIOnS':'ACTIONS',
 'BOnD':'BOND','HYDRATIOn':'HYDRATION','DISCRETIOn':'DISCRETION','OPERATIOnS':'OPERATIONS',
 'OnE':'ONE','ReturningING':'RETURNING','UNLocked':'UNLOCKED','CASHFQuiet':'CASHFLOW',
 'GLOBalance':'GLOBAL','HOLQuiet':'HOLLOW','LeadsPLY':'APPLY','BOOTSTRLeads':'BOOTSTRAP',
 'SNLeadsSHOT':'SNAPSHOT','CityS':'SYSTEMS','NightLEDGER':'NIGHTLEDGER',
 'Input':'INPUT','Choose':'SELECT','Textarea':'TEXTAREA',
 # 2) repair engine diagnostics schema and statusbar IDs
 'const market scale=14;':'const MARKET_SCALE=14;','market scale':'MARKET_SCALE',
 'marketIter:0':'solverIter:0','personUpdates:0':'agentUpdates:0','variation:0':'entropy:0',
 'S.diag.marketIter':'S.diag.solverIter','S.diag.personUpdates':'S.diag.agentUpdates',
 'S.diag.variation':'S.diag.entropy',
 'd.marketIter':'d.solverIter','d.personUpdates':'d.agentUpdates','d.variation':'d.entropy',
 "el('st-market')":"el('st-solver')","el('st-persons')":"el('st-agents')",
 "el('st-variation')":"el('st-entropy')",
 # 3) naturalise specific quoted phrases (kept last so nothing reverts them)
 "'Persons '":"'People '","'ENTROPY (norm)'":"'Variation (norm)'",
 "'WEATHER forced by climate model: '":"'Weather shifted by the climate model: '",
 "'WEATHER shifted by the climate model: '":"'Weather shifted by the climate model: '",

 "'Too much notice · PRESSURE'":"'Too much notice · needs attention'",
 "'03 · LIST & Deal'":"'03 · Choose a price'",
 "' MOD'":"' quiet effects'","'● SAVED '":"'Saved '","' RESEARCH'":"' Leads'",
 "'CITY'":"'City'", '"CITY"':'"City"',"'DAY '":"'Day '",
 "'FESTIVAL'":"'Festival'", "'REFERRAL'":"'Referral'",
 "'INTEL'":"'Intel'", "'SUPPLY'":"'Supply'", "'AUDIT'":"'Inspection'",
 "'CASH'":"'Cash'", "'FINISH'":"'Finish'", "'NEXT ▸'":"'Next ▸'",
 "'A · DAWN'":"'A · Dawn'","'B · DAY'":"'B · Day'",
 "'FIRST DROP'":"'First drop'", "'CLEAN TWELVE'":"'Clean twelve'",
 "'GRADE A'":"'Grade A'", "'THREE FLAGS'":"'Three flags'",
 "'Quiet WEEK'":"'Quiet week'", "'INNER CIRCLE'":"'Inner circle'",
 "'FORTY GRAND'":"'Forty grand'", "'Mirror & CO'":"'Mirror & Co'",
 "'SOC'":"'Social'", "' RESEARCH'":"' Leads'",
 "'Operation scrutinised'":"'An inspection'",
 "'Operation insolvent. The ledger is closed.'":"'The outfit is insolvent. The ledger is closed.'",
 "' left the operation.'":"' left the outfit.'",
 "'Audit triggered'":"'An inspection needs your attention'",
 "'Closed'":"'The ledger closed'",
 "'Auto-pause'":"'Stopped for you'",
 "' — simulation halted for your decision.'":"' — the city is waiting on your decision.'",
}


for a,b in code_fixes.items(): js=js.replace(a,b)

copy_fixes={
 # specific phrases
 "'MONTE CARLO // 48H What you are worth'":"'Outlook · next 48 hours'",
 "'BEHIND THE HUD'":"'Behind the ledger'",
 "'Behind the HUD'":"'Behind the ledger'",
 "'Look behind the HUD'":"'Look behind the ledger'",
 "'Peek behind the HUD'":"'Look behind the ledger'",
 "'Most of the city never reaches the HUD'":"'Most of the city never reaches the ledger'",
 "'Quiet decisions made behind the HUD'":"'Quiet decisions made behind the ledger'",
 "'WEATHER factor'":"'Weather factor'",
 "'WEATHER & the calendar'":"'Weather & the calendar'",
 "'RESEARCH & contacts'":"'Leads & contacts'",
 "'RESEARCH → '":"'Leads → '",
 "'Grid northORTH'":"'Grid North'",
 "'Grid north'":"'Grid North'",
 "'Lantern ROW'":"'Lantern Row'",
 "'Vesper HILL'":"'Vesper Hill'",
 "'Meridian QUAY'":"'Meridian Quay'",
 "'THE SPINE'":"'The Spine'",
 "'THE Spine'":"'The Spine'",
 "'DOCKLANDS'":"'Docklands'",
 "'HALO'":"'Halo'", "'KITE'":"'Kite'", "'MIRROR'":"'Mirror'", "'VANTAGE'":"'Vantage'",
 "'STATIC'":"'Still'",
 # plain natural-language substitutions (safe: not bare identifiers)
 'MONTE CARLO':'Outlook', 'HUD':'ledger',
 # quoted canonical tokens -> natural words
 "'WEATHER'":"'Weather'", '"WEATHER"':'"Weather"',
 "'RESEARCH'":"'Leads'", '"RESEARCH"':'"Leads"',
 "'EVENT_DEFS'":"'Happenings'", "'WHONOR'":"'Standing'",
 "'MARKET_SCALE'":"'market scale'",
 "'LOWLIGHT'":"'Lowlight'", '"LOWLIGHT"':'"Lowlight"',
 "'ONYX'":"'Onyx'", "'ONX'":"'ONX'",
 "'CONTRACT'":"'Order'", "'CONTACT'":"'Contact'", "'CONTAINED'":"'Contained'",
 "'BUYER'":"'Buyer'", "'OFFER'":"'Offer'", "'LOYALTY'":"'Loyalty'",
 "'DEALS'":"'Deals'", "'REVENUE'":"'Revenue'", "'BALANCE'":"'Balance'",
 "'WORKS'":"'Works'", "'RISKY'":"'Risky'", "'ACTION'":"'Action'", "'ACTIONS'":"'Actions'",
 "'BOND'":"'Bond'", "'HYDRATION'":"'Hydration'", "'DISCRETION'":"'Discretion'",
 "'OPERATIONS'":"'Operations'", "'ONE'":"'One'", "'RETURNING'":"'Returning'",
 "'UNLOCKED'":"'Unlocked'", "'CASHFLOW'":"'Cashflow'", "'GLOBAL'":"'All districts'",
 "'HOLLOW'":"'Hollow'", "'APPLY'":"'Apply'", "'BOOTSTRAP'":"'Bootstrap'",
 "'SNAPSHOT'":"'Snapshot'", "'NIGHTLEDGER'":"'Nightledger'", "'SYSTEMS'":"'Archive'",
 "'SELECT'":"'Choose'",
 "'MON'":"'Mon'", "'TUE'":"'Tue'", "'WED'":"'Wed'", "'THU'":"'Thu'",
 "'FRI'":"'Fri'", "'SAT'":"'Sat'", "'SUN'":"'Sun'",
 "'CLEAR'":"'Clear'", "'OVERCAST'":"'Overcast'", "'RAIN'":"'Rain'",
 "'FOG'":"'Fog'", "'STORM'":"'Storm'",
 "'HUD'":"'ledger'", "'JSON'":"'JSON'",
}
for a,b in copy_fixes.items(): js=js.replace(a,b)
# The SELECT mapping above also touched tag-name comparisons; put those back.
js=js.replace("ae.tagName==='Choose'","ae.tagName==='SELECT'")
js=js.replace("tag==='Choose'","tag==='SELECT'")
js=js.replace("tag === 'Choose'","tag === 'SELECT'")

# ---------- append presentation layer before start marker ----------
# Remove any pre-existing presentation-layer copy (idempotent).
skin_marker='/* =====================================================================================\n   Presentation layer — cinematic shell, layered sheets and interaction polish.\n   Adds no simulation state and touches no engine hooks.\n   ===================================================================================== */'
while skin_marker in js:
    a=js.index(skin_marker); b=js.index('})();',a)+len('})();')
    js=js[:a]+js[b:]
js=js.replace('/* Presentation layer is appended after the engine start hook below. */\n\n','')
# Insert one copy after the engine's start hook, before its IIFE closes.
engine_start="""if(typeof document!=='undefined'&&document.getElementById('app')){
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',UI.init);
  else UI.init();
}"""
js=js.rstrip()+'\n\n'+skin+'\n\n'+engine_start+'\n\n})();\n'

# ---------- assemble ----------
head=head.replace('<title>NIGHTLEDGER · Shadow Market Protocol</title>','<title>Nightledger — a quiet trade, after dark</title>')
out=head+'<style>\n'+new_css+'</style>\n'+new_body+'<script>\n'+js+'</script>'+tail[tail.index('</script>')+len('</script>'):]
open('NIGHTLEDGER.html','w',encoding='utf-8').write(out)
print('written',len(out),'chars')
