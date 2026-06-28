import os
import json
import time
from datetime import datetime


class SessionState:
    def __init__(self):
        self.targets = {}
        self.current_target = None
        self.current_stage = "idle"
        self.engagement_name = None
        self.start_time = time.time()

    def set_target(self, target):
        if target not in self.targets:
            self.targets[target] = {
                "target": target,
                "stage": "identified",
                "findings": {
                    "ports": [],
                    "services": {},
                    "vulns": [],
                    "osint": {},
                    "notes": "",
                    "shells": [],
                },
                "actions_taken": [],
                "first_seen": datetime.now().isoformat(),
                "last_action": None,
            }
        self.current_target = target
        self.current_stage = self.targets[target]["stage"]

    def add_finding(self, category, data):
        if not self.current_target:
            return
        t = self.targets[self.current_target]
        if category == "ports":
            for p in data:
                if p not in t["findings"]["ports"]:
                    t["findings"]["ports"].append(p)
        elif category == "services":
            t["findings"]["services"].update(data)
        elif category == "vulns":
            for v in data:
                if v not in t["findings"]["vulns"]:
                    t["findings"]["vulns"].append(v)
        elif category == "osint":
            t["findings"]["osint"].update(data)
        elif category == "shells":
            t["findings"]["shells"].append(data)

    def add_action(self, action, result_summary=""):
        if not self.current_target:
            return
        t = self.targets[self.current_target]
        t["actions_taken"].append({
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "result": result_summary,
        })
        t["last_action"] = action

    def set_stage(self, stage):
        if self.current_target:
            self.targets[self.current_target]["stage"] = stage
        self.current_stage = stage

    def get_current(self):
        if self.current_target and self.current_target in self.targets:
            return self.targets[self.current_target]
        return None

    def get_summary(self):
        t = self.get_current()
        if not t:
            return "No target selected."
        lines = [
            f"Target: {t['target']}",
            f"Stage: {t['stage']}",
            f"Open ports: {len(t['findings']['ports'])}",
            f"Services: {len(t['findings']['services'])}",
            f"Vulns found: {len(t['findings']['vulns'])}",
            f"Actions taken: {len(t['actions_taken'])}",
        ]
        if t["findings"]["shells"]:
            lines.append(f"Active shells: {len(t['findings']['shells'])}")
        return "\n".join(lines)

    def suggest_next_steps(self):
        t = self.get_current()
        if not t:
            return ["Tell me a target to begin with. Example: scan 10.0.0.5"]
        stage = t["stage"]
        suggestions = []
        ports = t["findings"]["ports"]
        services = t["findings"]["services"]
        vulns = t["findings"]["vulns"]
        shells = t["findings"]["shells"]

        if stage == "identified":
            suggestions.append(("Scan ports", f"Run nmap on {t['target']}"))
        elif stage == "scanned":
            if ports:
                suggestions.append(("Enumerate services", "Run detailed service detection"))
                suggestions.append(("Vuln scan", "Run vulnerability scan on open ports"))
            suggestions.append(("OSINT", f"Gather OSINT on {t['target']}"))
        elif stage in ("recon", "enumerated"):
            if not vulns:
                suggestions.append(("Find exploits", "Search CVEs and exploits for detected services"))
            if services:
                for svc, info in services.items():
                    if svc in ("http", "https", "80", "443", "8080"):
                        suggestions.append(("Web audit", "Run nikto/gobuster/wpscan on web service"))
                    if svc in ("ssh", "22"):
                        suggestions.append(("Brute force SSH", "Run hydra on SSH"))
                    if svc in ("ftp", "21"):
                        suggestions.append(("Brute force FTP", "Run hydra on FTP"))
                    if svc in ("mysql", "3306"):
                        suggestions.append(("MySQL enum", "Enumerate MySQL databases"))
                    if svc in ("smb", "445", "139"):
                        suggestions.append(("SMB enum", "Enumerate SMB shares"))
            if vulns:
                suggestions.append(("Exploit", "Run exploit against found vulnerabilities"))
        elif stage == "exploited":
            if shells:
                suggestions.append(("Interact with shell", "Use the active shell connection"))
                suggestions.append(("Escalate privileges", "Run privilege escalation"))
            suggestions.append(("Extract data", "Extract data from compromised target"))
            suggestions.append(("Pivot", "Use target as pivot point"))
        elif stage == "postexploit":
            suggestions.append(("Clean up", "Remove traces from target"))
            suggestions.append(("Generate report", "Generate pentest report"))

        suggestions.append(("Full autopwn", "Let me handle everything automatically"))
        return suggestions

    def to_dict(self):
        return {
            "targets": self.targets,
            "current_target": self.current_target,
            "current_stage": self.current_stage,
            "engagement_name": self.engagement_name,
            "start_time": self.start_time,
            "duration": time.time() - self.start_time,
        }

    def save(self, filepath):
        data = self.to_dict()
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath):
        s = cls()
        if os.path.exists(filepath):
            with open(filepath) as f:
                data = json.load(f)
            s.targets = data.get("targets", {})
            s.current_target = data.get("current_target")
            s.current_stage = data.get("current_stage", "idle")
            s.engagement_name = data.get("engagement_name")
            s.start_time = data.get("start_time", time.time())
        return s
