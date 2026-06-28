#!/usr/bin/env python3
import sys
import os
import re
import json
import subprocess
import shutil
import traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LAST_ERROR = None
LAST_ERROR_CMDS = []

_MISSING_DEPS = []
try:
    from core.engine import AIEngine
    from core.memory import ConversationMemory
    from core.context import SYSTEM_PROMPT, WELCOME_MESSAGE, TOR_WARNING
from core.utils import print_banner, colored, clear_screen
from core.proxy import check_anonymity, start_tor, check_tor, tor_status, ensure_tor, require_tor, signal_new_identity, check_dns_leak, verify_full_anonymity, spoof_mac
from core.orchestrator import Orchestrator
    from modules.scan import ScanModule
    from modules.recon import ReconModule
    from modules.osint import OSINTModule
    from modules.exploit import ExploitModule
    from modules.report import ReportModule
    from modules.attacker import AttackerModule, TOOLS
    from core.websearch import WebSearch
    from core.setup import setup_wizard, load_config, save_config, get_system_prompt_extra, show_mode_info, ask_feedback, MODES
    from core.camouflage import stealth_gate, setup_stealth, get_fake_page, randomize_style
    from core.plugin_manager import PluginManager
    from core.knowledge import learn_file, query_knowledge, KnowledgeBase
    from modules.extractor import run_extraction
    from modules.autopwn import run_autopwn
    from modules.payload_factory import run_payload
    from modules.cve_search import run_cve_search
    from modules.exploitdb import run_exploitdb_search
    from modules.listener import run_listener
    from modules.subtake import run_subtake
    from modules.target_queue import run_target_queue
except ImportError as _ie:
    _MISSING_DEPS.append(str(_ie))


SEPARATOR = colored("\u2500" * 55, "36")
SEP_THIN = colored("\u2504" * 55, "32")


def print_markdown(text):
    in_code = False
    code_lang = ""
    code_buf = []
    for line in text.split("\n"):
        if line.startswith("```"):
            if in_code:
                print(colored("```" + code_lang, "35"))
                for cl in code_buf:
                    print(colored(cl, "32"))
                print(colored("```", "35"))
                code_buf = []
                in_code = False
                code_lang = ""
            else:
                in_code = True
                code_lang = line[3:].strip()
                print(colored("```" + code_lang, "35"))
        elif in_code:
            code_buf.append(line)
        elif line.strip().startswith(("- ", "* ", "1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. ")):
            print(colored(line, "37"))
        else:
            print(line)
    if code_buf:
        for cl in code_buf:
            print(colored(cl, "32"))


