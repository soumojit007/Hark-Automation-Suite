"""
Chrome Profile Manager for Hark Automation
Manages isolated profiles, success records, failed records, and deduplication.
"""

import os
import sys
import json
import csv
import subprocess
import ctypes
import urllib.request
import urllib.error
import socket
import threading
import time
from datetime import datetime

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
]

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.json")
ACCOUNTS_TXT = os.path.join(BASE_DIR, "accounts.txt")
SUCCESS_FILE = os.path.join(BASE_DIR, "success_accounts.json")
SUCCESS_TXT = os.path.join(BASE_DIR, "success_accounts.txt")
FAILED_FILE = os.path.join(BASE_DIR, "failed_accounts.json")
FAILED_TXT = os.path.join(BASE_DIR, "failed_accounts.txt")
USED_EMAILS_FILE = os.path.join(BASE_DIR, "used_emails.txt")

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
PROFILES_DIR = os.path.join(BASE_DIR, "profiles")

DEFAULT_CONFIG = {
    "mail_provider_url": "https://atomicmail.io/app/mailbox/",
    "target_url": "https://hark.com",
    "base_email": "soumojm123@atomicmail.io",
    "default_password": "HarkPassword2026!",
    "aliasing_strategy": ".method (Dot Trick)",
    "accounts_count": 5
}

active_hark_processes = []
active_profile_ports = {}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

def get_chrome_path():
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    return "chrome.exe"

