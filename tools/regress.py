"""101% Anatomy regression playtest, v2.0. Run before EVERY release.

Usage: python3 tools/regress.py index.html [mode] [--tabs N|auto] [--seed N]

Modes (pick one; the default is --full):
  --quick       a handful of decks (one of each kind) plus the frozen-save check. Use while building.
  --full        every deck in every mode plus the frozen-save check. Use before a release.
  --units 3,11  only the decks of those units (chapter numbers or ids like ch3) plus the frozen-save check.
  --changed     decks whose questions or pictures changed since the last passing full/changed/units run,
                plus the quick set. Needs one full run first to learn what "unchanged" means.

What it checks, on a small touch phone screen, for every deck it plays (and every mode):
  - every question's buttons are on screen and not covered when pressed
  - the progress bar is full after answering the last question
  - the last Next ("See results") reaches the results page
  - stats are saved, including when the saved stats come back FROZEN from the Claude db
    (the bug behind v1.4's stuck "See results")
  - identification decks: the after-answer picture shows when the card has one, the tip shows exactly
    when the card was missed and has a tip, and every 4th card advances with a left swipe instead of Next

How it stays fast (v2.0):
  - several browser tabs (--tabs) pull decks from one shared queue, each tab with its own fake save
  - each card is answered, checked and advanced in ONE call into the page; a real touch/typing path
    (Playwright taps) still runs on the first, middle and last card of every round
  - it waits for the page to be ready instead of sleeping a fixed time
  - the frozen-save check replays three decks instead of the whole app
Every deck's random answers come from --seed (printed in the result line), so a failure can be replayed.
"""
import argparse, asyncio, functools, hashlib, http.server, json, os, random, sys, threading, time
from playwright.async_api import async_playwright

ap = argparse.ArgumentParser(description="101% Anatomy regression playtest v2.0")
ap.add_argument("page", nargs="?", default="index.html")
mg = ap.add_mutually_exclusive_group()
mg.add_argument("--quick", action="store_true")
mg.add_argument("--full", action="store_true")
mg.add_argument("--changed", action="store_true")
mg.add_argument("--units", metavar="LIST")
ap.add_argument("--tabs", default="auto", help="browser tabs at once, or 'auto' (twice the CPU cores, at most 8)")
ap.add_argument("--seed", type=int, default=None)
ARGS = ap.parse_args()
MODE = "quick" if ARGS.quick else "changed" if ARGS.changed else "units" if ARGS.units else "full"
SEED = ARGS.seed if ARGS.seed is not None else random.randrange(10**6)
TABS = max(2, min((os.cpu_count() or 2) * 2, 8)) if ARGS.tabs == "auto" else max(1, int(ARGS.tabs))

SRC = os.path.abspath(ARGS.page)
ROOT = os.path.dirname(SRC)
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".regress-cache.json")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=ROOT))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/{os.path.basename(SRC)}"

# Fake Claude db. get() hands the saved stats back FROZEN, like the real one did in v1.4.
MOCK = '''(()=>{const store=__STORE__;const freeze=o=>{if(o&&typeof o==="object"){Object.values(o).forEach(freeze);Object.freeze(o);}return o;};
const ref={get:async()=>({exists:!!store.doc,data:()=>store.doc?freeze(JSON.parse(JSON.stringify(store.doc))):undefined}),
 set:async d=>{store.doc=JSON.parse(JSON.stringify(d));window.__saved=JSON.stringify(store.doc);}};
const db={collection:()=>({doc:()=>ref})};const user={id:async()=>"u1"};
window.claude={use:async n=>n==="db"?db:n==="user"?user:null};})();'''