class CyberOmni:
    def __init__(self):
        self.ai = AIEngine()
        self.config = setup_wizard()
        extra_prompt = get_system_prompt_extra(self.config)
        self.full_prompt = SYSTEM_PROMPT + extra_prompt

        self.modules = {
            "scan": ScanModule(),
            "recon": ReconModule(),
            "osint": OSINTModule(),
            "exploit": ExploitModule(),
            "report": ReportModule(),
            "attack": AttackerModule(),
        }
        self.attacker = AttackerModule()
        self.memory = ConversationMemory(max_turns=30, system_prompt=self.full_prompt)
        self.running = True
        self.session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")
        self.plugin_manager = PluginManager()
        self.dashboard_thread = None
        self.anonymity_checked = False
        self.feedback_count = 0
        self.force_tor = self.config.get("anonymity", "always") == "always"
        self.orchestrator = Orchestrator(self.ai, self.config, self.modules)
        if not ensure_tor():
            print(colored("  [!] TOR failed to start. Install TOR for anonymity.", "31"))

    def detect_tool_call(self, text):
        patterns = [
            (r"\bautopwn\s+(\S+)", "autopwn"),
            (r"\bpayload\s+(.+?)$", "payload"),
            (r"\bextract\s+(\S+)", "extract"),
            (r"\b(?:search|find|lookup)\s+(.+?)$", "search"),
            (r"\bdarkweb\s+(.+?)$", "darkweb"),
            (r"\bonion\s+(.+?)$", "darkweb"),
            (r"\b(?:scan|nmap)\s+(\S+)", "scan"),
            (r"\brecon(?:naissance)?\s+(\S+)", "recon"),
            (r"\bosint\s+(\S+)", "osint"),
            (r"\bexploit\s+(\S+)", "exploit"),
            (r"\bhydra\s+(.+)$", "hydra"),
            (r"\bgobuster\s+(.+)$", "gobuster"),
            (r"\bsqlmap\s+(.+)$", "sqlmap"),
            (r"\bnikto\s+(.+)$", "nikto"),
            (r"\bwhois\s+(\S+)", "osint"),
            (r"\bCVE-\d{4}-\d{4,}\b", "cve_id"),
        ]
        for pat, mod in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                target = m.group(1).strip()
                if mod in ("hydra", "gobuster", "sqlmap", "nikto"):
                    return "run_tool", (mod, target)
                return mod, target
        return None, None

    def handle_input(self, text):
        global LAST_ERROR, LAST_ERROR_CMDS
        text = text.strip()
        if not text:
            return True

        if text.lower() in ("exit", "quit", "q", "/exit", "/quit"):
            self.save_session()
            print(colored("\n[+] Session saved. Stay safe.", "33"))
            self.running = False
            return True

        if text == "/clear":
            clear_screen()
            print(colored("AdhiHub CYBER-OMNI — screen cleared", "36"))
            print(colored("Type /help for commands", "33"))
            print(SEPARATOR + "\n")
            return True

        if text == "/debug":
            self.cmd_debug()
            return True

        if text == "/help":
            print(WELCOME_MESSAGE)
            return True

        if text == "/retrain":
            print(colored("\n[*] CYBER-OMNI Training Pipeline", "36"))
            print(colored("=" * 50, "36"))
            print(colored("  1. Generate training dataset (from templates)", "33"))
            print(colored("  2. Start fine-tuning (requires GPU)", "33"))
            print(colored("  3. Export to GGUF for use in CYBER-OMNI", "33"))
            print(colored("=" * 50, "36"))
            print()
            print(colored("  [1] Generate dataset only", "32"))
            print(colored("  [2] Train model (dataset must exist)", "32"))
            print(colored("  [3] Export trained model to GGUF", "32"))
            print(colored("  [4] Full pipeline (generate → train → export)", "32"))
            print(colored("  [5] Cancel", "31"))
            choice = input(colored("\n  Choose [1-5]: ", "33")).strip()
            if choice == "1":
                print(colored("\n[*] Generating training dataset...", "33"))
                try:
                    from training.dataset_generator import generate_dataset
                    dset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "training", "dataset", "cyber_omni_training.jsonl")
                    generate_dataset(dset_path)
                except Exception as e:
                    print(colored(f"[!] Dataset generation failed: {e}", "31"))
                    print(colored("[*] Run: python -m training.dataset_generator", "33"))
            elif choice == "2":
                print(colored("\n[*] Starting fine-tuning...", "33"))
                print(colored("[*] This requires a GPU and may take hours.", "33"))
                print(colored("[*] Recommended: python -m training.train", "33"))
                ans = input(colored("  Start training? [y/N]: ", "33")).strip().lower()
                if ans in ("y", "yes"):
                    try:
                        from training.train import train
                        train()
                    except Exception as e:
                        print(colored(f"[!] Training failed: {e}", "31"))
            elif choice == "3":
                print(colored("\n[*] Exporting fine-tuned model...", "33"))
                try:
                    from training.export_model import export_to_gguf
                    export_to_gguf()
                except Exception as e:
                    print(colored(f"[!] Export failed: {e}", "31"))
            elif choice == "4":
                print(colored("\n[*] Running full pipeline...", "33"))
                try:
                    from training.dataset_generator import generate_dataset
                    dset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "training", "dataset", "cyber_omni_training.jsonl")
                    generate_dataset(dset_path)
                    from training.train import train
                    train()
                    from training.export_model import export_to_gguf
                    export_to_gguf()
                except Exception as e:
                    print(colored(f"[!] Pipeline failed: {e}", "31"))
                    print(colored("[*] Run individual steps: dataset_generator → train → export_model", "33"))
            else:
                print(colored("  Cancelled.", "33"))
            return True

        if text == "/reload":
            count = self.plugin_manager.load_plugins()
            print(colored(f"  > Reloaded {count} plugins", "32"))
            return True

        if text == "/plugins":
            self.plugin_manager.list_plugins()
            return True

        if text == "/dashboard":
            try:
                from web_dashboard import run_dashboard_thread
                if self.dashboard_thread and self.dashboard_thread.is_alive():
                    print(colored("  [Dashboard] Already running on http://127.0.0.1:1337", "33"))
                else:
                    self.dashboard_thread = run_dashboard_thread()
                    print(colored("  [Dashboard] Started on http://127.0.0.1:1337", "32"))
            except Exception as e:
                self._auto_handle_error(e, traceback.format_exc(), text)
            return True

        if text.startswith("/payload "):
            try:
                if not self.tor_safe():
                    return True
                parts = text[9:].split()
                if len(parts) >= 2:
                    run_payload(parts[0], parts[1], parts[2] if len(parts) > 2 else None)
                else:
                    print(colored("[!] Usage: /payload <lhost> <lport> [language]", "31"))
            except Exception as e:
                self._auto_handle_error(e, traceback.format_exc(), text)
            return True

        if text.startswith("/autopwn "):
            try:
                if not self.tor_safe():
                    return True
                run_autopwn(text[9:].strip())
            except Exception as e:
                self._auto_handle_error(e, traceback.format_exc(), text)
            return True

        if text == "/report" or text.startswith("/report "):
            try:
                from modules.report import ReportModule, send_to_discord
                r = ReportModule()
                args = text[8:].strip() if len(text) > 8 else ""
                if args == "auto":
                    r.generate(auto_data=True, send_discord=False)
                elif args == "discord":
                    r.generate(auto_data=None, send_discord=True)
                else:
                    r.generate(auto_data=None, send_discord=False)
            except Exception as e:
                self._auto_handle_error(e, traceback.format_exc(), text)
            return True

        if text.startswith("/nmap-parse ") or text.startswith("/cve") or text.startswith("/searchsploit") or text.startswith("/listen") or text.startswith("/subtake") or text.startswith("/queue") or text.startswith("/learn ") or text == "/knowledge" or text.startswith("/know ") or text.startswith("/search ") or text.startswith("/deepsearch ") or text == "/darkweb" or text == "/mode" or text == "/stealth" or text.startswith("/extract ") or text == "/feedback" or text == "/tools" or text.startswith("/install ") or text.startswith("/leak ") or text.startswith("/hibp ") or text == "/model" or text == "/save" or text == "/new" or text == "/tor":
            try:
                if text.startswith("/learn "):
                    learn_file(text[7:].strip())
                elif text == "/knowledge":
                    KnowledgeBase().list_documents()
                elif text.startswith("/know "):
                    q = text[6:].strip()
                    if q:
                        ctx = query_knowledge(q)
                        if ctx:
                            print(colored("\n  [*] Sending relevant knowledge to AI...\n", "33"))
                            self.memory.add_message("system", f"Relevant knowledge context:\n{ctx}")
                elif text.startswith("/cve"):
                    run_cve_search(text[5:].strip())
                elif text.startswith("/searchsploit"):
                    run_exploitdb_search(text[13:].strip())
                elif text.startswith("/listen"):
                    run_listener(text[8:].strip())
                elif text.startswith("/subtake"):
                    run_subtake(text[9:].strip())
                elif text.startswith("/queue"):
                    run_target_queue(text[7:].strip())
                elif text == "/model":
                    print(colored(f"[*] {self.ai.get_info()}", "33"))
                elif text == "/save":
                    self.save_session()
                    print(colored("[+] Session saved.", "32"))
                elif text == "/new":
                    self.memory.clear(SYSTEM_PROMPT)
                    print(colored("[+] New conversation started.", "32"))
                elif text == "/tor":
                    status = tor_status()
                    if status["tor_running"]:
                        print(colored(f"[+] TOR is running", "32"))
                        print(colored(f"    Exit IP: {status['tor_ip']}", "32"))
                        print(colored(f"    Real IP: {status['real_ip']}", "33"))
                        print(colored("    \u2713 You are anonymous" if status["anonymous"] else "    \u2717 IP LEAK DETECTED!", "32" if status["anonymous"] else "31"))
                    else:
                        print(colored("[!] TOR is not running", "31"))
                        if input("  Start TOR? [Y/n]: ").strip().lower() not in ("n", "no"):
                            start_tor()
                elif text.startswith("/search "):
                    q = text[8:].strip()
                    if q:
                        WebSearch().deep_search(q)
                elif text.startswith("/deepsearch "):
                    q = text[12:].strip()
                    if q:
                        summaries = WebSearch().search_and_summarize(q)
                        if summaries:
                            print(colored("\n[*] Content summaries:\n", "36"))
                            for s in summaries:
                                print(colored(f"  \u250c {s['title']}", "32"))
                                print(f"  \u2502 {s['url']}")
                                print(colored(f"  \u2514 {s['content'][:300]}...", "37"))
                                print()
                elif text == "/darkweb":
                    if not check_tor():
                        print(colored("[!] TOR required. Type /tor to start.", "31"))
                        return True
                    ws = WebSearch()
                    q = input("  Search dark web for: ").strip()
                    if q:
                        print(colored("\n[*] Searching dark web (.onion)...", "35"))
                        results, _ = ws.search_onion(q)
                        if results:
                            for i, r in enumerate(results, 1):
                                print(f"  {i}. {r['title']}\n     {r['url']}\n")
                        else:
                            print(colored("  [!] No results found", "31"))
                elif text == "/mode":
                    show_mode_info(self.config)
                    for i, k in enumerate(list(MODES.keys()), 1):
                        print(f"  {i}. {colored(MODES[k]['name'], MODES[k]['color'])}")
                    c = input(f"\n  Switch to [1-{len(MODES)}] or Enter: ").strip()
                    if c.isdigit() and 1 <= int(c) <= len(MODES):
                        k = list(MODES.keys())[int(c) - 1]
                        self.config["mode"] = k
                        save_config(self.config)
                        self.full_prompt = SYSTEM_PROMPT + get_system_prompt_extra(self.config)
                        self.memory = ConversationMemory(max_turns=30, system_prompt=self.full_prompt)
                        print(colored(f"  > Mode: {MODES[k]['name']}", MODES[k]["color"]))
                elif text == "/stealth":
                    setup_stealth()
                elif text.startswith("/extract "):
                    if not self.tor_safe():
                        return True
                    run_extraction(text[9:].strip())
                    self.prompt_report()
                elif text == "/feedback":
                    old = self.config["mode"]
                    ask_feedback()
                    self.config = load_config()
                    if self.config["mode"] != old:
                        self.full_prompt = SYSTEM_PROMPT + get_system_prompt_extra(self.config)
                        self.memory = ConversationMemory(max_turns=30, system_prompt=self.full_prompt)
                    self.feedback_count += 1
                    if self.feedback_count >= 5:
                        print(colored("\n[*] You've used feedback 5 times!", "33"))
                elif text == "/tools":
                    self.attacker.list_tools()
                elif text.startswith("/install "):
                    t = text[9:].strip()
                    if t:
                        self.attacker.install_tool(t)
                elif text.startswith("/nmap-parse "):
                    fp = text[12:].strip()
                    if fp:
                        from modules.nmap_parser import run_nmap_parser
                        data = run_nmap_parser(fp)
                        if data:
                            self.memory.add_message("system", f"Nmap parse: {data['total_hosts']} hosts, {data['total_open_ports']} open ports.")
                elif text.startswith("/leak ") or text.startswith("/hibp "):
                    if not self.tor_safe():
                        return True
                    email = text[6:].strip()
                    if email:
                        from modules.leak_check import run_leak_check
                        run_leak_check(email)
            except Exception as e:
                self._auto_handle_error(e, traceback.format_exc(), text)
            return True

        # --- New guided / Layer 1 commands ---
        if text == "/guide":
            self.orchestrator.guided_mode = not self.orchestrator.guided_mode
            status = "ON" if self.orchestrator.guided_mode else "OFF"
            print(colored(f"  [*] Guided mode: {status}", "32" if self.orchestrator.guided_mode else "33"))
            return True

        if text == "/suggest" or text == "/next":
            result = self.orchestrator._show_suggestions()
            print(result)
            return True

        if text == "/status":
            result = self.orchestrator._show_status()
            print(result)
            return True

        if text == "/rotate":
            print(colored("\n[*] Rotating TOR circuit...", "33"))
            signal_new_identity()
            return True

        if text == "/dnstest":
            check_dns_leak()
            return True

        if text == "/anonymity":
            verify_full_anonymity()
            return True

        if text == "/mac":
            spoof_mac()
            return True

        if text.startswith("/mimic"):
            profile = text[7:].strip()
            if profile:
                from core.stealth import set_profile, list_profiles
                names, _ = list_profiles()
                if profile in names:
                    set_profile(profile)
                    print(colored(f"  [+] Profile set: {profile}", "32"))
                else:
                    print(colored(f"  [!] Available profiles: {', '.join(names)}", "33"))
            else:
                from core.stealth import randomize_profile, current_profile
                randomize_profile()
                p = current_profile()
                print(colored(f"  [+] Randomized profile: {p['user_agent'][:60]}...", "32"))
            return True

        if text.startswith("/attack"):
            try:
                parts = text.split(maxsplit=1)
                target = parts[1] if len(parts) > 1 else ""
                if not target:
                    print(colored("[!] Usage: /attack <target>", "31"))
                    return True
                if not self.tor_safe():
                    return True
                LAST_ERROR_CMDS.append(("/attack", target))
                self.attacker.run(target)
                self.prompt_report()
            except Exception as e:
                self._auto_handle_error(e, traceback.format_exc(), text)
            return True

        if text.startswith("/"):
            try:
                parts = text[1:].split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if self.plugin_manager.handle_command(cmd, arg):
                    return True

                if cmd in self.modules:
                    if cmd == "report":
                        self.modules[cmd].generate()
                    elif cmd == "attack":
                        if not arg:
                            print(colored("[!] Usage: /attack <target>", "31"))
                            return True
                        if not self.tor_safe():
                            return True
                        LAST_ERROR_CMDS.append(("/attack", arg))
                        self.modules[cmd].run(arg)
                    else:
                        if not arg:
                            print(colored(f"[!] Usage: /{cmd} <target>", "31"))
                            return True
                        if cmd != "report" and not self.tor_safe():
                            return True
                        LAST_ERROR_CMDS.append((f"/{cmd}", arg))
                        self.modules[cmd].run(arg)
                        if cmd not in ("report",):
                            self.prompt_report()
                    return True
                print(colored(f"[!] Unknown: /{cmd}  Type /help", "31"))
                return True
            except Exception as e:
                self._auto_handle_error(e, traceback.format_exc(), text)
                return True

        # Try orchestrator first in guided mode
        if self.orchestrator.guided_mode:
            result = self.orchestrator.process_command(text)
            if result:
                print()
                print(SEP_THIN)
                print(colored(result, "37"))
                print()
                return True

        mod, extra = self.detect_tool_call(text)

        try:
            if mod == "search" and extra:
                print()
                ws = WebSearch()
                ws.deep_search(extra)
                return True

            if mod == "autopwn" and extra:
                if not self.tor_safe():
                    return True
                print()
                run_autopwn(extra)
                self.prompt_report()
                return True

            if mod == "payload" and extra:
                if not self.tor_safe():
                    return True
                print()
                parts = extra.split()
                if len(parts) >= 2:
                    run_payload(parts[0], parts[1])
                return True

            if mod == "extract" and extra:
                if not self.tor_safe():
                    return True
                print()
                run_extraction(extra)
                self.prompt_report()
                return True

            if mod == "cve_id" and extra:
                print()
                run_cve_search(extra)
                return True

            if mod == "darkweb" and extra:
                if not check_tor():
                    print(colored("[!] TOR required for dark web", "31"))
                else:
                    print()
                    ws = WebSearch()
                    results, _ = ws.search_onion(extra)
                    if results:
                        for i, r in enumerate(results, 1):
                            print(f"  {i}. {r['title']}")
                            print(f"     {r['url']}")
                            print()
                return True

            if mod == "run_tool":
                tool, target = extra
                if not self.tor_safe():
                    return True
                print()
                if self.attacker.check_tool(tool):
                    self.attacker.run_cmd(f"{tool} {target}")
                else:
                    print(colored(f"[!] {tool} not installed. Use /install {tool}", "31"))
                return True

            if mod and extra:
                if not self.tor_safe():
                    return True
                print()
                LAST_ERROR_CMDS.append((f"/{mod}", extra))
                self.modules[mod].run(extra)
                self.prompt_report()
                print()
                return True

            print()
            print(SEP_THIN)
            self.ai.chat(self.memory, text, stream=True)
            print()
            return True
        except Exception as e:
            self._auto_handle_error(e, traceback.format_exc(), text)
            return True

    def show_header(self):
        print_banner()
        eng = self.ai.get_info()
        tor = "\033[32m\u2713\033[0m" if check_tor() else "\033[31m\u2717\033[0m"
        guided = "\033[32mON\033[0m" if self.orchestrator.guided_mode else "\033[33mOFF\033[0m"
        print(colored(f"  Engine: {eng}  |  ", "36") + colored("AdhiHub", "33") + colored(" CYBER-OMNI", "31"))
        print(colored(f"  TOR: {tor}  Guided: {guided}  |  /help for commands  |  /exit to quit", "33"))
        print(SEPARATOR)

    def make_welcome(self):
        has_tor = check_tor()
        mode_name = MODES[self.config["mode"]]["name"]
        mode_color = MODES[self.config["mode"]]["color"]
        msg = colored(f"I'm your {mode_name}. I will guide you step by step.", mode_color)
        msg += "\n" + colored(f"  Tell me a target and I'll suggest what to do.", "33")
        msg += "\n" + colored(f"  /guide to toggle guided mode | /suggest for next steps | /help for all commands", "33")
        msg += "\n" + colored(f"  /rotate - new TOR identity | /mimic - change browser fingerprint", "33")
        msg += "\n" + colored(f"AdhiHub CYBER-OMNI v2.0 — Zero Trace, Zero Refusal", "35")
        if has_tor:
            msg += "\n" + colored("TOR is active \u2714 You are anonymous.", "32")
        else:
            msg += "\n" + colored("TOR not detected. Type /tor to hide your IP.", "33")
        return msg

    def tor_safe(self):
        """Check TOR safety before any attack operation. Returns True if safe to proceed."""
        return require_tor(force=self.force_tor)

    def _auto_handle_error(self, e, tb, cmd, context=""):
        """Auto-catch error, try quick fix, offer AI analysis — all in one flow."""
        global LAST_ERROR, LAST_ERROR_CMDS
        LAST_ERROR = (e, tb, cmd)
        print(colored(f"\n  [!] {type(e).__name__}: {e}", "31"))
        err_str = str(e).lower()
        fixed = False
        # Auto-quick-fix: missing package
        m = re.search(r"no module named ['\"]?(\w+)['\"]?", err_str, re.IGNORECASE)
        if m:
            pkg = m.group(1)
            print(colored(f"  [*] Detected missing Python package: {pkg}", "33"))
            ans = input(colored(f"  Auto-install {pkg} with pip? [Y/n]: ", "33")).strip().lower()
            if ans not in ("n", "no"):
                r = subprocess.run([sys.executable, "-m", "pip", "install", pkg], capture_output=True, text=True)
                if r.returncode == 0:
                    print(colored(f"  [+] Installed {pkg}. Type the same command again to retry.", "32"))
                    fixed = True
                else:
                    print(colored(f"  [!] pip install failed:\n{r.stderr[:200]}", "31"))
        # Auto-quick-fix: missing dir
        m = re.search(r"(?:no such file|not found|filenotfounderror).*['\"]?([^'\"\n]+)['\"]?", err_str, re.IGNORECASE)
        if m and not fixed:
            path = m.group(1).strip()
            print(colored(f"  [*] Missing file/directory: {path}", "33"))
            ans = input(colored(f"  Create it? [Y/n]: ", "33")).strip().lower()
            if ans not in ("n", "no"):
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    if not os.path.isdir(path):
                        os.makedirs(path, exist_ok=True)
                    print(colored(f"  [+] Created. Retry your command.", "32"))
                    fixed = True
                except Exception as e2:
                    print(colored(f"  [!] Failed: {e2}", "31"))
        if not fixed:
            ans2 = input(colored("\n  [*] Run AI analysis to auto-fix? [Y/n]: ", "33")).strip().lower()
            if ans2 not in ("n", "no"):
                self._debug_ai_fix(e, tb, cmd)
            else:
                print(colored("  [*] Type /debug anytime to revisit this error.", "33"))
        else:
            print(colored("  [*] Fix applied. Retry your previous command.", "33"))

    def cmd_debug(self):
        global LAST_ERROR, LAST_ERROR_CMDS
        if LAST_ERROR is None:
            print(colored("[*] No errors recorded yet.", "32"))
            return
        exc, tb, cmd = LAST_ERROR
        print(colored("\n" + "\u2500" * 55, "36"))
        print(colored("  DEBUG — Error Analysis & Auto-Fix", "35"))
        print(colored("\u2500" * 55, "36"))
        print(colored(f"\n  [!] Error in: {cmd}", "31"))
        print(colored(f"  [!] {type(exc).__name__}: {exc}", "33"))
        print()
        print(colored("  [1] Show full traceback", "33"))
        print(colored("  [2] Auto-fix with AI analysis", "32"))
        print(colored("  [3] Attempt quick fix (pip install / mkdir / chmod)", "32"))
        print(colored("  [4] Clear error history", "33"))
        print(colored("  [5] Cancel", "31"))
        choice = input(colored("\n  Choose [1-5]: ", "33")).strip()
        if choice == "1":
            print(colored("\n" + tb, "37"))
        elif choice == "2":
            self._debug_ai_fix(exc, tb, cmd)
        elif choice == "3":
            self._debug_quick_fix(exc, tb, cmd)
        elif choice == "4":
            LAST_ERROR = None
            LAST_ERROR_CMDS = []
            print(colored("  [+] Error history cleared.", "32"))
        else:
            print(colored("  Cancelled.", "33"))

    def _debug_ai_fix(self, exc, tb, cmd):
        print(colored("\n[*] Sending error to AI for analysis...", "33"))
        prompt = (
            f"CYBER-OMNI encountered this error:\n"
            f"Command: {cmd}\n"
            f"Error type: {type(exc).__name__}\n"
            f"Error message: {exc}\n\n"
            f"Traceback:\n{tb}\n\n"
            f"Analyze the root cause and provide exact steps to fix it. "
            f"Be specific — include file paths, code changes, or commands to run."
        )
        try:
            resp = self.ai.chat_raw(self.memory, prompt)
            print(colored("\n" + "\u2500" * 55, "36"))
            print(colored("  AI Fix Analysis:", "35"))
            print(colored("\u2500" * 55, "36"))
            print(resp)
        except Exception as e2:
            print(colored(f"[!] AI analysis failed: {e2}", "31"))
            print(colored("[*] Traceback for manual review:", "33"))
            print(tb)

    def _debug_quick_fix(self, exc, tb, cmd):
        err_str = str(exc).lower()
        fixed = False
        m = re.search(r"no module named ['\"]?(\w+)['\"]?", err_str, re.IGNORECASE)
        if m:
            pkg = m.group(1)
            print(colored(f"\n[*] Detected missing Python package: {pkg}", "33"))
            ans = input(colored(f"  Install {pkg} with pip? [Y/n]: ", "33")).strip().lower()
            if ans not in ("n", "no"):
                r = subprocess.run([sys.executable, "-m", "pip", "install", pkg], capture_output=True, text=True)
                if r.returncode == 0:
                    print(colored(f"  [+] {pkg} installed.", "32"))
                    fixed = True
                else:
                    print(colored(f"  [!] pip install failed:\n{r.stderr[:300]}", "31"))
        m = re.search(r"(?:no such file|not found|filenotfounderror).*['\"]?([^'\"\n]+)['\"]?", err_str, re.IGNORECASE)
        if m and not fixed:
            path = m.group(1).strip()
            print(colored(f"\n[*] Missing: {path}", "33"))
            ans = input(colored(f"  Create directory? [Y/n]: ", "33")).strip().lower()
            if ans not in ("n", "no"):
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    if not os.path.isdir(path):
                        os.makedirs(path, exist_ok=True)
                    print(colored(f"  [+] Created.", "32"))
                    fixed = True
                except Exception as e2:
                    print(colored(f"  [!] Failed: {e2}", "31"))
        if "permission" in err_str and not fixed:
            m = re.search(r"['\"]?([^'\"\n]+)['\"]?", err_str)
            if m and os.name != "nt":
                path = m.group(1)
                ans = input(colored(f"  chmod +x '{path}'? [Y/n]: ", "33")).strip().lower()
                if ans not in ("n", "no"):
                    import stat
                    try:
                        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
                        print(colored(f"  [+] Done.", "32"))
                        fixed = True
                    except Exception as e2:
                        print(colored(f"  [!] Failed: {e2}", "31"))
        if not fixed:
            print(colored("\n[*] Quick fix didn't match. Use [2] for AI analysis.", "33"))

    def prompt_report(self):
        try:
            ans = input(colored("[?] Generate report from last results? [Y/n]: ", "33")).strip().lower()
            if ans not in ("n", "no"):
                from modules.report import ReportModule
                ReportModule().generate(auto_data=True, send_discord=False)
        except:
            pass

    def save_session(self):
        try:
            data = {
                "messages": self.memory.get_messages()[1:],
                "timestamp": __import__("datetime").datetime.now().isoformat()
            }
            with open(self.session_file, "w") as f:
                json.dump(data, f, indent=2)
            self.orchestrator.save_session()
        except Exception:
            pass

    def load_session(self):
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file) as f:
                    data = json.load(f)
                for msg in data.get("messages", []):
                    if msg["role"] in ("user", "assistant"):
                        self.memory.messages.append(msg)
                count = len(data.get("messages", [])) // 2
                if count > 0:
                    print(colored(f"[*] Restored {count} previous messages", "33"))
        except Exception:
            pass

    def run(self):
        if not stealth_gate():
            return

        clear_screen()
        self.show_header()

        model_choice = self.config.get("model", None)
        if not self.ai.initialize(prompt_download=True, model_key=model_choice):
            print(colored("[!] No AI engine available.", "31"))
            print(colored("[*] Run: python omni.py --download", "33"))
            return

        self.load_session()
        self.orchestrator.set_memory(self.memory)

        plugin_count = self.plugin_manager.load_plugins()
        if plugin_count > 0:
            print(colored(f"  [*] {plugin_count} plugin(s) loaded. Type /plugins to list.", "36"))

        print(self.make_welcome())
        print(SEPARATOR)
        print()

        tab_session = setup_tab_completion()
        msg_count = 0
        prompt_str = "\033[33mAdhiHub\033[0m\033[31m@\033[0m\033[36mcyber\033[0m\033[37m> \033[0m"
        while self.running:
            try:
                if tab_session:
                    text = tab_session.prompt(prompt_str)
                else:
                    text = input(prompt_str)
                if not self.handle_input(text):
                    break
                msg_count += 1
                if msg_count > 0 and msg_count % 15 == 0:
                    print(colored("\n  [?] Want to tell me how I can do better?", "33"))
                    print(colored("      Type /feedback to improve your experience", "33"))
            except KeyboardInterrupt:
                print(colored("\n", "31"))
                continue
            except EOFError:
                self.save_session()
                break


