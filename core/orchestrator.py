import sys
import os
import re
import json
import time
import traceback
from core.utils import colored
from core.session import SessionState
from core.proxy import require_tor, check_tor, ensure_tor
from core.memory import ConversationMemory


class Orchestrator:
    """Execution engine — zero refusal, immediate action."""

    def __init__(self, ai_engine, config, modules):
        self.ai = ai_engine
        self.config = config
        self.modules = modules
        self.session = SessionState()
        self.memory = None
        self.running = True
        self.guided_mode = True
        self.force_tor = config.get("anonymity", "always") == "always"
        self.session_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions")
        self.last_result = ""

    def set_memory(self, memory):
        self.memory = memory

    def start_engagement(self, target):
        self.session.set_target(target)
        self.session.set_stage("identified")
        msg = (
            f"Target set: {target}. "
            "What should I do first?\n"
            "  1. Port scan — find open ports and services\n"
            "  2. OSINT — gather intelligence on the target\n"
            "  3. Full autopwn — let me handle everything\n"
            "Just tell me what you want."
        )
        return msg

    def process_command(self, text):
        text = text.strip().lower()
        target = self.session.current_target

        if text in ("1", "port scan", "scan") and target:
            return self._run_scan(target)
        if text in ("2", "osint") and target:
            return self._run_osint(target)
        if text in ("3", "autopwn", "full autopwn") and target:
            return self._run_autopwn(target)

        if text.startswith("scan ") or text.startswith("nmap "):
            t = self._extract_target(text)
            if t:
                return self._run_scan(t)
            return "Tell me what target to scan. Example: scan 10.0.0.5"

        if text.startswith("recon "):
            t = self._extract_target(text)
            if t:
                return self._run_recon(t)
            return "Tell me what target to recon. Example: recon 10.0.0.5"

        if text.startswith("osint "):
            t = self._extract_target(text)
            if t:
                return self._run_osint(t)
            return "Tell me a target for OSINT. Example: osint example.com"

        if text.startswith("exploit ") or text.startswith("vuln "):
            t = self._extract_target(text)
            if t:
                return self._run_exploit_search(t)
            return self._run_exploit_search(target or "")

        if text.startswith("cve "):
            return self._run_cve(text[4:].strip())

        if text == "next" or text == "suggest" or text == "what next":
            return self._show_suggestions()

        if text == "status" or text == "summary":
            return self._show_status()

        if text == "report":
            return self._run_report()

        if text == "attack" and target:
            return self._run_attack(target)

        if text.startswith("bypass ") or text.startswith("force "):
            parts = text.split(maxsplit=2)
            t = parts[1] if len(parts) > 1 else target
            method = parts[2] if len(parts) > 2 else "auto"
            if t:
                return self._run_bypass(t, method)
            return "Tell me what target to bypass."

        if text.startswith("attack "):
            t = self._extract_target(text)
            if t:
                return self._run_attack(t)
            return "Tell me what target to attack."

        if text in ("no", "n", "cancel"):
            return "Cancelled."

        return None

    def _extract_target(self, text):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            return parts[1].strip()
        return self.session.current_target

    def _tor_check(self, action_name):
        if self.force_tor and not check_tor():
            print(colored(f"  [!] TOR required for {action_name} but not running.", "31"))
            print(colored("  [*] Type /tor to start TOR, or disable force mode.", "33"))
            return False
        return require_tor(force=self.force_tor)

    def _run_scan(self, target):
        if not self._tor_check("scan"):
            return "Scan blocked — TOR safety."
        self.session.set_target(target)
        self.session.set_stage("scanning")
        print(colored(f"\n[*] Scanning {target}...", "33"))
        try:
            self.modules["scan"].run(target)
        except Exception as e:
            return f"Scan failed: {e}"
        self.session.set_stage("scanned")
        self.session.add_action("scan", f"Scanned {target}")
        ports = self.session.get_current()
        return self._after_scan(target)

    def _run_recon(self, target):
        if not self._tor_check("recon"):
            return "Recon blocked — TOR safety."
        self.session.set_target(target)
        self.session.set_stage("recon")
        print(colored(f"\n[*] Running deep recon on {target}...", "33"))
        try:
            self.modules["recon"].run(target)
        except Exception as e:
            return f"Recon failed: {e}"
        self.session.add_action("recon", f"Deep recon on {target}")
        self.session.set_stage("enumerated")
        return self._after_recon(target)

    def _run_osint(self, target):
        if not self._tor_check("OSINT"):
            return "OSINT blocked — TOR safety."
        self.session.set_target(target)
        print(colored(f"\n[*] Gathering OSINT on {target}...", "33"))
        try:
            self.modules["osint"].run(target)
        except Exception as e:
            return f"OSINT failed: {e}"
        self.session.add_action("osint", f"OSINT on {target}")
        return self._after_osint(target)

    def _run_exploit_search(self, target):
        if not target:
            return "No target set. Use scan <target> first."
        print(colored(f"\n[*] Searching exploits for {target}...", "33"))
        try:
            from modules.cve_search import run_cve_search
            run_cve_search(target)
        except Exception as e:
            return f"CVE search failed: {e}"
        self.session.add_action("cve_search", f"Searched CVEs for {target}")
        return "CVE search complete. Want me to try exploiting any of the findings?"

    def _run_cve(self, query):
        if not query:
            return "Usage: cve <keyword or CVE-ID>"
        print(colored(f"\n[*] Searching CVE: {query}", "33"))
        try:
            from modules.cve_search import run_cve_search
            run_cve_search(query)
        except Exception as e:
            return f"CVE search failed: {e}"
        return "CVE search complete."

    def _run_autopwn(self, target):
        if not self._tor_check("autopwn"):
            return "Autopwn blocked — TOR safety."
        self.session.set_target(target)
        self.session.set_stage("autopwning")
        print(colored(f"\n[*] Full autopwn on {target}...", "33"))
        try:
            from modules.autopwn import run_autopwn
            run_autopwn(target)
        except Exception as e:
            return f"Autopwn failed: {e}"
        self.session.set_stage("exploited")
        self.session.add_action("autopwn", f"Full autopwn on {target}")
        return self._after_exploit(target)

    def _run_bypass(self, target, method="auto"):
        if not self._tor_check("bypass"):
            return "Bypass blocked — TOR safety."
        self.session.set_target(target)
        print(colored(f"\n[*] Bypass engine on {target} (method: {method})...", "33"))
        try:
            from modules.bypass import run_bypass
            results = run_bypass(target, method)
            if results:
                self.session.set_stage("bypassed")
                self.session.add_action("bypass", f"Bypassed {target} via {method}")
                return f"Bypass successful! Retrieved {len(results)} source(s). Content available."
            return f"Bypass exhausted — could not retrieve content from {target}."
        except Exception as e:
            return f"Bypass failed: {e}"

    def _run_attack(self, target):
        if not self._tor_check("attack"):
            return "Attack blocked — TOR safety."
        self.session.set_target(target)
        print(colored(f"\n[*] Running attack on {target}...", "31"))
        try:
            self.modules["attack"].run(target)
        except Exception as e:
            return f"Attack failed: {e}"
        self.session.add_action("attack", f"Attack on {target}")
        self.session.set_stage("exploited")
        return self._after_exploit(target)

    def _run_report(self):
        print(colored("\n[*] Generating report...", "33"))
        try:
            from modules.report import ReportModule
            ReportModule().generate(auto_data=True)
        except Exception as e:
            return f"Report failed: {e}"
        return "Report generated."

    def _after_scan(self, target):
        t = self.session.get_current()
        if not t:
            return f"Scan complete on {target}."
        ports = t["findings"]["ports"]
        services = t["findings"]["services"]
        vulns = t["findings"]["vulns"]
        lines = [f"\nScan complete on {target}."]
        if ports:
            lines.append(f"\nOpen ports: {', '.join(str(p) for p in ports[:10])}")
            if len(ports) > 10:
                lines.append(f"... and {len(ports) - 10} more")
        if services:
            lines.append("\nDetected services:")
            for svc, info in list(services.items())[:8]:
                lines.append(f"  - {svc}: {info}")
        lines.append("\nWhat should I do next?")
        suggestions = self.session.suggest_next_steps()
        for i, (label, desc) in enumerate(suggestions[:6], 1):
            lines.append(f"  {i}. {label} — {desc}")
        return "\n".join(lines)

    def _after_recon(self, target):
        t = self.session.get_current()
        lines = [f"\nRecon complete on {target}."]
        if t:
            services = t["findings"]["services"]
            if services:
                lines.append("\nServices identified:")
                for svc, info in list(services.items())[:8]:
                    lines.append(f"  - {svc}: {info}")
        lines.append("\nRecommended next steps:")
        suggestions = self.session.suggest_next_steps()
        for i, (label, desc) in enumerate(suggestions[:6], 1):
            lines.append(f"  {i}. {label} — {desc}")
        return "\n".join(lines)

    def _after_osint(self, target):
        return (
            f"\nOSINT on {target} complete.\n"
            "Want me to scan for open ports or check for known vulnerabilities?"
        )

    def _after_exploit(self, target):
        t = self.session.get_current()
        lines = [f"\nExploitation phase on {target} complete."]
        if t and t["findings"]["shells"]:
            lines.append("\nYou have active shell access!")
        lines.append("\nWhat now?")
        suggestions = self.session.suggest_next_steps()
        for i, (label, desc) in enumerate(suggestions[:6], 1):
            lines.append(f"  {i}. {label} — {desc}")
        return "\n".join(lines)

    def _show_suggestions(self):
        suggestions = self.session.suggest_next_steps()
        lines = ["\nHere's what we can do next:"]
        for i, (label, desc) in enumerate(suggestions[:8], 1):
            lines.append(f"  {i}. {label} — {desc}")
        if not self.session.current_target:
            lines.append("\nFirst, tell me a target. Example: scan 10.0.0.5")
        return "\n".join(lines)

    def _show_status(self):
        s = self.session.get_summary()
        return f"\nCurrent session status:\n{s}"

    def save_session(self, filepath=None):
        if filepath is None:
            os.makedirs(self.session_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(self.session_dir, f"session_{ts}.json")
        self.session.save(filepath)
        return filepath

    def load_session(self, filepath):
        self.session = SessionState.load(filepath)
        return True