# Everything a card needs, run inside the page so one call does a whole card.
HELPERS = r'''window.__t=(()=>{
const tick=()=>new Promise(r=>setTimeout(r,0));
const q=s=>document.querySelector(s);
const layout=sel=>{const e=q(sel);if(!e)return sel+" missing";const r=e.getBoundingClientRect();
  if(!(r.y>=0&&r.y+r.height<=innerHeight+1))return sel+" off screen";
  const t=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
  if(!(t&&t.closest("#"+e.id)))return sel+" covered";return null;};
const press=(sel,P)=>{const p=layout(sel);if(p)P.push(p);const e=q(sel);
  if(!e||e.disabled){P.push(sel+" not clickable");return false;}e.click();return true;};
const put=(v,P)=>{const a=q("#ans");if(!a||a.disabled){P.push("#ans not typeable");return false;}
  a.value=v;a.dispatchEvent(new Event("input",{bubbles:true}));return true;};
const kindOf=(r,acc)=>r<.2?"idk":r<.4?"wrongright":(r<.6&&acc.length>6)?"typo":"plain";
const answer=async(kind,acc,P)=>{
  if(kind==="idk"){press("#idk",P);}
  else if(kind==="wrongright"){put("zzzz",P);press("#go",P);await tick();put(acc,P);press("#go",P);}
  else if(kind==="typo"){put(acc.slice(0,-2)+acc.slice(-1),P);press("#go",P);await tick();
    if(q("#sug-yes"))press("#sug-yes",P);else if(!q("#next")){put(acc,P);press("#go",P);}}
  else{put(acc,P);press("#go",P);}
  await tick();};
const checks=(o,P)=>{
  if(o.last){const w=q(".bar i").style.width;if(w!=="100%")P.push("progress bar at last question is "+w);}
  if(o.ident){const st=round.qs[round.i].st,hasTip=!!st.tip,hasImg=!!idFiles(st);
    const tip=document.querySelectorAll("#tip").length,aimg=document.querySelectorAll("#aimg").length;
    if(tip!==(o.missed&&hasTip?1:0))P.push(st.id+": tip shown="+tip+", missed="+o.missed+", has tip="+hasTip);
    if(aimg!==(hasImg?1:0))P.push(st.id+": after-answer picture shown="+aimg+", built="+hasImg);}};
const swipe=async(o,P)=>{const before=round.i,el=q("#app");
  const t=(x,y)=>new Touch({identifier:1,target:el,clientX:x,clientY:y});
  el.dispatchEvent(new TouchEvent("touchstart",{bubbles:true,touches:[t(300,400)],changedTouches:[t(300,400)]}));
  el.dispatchEvent(new TouchEvent("touchend",{bubbles:true,touches:[],changedTouches:[t(200,410)]}));
  await tick();if(!(o.last||round.i===before+1))P.push("swipe did not advance card "+(o.i+1));};
const open=(deck,mode)=>{view={page:"unit",unit:DECKS[deck].unit};render();
  const tile=q('[data-deck="'+deck+'"]');if(!tile)return{err:"deck tile missing"};tile.click();
  if(mode){const b=q(mode);if(!b)return{err:"mode button "+mode+" missing"};b.click();}
  return{n:round.qs.length,ident:!!DECKS[deck].ident};};
const card=async o=>{const P=[];const acc=round.qs[round.i].st.accept[0];const kind=kindOf(o.r,acc);
  o.missed=kind==="idk";await answer(kind,acc,P);checks(o,P);
  if(o.swipe)await swipe(o,P);else press("#next",P);
  await tick();return P;};
const post=async o=>{const P=[];checks(o,P);if(o.swipe)await swipe(o,P);return P;};
return{layout,kindOf,open,card,post};})();'''

DECK_META = r'''(()=>{const fnv=s=>{let h=0x811c9dc5;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,0x01000193)>>>0;}return h.toString(16);};
return Object.values(DECKS).map(d=>{const it=itemsFor(d.id);const files=[];
  if(d.ident)it.forEach(st=>{const f=idFiles(st);if(f)Object.values(f).forEach(v=>{if(typeof v==="string")files.push(v);});});
  let h;try{h=fnv(JSON.stringify([d.name,it,files]));}catch(e){h="x"+it.length;}
  return{id:d.id,unit:d.unit,name:d.name,two:!!(d.fn||d.ident),ident:!!d.ident,fn:!!d.fn,n:it.length,
    pics:d.ident?it.filter(st=>!!idFiles(st)).length:0,h,files:[...new Set(files)]};});})()'''

fails = []
errs = []


def check(c, msg):
    if not c:
        fails.append(msg)


def kind_of(r, acc):
    return "idk" if r < .2 else "wrongright" if r < .4 else "typo" if (r < .6 and len(acc) > 6) else "plain"


async def tap(pg, sel, P):
    """A real Playwright touch tap, with the same on-screen / not-covered check as the fast path."""
    p = await pg.evaluate("s=>__t.layout(s)", sel)
    if p:
        P.append(p)
    await pg.locator(sel).tap()


async def answer_real(pg, kind, acc, P):
    if kind == "idk":
        await tap(pg, "#idk", P)
    elif kind == "wrongright":
        await pg.fill("#ans", "zzzz"); await tap(pg, "#go", P)
        await pg.fill("#ans", acc); await tap(pg, "#go", P)
    elif kind == "typo":
        await pg.fill("#ans", acc[:-2] + acc[-1]); await tap(pg, "#go", P)
        if await pg.locator("#sug-yes").count():
            await tap(pg, "#sug-yes", P)
        elif not await pg.locator("#next").count():
            await pg.fill("#ans", acc); await tap(pg, "#go", P)
    else:
        await pg.fill("#ans", acc); await tap(pg, "#go", P)


