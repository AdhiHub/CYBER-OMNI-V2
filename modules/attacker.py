import os
import sys
import subprocess
import shutil
from core.utils import colored

TOOLS = {
    "nmap": {"pkg": "nmap", "desc": "Network scanner"},
    "hydra": {"pkg": "hydra", "desc": "Password brute-forcer"},
    "sqlmap": {"pkg": "sqlmap", "desc": "SQL injection tool"},
    "gobuster": {"pkg": "gobuster", "desc": "Directory brute-forcer"},
    "hashcat": {"pkg": "hashcat", "desc": "Hash cracker"},
    "john": {"pkg": "john", "desc": "John the Ripper hash cracker"},
    "aircrack-ng": {"pkg": "aircrack-ng", "desc": "Wireless auditing"},
    "metasploit": {"pkg": "metasploit-framework", "desc": "Exploit framework"},
    "nikto": {"pkg": "nikto", "desc": "Web server scanner"},
    "whatweb": {"pkg": "whatweb", "desc": "Web technology detector"},
    "wpscan": {"pkg": "wpscan", "desc": "WordPress scanner"},
    "dnsrecon": {"pkg": "dnsrecon", "desc": "DNS enumeration"},
    "theharvester": {"pkg": "theharvester", "desc": "Email/domain OSINT"},
    "xsser": {"pkg": "xsser", "desc": "XSS framework"},
    "wfuzz": {"pkg": "wfuzz", "desc": "Web fuzzer"},
    "dirb": {"pkg": "dirb", "desc": "Directory scanner"},
    "netcat": {"pkg": "netcat-openbsd", "desc": "Network Swiss Army knife"},
}


class AttackerModule:
    def __init__(self):
        self.running = False

    def list_tools(self):
        print(colored("\nAvailable Tools:", "36"))
        print(colored("=" * 50, "36"))
        for name, info in TOOLS.items():
            status = "\033[32m\u2713\033[0m" if shutil.which(name) else "\033[31m\u2717\033[0m"
            print(f"  {status} {name:<15} {info['desc']}")
        print()

    def check_tool(self, name):
        return shutil.which(name) is not None

    def install_tool(self, name):
        if name not in TOOLS:
            print(colored(f"[!] Unknown tool: {name}", "31"))
            return False
        if self.check_tool(name):
            print(colored(f"[+] {name} already installed", "32"))
            return True
        pkg = TOOLS[name]["pkg"]
        print(colored(f"[*] Installing {name} ({pkg})...", "33"))

        installers = [
            (["apt", "install", "-y", pkg], "apt"),
            (["pkg", "install", "-y", pkg], "pkg"),
            (["pacman", "-S", "--noconfirm", pkg], "pacman"),
            (["brew", "install", pkg], "brew"),
        ]

        for cmd, mgr in installers:
            if shutil.which(mgr):
                try:
                    subprocess.run(cmd, check=True, timeout=120,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(colored(f"[+] {name} installed via {mgr}", "32"))
                    return True
                except Exception:
                    continue

        print(colored(f"[!] Failed to install {name}. Install manually: apt install {pkg}", "31"))
        return False

    def install_missing(self, needed):
        missing = [t for t in needed if not self.check_tool(t)]
        if not missing:
            print(colored("[+] All tools available", "32"))
            return True
        print(colored(f"[*] Missing tools: {', '.join(missing)}", "33"))
        for t in missing:
            if input(f"  Install {t}? [Y/n]: ").strip().lower() not in ("n", "no"):
                self.install_tool(t)
        return all(self.check_tool(t) for t in needed)

    def run_cmd(self, cmd, timeout=300, use_tor=False):
        if use_tor and shutil.which("torsocks"):
            cmd = f"torsocks {cmd}"
        print(colored(f"\n[*] Running: {cmd}", "33"))
        print(colored("[*] Press Ctrl+C to stop\n", "31"))

        self.running = True
        try:
            process = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )

            for line in process.stdout:
                if not self.running:
                    process.terminate()
                    break
                print(line, end="", flush=True)

            process.wait(timeout=timeout)
            self.running = False
            return process.returncode

        except subprocess.TimeoutExpired:
            process.kill()
            print(colored(f"\n[!] Command timed out ({timeout}s)", "31"))
            self.running = False
            return -1
        except KeyboardInterrupt:
            process.terminate()
            print(colored("\n[!] Stopped by user", "31"))
            self.running = False
            return -1
        except Exception as e:
            print(colored(f"\n[!] Error: {e}", "31"))
            self.running = False
            return -1

    def suggest_attack(self, service, port):
        attacks = {
            "FTP": ["hydra -l admin -P passwords.txt ftp://<target>",
                     "nmap --script ftp-anon,ftp-bounce <target>"],
            "SSH": ["hydra -l root -P passwords.txt ssh://<target>",
                     "nmap --script ssh2-enum-algos <target>"],
            "HTTP": ["gobuster dir -u http://<target> -w /usr/share/wordlists/dirb/common.txt",
                      "nikto -h http://<target>",
                      "sqlmap -u http://<target>/page?id=1 --batch --dump"],
            "HTTPS": ["nikto -h https://<target>",
                       "nmap --script ssl-enum-ciphers -p 443 <target>"],
            "SMB": ["nmap --script smb-enum-shares,smb-vuln-* -p 445 <target>",
                     "smbclient -L //<target> -N"],
            "RDP": ["nmap --script rdp-vuln-ms12-020 -p 3389 <target>"],
            "MySQL": ["hydra -l root -P passwords.txt mysql://<target>"],
            "MSSQL": ["hydra -l sa -P passwords.txt mssql://<target>"],
            "Redis": ["redis-cli -h <target> info"],
            "MongoDB": ["nmap --script mongodb-info -p 27017 <target>"],
            "DNS": ["dnsrecon -d <target> -t axfr",
                     "dnsrecon -d <target> -D subdomains.txt -t brt"],
            "SMTP": ["nmap --script smtp-enum-users -p 25 <target>"],
            "Telnet": ["hydra -l admin -P passwords.txt telnet://<target>"],
            "VNC": ["hydra -P passwords.txt vnc://<target>"],
        }

        if service in attacks:
            print(colored(f"\n\u250c\u2500\u2500\u2500 Attack suggestions for {service} (port {port}) \u2500\u2500\u2500\u2500\u2510", "31"))
            for i, attack in enumerate(attacks[service], 1):
                print(f"\u2502  {i}. {attack}")
            print(colored("\u2514" + "\u2500" * 50 + "\u2518", "31"))
            print()
            choice = input(f"Run attack number (or Enter to skip): ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(attacks[service]):
                    cmd = attacks[service][idx].replace("<target>", str(self.last_target))
                    self.run_cmd(cmd)
        else:
            print(colored(f"[!] No pre-built attacks for {service}", "33"))

    def run(self, target):
        self.last_target = target
        print(colored(f"[*] Attack module loaded for target: {target}", "31"))
        print(colored("[!] Only use on systems you OWN or have WRITTEN PERMISSION to test!", "31"))

        if not self.install_missing(["nmap", "hydra", "gobuster", "nikto"]):
            print(colored("[!] Some tools missing. Functionality limited.", "33"))

        print(colored("\nQuick scan to find open services...", "33"))
        from modules.scan import ScanModule
        sm = ScanModule()
        sm.run(target)

        print(colored("\nAvailable attack vectors from scan...", "36"))
        print(colored("=" * 50, "36"))
        for p in sm.open_ports:
            self.suggest_attack(p["service"], p["port"])
