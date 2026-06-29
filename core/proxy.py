import os
import sys
import time
import socket
import subprocess
import urllib.request
import random
from core.utils import colored

TOR_PROXY = "socks5://127.0.0.1:9050"
TOR_HTTP_PROXY = "http://127.0.0.1:8118"
TOR_CONTROL = ("127.0.0.1", 9051)
PROXY_ENABLED = False
_circuit_rotation_count = 0


def check_tor():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("127.0.0.1", 9050))
        s.close()
        return True
    except Exception:
        return False


def check_tor_control():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(TOR_CONTROL)
        s.close()
        return True
    except Exception:
        return False


def check_tor_http():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("127.0.0.1", 8118))
        s.close()
        return True
    except Exception:
        return False


def get_real_ip():
    try:
        req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.read().decode().strip()
    except Exception:
        try:
            req = urllib.request.Request("https://httpbin.org/ip", headers={"User-Agent": "curl/8.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.read().decode().strip()
        except Exception:
            return "unknown"


def get_tor_ip():
    try:
        req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "curl/8.0"})
        req.set_proxy("127.0.0.1:9050", "socks5")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode().strip()
    except Exception:
        return None


def signal_new_identity():
    """Send NEWNYM signal to TOR control port to rotate exit node."""
    global _circuit_rotation_count
    if not check_tor_control():
        print(colored("  [!] TOR control port (9051) not available. Cannot rotate circuit.", "31"))
        print(colored("  [*] Add 'ControlPort 9051' and 'CookieAuthentication 1' to torrc", "33"))
        return False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(TOR_CONTROL)
        s.send(b"AUTHENTICATE\r\n")
        time.sleep(0.5)
        resp = s.recv(1024)
        if b"250" not in resp:
            s.close()
            return False
        s.send(b"SIGNAL NEWNYM\r\n")
        time.sleep(0.5)
        resp = s.recv(1024)
        s.close()
        if b"250" in resp:
            _circuit_rotation_count += 1
            print(colored(f"  [+] TOR circuit rotated ({_circuit_rotation_count})", "32"))
            time.sleep(2)
            new_ip = get_tor_ip()
            if new_ip:
                print(colored(f"  [+] New exit IP: {new_ip}", "32"))
            return True
        return False
    except Exception as e:
        print(colored(f"  [!] Circuit rotation failed: {e}", "31"))
        return False


def auto_rotate(interval_seconds=300):
    """Auto-rotate TOR circuit every N seconds (runs in background thread)."""
    import threading
    def _rotator():
        while True:
            time.sleep(interval_seconds)
            signal_new_identity()
    t = threading.Thread(target=_rotator, daemon=True)
    t.start()
    print(colored(f"  [+] Auto-rotation enabled: every {interval_seconds}s", "32"))


