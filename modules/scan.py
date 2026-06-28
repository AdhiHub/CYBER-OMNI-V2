import os
import json
import socket
import threading
import time
from core.utils import validate_target, resolve_target, get_timestamp, colored


def _load_ports():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core", "ports.json")
    try:
        with open(path) as f:
            return {int(k): v for k, v in json.load(f).items()}
    except Exception:
        return {}

PORTS = _load_ports()


class ScanModule:
    def __init__(self):
        self.open_ports = []
        self.lock = threading.Lock()

    def run(self, target):
        target = validate_target(target)
        print(colored(f"[*] Starting scan on {target}...", "33"))
        ip = resolve_target(target)
        if not ip:
            print(colored("[!] Could not resolve target", "31"))
            return
        print(colored(f"[+] Target IP: {ip}", "32"))
        try:
            port_range = input("Port range [1-1024]: ").strip()
            if not port_range:
                port_range = "1-1024"
            if "-" in port_range:
                start, end = map(int, port_range.split("-"))
            else:
                start, end = 1, int(port_range)
        except Exception:
            start, end = 1, 1024
        print(colored(f"\n[*] Scanning ports {start}-{end} on {ip}...", "33"))
        start_time = time.time()
        self._scan_ports(ip, start, end)
        elapsed = time.time() - start_time
        self._print_results(ip, elapsed)

    def _scan_port(self, ip, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((ip, port))
            if result == 0:
                banner = self._grab_banner(sock)
                with self.lock:
                    self.open_ports.append({"port": port, "service": self._get_service(port), "banner": banner})
            sock.close()
        except Exception:
            pass

    def _grab_banner(self, sock):
        try:
            sock.settimeout(1.0)
            data = sock.recv(256).decode("utf-8", errors="ignore").strip()
            return data[:120] if data else None
        except Exception:
            return None

    def _scan_ports(self, ip, start, end):
        threads = []
        for port in range(start, end + 1):
            t = threading.Thread(target=self._scan_port, args=(ip, port))
            threads.append(t)
            t.start()
            if len(threads) >= 100:
                for t in threads:
                    t.join()
                threads = []
        for t in threads:
            t.join()

    def _get_service(self, port):
        return PORTS.get(port, "Unknown")

    def _print_results(self, ip, elapsed):
        print(colored("\n" + "\u2550" * 45, "36"))
        print(colored("            SCAN RESULTS               ", "36"))
        print(colored("\u2550" * 45, "36"))
        print(f"  Target: {ip}")
        print(f"  Time: {elapsed:.2f}s")
        if self.open_ports:
            print(f"  Open ports: {len(self.open_ports)}")
            for p in sorted(self.open_ports, key=lambda x: x["port"]):
                bn = f" - {p['banner']}" if p.get("banner") else ""
                print(f"    {p['port']}/tcp   {p['service']}{bn}")
        else:
            print(colored("  [!] No open ports found", "31"))
        print(colored("\u2550" * 45 + "\n", "36"))
