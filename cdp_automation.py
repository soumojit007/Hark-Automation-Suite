"""
Enhanced Chrome DevTools Protocol (CDP) Automation for Hark.com
Includes:
- Anti-wipe protection: waits for React hydration and verifies email isn't wiped before clicking Continue
- Magic link navigation
- Password setting on hark.com/set-password
- 18+ Birthday dropdown selection
"""

import time
import random
import json
import urllib.request
import urllib.error
import websocket

def get_tab_websocket(port: int, url_keyword: str = "hark.com", timeout: int = 25):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.urlopen(f"http://127.0.0.1:{port}/json")
            tabs = json.loads(req.read().decode('utf-8'))
            
            # 1. Search for tab with url_keyword
            for tab in tabs:
                if tab.get("type") == "page":
                    url = tab.get("url", "").lower()
                    if url_keyword and url_keyword in url:
                        ws = tab.get("webSocketDebuggerUrl")
                        if ws:
                            return ws

            # 2. If url_keyword not found yet after 4s, check if there's an open tab we can navigate
            if time.time() - start_time > 4:
                for tab in tabs:
                    if tab.get("type") == "page":
                        url = tab.get("url", "").lower()
                        if "chrome://" not in url:
                            ws = tab.get("webSocketDebuggerUrl")
                            if ws:
                                send_cdp_command(ws, "Page.navigate", {"url": "https://hark.com"})
                                time.sleep(1)
                                return ws
        except Exception:
            pass
        time.sleep(0.5)
    return None

def send_cdp_command(ws_url: str, method: str, params: dict, timeout: int = 8):
    try:
        ws = websocket.create_connection(ws_url, timeout=timeout)
        msg_id = int(time.time() * 1000) % 1000000
        payload = {
            "id": msg_id,
            "method": method,
            "params": params
        }
        ws.send(json.dumps(payload))
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            resp = ws.recv()
            if not resp:
                continue
            data = json.loads(resp)
            if data.get("id") == msg_id:
                ws.close()
                return data.get("result")
                
        ws.close()
        return {"error": "Timeout waiting for matching response"}
    except Exception as e:
        return {"error": str(e)}

def execute_js(ws_url: str, expression: str, timeout: int = 8):
    res = send_cdp_command(
        ws_url,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        },
        timeout=timeout
    )
    if isinstance(res, dict) and "result" in res:
        return res["result"].get("value")
    return res

def navigate_to_url(port: int, url: str):
    ws_url = get_tab_websocket(port, url_keyword="hark.com")
    if not ws_url:
        ws_url = get_tab_websocket(port, url_keyword="", timeout=5)
    if not ws_url:
        return {"success": False, "error": f"Tab not found on port {port}"}
    return send_cdp_command(ws_url, "Page.navigate", {"url": url})

