import os
import re
import subprocess
import json
import time
from datetime import datetime
from core.utils import colored
from core.proxy import check_tor


class AutoPentestPipeline:
    def __init__(self):
        self.target = ""
        self.results = {
            "target": "",
            "start_time": "",
            "end_time": "",
            "recon": {},
            "scan": {},
            "exploit": [],
            "post_exploit": [],
            "summary": ""
        }
        self.log_file = ""

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(colored(f"  [{ts}] {msg}", "36"))
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(f"[{ts}] {msg}\n")

    def _run(self, cmd, timeout=120):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=True)
            return r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            return "[TIMEOUT]"
        except Exception as e:
            return str(e)

    def _save(self, name, data):
        path = f"reports/{name}"
        if isinstance(data, (dict, list)):
            with open(path + ".json", "w") as f:
                json.dump(data, f, indent=2)
            return path + ".json"
        with open(path + ".txt", "w") as f:
            f.write(str(data))
        return path + ".txt"

    def phase_recon(self):
        self._log("Phase 1/5: Reconnaissance")
        results = {}

        self._log("  Resolving DNS...")
        dns = self._run(f"nslookup {self.target} 2>&1 || host {self.target} 2>&1")
        results["dns"] = dns[:500]

        self._log("  Checking WHOIS...")
        whois = self._run(f"whois {self.target} 2>&1 || echo 'whois not available'")
        results["whois"] = whois[:300]

        self._log("  Checking HTTP service...")
        http = self._run(f"curl -s -I -L --max-time 15 'http://{self.target}' 2>&1")
        results["http_headers"] = http[:500]

        self._log("  Checking HTTPS service...")
        https = self._run(f"curl -s -I -L --max-time 15 'https://{self.target}' 2>&1")
        results["https_headers"] = https[:500]

        path = self._save(f"autopwn_recon_{self.target}", results)
        self.results["recon"] = results
        self._log(f"  Recon complete -> {path}")
        return results

    def phase_scan(self):
        self._log("Phase 2/5: Port Scanning")

        self._log("  Quick scan (top 100 ports)...")
        quick = self._run(f"nmap -F -T4 --open {self.target} 2>&1 || echo 'nmap not available'")
        self._save(f"autopwn_scan_quick_{self.target}", quick)

        ports = re.findall(r"(\d+)/tcp\s+open", quick)
        if not ports:
            self._log("  No open ports found in quick scan")
            self.results["scan"]["ports"] = []
            return []

        self._log(f"  Found {len(ports)} open port(s): {', '.join(ports)}")

        self._log("  Service version detection...")
        verbose = self._run(f"nmap -sV -sC -p{','.join(ports)} --open {self.target} 2>&1")
        self._save(f"autopwn_scan_deep_{self.target}", verbose)

        services = []
        for p in ports:
            svc_match = re.search(rf"{p}/tcp\s+open\s+(\S+)\s+(.+)", verbose)
            if svc_match:
                services.append({"port": p, "service": svc_match.group(1), "version": svc_match.group(2).strip()})
            else:
                services.append({"port": p, "service": "unknown", "version": ""})

        self.results["scan"]["ports"] = services
        self._log(f"  Scan complete — {len(services)} services identified")
        return services

    def phase_exploit(self, services):
        self._log("Phase 3/5: Exploitation")
        exploited = []

        for svc in services:
            port = svc["port"]
            service = svc["service"].lower()
            version = svc["version"]

            self._log(f"  Analyzing {service} on port {port}...")

            suggestions = []
            if "ssh" in service:
                suggestions.append(f"hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://{self.target}:{port}")
                suggestions.append(f"nmap --script ssh2-enum-algos,ssh-hostkey {self.target} -p {port}")
            elif "http" in service or "https" in service:
                suggestions.append(f"gobuster dir -u http://{self.target}:{port} -w /usr/share/wordlists/dirb/common.txt")
                suggestions.append(f"nikto -h {self.target}:{port}")
                suggestions.append(f"sqlmap -u 'http://{self.target}:{port}/' --batch --crawl=2")
            elif "mysql" in service:
                suggestions.append(f"hydra -l root -P /usr/share/wordlists/rockyou.txt mysql://{self.target}:{port}")
                suggestions.append("mysql -h {self.target} -u root")
            elif "ftp" in service:
                suggestions.append(f"hydra -l ftp -P /usr/share/wordlists/rockyou.txt ftp://{self.target}:{port}")
            elif "smb" in service or "microsoft-ds" in service:
                suggestions.append(f"smbclient -L //{self.target}/")
                suggestions.append(f"nmap --script smb-enum-shares,smb-os-discovery {self.target} -p {port}")
            elif "rdp" in service:
                suggestions.append(f"crackmapexec rdp {self.target} -u admin -p /usr/share/wordlists/rockyou.txt")
            elif "telnet" in service:
                suggestions.append(f"hydra -l root -P /usr/share/wordlists/rockyou.txt telnet://{self.target}:{port}")

            if suggestions:
                exploited.append({"port": port, "service": service, "attacks": suggestions})
                self._log(f"  {len(suggestions)} attack suggestions for {service}")

        path = self._save(f"autopwn_exploit_{self.target}", exploited)
        self.results["exploit"] = exploited
        self._log(f"  Exploit plan saved -> {path}")
        return exploited

    def phase_post_exploit(self):
        self._log("Phase 4/5: Post-Exploitation")
        self._log("  (Skeleton — extend with real post-exploit modules)")
        self.results["post_exploit"] = [{"note": "Post-exploitation phase ready for extensibility"}]

    def phase_report(self):
        self._log("Phase 5/5: Report Generation")
        self.results["end_time"] = datetime.now().isoformat()

        services = self.results["scan"].get("ports", [])
        exploits = self.results.get("exploit", [])

        total_ports = len(services)
        total_attacks = sum(len(e.get("attacks", [])) for e in exploits)

        self.results["summary"] = (
            f"Auto-pentest completed for {self.target}. "
            f"Found {total_ports} open ports across {len(services)} services. "
            f"Generated {total_attacks} attack suggestions."
        )

        path = self._save(f"autopwn_report_{self.target}", self.results)
        self._log(f"  Report saved -> {path}")
        return path

    def run(self, target):
        self.target = target
        self.results["target"] = target
        self.results["start_time"] = datetime.now().isoformat()
        self.log_file = f"reports/autopwn_{target.replace('/', '_')}.log"

        os.makedirs("reports", exist_ok=True)

        print(colored(f"\n{'═' * 55}", "36"))
        print(colored(f"  AUTO-PENTEST PIPELINE — {target}", "36"))
        print(colored(f"{'═' * 55}\n", "36"))

        try:
            self.phase_recon()
            print()

            services = self.phase_scan()
            print()

            if services:
                self.phase_exploit(services)
            else:
                self._log("Skipping exploit phase — no services found")
            print()

            self.phase_post_exploit()
            print()

            self.phase_report()
            print()

            print(colored(f"{'═' * 55}", "36"))
            print(colored(f"  PIPELINE COMPLETE", "32"))
            print(colored(f"  Report: reports/autopwn_report_{target}.json", "33"))
            print(colored(f"  Log: {self.log_file}", "33"))
            print(colored(f"{'═' * 55}", "36"))

        except KeyboardInterrupt:
            self._log("Pipeline interrupted by user")
        except Exception as e:
            self._log(f"Pipeline error: {e}")

        return self.results


def run_autopwn(target):
    if not target:
        print(colored("[!] Usage: /autopwn <target>", "31"))
        return
    pipeline = AutoPentestPipeline()
    pipeline.run(target)
