"""101% Anatomy CORRECTNESS test, v1.0. Companion to regress.py (which checks the app *behaves*;
this checks the app is *right*).

Usage: python3 tools/correctness.py [index.html] [--tabs N] [--decks a,b] [--strict]

Same shape as regress.py: a few browser tabs pull decks from one shared queue; every deck is checked
inside the page in one call, then a real typing path runs on the first card of each deck.

Errors (exit 1):
  - an accepted answer of a card does not grade as correct on that card (typo-suggest swallows it,
    a 'near' hint intercepts it, or it normalises to nothing)
  - a card has no accepted answers, or its name is not among them
  - duplicate card ids
  - a registered identification card (IDIMG) has a picture that is missing, whose three files differ in
    size, whose highlight is empty, covers more than 45% of the picture, or leaves the answer image
    identical to the question image
  - a card's textbook figure file does not load
  - typing the right answer on the first card is not marked correct, or "zzzz" twice is not marked wrong
Warnings (shown; errors only with --strict):
  - two cards in one deck accept the same answer (ambiguous)
  - the clue contains the answer (gives it away)
"""
import argparse, asyncio, functools, http.server, json, os, sys, threading
from playwright.async_api import async_playwright

ap = argparse.ArgumentParser(description="101% Anatomy correctness test v1.0")
ap.add_argument("page", nargs="?", default="index.html")
ap.add_argument("--tabs", type=int, default=4)
ap.add_argument("--decks", help="comma-separated deck ids")
ap.add_argument("--strict", action="store_true", help="count warnings as errors")
ARGS = ap.parse_args()

SRC = os.path.abspath(ARGS.page)
ROOT = os.path.dirname(SRC)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=ROOT))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/{os.path.basename(SRC)}"

MOCK = '''(()=>{const store={};const ref={get:async()=>({exists:false,data:()=>undefined}),set:async d=>{}};
const db={collection:()=>({doc:()=>ref})};const user={id:async()=>"u1"};
window.claude={use:async n=>n==="db"?db:n==="user"?user:null};})();'''

# Per-deck data checks, all inside the page.
CHECK = r'''async deckId=>{
const E=[],W=[];const d=DECKS[deckId];const items=itemsFor(deckId);
const loadImg=src=>new Promise(r=>{const i=new Image();i.onload=()=>r(i);i.onerror=()=>r(null);i.src=src;});
const px=img=>{const c=document.createElement("canvas");c.width=img.naturalWidth;c.height=img.naturalHeight;
  const x=c.getContext("2d");x.drawImage(img,0,0);return x.getImageData(0,0,c.width,c.height).data;};
const seen=new Set(),owner=new Map();
for(const st of items){
  if(seen.has(st.id))E.push(st.id+": duplicate card id");seen.add(st.id);
  if(!st.accept||!st.accept.length){E.push(st.id+": no accepted answers");continue;}
  {const c=classify(st.name,deckId);
   if(!(c.kind==="answer"&&(c.id===st.id||(st.also||[]).includes(c.id)||st.accept.some(x=>norm(x)===c.n))))
     E.push(st.id+": typing the answer shown on screen, '"+st.name+"', would not be graded correct");}
  for(const a of st.accept){
    const n=norm(a);if(!n){E.push(st.id+": accepted answer '"+a+"' normalises to nothing");continue;}
    const c=classify(a,deckId);
    if(c.kind!=="answer"){E.push(st.id+": '"+a+"' is read as "+c.kind+", not an answer");continue;}
    const ok=c.id===st.id||(st.also||[]).includes(c.id)||st.accept.some(x=>norm(x)===c.n);
    if(!ok)E.push(st.id+": '"+a+"' would be graded wrong");
    if(st.near&&st.near[c.id])E.push(st.id+": '"+a+"' is intercepted by a 'near' hint");
    if(owner.has(n)&&owner.get(n)!==st.id)W.push(st.id+": '"+a+"' is also accepted by "+owner.get(n));
    owner.set(n,owner.get(n)||st.id);
  }
  const nn=norm(st.name);
  if(st.clue&&nn.length>=5&&norm(st.clue).includes(nn))W.push(st.id+": clue contains the answer '"+st.name+"'");
  if(d.ident){
    const f=idFiles(st);
    if(f){
      const [q,m,a]=await Promise.all([loadImg(f.q),loadImg(f.m),loadImg(f.a)]);
      if(!q||!m||!a){E.push(st.id+": picture file missing ("+[!q&&"q",!m&&"m",!a&&"a"].filter(Boolean).join(",")+")");}
      else{
        if(q.naturalWidth!==m.naturalWidth||q.naturalHeight!==m.naturalHeight||q.naturalWidth!==a.naturalWidth||q.naturalHeight!==a.naturalHeight)
          E.push(st.id+": q/m/a pictures differ in size");
        else{
          const mp=px(m);let on=0;for(let i=3;i<mp.length;i+=4)if(mp[i]>20)on++;
          const frac=on/(mp.length/4);
          if(frac<0.001)E.push(st.id+": highlight is empty");
          else if(frac>0.45)E.push(st.id+": highlight covers "+Math.round(frac*100)+"% of the picture");
          const qp=px(q),ap=px(a);let diff=0;for(let i=0;i<qp.length;i+=16)if(Math.abs(qp[i]-ap[i])+Math.abs(qp[i+1]-ap[i+1])+Math.abs(qp[i+2]-ap[i+2])>30)diff++;
          if(diff<5)E.push(st.id+": answer picture is the same as the question picture");
        }
      }
    }
    if(st.fig&&st.fig!=="-"&&typeof FIGS!=="undefined"&&FIGS.has(st.fig)){
      const i=await loadImg("figs/"+st.fig+".jpg");if(!i)E.push(st.id+": textbook figure figs/"+st.fig+".jpg does not load");
    }
  }
}
return{E,W,n:items.length};}'''