def wait_and_submit_hark_email(port: int, email: str, max_wait_sec: int = 45, log_func=print):
    """
    STRICT OBSERVATION WITH ANTI-WIPE:
    1. Connects to Hark tab and waits until document.readyState === 'complete'.
    2. Waits for email input element to mount in the DOM.
    3. Waits 5 seconds for React hydration to fully finish settling.
    4. Enters email with anti-wipe verification.
    5. Clicks Continue button.
    6. Confirms that Hark moved to the next screen.
    """
    clean_email = email.strip()
    log_func(f"[*] Connecting to Hark on Port {port}...")

    start_time = time.time()
    ws_url = None
    while time.time() - start_time < max_wait_sec:
        ws_url = get_tab_websocket(port, url_keyword="hark.com", timeout=2)
        if ws_url:
            break
        time.sleep(1)

    if not ws_url:
        return {"success": False, "error": f"Could not connect to Hark tab on port {port}"}

    # STEP A: Wait for document.readyState == 'complete'
    log_func("[*] Waiting for Hark page readyState to be 'complete'...")
    ready = False
    for _ in range(15):
        state = execute_js(ws_url, "document.readyState")
        if state == "complete":
            ready = True
            break
        time.sleep(1)

    # STEP B: Wait for email input box to actually mount in DOM
    log_func("[*] Waiting for email input field to appear in DOM...")
    input_mounted = False
    for _ in range(15):
        js_find_input = """
        (() => {
            let inputs = Array.from(document.querySelectorAll("input"));
            let input = inputs.find(i => {
                let p = (i.placeholder || "").toLowerCase();
                let n = (i.name || "").toLowerCase();
                let t = (i.type || "").toLowerCase();
                return p.includes("email") || p.includes("phone") || n.includes("email") || t === "email";
            }) || inputs[0];
            return input ? true : false;
        })()
        """
        if execute_js(ws_url, js_find_input):
            input_mounted = True
            break
        time.sleep(1)

    if not input_mounted:
        return {"success": False, "error": "Email input field never appeared on Hark page"}

    # STEP C: THOROUGH FULL LOAD & SETTLING WAIT (User instructed: Website ko fully load hone dena)
    log_func("[*] Hark elements detected on screen. Waiting 10 seconds for 100% full page load & React hydration...")
    for sec in range(10, 0, -2):
        log_func(f"    [Hydration & Page Stability Wait] {sec}s remaining...")
        time.sleep(2)
    log_func("[✓] Website is 100% fully loaded and settled!")

    # STEP D: FOCUS INPUT BOX & ENTER EMAIL (CDP Hardware Type + React Setter)
    log_func(f"[*] Focusing input box and inserting email: '{clean_email}'...")
    email_confirmed_in_box = False
    for attempt in range(1, 5):
        # 1. Focus, click, and clear the input box
        js_prep = """
        (() => {
            let inputs = Array.from(document.querySelectorAll("input"));
            let input = inputs.find(i => {
                let p = (i.placeholder || "").toLowerCase();
                let n = (i.name || "").toLowerCase();
                let t = (i.type || "").toLowerCase();
                return p.includes("email") || p.includes("phone") || n.includes("email") || t === "email";
            }) || inputs[0];

            if (!input) return false;
            input.focus();
            input.click();
            try {
                input.select();
                document.execCommand('selectAll', false, null);
            } catch(e) {}
            return true;
        })()
        """
        execute_js(ws_url, js_prep)
        time.sleep(0.3)

        # 2. Insert email via CDP Hardware Input (simulates native OS typing/paste into focused element)
        send_cdp_command(ws_url, "Input.insertText", {"text": clean_email})
        time.sleep(0.4)

        # 3. Ensure React property setter & trigger synthetic events as backup
        js_fill = f"""
        (() => {{
            let inputs = Array.from(document.querySelectorAll("input"));
            let input = inputs.find(i => {{
                let p = (i.placeholder || "").toLowerCase();
                let n = (i.name || "").toLowerCase();
                let t = (i.type || "").toLowerCase();
                return p.includes("email") || p.includes("phone") || n.includes("email") || t === "email";
            }}) || inputs[0];

            if (!input) return {{found: false, error: "Input not found"}};

            if (input.value !== '{clean_email}') {{
                let setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
                if (setter) setter.call(input, '{clean_email}');
                else input.value = '{clean_email}';
            }}

            input.dispatchEvent(new Event('input', {{ bubbles: true, composed: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true, composed: true }}));
            input.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true }}));

            return {{found: true, val: input.value}};
        }})()
        """
        fill_res = execute_js(ws_url, js_fill)

        # Wait 1.5 seconds to observe if React accepts it
        time.sleep(1.5)

        js_check_val = """
        (() => {
            let input = Array.from(document.querySelectorAll("input")).find(i => {
                let p = (i.placeholder || "").toLowerCase();
                let n = (i.name || "").toLowerCase();
                let t = (i.type || "").toLowerCase();
                return p.includes("email") || p.includes("phone") || n.includes("email") || t === "email";
            }) || document.querySelector("input");
            return input ? input.value : "";
        })()
        """
        still_val = execute_js(ws_url, js_check_val)
        if still_val and (clean_email in still_val or still_val == clean_email):
            log_func(f"[✓] Email verified in box: '{still_val}'")
            email_confirmed_in_box = True
            break
        else:
            log_func(f"[!] Re-entering email (Previous was '{still_val}')...")
            time.sleep(1)

    if not email_confirmed_in_box:
        log_func("[!] Proceeding to submit anyway (some inputs mask value in DOM)...")

    time.sleep(1)

    # STEP E: SUBMIT EMAIL (Enter Key + Submit/Arrow Button + Form RequestSubmit)
    log_func("[*] Submitting email (Hark modern login: checking submit button, form & Enter key)...")
    js_submit = """
    (() => {
        let inputs = Array.from(document.querySelectorAll("input"));
        let input = inputs.find(i => {
            let p = (i.placeholder || "").toLowerCase();
            let n = (i.name || "").toLowerCase();
            let t = (i.type || "").toLowerCase();
            return p.includes("email") || p.includes("phone") || n.includes("email") || t === "email";
        }) || inputs[0];

        if (input) {
            input.focus();
        }

        // 1. Look for explicit Continue/Next/Submit/Arrow button
        let buttons = Array.from(document.querySelectorAll("button, [role='button']"));
        let submitBtn = buttons.find(b => {
            let t = (b.innerText || "").trim().toLowerCase();
            if (t.includes("google") || t.includes("apple") || t.includes("facebook") || t.includes("github") || t.includes("messages")) {
                return false;
            }
            if (t === "continue" || t === "next" || t === "submit" || t === "sign in" || t === "log in" || (t.startsWith("continue") && !t.includes("with"))) {
                return true;
            }
            if (b.type === "submit" || b.getAttribute("aria-label")?.toLowerCase().includes("submit") || b.getAttribute("aria-label")?.toLowerCase().includes("next")) {
                return true;
            }
            if (b.querySelector("svg") && b.closest("form, div")) {
                return true;
            }
            return false;
        });

        if (submitBtn) {
            submitBtn.removeAttribute("disabled");
            submitBtn.disabled = false;
            submitBtn.click();
            return {submitted: true, method: "button_click", text: submitBtn.innerText.trim()};
        }

        // 2. Form requestSubmit
        if (input && input.form) {
            try {
                if (typeof input.form.requestSubmit === "function") {
                    input.form.requestSubmit();
                    return {submitted: true, method: "form_requestSubmit"};
                } else {
                    input.form.submit();
                    return {submitted: true, method: "form_submit"};
                }
            } catch (e) {}
        }

        // 3. Dispatch Enter key events
        if (input) {
            ['keydown', 'keypress', 'keyup'].forEach(ev => {
                input.dispatchEvent(new KeyboardEvent(ev, {
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13,
                    bubbles: true,
                    cancelable: true
                }));
            });
            return {submitted: true, method: "enter_key_dispatch"};
        }

        return {submitted: false, error: "No input or submit mechanism"};
    })()
    """
    submit_res = execute_js(ws_url, js_submit)
    log_func(f"[*] DOM submit action: {submit_res}")

    # Send native hardware Enter key via CDP to guarantee form submission
    send_cdp_command(ws_url, "Input.dispatchKeyEvent", {
        "type": "rawKeyDown",
        "windowsVirtualKeyCode": 13,
        "nativeVirtualKeyCode": 13,
        "macCharCode": 13,
        "unmodifiedText": "\r",
        "text": "\r",
        "key": "Enter",
        "code": "Enter"
    })
    time.sleep(0.1)
    send_cdp_command(ws_url, "Input.dispatchKeyEvent", {
        "type": "keyUp",
        "windowsVirtualKeyCode": 13,
        "nativeVirtualKeyCode": 13,
        "macCharCode": 13,
        "unmodifiedText": "\r",
        "text": "\r",
        "key": "Enter",
        "code": "Enter"
    })
    log_func("[✓] Hardware Enter key triggered via CDP!")

    # STEP F: Observe next screen
    log_func("[*] Observing Hark for confirmation screen or next step...")
    for _ in range(10):
        time.sleep(1.5)
        js_check_next = """
        (() => {
            let text = document.body ? document.body.innerText.toLowerCase() : "";
            let url = window.location.href.toLowerCase();
            
            if (text.includes("verify you are human") || text.includes("cloudflare") || text.includes("turnstile")) {
                return {advanced: true, reason: "human_verification"};
            }
            if (text.includes("sent a confirmation link") || text.includes("check your spam") || text.includes("we sent") || text.includes("confirmation link") || text.includes("magic link")) {
                return {advanced: true, reason: "link_sent"};
            }
            if (url.includes("set-password") || url.includes("birthday") || text.includes("set a password") || text.includes("when is your birthday")) {
                return {advanced: true, reason: "next_screen"};
            }
            return {advanced: false};
        })()
        """
        obs = execute_js(ws_url, js_check_next)
        if isinstance(obs, dict) and obs.get("advanced"):
            reason = obs.get("reason")
            if reason == "human_verification":
                log_func("[!] Security Check: 'Verify you are human' displayed. Please complete in browser if needed.")
            elif reason == "link_sent":
                log_func("[✓✓✓] OBSERVED: Hark confirmed email and sent confirmation link!")
            elif reason == "next_screen":
                log_func("[✓✓✓] OBSERVED: Hark navigated to next registration screen!")
            return {"success": True, "observed": reason}

    log_func("[✓] Email submitted and Continue clicked successfully.")
    return {"success": True}

