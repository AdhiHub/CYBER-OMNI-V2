import json
import os
import sys
import html
from datetime import datetime
from core.utils import ensure_dir, get_timestamp, colored

import urllib.parse

DISCORD_WEBHOOK = ""
DISCORD_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "discord_webhook.json")
TELEGRAM_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "telegram_bot.json")


def load_discord_config():
    if os.path.exists(DISCORD_CONFIG_FILE):
        try:
            with open(DISCORD_CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_discord_config(webhook):
    with open(DISCORD_CONFIG_FILE, "w") as f:
        json.dump({"webhook": webhook}, f, indent=2)
    print(colored(f"  [+] Discord webhook saved to {DISCORD_CONFIG_FILE}", "32"))


def load_telegram_config():
    if os.path.exists(TELEGRAM_CONFIG_FILE):
        try:
            with open(TELEGRAM_CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_telegram_config(token, chat_id):
    with open(TELEGRAM_CONFIG_FILE, "w") as f:
        json.dump({"token": token, "chat_id": chat_id}, f, indent=2)
    print(colored(f"  [+] Telegram config saved to {TELEGRAM_CONFIG_FILE}", "32"))


def send_to_telegram(file_path, title="Pentest Report", token=None, chat_id=None):
    try:
        import requests
    except ImportError:
        print(colored("  [!] requests not installed. Cannot send to Telegram.", "31"))
        return

    cfg = load_telegram_config()
    token = token or cfg.get("token")
    chat_id = chat_id or cfg.get("chat_id")

    if not token or not chat_id:
        print(colored("  [!] Telegram not configured.", "31"))
        ans = input(colored("  [?] Enter Telegram Bot Token: ", "33")).strip()
        if not ans:
            return
        token = ans
        ans2 = input(colored("  [?] Enter Chat ID: ", "33")).strip()
        if not ans2:
            return
        chat_id = ans2
        if input(colored("  [?] Save for future? [Y/n]: ", "33")).strip().lower() not in ("n", "no"):
            save_telegram_config(token, chat_id)

    api_url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": (os.path.basename(file_path), f, "application/pdf")}
            data = {"chat_id": chat_id, "caption": f"\U0001f4cb {title}"}
            resp = requests.post(api_url, data=data, files=files, timeout=30)
            if resp.status_code == 200:
                print(colored(f"  [+] Sent PDF to Telegram \u2714", "32"))
            else:
                print(colored(f"  [!] Telegram send failed: {resp.text[:200]}", "31"))
    except Exception as e:
        print(colored(f"  [!] Telegram send error: {e}", "31"))


def send_to_discord(file_path, title="Pentest Report", webhook_url=None):
    try:
        import requests

        if webhook_url:
            webhook = webhook_url
        else:
            cfg = load_discord_config()
            webhook = cfg.get("webhook")
            if not webhook:
                print(colored("  [!] No Discord webhook configured.", "31"))
                webhook = input(colored("  [?] Enter Discord Webhook URL: ", "33")).strip()
                if not webhook:
                    return
                if input(colored("  [?] Save for future? [Y/n]: ", "33")).strip().lower() not in ("n", "no"):
                    save_discord_config(webhook)

        # Prepare embed
        fname = os.path.basename(file_path)
        fsize = os.path.getsize(file_path)
        size_str = f"{fsize/1024:.1f} KB" if fsize < 1024 * 1024 else f"{fsize/1024/1024:.2f} MB"

        embed = {
            "embeds": [{
                "title": f"\U0001f4cb {title}",
                "color": 0xff4444,
                "fields": [
                    {"name": "File", "value": f"`{fname}`", "inline": True},
                    {"name": "Size", "value": size_str, "inline": True},
                    {"name": "Type", "value": "PDF Report", "inline": True},
                ],
                "footer": {"text": f"AdhiHub CYBER-OMNI v2 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
            }]
        }

        # Send embed first
        resp = requests.post(webhook, json=embed, timeout=10)
        if resp.status_code not in (200, 204):
            print(colored(f"  [!] Discord embed failed: {resp.status_code}", "31"))

        # Send file as attachment
        with open(file_path, "rb") as f:
            files = {"file": (fname, f, "application/pdf")}
            resp2 = requests.post(webhook, files=files, timeout=30)
            if resp2.status_code in (200, 204):
                print(colored(f"  [+] Sent PDF to Discord webhook \u2714", "32"))
            else:
                print(colored(f"  [!] Discord file upload failed: {resp2.status_code}", "31"))

    except ImportError:
        print(colored("  [!] requests not installed. Cannot send to Discord.", "31"))
    except Exception as e:
        print(colored(f"  [!] Discord send error: {e}", "31"))


LAST_SCAN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "last_scan_results.json")


def generate_ai_summary(findings, scope="N/A"):
    try:
        from core.engine import AIEngine
        from core.memory import ConversationMemory
        engine = AIEngine()
        if not engine.initialize(prompt_download=False):
            return None
        findings_text = "\n".join([f"- {f['finding']} ({f['severity']})" for f in findings])
        prompt = f"""You are a senior cybersecurity reporting expert. Write a concise, professional executive summary for a penetration test report.

Scope: {scope}
Number of findings: {len(findings)}

Findings:
{findings_text}

Write 3-4 paragraphs: (1) what was tested, (2) key findings summary, (3) overall risk assessment, (4) recommended next steps. Be direct and technical. Do not use markdown."""
        mem = ConversationMemory(max_turns=2)
        mem.add_message("user", prompt)
        result = engine.chat(mem, prompt, stream=False)
        return result.strip() if result else None
    except Exception as e:
        print(colored(f"  [!] AI summary generation failed: {e}", "31"), file=sys.stderr)
        return None


def load_last_scan():
    if os.path.exists(LAST_SCAN_FILE):
        try:
            with open(LAST_SCAN_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return None


class ReportModule:
    def __init__(self):
        self.report_dir = "reports"
        ensure_dir(self.report_dir)

    def generate_summary(self, data):
        return self.generate(data)

    def generate(self, auto_data=None, send_discord=False):
        if auto_data is True:
            auto_data = load_last_scan()
            if auto_data:
                print(colored("[*] Auto-generating report from last scan results...", "33"))

        if auto_data and isinstance(auto_data, dict):
            report = {
                "title": auto_data.get("title", "Automated Security Assessment"),
                "client": auto_data.get("client", "N/A"),
                "date": get_timestamp(),
                "assessor": "AdhiHub CYBER-OMNI v2",
                "scope": ", ".join(auto_data.get("results", {}).keys()) if "results" in auto_data else auto_data.get("scope", "N/A"),
                "methodology": "Automated (CYBER-OMNI)",
                "findings": [],
                "recommendations": [
                    "Close unnecessary open ports",
                    "Update outdated services",
                    "Use strong authentication mechanisms",
                    "Enable HTTPS with valid certificates",
                    "Regular security assessments",
                ],
            }
            results = auto_data.get("results", {})
            for target, info in results.items():
                status = info.get("status", "unknown")
                module = info.get("module", "scan")
                severity = "Info" if status == "done" else "High"
                report["findings"].append({
                    "finding": f"[{module.upper()}] {target}: {status}",
                    "severity": severity,
                })
            if not report["findings"]:
                report["findings"].append({"finding": "No findings recorded", "severity": "Info"})
        else:
            print(colored("[*] Pentest Report Generator", "33"))
            report = {}
            report["title"] = input("Report Title: ").strip()
            report["client"] = input("Client Name: ").strip()
            report["date"] = get_timestamp()
            report["assessor"] = input("Assessor Name: ").strip()
            print(colored("\n[*] Scope Definition:", "33"))
            report["scope"] = input("Scope (IPs/domains): ").strip()
            report["methodology"] = input("Methodology [PTES]: ").strip() or "PTES"

            print(colored("\n[*] Findings (empty line to end):", "33"))
            findings = []
            while True:
                finding = input("  Finding: ").strip()
                if not finding:
                    break
                severity = input("  Severity (Crit/High/Med/Low/Info): ").strip() or "Info"
                findings.append({"finding": finding, "severity": severity})
            report["findings"] = findings

            print(colored("\n[*] Recommendations (empty line to end):", "33"))
            recs = []
            while True:
                rec = input("  Recommendation: ").strip()
                if not rec:
                    break
                recs.append(rec)
            report["recommendations"] = recs

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"{self.report_dir}/pentest_report_{ts}"

        self._save_json(report, f"{base}.json")
        self._save_markdown(report, f"{base}.md")
        self._save_html(report, f"{base}.html")
        pdf_path = self._save_pdf(report, f"{base}.pdf")

        print(colored(f"\n[+] Report saved:", "32"))
        print(f"    {base}.json")
        print(f"    {base}.md")
        print(f"    {base}.html")
        print(f"    {base}.pdf")

        if send_discord and pdf_path:
            print()
            send_to_discord(pdf_path, report.get("title", "Pentest Report"))

        if pdf_path and not send_discord:
            self.prompt_delivery(pdf_path, report.get("title", "Pentest Report"))

        return base

    def prompt_delivery(self, pdf_path, title):
        print(colored("\n[*] Where to send the report?", "33"))
        print("  1. Local only (default)")
        print("  2. Discord webhook")
        print("  3. Telegram bot")
        print("  4. Both Discord + Telegram")
        choice = input(colored("\n  Choose [1-4] (default: 1): ", "33")).strip()
        if choice == "2":
            send_to_discord(pdf_path, title)
        elif choice == "3":
            send_to_telegram(pdf_path, title)
        elif choice == "4":
            send_to_discord(pdf_path, title)
            send_to_telegram(pdf_path, title)

    def _save_json(self, report, path):
        with open(path, "w") as f:
            json.dump(report, f, indent=2)

    def _save_markdown(self, report, path):
        with open(path, "w") as f:
            f.write(f"# Pentest Report: {report['title']}\n\n")
            f.write(f"**Client:** {report['client']}  \n")
            f.write(f"**Date:** {report['date']}  \n")
            f.write(f"**Assessor:** {report['assessor']}  \n")
            f.write(f"**Scope:** {report['scope']}  \n")
            f.write(f"**Methodology:** {report['methodology']}  \n\n")
            f.write("## Executive Summary\n\n")
            ai_summary = generate_ai_summary(report.get("findings", []), report.get("scope", "N/A"))
            if ai_summary:
                f.write(ai_summary + "\n\n")
            else:
                f.write(f"A security assessment was conducted. {len(report['findings'])} findings were identified.\n\n")
            if report["findings"]:
                f.write("## Findings\n\n")
                f.write("| # | Finding | Severity |\n")
                f.write("|---|---------|----------|\n")
                for i, fv in enumerate(report["findings"], 1):
                    f.write(f"| {i} | {fv['finding']} | {fv['severity']} |\n")
                f.write("\n")
            if report["recommendations"]:
                f.write("## Recommendations\n\n")
                for i, r in enumerate(report["recommendations"], 1):
                    f.write(f"{i}. {r}\n")
                f.write("\n")
            f.write("---\n")
            f.write(f"*Generated by CYBER-OMNI on {get_timestamp()}*\n")

    def _save_pdf(self, report, path):
        try:
            from fpdf import FPDF
        except ImportError:
            print(colored("  [!] fpdf2 not installed. Run: pip install fpdf2", "31"))
            return None

        try:
            pdf = FPDF()
            pdf.add_page()

            # Title
            pdf.set_font("Helvetica", "B", 20)
            pdf.set_text_color(255, 68, 68)
            pdf.cell(0, 15, "Pentest Report", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.ln(5)

            # Separator
            pdf.set_draw_color(255, 68, 68)
            pdf.set_line_width(0.5)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(8)

            # Meta
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(200, 200, 200)
            meta = [
                ("Title:", report.get("title", "N/A")),
                ("Client:", report.get("client", "N/A")),
                ("Date:", report.get("date", "N/A")),
                ("Assessor:", report.get("assessor", "N/A")),
                ("Scope:", report.get("scope", "N/A")),
                ("Methodology:", report.get("methodology", "PTES")),
            ]
            for label, value in meta:
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(255, 170, 68)
                pdf.cell(35, 7, label)
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(200, 200, 200)
                pdf.cell(0, 7, str(value), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(8)

            # Executive Summary
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(255, 136, 68)
            pdf.cell(0, 10, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(200, 200, 200)
            ai_summary = generate_ai_summary(report.get("findings", []), report.get("scope", "N/A"))
            if ai_summary:
                pdf.multi_cell(0, 6, ai_summary)
            else:
                findings_count = len(report.get("findings", []))
                pdf.multi_cell(0, 6, f"A security assessment was conducted. {findings_count} findings were identified.")
            pdf.ln(5)

            # Findings
            findings = report.get("findings", [])
            if findings:
                pdf.set_font("Helvetica", "B", 14)
                pdf.set_text_color(255, 136, 68)
                pdf.cell(0, 10, "Findings", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(3)

                # Table header
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_fill_color(50, 50, 50)
                pdf.set_text_color(255, 170, 68)
                pdf.cell(10, 8, "#", border=1, fill=True, align="C")
                pdf.cell(140, 8, "Finding", border=1, fill=True)
                pdf.cell(40, 8, "Severity", border=1, fill=True, align="C")
                pdf.ln()

                # Table rows
                pdf.set_font("Helvetica", "", 9)
                for i, fv in enumerate(findings, 1):
                    sev = fv.get("severity", "Info")
                    sev_colors = {
                        "Critical": (255, 68, 68),
                        "High": (255, 136, 68),
                        "Medium": (255, 204, 68),
                        "Low": (68, 255, 68),
                        "Info": (136, 136, 255),
                    }
                    sc = sev_colors.get(sev, (200, 200, 200))

                    pdf.set_text_color(200, 200, 200)
                    pdf.cell(10, 7, str(i), border=1, align="C")
                    pdf.cell(140, 7, fv.get("finding", "")[:80], border=1)
                    pdf.set_text_color(*sc)
                    pdf.cell(40, 7, sev, border=1, align="C")
                    pdf.ln()

                pdf.ln(8)

            # Recommendations
            recs = report.get("recommendations", [])
            if recs:
                pdf.set_font("Helvetica", "B", 14)
                pdf.set_text_color(255, 136, 68)
                pdf.cell(0, 10, "Recommendations", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(3)

                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(200, 200, 200)
                for i, rec in enumerate(recs, 1):
                    pdf.set_fill_color(40, 40, 40)
                    pdf.multi_cell(0, 6, f"{i}. {rec}")
                    pdf.ln(2)

            # Footer
            pdf.ln(10)
            pdf.set_draw_color(255, 68, 68)
            pdf.set_line_width(0.3)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, f"Generated by AdhiHub CYBER-OMNI v2 on {get_timestamp()}", align="C")

            pdf.output(path)
            print(colored(f"    {path} (PDF)", "32"))
            return path

        except Exception as e:
            print(colored(f"  [!] PDF generation failed: {e}", "31"))
            print(colored("  [!] Try: pip install fpdf2", "31"))
            return None

    def _save_html(self, report, path):
        rows = ""
        for i, fv in enumerate(report["findings"], 1):
            sev_cls = f'severity-{fv["severity"]}'
            rows += f'            <tr><td>{i}</td><td>{html.escape(fv["finding"])}</td><td class="{sev_cls}">{html.escape(fv["severity"])}</td></tr>\n'
        rec_blocks = ""
        for i, r in enumerate(report["recommendations"], 1):
            rec_blocks += f'        <div class="rec">{i}. {html.escape(r)}</div>\n'

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Pentest Report: {html.escape(report['title'])}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 40px; line-height: 1.6; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #1a1a1a; padding: 40px; border-radius: 8px; border: 1px solid #333; }}
        h1 {{ color: #ff4444; border-bottom: 2px solid #ff4444; padding-bottom: 10px; margin-bottom: 20px; }}
        h2 {{ color: #ff8844; margin: 25px 0 10px 0; }}
        .meta {{ background: #252525; padding: 15px; border-radius: 4px; margin-bottom: 20px; }}
        .meta p {{ margin: 5px 0; }}
        .meta strong {{ color: #ffaa44; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th {{ background: #333; color: #ff8844; padding: 10px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #333; }}
        .severity-Critical {{ color: #ff4444; font-weight: bold; }}
        .severity-High {{ color: #ff8844; font-weight: bold; }}
        .severity-Medium {{ color: #ffcc44; font-weight: bold; }}
        .severity-Low {{ color: #44ff44; font-weight: bold; }}
        .severity-Info {{ color: #8888ff; }}
        .rec {{ background: #252525; padding: 10px 15px; margin: 5px 0; border-left: 3px solid #44ff44; border-radius: 0 4px 4px 0; }}
        .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #333; font-size: 0.9em; color: #888; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Pentest Report: {html.escape(report['title'])}</h1>
        <div class="meta">
            <p><strong>Client:</strong> {html.escape(report['client'])}</p>
            <p><strong>Date:</strong> {html.escape(report['date'])}</p>
            <p><strong>Assessor:</strong> {html.escape(report['assessor'])}</p>
            <p><strong>Scope:</strong> {html.escape(report['scope'])}</p>
            <p><strong>Methodology:</strong> {html.escape(report['methodology'])}</p>
        </div>
        <h2>Executive Summary</h2>
        <p>{html.escape(generate_ai_summary(report.get('findings', []), report.get('scope', 'N/A')) or f'A security assessment was conducted. {len(report["findings"])} findings were identified.')}</p>
        <h2>Findings</h2>
        <table><tr><th>#</th><th>Finding</th><th>Severity</th></tr>
{rows}
        </table>
        <h2>Recommendations</h2>
{rec_blocks}
        <div class="footer">Generated by CYBER-OMNI on {html.escape(get_timestamp())}</div>
    </div>
</body>
</html>"""
        with open(path, "w") as f:
            f.write(html_content)
