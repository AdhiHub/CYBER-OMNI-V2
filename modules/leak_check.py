import json
import os
import requests
from datetime import datetime
from core.utils import colored

HIBP_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hibp_config.json")


def load_hibp_config():
    if os.path.exists(HIBP_CONFIG_FILE):
        try:
            with open(HIBP_CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_hibp_config(api_key):
    with open(HIBP_CONFIG_FILE, "w") as f:
        json.dump({"api_key": api_key}, f, indent=2)
    print(colored(f"  [+] HIBP API key saved to {HIBP_CONFIG_FILE}", "32"))


def check_hibp_email(email, api_key=None):
    if not api_key:
        cfg = load_hibp_config()
        api_key = cfg.get("api_key", "")

    if not api_key:
        print(colored("  [!] HIBP API key required.", "31"))
        print(colored("  [*] Get one free at: https://haveibeenpwned.com/API/Key", "33"))
        try:
            key = input(colored("  [?] Enter HIBP API Key: ", "33")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if not key:
            return None
        api_key = key
        try:
            if input(colored("  [?] Save for future? [Y/n]: ", "33")).strip().lower() not in ("n", "no"):
                save_hibp_config(api_key)
        except (EOFError, KeyboardInterrupt):
            save_hibp_config(api_key)

    headers = {
        "hibp-api-key": api_key,
        "User-Agent": "AdhiHub-CYBER-OMNI/2.0",
    }
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            return []
        elif resp.status_code == 429:
            print(colored("  [!] Rate limited by HIBP. Try again later.", "31"))
            return None
        else:
            print(colored(f"  [!] HIBP error: HTTP {resp.status_code}", "31"))
            return None
    except requests.exceptions.RequestException as e:
        print(colored(f"  [!] Request failed: {e}", "31"))
        return None


def check_pastebin(email, api_key=None):
    if not api_key:
        cfg = load_hibp_config()
        api_key = cfg.get("api_key", "")

    if not api_key:
        return None

    headers = {
        "hibp-api-key": api_key,
        "User-Agent": "AdhiHub-CYBER-OMNI/2.0",
    }
    url = f"https://haveibeenpwned.com/api/v3/pasteaccount/{email}"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            return []
        else:
            return None
    except requests.exceptions.RequestException:
        return None


def format_leak_results(email, breaches, pastes):
    lines = []
    lines.append("=" * 55)
    lines.append(f"Credential Leak Check Report")
    lines.append(f"Target: {email}")
    lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 55)

    if breaches is None and pastes is None:
        lines.append(colored("\n[!] Could not complete check. No API key configured.", "31"))
        lines.append(colored("[*] Use: python omni.py --credits to see API info", "33"))
        return "\n".join(lines)

    if breaches and len(breaches) > 0:
        lines.append(colored(f"\n[!] Found in {len(breaches)} breach(es)!", "31"))
        lines.append("-" * 55)
        for b in breaches:
            name = b.get("Name", "Unknown")
            domain = b.get("Domain", "")
            date = b.get("BreachDate", "")
            data_classes = ", ".join(b.get("DataClasses", []))
            desc = b.get("Description", "")[:150]
            lines.append(f"\n  Breach: {colored(name, '31')}")
            if domain:
                lines.append(f"  Domain: {domain}")
            if date:
                lines.append(f"  Date: {date}")
            if data_classes:
                lines.append(f"  Compromised: {data_classes}")
            if desc:
                lines.append(f"  Description: {desc}")
    else:
        lines.append(colored("\n[*] No known breaches found for this email.", "32"))

    if pastes and len(pastes) > 0:
        lines.append(colored(f"\n[!] Found in {len(pastes)} paste(s)!", "31"))
        lines.append("-" * 55)
        for p in pastes[:5]:
            source = p.get("Source", "Unknown")
            title = p.get("Title", "Untitled")
            date = p.get("Date", "")
            lines.append(f"\n  Source: {source}  |  {title}  |  {date}")
        if len(pastes) > 5:
            lines.append(f"  ... and {len(pastes) - 5} more")
    else:
        lines.append(colored("\n[*] No pastes found.", "32"))

    lines.append("\n" + "=" * 55)
    return "\n".join(lines)


def run_leak_check(email, api_key=None):
    print(colored(f"[*] Checking credential leaks for: {email}", "33"))
    print(colored("[*] Querying Have I Been Pwned...", "33"))

    if api_key is None:
        cfg = load_hibp_config()
        api_key = cfg.get("api_key", "")

    if not api_key:
        print(colored("  [!] HIBP API key not configured.", "31"))
        print(colored("  [*] You need a free API key from https://haveibeenpwned.com/API/Key", "33"))
        try:
            key = input(colored("  [?] Enter HIBP API Key: ", "33")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if key:
            api_key = key
            try:
                if input(colored("  [?] Save for future? [Y/n]: ", "33")).strip().lower() not in ("n", "no"):
                    save_hibp_config(api_key)
            except (EOFError, KeyboardInterrupt):
                save_hibp_config(api_key)
        else:
            return

    breaches = check_hibp_email(email, api_key)
    pastes = check_pastebin(email, api_key)

    output = format_leak_results(email, breaches, pastes)
    print("\n" + output)

    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    fname = f"{report_dir}/leak_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(output)
    print(colored(f"\n[+] Report saved: {fname}", "32"))