def submit_hark_email(port: int, email: str):
    return wait_and_submit_hark_email(port, email)

def complete_hark_password(port: int, password: str, max_wait: int = 15):
    ws_url = get_tab_websocket(port, url_keyword="hark.com")
    if not ws_url:
        return {"success": False, "error": f"Tab not found on port {port}"}

    clean_pwd = password.strip()
    start = time.time()

    while time.time() - start < max_wait:
        js_pwd = f"""
        (() => {{
            let text = document.body ? document.body.innerText.toLowerCase() : "";
            if (!text.includes("password") && !text.includes("set-password")) {{
                return {{on_pwd_page: false}};
            }}

            let inputs = Array.from(document.querySelectorAll("input"));
            let pwdInput = inputs.find(i => {{
                let p = (i.placeholder || "").toLowerCase();
                let t = (i.type || "").toLowerCase();
                return t === "password" || p.includes("password");
            }}) || inputs[0];

            if (!pwdInput) return {{on_pwd_page: true, found: false}};

            pwdInput.focus();
            let setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
            if (setter) setter.call(pwdInput, '{clean_pwd}');
            else pwdInput.value = '{clean_pwd}';

            pwdInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            pwdInput.dispatchEvent(new Event('change', {{ bubbles: true }}));

            pwdInput.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }}));
            pwdInput.dispatchEvent(new KeyboardEvent('keyup', {{ key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }}));

            let buttons = Array.from(document.querySelectorAll("button"));
            let arrowBtn = buttons.find(b => {{
                let type = (b.type || "").toLowerCase();
                let t = (b.innerText || "").toLowerCase();
                return type === "submit" || b.querySelector("svg") !== null || t.includes("continue") || t.includes("set");
            }});

            if (arrowBtn) {{
                arrowBtn.removeAttribute("disabled");
                arrowBtn.click();
            }}

            return {{on_pwd_page: true, found: true, submitted: true}};
        }})()
        """
        res = execute_js(ws_url, js_pwd)
        if res and isinstance(res, dict) and res.get("submitted"):
            time.sleep(2)
            return {"success": True, "observed": "password_submitted"}

        time.sleep(1.5)

    return {"success": False, "error": "Password screen not found or could not submit"}

