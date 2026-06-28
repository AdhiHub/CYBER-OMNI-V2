import subprocess
from core.utils import colored

def register():
    return {
        "name": "Example Plugin",
        "version": "1.0",
        "description": "Example plugin for CYBER-OMNI",
        "commands": [
            {
                "name": "hello",
                "description": "Say hello",
                "usage": "/hello"
            },
            {
                "name": "sysinfo",
                "description": "Show system info",
                "usage": "/sysinfo"
            }
        ]
    }

def handle(cmd, args, extra=None):
    if cmd == "hello":
        print(colored("  Hello from example plugin!", "32"))
        return True
    if cmd == "sysinfo":
        import platform
        print(colored(f"  System: {platform.system()} {platform.release()}", "36"))
        print(colored(f"  Python: {platform.python_version()}", "36"))
        return True
    return False
