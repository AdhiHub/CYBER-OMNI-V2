import random
import ssl
import sys

BROWSER_PROFILES = {
    "chrome_120": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept_language": "en-US,en;q=0.9",
        "sec_ch_ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Windows"',
        "tls_fingerprint": "chrome_120",
    },
    "chrome_120_linux": {
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept_language": "en-US,en;q=0.9",
        "sec_ch_ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Linux"',
        "tls_fingerprint": "chrome_120",
    },
    "chrome_120_mac": {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept_language": "en-US,en;q=0.9",
        "sec_ch_ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"macOS"',
        "tls_fingerprint": "chrome_120",
    },
    "firefox_121": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept_language": "en-US,en;q=0.5",
        "tls_fingerprint": "firefox_121",
    },
    "firefox_121_linux": {
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept_language": "en-US,en;q=0.5",
        "tls_fingerprint": "firefox_121",
    },
    "safari_17": {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept_language": "en-US,en;q=0.9",
        "tls_fingerprint": "safari_17",
    },
    "edge_120": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept_language": "en-US,en;q=0.9",
        "sec_ch_ua": '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Windows"',
        "tls_fingerprint": "chrome_120",
    },
    "mobile_chrome_android": {
        "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept_language": "en-US,en;q=0.9",
        "sec_ch_ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec_ch_ua_mobile": "?1",
        "sec_ch_ua_platform": '"Android"',
        "tls_fingerprint": "chrome_120",
    },
    "mobile_safari_ios": {
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept_language": "en-US,en;q=0.9",
        "tls_fingerprint": "safari_17",
    },
}

USER_AGENTS_MOBILE = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Samsung Galaxy S24) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]

USER_AGENTS_DESKTOP = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

_CURRENT_PROFILE = None


def get_random_profile():
    return random.choice(list(BROWSER_PROFILES.values()))


def get_profile(name):
    return BROWSER_PROFILES.get(name, get_random_profile())


def set_profile(name):
    global _CURRENT_PROFILE
    if name in BROWSER_PROFILES:
        _CURRENT_PROFILE = BROWSER_PROFILES[name]
        return _CURRENT_PROFILE
    return None


def current_profile():
    global _CURRENT_PROFILE
    if _CURRENT_PROFILE is None:
        _CURRENT_PROFILE = get_random_profile()
    return _CURRENT_PROFILE


def randomize_profile():
    global _CURRENT_PROFILE
    _CURRENT_PROFILE = get_random_profile()
    return _CURRENT_PROFILE


def get_headers():
    profile = current_profile()
    return {
        "User-Agent": profile["user_agent"],
        "Accept": profile["accept"],
        "Accept-Language": profile["accept_language"],
        **({"Sec-CH-UA": profile["sec_ch_ua"]} if "sec_ch_ua" in profile else {}),
        **({"Sec-CH-UA-Mobile": profile["sec_ch_ua_mobile"]} if "sec_ch_ua_mobile" in profile else {}),
        **({"Sec-CH-UA-Platform": profile["sec_ch_ua_platform"]} if "sec_ch_ua_platform" in profile else {}),
    }


def get_user_agent():
    return current_profile()["user_agent"]


def get_request_kwargs():
    """Return kwargs suitable for urllib or requests to mimic browser TLS fingerprint."""
    profile = current_profile()
    headers = get_headers()
    kwargs = {"headers": headers}

    if profile.get("tls_fingerprint") in ("chrome_120",) and sys.platform != "win32":
        try:
            ctx = ssl.create_default_context()
            ctx.set_ciphers(
                "TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:"
                "TLS_CHACHA20_POLY1305_SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:"
                "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:"
                "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:"
                "ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:"
                "DHE-RSA-AES256-GCM-SHA384"
            )
            kwargs["context"] = ctx
        except Exception:
            pass

    return kwargs


def list_profiles():
    names = list(BROWSER_PROFILES.keys())
    current_name = None
    for name, profile in BROWSER_PROFILES.items():
        if _CURRENT_PROFILE and profile["user_agent"] == _CURRENT_PROFILE["user_agent"]:
            current_name = name
            break
    return names, current_name
