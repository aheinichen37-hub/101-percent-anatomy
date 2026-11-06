"""101% Anatomy regression playtest. Run on EVERY new version before publishing.
Usage: python3 tools/regress.py index.html
Serves the page's folder over HTTP so figures and identification pictures load.
Checks, on a small touch phone screen, for every deck (and every mode):
  - every question's buttons are on screen and not covered when tapped
  - progress bar is full after answering the last question
  - the last Next ("See results") reaches the results page
  - stats are saved, including when saved stats come back FROZEN from the Claude db
    (the bug behind v1.4's stuck "See results")
  - identification decks (v2.5): the after-answer picture shows when the card has one, the tip shows exactly
    when the card was missed and has a tip, and every 4th card advances with a left swipe instead of Next
"""
import asyncio, random, json, sys, os, threading, functools, http.server
from playwright.async_api import async_playwright
SRC=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else "index.html")
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Quiet,directory=os.path.dirname(SRC)))
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL=f"http://127.0.0.1:{srv.server_address[1]}/{os.path.basename(SRC)}"
MOCK='''(()=>{const store=%s;const freeze=o=>{if(o&&typeof o==="object"){Object.values(o).forEach(freeze);Object.freeze(o);}return o;};
const ref={get:async()=>({exists:!!store.doc,data:()=>store.doc?freeze(JSON.parse(JSON.stringify(store.doc))):undefined}),
 set:async d=>{store.doc=JSON.parse(JSON.stringify(d));window.__saved=JSON.stringify(store.doc);}};
const db={collection:()=>({doc:()=>ref})};const user={id:async()=>"u1"};
window.claude={use:async n=>n==="db"?db:n==="user"?user:null};})();'''
fails=[]
def check(c,msg):
    if not c: fails.append(msg); print("FAIL:",msg)
async def tap(pg,sel):
    el=pg.locator(sel); bb=await el.bounding_box(); vh=pg.viewport_size["height"]
    check(bb and bb["y"]>=0 and bb["y"]+bb["height"]<=vh+1, f"{sel} off screen {bb}")
    ok=await pg.evaluate("([x,y,id])=>{const e=document.elementFromPoint(x,y);return !!(e&&e.closest('#'+id))}",[bb["x"]+bb["width"]/2,bb["y"]+bb["height"]/2,sel[1:]])
    check(ok, f"{sel} covered")
    await el.tap()
async def play(pg,deck,mode):
    await pg.evaluate(f"view={{page:'unit',unit:DECKS['{deck}'].unit}};render()")
    await pg.tap(f'[data-deck="{deck}"]',timeout=3000)
    if mode: await pg.tap(mode)
    n=await pg.evaluate("round.qs.length")
    ident=await pg.evaluate(f"!!DECKS['{deck}'].ident")
    for i in range(n):
        acc=await pg.evaluate("round.qs[round.i].st.accept[0]"); r=random.random(); missed=r<0.2
        if r<0.2: await tap(pg,"#idk")
        elif r<0.4: await pg.fill("#ans","zzzz"); await tap(pg,"#go"); await pg.fill("#ans",acc); await tap(pg,"#go")
        elif r<0.6 and len(acc)>6:
            await pg.fill("#ans",acc[:-2]+acc[-1]); await tap(pg,"#go")
            if await pg.locator("#sug-yes").count(): await tap(pg,"#sug-yes")
            elif not await pg.locator("#next").count(): await pg.fill("#ans",acc); await tap(pg,"#go")  # typo may already be exact (e.g. "Vitamin A" -> "VitaminA")
        else: await pg.fill("#ans",acc); await tap(pg,"#go")
        if i==n-1:
            w=await pg.evaluate("document.querySelector('.bar i').style.width")
            check(w=="100%", f"{deck} progress bar at last question is {w}")
        if ident:
            cid,hasTip,hasImg=await pg.evaluate("[round.qs[round.i].st.id,!!round.qs[round.i].st.tip,!!idFiles(round.qs[round.i].st)]")
            tip=await pg.locator("#tip").count()
            check(tip==(1 if missed and hasTip else 0), f"{cid} {mode}: tip shown={tip}, missed={missed}, has tip={hasTip}")
            aimg=await pg.locator("#aimg").count()
            check(aimg==(1 if hasImg else 0), f"{cid} {mode}: after-answer picture shown={aimg}, built={hasImg}")
        if ident and i%4==3:
            before=await pg.evaluate("round.i")
            await pg.evaluate("""()=>{const el=document.querySelector('#app');const t=(x,y)=>new Touch({identifier:1,target:el,clientX:x,clientY:y});
              el.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,touches:[t(300,400)],changedTouches:[t(300,400)]}));
              el.dispatchEvent(new TouchEvent('touchend',{bubbles:true,touches:[],changedTouches:[t(200,410)]}));}""")
            check(i==n-1 or await pg.evaluate("round.i")==before+1, f"{deck} {mode}: swipe did not advance card {i+1}")
        else: await tap(pg,"#next")
    await pg.wait_for_timeout(300)
    check(await pg.evaluate("view.page")=="results", f"{deck} {mode} did not reach results")
async def session(b,store,errs):
    ctx=await b.new_context(viewport={"width":390,"height":664},has_touch=True,is_mobile=True)
    await ctx.add_init_script(MOCK%json.dumps(store))
    pg=await ctx.new_page(); pg.on("pageerror",lambda e:errs.append(str(e)))
    await pg.goto(URL); await pg.wait_for_timeout(400)
    return ctx,pg
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    pg0=await b.new_page(); perr=[]; pg0.on("pageerror",lambda e:perr.append(str(e))); await pg0.goto(URL)
    # two-mode decks must match the app's own test in unitPage(): d.fn || d.ident
    try: decks=await pg0.evaluate("Object.values(DECKS).map(d=>[d.id,!!(d.fn||d.ident)])")
    except Exception: check(False,f"page script failed to load: {perr}"); print("RESULT: 1 FAILURE(S)"); sys.exit(1)
    store={}
    for sess in range(2):   # session 1: empty db; session 2: saved stats come back frozen
        ctx,pg=await session(b,store,errs)
        before=await pg.evaluate("DATA.rounds.length")
        played=0
        for did,fn in decks:
            for mode in (["#img-on","#img-off"] if fn else [None]):
                try: await play(pg,did,mode)
                except Exception as e: check(False, f"session {sess+1}: {did} {mode} crashed/stuck: {str(e).splitlines()[0][:120]}")
                played+=1
        await pg.wait_for_timeout(300)
        saved=await pg.evaluate("window.__saved||null")
        check(saved is not None, f"session {sess+1}: nothing saved")
        if saved:
            store["doc"]=json.loads(saved)
            check(len(store["doc"]["rounds"])==before+played, f"session {sess+1}: saved {len(store['doc']['rounds'])} rounds, expected {before+played}")
        await ctx.close()
    check(not errs, f"page errors: {errs}")
    await b.close()
  print("RESULT:", "PASS" if not fails else f"{len(fails)} FAILURE(S)")
  sys.exit(1 if fails else 0)
asyncio.run(main())