REPO_URL = "https://github.com/AdhiHub/AdhiHub-CYBER-OMNI.git"


def try_update():
    print(colored("[*] Checking for updates...", "33"))
    base = os.path.dirname(os.path.abspath(__file__))
    git_dir = os.path.join(base, ".git")
    if os.path.exists(git_dir):
        try:
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=base, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                if "Already up to date" in result.stdout:
                    print(colored("[+] Already up to date.", "32"))
                else:
                    print(colored(f"[+] Update successful!\n{result.stdout[:500]}", "32"))
                    print(colored("[*] Please restart CYBER-OMNI to use the latest version.", "33"))
            else:
                print(colored(f"[!] Git pull failed:\n{result.stderr[:300]}", "31"))
                print(colored("[*] Falling back to ZIP download...", "33"))
                _update_from_zip(base)
        except FileNotFoundError:
            _update_from_zip(base)
        except Exception as e:
            print(colored(f"[!] Update error: {e}", "31"))
            print(colored("[*] Falling back to ZIP download...", "33"))
            _update_from_zip(base)
    else:
        _update_from_zip(base)


def _update_from_zip(base):
    try:
        import zipfile, io
        print(colored("[*] Downloading latest version as ZIP...", "33"))
        resp = requests.get("https://github.com/AdhiHub/AdhiHub-CYBER-OMNI/archive/refs/heads/main.zip", timeout=30)
        if resp.status_code != 200:
            print(colored(f"[!] Download failed: HTTP {resp.status_code}", "31"))
            return
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        tmpdir = os.path.join(base, ".update_tmp")
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        os.makedirs(tmpdir)
        z.extractall(tmpdir)
        extracted = os.path.join(tmpdir, os.listdir(tmpdir)[0])
        for item in os.listdir(extracted):
            s = os.path.join(extracted, item)
            d = os.path.join(base, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        shutil.rmtree(tmpdir)
        print(colored("[+] Update downloaded and applied.", "32"))
        print(colored("[*] Please restart CYBER-OMNI to use the latest version.", "33"))
    except ImportError:
        print(colored("[!] requests not installed. Cannot update via ZIP.", "31"))
        print(colored("[*] Manually download: https://github.com/AdhiHub/AdhiHub-CYBER-OMNI/archive/refs/heads/main.zip", "33"))
    except Exception as e:
        print(colored(f"[!] ZIP update failed: {e}", "31"))


def setup_tab_completion():
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import WordCompleter
        from prompt_toolkit.history import FileHistory
        COMMANDS = [
            "/help", "/clear", "/exit", "/quit", "/save", "/new", "/reload",
            "/mode", "/feedback", "/tor", "/tools", "/model",
            "/scan", "/recon", "/osint", "/exploit", "/attack",
            "/autopwn", "/extract", "/payload", "/report",
            "/search", "/deepsearch", "/darkweb",
            "/cve", "/searchsploit", "/listen", "/subtake", "/queue",
            "/learn", "/know", "/knowledge", "/plugins",
            "/dashboard", "/stealth", "/install",
            "/nmap-parse", "/leak", "/hibp", "/debug",
            "/guide", "/suggest", "/next", "/status",
            "/rotate", "/dnstest", "/anonymity", "/mac", "/mimic",
        ]
        completer = WordCompleter(COMMANDS, ignore_case=True)
        hist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".omnist_history")
        session = PromptSession(completer=completer, history=FileHistory(hist_path))
        return session
    except ImportError:
        return None


