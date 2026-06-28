import os
import sys
import importlib.util
import inspect
from core.utils import colored


class PluginManager:
    def __init__(self, plugin_dir=None):
        if plugin_dir:
            self.plugins_dir = plugin_dir
        else:
            self.plugins_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins")
        self.plugins = {}
        self.commands = {}
        os.makedirs(self.plugins_dir, exist_ok=True)
        self._create_example()

    def _create_example(self):
        path = os.path.join(self.plugins_dir, "example_plugin.py")
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write('''import subprocess
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
''')

    def load_plugins(self):
        self.plugins = {}
        self.commands = {}
        count = 0
        for fname in sorted(os.listdir(self.plugins_dir)):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            path = os.path.join(self.plugins_dir, fname)
            try:
                mod_name = fname[:-3]
                spec = importlib.util.spec_from_file_location(mod_name, path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)

                if hasattr(mod, "register") and hasattr(mod, "handle"):
                    info = mod.register()
                    name = info["name"]
                    self.plugins[name] = {
                        "module": mod,
                        "info": info,
                        "path": path
                    }
                    for cmd_info in info.get("commands", []):
                        cmd_name = cmd_info["name"]
                        self.commands[cmd_name] = {
                            "plugin": name,
                            "info": cmd_info
                        }
                    count += 1
                    print(colored(f"  [Plugin] Loaded: {name} v{info.get('version', '?')}", "32"))
            except Exception as e:
                print(colored(f"  [Plugin] Failed to load {fname}: {e}", "31"))
        return count

    def handle_command(self, cmd, args, extra=None):
        if cmd in self.commands:
            plugin_name = self.commands[cmd]["plugin"]
            plugin = self.plugins[plugin_name]
            try:
                return plugin["module"].handle(cmd, args, extra)
            except Exception as e:
                print(colored(f"  [Plugin Error] {plugin_name}: {e}", "31"))
            return True
        return False

    def list_plugins(self):
        if not self.plugins:
            print(colored("  No plugins loaded.", "33"))
            print(colored("  Add .py files to: plugins/", "33"))
            return
        print(colored(f"\n  Loaded Plugins ({len(self.plugins)}):", "36"))
        for name, plugin in self.plugins.items():
            info = plugin["info"]
            print(colored(f"    \u25CF {name}", "32"))
            print(f"      v{info.get('version', '?')} — {info.get('description', '')}")
            for cmd_info in info.get("commands", []):
                print(f"      \u2514 /{cmd_info['name']}  {cmd_info.get('description', '')}")
        print()

    def get_help(self):
        lines = []
        for name, plugin in self.plugins.items():
            info = plugin["info"]
            for cmd_info in info.get("commands", []):
                lines.append((f"/{cmd_info['name']}", cmd_info.get('description', ''), cmd_info.get('usage', '')))
        return lines
