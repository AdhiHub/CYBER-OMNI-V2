import os
import sys
import json
import socket
from core.utils import colored

try:
    import dns.resolver
    HAVE_DNS = True
except ImportError:
    HAVE_DNS = False

CLOUD_SERVICES = {
    "aws": [
        ".s3.amazonaws.com",
        ".s3-us-west-2.amazonaws.com",
        ".s3-eu-west-1.amazonaws.com",
        ".s3-ap-southeast-1.amazonaws.com",
        "s3-website-us-east-1.amazonaws.com",
        "s3-website-us-west-2.amazonaws.com",
        "cloudfront.net",
        "elasticbeanstalk.com",
    ],
    "azure": [
        ".azurewebsites.net",
        ".azurefd.net",
        ".trafficmanager.net",
        ".blob.core.windows.net",
        ".cloudapp.net",
    ],
    "gcp": [
        ".appspot.com",
        ".storage.googleapis.com",
        ".firebaseio.com",
    ],
    "other": [
        ".herokuapp.com",
        ".firebaseapp.com",
        ".netlify.app",
        ".pages.dev",
        ".vercel.app",
        ".github.io",
        ".readthedocs.io",
        ".pantheonsite.io",
        ".unbouncepages.com",
        ".squarespace.com",
        ".wordpress.com",
        ".shopify.com",
        ".fastly.net",
        ".acmecache.com",
    ],
}


def check_dangling(domain):
    if not HAVE_DNS:
        return {"vulnerable": False, "error": "dnspython not installed (pip install dnspython)"}
    try:
        answers = dns.resolver.resolve(domain, "CNAME")
        for rdata in answers:
            target = str(rdata.target).rstrip(".")
            target_lower = target.lower()
            for provider, domains in CLOUD_SERVICES.items():
                for suffix in domains:
                    if suffix in target_lower or target_lower.endswith(suffix):
                        return {
                            "vulnerable": True,
                            "type": "dangling_cname",
                            "cname": target,
                            "provider": provider,
                        }
            return {
                "vulnerable": False,
                "type": "has_cname",
                "cname": target,
                "provider": "unknown",
            }
    except dns.resolver.NoAnswer:
        pass
    except dns.resolver.NXDOMAIN:
        return {
            "vulnerable": True,
            "type": "nxdomain",
            "cname": "NXDOMAIN",
            "provider": "unregistered",
        }
    except Exception as e:
        return {"vulnerable": False, "error": str(e)}
    return {"vulnerable": False, "type": "no_cname"}


def check_http_response(domain):
    try:
        import urllib.request
        req = urllib.request.Request(f"http://{domain}", headers={"User-Agent": "Mozilla/5.0"}, method="GET")
        with urllib.request.urlopen(req, timeout=8) as r:
            code = r.status
            body = r.read(500).decode(errors="replace").lower()
            takeover_indicators = [
                "there is nothing here",
                "no such bucket",
                "the specified bucket does not exist",
                "repository not found",
                "404 not found",
                "this page is not found",
                "no such app",
                "application not found",
                "heroku no such app",
                "page not found",
                "does not exist",
                "site not found",
                "not found, ",
                "domain is not configured",
                "cname does not resolve",
                "this site is not configured",
                "there is no app",
            ]
            for indicator in takeover_indicators:
                if indicator in body:
                    return {"vulnerable": True, "type": "http_indicator", "http_code": code, "indicator": indicator}
            return {"vulnerable": False, "http_code": code}
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            body = e.read(500).decode(errors="replace").lower()
            for indicator in [
                "there is nothing here", "no such bucket", "repository not found",
                "page not found", "site not found", "does not exist",
            ]:
                if indicator in body:
                    return {"vulnerable": True, "type": "http_indicator", "http_code": e.code, "indicator": indicator}
            return {"vulnerable": True, "type": "http_404", "http_code": e.code}
        return {"vulnerable": False, "http_code": e.code}
    except Exception as e:
        return {"vulnerable": False, "error": str(e)}


