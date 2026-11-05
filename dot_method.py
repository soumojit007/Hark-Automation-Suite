"""
Dot Method (Email Aliasing Generator)
Generates fresh, unique dot combinations of an email address.
Automatically skips any email that has already been used in accounts.json.
Guarantees at least one dot in the email so it's a true dot-alias.
"""

def generate_dot_variations(email: str, used_emails: set = None, limit: int = 100, must_have_dot: bool = True) -> list[str]:
    """
    Generates unique dot variations that have NOT been used yet.
    Example for soumojm123@atomicmail.io:
      - s.oumojm123@atomicmail.io
      - so.umojm123@atomicmail.io
      - s.o.umojm123@atomicmail.io
      - sou.mojm123@atomicmail.io
    """
    if used_emails is None:
        used_emails = set()
    used_lower = {e.strip().lower() for e in used_emails if e}

    if "@" not in email:
        return [email]
    
    username, domain = email.strip().split("@", 1)
    clean_user = username.replace(".", "")
    n = len(clean_user)
    
    if n <= 1:
        return [f"{clean_user}@{domain}"]
    
    results = []
    total_combinations = 1 << (n - 1)
    
    # i=0 has no dot at all, so start from i=1 to guarantee a dot
    start_idx = 1 if must_have_dot else 0
    
    for i in range(start_idx, total_combinations):
        variant = []
        for j in range(n):
            variant.append(clean_user[j])
            if j < n - 1 and (i & (1 << j)):
                variant.append(".")
        
        cand = f"{''.join(variant)}@{domain}".lower()
        # Skip if already used or already in current batch
        if cand not in used_lower and cand not in results:
            results.append(cand)
            if len(results) >= limit:
                break
            
    return results

if __name__ == "__main__":
    already_used = {"soumojm123@atomicmail.io", "s.oumojm123@atomicmail.io"}
    fresh = generate_dot_variations("soumojm123@atomicmail.io", used_emails=already_used, limit=5)
    print("Fresh Unused Dot Variations (Skipping already used):")
    for v in fresh:
        print(" ->", v)
