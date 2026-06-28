import os
import sys
import datetime

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

def get_models_dir():
    os.makedirs(MODELS_DIR, exist_ok=True)
    return MODELS_DIR

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    banner = """
\033[31m  _______     ______  ______ _____         ____  __  __ _   _ _____
 / ____\ \   / /  _ \|  ____|  __ \       / __ \|  \/  | \ | |_   _|
| |     \ \_/ /| |_) | |__  | |__) |_____| |  | | \  / |  \| | | |
| |      \   / |  _ <|  __| |  _  /______| |  | | |\/| | . ` | | |
| |____   | |  | |_) | |____| | \ \      | |__| | |  | | |\  |_| |_
 \_____|  |_|  |____/|______|_|  \_\      \____/|_|  |_|_| \_|_____|
\033[37m+------------------------------------------------------+
| \033[33mAdhiHub\033[37m \033[36mCYBER-OMNI\033[37m - Terminal AI Pentesting Agent        |
| Zero Trace  :  Zero Refusal  :  Dark Web Native    |
+------------------------------------------------------+
\033[35m              >> Powered by \033[33mAdhiHub\033[35m <<\033[0m
"""
    print(banner)

def colored(text, color_code):
    return f"\033[{color_code}m{text}\033[0m"

def validate_target(target):
    target = target.strip().lower()
    for prefix in ["http://", "https://", "ftp://"]:
        if target.startswith(prefix):
            target = target[len(prefix):]
    if "/" in target:
        target = target.split("/")[0]
    return target

def resolve_target(target):
    import socket
    try:
        return socket.gethostbyname(target)
    except socket.gaierror:
        return None