def check_subdomain(domain):
    result = {"domain": domain, "vulnerable": False, "checks": []}

    dns_result = check_dangling(domain)
    result["checks"].append(("DNS", dns_result))
    if dns_result.get("vulnerable"):
        result["vulnerable"] = True

    http_result = check_http_response(domain)
    result["checks"].append(("HTTP", http_result))
    if http_result.get("vulnerable"):
        result["vulnerable"] = True

    return result


def run_subtake(target):
    target = target.strip().lower()
    if not target:
        print(colored("[!] Usage: /subtake <domain>", "31"))
        return

    print(colored(f"\n[*] Checking subdomain takeover for: {target}", "33"))
    print(colored("[*] Checking DNS CNAME records...", "33"))

    result = check_subdomain(target)

    print(colored("\n" + "\u2550" * 50, "36"))
    print(colored(f"  Results for {target}", "36"))
    print(colored("\u2550" * 50, "36"))

    for check_type, check_result in result["checks"]:
        status = colored("[VULNERABLE]", "31") if check_result.get("vulnerable") else colored("[SAFE]", "32")
        print(f"\n  {check_type}: {status}")
        if check_result.get("vulnerable"):
            if check_result.get("type") == "dangling_cname":
                print(f"    CNAME: {check_result.get('cname', 'N/A')}")
                print(f"    Provider: {check_result.get('provider', 'N/A')}")
                print(colored(f"    [>] This subdomain CAN BE TAKEN OVER!", "31"))
                print(colored(f"    [>] Register the service at {check_result.get('provider', 'the cloud provider')}", "31"))
            elif check_result.get("type") == "nxdomain":
                print(colored(f"    [>] Domain does not exist (NXDOMAIN) - CAN BE REGISTERED", "31"))
            elif check_result.get("type") == "http_indicator":
                print(f"    HTTP: {check_result.get('http_code', 'N/A')}")
                print(f"    Indicator: {check_result.get('indicator', 'N/A')}")
                print(colored(f"    [>] HTTP response suggests takeover possible!", "31"))
            elif check_result.get("type") == "http_404":
                print(f"    HTTP: 404")
                print(colored(f"    [>] 404 response - may be vulnerable to takeover", "31"))
        elif check_result.get("error"):
            print(f"    Error: {check_result['error']}")
        else:
            if check_type == "DNS":
                cname = check_result.get("cname")
                if cname:
                    print(f"    CNAME: {cname}")
                else:
                    print(f"    No CNAME record found")

    if result["vulnerable"]:
        print(colored(f"\n  \u26a0 TAKEOVER POSSIBLE!", "31"))
        print(colored(f"  [>] Steps to exploit:", "33"))
        print(f"     1. Identify the cloud service ({result['checks'][0][1].get('provider', 'unknown')})")
        print(f"     2. Sign up for the service")
        print(f"     3. Claim the domain in the service settings")
        print(f"     4. Host your content")
    else:
        print(colored(f"\n  \u2713 No takeover detected", "32"))

    print(colored("\u2550" * 50 + "\n", "36"))

    print(colored("  [?] Scan a list of subdomains from file? (y/N): ", "33"), end="")
    ans = input().strip().lower()
    if ans in ("y", "yes"):
        path = input(colored("  Path to subdomain list (one per line): ", "33")).strip()
        if os.path.exists(path):
            with open(path) as f:
                subs = [l.strip() for l in f if l.strip()]
            print(colored(f"\n[*] Scanning {len(subs)} subdomains...\n", "33"))
            vulnerable = []
            for i, sub in enumerate(subs, 1):
                full_domain = f"{sub}.{target}" if "." not in sub else sub
                print(colored(f"  [{i}/{len(subs)}] {full_domain}", "36"), end="")
                res = check_subdomain(full_domain)
                if res["vulnerable"]:
                    print(colored(" [VULNERABLE]", "31"))
                    vulnerable.append(full_domain)
                else:
                    print(colored(" [SAFE]", "32"))
            if vulnerable:
                print(colored(f"\n[*] Vulnerable subdomains ({len(vulnerable)}):", "31"))
                for v in vulnerable:
                    print(f"  [>] {v}")
            else:
                print(colored(f"\n[*] No vulnerable subdomains found", "32"))
        else:
            print(colored(f"[!] File not found: {path}", "31"))
