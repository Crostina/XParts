# main.py
# ================== IMPORTS ==================
import os # <--- NEW: For environment variables
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from playwright.async_api import async_playwright

# ================== CONFIG FROM ENVIRONMENT ==================
# CRITICAL: Use environment variables to keep credentials secret.
# You will set these in the Render dashboard.
START_URL = "https://www.partslink24.com/"
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "94 221 143") # <--- EXAMPLE

LOGIN_COMPANY = "fr-339599"
LOGIN_USER = "admin"
LOGIN_PASS = "Yassine21231434"
# ================== HELPERS ==================
def url_is_forbidden(url: str) -> bool:
    bad = ["/user/adminMenu.do", "adminMenu.do", "account-users", "/administration", "/admin/", "/manage/users", "/user/manage"]
    return any(p in url for p in bad)

# ================== JS – safer versions ==================
FORCE_FRENCH_JS = """
Object.defineProperty(navigator, 'language', {get: () => 'fr-FR'});
Object.defineProperty(navigator, 'languages', {get: () => ['fr-FR', 'fr']});
console.log("[XParts] Language forced to fr-FR");
"""

BLOCKING_JS = """
console.log("[XParts] Blocking admin paths active");
(function() {
  try {
    if (window.__xparts_admin_blocker) return;
    window.__xparts_admin_blocker = true;
    var forbiddenPatterns = [
      '/user/adminMenu.do', 'adminMenu.do', 'account-users',
      '/administration', '/admin/', '/manage/users', '/user/manage'
    ];
    function isForbiddenUrl(url) {
      if (!url) return false;
      url = String(url);
      for (var i=0; i<forbiddenPatterns.length; i++) {
        if (url.indexOf(forbiddenPatterns[i]) !== -1) return true;
      }
      return false;
    }
    function forceBack(){
      try { alert('Access to administration features is restricted.'); } catch(e) {}
      try { location.href = 'https://www.partslink24.com/'; } catch(e) {}
    }
    function checkNow(){
      try {
        if (isForbiddenUrl(location.href)) forceBack();
      } catch(e) {}
    }
    try {
      var _assign = location.assign.bind(location);
      location.assign = function(u){ if(isForbiddenUrl(u)) { forceBack(); return; } return _assign(u); };
    } catch(e) {}
    try {
      var _replace = location.replace.bind(location);
      location.replace = function(u){ if(isForbiddenUrl(u)) { forceBack(); return; } return _replace(u); };
    } catch(e) {}
    var _pushState = history.pushState;
    history.pushState = function(state, title, url) {
      if (url && isForbiddenUrl(url)) { forceBack(); return; }
      return _pushState.apply(history, arguments);
    };
    var _replaceState = history.replaceState;
    history.replaceState = function(state, title, url) {
      if (url && isForbiddenUrl(url)) { forceBack(); return; }
      return _replaceState.apply(history, arguments);
    };
    document.addEventListener('click', function(e){
      try {
        var t = e.target;
        while (t && t !== document.documentElement) {
          if (t.href && isForbiddenUrl(t.href)) {
            e.preventDefault();
            e.stopPropagation();
            if (e.stopImmediatePropagation) e.stopImmediatePropagation();
            forceBack();
            return false;
          }
          t = t.parentNode;
        }
      } catch(_e) {}
    }, true);
    document.addEventListener('submit', function(e){
      try {
        var f = e.target;
        var action = (f && f.action) ? f.action : '';
        if (isForbiddenUrl(action)) {
          e.preventDefault();
          e.stopPropagation();
          if (e.stopImmediatePropagation) e.stopImmediatePropagation();
          forceBack();
          return false;
        }
      } catch(_e) {}
    }, true);
    function hideAdminElements() {
      var selectors = [
        'a[href*="adminMenu.do"]',
        'a[href*="account-users"]',
        'a[href*="/administration"]',
        'a[href*="/admin/"]',
        'a[href*="manage/users"]',
        'a[title*="Administrer"]',
        'a[title*="Administration"]',
        'button[onclick*="admin"]',
        '[data-admin]',
        '.admin-menu',
        '#admin-menu'
      ];
      for (var i=0; i<selectors.length; i++) {
        var els = document.querySelectorAll(selectors[i]);
        for (var j=0; j<els.length; j++) {
          var el = els[j];
          var span = document.createElement('span');
          span.textContent = (el.textContent || '').trim() || 'Admin';
          span.style.color = '#888';
          span.style.cursor = 'not-allowed';
          span.style.textDecoration = 'none';
          span.title = 'Access Restricted';
          if (el.parentNode) el.parentNode.replaceChild(span, el);
        }
      }
    }
    function refreshAll(){
      try { hideAdminElements(); } catch(e) {}
      try { checkNow(); } catch(e) {}
    }
    refreshAll();
    if (typeof MutationObserver !== 'undefined') {
      var mo = new MutationObserver(refreshAll);
      mo.observe(document.documentElement || document.body, { childList:true, subtree:true });
    }
    window.addEventListener('pageshow', refreshAll, true);
    window.addEventListener('popstate', refreshAll, true);
    window.addEventListener('hashchange', refreshAll, true);
    setInterval(refreshAll, 1000);
  } catch(e) {}
})();
"""
OVERLAY_JS = """
console.log("[XParts] Overlay init started");
(function(){
  function waitBody(fn) {
    if (document.body) return fn();
    const iv = setInterval(() => { if (document.body) { clearInterval(iv); fn(); } }, 400);
  }
  waitBody(() => {
    console.log("[XParts] Body ready – creating overlay");
    const ov = document.createElement('div');
    ov.id = 'xparts-ov';
    Object.assign(ov.style, {
      position: 'fixed', top: '10px', left: '10px', width: '300px', zIndex: '9999999',
      background: 'rgba(20,20,35,0.92)', border: '1px solid #555', borderRadius: '8px',
      color: '#ddd', fontFamily: 'Arial', boxShadow: '0 8px 24px #0008'
    });
    ov.innerHTML = `
      <div style="padding:8px;background:#222;display:flex;justify-content:space-between;">
        <b style="color:#4a90e2">XParts</b>
        <span>
          <button id="ov-min" style="background:none;border:none;color:#aaa;cursor:pointer;font-size:16px;">—</button>
          <button id="ov-cls" style="background:none;border:none;color:#aaa;cursor:pointer;font-size:16px;">×</button>
        </span>
      </div>
      <div id="ov-cont" style="padding:12px;">
        <div>Expires: <b>Unlimited</b></div>
        <div>Remaining: <b>Unlimited</b></div>
        <div>ID: <b>WEB</b></div>
        <div style="color:#aaa;font-size:12px;">Support: 94 221 143</div>
        <div style="margin-top:12px;display:flex;gap:10px;">
          <button id="ov-home" style="flex:1;padding:9px;background:#2a3c5e;border:none;border-radius:5px;color:#fff;cursor:pointer;">Home</button>
          <button id="ov-ref" style="flex:1;padding:9px;background:#2a3c5e;border:none;border-radius:5px;color:#fff;cursor:pointer;">Reload</button>
        </div>
      </div>`;
    document.body.appendChild(ov);
    let min = false;
    document.getElementById('ov-min').onclick = () => {
      min = !min;
      document.getElementById('ov-cont').style.display = min ? 'none' : 'block';
      document.getElementById('ov-min').textContent = min ? '+' : '—';
    };
    document.getElementById('ov-cls').onclick = () => ov.remove();
    document.getElementById('ov-home').onclick = () => location.href = 'https://www.partslink24.com/';
    document.getElementById('ov-ref').onclick = () => location.reload();
  });
})();
"""
# ================== App Lifespan ==================
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.page = None
    async with async_playwright() as p:
        # 1. CRITICAL CHANGE: Browser must be launched in HEADLESS mode for a server.
        browser = await p.chromium.launch(
            headless=True,  # <--- CHANGED FROM 'False' TO 'True'
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            viewport=None,
            locale="fr-FR",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            ignore_https_errors=True,
            java_script_enabled=True,
            bypass_csp=True,
            # Important for popupcheck
            extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9"}
        )
        page = await context.new_page()
        app.state.page = page

        def log_console(msg):
            print(f"[Browser JS] {msg.type.upper()}: {msg.text}")
        page.on("console", log_console)
        page.on("pageerror", lambda err: print(f"[Browser Error] {err}"))
        # Handle any popups by closing them immediately
        page.on("popup", lambda popup: asyncio.create_task(popup.close()))

        await page.add_init_script(FORCE_FRENCH_JS)
        await page.add_init_script(OVERLAY_JS) # overlay first – it's safe now
        await page.add_init_script(BLOCKING_JS)

        print("→ Going to start page...")
        await page.goto(START_URL, wait_until="domcontentloaded", timeout=60000)

        # 2. MODIFIED: Only attempt login if credentials are provided via environment variables.
        if LOGIN_COMPANY and LOGIN_USER and LOGIN_PASS:
            print("→ Attempting login...")
            success = False
            for i in range(4):
                try:
                    await page.wait_for_selector('input[name="accountLogin"]', timeout=15000)
                    await page.fill('input[name="accountLogin"]', LOGIN_COMPANY)
                    await page.fill('input[name="userLogin"]', LOGIN_USER)
                    await page.fill('input[type="password"]', LOGIN_PASS)
                    print("→ Clicking submit or pressing Enter...")
                    try:
                        await page.click('button[type="submit"], button:has-text("Login"), input[type="submit"]', timeout=10000)
                    except:
                        await page.press('input[type="password"]', "Enter")
                    # Wait for redirect away from login/popupcheck
                    await page.wait_for_url(lambda u: "popupcheck.html" not in u and "login" not in u.lower(), timeout=30000)
                    print("→ Navigation detected – assuming logged in")
                    success = True
                    break
                except Exception as e:
                    print(f"Login try {i+1} failed: {e}")
                    await asyncio.sleep(2.5)
            if not success:
                print("Login might have failed – check logs and credentials.")
            # Fallback: if stuck on popupcheck, force go to dashboard
            if "popupcheck.html" in page.url:
                print("Stuck on popupcheck – forcing redirect...")
                await page.goto("https://www.partslink24.com/partslink24/user/start.do", timeout=20000)
        else:
            print("→ No login credentials provided via environment variables. Proceeding without login.")

        yield

        await browser.close()

