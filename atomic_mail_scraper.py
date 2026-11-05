"""
Atomic Mail Scraper via Chrome DevTools Protocol (CDP) on Port 9333
Extracts the exact Magic Confirmation Link (auth.hark.com/api/auth/magic-link/verify?token=...)
"""

import os
import time
import re
import subprocess
import cdp_automation as cdp
import profile_manager as pm

MASTER_PORT = 9333
MASTER_PROFILE_DIR = os.path.abspath(os.path.join(pm.PROFILES_DIR, "atomic_mail_master"))

def launch_master_atomic_mail(pos=None, size=None):
    os.makedirs(MASTER_PROFILE_DIR, exist_ok=True)
    chrome_exe = pm.get_chrome_path()
    cfg = pm.load_config()
    mail_url = cfg.get("mail_provider_url", "https://atomicmail.io/app/mailbox/")

    args = [
        chrome_exe,
        f"--user-data-dir={MASTER_PROFILE_DIR}",
        f"--remote-debugging-port={MASTER_PORT}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    if pos and size:
        args.append(f"--window-position={pos[0]},{pos[1]}")
        args.append(f"--window-size={size[0]},{size[1]}")
    args.append(mail_url)
    proc = subprocess.Popen(args)
    pm.active_profile_ports[MASTER_PORT] = proc
    return proc

def get_atomic_mailbox_state():
    """
    Inspects Atomic Mail on Port 9333.
    Returns:
    - current_id: integer message ID currently open (e.g. 93)
    - max_id: highest message ID detected in the mailbox (e.g. 94)
    - mailbox_base: base mailbox URL
    - magic_link: Hark magic link if already present on open page
    """
    ws_url = cdp.get_tab_websocket(MASTER_PORT, url_keyword="atomicmail.io", timeout=4)
    if not ws_url:
        ws_url = cdp.get_tab_websocket(MASTER_PORT, url_keyword="", timeout=3)
    if not ws_url:
        return None

    js_state = r"""
    (() => {
        let url = window.location.href;
        
        // 1. Current message ID from URL: /message/93 -> 93
        let curMatch = url.match(/\/message\/(\d+)/);
        let current_id = curMatch ? parseInt(curMatch[1]) : 0;
        
        // 2. Mailbox base URL
        let mbMatch = url.match(/(https?:\\/\\/[^\\/]+\\/app\\/mailbox\\/[a-zA-Z0-9_-]+)/);
        let mailbox_base = mbMatch ? mbMatch[1] : null;

        // 3. Scan all message links in sidebar / inbox
        let anchors = Array.from(document.querySelectorAll("a[href*='/message/']"));
        let found_ids = [];
        anchors.forEach(a => {
            let m = a.href.match(/\/message\/(\d+)/);
            if (m) {
                let id = parseInt(m[1]);
                found_ids.push({ id: id, href: a.href });
            }
        });

        // 4. Determine max message ID
        let max_id = current_id;
        found_ids.forEach(x => {
            if (x.id > max_id) max_id = x.id;
        });

        // 5. Extract Hark Magic Link from currently open message
        let html = document.body ? document.body.innerHTML : "";
        let regex = /https?:\\/\\/[a-zA-Z0-9_.-]*hark\\.com\\/api\\/auth\\/magic-link\\/verify\\?[^"\'\\s<>]+/gi;
        let matches = html.match(regex);
        let magic_link = null;
        if (matches && matches.length > 0) {
            magic_link = matches[0].replace(/&amp;/g, '&').replace(/[.,;)\\]]+$/, '');
        }
        if (!magic_link) {
            let allA = Array.from(document.querySelectorAll("a"));
            let fA = allA.find(a => (a.href || "").includes("magic-link/verify") || ((a.href || "").includes("hark.com") && (a.href || "").includes("token=")));
            if (fA) magic_link = fA.href;
        }

        return {
            url: url,
            current_id: current_id,
            max_id: max_id,
            mailbox_base: mailbox_base,
            found_count: found_ids.length,
            magic_link: magic_link
        };
    })()
    """
    return cdp.execute_js(ws_url, js_state)

def fetch_incremental_hark_link(last_msg_id=None, timeout=60, log_func=print):
    """
    Auto-detects the NEXT incoming Hark email based on incremental message numbering (e.g. 93 -> 94 -> 95).
    Extracts the exact magic link circled in yellow:
    https://auth.eu.hark.com/api/auth/magic-link/verify?token=...
    """
    log_func(f"[*] Monitoring Atomic Mail for incoming Hark link (Last Message ID: {last_msg_id or 'Auto'})...")
    
    ws_url = cdp.get_tab_websocket(MASTER_PORT, url_keyword="atomicmail.io", timeout=6)
    if not ws_url:
        ws_url = cdp.get_tab_websocket(MASTER_PORT, url_keyword="", timeout=4)
    if not ws_url:
        log_func(f"[!] Atomic Mail window not found on Port {MASTER_PORT}. Please click '📬 Open Atomic Mail' first!")
        return None

    baseline_id = last_msg_id
    if baseline_id is None:
        initial_state = get_atomic_mailbox_state()
        if initial_state and isinstance(initial_state, dict):
            baseline_id = initial_state.get("max_id") or initial_state.get("current_id") or 0
        else:
            baseline_id = 0

    log_func(f"[*] Baseline Message ID: {baseline_id}. Waiting for new message #{baseline_id + 1}...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        state = get_atomic_mailbox_state()
        if state and isinstance(state, dict):
            current_id = state.get("current_id", 0)
            max_id = state.get("max_id", 0)
            mailbox_base = state.get("mailbox_base")

            # Case A: A newer message number arrived (e.g. 94 > 93)
            if max_id > baseline_id:
                target_msg_id = max_id
                log_func(f"[✓] Detected NEW message #{target_msg_id} in Atomic Mail (Incremented from #{baseline_id})!")

                # If not currently on that message, navigate to it
                if current_id != target_msg_id and mailbox_base:
                    target_url = f"{mailbox_base}/message/{target_msg_id}"
                    log_func(f"[*] Opening message #{target_msg_id}: {target_url}...")
                    cdp.send_cdp_command(ws_url, "Page.navigate", {"url": target_url})
                    time.sleep(2.5)
                    state = get_atomic_mailbox_state()

                # Extract magic link from the new message
                link = state.get("magic_link") if state else None
                if link:
                    log_func("\n" + "=" * 60)
                    log_func(f"[✓✓✓] CAPTURED HARK MAGIC LINK FROM MESSAGE #{target_msg_id}!")
                    log_func(f"[*] URL: {link}")
                    log_func("=" * 60)
                    return {
                        "success": True,
                        "magic_link": link,
                        "message_id": target_msg_id
                    }

            # Case B: Already on a message that has the link and we didn't have baseline
            elif state.get("magic_link") and (baseline_id == 0 or current_id > baseline_id):
                link = state.get("magic_link")
                log_func(f"[✓✓✓] Captured Hark Magic Link from open message #{current_id}: {link}")
                return {
                    "success": True,
                    "magic_link": link,
                    "message_id": current_id
                }

        # Click top email row to refresh / open newest mail
        js_click_top = """
        (() => {
            let anchors = Array.from(document.querySelectorAll("a[href*='/message/']"));
            if (anchors.length > 0) {
                anchors[0].click();
                return true;
            }
            let rows = Array.from(document.querySelectorAll("div[class*='item'], div[class*='mail'], tr"));
            let harkRow = rows.find(r => (r.innerText || "").toLowerCase().includes("hark"));
            if (harkRow) { harkRow.click(); return true; }
            return false;
        })()
        """
        cdp.execute_js(ws_url, js_click_top)
        time.sleep(2)

    log_func(f"[!] Timeout: Message #{baseline_id + 1} did not arrive in Atomic Mail within {timeout}s.")
    return None

def fetch_latest_atomic_verification(timeout=65, log_func=print):
    """
    Backward-compatible alias for incremental link fetcher.
    """
    return fetch_incremental_hark_link(last_msg_id=None, timeout=timeout, log_func=log_func)

if __name__ == "__main__":
    print("Atomic Mail scraper loaded.")
