import os
import sys
import urllib.request
import json
import hashlib
from core.utils import get_models_dir, colored

MODELS = {
    "llama-3.2-1b-q3": {
        "url": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q3_K_M.gguf",
        "filename": "llama-3.2-1b-q3_k_m.gguf",
        "size_gb": 0.7,
        "description": "Llama 3.2 1B Q3 (~700MB) — Best for low storage, runs anywhere"
    },
    "llama-3.2-3b-q4": {
        "url": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "filename": "llama-3.2-3b-q4_k_m.gguf",
        "size_gb": 2.0,
        "description": "Llama 3.2 3B Q4 (~2GB) — Best balance, smart responses"
    },
    "qwen-2.5-7b-q4": {
        "url": "https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        "filename": "qwen-2.5-7b-q4_k_m.gguf",
        "size_gb": 4.5,
        "description": "Qwen 2.5 7B Q4 (~4.5GB) — Powerful, near ChatGPT quality"
    },
    "cyber-omni-finetuned": {
        "url": None,
        "filename": "cyber-omni-finetuned-q4_k_m.gguf",
        "size_gb": None,
        "description": "CYBER-OMNI Fine-Tuned Model — Local, created via training pipeline"
    }
}

DEFAULT_MODEL = "llama-3.2-1b-q3"

class DownloadProgress:
    def __init__(self, total):
        self.total = total
        self.downloaded = 0
        self.last_percent = -1

    def update(self, chunk_size):
        self.downloaded += chunk_size
        percent = int(self.downloaded * 100 / self.total) if self.total else 0
        if percent != self.last_percent and percent % 5 == 0:
            self.last_percent = percent
            mb_dl = self.downloaded / (1024 * 1024)
            mb_total = self.total / (1024 * 1024)
            bar_len = 30
            filled = int(bar_len * percent // 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            sys.stdout.write(f"\r\033[33m  Downloading: [{bar}] {percent}% ({mb_dl:.0f}/{mb_total:.0f} MB)\033[0m")
            sys.stdout.flush()

def list_models():
    print(colored("\nAvailable Models:", "36"))
    print(colored("=" * 55, "36"))
    for key, info in MODELS.items():
        default = " [DEFAULT]" if key == DEFAULT_MODEL else ""
        print(f"  {key}{default}")
        print(f"    {info['description']}")
        print()
    return dict(MODELS)

def download_model(model_key=None):
    if model_key is None:
        model_key = DEFAULT_MODEL

    if model_key not in MODELS:
        print(colored(f"[!] Unknown model: {model_key}", "31"))
        return None

    info = MODELS[model_key]
    models_dir = get_models_dir()
    filepath = os.path.join(models_dir, info["filename"])

    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000000:
        mb = os.path.getsize(filepath) / (1024 * 1024)
        print(colored(f"[+] Model already downloaded: {os.path.basename(filepath)} ({mb:.0f} MB)", "32"))
        return filepath

    print(colored(f"\n[*] Downloading model: {model_key}", "33"))
    print(colored(f"    Size: ~{info['size_gb']} GB", "33"))
    print(colored(f"    URL: {info['url']}", "33"))
    print(colored(f"    To: {filepath}", "33"))
    print()

    try:
        req = urllib.request.Request(info["url"], headers={"User-Agent": "CYBER-OMNI/2.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            total = int(response.headers.get("Content-Length", 0))
            progress = DownloadProgress(total)
            chunk_size = 8192
            with open(filepath, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    progress.update(len(chunk))
            print()

        mb = os.path.getsize(filepath) / (1024 * 1024)
        print(colored(f"\n[+] Download complete: {mb:.0f} MB", "32"))
        return filepath

    except Exception as e:
        print(colored(f"\n[!] Download failed: {e}", "31"))
        if os.path.exists(filepath):
            os.remove(filepath)
        return None

def ensure_model(model_key=None):
    models_dir = get_models_dir()
    os.makedirs(models_dir, exist_ok=True)

    if model_key is None:
        model_key = DEFAULT_MODEL
    if model_key not in MODELS:
        model_key = DEFAULT_MODEL

    info = MODELS[model_key]
    filepath = os.path.join(models_dir, info["filename"])

    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000000:
        return filepath

    print(colored("\n[!] No AI model found locally", "33"))
    print(colored("[*] CYBER-OMNI needs to download a language model to work.", "33"))
    print(colored("[*] This is a one-time download. After this, it works fully offline.\n", "33"))

    print(colored("Available models:", "36"))
    for key, m in MODELS.items():
        d = " [RECOMMENDED]" if key == DEFAULT_MODEL else ""
        print(f"  {colored(key, '36')} — {m['description']}{d}")
    print()
    choice = input(f"Enter model name [{DEFAULT_MODEL}]: ").strip() or DEFAULT_MODEL

    return download_model(choice)
