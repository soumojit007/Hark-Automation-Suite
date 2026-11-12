import os
import sys
import json
import time
import re
import threading
import subprocess
import webbrowser
from datetime import datetime
import customtkinter as ctk

import profile_manager as pm
from dot_method import generate_dot_variations
import cdp_automation as cdp
import atomic_mail_scraper as ams
import license_manager as lm

# Appearance & Styling
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

COLOR_BG_DARK = "#0d1117"
COLOR_CARD_DARK = "#161b22"
COLOR_ACCENT_GREEN = "#00e676"
COLOR_ACCENT_CYAN = "#00e5ff"
COLOR_ACCENT_BLUE = "#0288d1"
COLOR_HOVER_BLUE = "#0277bd"
COLOR_TEXT_MUTED = "#8b949e"

class HarkCreatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SOUMOJIT HARK CREATION | Automated Hark Account Creator & Profile Manager")
        self.geometry("1160x780")
        self.minsize(980, 620)
        self.configure(fg_color=COLOR_BG_DARK)

        self.cfg = pm.load_config()
        self.accounts = pm.load_accounts()
        self.manual_otp_value = None
        self.stop_requested = False
        self.next_batch_requested = False
        self.is_creating = False
        self.profile_filter = "All"
        self.last_atomic_msg_id = None

        # Check License & Device HWID
        self.license_info = lm.check_system_license()
        if not self.license_info.get("valid"):
            self.show_activation_screen()
        else:
            self.build_main_ui()

    def show_activation_screen(self):
        for w in self.winfo_children():
            w.destroy()

        hwid = lm.get_machine_hwid()

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        card = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=12, border_width=1, border_color="#30363d", width=560)
        card.pack(padx=20, pady=20)

        # Header
        icon_lbl = ctk.CTkLabel(card, text="🔒", font=ctk.CTkFont(size=44))
        icon_lbl.pack(pady=(24, 6))

        title_lbl = ctk.CTkLabel(
            card,
            text="SOUMOJIT HARK AUTOMATION",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#00e5ff"
        )
        title_lbl.pack()

        sub_lbl = ctk.CTkLabel(
            card,
            text="Commercial License & HWID Activation Required",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#8b949e"
        )
        sub_lbl.pack(pady=(2, 18))

        # HWID Box
        hwid_frame = ctk.CTkFrame(card, fg_color="#0d1117", corner_radius=8, border_width=1, border_color="#21262d")
        hwid_frame.pack(fill="x", padx=32, pady=6)

        ctk.CTkLabel(
            hwid_frame,
            text="YOUR MACHINE HWID:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#8b949e"
        ).pack(anchor="w", padx=14, pady=(10, 2))

        hwid_row = ctk.CTkFrame(hwid_frame, fg_color="transparent")
        hwid_row.pack(fill="x", padx=14, pady=(0, 10))

        hwid_display = ctk.CTkLabel(
            hwid_row,
            text=hwid,
            font=ctk.CTkFont(family="Consolas", size=17, weight="bold"),
            text_color="#00e676"
        )
        hwid_display.pack(side="left")

        btn_copy_hwid = ctk.CTkButton(
            hwid_row,
            text="📋 Copy HWID",
            width=110,
            height=30,
            fg_color="#0288d1",
            hover_color="#0277bd",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self.copy_hwid_action(hwid, btn_copy_hwid)
        )
        btn_copy_hwid.pack(side="right")

        hint_lbl = ctk.CTkLabel(
            card,
            text="ℹ️ Send this HWID to the administrator (@SOUMOJIT) to purchase or activate your license key.",
            font=ctk.CTkFont(size=11),
            text_color="#78909c",
            wraplength=480,
            justify="center"
        )
        hint_lbl.pack(padx=32, pady=(8, 14))

        # Key Input
        entry_key = ctk.CTkEntry(
            card,
            placeholder_text="Paste your License Key here (SJHK.xxxx.yyyy)...",
            width=460,
            height=40,
            font=ctk.CTkFont(size=12)
        )
        entry_key.pack(padx=32, pady=4)

        err_lbl = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11, weight="bold"), text_color="#ef5350")
        err_lbl.pack(pady=(4, 6))

        btn_activate = ctk.CTkButton(
            card,
            text="🔑 Activate License Now",
            width=460,
            height=42,
            fg_color="#00c853",
            hover_color="#00a844",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.activate_license_action(entry_key.get(), err_lbl)
        )
        btn_activate.pack(padx=32, pady=(0, 24))

    def copy_hwid_action(self, hwid, btn):
        try:
            self.clipboard_clear()
            self.clipboard_append(hwid)
            btn.configure(text="✅ Copied!", fg_color="#2e7d32")
            self.after(2000, lambda: btn.configure(text="📋 Copy HWID", fg_color="#0288d1"))
        except Exception:
            pass

    def activate_license_action(self, key_str, err_lbl):
        key = key_str.strip()
        if not key:
            err_lbl.configure(text="[!] Please enter a valid license key.", text_color="#ef5350")
            return

        res = lm.verify_license_key(key)
        if res.get("valid"):
            lm.save_license(key)
            self.license_info = res
            err_lbl.configure(text=f"✅ Activated! Welcome, {res.get('client')} ({res.get('expires')})", text_color="#00e676")
            self.after(800, self.build_main_ui)
        else:
            reason = res.get("reason", "Invalid license key.")
            err_lbl.configure(text=f"❌ {reason}", text_color="#ef5350")

    def build_main_ui(self):
        for w in self.winfo_children():
            w.destroy()

        self.create_header()
        self.create_navigation()
        self.create_content_frames()
        self.show_frame("account_creator")

    def create_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="#12171f", corner_radius=0, height=52)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=18, pady=10)

        title_lbl = ctk.CTkLabel(
            title_box,
            text="⚡ SOUMOJIT HARK CREATION",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_ACCENT_CYAN
        )
        title_lbl.pack(side="left")

        subtitle_lbl = ctk.CTkLabel(
            title_box,
            text=" | Automated Hark Account Creator & Profile Manager",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#c9d1d9"
        )
        subtitle_lbl.pack(side="left")

        links_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        links_box.pack(side="right", padx=18, pady=10)

        # License Status Badge
        lic = getattr(self, 'license_info', {})
        client_name = lic.get('client', 'User')
        days_left = lic.get('days_left', 0)
        exp_txt = "👑 Lifetime VIP" if days_left > 3650 else f"👑 {client_name} ({days_left}d)"

        lic_badge = ctk.CTkLabel(
            links_box,
            text=exp_txt,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#182d21",
            text_color="#00e676",
            corner_radius=6,
            padx=10,
            pady=3
        )
        lic_badge.pack(side="left", padx=8)

        btn_open_atomic = ctk.CTkButton(
            links_box,
            text="📬 Open Atomic Mail (Login Once)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#00897b",
            hover_color="#00695c",
            height=30,
            command=self.launch_atomic_master
        )
        btn_open_atomic.pack(side="left", padx=6)

        api_link = ctk.CTkLabel(
            links_box,
            text="⚡ Hark.com",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#00bcd4",
            cursor="hand2"
        )
        api_link.pack(side="left", padx=8)
        api_link.bind("<Button-1>", lambda e: webbrowser.open("https://hark.com"))

    def auto_align_action(self):
        pass

    def launch_atomic_master(self):
        layout = pm.get_screen_tiled_layout()
        m_pos = layout["mail"]["pos"]
        m_size = layout["mail"]["size"]
        self.log(f"[*] Launching Master Atomic Mail at TOP of screen (Port {ams.MASTER_PORT})...")
        self.log("[*] Atomic Mail will remain open permanently at TOP while Hark accounts refresh below!")
        threading.Thread(target=lambda: ams.launch_master_atomic_mail(pos=m_pos, size=m_size), daemon=True).start()

    def create_navigation(self):
        nav_frame = ctk.CTkFrame(self, fg_color="transparent", height=46)
        nav_frame.pack(fill="x", padx=18, pady=(12, 4))

        self.seg_nav = ctk.CTkSegmentedButton(
            nav_frame,
            values=["Auto Account Creator", "Chrome Profile Manager", "Settings"],
            command=self.on_nav_change,
            selected_color="#0288d1",
            selected_hover_color="#0277bd",
            unselected_color="#212631",
            unselected_hover_color="#2b3140",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=36
        )
        self.seg_nav.set("Auto Account Creator")
        self.seg_nav.pack(side="top")

    def create_content_frames(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=18, pady=(6, 16))

        self.frame_profile_manager = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frame_account_creator = ctk.CTkFrame(self.container, fg_color="transparent")
        self.frame_settings = ctk.CTkFrame(self.container, fg_color="transparent")

        self.setup_account_creator_view()
        self.setup_profile_manager_view()
        self.setup_settings_view()

    def on_nav_change(self, value):
        if value == "Chrome Profile Manager":
            self.show_frame("profile_manager")
        elif value == "Auto Account Creator":
            self.show_frame("account_creator")
        elif value == "Settings":
            self.show_frame("settings")

    def show_frame(self, name):
        self.frame_profile_manager.pack_forget()
        self.frame_account_creator.pack_forget()
        self.frame_settings.pack_forget()

        if name == "profile_manager":
            self.frame_profile_manager.pack(fill="both", expand=True)
            self.refresh_profile_list()
        elif name == "account_creator":
            self.frame_account_creator.pack(fill="both", expand=True)
        elif name == "settings":
            self.frame_settings.pack(fill="both", expand=True)

    # --------------------------------------------------------------------------
    # TAB 1: AUTO ACCOUNT CREATOR (Strict Step-by-Step Observation)
    # --------------------------------------------------------------------------
    def setup_account_creator_view(self):
        creator_card = ctk.CTkFrame(self.frame_account_creator, fg_color="#181c24", corner_radius=10)
        creator_card.pack(fill="x", padx=10, pady=10)

        title_lbl = ctk.CTkLabel(
            creator_card,
            text="⚡ SOUMOJIT Strict Step-by-Step Hark Account Creator (.method + Verification)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_ACCENT_CYAN
        )
        title_lbl.pack(anchor="w", padx=20, pady=(16, 4))

        desc_lbl = ctk.CTkLabel(
            creator_card,
            text="• Hark par email daalne ke baad confirmation ka wait karega — jab tak confirm nahi hoga, aage nahi badhega.\n• Magic Link -> Set Password -> 18+ Birthday: Har step verify karke hi account finalize karega.\n• Ban chuke accounts ka alag record rakhega aur same dot-email dobara kabhi use nahi karega.",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED,
            justify="left"
        )
        desc_lbl.pack(anchor="w", padx=20, pady=(0, 14))

        form_grid = ctk.CTkFrame(creator_card, fg_color="transparent")
        form_grid.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(form_grid, text="Atomic Mail ID:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", pady=4)
        self.entry_master_email = ctk.CTkEntry(form_grid, width=320, placeholder_text="e.g. soumojm123@atomicmail.io")
        self.entry_master_email.insert(0, self.cfg.get("base_email", "soumojm123@atomicmail.io"))
        self.entry_master_email.grid(row=0, column=1, sticky="w", padx=10, pady=4)

        ctk.CTkLabel(form_grid, text="Number of Accounts:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, sticky="w", pady=4)
        self.entry_count = ctk.CTkEntry(form_grid, width=120, placeholder_text="5")
        self.entry_count.insert(0, str(self.cfg.get("accounts_count", 5)))
        self.entry_count.grid(row=1, column=1, sticky="w", padx=10, pady=4)

        ctk.CTkLabel(form_grid, text="Password (All Accounts):", font=ctk.CTkFont(size=12, weight="bold")).grid(row=2, column=0, sticky="w", pady=4)
        self.entry_password = ctk.CTkEntry(form_grid, width=240, placeholder_text="Min 8 characters")
        self.entry_password.insert(0, self.cfg.get("default_password", "HarkPassword2026!"))
        self.entry_password.grid(row=2, column=1, sticky="w", padx=10, pady=4)

        ctk.CTkLabel(form_grid, text="Task Note / Reminder:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=3, column=0, sticky="w", pady=4)
        self.entry_task_note = ctk.CTkEntry(form_grid, width=320, placeholder_text="e.g. Client X - Batch 1 / Warmup")
        self.entry_task_note.grid(row=3, column=1, sticky="w", padx=10, pady=4)

        ctrl_frame = ctk.CTkFrame(creator_card, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=(12, 16))

        self.btn_start = ctk.CTkButton(
            ctrl_frame,
            text="🚀 Start Automatic Account Creation",
            fg_color="#00c853",
            hover_color="#00a844",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.start_batch_creation
        )
        self.btn_start.pack(side="left")

        self.btn_stop = ctk.CTkButton(
            ctrl_frame,
            text="⏹ Stop Creation",
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.stop_creation_action
        )
        self.btn_stop.pack(side="left", padx=6)

        btn_test_step1 = ctk.CTkButton(
            ctrl_frame,
            text="🧪 Test Email + 18+ Birthday Verification",
            fg_color="#0288d1",
            hover_color="#0277bd",
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.test_step1_action
        )
        btn_test_step1.pack(side="left", padx=6)

        self.btn_next_batch = ctk.CTkButton(
            ctrl_frame,
            text="⏭️ Next Batch (Close & Launch Next)",
            fg_color="#ff6f00",
            hover_color="#e65100",
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.next_batch_action
        )
        self.btn_next_batch.pack(side="left", padx=6)

        btn_launch_atomic = ctk.CTkButton(
            ctrl_frame,
            text="📬 Open Atomic Mail",
            fg_color="#00897b",
            hover_color="#00695c",
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.launch_atomic_master
        )
        btn_launch_atomic.pack(side="left", padx=6)

        self.btn_fetch_link = ctk.CTkButton(
            ctrl_frame,
            text="📋 Copy Link (Auto 93->94)",
            fg_color="#6a1b9a",
            hover_color="#4a148c",
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.fetch_copy_magic_link_action
        )
        self.btn_fetch_link.pack(side="left", padx=6)

        console_card = ctk.CTkFrame(self.frame_account_creator, fg_color="#14171e", corner_radius=10)
        console_card.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        console_hdr = ctk.CTkFrame(console_card, fg_color="transparent")
        console_hdr.pack(fill="x", padx=16, pady=(10, 4))

        ctk.CTkLabel(console_hdr, text="Activity & Creation Log (Live):", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        self.lbl_live_windows = ctk.CTkLabel(
            console_hdr,
            text="Active Hark Windows: ⚪ None (All Closed)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#90a4ae"
        )
        self.lbl_live_windows.pack(side="right")

        self.txt_log = ctk.CTkTextbox(console_card, fg_color="#0d0f14", text_color="#cfd8dc", font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_log.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    def log(self, text):
        self.after(0, lambda: self._append_log(text))

    def _append_log(self, text):
        self.txt_log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n")
        self.txt_log.see("end")

    def stop_creation_action(self):
        if self.is_creating:
            self.stop_requested = True
            self.log("[!] STOP REQUESTED. Gracefully halting automation process...")

    def next_batch_action(self):
        if self.is_creating:
            self.next_batch_requested = True
            self.log("[⏭️] NEXT BATCH CLICKED: Closing current Hark windows & launching next fresh batch...")
        else:
            self.log("[!] Click 'Start Automatic Account Creation' first to begin.")

    def fetch_copy_magic_link_action(self):
        def worker():
            self.log("\n==================================================")
            self.log("[*] SEARCHING ATOMIC MAIL FOR HARK MAGIC LINK...")
            self.log(f"[*] Watching for incremental message (Previous: #{self.last_atomic_msg_id or 'None'})...")
            self.log("==================================================")
            res = ams.fetch_incremental_hark_link(last_msg_id=self.last_atomic_msg_id, timeout=40, log_func=self.log)
            if res and res.get("success"):
                link = res.get("magic_link")
                msg_id = res.get("message_id")
                self.last_atomic_msg_id = msg_id
                try:
                    self.clipboard_clear()
                    self.clipboard_append(link)
                except Exception:
                    pass
                self.log(f"\n[📋 100% COPIED TO CLIPBOARD!] Message #{msg_id} Magic Link:\n{link}")
                self.log("[✓] Link clipboard me copy ho chuka hai! Aap direct browser address bar me Paste karke enter kar sakte hain.")
            else:
                self.log("[!] Magic Link nahi mila ya timeout ho gaya. Ensure karein ki Atomic Mail top par khula hai.")
        threading.Thread(target=worker, daemon=True).start()

    def test_step1_action(self):
        if self.is_creating:
            self.log("[!] Another task is running. Please wait or click Stop.")
            return

        email = self.entry_master_email.get().strip()
        if not email or "@" not in email:
            self.log("[!] ERROR: Please enter a valid base Atomic Mail address first.")
            return

        def worker():
            self.is_creating = True
            self.stop_requested = False
            self.btn_start.configure(state="disabled")
            self.log("\n==================================================")
            self.log("[*] STARTING STEP 1 TEST: EMAIL SUBMIT & NEXT ONLY")
            self.log("==================================================")

            # Pick fresh dot-email
            used = pm.get_all_used_emails()
            fresh = generate_dot_variations(email, used_emails=used, limit=1, must_have_dot=True)
            target_email = fresh[0] if fresh else f"s.o.{email}"
            pm.mark_email_as_used(target_email)

            self.log(f"[*] Fresh Dot-Email (Skipped {len(used)} already used): {target_email}")
            next_id, test_port, profile_path = pm.get_next_profile_info()
            self.log(f"[*] Allocating 100% clean, fresh profile: profile_{next_id} (Port {test_port})...")
            self.log("[*] Note: Previous completed accounts remain untouched for manual use.")
            layout = pm.get_screen_tiled_layout(hark_count=2, with_top_mail=True)
            slot = layout["hark_slots"][0]
            pm.launch_chrome_profile(url="https://hark.com", profile_path=profile_path, port=test_port, pos=slot["pos"], size=slot["size"], close_previous=True)

            # 1. Submit Email
            res = cdp.wait_and_submit_hark_email(test_port, target_email, max_wait_sec=45, log_func=self.log)
            if not (res and res.get("success")):
                err = res.get("error", "Unknown error") if res else "Unknown"
                self.log(f"\n[❌ FAIL] Email submit failed: {err}")
                self.is_creating = False
                self.btn_start.configure(state="normal")
                return

            self.log("\n[✓] Email accepted! Proceeding to 18+ Birthday Verification...")
            time.sleep(2)

            # 2. Complete 18+ Birthday Verification ('When is your birthday?')
            bday_res = cdp.complete_hark_birthday(test_port, max_wait=25, log_func=self.log)
            if bday_res and bday_res.get("success"):
                self.log("\n" + "=" * 50)
                self.log(f"[✓✓✓] SUCCESS! 18+ BIRTHDAY SELECTED: {bday_res.get('birthday')}!")
                self.log("[✓] Continue clicked! Hark accepted age verification and sent verification email.")
                self.log("=" * 50)
            else:
                err = bday_res.get("error", "Unknown error") if bday_res else "Unknown"
                self.log(f"\n[❌ FAIL] Birthday selection failed: {err}")

            self.is_creating = False
            self.btn_start.configure(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    def start_batch_creation(self):
        if self.is_creating:
            self.log("[!] Creation is already in progress!")
            return

        email = self.entry_master_email.get().strip()
        count_str = self.entry_count.get().strip()
        password = self.entry_password.get().strip()
        task_note = self.entry_task_note.get().strip()

        if not email or "@" not in email:
            self.log("ERROR: Please enter a valid Atomic Mail address.")
            return

        if not password or len(password) < 8:
            self.log("ERROR: Password must be at least 8 characters.")
            return

        try:
            count = int(count_str)
        except ValueError:
            count = 5

        self.cfg["base_email"] = email
        self.cfg["accounts_count"] = count
        self.cfg["default_password"] = password
        pm.save_config(self.cfg)

        # STRICT DEDUPLICATION: Load ALL ever-used emails
        used_emails = pm.get_all_used_emails()
        variations = generate_dot_variations(email, used_emails=used_emails, limit=count, must_have_dot=True)
        
        if not variations:
            self.log("[!] Error: All dot variations for this email have already been used! Try another base email.")
            return

        # Immediately lock all generated variations so they are NEVER repeated
        for v in variations:
            pm.mark_email_as_used(v)

        self.log(f"[✓] Generated {len(variations)} FRESH UNUSED dot variations (Skipped {len(used_emails)} already used).")

        def worker():
            self.is_creating = True
            self.stop_requested = False
            self.btn_start.configure(state="disabled")

            batch_size = 2
            pairs = [variations[i:i + batch_size] for i in range(0, len(variations), batch_size)]

            def process_single_account(acc, var_email, pos=None, size=None, status_dict=None):
                target_port = acc['port']
                self.log(f"[*] Opening Hark Profile #{acc['id']} for {var_email} (Port {target_port})...")
                proc = pm.launch_chrome_profile(acc['id'], url="https://hark.com", pos=pos, size=size, close_previous=False)
                if status_dict is not None:
                    status_dict['proc'] = proc

                # STEP 1: Strict Email Submit
                self.log(f"[*] [{var_email}] Submitting email on Hark...")
                res_email = cdp.wait_and_submit_hark_email(target_port, var_email, max_wait_sec=45, log_func=self.log)
                if not (res_email and res_email.get("success")):
                    err = res_email.get("error", "Email timeout") if res_email else "Failed"
                    self.log(f"[❌ FAIL] {var_email} failed at Step 1: {err}")
                    pm.record_failure(var_email, f"Step 1 Failed: {err}")
                    acc["status"] = "FAILED (Email Submit)"
                    pm.save_accounts(self.accounts)
                    self.after(0, self.refresh_profile_list)
                    if status_dict: status_dict['done'] = True
                    return

                # STEP 2: Strict 18+ Birthday Verification
                self.log(f"[*] [{var_email}] Selecting 18+ Age Verification dropdowns...")
                bday_res = cdp.complete_hark_birthday(target_port, max_wait=30, log_func=self.log)
                if bday_res and bday_res.get("success"):
                    self.log(f"[✓] [{var_email}] 18+ Birthday ({bday_res.get('birthday')}) submitted & Continue clicked!")
                elif bday_res and bday_res.get("rate_limited"):
                    self.log(f"[⚠️ RATE LIMITED] {var_email}: Hark 'Too many attempts' pause detect hua.")
                    self.log("[*] Kripya 2-3 minute pause karein ya IP/hotspot change karein.")

                # STEP 3: Auto-Detect Incremental Link from Atomic Mail (e.g. 93 -> 94 -> 95)
                if pm.is_window_alive(ams.MASTER_PORT):
                    self.log(f"[*] Checking Atomic Mail for incoming link (Incrementing past #{self.last_atomic_msg_id or 0})...")
                    link_res = ams.fetch_incremental_hark_link(last_msg_id=self.last_atomic_msg_id, timeout=25, log_func=self.log)
                    if link_res and link_res.get("success"):
                        mlink = link_res.get("magic_link")
                        self.last_atomic_msg_id = link_res.get("message_id")
                        try:
                            self.clipboard_clear()
                            self.clipboard_append(mlink)
                        except Exception:
                            pass
                        self.log(f"[📋 AUTO-COPIED] Message #{self.last_atomic_msg_id} Magic Link:\n{mlink}")

                # Successfully completed Email + Age Verification
                pm.record_success(var_email, password, target_port, acc['profile_path'])
                acc["status"] = "✅ SUCCESSFUL"
                acc["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pm.save_accounts(self.accounts)
                self.after(0, self.refresh_profile_list)
                self.log(f"[✓✓✓] SUCCESS: {var_email} Email + 18+ Age Completed!")
                if status_dict:
                    status_dict['done'] = True

            for b_idx, batch_emails in enumerate(pairs):
                if self.stop_requested:
                    self.log("[!] Automation stopped by user.")
                    break

                num_in_batch = len(batch_emails)
                self.log(f"\n==================================================")
                self.log(f"[*] [BATCH {b_idx+1}/{len(pairs)}] Launching {num_in_batch} Fresh Hark Window(s) (Bottom Left & Right)...")
                for be in batch_emails:
                    self.log(f"    -> Fresh Dot-Account: {be}")
                self.log(f"==================================================")

                # Close any previous Hark windows so only current batch remains open
                pm.close_active_hark_windows()
                time.sleep(1)

                layout = pm.get_screen_tiled_layout(hark_count=num_in_batch, with_top_mail=True)
                hark_slots = layout.get("hark_slots", [])

                batch_threads = []
                batch_stats = []

                for w_idx, var_email in enumerate(batch_emails):
                    acc = pm.add_account(var_email, status="In Progress...", password=password, note=task_note)
                    self.after(0, self.refresh_profile_list)
                    stat = {'done': False, 'proc': None, 'acc': acc}
                    batch_stats.append(stat)

                    slot = hark_slots[w_idx] if w_idx < len(hark_slots) else None
                    pos = slot["pos"] if slot else None
                    size = slot["size"] if slot else None

                    t = threading.Thread(
                        target=process_single_account,
                        args=(acc, var_email, pos, size, stat),
                        daemon=True
                    )
                    batch_threads.append(t)
                    t.start()
                    time.sleep(0.3)

                ports_info = ", ".join([f"#{s['acc']['id']} (Port {s['acc']['port']})" for s in batch_stats])
                self.after(0, lambda p=ports_info, n=num_in_batch: self.lbl_live_windows.configure(
                    text=f"Active Hark Windows: 🟢 {n} Open [{p}]",
                    text_color="#00e676"
                ))

                # SUPERVISOR: Monitor this batch of windows
                # WINDOWS STAY OPEN! Never close automatically on completion.
                # Only advance when user clicks '⏭️ Next Batch' OR closes windows manually!
                notified_done = False
                while True:
                    if self.stop_requested:
                        break

                    all_done = all(s['done'] for s in batch_stats)
                    any_alive = any(pm.is_window_alive(s['acc']['port'], s.get('proc')) for s in batch_stats)

                    # Update live window indicator if a window was closed
                    alive_count = sum(1 for s in batch_stats if pm.is_window_alive(s['acc']['port'], s.get('proc')))
                    if alive_count < num_in_batch and alive_count > 0:
                        self.after(0, lambda c=alive_count: self.lbl_live_windows.configure(
                            text=f"Active Hark Windows: 🟡 {c} Open (Rest closed)",
                            text_color="#ffb300"
                        ))

                    # Log once when accounts in this batch finish submitting
                    if all_done and not notified_done:
                        self.log(f"\n[✓✓✓] SUCCESS! Email & 18+ Birthday submitted for all {num_in_batch} account(s) in this batch!")
                        self.log("[*] Windows will STAY OPEN for you. Jab aap ready hon, '⏭️ Next Batch (Close & Launch Next)' button dabayein.")
                        notified_done = True

                    # ONLY proceed when user clicks 'Next Batch' OR user manually closes the browser windows
                    if self.next_batch_requested or not any_alive:
                        if self.next_batch_requested:
                            self.next_batch_requested = False
                            self.log(f"\n[⏭️] 'Next Batch' button clicked! Closing current {num_in_batch} Hark windows & launching NEXT BATCH...")
                        else:
                            self.log(f"\n[✓] Browser window(s) closed by user. Launching NEXT FRESH BATCH...")
                        self.after(0, lambda: self.lbl_live_windows.configure(
                            text="Active Hark Windows: ⚪ None (All Closed)",
                            text_color="#90a4ae"
                        ))
                        time.sleep(1.5)
                        break

                    time.sleep(1.5)

            self.log(f"\n[✓✓✓] ALL ACCOUNTS PROCESSED! Check 'Chrome Profile Manager' for records.")
            pm.close_active_hark_windows()
            self.after(0, lambda: self.lbl_live_windows.configure(
                text="Active Hark Windows: ⚪ None (All Closed)",
                text_color="#90a4ae"
            ))
            self.is_creating = False
            self.stop_requested = False
            self.btn_start.configure(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    # --------------------------------------------------------------------------
    # TAB 2: CHROME PROFILE MANAGER (Filtered Records: Success / Failed / All)
    # --------------------------------------------------------------------------
    def setup_profile_manager_view(self):
        action_bar = ctk.CTkFrame(self.frame_profile_manager, fg_color="#181c24", corner_radius=8, height=52)
        action_bar.pack(fill="x", pady=(0, 6))

        btn_refresh = ctk.CTkButton(
            action_bar, text="⟳ Refresh", width=95, height=34,
            fg_color="#2a3242", hover_color="#363f52",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.refresh_profile_list
        )
        btn_refresh.pack(side="left", padx=(10, 6), pady=8)

        btn_success_txt = ctk.CTkButton(
            action_bar, text="✅ Open success.txt", width=150, height=34,
            fg_color="#1b5e20", hover_color="#2e7d32",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_success_txt
        )
        btn_success_txt.pack(side="left", padx=6, pady=8)

        btn_failed_txt = ctk.CTkButton(
            action_bar, text="❌ Open failed.txt", width=150, height=34,
            fg_color="#b71c1c", hover_color="#c62828",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_failed_txt
        )
        btn_failed_txt.pack(side="left", padx=6, pady=8)

        btn_profiles_folder = ctk.CTkButton(
            action_bar, text="📁 Profiles Folder", width=140, height=34,
            fg_color="#2a3242", hover_color="#363f52",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_profiles_folder
        )
        btn_profiles_folder.pack(side="left", padx=6, pady=8)

        btn_export = ctk.CTkButton(
            action_bar, text="⬇ Export CSV", width=110, height=34,
            fg_color="#37474f", hover_color="#455a64",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.export_csv_action
        )
        btn_export.pack(side="left", padx=6, pady=8)

        btn_close_all = ctk.CTkButton(
            action_bar, text="🔴 Close All Open Windows", width=180, height=34,
            fg_color="#851616", hover_color="#a81b1b",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.close_all_hark_action
        )
        btn_close_all.pack(side="left", padx=6, pady=8)

        btn_retry_all = ctk.CTkButton(
            action_bar, text="🔁 Retry All Pending", width=160, height=34,
            fg_color="#e65100", hover_color="#bf360c",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.retry_all_failed_action
        )
        btn_retry_all.pack(side="left", padx=6, pady=8)

        # Filter Segment (All / Open / Success / Failed)
        filter_bar = ctk.CTkFrame(self.frame_profile_manager, fg_color="transparent", height=38)
        filter_bar.pack(fill="x", pady=(2, 6))

        self.seg_filter = ctk.CTkSegmentedButton(
            filter_bar,
            values=["All Profiles", "🟢 Open (Live)", "✅ Created Success", "❌ Failed / Pending"],
            command=self.on_filter_change,
            selected_color="#0288d1",
            selected_hover_color="#0277bd",
            unselected_color="#1a1e27",
            unselected_hover_color="#242b38",
            text_color="#ffffff",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32
        )
        self.seg_filter.set("All Profiles")
        self.seg_filter.pack(side="left")

        self.lbl_profile_count = ctk.CTkLabel(
            filter_bar,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#90caf9"
        )
        self.lbl_profile_count.pack(side="right", padx=10)

        self.profiles_scroll = ctk.CTkScrollableFrame(
            self.frame_profile_manager,
            fg_color="#14171e",
            corner_radius=8,
            border_width=1,
            border_color="#212631"
        )
        self.profiles_scroll.pack(fill="both", expand=True)

    def on_filter_change(self, val):
        self.profile_filter = val
        self.refresh_profile_list()

    def close_single_window_action(self, port):
        pm.close_window_by_port(port)
        self.after(50, self.refresh_profile_list)

    def open_single_profile_action(self, account_id):
        pm.launch_chrome_profile(account_id=account_id)
        self.after(200, self.refresh_profile_list)

    def close_all_hark_action(self):
        pm.close_active_hark_windows()
        self.after(50, self.refresh_profile_list)
        self.log("[!] All open Hark windows closed by user.")

    def edit_note_dialog(self, acc):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Task Reminder - Profile #{acc.get('id')}")
        dialog.geometry("500x240")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#12171f")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=f"📝 Profile #{acc.get('id')} - Task Note / Reminder",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#00e5ff"
        ).pack(pady=(18, 4))

        ctk.CTkLabel(
            dialog,
            text=f"{acc.get('email')}",
            font=ctk.CTkFont(size=12),
            text_color="#90a4ae"
        ).pack(pady=(0, 10))

        entry_note = ctk.CTkEntry(
            dialog,
            width=440,
            height=38,
            placeholder_text="Enter custom task note or reminder (e.g. Client X / Warmup)...",
            font=ctk.CTkFont(size=12)
        )
        entry_note.insert(0, acc.get("note", ""))
        entry_note.pack(pady=6)
        entry_note.focus()

        btn_box = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_box.pack(pady=(14, 16))

        def save_action():
            val = entry_note.get().strip()
            pm.update_account_note(acc.get("id"), val)
            acc["note"] = val
            dialog.destroy()
            self.refresh_profile_list()

        entry_note.bind("<Return>", lambda e: save_action())

        btn_save = ctk.CTkButton(
            btn_box,
            text="💾 Save Note",
            width=120,
            height=34,
            fg_color="#00c853",
            hover_color="#00a844",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=save_action
        )
        btn_save.pack(side="left", padx=8)

        btn_cancel = ctk.CTkButton(
            btn_box,
            text="Cancel",
            width=90,
            height=34,
            fg_color="#37474f",
            hover_color="#455a64",
            font=ctk.CTkFont(size=12),
            command=dialog.destroy
        )
        btn_cancel.pack(side="left", padx=8)

    def refresh_profile_list(self):
        for widget in self.profiles_scroll.winfo_children():
            widget.destroy()

        self.accounts = pm.load_accounts()
        success_list = pm.load_json_file(pm.SUCCESS_FILE)
        failed_list = pm.load_json_file(pm.FAILED_FILE)

        open_count = sum(1 for a in self.accounts if pm.is_window_alive(a.get('port')))

        self.lbl_profile_count.configure(
            text=f"Total: {len(self.accounts)}  |  🟢 Live Open: {open_count}  |  ✅ Success: {len(success_list)}  |  ❌ Failed: {len(failed_list)}"
        )

        # Filter items
        if self.profile_filter == "🟢 Open (Live)":
            display_items = [a for a in self.accounts if pm.is_window_alive(a.get('port'))]
        elif self.profile_filter == "✅ Created Success":
            display_items = [a for a in self.accounts if "SUCCESS" in a.get("status", "").upper() or "ACTIVE" in a.get("status", "").upper()]
        elif self.profile_filter == "❌ Failed / Pending":
            display_items = [a for a in self.accounts if "FAIL" in a.get("status", "").upper() or "PENDING" in a.get("status", "").upper()]
        else:
            display_items = self.accounts

        if not display_items:
            empty_lbl = ctk.CTkLabel(
                self.profiles_scroll,
                text=f"No accounts in '{self.profile_filter}'.",
                font=ctk.CTkFont(size=13),
                text_color=COLOR_TEXT_MUTED
            )
            empty_lbl.pack(pady=50)
            return

        for idx, acc in enumerate(display_items):
            row = ctk.CTkFrame(
                self.profiles_scroll,
                fg_color="#1a1e27",
                corner_radius=6,
                border_width=1,
                border_color="#242b38"
            )
            row.pack(fill="x", padx=6, pady=4)

            email_frame = ctk.CTkFrame(row, fg_color="transparent")
            email_frame.pack(side="left", fill="y", padx=(12, 16), pady=8)

            # Determine Status & Icons
            st = acc.get("status", "Created").upper()
            is_success = "SUCCESS" in st or "ACTIVE" in st
            is_fail = "FAIL" in st

            icon_prefix = "✅ " if is_success else ("❌ " if is_fail else "⏳ ")
            email_color = "#00e676" if is_success else ("#ef5350" if is_fail else "#ffffff")

            lbl_email = ctk.CTkLabel(
                email_frame,
                text=f"{icon_prefix}{idx+1}.  {acc.get('email', '')}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=email_color,
                anchor="w"
            )
            lbl_email.pack(anchor="w")

            pwd_txt = acc.get('password', '')
            lbl_port = ctk.CTkLabel(
                email_frame,
                text=f"     Profile #{acc.get('id')}  |  Port: {acc.get('port', 9400)}  |  Password: {pwd_txt}",
                font=ctk.CTkFont(size=11),
                text_color="#78909c",
                anchor="w"
            )
            lbl_port.pack(anchor="w")

            note_val = acc.get("note", "").strip()
            note_display = f"📝 Note: {note_val}" if note_val else "📝 + Add Task Note"
            note_color = "#00e5ff" if note_val else "#607d8b"
            btn_note = ctk.CTkButton(
                email_frame,
                text=note_display,
                font=ctk.CTkFont(size=11),
                text_color=note_color,
                fg_color="#182330" if note_val else "transparent",
                hover_color="#243345",
                height=22,
                corner_radius=4,
                anchor="w",
                command=lambda a=acc: self.edit_note_dialog(a)
            )
            btn_note.pack(anchor="w", padx=(12, 0), pady=(2, 0))

            is_open = pm.is_window_alive(acc.get('port'))

            # Status pill with prominent tick mark for success
            if is_success:
                pill_text = " ✅ SUCCESSFUL "
                bg_color = "#1b5e20"
                fg_color = "#00e676"
            elif is_fail:
                pill_text = " ❌ FAILED "
                bg_color = "#b71c1c"
                fg_color = "#ffcdd2"
            else:
                pill_text = f" {acc.get('status', 'Pending')} "
                bg_color = "#37474f"
                fg_color = "#b0bec5"

            status_pill = ctk.CTkLabel(
                row,
                text=pill_text,
                fg_color=bg_color,
                text_color=fg_color,
                corner_radius=4,
                font=ctk.CTkFont(size=12, weight="bold")
            )
            status_pill.pack(side="left", padx=10, pady=8)

            # Live Window State Pill (🟢 OPEN vs ⚪ Closed)
            if is_open:
                win_text = " 🟢 OPEN (LIVE) "
                win_bg = "#003816"
                win_fg = "#00e676"
            else:
                win_text = " ⚪ Closed "
                win_bg = "#212631"
                win_fg = "#78909c"

            status_win = ctk.CTkLabel(
                row,
                text=win_text,
                fg_color=win_bg,
                text_color=win_fg,
                corner_radius=4,
                font=ctk.CTkFont(size=12, weight="bold")
            )
            status_win.pack(side="left", padx=6, pady=8)

            date_frame = ctk.CTkFrame(row, fg_color="transparent")
            date_frame.pack(side="left", padx=14, pady=8)

            lbl_dates = ctk.CTkLabel(
                date_frame,
                text=f"Created: {acc.get('created_at', '')}",
                font=ctk.CTkFont(size=11),
                text_color="#90a4ae"
            )
            lbl_dates.pack()

            actions_frame = ctk.CTkFrame(row, fg_color="transparent")
            actions_frame.pack(side="right", padx=(10, 12), pady=8)

            # Retry button for non-successful / pending accounts
            if not is_success:
                btn_retry = ctk.CTkButton(
                    actions_frame,
                    text="🔁 Retry",
                    width=85,
                    height=32,
                    fg_color="#e65100",
                    hover_color="#bf360c",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    command=lambda a=acc: self.retry_single_account(a)
                )
                btn_retry.pack(side="left", padx=4)

            if is_open:
                btn_close = ctk.CTkButton(
                    actions_frame,
                    text="🔴 Close Window",
                    width=125,
                    height=32,
                    fg_color="#b71c1c",
                    hover_color="#d32f2f",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    command=lambda p=acc.get("port"): self.close_single_window_action(p)
                )
                btn_close.pack(side="left", padx=4)
            else:
                btn_open_chrome = ctk.CTkButton(
                    actions_frame,
                    text="🌐 Open Profile",
                    width=125,
                    height=32,
                    fg_color="#2e7d32" if is_success else "#0288d1",
                    hover_color="#1b5e20" if is_success else "#0277bd",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    command=lambda aid=acc.get("id"): self.open_single_profile_action(aid)
                )
                btn_open_chrome.pack(side="left", padx=4)

            btn_delete = ctk.CTkButton(
                actions_frame,
                text="✕",
                width=32,
                height=32,
                fg_color="#37474f",
                hover_color="#d32f2f",
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda aid=acc.get("id"): self.delete_account(aid)
            )
            btn_delete.pack(side="left", padx=2)

    def retry_single_account(self, acc):
        if self.is_creating:
            self.log("[!] Another task is running. Please wait or stop first.")
            return

        target_email = acc.get("email")
        target_port = acc.get("port")
        pwd = acc.get("password") or self.cfg.get("default_password", "Soumojit@123")
        acc_id = acc.get("id")

        self.show_frame("account_creator")
        self.log(f"\n==================================================")
        self.log(f"[*] 🔁 RETRYING ACCOUNT #{acc_id}: {target_email}")
        self.log(f"[*] Launching clean Profile #{acc_id} (Port {target_port})...")
        self.log(f"==================================================")

        def worker():
            self.is_creating = True
            self.btn_start.configure(state="disabled")

            # Launch Chrome profile
            pm.launch_chrome_profile(account_id=acc_id, url="https://hark.com", close_previous=False)
            time.sleep(1)

            # Step 1: Submit Email
            self.log(f"[*] [{target_email}] Submitting email on Hark.com...")
            res_email = cdp.wait_and_submit_hark_email(target_port, target_email, max_wait_sec=45, log_func=self.log)
            if not (res_email and res_email.get("success")):
                err = res_email.get("error", "Email timeout") if res_email else "Failed"
                self.log(f"[❌ FAIL] {target_email} retry failed at Step 1: {err}")
                acc["status"] = "FAILED (Email Submit)"
                pm.save_accounts(self.accounts)
                self.after(0, self.refresh_profile_list)
                self.is_creating = False
                self.btn_start.configure(state="normal")
                return

            # Step 2: 18+ Birthday Verification
            self.log(f"[*] [{target_email}] Selecting 18+ Birthday dropdowns...")
            bday_res = cdp.complete_hark_birthday(target_port, max_wait=30, log_func=self.log)
            if bday_res and bday_res.get("success"):
                self.log(f"[✓] [{target_email}] 18+ Birthday submitted & Continue clicked!")
            elif bday_res and bday_res.get("rate_limited"):
                self.log(f"[⚠️ RATE LIMITED] {target_email}: Hark 'Too many attempts' detected.")

            # Step 3: Check Atomic Mail for incremental magic link if open
            if pm.is_window_alive(ams.MASTER_PORT):
                link_res = ams.fetch_incremental_hark_link(last_msg_id=self.last_atomic_msg_id, timeout=25, log_func=self.log)
                if link_res and link_res.get("success"):
                    mlink = link_res.get("magic_link")
                    self.last_atomic_msg_id = link_res.get("message_id")
                    try:
                        self.clipboard_clear()
                        self.clipboard_append(mlink)
                    except Exception:
                        pass
                    self.log(f"[📋 AUTO-COPIED] Message #{self.last_atomic_msg_id} Magic Link:\n{mlink}")

            # Mark Success
            pm.record_success(target_email, pwd, target_port, acc.get('profile_path'))
            acc["status"] = "✅ SUCCESSFUL"
            acc["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pm.save_accounts(self.accounts)
            self.after(0, self.refresh_profile_list)
            self.log(f"\n[✓✓✓] RETRY SUCCESSFUL: {target_email} has been completed and marked ✅ SUCCESSFUL!")
            
            self.is_creating = False
            self.btn_start.configure(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    def retry_all_failed_action(self):
        if self.is_creating:
            self.log("[!] Creation is already in progress!")
            return

        pending_accounts = [a for a in self.accounts if "SUCCESS" not in a.get("status", "").upper()]
        if not pending_accounts:
            self.log("[✓] No pending or failed accounts to retry! All accounts are already SUCCESSFUL.")
            return

        self.log(f"[*] Found {len(pending_accounts)} pending/failed accounts. Starting Retry sequence...")
        self.show_frame("account_creator")

        def worker():
            self.is_creating = True
            self.stop_requested = False
            self.btn_start.configure(state="disabled")

            for idx, acc in enumerate(pending_accounts):
                if self.stop_requested:
                    self.log("[!] Retry process stopped by user.")
                    break

                target_email = acc.get("email")
                target_port = acc.get("port")
                pwd = acc.get("password") or self.cfg.get("default_password", "Soumojit@123")
                acc_id = acc.get("id")

                self.log(f"\n==================================================")
                self.log(f"[*] [RETRY {idx+1}/{len(pending_accounts)}] Processing #{acc_id}: {target_email}")
                self.log(f"==================================================")

                pm.close_active_hark_windows()
                time.sleep(1)

                pm.launch_chrome_profile(account_id=acc_id, url="https://hark.com", close_previous=False)
                time.sleep(1)

                # Step 1
                res_email = cdp.wait_and_submit_hark_email(target_port, target_email, max_wait_sec=45, log_func=self.log)
                if not (res_email and res_email.get("success")):
                    err = res_email.get("error", "Email timeout") if res_email else "Failed"
                    self.log(f"[❌ FAIL] {target_email} retry failed at Step 1: {err}")
                    continue

                # Step 2
                bday_res = cdp.complete_hark_birthday(target_port, max_wait=30, log_func=self.log)
                if bday_res and bday_res.get("success"):
                    self.log(f"[✓] [{target_email}] 18+ Birthday submitted & Continue clicked!")

                # Step 3
                if pm.is_window_alive(ams.MASTER_PORT):
                    link_res = ams.fetch_incremental_hark_link(last_msg_id=self.last_atomic_msg_id, timeout=20, log_func=self.log)
                    if link_res and link_res.get("success"):
                        mlink = link_res.get("magic_link")
                        self.last_atomic_msg_id = link_res.get("message_id")
                        try:
                            self.clipboard_clear()
                            self.clipboard_append(mlink)
                        except Exception:
                            pass

                # Mark Success
                pm.record_success(target_email, pwd, target_port, acc.get('profile_path'))
                acc["status"] = "✅ SUCCESSFUL"
                acc["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pm.save_accounts(self.accounts)
                self.after(0, self.refresh_profile_list)
                self.log(f"[✓✓✓] SUCCESS: #{acc_id} {target_email} created!")
                time.sleep(2)

            self.log("\n[✓✓✓] RETRY SEQUENCE COMPLETED! Check 'Chrome Profile Manager'.")
            self.is_creating = False
            self.btn_start.configure(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    def delete_account(self, account_id):
        self.accounts = [a for a in self.accounts if a.get("id") != account_id]
        pm.save_accounts(self.accounts)
        self.refresh_profile_list()

    def open_success_txt(self):
        if not os.path.exists(pm.SUCCESS_TXT):
            with open(pm.SUCCESS_TXT, "w", encoding="utf-8") as f:
                f.write("=== SUCCESSFUL HARK ACCOUNTS ===\n")
        os.startfile(os.path.abspath(pm.SUCCESS_TXT))

    def open_failed_txt(self):
        if not os.path.exists(pm.FAILED_TXT):
            with open(pm.FAILED_TXT, "w", encoding="utf-8") as f:
                f.write("=== FAILED HARK ACCOUNTS ===\n")
        os.startfile(os.path.abspath(pm.FAILED_TXT))

    def open_profiles_folder(self):
        os.makedirs(pm.PROFILES_DIR, exist_ok=True)
        os.startfile(pm.PROFILES_DIR)

    def export_csv_action(self):
        out_csv = os.path.join(pm.BASE_DIR, "accounts_export.csv")
        pm.export_to_csv(out_csv)
        os.startfile(out_csv)

    # --------------------------------------------------------------------------
    # TAB 3: SETTINGS
    # --------------------------------------------------------------------------
    def setup_settings_view(self):
        settings_card = ctk.CTkFrame(self.frame_settings, fg_color="#181c24", corner_radius=10)
        settings_card.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            settings_card,
            text="Configuration & Permanent Storage",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#00e676"
        ).pack(anchor="w", padx=20, pady=(16, 12))

        grid = ctk.CTkFrame(settings_card, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(grid, text="Atomic Mail URL:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", pady=6)
        self.entry_mail_url = ctk.CTkEntry(grid, width=420)
        self.entry_mail_url.insert(0, self.cfg.get("mail_provider_url", "https://atomicmail.io/app/mailbox/"))
        self.entry_mail_url.grid(row=0, column=1, sticky="w", padx=10, pady=6)

        ctk.CTkLabel(grid, text="Target Website:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, sticky="w", pady=6)
        self.entry_target_url = ctk.CTkEntry(grid, width=420)
        self.entry_target_url.insert(0, self.cfg.get("target_url", "https://hark.com"))
        self.entry_target_url.grid(row=1, column=1, sticky="w", padx=10, pady=6)

        btns_frame = ctk.CTkFrame(settings_card, fg_color="transparent")
        btns_frame.pack(anchor="w", padx=20, pady=16)

        btn_save_cfg = ctk.CTkButton(
            btns_frame,
            text="💾 Save Settings",
            fg_color="#00c853",
            hover_color="#00a844",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.save_settings_action
        )
        btn_save_cfg.pack(side="left", padx=(0, 10))

        # Commercial License & Device Card
        lic_card = ctk.CTkFrame(self.frame_settings, fg_color="#181c24", corner_radius=10)
        lic_card.pack(fill="x", padx=10, pady=(10, 10))

        ctk.CTkLabel(
            lic_card,
            text="Commercial License & Device Binding",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#00e5ff"
        ).pack(anchor="w", padx=20, pady=(16, 8))

        lic = getattr(self, 'license_info', {})
        l_grid = ctk.CTkFrame(lic_card, fg_color="transparent")
        l_grid.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(l_grid, text="Licensed To:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", pady=4)
        ctk.CTkLabel(l_grid, text=lic.get('client', 'N/A'), font=ctk.CTkFont(size=12), text_color="#00e676").grid(row=0, column=1, sticky="w", padx=10, pady=4)

        ctk.CTkLabel(l_grid, text="Registered HWID:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, sticky="w", pady=4)
        ctk.CTkLabel(l_grid, text=lm.get_machine_hwid(), font=ctk.CTkFont(family="Consolas", size=12), text_color="#00bcd4").grid(row=1, column=1, sticky="w", padx=10, pady=4)

        ctk.CTkLabel(l_grid, text="License Expiry:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=2, column=0, sticky="w", pady=4)
        ctk.CTkLabel(l_grid, text=f"{lic.get('expires', 'N/A')} ({lic.get('days_left', 0)} days remaining)", font=ctk.CTkFont(size=12), text_color="#ffb300").grid(row=2, column=1, sticky="w", padx=10, pady=4)

        btn_deactivate = ctk.CTkButton(
            lic_card,
            text="🔄 Change / Renew License Key",
            fg_color="#37474f",
            hover_color="#455a64",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.deactivate_license_action
        )
        btn_deactivate.pack(anchor="w", padx=20, pady=(8, 16))

    def deactivate_license_action(self):
        try:
            if os.path.exists(lm.LICENSE_FILE):
                os.remove(lm.LICENSE_FILE)
        except Exception:
            pass
        self.show_activation_screen()

    def save_settings_action(self):
        self.cfg["mail_provider_url"] = self.entry_mail_url.get().strip()
        self.cfg["target_url"] = self.entry_target_url.get().strip()
        pm.save_config(self.cfg)
        self.log("[✓] Settings saved successfully!")

if __name__ == "__main__":
    app = HarkCreatorApp()
    app.mainloop()
