import os
import json
import random
import hashlib
import sys
from core.utils import colored

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

FAKE_PAGES = {
    "404": [
        "Not Found",
        "The requested URL was not found on this server.",
        "Apache/2.4.41 (Ubuntu) Server at localhost Port 80",
        "404 - Page Not Found",
        "The page you are looking for does not exist."
    ],
    "403": [
        "Forbidden",
        "You don't have permission to access this resource.",
        "Apache/2.4.41 (Ubuntu) Server at localhost Port 80",
        "403 - Access Denied",
        "Client is not authorized to access this resource."
    ],
    "500": [
        "Internal Server Error",
        "The server encountered an internal error and cannot complete your request.",
        "Apache/2.4.41 (Ubuntu) Server at localhost Port 80",
        "500 - Internal Server Error",
        "Please try again later."
    ],
    "maintenance": [
        "System Maintenance",
        "This system is currently undergoing scheduled maintenance.",
        "Expected completion: Unknown",
        "We apologize for the inconvenience.",
        "Please check back later."
    ],
    "cloudflare": [
        "Attention Required! | Cloudflare",
        "This website is using a security service to protect itself from online attacks.",
        "Please complete the security check to access this website.",
        "Your IP: 103.x.x.x",
        "Ray ID: 7a8b9c0d1e2f3g4h"
    ],
    "nginx": [
        "502 Bad Gateway",
        "nginx/1.18.0",
        "The upstream server returned an invalid response."
    ],
    "iis": [
        "404 - File or directory not found.",
        "Internet Information Services (IIS)",
        "Microsoft-IIS/10.0",
        "The resource you are looking for might have been removed, had its name changed, or is temporarily unavailable."
    ]
}

FAKE_PAGE_STYLES = list(FAKE_PAGES.keys())


def get_fake_page(style=None):
    if style is None:
        style = random.choice(FAKE_PAGE_STYLES)
    if style not in FAKE_PAGES:
        style = "404"
    lines = FAKE_PAGES[style]
    border = "\u2500" * 55
    out = f"\n{colored(border, '31')}\n"
    out += f"{colored('  ' + lines[0], '31')}\n"
    out += f"{colored(border, '31')}\n"
    for line in lines[1:]:
        out += f"  {line}\n"
    out += f"{colored(border, '31')}\n\n"
    return out


def get_stealth_key():
    cfg = _load_cfg()
    return cfg.get("stealth_key", "")


def set_stealth_key(key):
    cfg = _load_cfg()
    cfg["stealth_key"] = key
    _save_cfg(cfg)


def _load_cfg():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cfg(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def stealth_gate():
    cfg = _load_cfg()
    stealth_key = cfg.get("stealth_key", "")
    stealth_enabled = cfg.get("stealth_enabled", False)

    if not stealth_enabled:
        return True

    max_attempts = 3
    for attempt in range(max_attempts):
        print(get_fake_page())
        key = input("  > ").strip()

        if key == stealth_key:
            print(colored("\n  [+] Access granted.\n", "32"))
            return True

        remaining = max_attempts - attempt - 1
        if remaining > 0:
            print(colored(f"\n  [!] {remaining} attempt(s) remaining.\n", "31"))
        else:
            print(colored("\n  [!] Access denied. Exiting.\n", "31"))
            return False

    return False


def setup_stealth():
    cfg = _load_cfg()
    print(colored("\n" + "\u2550" * 50, "36"))
    print(colored("        STEALTH MODE SETUP", "36"))
    print(colored("\u2550" * 50, "36"))
    print()
    print(colored("  Stealth mode makes CYBER-OMNI look like a harmless", "33"))
    print(colored("  404 error page when someone tries to access it.", "33"))
    print(colored("  Only those who know the secret key can get in.\n", "33"))

    enable = input("  Enable stealth mode? [y/N]: ").strip().lower()
    if enable not in ("y", "yes"):
        cfg["stealth_enabled"] = False
        _save_cfg(cfg)
        print(colored("  > Stealth mode disabled.", "33"))
        return

    print(colored("\n  Choose your camouflage style:", "33"))
    styles = list(FAKE_PAGES.keys())
    for i, s in enumerate(styles, 1):
        print(f"  {i}. {s.upper()} — {FAKE_PAGES[s][0]}")
    choice = input(f"\n  Pick [1-{len(styles)}] (default: 1): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(styles):
        cfg["stealth_style"] = styles[int(choice) - 1]
    else:
        cfg["stealth_style"] = "404"

    print(colored("\n  Set your secret access key:", "33"))
    print(colored("  (type it now — remember it, there's no recovery)", "33"))
    key1 = input("  Key: ").strip()
    if not key1:
        key1 = "cyberomni"
        print(colored(f"  > Using default key: {key1}", "33"))
    key2 = input("  Confirm: ").strip()
    if key1 != key2:
        print(colored("  [!] Keys don't match. Using default.", "31"))
        key1 = "cyberomni"

    cfg["stealth_key"] = key1
    cfg["stealth_enabled"] = True
    _save_cfg(cfg)

    print(colored(f"\n  [+] Stealth mode ACTIVE.", "32"))
    print(colored(f"  [+] Camouflage: {cfg['stealth_style'].upper()}", "32"))
    print(colored(f"  [+] Secret key: {key1}", "32"))
    print(colored(f"  [*] Next launch will show a fake error page.", "33"))
    print(colored(f"  [*] Type the key at the prompt to enter.\n", "33"))


def randomize_style():
    cfg = _load_cfg()
    if cfg.get("stealth_enabled"):
        cfg["stealth_style"] = random.choice(FAKE_PAGE_STYLES)
        _save_cfg(cfg)