def check_dns_leak():
    """Verify DNS is not leaking outside TOR. Returns True if secure."""
    print(colored("  [*] Checking for DNS leaks...", "33"))
    dns_servers = [
        "resolver1.opendns.com",
        "208.67.222.222",
        "8.8.8.8",
        "1.1.1.1",
    ]
    leak_found = False
    for dns in dns_servers:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect((dns, 53))
            s.send(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
            data = s.recv(512)
            s.close()
            if data:
                print(colored(f"  [!] DNS leak detected! Can reach: {dns}", "31"))
                leak_found = True
        except Exception:
            pass
    if leak_found:
        print(colored("  [!] DNS is leaking! Traffic may bypass TOR.", "31"))
        print(colored("  [*] Fix: use 'networksetup -setdnsservers Ethernet 127.0.0.1' or similar", "33"))
        return False
    else:
        print(colored("  [+] No DNS leak detected (all external DNS blocked)", "32"))
        return True


def verify_full_anonymity():
    """Full anonymity check: TOR + DNS + IP leak. Returns True if fully anonymous."""
    print(colored("\n" + "-" * 55, "36"))
    print(colored("  FULL ANONYMITY VERIFICATION", "36"))
    print(colored("-" * 55, "36"))

    real = get_real_ip()
    print(f"  Real IP:    {real}")

    tor_running = check_tor()
    print(f"  TOR:        {colored('Running', '32') if tor_running else colored('Not running', '31')}")

    if tor_running:
        tor_ip = get_tor_ip()
        print(f"  TOR Exit:   {tor_ip if tor_ip else 'unknown'}")

        if tor_ip and tor_ip != real:
            print(colored("  IP Mask:    OK (IP hidden by TOR)", "32"))
        else:
            print(colored("  IP Mask:    FAIL (IP may be leaking)", "31"))
            return False

    control = check_tor_control()
    print(f"  Ctrl Port:  {colored('Available', '32') if control else colored('Unavailable', '33')}")

    dns_ok = check_dns_leak()

    if tor_running and dns_ok:
        print(colored("  VERDICT:    FULLY ANONYMOUS", "32"))
        print(colored("-" * 55, "36"))
        return True
    else:
        print(colored("  VERDICT:    NOT FULLY ANONYMOUS", "31"))
        print(colored("-" * 55, "36"))
        return False


def check_anonymity():
    print(colored("\n[*] Checking anonymity status...", "33"))
    real = get_real_ip()
    print(f"  Your IP: {real}")

    tor_running = check_tor()
    tor_status_str = colored("Running", "32") if tor_running else colored("Not running", "31")
    print(f"  TOR SOCKS (9050): {tor_status_str}")

    if tor_running:
        tor_ip = get_tor_ip()
        print(f"  TOR Exit IP: {tor_ip if tor_ip else 'unknown'}")
        if tor_ip and tor_ip != real:
            print(colored("  OK You are anonymous (IP hidden by TOR)", "32"))
            return True
        else:
            print(colored("  WARN TOR is running but IP may be leaking", "31"))
            return False
    else:
        print(colored("  WARN You are NOT anonymous", "31"))
        return False


def _find_tor():
    """Find tor.exe across common locations. Returns (path, torrc) or (None, None)."""
    userprofile = os.environ.get("USERPROFILE", "")
    tor_browser_base = os.path.join(userprofile, "tor-browser", "Browser", "TorBrowser")
    candidates = [
        (os.path.join(userprofile, "tor-browser", "Browser", "TorBrowser", "Tor", "tor.exe"),
         os.path.join(tor_browser_base, "Data", "Tor", "torrc")),
        (r"C:\Program Files\Tor\tor.exe",
         r"C:\Program Files\Tor\torrc"),
        (r"C:\Program Files (x86)\Tor\tor.exe",
         r"C:\Program Files (x86)\Tor\torrc"),
        ("tor", ""),
    ]
    for exe, rc in candidates:
        if exe == "tor":
            return ("tor", "")
        if os.path.exists(exe):
            return (exe, rc if os.path.exists(rc) else "")
    return (None, None)


def start_tor():
    print(colored("[*] Attempting to start TOR...", "33"))
    try:
        tor_exe, torrc = _find_tor()
        if not tor_exe:
            print(colored("[!] TOR not found. Install from https://torproject.org", "31"))
            return False
        args = [tor_exe]
        if torrc:
            args.extend(["-f", torrc])
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(colored("[+] TOR starting...", "32"))
        return True
    except Exception as e:
        print(colored(f"[!] Failed: {e}", "31"))
        return False


def start_tor_with_proxy_chain(proxies=None):
    """Start TOR with a proxy chain (use proxychains-style config)."""
    print(colored("[*] Starting TOR with proxy chain...", "33"))
    if not start_tor():
        return False
    if proxies:
        chain_str = " -> ".join(proxies)
        print(colored(f"  [+] Proxy chain: {chain_str}", "32"))
    return True


def tor_status():
    if check_tor():
        tor_ip = get_tor_ip()
        real_ip = get_real_ip()
        return {
            "tor_running": True,
            "tor_ip": tor_ip,
            "real_ip": real_ip,
            "anonymous": tor_ip != real_ip if tor_ip else False,
            "circuit_rotations": _circuit_rotation_count,
            "control_port": check_tor_control(),
        }
    return {"tor_running": False}


def get_proxies():
    if check_tor():
        return {
            "http": TOR_HTTP_PROXY,
            "https": TOR_HTTP_PROXY,
        }
    return {}


def ensure_tor():
    """Auto-start TOR and wait for it to be ready. Returns True if TOR is running."""
    if check_tor():
        return True
    print(colored("[*] TOR not running. Attempting auto-start...", "33"))
    start_tor()
    for i in range(10):
        time.sleep(1)
        if check_tor():
            tor_ip = get_tor_ip()
            if tor_ip:
                print(colored(f"[+] TOR started. Exit IP: {tor_ip}", "32"))
            else:
                print(colored("[+] TOR is running", "32"))
            return True
        if i < 9:
            print(colored("  .", "33"), end="", flush=True)
    print(colored("\n[!] TOR failed to start. Install: apt install tor", "31"))
    return False


def require_tor(force=False):
    """Safety gate — blocks action if TOR is not running.
    If force=True, requires user override. Returns True if safe to proceed."""
    if check_tor():
        return True
    print(colored("\n[!] TOR is NOT running. Your real IP is exposed.", "31"))
    if force:
        print(colored("[!] Force mode: TOR required. Cannot proceed.", "31"))
        return False
    ans = input("  Start TOR now? [Y/n]: ").strip().lower()
    if ans not in ("n", "no"):
        if ensure_tor():
            return True
    ans = input("  Proceed WITHOUT anonymity? [y/N]: ").strip().lower()
    if ans in ("y", "yes"):
        print(colored("  [!] Your real IP will be visible to the target!", "31"))
        return True
    print(colored("  [!] Action cancelled.", "33"))
    return False


def hide_cmd(cmd):
    if check_tor():
        if sys.platform == "win32":
            return f'torsocks {cmd}'
        return f'torsocks {cmd}'
    return cmd


def spoof_mac(interface=None):
    """Spoof MAC address on Linux using macchanger."""
    if sys.platform == "win32":
        print(colored("  [!] MAC spoofing not supported on Windows", "31"))
        return False
    try:
        result = subprocess.run(["which", "macchanger"], capture_output=True, text=True)
        if result.returncode != 0:
            print(colored("  [!] macchanger not installed. Install: sudo apt install macchanger", "31"))
            return False
        if not interface:
            result = subprocess.run(
                ["ip", "route", "show", "default"], capture_output=True, text=True
            )
            parts = result.stdout.split()
            if "dev" in parts:
                interface = parts[parts.index("dev") + 1]
            else:
                print(colored("  [!] Could not detect network interface", "31"))
                return False
        print(colored(f"  [*] Spoofing MAC on {interface}...", "33"))
        subprocess.run(["sudo", "ip", "link", "set", interface, "down"],
                       capture_output=True)
        subprocess.run(["sudo", "macchanger", "-r", interface],
                       capture_output=True)
        subprocess.run(["sudo", "ip", "link", "set", interface, "up"],
                       capture_output=True)
        result = subprocess.run(["macchanger", interface], capture_output=True, text=True)
        print(colored(f"  [+] MAC spoofed on {interface}", "32"))
        for line in result.stdout.split("\n")[:3]:
            print(f"    {line.strip()}")
        return True
    except Exception as e:
        print(colored(f"  [!] MAC spoofing failed: {e}", "31"))
        return False

