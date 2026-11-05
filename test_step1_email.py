"""
Standalone Step 1 Tester: Hark Email Submission
Focuses ONLY on:
1. Waiting for Hark.com to 100% fully load & hydrate.
2. Clicking and typing the dot-email.
3. Anti-wipe check: ensures React doesn't wipe the email.
4. Clicking Continue and confirming submission.
"""

import time
import sys
import profile_manager as pm
import cdp_automation as cdp
from dot_method import generate_dot_variations

def run_step1_test():
    print("=" * 60)
    print("   HARK.COM STEP 1 TEST: EMAIL SUBMISSION ONLY")
    print("=" * 60)

    cfg = pm.load_config()
    base_email = cfg.get("base_email", "soumojm123@atomicmail.io")
    
    # Pick a fresh dot email
    used = pm.get_all_used_emails()
    fresh_emails = generate_dot_variations(base_email, used_emails=used, limit=1, must_have_dot=True)
    target_email = fresh_emails[0] if fresh_emails else f"s.ou.{base_email}"
    pm.mark_email_as_used(target_email)

    print(f"[*] Target Dot-Email (100% Fresh & Unused): {target_email}")
    print(f"[*] Total previously used dot-emails skipped: {len(used)}")
    print(f"[*] Target Website:    https://hark.com")

    # Allocate a 100% fresh, unused profile folder so previous accounts are never opened
    next_id, test_port, profile_path = pm.get_next_profile_info()
    print(f"[*] Allocating 100% clean, fresh profile: profile_{next_id} (Port {test_port})...")
    print(f"[*] Previous accounts are untouched and preserved for manual use.")
    pm.launch_chrome_profile(url="https://hark.com", profile_path=profile_path, port=test_port, close_previous=True)

    # Step 1: Submit email with full page settlement & anti-wipe
    res = cdp.wait_and_submit_hark_email(test_port, target_email, max_wait_sec=45, log_func=print)
    if not (res and res.get("success")):
        print(f"\n[❌ FAIL] Email submit failed: {res.get('error') if res else 'Unknown'}")
        return False

    print("\n[✓] Email submission accepted! Moving to Step 2: 18+ Age Verification...")
    time.sleep(2)

    # Step 2: 18+ Age Verification ('When is your birthday?')
    bday_res = cdp.complete_hark_birthday(test_port, max_wait=25, log_func=print)
    if bday_res and bday_res.get("success"):
        print("\n" + "=" * 60)
        print(f"[✓✓✓] SUCCESS! 18+ AGE VERIFICATION COMPLETED: {bday_res.get('birthday')}!")
        print("[✓✓✓] CONTINUE CLICKED! Hark has accepted the birthday and moved to next step!")
        print("=" * 60)
        return True
    else:
        print(f"\n[❌ FAIL] Birthday step failed: {bday_res.get('error') if bday_res else 'Unknown'}")
        return False

if __name__ == "__main__":
    run_step1_test()