# Real typing path on one card per deck.
UI = r'''async ([deckId,mode])=>{
const tick=()=>new Promise(r=>setTimeout(r,30));const q=s=>document.querySelector(s);
view={page:"unit",unit:DECKS[deckId].unit};render();
const tile=q('[data-deck="'+deckId+'"]');if(!tile)return["deck tile missing"];tile.click();
if(mode){const b=q(mode);if(!b)return["mode button "+mode+" missing"];b.click();}
const P=[];const put=v=>{const a=q("#ans");if(!a||a.disabled){P.push("#ans not typeable");return false;}a.value=v;a.dispatchEvent(new Event("input",{bubbles:true}));return true;};
const go=()=>{const b=q("#go");if(b)b.click();};
if(typeof round==="undefined"||!round||!round.qs){return["round did not start"];}
const st=round.qs[round.i].st;
if(put(st.name)){go();await tick();if(!q(".fb.ok"))P.push(st.id+": typing the right answer '"+st.name+"' was not marked correct");}
view={page:"unit",unit:DECKS[deckId].unit};render();q('[data-deck="'+deckId+'"]').click();if(mode)q(mode).click();
if(put("zzzz")){go();await tick();put("zzzz");go();await tick();
  if(!q(".fb.bad"))P.push("typing a wrong answer twice was not marked wrong");
  else if(!(q(".fb.bad").textContent||"").includes(round.qs[round.i].st.name))P.push("after two misses the right answer is not shown");}
return P;}'''

fails, warns, errs = [], [], []


async def worker(tag, browser, queue, stats):
    ctx = await browser.new_context(viewport={"width": 390, "height": 664}, has_touch=True, is_mobile=True)
    await ctx.add_init_script(MOCK)
    pg = await ctx.new_page()
    pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    try:
        await pg.goto(URL)
        await pg.wait_for_function("typeof DECKS!=='undefined'&&typeof remote!=='undefined'&&remote!==null")
        while True:
            try:
                deck, mode = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                r = await pg.evaluate(CHECK, deck)
                fails.extend(f"{deck}: {m}" for m in r["E"])
                warns.extend(f"{deck}: {m}" for m in r["W"])
                stats["cards"] += r["n"]
                stats["decks"] += 1
                for m in await pg.evaluate(UI, [deck, mode]):
                    fails.append(f"{deck}: {m}")
            except Exception as e:
                fails.append(f"{tag}: {deck} crashed: {str(e).splitlines()[0][:140]}")
    finally:
        await ctx.close()


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        probe = await browser.new_page()
        await probe.add_init_script(MOCK)
        await probe.goto(URL)
        await probe.wait_for_function("typeof DECKS!=='undefined'")
        ids = await probe.evaluate("Object.values(DECKS).filter(d=>{try{return itemsFor(d.id).length>0}catch(e){return false}}).map(d=>[d.id,d.ident?'#img-on':d.fn?'#img-off':null])")
        await probe.close()
        if ARGS.decks:
            want = set(ARGS.decks.split(","))
            ids = [i for i in ids if i[0] in want]
        queue = asyncio.Queue()
        for i in ids:
            queue.put_nowait(tuple(i))
        stats = {"cards": 0, "decks": 0}
        t0 = asyncio.get_event_loop().time()
        await asyncio.gather(*[worker(f"tab{n + 1}", browser, queue, stats) for n in range(max(1, ARGS.tabs))])
        await browser.close()
    secs = round(asyncio.get_event_loop().time() - t0)
    for e in sorted(set(errs)):
        fails.append("page error: " + e[:140])
    bad = fails + (warns if ARGS.strict else [])
    for f in fails[:60]:
        print("FAIL", f)
    if len(fails) > 60:
        print(f"... and {len(fails) - 60} more failures")
    for w in warns[:25]:
        print("warn", w)
    if len(warns) > 25:
        print(f"... and {len(warns) - 25} more warnings")
    print(f"RESULT: {'FAIL' if bad else 'PASS'} | correctness v1.0 | {stats['decks']} decks, {stats['cards']} cards | "
          f"{len(fails)} errors, {len(warns)} warnings | {ARGS.tabs} tabs | {secs}s")
    return 1 if bad else 0


sys.exit(asyncio.run(main()))
