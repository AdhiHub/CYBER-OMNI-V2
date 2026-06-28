import socket
import http.client
from core.utils import validate_target, resolve_target, get_timestamp, colored


class ReconModule:
    def __init__(self):
        self.results = {}

    def run(self, target):
        target = validate_target(target)
        print(colored(f"[*] Starting reconnaissance on {target}...", "33"))

        ip = resolve_target(target)
        if not ip:
            print(colored("[!] Could not resolve target", "31"))
            return

        print(colored(f"[+] Resolved to IP: {ip}", "32"))
        self.results["target"] = target
        self.results["ip"] = ip
        self.results["timestamp"] = get_timestamp()

        self._dns_recon(target)
        self._http_headers(target)
        self._quick_scan(ip)
        self._print_summary()

    def _dns_recon(self, target):
        print(colored("\n[*] DNS Reconnaissance...", "33"))
        try:
            ip = socket.gethostbyname(target)
            print(f"  A Record: {target} -> {ip}")
            try:
                addrs = socket.getaddrinfo(target, 80)
                seen = {ip}
                for info in addrs:
                    addr = info[4][0]
                    if addr not in seen:
                        print(f"  Additional IP: {addr}")
                        seen.add(addr)
            except Exception:
                pass
        except socket.gaierror:
            print(colored("  [!] DNS resolution failed", "31"))

    def _http_headers(self, target):
        print(colored("\n[*] HTTP Header Analysis...", "33"))
        for scheme, port in [("HTTPS", 443), ("HTTP", 80)]:
            try:
                conn_class = http.client.HTTPSConnection if scheme == "HTTPS" else http.client.HTTPConnection
                conn = conn_class(target, timeout=5)
                conn.request("GET", "/")
                resp = conn.getresponse()
                print(f"  [{scheme}] Status: {resp.status} {resp.reason}")
                interesting = ["Server", "X-Powered-By", "X-Frame-Options", "Strict-Transport-Security",
                               "Content-Security-Policy", "X-XSS-Protection", "X-Content-Type-Options",
                               "Set-Cookie", "WWW-Authenticate"]
                for h in interesting:
                    val = resp.getheader(h)
                    if val:
                        print(f"    {h}: {val}")
                conn.close()
                break
            except Exception:
                continue

    def _quick_scan(self, ip):
        print(colored("\n[*] Quick Port Scan (top 20 ports)...", "33"))
        top_ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995,
                     1433, 1521, 2049, 3306, 3389, 5432, 5900, 8080, 8443, 6379, 27017]
        open_ports = []
        for port in top_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((ip, port))
            if result == 0:
                service = self._get_port_service(port)
                print(f"  [+] Port {port}/tcp open - {service}")
                open_ports.append({"port": port, "service": service})
            sock.close()
        if not open_ports:
            print(colored("  [!] No open ports found on top-25 scan", "31"))
        self.results["open_ports"] = open_ports

    def _get_port_service(self, port):
        services = {
            21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
            80: "HTTP", 110: "POP3", 135: "RPC", 139: "NetBIOS", 143: "IMAP",
            443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S", 1433: "MSSQL",
            1521: "Oracle", 2049: "NFS", 3306: "MySQL", 3389: "RDP",
            5432: "PostgreSQL", 5900: "VNC", 8080: "HTTP-Proxy", 8443: "HTTPS-Alt",
            6379: "Redis", 27017: "MongoDB"
        }
        return services.get(port, "Unknown")

    def _print_summary(self):
        print(colored("\n" + "\u2550" * 45, "36"))
        print(colored("         RECONNAISSANCE SUMMARY        ", "36"))
        print(colored("\u2550" * 45, "36"))
        print(f"  Target: {self.results.get('target')}")
        print(f"  IP: {self.results.get('ip')}")
        print(f"  Timestamp: {self.results.get('timestamp')}")
        ports = self.results.get("open_ports", [])
        if ports:
            print(f"  Open Ports: {len(ports)}")
            for p in ports:
                print(f"    {p['port']}/tcp - {p['service']}")
        print(colored("\u2550" * 45 + "\n", "36"))