app = FastAPI(lifespan=lifespan)

# ================== Routes (UNCHANGED) ==================
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>XParts Web – PartsLink24</title>
    <style>
        body { margin:0; font-family:Arial,sans-serif; background:#0f0f1a; color:#e0e0ff; padding:20px; overflow:auto; }
        h1 { color:#5a9eff; }
        .view-container { position:relative; display:block; max-width:100%; overflow:auto; }
        #view { max-width:100%; height:auto; border:2px solid #444; border-radius:8px; box-shadow:0 0 15px #0008; image-rendering:pixelated; }
        button { padding:10px 20px; margin:8px 4px; background:#2a3f6e; color:white; border:none; border-radius:6px; cursor:pointer; }
        input { padding:10px; width:340px; font-size:16px; }
    </style>
</head>
<body>
    <h1>XParts – Live PartsLink24</h1>
    <p>Click on image to interact • Updates every 2s</p>
    <div class="view-container">
        <img id="view" src="/screenshot?t=0">
    </div>
    <br><br>
    <button onclick="location='/home'">Accueil</button>
    <button onclick="location='/reload'">Actualiser</button>
    <br><br>
    <input id="inp" placeholder="Texte à envoyer (cliquez d'abord sur un champ)">
    <button onclick="sendText()">Envoyer</button>
    <script>
        const img = document.getElementById('view');
        img.addEventListener('load', () => { img.style.height = 'auto'; }); // Ensure proper scaling
        img.addEventListener('click', async e => {
            const rect = img.getBoundingClientRect();
            const naturalW = img.naturalWidth;
            const naturalH = img.naturalHeight;
            const displayedW = rect.width;
            const displayedH = rect.height;
            const scaleX = naturalW / displayedW;
            const scaleY = naturalH / displayedH;
            const x = Math.round((e.clientX - rect.left) * scaleX);
            const y = Math.round((e.clientY - rect.top) * scaleY);
            await fetch(`/click?x=${x}&y=${y}`);
            img.src = `/screenshot?t=${Date.now()}`;
        });
        async function sendText() {
            const val = document.getElementById('inp').value.trim();
            if (val) {
                await fetch(`/type?text=${encodeURIComponent(val)}`);
                document.getElementById('inp').value = '';
                img.src = `/screenshot?t=${Date.now()}`;
            }
        }
        setInterval(() => { img.src = `/screenshot?t=${Date.now()}`; }, 2000);
    </script>
</body>
</html>
    """

@app.get("/screenshot")
async def screenshot(request: Request):
    page = request.app.state.page
    if not page: return Response(b"Not ready", status_code=503)
    try:
        return Response(await page.screenshot(type="png", full_page=True), media_type="image/png")
    except:
        return Response(b"Capture error", status_code=500)

@app.get("/home")
async def home(request: Request):
    if p := request.app.state.page:
        await p.goto(START_URL)
    return {"ok":True}

@app.get("/reload")
async def reload(request: Request):
    if p := request.app.state.page:
        await p.reload()
    return {"ok":True}

@app.get("/click")
async def click(x: float, y: float, request: Request):
    if p := request.app.state.page:
        await p.mouse.click(x, y)
    return {"ok":True}

@app.get("/type")
async def type_text(text: str, request: Request):
    if p := request.app.state.page and text:
        await p.keyboard.type(text)
    return {"ok":True}

# 3. CRITICAL CHANGE: Remove the local development server block.
# The server will be started by Render using its own command.
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")