async def play(pg, deck, mode):
    """Play one deck in one mode. Returns (reached_results, cards_played)."""
    label = f"{deck} {mode}" if mode else deck
    rng = random.Random(f"{SEED}|{deck}|{mode}")
    o = await pg.evaluate("a=>__t.open(a[0],a[1])", [deck, mode])
    if o.get("err"):
        check(False, f"{label}: {o['err']}")
        return False, 0
    n, ident = o["n"], o["ident"]
    done = 0
    for i in range(n):
        opt = {"r": rng.random(), "last": i == n - 1, "ident": ident, "swipe": ident and i % 4 == 3, "i": i}
        if i in (0, n // 2, n - 1):   # real touch + typing path on a sample of cards
            acc = await pg.evaluate("round.qs[round.i].st.accept[0]")
            kind = kind_of(opt["r"], acc)
            opt["missed"] = kind == "idk"
            P = []
            await answer_real(pg, kind, acc, P)
            P += await pg.evaluate("o=>__t.post(o)", opt)
            if not opt["swipe"]:
                await tap(pg, "#next", P)
        else:
            P = await pg.evaluate("o=>__t.card(o)", opt)
        done += 1
        for p in P:
            check(False, f"{label} card {i + 1}: {p}")
        if any("#next" in p for p in P):   # stuck on this card; the rest would only repeat the failure
            break
    ok = await pg.evaluate("view.page") == "results"
    if not ok:
        try:
            await pg.wait_for_function("view.page==='results'", timeout=1500); ok = True
        except Exception:
            pass
    check(ok, f"{label} did not reach results")
    return ok, done


async def worker(tag, browser, queue, doc):
    ctx = await browser.new_context(viewport={"width": 390, "height": 664}, has_touch=True, is_mobile=True)
    store = {} if doc is None else {"doc": doc}
    await ctx.add_init_script(MOCK.replace("__STORE__", json.dumps(store)))
    pg = await ctx.new_page()
    pg.set_default_timeout(5000)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    played = cards = 0
    saved = None
    try:
        await pg.goto(URL)
        try:   # the page is ready once the (fake) saved stats have been fetched
            await pg.wait_for_function("typeof DECKS!=='undefined'&&typeof remote!=='undefined'&&remote!==null")
        except Exception:
            check(False, f"{tag}: the page never finished loading its saved stats")
            return None, 0, 0
        await pg.evaluate(HELPERS)
        before = await pg.evaluate("DATA.rounds.length")
        while True:
            try:
                deck, mode = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                ok, c = await play(pg, deck, mode)
                cards += c
                played += 1 if ok else 0
            except Exception as e:
                check(False, f"{tag}: {deck} {mode} crashed/stuck: {str(e).splitlines()[0][:120]}")
        if played:
            try:
                await pg.wait_for_function("window.__saved&&JSON.parse(window.__saved).rounds.length>=%d" % (before + played), timeout=4000)
            except Exception:
                pass
            raw = await pg.evaluate("window.__saved||null")
            check(raw is not None, f"{tag}: nothing saved")
            if raw:
                saved = json.loads(raw)
                check(len(saved["rounds"]) == before + played,
                      f"{tag}: saved {len(saved['rounds'])} rounds, expected {before + played}")
    finally:
        await ctx.close()
    return saved, played, cards


def pick_quick(decks):
    ident = [d for d in decks if d["ident"]]
    plain = [d for d in decks if not d["two"]]
    sel = []
    if ident:
        sel.append(max(ident, key=lambda d: d["n"]))
        nopic = [d for d in ident if d["pics"] == 0]
        part = [d for d in ident if 0 < d["pics"] < d["n"]]
        if nopic: sel.append(nopic[0])
        if part: sel.append(max(part, key=lambda d: d["n"]))
    sel += [d for d in decks if d["fn"]]
    if plain:
        sel += [max(plain, key=lambda d: d["n"]), min(plain, key=lambda d: d["n"])]
    seen, out = set(), []
    for d in sel:
        if d["id"] not in seen:
            seen.add(d["id"]); out.append(d)
    return out


def pick_frozen(decks):
    ident = [d for d in decks if d["ident"]]
    fn = [d for d in decks if d["fn"]]
    plain = [d for d in decks if not d["two"]]
    jobs = []
    if ident: jobs.append((max(ident, key=lambda d: d["n"])["id"], "#img-on"))
    if fn: jobs.append((fn[0]["id"], "#img-off"))
    if plain: jobs.append((min(plain, key=lambda d: d["n"])["id"], None))
    return jobs


def plays(ds):
    out = []
    for d in ds:
        out += [(d["id"], "#img-on"), (d["id"], "#img-off")] if d["two"] else [(d["id"], None)]
    return out


def fingerprint(d):
    parts = [d["h"]]
    for f in sorted(d["files"]):
        try: parts.append(f"{f}:{os.path.getsize(os.path.join(ROOT, f))}")
        except OSError: parts.append(f"{f}:-1")
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


async def main():
    t0 = time.perf_counter()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg0 = await b.new_page()
        perr = []
        pg0.on("pageerror", lambda e: perr.append(str(e)))
        await pg0.goto(URL)
        try:
            decks = await pg0.evaluate(DECK_META)
        except Exception:
            print(f"FAIL: page script failed to load: {perr}")
            print("RESULT: 1 FAILURE(S)")
            sys.exit(1)
        await pg0.close()
        for d in decks:
            d["fp"] = fingerprint(d)
        by_id = {d["id"]: d for d in decks}

        note = ""
        if MODE == "full":
            chosen = decks
        elif MODE == "quick":
            chosen = pick_quick(decks)
        elif MODE == "units":
            want = {("ch" + u if u.strip().isdigit() else u).strip() for u in ARGS.units.split(",")}
            chosen = [d for d in decks if d["unit"] in want]
            if not chosen:
                print(f"RESULT: no decks found for units {sorted(want)}"); sys.exit(1)
        else:  # changed
            try:
                old = json.load(open(CACHE))
            except Exception:
                old = None
            if old is None:
                chosen, note = decks, " (no cache yet, so running everything)"
            else:
                ch = [d for d in decks if old.get(d["id"]) != d["fp"]]
                have = {d["id"] for d in ch}
                chosen = ch + [d for d in pick_quick(decks) if d["id"] not in have]
                note = f" ({len(ch)} changed + quick set)"
        chosen = sorted(chosen, key=lambda d: -d["n"] * (2 if d["two"] else 1))   # big decks first keeps tabs balanced
        jobs = plays(chosen)
        planned_cards = sum(d["n"] * (2 if d["two"] else 1) for d in chosen)
        print(f"{MODE}{note}: {len(chosen)} decks, {len(jobs)} plays, {planned_cards} cards, {min(TABS, len(jobs))} tabs, seed {SEED}", flush=True)

        # pass A: fresh (empty) save, decks spread over the tabs
        queue = asyncio.Queue()
        for j in jobs:
            queue.put_nowait(j)
        res = await asyncio.gather(*[worker(f"tab {k + 1}", b, queue, None) for k in range(min(TABS, len(jobs)))])
        docs = [r[0] for r in res if r[0]]
        cards = sum(r[2] for r in res)

        # frozen pass: saved stats come back frozen. Any deck can trigger the bug, so three are enough.
        fq = asyncio.Queue()
        for j in pick_frozen(decks):
            fq.put_nowait(j)
        seed_doc = max(docs, key=lambda d: len(d["rounds"])) if docs else None
        if seed_doc:
            fr = await worker("frozen-save pass", b, fq, seed_doc)
            cards += fr[2]
        else:
            check(False, "no tab saved anything, so the frozen-save pass could not run")
        check(not errs, f"page errors: {errs}")
        await b.close()

    ok = not fails
    if ok and MODE in ("full", "units", "changed"):
        try: cache = json.load(open(CACHE))
        except Exception: cache = {}
        cache.update({d["id"]: d["fp"] for d in chosen})
        try: json.dump(cache, open(CACHE, "w"), indent=0)
        except OSError: pass
    seen = []
    for f in fails:
        if f not in seen: seen.append(f)
    for f in seen[:40]:
        print("FAIL:", f)
    if len(seen) > 40:
        print(f"... and {len(seen) - 40} more")
    secs = time.perf_counter() - t0
    print("RESULT:", "PASS" if ok else f"{len(seen)} FAILURE(S)",
          f"| {MODE} | {len(chosen)} decks, {len(jobs)} plays, {cards} cards | {min(TABS, len(jobs))} tabs | {secs:.0f}s | seed {SEED}")
    sys.exit(0 if ok else 1)


asyncio.run(main())
