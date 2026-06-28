import os
import json
from core.utils import colored

QUEUE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "target_queue.json")
SCAN_RESULTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "last_scan_results.json")


def load_queue():
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def save_scan_results(results):
    with open(SCAN_RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)


def load_scan_results():
    if os.path.exists(SCAN_RESULTS_FILE):
        try:
            with open(SCAN_RESULTS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def run_target_queue(args):
    parts = args.strip().split(maxsplit=1)
    cmd = parts[0].lower() if parts else "help"
    arg = parts[1] if len(parts) > 1 else ""

    queue = load_queue()

    if cmd == "help":
        print(colored("\nTarget Queue Commands:", "36"))
        print(colored("=" * 50, "36"))
        print("  /queue add <target>     Add target to queue")
        print("  /queue list             List queued targets")
        print("  /queue remove <n>       Remove target by number")
        print("  /queue clear            Clear all targets")
        print("  /queue run [module]     Run attack on all queued targets")
        print("  /queue help             Show this help")
        print()
        print(colored("Available modules: scan, recon, osint, exploit, extract", "33"))
        print(colored("Default: scan", "33"))
        print()
        return

    if cmd == "add":
        target = arg.strip()
        if not target:
            print(colored("[!] Usage: /queue add <target>", "31"))
            return
        if target not in queue:
            queue.append(target)
            save_queue(queue)
            print(colored(f"[+] Added {target} to queue (total: {len(queue)})", "32"))
        else:
            print(colored(f"[!] {target} already in queue", "33"))
        return

    if cmd == "list":
        if not queue:
            print(colored("[!] Queue is empty", "31"))
            print(colored("[*] Add targets with: /queue add <target>", "33"))
            return
        print(colored(f"\nTarget Queue ({len(queue)} targets):", "36"))
        print(colored("=" * 50, "36"))
        for i, t in enumerate(queue, 1):
            print(f"  {i}. {t}")
        print()
        return

    if cmd == "remove":
        if not arg.isdigit():
            print(colored("[!] Usage: /queue remove <number>", "31"))
            return
        idx = int(arg) - 1
        if 0 <= idx < len(queue):
            removed = queue.pop(idx)
            save_queue(queue)
            print(colored(f"[-] Removed {removed} from queue", "33"))
        else:
            print(colored(f"[!] Invalid index: {arg}", "31"))
        return

    if cmd == "clear":
        save_queue([])
        print(colored("[+] Queue cleared", "33"))
        return

    if cmd == "run":
        if not queue:
            print(colored("[!] Queue is empty", "31"))
            print(colored("[*] Add targets with: /queue add <target>", "33"))
            return

        module = arg.strip().lower() or "scan"

        available = {"scan", "recon", "osint", "exploit", "extract"}
        if module not in available:
            print(colored(f"[!] Unknown module: {module}", "31"))
            print(colored(f"[*] Available: {', '.join(sorted(available))}", "33"))
            return

        from modules.scan import ScanModule
        from modules.recon import ReconModule
        from modules.osint import OSINTModule
        from modules.exploit import ExploitModule
        from modules.extractor import run_extraction

        mod_map = {
            "scan": ScanModule(),
            "recon": ReconModule(),
            "osint": OSINTModule(),
            "exploit": ExploitModule(),
        }

        print(colored(f"\n{'=' * 55}", "36"))
        print(colored(f"  QUEUE RUN — Module: {module.upper()}", "36"))
        print(colored(f"  Targets: {len(queue)}", "36"))
        print(colored(f"{'=' * 55}\n", "36"))

        all_results = {}
        total = len(queue)

        for i, target in enumerate(queue, 1):
            print(colored(f"[{i}/{total}] Processing: {target}", "33"))
            print(colored("-" * 40, "36"))

            if module == "extract":
                run_extraction(target)
                all_results[target] = {"status": "done", "module": module}
            elif module in mod_map:
                try:
                    mod_map[module].run(target)
                    all_results[target] = {"status": "done", "module": module}
                except Exception as e:
                    print(colored(f"[!] Error on {target}: {e}", "31"))
                    all_results[target] = {"status": "error", "error": str(e)}
            else:
                all_results[target] = {"status": "skipped", "reason": "unknown module"}

            print()

        save_scan_results({
            "module": module,
            "results": all_results,
            "total": total,
            "success": sum(1 for r in all_results.values() if r.get("status") == "done"),
            "failed": sum(1 for r in all_results.values() if r.get("status") == "error"),
        })

        success = sum(1 for r in all_results.values() if r.get("status") == "done")
        failed = sum(1 for r in all_results.values() if r.get("status") == "error")

        print(colored(f"{'=' * 55}", "36"))
        print(colored(f"  QUEUE COMPLETE", "32"))
        print(colored(f"  Total: {total} | Successful: {success} | Failed: {failed}", "36"))
        print(colored(f"{'=' * 55}\n", "36"))
        print(colored(f"  [?] Generate report from these results? (Y/n): ", "33"), end="")
        ans = input().strip().lower()
        if ans not in ("n", "no"):
            try:
                from modules.report import ReportModule
                r = ReportModule()
                r.generate(auto_data=all_results, send_discord=False)
            except Exception as e:
                print(colored(f"[!] Report error: {e}", "31"))
        return

    print(colored(f"[!] Unknown queue command: {cmd}", "31"))
    print(colored("[*] Try: /queue help", "33"))
