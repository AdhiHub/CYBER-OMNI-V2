import os
import re
import json
import subprocess
import tempfile
from core.utils import colored
from core.proxy import check_tor


class DataExtractor:
    def __init__(self):
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "extracted_data")
        os.makedirs(self.output_dir, exist_ok=True)

    def _save(self, name, data):
        path = os.path.join(self.output_dir, name)
        if isinstance(data, (dict, list)):
            with open(path + ".json", "w") as f:
                json.dump(data, f, indent=2)
            return path + ".json"
        with open(path + ".txt", "w", encoding="utf-8", errors="replace") as f:
            f.write(str(data))
        return path + ".txt"

    def _run(self, cmd, timeout=60):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=True)
            return r.stdout + r.stderr
        except Exception as e:
            return str(e)

    def extract_http_headers(self, target):
        print(colored(f"  [*] Extracting HTTP headers from {target}...", "33"))
        out = self._run(f"curl -s -I -L --max-time 15 '{target}'")
        path = self._save(f"http_headers_{target.replace('/', '_')}", out)
        server = re.search(r"Server:\s*(.+)", out, re.I)
        if server:
            print(colored(f"    Server: {server.group(1)}", "32"))
        return out

    def extract_robots(self, target):
        url = target.rstrip("/") + "/robots.txt"
        print(colored(f"  [*] Fetching robots.txt from {url}...", "33"))
        out = self._run(f"curl -s -L --max-time 15 '{url}'")
        if "Disallow" in out or "Allow" in out:
            path = self._save(f"robots_{target.replace('/', '_')}", out)
            disallowed = re.findall(r"Disallow:\s*(.+)", out)
            if disallowed:
                print(colored(f"    Found {len(disallowed)} disallowed paths", "32"))
                for d in disallowed[:5]:
                    print(f"      {d}")
            return out
        print(colored("    No robots.txt or empty", "31"))
        return ""

    def extract_sitemap(self, target):
        url = target.rstrip("/") + "/sitemap.xml"
        print(colored(f"  [*] Fetching sitemap from {url}...", "33"))
        out = self._run(f"curl -s -L --max-time 15 '{url}'")
        if "<loc>" in out:
            urls = re.findall(r"<loc>(.+?)</loc>", out)
            path = self._save(f"sitemap_{target.replace('/', '_')}", out)
            print(colored(f"    Found {len(urls)} URLs in sitemap", "32"))
            return urls
        print(colored("    No sitemap.xml", "31"))
        return []

    def extract_page_content(self, target):
        print(colored(f"  [*] Extracting page content from {target}...", "33"))
        out = self._run(f"curl -s -L --max-time 15 '{target}'")
        path = self._save(f"page_{target.replace('/', '_')}", out)
        print(colored(f"    Saved {len(out)} bytes", "32"))

        emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", out))
        if emails:
            self._save(f"emails_{target.replace('/', '_')}", list(emails))
            print(colored(f"    Found {len(emails)} email addresses", "32"))

        phones = set(re.findall(r"[\+]?[\d\s\-\(\)]{7,15}", out))
        phones = {p for p in phones if len(re.sub(r"\D", "", p)) >= 7}
        if phones:
            self._save(f"phones_{target.replace('/', '_')}", list(phones))
            print(colored(f"    Found {len(phones)} phone numbers", "32"))

        links = re.findall(r'href=[\'"]?(https?://[^\'">\s]+)', out)
        if links:
            self._save(f"links_{target.replace('/', '_')}", list(set(links)))
            print(colored(f"    Found {len(set(links))} unique links", "32"))

        comments = re.findall(r"<!--(.+?)-->", out, re.DOTALL)
        if comments:
            self._save(f"comments_{target.replace('/', '_')}", comments)
            print(colored(f"    Found {len(comments)} HTML comments", "32"))

        return out

    def extract_js_files(self, target):
        print(colored(f"  [*] Extracting JavaScript files from {target}...", "33"))
        html = self._run(f"curl -s -L --max-time 15 '{target}'")
        js_files = re.findall(r'src=[\'"]([^\'"]*\.js[^\'"]*)[\'"]', html)
        if not js_files:
            print(colored("    No JS files found", "31"))
            return []

        results = []
        for js in js_files:
            if js.startswith("//"):
                js = "https:" + js
            elif js.startswith("/"):
                base = re.match(r"(https?://[^/]+)", target)
                if base:
                    js = base.group(1) + js
            elif not js.startswith("http"):
                js = target.rstrip("/") + "/" + js.lstrip("/")

            content = self._run(f"curl -s --max-time 10 '{js}'")
            if content and len(content) > 10:
                results.append({"url": js, "size": len(content)})
                self._save(f"js_{js.replace('/', '_').replace(':', '_')}", content)

        if results:
            self._save(f"js_files_{target.replace('/', '_')}", results)
            print(colored(f"    Extracted {len(results)} JS files", "32"))
        return results

    def extract_forms(self, target):
        print(colored(f"  [*] Extracting forms from {target}...", "33"))
        html = self._run(f"curl -s -L --max-time 15 '{target}'")
        forms = re.findall(r"<form\s(.+?)</form>", html, re.DOTALL | re.I)
        if not forms:
            print(colored("    No forms found", "31"))
            return []

        parsed = []
        for i, form in enumerate(forms):
            action = re.search(r'action=[\'"]([^\'"]*)[\'"]', form)
            method = re.search(r'method=[\'"]([^\'"]*)[\'"]', form, re.I)
            inputs = re.findall(r'<input\s(.+?)/?>', form, re.I)
            fields = []
            for inp in inputs:
                name = re.search(r'name=[\'"]([^\'"]*)[\'"]', inp)
                typ = re.search(r'type=[\'"]([^\'"]*)[\'"]', inp, re.I)
                fields.append({
                    "name": name.group(1) if name else "",
                    "type": typ.group(1) if typ else "text"
                })

            parsed.append({
                "action": action.group(1) if action else "",
                "method": method.group(1).upper() if method else "GET",
                "fields": fields
            })

        self._save(f"forms_{target.replace('/', '_')}", parsed)
        if parsed:
            print(colored(f"    Found {len(parsed)} form(s)", "32"))
            for p in parsed:
                print(f"      [{p['method']}] {p['action']} ({len(p['fields'])} fields)")
        return parsed

    def extract_directory_listing(self, target, path="/"):
        url = target.rstrip("/") + path
        print(colored(f"  [*] Checking for directory listing at {url}...", "33"))
        out = self._run(f"curl -s --max-time 15 '{url}'")

        dir_indicators = ["Index of /", "<title>Index of", "Parent Directory</a>", "[DIR]"]
        if any(ind in out for ind in dir_indicators):
            path = self._save(f"dir_listing_{target.replace('/', '_').replace(':', '_')}", out)
            entries = re.findall(r'<a href="([^"]+)">', out)
            print(colored(f"    Directory listing FOUND!", "32"))
            print(colored(f"    {len(entries)} entries", "32"))
            return True, entries
        print(colored("    No directory listing", "31"))
        return False, []

    def extract_all(self, target):
        print(colored(f"\n{'═' * 50}", "36"))
        print(colored(f"  DATA EXTRACTION — {target}", "36"))
        print(colored(f"{'═' * 50}\n", "36"))

        target = target if target.startswith("http") else f"http://{target}"

        results = {}
        results["headers"] = self.extract_http_headers(target)
        results["robots"] = self.extract_robots(target)
        results["sitemap"] = self.extract_sitemap(target)
        results["page"] = self.extract_page_content(target)
        results["js"] = self.extract_js_files(target)
        results["forms"] = self.extract_forms(target)

        self.extract_directory_listing(target)

        summary = {
            "target": target,
            "http_headers": bool(results.get("headers")),
            "robots_txt": bool(results.get("robots")),
            "sitemap": len(results.get("sitemap", [])),
            "js_files": len(results.get("js", [])),
            "forms": len(results.get("forms", [])),
        }
        summary_path = self._save(f"extraction_summary_{target.replace('/', '_').replace(':', '_')}", summary)

        print(colored(f"\n{'═' * 50}", "36"))
        print(colored(f"  EXTRACTION COMPLETE", "32"))
        print(colored(f"  Saved to: {self.output_dir}", "33"))
        print(colored(f"  Summary: {summary_path}", "33"))
        print(colored(f"{'═' * 50}", "36"))

        return summary


def run_extraction(target):
    if not target:
        print(colored("[!] Usage: /extract <target>", "31"))
        return

    if not target.startswith("http"):
        target = f"http://{target}"

    extractor = DataExtractor()
    extractor.extract_all(target)
