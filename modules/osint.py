import socket
import subprocess
from core.utils import validate_target, resolve_target, get_timestamp, colored


class OSINTModule:
    def __init__(self):
        self.results = {}

    def run(self, target):
        target = validate_target(target)
        print(colored(f"[*] Starting OSINT gathering on {target}...", "33"))
        self.results["target"] = target
        self.results["timestamp"] = get_timestamp()
        self._dns_enum(target)
        self._whois_lookup(target)
        self._subdomain_scan(target)
        self._http_info(target)
        self._email_suggestions(target)
        self._print_summary()

    def _dns_enum(self, target):
        print(colored("\n[*] DNS Enumeration...", "33"))
        try:
            ip = socket.gethostbyname(target)
            print(f"  A Record: {target} -> {ip}")
            self.results["a_record"] = ip
        except socket.gaierror:
            print(colored("  [!] DNS A record failed", "31"))
        try:
            addrs = socket.getaddrinfo(target, 80, socket.AF_INET6, socket.SOCK_STREAM)
            for addr in addrs:
                print(f"  AAAA Record: {addr[4][0]}")
        except Exception:
            pass
        try:
            result = subprocess.run(["nslookup", "-type=MX", target], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                mx = [l.strip() for l in result.stdout.split("\n") if "mail exchanger" in l.lower()]
                for m in mx:
                    print(f"  MX: {m}")
        except Exception:
            print(colored("  [!] MX lookup unavailable (nslookup not found)", "33"))
        try:
            result = subprocess.run(["nslookup", "-type=NS", target], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                ns = [l.strip() for l in result.stdout.split("\n") if "nameserver" in l.lower() and "nameserver" not in l.lower()[:2]]
                for n in ns:
                    print(f"  NS: {n}")
        except Exception:
            pass

    def _whois_lookup(self, target):
        print(colored("\n[*] WHOIS Lookup...", "33"))
        try:
            result = subprocess.run(["whois", target], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split("\n")
                important = []
                for line in lines:
                    ll = line.lower()
                    if any(kw in ll for kw in ["registrar", "creation date", "expir", "name server",
                                                "org:", "admin", "tech", "registrant"]):
                        important.append(line.strip())
                if important:
                    for line in important[:12]:
                        print(f"  {line}")
                else:
                    print("  [!] No key WHOIS data parsed")
            else:
                print("  [!] whois command not found/returned error")
        except FileNotFoundError:
            print(colored("  [!] WHOIS not installed. Install with: apt install whois", "33"))
        except Exception as e:
            print(colored(f"  [!] WHOIS lookup failed: {e}", "31"))

    def _subdomain_scan(self, target):
        print(colored("\n[*] Subdomain Discovery (common subdomains)...", "33"))
        common = ["www", "mail", "admin", "blog", "dev", "test", "api", "cdn",
                   "app", "portal", "secure", "vpn", "remote", "webmail", "forum",
                   "shop", "store", "m", "mobile", "ftp", "dns", "ns1", "ns2",
                   "smtp", "pop", "imap", "server", "git", "jenkins", "jira",
                   "wiki", "confluence", "help", "support", "status", "stage",
                   "staging", "backup", "mail2", "admin2", "ssl", "proxy"]
        found = []
        for sub in common:
            hostname = f"{sub}.{target}"
            try:
                ip = socket.gethostbyname(hostname)
                print(f"  [+] {hostname} -> {ip}")
                found.append({"subdomain": hostname, "ip": ip})
            except socket.gaierror:
                pass
        if not found:
            print("  [!] No common subdomains resolved")
        else:
            print(colored(f"  [*] Found {len(found)} subdomains", "32"))
        self.results["subdomains"] = found

    def _http_info(self, target):
        print(colored("\n[*] HTTP Target Information...", "33"))
        import http.client
        for scheme, port, conn_cls in [("HTTPS", 443, http.client.HTTPSConnection),
                                        ("HTTP", 80, http.client.HTTPConnection)]:
            try:
                conn = conn_cls(target, timeout=5)
                conn.request("GET", "/")
                resp = conn.getresponse()
                data = resp.read(512)
                print(f"  [{scheme}] Status: {resp.status} {resp.reason}")
                print(f"    Server: {resp.getheader('Server', 'N/A')}")
                print(f"    X-Powered-By: {resp.getheader('X-Powered-By', 'N/A')}")
                print(f"    Content-Type: {resp.getheader('Content-Type', 'N/A')}")
                title = ""
                try:
                    text = data.decode("utf-8", errors="ignore")
                    if "<title>" in text:
                        title = text.split("<title>")[1].split("</title>")[0].strip()
                except Exception:
                    pass
                if title:
                    print(f"    Page Title: {title}")
                conn.close()
                break
            except Exception:
                continue
        else:
            print("  [!] No HTTP response obtained")

    def _email_suggestions(self, target):
        print(colored("\n[*] OSINT Techniques for this target...", "33"))
        domain = target
        suggestions = [
            f"  Email: theHarvester -d {domain} -b google,linkedin,bing",
            f"  Dork: site:{domain} filetype:pdf|doc|xls|sql|env|bak",
            f"  Certs: https://crt.sh/?q=%25.{domain}",
            f"  GitHub search: \"@{domain}\" OR \"{domain.split('.')[0]}\"",
            f"  Shodan: hostname:{domain}",
            f"  Wayback: https://web.archive.org/web/*/{domain}",
            f"  DNS dumpster: https://dnsdumpster.com/",
        ]
        for s in suggestions:
            print(s)
        self.results["techniques"] = suggestions

    def _print_summary(self):
        print(colored("\n" + "\u2550" * 45, "36"))
        print(colored("           OSINT SUMMARY               ", "36"))
        print(colored("\u2550" * 45, "36"))
        print(f"  Target: {self.results.get('target')}")
        print(f"  Timestamp: {self.results.get('timestamp')}")
        subs = self.results.get("subdomains", [])
        if subs:
            print(f"  Subdomains: {len(subs)}")
        print(colored("\u2550" * 45 + "\n", "36"))
