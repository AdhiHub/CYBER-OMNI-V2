import json
import urllib.request
import urllib.error
import urllib.parse
from core.utils import colored

CIRCL_API = "https://cve.circl.lu/api/cve"
NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def fetch_json(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CYBER-OMNI/2.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def search_cve_by_id(cve_id):
    cve_id = cve_id.upper().strip()
    if not cve_id.startswith("CVE-"):
        cve_id = f"CVE-{cve_id}"
    data = fetch_json(f"{CIRCL_API}/{cve_id}")
    if data and "id" in data:
        return data
    return None


def search_cve_by_keyword(keyword):
    try:
        url = f"{NVD_API}?keywordSearch={urllib.parse.quote(keyword)}&resultsPerPage=10"
        req = urllib.request.Request(url, headers={"User-Agent": "CYBER-OMNI/2.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode()
        data = json.loads(raw)
        vulns = data.get("vulnerabilities", [])
        if vulns:
            return [v["cve"] for v in vulns]
    except Exception:
        pass
    try:
        url = f"https://cve.circl.lu/api/cve/search/{urllib.parse.quote(keyword)}"
        data = fetch_json(url, timeout=10)
        if data and isinstance(data, list):
            return data[:10]
    except Exception:
        pass
    return []


def format_cve(cve):
    lines = []
    cve_id = cve.get("id", "N/A")
    desc = ""
    descriptions = cve.get("descriptions") or cve.get("description") or []
    if isinstance(descriptions, list):
        for d in descriptions:
            if isinstance(d, dict) and d.get("lang") == "en":
                desc = d.get("value", "")
                break
            if isinstance(d, str):
                desc = d
                break
    elif isinstance(descriptions, str):
        desc = descriptions

    metrics = cve.get("metrics") or {}
    cvss_score = "N/A"
    cvss_severity = ""
    for version_key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
        if version_key in metrics:
            m = metrics[version_key][0]["cvssData"]
            cvss_score = str(m.get("baseScore", "N/A"))
            cvss_severity = m.get("baseSeverity", "")
            break

    if cvss_score == "N/A":
        try:
            cvss = cve.get("cvss", {})
            if cvss:
                cvss_score = str(cvss.get("score", "N/A"))
                cvss_severity = cvss.get("severity", "")
        except Exception:
            pass

    published = (cve.get("published") or cve.get("Published") or "N/A")[:10]

    lines.append(f"  ID: {colored(cve_id, '36')}")
    lines.append(f"  Published: {colored(published, '33')}")
    sev_color = "31" if cvss_severity in ("CRITICAL", "HIGH") or (cvss_score != "N/A" and float(cvss_score) >= 7) else "33"
    lines.append(f"  CVSS: {colored(cvss_score + ' ' + cvss_severity, sev_color)}")
    if desc:
        lines.append(f"  Description: {desc[:300]}")
    lines.append("")

    refs = cve.get("references") or []
    if refs:
        shown = 0
        for r in refs:
            url = r if isinstance(r, str) else r.get("url", "")
            if url and ("exploit" in url.lower() or "github" in url.lower() or "metasploit" in url.lower() or "packetstorm" in url.lower()):
                lines.append(f"    {colored('[PoC]', '31')} {url}")
                shown += 1
                if shown >= 3:
                    break
        if shown == 0:
            for r in refs[:2]:
                url = r if isinstance(r, str) else r.get("url", "")
                if url:
                    lines.append(f"    {url}")

    return "\n".join(lines)


def format_cve_short(cve):
    cve_id = cve.get("id", "N/A")
    desc = ""
    descriptions = cve.get("descriptions") or cve.get("description") or []
    if isinstance(descriptions, list):
        for d in descriptions:
            if isinstance(d, dict) and d.get("lang") == "en":
                desc = d.get("value", "")[:80]
                break
    elif isinstance(descriptions, str):
        desc = descriptions[:80]

    metrics = cve.get("metrics") or {}
    score = "?"
    for vk in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
        if vk in metrics:
            score = str(metrics[vk][0]["cvssData"].get("baseScore", "?"))
            break
    if score == "?":
        try:
            score = str(cve.get("cvss", {}).get("score", "?"))
        except Exception:
            pass

    return f"  {cve_id} [{colored(score, '31' if score != '?' and float(score) >= 7 else '33')}] {desc}"


def run_cve_search(query):
    query = query.strip()
    if not query:
        print(colored("[!] Usage: /cve <CVE-ID or keyword>", "31"))
        return

    if query.upper().startswith("CVE-") or query.upper().startswith("CVE "):
        query = query.replace(" ", "-")
        print(colored(f"\n[*] Looking up {query}...", "33"))
        cve = search_cve_by_id(query)
        if cve:
            print(colored("\n" + "\u2550" * 50, "36"))
            print(format_cve(cve))
            print(colored("\u2550" * 50, "36"))
            print(colored("  [?] Want to search PoC on GitHub? (y/N): ", "33"), end="")
            ans = input().strip().lower()
            if ans in ("y", "yes"):
                gh_url = f"https://github.com/search?q={urllib.parse.quote(query)}+PoC&type=repositories"
                print(colored(f"  [*] Open this URL in your browser:", "36"))
                print(f"     {gh_url}")
        else:
            print(colored(f"[!] No data found for {query}", "31"))
        return

    print(colored(f"\n[*] Searching CVEs for: {query}", "33"))
    results = search_cve_by_keyword(query)

    if not results:
        print(colored("[!] No results found or API unavailable", "31"))
        return

    print(colored(f"\n  Found {len(results)} CVEs:\n", "32"))
    for i, cve in enumerate(results, 1):
        print(f"  {i}. {format_cve_short(cve)}")
    print()

    choice = input(colored("  View details for CVE number (or Enter to skip): ", "33")).strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(results):
            cve_id = results[idx].get("id", "")
            if cve_id:
                print(colored(f"\n[*] Loading details for {cve_id}...", "33"))
                detail = search_cve_by_id(cve_id)
                if detail:
                    print(colored("\n" + "\u2550" * 50, "36"))
                    print(format_cve(detail))
                    print(colored("\u2550" * 50, "36"))
                    print(colored("  [?] Search PoC on GitHub? (y/N): ", "33"), end="")
                    ans = input().strip().lower()
                    if ans in ("y", "yes"):
                        gh_url = f"https://github.com/search?q={urllib.parse.quote(cve_id)}+PoC&type=repositories"
                        print(colored(f"  [*] Open in browser:", "36"))
                        print(f"     {gh_url}")
    elif choice.upper().startswith("CVE-"):
        print(colored(f"\n[*] Loading details for {choice}...", "33"))
        detail = search_cve_by_id(choice)
        if detail:
            print(colored("\n" + "\u2550" * 50, "36"))
            print(format_cve(detail))
            print(colored("\u2550" * 50, "36"))