def load_json_file(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_json_file(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_accounts():
    return load_json_file(ACCOUNTS_FILE)

def save_accounts(accounts):
    save_json_file(ACCOUNTS_FILE, accounts)
    sync_accounts_txt(accounts)

def sync_accounts_txt(accounts):
    with open(ACCOUNTS_TXT, "w", encoding="utf-8") as f:
        for acc in accounts:
            note_str = f" | Note: {acc.get('note', '')}" if acc.get('note') else ""
            f.write(f"#{acc.get('id', '')} - {acc.get('email', '')} | Password: {acc.get('password', '')} | Port: {acc.get('port', '')} | Status: {acc.get('status', '')}{note_str} | Created: {acc.get('created_at', '')}\n")

def record_success(email, password, port, profile_path):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    success_list = load_json_file(SUCCESS_FILE)
    
    # Avoid duplicates in success
    existing = next((s for s in success_list if s["email"].lower() == email.lower()), None)
    if not existing:
        new_entry = {
            "id": len(success_list) + 1,
            "email": email,
            "password": password,
            "port": port,
            "profile_path": profile_path,
            "status": "✅ SUCCESSFUL",
            "created_at": now_str
        }
        success_list.append(new_entry)
        save_json_file(SUCCESS_FILE, success_list)
        
        # Sync success.txt
        with open(SUCCESS_TXT, "a", encoding="utf-8") as f:
            f.write(f"[✅ SUCCESSFUL] {email} | Password: {password} | Port: {port} | Date: {now_str}\n")

    # Update in accounts.json as well so GUI displays ✅ SUCCESSFUL
    accounts = load_accounts()
    for acc in accounts:
        if acc.get("email", "").lower() == email.lower():
            acc["status"] = "✅ SUCCESSFUL"
            acc["password"] = password
            acc["last_active"] = now_str
    save_accounts(accounts)

    # Remove from failed list if present
    failed_list = [f for f in load_json_file(FAILED_FILE) if f.get("email", "").lower() != email.lower()]
    save_json_file(FAILED_FILE, failed_list)

def record_failure(email, reason):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    failed_list = load_json_file(FAILED_FILE)
    
    existing = next((f for f in failed_list if f["email"].lower() == email.lower()), None)
    if existing:
        existing["reason"] = reason
        existing["failed_at"] = now_str
    else:
        new_entry = {
            "id": len(failed_list) + 1,
            "email": email,
            "reason": reason,
            "status": "FAILED",
            "failed_at": now_str
        }
        failed_list.append(new_entry)
        
    save_json_file(FAILED_FILE, failed_list)
    
    with open(FAILED_TXT, "a", encoding="utf-8") as f:
        f.write(f"[FAILED] {email} | Reason: {reason} | Date: {now_str}\n")

def mark_email_as_used(email):
    """
    Persistently records an email as used so it is NEVER generated again.
    """
    clean = email.strip().lower()
    if not clean:
        return
    used = get_all_used_emails()
    if clean not in used:
        with open(USED_EMAILS_FILE, "a", encoding="utf-8") as f:
            f.write(clean + "\n")

def get_all_used_emails():
    """
    Returns a set of all emails that have ever been used (successful + accounts + failed + used_emails.txt).
    """
    used = set()
    if os.path.exists(USED_EMAILS_FILE):
        try:
            with open(USED_EMAILS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    em = line.strip().lower()
                    if em:
                        used.add(em)
        except Exception:
            pass

    for acc in load_accounts():
        if acc.get("email"):
            used.add(acc["email"].strip().lower())
    for s in load_json_file(SUCCESS_FILE):
        if s.get("email"):
            used.add(s["email"].strip().lower())
    for f in load_json_file(FAILED_FILE):
        if f.get("email"):
            used.add(f["email"].strip().lower())
    return used

def export_to_csv(filepath="accounts_export.csv"):
    accounts = load_accounts()
    if not accounts:
        return False
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["id", "email", "password", "port", "status", "note", "created_at", "last_active", "profile_path"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for acc in accounts:
            writer.writerow(acc)
    return True

def update_account_note(account_id: int, note: str):
    accounts = load_accounts()
    for a in accounts:
        if a.get("id") == account_id:
            a["note"] = note.strip()
            save_accounts(accounts)
            return True
    return False

def get_next_profile_info():
    """
    Finds the absolute maximum profile number across accounts.json and profiles/ directory.
    Guarantees a 100% fresh, unused, clean profile folder so old accounts are NEVER touched.
    """
    accounts = load_accounts()
    existing_ids = [a.get("id", 0) for a in accounts if isinstance(a.get("id"), int)]
    
    # Check disk folders in profiles/
    if os.path.exists(PROFILES_DIR):
        for item in os.listdir(PROFILES_DIR):
            if item.startswith("profile_"):
                try:
                    num = int(item.replace("profile_", ""))
                    existing_ids.append(num)
                except ValueError:
                    pass

    next_id = max(existing_ids, default=0) + 1
    next_port = 9400 + (next_id % 500)
    profile_path = os.path.join(PROFILES_DIR, f"profile_{next_id}")
    os.makedirs(profile_path, exist_ok=True)
    return next_id, next_port, profile_path

def add_account(email: str, status="In Progress...", password="", note=""):
    """
    Creates a new account entry with a brand new, unused Chrome profile.
    If an existing account is already marked SUCCESSFUL, it will NOT be touched.
    """
    accounts = load_accounts()
    clean_email = email.strip().lower()
    
    # Check if already successful: if so, leave it alone!
    for a in accounts:
        if a.get("email", "").lower() == clean_email:
            st = a.get("status", "").upper()
            if "SUCCESS" in st:
                # Do NOT touch or overwrite existing successful accounts!
                if note and not a.get("note"):
                    a["note"] = note
                    save_accounts(accounts)
                return a
            else:
                a["status"] = status
                if password:
                    a["password"] = password
                if note:
                    a["note"] = note
                a["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_accounts(accounts)
                return a

    acc_id, port, profile_path = get_next_profile_info()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_acc = {
        "id": acc_id,
        "email": email,
        "password": password,
        "port": port,
        "status": status,
        "note": note,
        "created_at": now_str,
        "last_active": now_str,
        "profile_path": profile_path
    }
    accounts.append(new_acc)
    save_accounts(accounts)
    return new_acc

def close_active_hark_windows():
    global active_hark_processes, active_profile_ports
    for proc in list(active_hark_processes):
        try:
            proc.terminate()
        except Exception:
            pass
    active_hark_processes.clear()
    active_profile_ports.clear()

def launch_chrome_profile(account_id: int = None, url="https://hark.com", profile_path=None, port=None, pos=None, size=None, close_previous=False):
    global active_hark_processes, active_profile_ports
    if close_previous:
        close_active_hark_windows()

    if account_id is not None:
        accounts = load_accounts()
        target_acc = next((a for a in accounts if a["id"] == account_id), None)
        if target_acc:
            profile_path = target_acc["profile_path"]
            port = target_acc["port"]

    if not profile_path or not port:
        return False

    profile_path = os.path.abspath(profile_path)
    os.makedirs(profile_path, exist_ok=True)

    chrome_exe = get_chrome_path()

    args = [
        chrome_exe,
        f"--user-data-dir={profile_path}",
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check"
    ]

    if pos and size:
        args.append(f"--window-position={pos[0]},{pos[1]}")
        args.append(f"--window-size={size[0]},{size[1]}")

    args.append(url)
    proc = subprocess.Popen(args)
    active_hark_processes.append(proc)
    if port:
        active_profile_ports[int(port)] = proc
    return proc

def get_screen_tiled_layout(hark_count=2, with_top_mail=True):
    """
    Fixed Clean 3-Window Layout (Exact as User Drawing):
    - Top: Mail window (Width = 100%, Height = 32%)
    - Bottom Left: Hark Window 1 (Width = 50%, Height = 68%)
    - Bottom Right: Hark Window 2 (Width = 50%, Height = 68%)
    """
    try:
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1) - 40 # exclude Windows taskbar
    except Exception:
        sw, sh = 1920, 1040

    if with_top_mail:
        mail_h = max(260, int(sh * 0.32))
        mail_slot = {"pos": (0, 0), "size": (sw, mail_h)}
        hark_y = mail_h
        avail_h = sh - mail_h
    else:
        mail_slot = None
        hark_y = 0
        avail_h = sh

    w = sw // 2
    slots = [
        {"pos": (0, hark_y), "size": (w, avail_h)},
        {"pos": (w, hark_y), "size": (sw - w, avail_h)}
    ]

    return {
        "mail": mail_slot,
        "hark_slots": slots
    }

def get_screen_half_dimensions():
    """
    Returns (x, y, w, h) for Window 1 (Bottom Left) and Window 2 (Bottom Right)
    placed cleanly below the Top Mail window.
    """
    layout = get_screen_tiled_layout(hark_count=2, with_top_mail=True)
    s1 = layout["hark_slots"][0]
    s2 = layout["hark_slots"][1]
    return [
        (s1["pos"][0], s1["pos"][1], s1["size"][0], s1["size"][1]),
        (s2["pos"][0], s2["pos"][1], s2["size"][0], s2["size"][1])
    ]

def auto_align_windows(hark_count=None):
    return True

def schedule_auto_align(hark_count=None, retries=5, interval=0.6):
    pass

def is_window_alive(port, proc=None):
    if not port:
        return False
    try:
        port_int = int(port)
    except Exception:
        return False

    p = proc or active_profile_ports.get(port_int)
    if p is not None:
        if p.poll() is None:
            return True
        active_profile_ports.pop(port_int, None)
        return False
    return False

def close_window_by_port(port):
    """
    Closes a specific Chrome profile window immediately without blocking the UI.
    """
    if not port:
        return False
    try:
        port_int = int(port)
    except Exception:
        return False

    proc = active_profile_ports.pop(port_int, None)
    if proc:
        try:
            proc.terminate()
            return True
        except Exception:
            pass
    return False

def launch_tiled_windows(count=5, url="https://hark.com"):
    accounts = load_accounts()
    if not accounts:
        return False

    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1) - 40

    limit = min(count, len(accounts))
    rows = 2 if limit > 3 else 1
    cols_top = 3 if limit > 3 else limit
    cols_bottom = limit - cols_top

    w_top = screen_w // cols_top
    h_top = screen_h // rows

    for i in range(limit):
        acc = accounts[i]
        if i < cols_top:
            x = i * w_top
            y = 0
            w = w_top
            h = h_top
        else:
            w_bot = screen_w // max(1, cols_bottom)
            x = (i - cols_top) * w_bot
            y = h_top
            w = w_bot
            h = h_top

        launch_chrome_profile(acc["id"], url=url, pos=(x, y), size=(w, h))

    return True

if __name__ == "__main__":
    print("Profile manager ready. Used emails:", len(get_all_used_emails()))
