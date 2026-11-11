# Nightledger → Red Dead–grade backend: 40 features, judged by decisions

**The question this document answers is not "what does RDR2 have".** It is: *why would a
dashboard simulator need <feature X>?* Every feature below has to survive that question.

**What the audit found.** A read of the engine's own wiring (not its feature list):

| Measure | Value |
|---|---|
| Player verbs in `A.*` that contain a roll (`rnd`, `chance`, `offerOdds`, `power>`) | **3 of 21** (`acceptOffer`, `diplomacy`, `fireEvent`) |
| Player verbs that are pure arithmetic (buy, queue, set a number) | **18** |
| Distinct decision axes in the core loop | **1** — pick ask + qty, roll one sigmoid (`offerOdds`) |
| Tracked variables with **no** decision consumer (displayed only) | **9** — `cl.wind`, `cl.pressure`, `cal.moon`, `wd.chatter`, `wd.transit`, `crew.sharedShifts`, `crew.campMorale`, `e.blackMarketVolume`, plus `cal.week` |
| Bytes: engine (state + rules) vs UI (paint) | **57 KB vs 229 KB** |

Read that third row again. The city has weather, patrol shifts, rumors, witnesses, moisture,
gear wear and seven districts — and *all of it* funnels into one number per offer, compared
against one threshold. Weather variation is not needed because weather is *readable*; it is
needed **only if it changes what you do next**. Today it does not: it changes the same sigmoid
you already tune by matching the market price.

**The rule this revision enforces.** Before a feature is allowed in, it must pass four gates:

1. **It changes a decision you make** — a different action becomes correct, or the same action
   becomes correct at a different time, price, or place.
2. **It creates a real fork** — a genuine chance node or an irreversible commitment, not a
   new number to look at.
3. **It costs something you had** — hours you could have traded, access you could have kept,
   a relationship you could have spent. No free instrumentation.
4. **Its absence would make your choices worse** — if the player would choose identically with
   it deleted, it is decoration and it is rejected.

Anything that only *describes* the world fails gate 1. That is why weather, moon phase, camp
morale and the affinity matrix do not get features here; they are on the demolition list in
Part 0 instead. RDR2 "feels real" because its systems also fail gates 1–4 — they are
atmosphere. Atmosphere is what you add *after* a decision layer exists, never instead of it.

**Scope.** A design brief, not code. Every claim about the current engine is checkable
against `_extracted.js` (the JS block of `NIGHTLEDGER.html`) and `node _bench.js`.

---

## Status: what is actually in the engine now

This is no longer only a brief. The first stage was implemented and is verified by
`node _test_new.js` (25 tests) and `node _bench.js`. Shipped in `_extracted.js`:

| Done | Evidence in the engine |
|---|---|
| Grade is monetised (row 1) | `gradeValue(p,purity)` drives direct deals and listings; measured **+22.8%** revenue for .95 vs .52 grade at the same ask |
| Deal memory (row 3) | `c.mem` (max 8), `remember()`, `memScore()`; an offer's price and TTL bend with it |
| Named buyers for every tier (row 4) | `weightedPref()` replaces `pref:ri(0,4)`; measured offers reaching **all 8 products** |
| Counter-offer as a position (row 5) | `mode` accepts `'counter'` and `'split'`; sharpness scales the roll. A third mode (`'grade'`) was built, measured identical to accepting, and deleted — gate 1 applies to my own work |
| The operator has a body (rows 15–16) | `S.you` + `youSharp()`; `sleep`/`eat` verbs; ten trading verbs refuse while `downtime>0` |
| Population replaced by attribution (row 12, hole 3) | churn now introduces a contact *through* the one who left |
| Holes 5 and 6 repaired | forecast sees `dossier.evidence` and uses `>=` on the audit threshold; threads capped at 24; `W.lots` no longer leaks |
| Ornament state deleted (demolition list) | `wind`, `pressure`, `seaBreeze`, `moon`, `week`, `chatter`, `transit`, `sharedShifts`, `campMorale`, `blackMarketVolume` are gone from state; a test fails if they return |
| Build can no longer drift | `_build.js` regenerates the HTML from `_extracted.js`; `node _build.js --check` runs inside the test suite |

