"""
Hark.com Login Automation Script
Supports:
- Navigating to hark.com sign-in page
- Submitting Email ID to request OTP
- Automatically switching to email tab or reading OTP
- Entering OTP to complete sign-in
"""

import re
import time
import sys
from playwright.sync_api import sync_playwright

# Configuration
PROFILE_DIR = "./hark_browser_profile"  # Directory where browser session/cookies are saved
TARGET_URL = "https://hark.com"
EMAIL_URL = "https://mail.google.com"   # Ya aapka jo bhi webmail ho

def login_to_hark(user_email: str):
    print(f"[*] Starting automation for Hark.com with email: {user_email}")
    
    with sync_playwright() as p:
        # Launch persistent browser profile
        # Is profile me aapka email login hamesha save rahega
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,  # Browser samne open hoga taaki aap live dekh sakein
            channel="chrome", # System Chrome use karega
            args=["--start-maximized"]
        )

        # ---------------------------------------------------------
        # Step 1: Open Hark.com and Navigate to Sign In / Sign Up
        # ---------------------------------------------------------
        page = context.pages[0] if context.pages else context.new_page()
        print(f"[*] Opening {TARGET_URL}...")
        page.goto(TARGET_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Hark.com par Sign In / Get Started button click karna
        print("[*] Looking for Sign In / Log In button...")
        try:
            sign_in_button = page.locator("a:has-text('Sign In'), a:has-text('Log in'), button:has-text('Sign In'), button:has-text('Log in'), a:has-text('Get Started')").first
            if sign_in_button.is_visible():
                sign_in_button.click()
                page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[!] Info: Sign-in button direct click error or already on login page: {e}")

        # ---------------------------------------------------------
        # Step 2: Email ID Enter karna
        # ---------------------------------------------------------
        print(f"[*] Entering email: {user_email}...")
        email_input = page.locator("input[type='email'], input[name='email'], input[placeholder*='email' i]").first
        email_input.wait_for(state="visible", timeout=15000)
        email_input.fill(user_email)
        page.wait_for_timeout(1000)

        # Continue / Submit button click karna
        continue_btn = page.locator("button[type='submit'], button:has-text('Continue'), button:has-text('Next'), button:has-text('Send')").first
        continue_btn.click()
        print("[*] Email submitted. OTP sent by Hark! Waiting for OTP...")

        # ---------------------------------------------------------
        # Step 3: Nayi Tab me Email khol kar OTP read karna
        # ---------------------------------------------------------
        print("[*] Opening email tab to read OTP...")
        mail_tab = context.new_page()
        mail_tab.goto(EMAIL_URL)

        # Email aane ke liye 5-7 second wait
        page.wait_for_timeout(6000)

        # Note: Gmail / Webmail UI se latest unread email open karna
        otp = None
        for attempt in range(6): # 30 seconds tak check karega
            try:
                # Latest email dhoondhna
                unread_items = mail_tab.locator("tr.zA, [role='row'], div.mail-item").first
                if unread_items.is_visible():
                    unread_items.click()
                    mail_tab.wait_for_timeout(2000)
                    
                    # Email content read karna
                    content = mail_tab.content()
                    
                    # 4 se 6 digit ka OTP dhoondna (e.g. 123456 ya 1234)
                    match = re.search(r'\b\d{6}\b', content) or re.search(r'\b\d{4}\b', content)
                    if match:
                        otp = match.group(0)
                        print(f"[✓] OTP Successfully Found: {otp}")
                        break
            except Exception as err:
                print(f"[*] Waiting for OTP email... (Attempt {attempt+1}/6)")
            
            page.wait_for_timeout(4000)

        if not otp:
            print("[!] OTP automatic read nahi ho saka. Kripya screen par dekhein.")
            input("Manual OTP enter karne ke baad console me Enter press karein...")
        else:
            mail_tab.close() # Email tab band kar do

            # ---------------------------------------------------------
            # Step 4: Hark.com par wapas aakar OTP fill karna
            # ---------------------------------------------------------
            page.bring_to_front()
            print("[*] Entering OTP on Hark.com...")
            
            # OTP input locator
            otp_input = page.locator("input[name*='otp' i], input[name*='code' i], input[placeholder*='code' i], input[type='text']").first
            otp_input.wait_for(state="visible", timeout=10000)
            otp_input.fill(otp)
            page.wait_for_timeout(1000)

            # Submit OTP
            verify_btn = page.locator("button[type='submit'], button:has-text('Verify'), button:has-text('Submit'), button:has-text('Continue')").first
            if verify_btn.is_visible():
                verify_btn.click()
            print("[✓] Login complete successfully!")

        page.wait_for_timeout(5000)
        context.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = input("Aapka email ID daaliye: ").strip()
    
    if email:
        login_to_hark(email)
    else:
        print("[!] Email ID daalna zaroori hai.")

