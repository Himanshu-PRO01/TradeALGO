#!/usr/bin/env python3
"""Check that your DEPLOYED website really works, the way a visitor would see it."""
from __future__ import annotations
import argparse, os, re, sys, time, urllib.error, urllib.request
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS=os.path.join(ROOT,"site-check-artifacts")
SELECTORS={"app_frame":'iframe[title="streamlitApp"]',"wake_button":'button:has-text("get this app back up")',"app_ready":'[data-testid="stApp"]',"python_error":'[data-testid="stException"]',"password_box":'input[type="password"]',"busy":'[data-testid="stStatusWidget"]'}
SLOW_SECONDS=20
def page_urls():
    out=[("Trading Desk (front page)","")]
    folder=os.path.join(ROOT,"pages")
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder),key=lambda n:(int(re.match(r"\d+",n).group()) if re.match(r"\d+",n) else 0,n)):
            if name.endswith(".py"): out.append((name[:-3],"/"+re.sub(r"^[0-9_\s]+","",name[:-3])))
    return out
def http_check(base):
    results=[]
    for label,path,want_body in (("Site responds","/",None),("Streamlit health endpoint","/_stcore/health","ok")):
        started=time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(base+path,headers={"User-Agent":"site-check"}),timeout=30) as r:
                body=r.read(2000).decode("utf-8","replace").strip(); took=time.time()-started
                if r.status!=200: results.append(("FAIL",label,f"HTTP {r.status}"))
                elif want_body and body.lower()!=want_body: results.append(("FAIL",label,f"expected '{want_body}', got '{body[:60]}'"))
                else: results.append(("PASS",label,f"{took:.1f}s"))
        except urllib.error.HTTPError as e: results.append(("FAIL",label,f"HTTP {e.code}"))
        except Exception as e: results.append(("FAIL",label,f"{type(e).__name__}: {e}"))
    return results
class LoginFailed(Exception): pass
def open_and_login(page,url,password,wake_timeout_ms):
    page.goto(url,wait_until="domcontentloaded",timeout=60000)
    deadline=time.time()+wake_timeout_ms/1000; scope,clicked=page,False
    while True:
        if not clicked and page.locator(SELECTORS["wake_button"]).count(): page.locator(SELECTORS["wake_button"]).first.click(timeout=5000); clicked=True
        if page.locator(SELECTORS["app_frame"]).count(): scope=page.frame_locator(SELECTORS["app_frame"])
        if scope.locator(SELECTORS["app_ready"]).count(): break
        if time.time()>deadline: raise TimeoutError("the app never appeared (still asleep, crashed on start, or blocked)")
        time.sleep(1)
    box=scope.locator(SELECTORS["password_box"])
    if password:
        try: box.first.wait_for(state="visible",timeout=15000)
        except Exception: raise LoginFailed("no password screen appeared, so this page may be open to anyone (leave out --password if the site is meant to be open)")
        box.first.fill(password); box.first.press("Enter")
        try: box.first.wait_for(state="detached",timeout=15000)
        except Exception: raise LoginFailed("the password was not accepted (or the site locked this session)")
    else:
        time.sleep(1.5)
        if box.count(): raise LoginFailed("the site shows a password screen but no --password was given")
    return scope
def wait_until_idle(page,scope,seconds=60):
    time.sleep(1.5)
    try: scope.locator(SELECTORS["busy"]).first.wait_for(state="hidden",timeout=seconds*1000)
    except Exception: pass
def browser_check(base,password,quick,headed,wake_timeout):
    try: from playwright.sync_api import sync_playwright
    except ImportError: return [("FAIL","Browser check","Playwright is not installed: pip install playwright && python -m playwright install chromium")]
    os.makedirs(SHOTS,exist_ok=True); pages=page_urls()[:1] if quick else page_urls(); results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=not headed)
        for label,path in pages:
            context=browser.new_context(viewport={"width":1280,"height":900}); page=context.new_page(); js_errors=[]; page.on("pageerror",lambda e,bucket=js_errors: bucket.append(str(e)[:200])); started=time.time()
            try:
                scope=open_and_login(page,base+path,password,wake_timeout*1000); wait_until_idle(page,scope); took=time.time()-started
                errors=scope.locator(SELECTORS["python_error"])
                if errors.count(): raise AssertionError("Python error on the page: "+errors.first.inner_text()[:300].replace("\n"," "))
                if js_errors: raise AssertionError("browser JavaScript error: "+js_errors[0])
                results.append(("SLOW" if took>SLOW_SECONDS else "PASS",label,f"{took:.1f}s"))
            except LoginFailed as e: results.append(("FAIL",label,f"{e}  (stopping: every other page would fail the same way)")); break
            except Exception as e:
                shot=os.path.join(SHOTS,re.sub(r"\W+","_",label)+".png")
                try: page.screenshot(path=shot,full_page=True)
                except Exception: shot="no screenshot"
                results.append(("FAIL",label,f"{str(e).splitlines()[0][:200]}  [{shot}]"))
            finally: context.close()
        browser.close()
    return results
def main():
    ap=argparse.ArgumentParser(description="Check a deployed Streamlit site end to end.")
    ap.add_argument("url",nargs="?",default=os.environ.get("SITE_URL")); ap.add_argument("--password",default=os.environ.get("SITE_PASSWORD")); ap.add_argument("--quick",action="store_true"); ap.add_argument("--headed",action="store_true"); ap.add_argument("--wake-timeout",type=int,default=150)
    args=ap.parse_args()
    if not args.url: ap.error("give the site address (or set SITE_URL)")
    base=args.url.rstrip("/"); print(f"\nChecking {base}\n"+"-"*60); results=http_check(base)
    if results[0][0]=="FAIL": results.append(("FAIL","Browser check","skipped: the site did not respond at all"))
    else: results+=browser_check(base,args.password,args.quick,args.headed,args.wake_timeout)
    icons={"PASS":"OK  ","SLOW":"SLOW","FAIL":"FAIL"}
    for status,label,detail in results: print(f"[{icons[status]}] {label:<38} {detail}")
    failed=[r for r in results if r[0]=="FAIL"]; slow=[r for r in results if r[0]=="SLOW"]; print("-"*60); print(f"{len(results)-len(failed)-len(slow)} passed, {len(slow)} slow, {len(failed)} failed")
    if failed: print(f"Screenshots of failures are in: {SHOTS}")
    return 1 if failed else 0
if __name__=="__main__": sys.exit(main())
