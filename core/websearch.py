import socket
import urllib.request
import urllib.parse
import re
import html
import time
import random
import ssl
from core.proxy import check_tor
from core.utils import colored

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Android 14; Mobile; rv:109.0) Gecko/20100101 Firefox/119.0",
]


def random_ua():
    return random.choice(USER_AGENTS)


def build_opener(use_tor=True, timeout=15):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    if use_tor and check_tor():
        try:
            import socks
            proxy_type = socks.SOCKS5
            s = socks.socksocket()
            s.set_proxy(proxy_type, "127.0.0.1", 9050)
            s.settimeout(timeout)

            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({
                    "http": "socks5://127.0.0.1:9050",
                    "https": "socks5://127.0.0.1:9050",
                }),
                urllib.request.HTTPSHandler(context=ctx),
            )
            return opener, True
        except ImportError:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({
                    "http": "socks5://127.0.0.1:9050",
                    "https": "socks5://127.0.0.1:9050",
                }),
                urllib.request.HTTPSHandler(context=ctx),
            )
            return opener, True
        except Exception:
            pass

    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    return opener, False


def fetch_url(url, use_tor=True, timeout=15, max_size=500000):
    opener, used_tor = build_opener(use_tor, timeout)
    req = urllib.request.Request(url, headers={"User-Agent": random_ua()})
    try:
        resp = opener.open(req, timeout=timeout)
        data = resp.read(max_size)
        content_type = resp.headers.get("Content-Type", "")
        if "text" not in content_type and "html" not in content_type and "json" not in content_type:
            return None, used_tor
        text = data.decode("utf-8", errors="replace")
        return text, used_tor
    except Exception as e:
        return None, used_tor


def extract_text(html_content):
    text = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_links(html_content, base_url=""):
    links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html_content, re.IGNORECASE)
    return links


class WebSearch:
    def __init__(self):
        self.last_request = 0
        self.rate_limit = 1.5

    def _wait(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

    def search_ddg(self, query, max_results=8):
        """Search DuckDuckGo HTML (TOR-friendly, no API key needed)"""
        self._wait()
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        html_content, used_tor = fetch_url(url, use_tor=True, timeout=15)
        if not html_content:
            return [], used_tor

        results = []
        for match in re.finditer(
            r'<a[^>]*class="result__a"[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>',
            html_content, re.DOTALL
        ):
            link = html.unescape(match.group(1))
            title = extract_text(match.group(2))
            if link and title and len(results) < max_results:
                results.append({"title": title.strip(), "url": link})
        return results, used_tor

    def search_ahmia(self, query, max_results=8):
        """Search Ahmia (.onion search engine) through TOR"""
        if not check_tor():
            return [], False

        self._wait()
        url = f"https://ahmia.fi/search/?q={urllib.parse.quote(query)}"
        html_content, used_tor = fetch_url(url, use_tor=True, timeout=30)
        if not html_content:
            return [], used_tor

        results = []
        for match in re.finditer(
            r'<a[^>]*href=["\'](https?://[^"\']+\.onion[^"\']*)["\'][^>]*>(.*?)</a>',
            html_content, re.DOTALL
        ):
            link = html.unescape(match.group(1))
            title = extract_text(match.group(2))
            if link and title and len(results) < max_results:
                results.append({"title": title.strip(), "url": link, "type": "onion"})
        return results, used_tor

    def search_onion(self, query, max_results=8):
        """Search for .onion sites related to the query"""
        if not check_tor():
            return [], False

        results = []
        engines = [
            ("Ahmia", self.search_ahmia),
            ("DuckDuckGo", self.search_ddg),
        ]

        for name, engine in engines:
            res, used = engine(f"{query} site:*.onion", max_results)
            results.extend(res)
            if len(results) >= max_results:
                break

        return results[:max_results], True

    def fetch_onion_page(self, onion_url, timeout=30):
        """Fetch a .onion page directly through TOR"""
        if not check_tor():
            return None, False

        if ".onion" not in onion_url:
            return None, False

        html_content, used_tor = fetch_url(onion_url, use_tor=True, timeout=timeout)
        if html_content:
            text = extract_text(html_content)
            links = extract_links(html_content)
            return {"text": text[:5000], "links": links[:20]}, True
        return None, used_tor

    def deep_search(self, query, max_results=12):
        """Combined search across surface web and dark web"""
        print(colored(f"\n[*] Deep search for: {query}", "33"))
        tor_active = check_tor()
        if tor_active:
            print(colored("[+] TOR active — searching surface web + dark web", "32"))
        else:
            print(colored("[!] TOR not active — surface web only. Use /tor for dark web access", "33"))

        all_results = []

        print(colored("  [*] Searching DuckDuckGo...", "33"))
        ddg_results, _ = self.search_ddg(query)
        all_results.extend(ddg_results)
        print(colored(f"    -> {len(ddg_results)} surface results", "32"))

        if tor_active:
            print(colored("  [*] Searching Ahmia (.onion dark web)...", "33"))
            onion_results, _ = self.search_ahmia(query)
            all_results.extend(onion_results)
            print(colored(f"    -> {len(onion_results)} dark web results", "35"))

        print(colored(f"\n[*] Total: {len(all_results)} results\n", "36"))

        if not all_results:
            print(colored("  [!] No results found", "31"))
            return all_results

        for i, r in enumerate(all_results[:max_results], 1):
            rtype = colored("[DARK]", "35") if r.get("type") == "onion" else colored("[WEB]", "32")
            print(f"  {i}. {rtype} {r['title']}")
            print(f"     {r['url']}")
            print()

        return all_results[:max_results]

    def search_dumps(self, query, max_results=10):
        """Search for leaked credentials, pastebin dumps, data leaks via TOR"""
        self._wait()
        all_results = []

        dump_sites = [
            f"site:pastebin.com {query}",
            f"site:ghostbin.com {query}",
            f"site:rentry.org {query}",
            f"site:controlc.com {query}",
            f"site:ix.io {query}",
            f"site:hastebin.com {query}",
            f"\"leaked\" \"{query}\"",
            f"\"dump\" \"{query}\"",
            f"\"database\" \"leak\" \"{query}\"",
            f"\"credentials\" \"{query}\"",
        ]

        for dump_query in dump_sites:
            self._wait()
            results, used_tor = self.search_ddg(dump_query, max_results=3)
            for r in results:
                if r not in all_results:
                    all_results.append(r)

        if check_tor():
            for dump_query in dump_sites[:5]:
                self._wait()
                results, _ = self.search_ahmia(dump_query, max_results=2)
                for r in results:
                    if r not in all_results:
                        all_results.append(r)

        return all_results[:max_results]

    def search_and_summarize(self, query, max_results=5):
        """Search and fetch each result's content"""
        results = self.deep_search(query, max_results)

        summaries = []
        for i, r in enumerate(results[:3]):
            self._wait()
            content, _ = fetch_url(r["url"], use_tor=True, timeout=10)
            if content:
                text = extract_text(content)[:2000]
                summaries.append({"title": r["title"], "url": r["url"], "content": text})

        return summaries