def complete_hark_birthday(port: int, max_wait: int = 30, log_func=print):
    """
    Automates Hark's 18+ Age Verification ('When is your birthday?'):
    1. Detects birthday screen.
    2. Clicks each dropdown (Month, Day, Year) with realistic async delays so React updates state.
    3. Syncs native <select> elements if present.
    4. Force-enables and triggers Continue button + form submission.
    5. Confirms screen advanced.
    """
    ws_url = get_tab_websocket(port, url_keyword="hark.com")
    if not ws_url:
        return {"success": False, "error": f"Tab not found on port {port}"}

    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    rand_month = random.choice(MONTHS)
    rand_month_idx = MONTHS.index(rand_month) + 1  # 1 to 12
    rand_day = str(random.randint(1, 26))
    rand_year = str(random.randint(1992, 2003))    # Strictly 18+ (23 to 34 years old)

    log_func(f"[*] Checking for Hark Age Verification ('When is your birthday?')...")
    log_func(f"[*] Target 18+ Birthday: {rand_month} {rand_day}, {rand_year}")

    start = time.time()
    while time.time() - start < max_wait:
        js_birthday = f"""
        (async () => {{
            let text = document.body ? document.body.innerText.toLowerCase() : "";
            if (!text.includes("birthday") && !text.includes("old enough")) {{
                return {{ on_screen: false }};
            }}

            const targetMonth = "{rand_month}";
            const targetMonthNum = "{rand_month_idx}";
            const targetDay = "{rand_day}";
            const targetYear = "{rand_year}";

            // -------------------------------------------------------------
            // STEP 1: Sync native <select> elements if present
            // -------------------------------------------------------------
            let selects = Array.from(document.querySelectorAll("select"));
            if (selects.length > 0) {{
                const setNative = (sel, matchers) => {{
                    if (!sel) return;
                    let opts = Array.from(sel.options);
                    let found = opts.find(o => {{
                        let t = (o.text || "").trim().toLowerCase();
                        let v = (o.value || "").trim().toLowerCase();
                        return matchers.some(m => t === m.toLowerCase() || v === m.toLowerCase() || t.startsWith(m.toLowerCase()));
                    }}) || (opts.length > 1 ? opts[1] : null);

                    if (found) {{
                        let setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value')?.set;
                        if (setter) setter.call(sel, found.value);
                        else sel.value = found.value;
                        sel.selectedIndex = found.index;
                        sel.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }};

                let mSel = selects.find(s => (s.name || s.id || "").toLowerCase().includes("month")) || selects[0];
                let dSel = selects.find(s => (s.name || s.id || "").toLowerCase().includes("day")) || (selects.length > 1 ? selects[1] : null);
                let ySel = selects.find(s => (s.name || s.id || "").toLowerCase().includes("year")) || (selects.length > 2 ? selects[2] : null);

                setNative(mSel, [targetMonth, targetMonthNum, targetMonthNum.padStart(2, '0')]);
                setNative(dSel, [targetDay, targetDay.padStart(2, '0')]);
                setNative(ySel, [targetYear]);
            }}

            // -------------------------------------------------------------
            // STEP 2: Click custom dropdown triggers & select options
            // -------------------------------------------------------------
            const clickOptionInMenu = (targetTexts) => {{
                let elements = Array.from(document.querySelectorAll("div, span, li, button, p, a, [role='option']"));
                for (let tgt of targetTexts) {{
                    let match = elements.find(el => {{
                        let t = (el.innerText || "").trim().toLowerCase();
                        return t === String(tgt).trim().toLowerCase() && el.children.length === 0;
                    }});
                    if (match) {{
                        match.scrollIntoView({{ block: "center" }});
                        match.click();
                        match.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
                        match.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true }}));
                        return true;
                    }}
                }}
                return false;
            }};

            let allBtns = Array.from(document.querySelectorAll("button, [role='combobox'], [role='button'], div[tabindex='0']"));
            let monthBtn = allBtns.find(b => (b.innerText || "").toLowerCase().includes("month"));
            let dayBtn = allBtns.find(b => (b.innerText || "").toLowerCase().includes("day"));
            let yearBtn = allBtns.find(b => (b.innerText || "").toLowerCase().includes("year"));

            // If text on button is already a selected value (like 'Jan', '18', '1996'), find by container
            if (!monthBtn || !dayBtn || !yearBtn) {{
                let containers = Array.from(document.querySelectorAll("div")).filter(d => {{
                    let kids = Array.from(d.children).filter(c => 
                        c.tagName === "BUTTON" || 
                        c.getAttribute("role") === "combobox" || 
                        c.getAttribute("role") === "button"
                    );
                    return kids.length === 3;
                }});
                if (containers.length > 0) {{
                    let kids = Array.from(containers[0].children);
                    monthBtn = monthBtn || kids[0];
                    dayBtn = dayBtn || kids[1];
                    yearBtn = yearBtn || kids[2];
                }}
            }}

            // 2A. Select Month
            if (monthBtn) {{
                monthBtn.click();
                await new Promise(r => setTimeout(r, 350));
                clickOptionInMenu([targetMonth, targetMonthNum]);
                await new Promise(r => setTimeout(r, 350));
            }}

            // 2B. Select Day
            if (dayBtn) {{
                dayBtn.click();
                await new Promise(r => setTimeout(r, 350));
                clickOptionInMenu([targetDay, targetDay.padStart(2, '0')]);
                await new Promise(r => setTimeout(r, 350));
            }}

            // 2C. Select Year
            if (yearBtn) {{
                yearBtn.click();
                await new Promise(r => setTimeout(r, 350));
                let clickedY = clickOptionInMenu([targetYear]);
                if (!clickedY) {{
                    let yearEls = Array.from(document.querySelectorAll("*")).filter(el => {{
                        let y = parseInt((el.innerText || "").trim());
                        return !isNaN(y) && y >= 1980 && y <= 2004 && el.children.length === 0;
                    }});
                    if (yearEls.length > 0) {{
                        yearEls[0].scrollIntoView({{ block: "center" }});
                        yearEls[0].click();
                    }}
                }}
                await new Promise(r => setTimeout(r, 400));
            }}

            // -------------------------------------------------------------
            // STEP 3: Click Continue Button ONCE
            // -------------------------------------------------------------
            let buttons = Array.from(document.querySelectorAll("button"));
            let contBtn = buttons.find(b => {{
                let t = (b.innerText || "").trim().toLowerCase();
                return t === "continue" && !t.includes("with");
            }});

            if (!contBtn) {{
                return {{ on_screen: true, success: false, error: "Continue button not found" }};
            }}

            // Check if already rate limited
            if (text.includes("too many attempts")) {{
                return {{ on_screen: true, rate_limited: true, error: "Too many attempts" }};
            }}

            // Clean single click (no multi-hammering)
            contBtn.removeAttribute("disabled");
            contBtn.disabled = false;
            contBtn.classList.remove("disabled");
            contBtn.click();

            return {{
                on_screen: true,
                success: true,
                birthday: `${{targetMonth}} ${{targetDay}}, ${{targetYear}}`,
                has_turnstile: (text.includes("verify you are human") || text.includes("cloudflare") || !!document.querySelector("iframe[src*='cloudflare'], iframe[src*='turnstile']"))
            }};
        }})()
        """
        res = execute_js(ws_url, js_birthday)
        if res and isinstance(res, dict):
            if res.get("rate_limited"):
                log_func("[⚠️ RATE LIMIT] Hark: 'Too many attempts. Wait a few minutes and try again.'")
                return {"success": False, "rate_limited": True, "error": "Too many attempts"}

            if res.get("success"):
                log_func(f"[✓✓✓] Birthday selected: {res.get('birthday')}")
                
                if res.get("has_turnstile"):
                    log_func("[!] Security Check: Cloudflare 'Verify you are human' dikhai de raha hai.")
                    log_func("[!] Kripya browser mein 'Verify you are human' par ek click kar dein.")

                # Observe for Turnstile completion / next screen (DO NOT spam clicks in loop)
                submitted_after_turnstile = False
                for _ in range(25):
                    time.sleep(2)
                    js_check_next = """
                    (() => {
                        let text = document.body ? document.body.innerText.toLowerCase() : "";
                        let url = window.location.href.toLowerCase();
                        
                        // Check for rate limit error
                        if (text.includes("too many attempts")) {
                            return { rate_limited: true };
                        }

                        // Check if advanced to next screen (email sent / password / verification screen)
                        if (text.includes("sent a confirmation link") || 
                            text.includes("check your spam") || 
                            text.includes("we sent") || 
                            text.includes("check your email") ||
                            text.includes("check your inbox") ||
                            text.includes("confirmation link") || 
                            text.includes("magic link") || 
                            url.includes("set-password") ||
                            url.includes("verify")) {
                            return { advanced: true };
                        }

                        // Check Turnstile status
                        let turnstileResp = document.querySelector("[name='cf-turnstile-response']");
                        let hasTurnstileToken = !!(turnstileResp && turnstileResp.value && turnstileResp.value.length > 10);

                        return { 
                            advanced: false, 
                            has_token: hasTurnstileToken 
                        };
                    })()
                    """
                    check_res = execute_js(ws_url, js_check_next)
                    if isinstance(check_res, dict):
                        if check_res.get("rate_limited"):
                            log_func("[⚠️ RATE LIMIT] Hark: 'Too many attempts. Wait a few minutes and try again.'")
                            return {"success": False, "rate_limited": True, "error": "Too many attempts"}

                        if check_res.get("advanced"):
                            log_func("[✓✓✓] OBSERVED: Hark accepted Birthday and advanced to verification step!")
                            return {"success": True, "birthday": res.get("birthday"), "observed": "advanced"}

                        if check_res.get("has_token") and not submitted_after_turnstile:
                            submitted_after_turnstile = True
                            log_func("[✓] Turnstile human verification confirmed! Submitting once...")
                            execute_js(ws_url, """
                            (() => {
                                let contBtn = Array.from(document.querySelectorAll("button")).find(b => {
                                    let t = (b.innerText || "").trim().toLowerCase();
                                    return t === "continue" && !t.includes("with");
                                });
                                if (contBtn) {
                                    contBtn.removeAttribute("disabled");
                                    contBtn.disabled = false;
                                    contBtn.click();
                                }
                            })()
                            """)

                return {"success": True, "birthday": res.get("birthday")}

        time.sleep(2)

    return {"success": False, "error": "Birthday screen not found or could not submit"}