Measured as a fork, not just shipped: holding a full order vs splitting it on the same stock gives
**80,785 / 122 deals** versus **36,868 / 112 deals** over 300 hours — the split costs real money and
buys real exposure, which is what a decision is supposed to do.

Not done yet: law (#21–25), knowledge gating (#9), routes (#26–29), money layers (#30–32),
supply damage (#33–35), the nightly page (#36). Each stays in Part 2 with its gate intact.

---

## Part 0 · Where the simulation actually stands

Honest inventory first, because 40 additions on top of a broken base is 40× the breakage.

**Already at a good standard** — do not rebuild these:

| Area | State | Where |
|---|---|---|
| Climate | Ornstein–Uhlenbeck temperature, pressure, humidity, wind, rain → wet ground, visibility, heat index; climate *overrides* the visible weather enum with hysteresis | `worldTick` §2 |
| Rumor diffusion | One hop per simulated hour over the district graph, 3-hour edge rotation, strength decay, seeded from the news wire, converted into demand/price/supply modifiers | §10, `WRUMORS` |
| Investigation | Witness reports mature into evidence threads after a strength threshold; evidence raises audit severity and heat; audits collapse evidence | `worldPostTick`, `runAudit` |
| NPC schedules | 24-slot routine per client, shifted by district and night-owl trait; sleeping clients can't be reached; energy/stress/suspicion feed back into mood and loyalty | §5 |
| Physical stock | Per-lot moisture/exposure/integrity/seal; depot parcels degrade with humidity and flooding; degradation lowers purity | §12 |
| Economy | CPI, liquidity, wage index, credit tightness, rent index, consumer power per district, wholesale lead times | §9 |
| Determinism | Pure mulberry32, `S.rs` in the save, `diag.hash` over cash/heat/prices/world — replayable | `step`, `serialize` |

That is roughly 60% of the "living world" backbone. The gap to RDR2-grade is not more
systems of these kinds; it is **persons that persist and can punish you socially**, **a state
you personally have to live in**, and **legibility of what already exists**.

**Demolition list — state that currently buys nothing.** These pass gate 1 in reverse: they
cost an hour of decay math every tick and change no choice. Delete or re-point them before any
new feature is written. This is the cheapest "realism" in the document, because it is
subtraction.

| State | Written by | Read by a decision? | Verdict |
|---|---|---|---|
| `cl.wind`, `cl.pressure` | climate OU (§2) | No — print only ("Wind 1.6 m/s") | Delete, or make them drive **route time** (#25) |
| `cal.moon` | calendar (§1) | No — print only ("Moonlight 62%") | Delete, or gate **night courier risk** on it |
| `wd.chatter` | street ecology (§3) | No — decays, never read | Delete |
| `wd.transit` | initialised to 1 | Nothing ever writes it | Delete (it is dead) |
| `crew.sharedShifts` | incremented | Nothing reads it | Delete |
| `crew.campMorale` | smoothed from crew morale | No — display only | Re-point into **resignation odds** or delete |
| `e.blackMarketVolume` | recomputed from units sold | No — display only | Delete (a tautology: it is your own sales) |
| `cal.week` | calendar | No | Delete or use for **wage/pay cycles** (#20) |

Nine of the engine's "living world" numbers are dashboard ornaments. A reviewer who sees a moon
phase but no decision attached is right to call it cosplay.

**Seven holes found while reading** (each one checked in source or by `node _bench.js`, not guessed):

1. **Purity is economically decorative.** `markPrice` prices grade as
   `clamp(.45+purity*.72,.5,1.35)` — grade 0.60 → 0.88, grade 0.95 → 1.13, a **28.6% spread**.
   Settlement pays nothing like it: `acceptOffer` pays `ask×qty` with only a `minGrade` gate
   (grade above spec earns zero), and `updateListings` pays `ask×qty×(.90+.10×purity)`, which
   is **3.5% of revenue across that whole 35-point range**. So the game models a premium and
   then refuses to pay it. Every per-lot moisture, seal, integrity and re-grading mechanic in
   the engine (§12 of `worldTick`) currently changes a number nobody is paid for.
2. **The top-margin goods have no buyers.** `mkClient` sets `pref:ri(0,4)`, so named buyers
   only ever want products 0–4. Products 5–7 (`LUMEN`, `Onyx`, `Mirror`, tiers 3–4, base price
   212–470) can only move through anonymous passive listings. The most interesting inventory
   in the game has no cast of characters attached to it.
3. **The population can only shrink.** `S.clients.push` appears twice (world creation, the
   referral event); churn deletes clients and nothing replaces them. Latent rather than active
   — measured stable at 19 contacts over 600 hours — but any harder churn tuning turns it into
   a slow starvation with no recruitment path.
4. **Memory is written, never written to.** `W.clients[].memory` is decayed hourly and shown as
   "N memories" in the analyst panel, but nothing ever pushes into it, so the count is always 0
   and the `m.val` read path is dead. The data structure for #2 in Part 2 already exists and is
   empty.
5. **The forecast cannot see the world layer.** It always runs at the hard-coded 150 paths,
   and its Monte Carlo steps price, heat and reconciliation only — so it is blind to curfews,
   strikes, inspections, `heatGen`, and the case file. It forecasts a simpler city than the one
   you are running. Its `auditRisk` also compares with `>` where the engine uses `>=`
   (`updateAttention`), so at exactly the threshold it under-reports.
6. **Two arrays grow without a clamp.** `W.dossier.threads` has no length cap (unlike
   `reports`, capped at 70) and `W.lots` is rebuilt hourly with no eviction (unlike `S.lots`,
   filtered to qty>0.05). Neither bites today; both are save-blob growth in a long game.
7. **An idle player is dead in 20 days.** Measured: doing nothing, the outfit hits
   "The ledger closed" at **hour 486 (day 20.3)** — cash 0, debt ¤19,251, worth −¤18,024.
   Fixed hourly overheads (~¤386/day at start) plus 0.12%/hour compounding do it. This is not
   a bug — pressure is good — but it is a **hard constraint on the road map**: any feature
   that takes days away from trading (injury downtime #9, a trial #15, the sleep ritual #11)
   ships a loss the player cannot avoid unless overheads or downtime rules change first.

Fixes 1–6 total roughly 120 lines. Fix 7 is a design decision, not a patch, and it comes
before the features that depend on it (Stage 0, Part 4).

**Verified budget** (`node _bench.js`, current build, seeded runs):

```
tick            0.52 ms per simulated hour (19 persons, 2 couriers, 7×8 market)
frame headroom  ~32 simulated hours per 16 ms frame → 8× speed costs ~3% of a core
save            ~62 KB JSON after 400 simulated hours, one snapshot per hour
idle lifespan   ~486 h (20.3 days) before insolvency, with no trading at all
offers          ~1,300 offer-hours over 600 h, 100% in the buyer's own district
scale           7 districts · 8 products · 12 live modifier tags · witnesses capped at 5/hour
```

Two of those numbers shape the whole plan: the tick budget says per-person bookkeeping is
nearly free (≈10 µs per person per hour available), and the idle lifespan says the economy
has no slack for downtime until Stage 0 addresses it.

---

## Part 1 · The recipe

### 1.1 Four causal layers, and the one direction that matters

The layers still apply, but the failure mode this repo actually demonstrates is not orphaning —
it is **a full layer with nothing above it**. Climate, ecology and crew affinity are L0/L1
state with no L3 consumer, so they are instrumentation. Every feature must sit in a layer *and*
be consumed by the layer above it, ending in a decision the player can make.

```
L0  Substrate    hours, weather, prices, district ecology          (largely built)
L1  Persons      needs → intent → action → capacity                (thin: schedules only)
L2  Traces       witness reports · rumors · debts · memories ·
                 police file · health · promises made              (thin: dossier only)
L3  Consequences price, heat, standing, access, who will still
                 talk to you                                        (thin: heat + honor)
```

L2 is where this game is thin: one dossier pipeline, an empty `memory` array, and a `S.rep`
scalar. RDR2's L2 is dense and slow — a thing you did at hour 40 is still legible at hour 400.
That density is only worth building once L3 decisions exist to read it, which is why the
sequence in Part 4 puts the deal before the law.

### 1.2 The three rules every feature must pass

1. **Decision-changing or absent** — a feature that does not alter a choice is deleted, not
   documented. If the player would act identically with it removed, it is atmosphere and it
   waits until the decision layer exists. Tracing ("why is this price like this") is the
   *second* question, answered by `S.log`, `S.news`, `W.log`, `W.mods[].why`.
2. **Bounded** — new arrays get a hard cap and a decay in the same commit that introduces them.
   Cap = what one screen can show; overflow rotates out, never truncates silently.
3. **One writer per number** — if two systems write `c.loyalty`, one of them is wrong. Today
   `updateClients` writes mood, `worldTick` §5 overwrites mood from physiology, and
   `acceptOffer` writes it again. That needs a single owner per field before adding more.

### 1.3 Surface budget — fewer screens, not more

The UI is already 229 KB of paint against 57 KB of engine. Adding 40 systems to a 9-tab
dashboard makes all of them invisible, so the surface budget runs the other way:

- **No new tabs.** New state lands on the screen where the decision is made: grade on the deal
  card, knowledge on the market board, the case on the heat chip, downtime on the clock.
- **One "Why?" affordance**, reusing `W.mods[].why` and `S.log`, so a surprising number is
  always one click from its cause.
- **Four rituals, replacing four panels** — morning agenda, deal card, nightly page, week end.
  Each one consumes an existing dashboard so the net screen count does not grow.
- **Two densities stay two** (`clean` / `analyst`). The analyst tier is where the instrument
  panel lives; if a variable only ever appears there, it is demolition-list material.

### 1.4 Cost legend

| Cost | Means |
|---|---|
| **S** | ≤ 60 lines, no new state, one hook |
| **M** | new state array/object + one per-hour hook + one readout |
| **L** | new subsystem: its own tick slice, its own screen, save migration |

---

## Part 2 · The 40 features, re-judged by decision

Same count, different admission test. Each row must name **the decision it changes** and **the
fork it adds**. Where a row cannot name one, it is either cut or re-pointed at an existing
decision — and the re-point is written in the row.

Key: **◆** = spine (carries the realism), **F** = a fork is created (a real chance node or an
irreversible commitment), **C** = a clock/cost the player must spend.

### System A — The deal itself is the game (8)

The core loop's only decision is *ask + quantity*. These widen it without moving the tick.

| # | Feature | The decision it changes | Fork |
|---|---|---|---|
| 1 | **◆◆ Buyer tolerances with a real curve** | "Which good do I give this buyer?" — today grade above spec pays nothing (`acceptOffer` pays `ask×qty`; listings pay a 3.5%-of-revenue slope for a 35-point grade gap, while `markPrice` spreads 28.6%) | **F** — push 95% grade at spec price, or 70% at a discount; both are now live options |
| 2 | **◆◆ Promised vs delivered grade** | "What do I promise, and can I afford to break it?" — a contract is a written claim, checked on delivery | **F + C** — under-deliver for margin, lose the buyer's memory of it |
| 3 | **◆◆ Deal memory (buyer remembers you)** | "Do I overcharge this one?" — reprices the next offer (−8% and shorter TTL after two bad deals) | **F** — squeezing a contact is now a debt with a due date |
| 4 | **◆◆ Named buyers for every tier** | "Do I sell the expensive good, and to whom?" — `pref:ri(0,4)` leaves `LUMEN`/`Onyx`/`Mirror` with no cast | **F** — chase the tier-4 buyer who trusts you, or keep moving cheap volume |
| 5 | Counter-offer as a position, not a roll | "What is my price, and what do I concede?" — one sigmoid (`offerOdds`) currently resolves everything | **F** — concede grade, speed, or quantity instead of price |
| 6 | Deadlines and urgency | "Do I take the order I cannot fill in time?" — TTL is uniform; urgency costs nothing | **C** — hours as currency |
| 7 | Batch tests (pay to know what you have) | "Do I pay to know, or sell blind?" — purity is free information today | **C** — money for certainty, which then prices the gamble |
| 8 | Refusal as a play | "Do I take this deal at all?" — declining costs a mood tick and nothing else | **F** — a reputation for refusal has value in a squeeze |

**Why these first.** The whole game funnels into row 1–5. Grade that pays (1–2) plus memory (3)
turns one sigmoid into a negotiation with a history, and it is the only place where more
simulation *is* more decision. Everything else in this document is downstream of it.

### System B — Access: who will still talk to you (6)

| # | Feature | The decision it changes | Fork |
|---|---|---|---|
| 9 | **◆◆ Knowledge with an age stamp** | "Is this price worth acting on?" — every district×product unknown until seen; stale cells show a range and an age | **F** — scouting costs hours; acting on stale info is a real gamble |
| 10 | **◆◆ Standing as a gate, not a score** | "Who do I have to be, to be in this room?" — tiers of access held by people, not a `S.rep` bar | **F** — a favour spent is a favour gone |
| 11 | Favours owed and called | "Whose favour do I burn, and when?" — a bounded list of specific people who owe you one thing | **C** — irreversible, one-shot |
| 12 | Introductions through people | "Which contact do I ask for an intro?" — replacement population arrives by attribution (fixes hole #3) | **C** — a bad intro damages the *introducer* |
| 13 | Refusals that stick | "Whose offer do I turn down?" — refusing a powerful buyer closes a door for weeks | **F** |
| 14 | Buyer density is a place, not a number | "Where do I work tonight?" — same goods, different buyers per district, gated by knowledge (#9) | **F** |

**9 · Knowledge with an age stamp** replaces the old "confidence bands" entry, because bands
alone are a readout. What makes it a decision is the *cost of refresh*: scouting a district is
an hour and a courier, and stale prices are actionable but wrong. That converts the market board
from a dashboard into a map of what you don't know.

### System C — Time you cannot buy back (6)

| # | Feature | The decision it changes | Fork |
|---|---|---|---|
| 15 | **◆◆ Downtime that costs trading hours** | "Is this errand worth four trading hours?" — the operator has a clock too | **C** |
| 16 | Sleep debt degrades judgement | "Do I push to 04:00?" — exhausted actions get quietly worse odds | **F** — the error is real, not cosmetic |
| 17 | Injury as lost days | "Do I run the risky route tonight?" — a bad outcome removes you for 8–30 h | **C** + survival risk |
| 18 | The nightly page → morning agenda | "What do I do with these 24 hours?" — a short agenda, not a report | **C** |
| 19 | Two clocks (weeks exist) | "Do I hold stock into next week?" — seasons and pay cycles move prices on a slow band | **F** |
| 20 | Wage and pay cycles that bite | "Do I pay now or late?" — late wages become a rumour with your name on it | **F** |

**15 · Downtime** is only admissible *because* hole #7 is fixed first (an idle player dies in
20.3 days). A cost that cannot be paid is not a decision; it is a loss. That ordering is not
negotiable — Stage 0 before Stage 2.

### System D — Law as an opponent (5)

| # | Feature | The decision it changes | Fork |
|---|---|---|---|
| 21 | **◆◆ Named case file with a hypothesis** | "Which pattern do I break, and which do I keep?" — the detective's guess drifts toward your actual habit; switching product/district sends it cold | **F** — the strongest fork in the document |
| 22 | Interviews: pressure, pay, discredit | "Which witness do I spend on?" — each option leaves a different trace | **F** |
| 23 | Bribery with a corruption market | "Is this official worth buying?" — a bribe can become a charge | **F** |
| 24 | Charges → counsel → trial | "Do I fight, or take the deal?" — evidence-weighted outcome vs a sentence that removes days | **F + C** |
| 25 | Informants who can be flipped | "Who do I cut in?" — a contact who knows your buyers is a liability | **F** — reversible betrayal |

**21 · The case file** is the one feature in this document that creates a *strategic* habit
rather than a tactical one: it rewards rotating product, district and timing, which is the
first time the player has anything to be disciplined about. It costs one object
(`{detective, hypothesis, witnesses, budget}`) on top of the existing `W.dossier.threads`.

### System E — Route and distance (4)

| # | Feature | The decision it changes | Fork |
|---|---|---|---|
| 26 | **◆◆ Route choice with a named bottleneck** | "Which way, and when?" — patrol shifts/lighting/footfall exist per district; make the *edge* the choice | **F** — per-run risk you accept knowingly |
| 27 | Wind and pressure → transit time | "Do I ship into the storm?" — re-points two demolition-list variables at a decision (see Part 0) | **F** |
| 28 | Moon → night visibility | "Do I move at 02:00 or 04:00?" — re-points `cal.moon` at a decision | **F** |
| 29 | Capacity as a place | "Where do I hold stock?" — volume by district, access hours, wrong district = gone for 8 h | **C** |

**26–28** exist to answer your objection rather than dodge it: weather and moon are *only* in
this document because they can be wired into per-run risk and transit time, which are decisions.
If they cannot be wired, they belong on the demolition list with `chatter`.

### System F — Money with edges (3)

| # | Feature | The decision it changes | Fork |
|---|---|---|---|
| 30 | **◆◆ Four money layers** | "Which money do I spend?" — cash / unreconciled / credit / laundered reach different people | **F** |
| 31 | Lenders and violent default | "Do I borrow to cover the shortfall?" — collections costs stock or days | **F** |
| 32 | Insurance and hedging | "Do I pay to cap this risk?" — a premium against a specific damage class | **C** |

### System G — Supply chain (3)

| # | Feature | The decision it changes | Fork |
|---|---|---|---|
| 33 | **◆◆ Breakage and re-grading** | "Sell damaged now, or pay to re-grade?" — per-lot integrity finally pays | **F** |
| 34 | Batch lineage | "Do I clean my chain or risk the trace?" — a seized lot traces back through job→courier→depot | **C** |
| 35 | Cold-chain events with a named cause | "Which storage do I trust in this heat?" — humidity hits specific lots in specific places | **F** |

### System H — Consequence made legible (5)

| # | Feature | The decision it changes | Fork |
|---|---|---|---|
| 36 | **◆◆ The nightly page** | "What changed while I slept?" — five bullets, each citing the event it came from | **C** (it is a ritual, not a readout) |
| 37 | Contradiction surfacing | "Which source do I believe?" — two sources disagree and the game says so instead of averaging | **F** |
| 38 | Rival bosses as people | "Which rival do I let grow?" — succession changes stance, so alliances have a shelf life | **F** |
| 39 | District grudges | "Do I hit the same block twice?" — repeat seizures change *who buys* there for weeks | **C** |
| 40 | Your own standing, seen from outside | "What do I have to be, for this to keep working?" — the aggregate of per-buyer opinion, readable in one card | **F** |

### The cut list (features that failed the gates)

Removed from the previous draft, with the reason:

- **Weather fidelity upgrade** (finer climate) — changes the sigmoid you already tune. Fails gate 1.
- **Moon phase as a calendar feature** — readout with no decision; survives only if #28 wires it.
- **Camp morale / affinity matrix as features** — already display-only (Part 0 demolition list).
- **Courier "life" flavour (off-shift needs, followed home)** — atmosphere without a fork; the
  *risk* half survives as #26/#27.
- **Refining as chemistry** — the shop becomes a place with conditions, but the player's action
  (queue a job) is unchanged. Re-point it at grade yield (#1/#33) or leave it out.
- **Aging and succession for contacts** — time-passing without a choice; rival succession
  survives as #38 because it changes an alliance.

## Part 3 · What NOT to build (and why)

Ponytail applies to the road map as much as to code. Five exclusions, each one a gate failure:

1. **No graphics, no 3D, no animated world.** A 3D city would make the *debate* harder to read,
   not the world easier to feel. This game's realism is arithmetic you can see through.
2. **No growth-by-addition population.** Do not fix hole #3 by topping the roster back up with
   strangers; that is how a city becomes a vending machine. Replacement arrives by named cause
   (#12).
3. **No combat verbs.** The *consequences* of violence (injury #17, default #31, trial #24) are
   already decision-shaped; the verb is a minigame that competes with the core loop.
4. **No LLM dialogue in the loop.** Nondeterminism breaks `diag.hash` replay and adds per-tick
   cost. Templates keyed by deal memory (#3) give named lines with zero new failure modes.
5. **No more instrumentation.** Anything that produces a number the player cannot act on is
   rejected at review. This is the rule that kills weather-as-atmosphere and it is the reason
   Part 0 exists.

Also: **do not widen the tick.** 1 tick = 1 hour is the backbone of determinism and the 0.5 ms
budget. Features that "need" minutes become one hour with a seeded resolution and a trace.

---

## Part 4 · Sequencing

Stage 0 is subtraction; Stages 1–2 are the decision layer; everything after is consequence.
Each stage ends with the suite green (`node _test_new.js`) and its number added to `_bench.js`.

| Stage | Contents | Why in this order | Exit check (a decision test, not a feature test) |
|---|---|---|---|
| **0 — Subtraction & repair** | Part 0 demolition list; holes 1–6; the idle-lifespan decision (7) | Every instrument you keep is a lie you have to maintain | Engine no longer writes a number that nothing reads; grade gap pays ~28%; products 5–7 get named offers |
| **1 — The deal** | #1–5, #7, #8, #40 | The only place where simulation *is* decision; everything else is downstream | A player can lose money by overcharging a specific buyer and explain why |
| **2 — Time & access** | #9–18, #6 | Turns hours and information into currency, now that idle death is fixed | Two players with the same cash make different plans because of what they know |
| **3 — Law** | #21–25, #39 | The first strategic habit: rotate or get caught | A case that names its detective, its guess, and the pattern that beat it |
| **4 — Route & supply** | #26–29, #33–35 | Per-decision risk on top of a working deal layer | Every run has a risk you chose; broken stock has a price and a buyer |
| **5 — Long game** | #19, #20, #30–32, #38 | Weeks and money layers, once the loop is honest | 300 hours: save ≤ 400 KB, ≤ 4 ms/tick, ≥ 30 days survivable idle |
| **6 — Atmosphere** | Re-pointed climate/moon (#27, #28) only | And only if stages 1–5 kept their gates | Each new variable has a named decision consumer or is deleted |

Stage 0 is non-negotiable and it is small: mostly deletion, plus ~120 lines of repair.

---

## Part 5 · How to verify the claims in this document

```bash
node _bench.js      # tick cost, save size, idle lifespan, whether grade pays — read-only
node _test_new.js   # full UI/engine suite (13/13 passing, 0 errors)
```

The gate in the introduction is mechanically checkable, and was checked:

```bash
# player verbs with a genuine roll vs verbs that are arithmetic
grep -oE '^A\.[a-zA-Z]+=' _extracted.js | wc -l          # 21 verbs
# tracked variables with no decision consumer: each of these appears once (write) plus
# display-only reads — wind, pressure, moon, chatter, transit, sharedShifts, campMorale,
# blackMarketVolume, week
```

`_bench.js` is a probe, not a test: it prints and never fails the build. Two budgets it
currently confirms with margin, and that every stage must keep:

- **≤ 4 ms** per simulated hour with 400 tracked persons (today: 0.52 ms at 19 persons, so the
  per-person budget is ≈10 µs — most features above are per-hour bookkeeping and fit).
- **≤ 400 KB** save JSON at 300 in-game days (today: 62 KB after 400 simulated hours; the caps
  in Part 1.2 rule 2 are what keep it from growing).
- **≥ 30 days** of survivable idle time after Stage 0 (today: 20.3 days), so downtime features
  cannot hand the player an unavoidable loss.

When a stage lands, add its number to `_bench.js` output so the next reader can see the trend
rather than trusting a sentence in a markdown file.

---

*Written against `main` @ `20e4373`. Every number in this file is reproducible with
`node _bench.js`; four claims from the first draft were cut after the probe contradicted them.
Engine references are symbol names in `_extracted.js` (the JS block of `NIGHTLEDGER.html`),
because line numbers shift with every edit.*