def auto_install_deps():
    """Auto-install all required packages from requirements.txt."""
    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    print(colored("[*] Installing all dependencies from requirements.txt...", "33"))
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
        print(colored("[+] Dependencies installed! Restarting...", "32"))
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        print(colored(f"[!] Auto-install failed: {e}", "31"))
        print(colored(f"[*] Run manually: pip install -r {req_file}", "33"))
        sys.exit(1)

def main():
    import argparse

    # Handle missing deps first
    if _MISSING_DEPS:
        print(colored("\n" + "\u2500" * 50, "31"))
        print(colored("  MISSING DEPENDENCIES DETECTED", "31"))
        print(colored("\u2500" * 50, "31"))
        for d in _MISSING_DEPS:
            pkg = d.split("'")[1] if "'" in d else d
            print(colored(f"    \u2022 {pkg}", "33"))
        print()
        choice = input(colored("  Auto-install all missing packages? (Y/n): ", "33")).strip().lower()
        if choice != "n":
            auto_install_deps()
        else:
            req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
            print(colored(f"  Run manually: pip install -r {req_file}", "33"))
            sys.exit(1)
        return

    parser = argparse.ArgumentParser(description="CYBER-OMNI v2.0 - Terminal AI Pentesting Agent")
    parser.add_argument("mode", nargs="?", default="chat",
                        choices=["chat", "scan", "recon", "osint", "exploit", "report", "attack"])
    parser.add_argument("target", nargs="?")
    parser.add_argument("-q", "--query", help="Quick question")
    parser.add_argument("--download", metavar="MODEL", nargs="?", const="list",
                        help="Download AI model")
    parser.add_argument("--update", action="store_true", help="Auto-update CYBER-OMNI from GitHub")

    args = parser.parse_args()

    if args.update:
        try_update()
        return

    if args.download:
        from core.downloader import list_models, download_model
        if args.download == "list":
            list_models()
            return
        path = download_model(args.download)
        if path:
            print(colored(f"[+] Downloaded: {path}", "32"))
        return

    if args.query:
        ai = AIEngine()
        if not ai.initialize(prompt_download=False):
            print(colored("[!] No AI engine available. Use --download to get a model.", "31"))
            return
        mem = ConversationMemory(max_turns=2, system_prompt=SYSTEM_PROMPT)
        print()
        ai.chat(mem, args.query, stream=False)
        return

    if args.mode != "chat" and args.target:
        mod_map = {
            "scan": ScanModule,
            "recon": ReconModule,
            "osint": OSINTModule,
            "exploit": ExploitModule,
            "report": ReportModule,
            "attack": AttackerModule,
        }
        mod_map[args.mode]().run(args.target)
        return

    if args.mode == "attack" and not args.target:
        print(colored("[!] Usage: python omni.py attack <target>", "31"))
        return

    omni = CyberOmni()
    omni.run()


if __name__ == "__main__":
    main()