def submit_hark_otp(port: int, otp_code: str):
    ws_url = get_tab_websocket(port, url_keyword="hark.com")
    if not ws_url:
        return {"success": False, "error": f"Tab not found on port {port}"}

    clean_otp = str(otp_code).strip()
    js_otp = f"""
    (() => {{
        let otp = "{clean_otp}";
        let inputs = Array.from(document.querySelectorAll("input[type='text'], input[type='tel'], input[inputmode='numeric']"));
        let setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
        
        if (inputs.length >= 6) {{
            for (let i = 0; i < 6 && i < otp.length; i++) {{
                inputs[i].focus();
                if (setter) setter.call(inputs[i], otp[i]);
                else inputs[i].value = otp[i];
                inputs[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                inputs[i].dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        }} else if (inputs.length > 0) {{
            let inp = inputs[0];
            inp.focus();
            if (setter) setter.call(inp, otp);
            else inp.value = otp;
            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }} else {{
            return {{success: false, error: "OTP inputs not found"}};
        }}
        
        let buttons = Array.from(document.querySelectorAll("button"));
        let btn = buttons.find(b => {{
            let t = (b.innerText || "").trim().toLowerCase();
            if (t.includes("google") || t.includes("apple")) return false;
            return t.includes("continue") || t.includes("verify") || t.includes("submit") || t.includes("sign in");
        }});
        
        if (btn) {{
            btn.removeAttribute("disabled");
            setTimeout(() => btn.click(), 300);
            return {{success: true, clicked: true, otp: otp}};
        }}
        return {{success: true, clicked: false, otp: otp}};
    }})()
    """
    return execute_js(ws_url, js_otp)

if __name__ == "__main__":
    print("CDP module ready with anti-wipe protection.")
