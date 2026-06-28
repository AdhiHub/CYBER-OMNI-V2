import os
import sys
from core.context import SYSTEM_PROMPT
from core.memory import ConversationMemory
from core.downloader import ensure_model
from core.utils import colored

class AIEngine:
    def __init__(self):
        self.model_path = None
        self.llm = None
        self.model_name = "unknown"
        self.use_ollama = False
        self.ollama_model = "tinyllama:latest"
        self.initialized = False
        self.model_key = None

    def initialize(self, prompt_download=True, model_key=None):
        self.model_key = model_key
        if self._try_ollama():
            self.initialized = True
            return True
        if self._find_local_model():
            return self._load_model()
        if prompt_download:
            return self._try_local_model()
        return False

    def _try_ollama(self):
        try:
            import requests
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            if r.status_code == 200:
                self.use_ollama = True
                self.initialized = True
                models = r.json().get("models", [])
                if models:
                    self.ollama_model = models[0]["name"]
                return True
        except Exception:
            pass
        return False

    def _find_local_model(self):
        import glob
        from core.utils import get_models_dir
        dirpath = get_models_dir()
        gguvs = glob.glob(os.path.join(dirpath, "*.gguf"))
        if gguvs:
            self.model_path = gguvs[0]
            self.model_name = os.path.basename(gguvs[0]).replace(".gguf", "")
            return True
        return False

    def _try_local_model(self):
        path = ensure_model(self.model_key)
        if path is None:
            return False
        self.model_path = path
        self.model_name = os.path.basename(path).replace(".gguf", "")
        return self._load_model()

    def _load_model(self):
        try:
            from llama_cpp import Llama
            print(colored(f"[*] Loading model: {self.model_name}", "33"))
            print(colored("[*] AdhiHub CYBER-OMNI — initializing AI engine...", "33"))
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            n_threads = max(2, cpu_count - 1)
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=2048, n_threads=n_threads, n_gpu_layers=0, verbose=False
            )
            self.initialized = True
            print(colored(f"[+] AdhiHub CYBER-OMNI ready — model loaded: {self.model_name}", "32"))
            return True
        except ImportError:
            print(colored("\n[!] llama-cpp-python not installed.", "31"))
            print(colored("[*] Install: pip install llama-cpp-python", "33"))
            return False
        except Exception as e:
            print(colored(f"\n[!] Failed to load model: {e}", "31"))
            return False

    def chat(self, memory, query, stream=True):
        memory.add_user(query)
        messages = memory.get_messages()
        if stream and self.llm is not None:
            return self._stream_local(memory, messages)
        elif stream and self.use_ollama:
            return self._stream_ollama(memory, messages)
        return self._generate(memory, messages)

    def chat_raw(self, memory, query):
        """Non-streaming chat that returns the response as a string without printing."""
        memory.add_user(query)
        messages = memory.get_messages()
        try:
            if self.llm is not None:
                r = self.llm.create_chat_completion(messages, max_tokens=1024, temperature=0.7)
                content = r["choices"][0]["message"]["content"]
            elif self.use_ollama:
                import requests
                fm = [{"role": m["role"], "content": m["content"]} for m in messages]
                r = requests.post("http://localhost:11434/api/chat",
                    json={"model": self.ollama_model, "messages": fm, "stream": False}, timeout=120)
                content = r.json()["message"]["content"]
            else:
                content = "[!] No AI engine available"
            memory.add_assistant(content)
            return content
        except Exception as e:
            return f"[!] AI error: {e}"

    def _stream_local(self, memory, messages):
        collected = []
        try:
            for chunk in self.llm.create_chat_completion(messages, stream=True, max_tokens=1024, temperature=0.7):
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    collected.append(content)
                    sys.stdout.write(content)
                    sys.stdout.flush()
        except Exception as e:
            msg = f"\n[!] Error: {e}"
            collected.append(msg)
            sys.stdout.write(colored(msg, "31"))
            sys.stdout.flush()
        full = "".join(collected)
        memory.add_assistant(full)
        print()
        return full

    def _stream_ollama(self, memory, messages):
        try:
            import json, httpx
            full_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
            with httpx.Client(timeout=120) as client:
                with client.stream("POST", "http://localhost:11434/api/chat",
                    json={"model": self.ollama_model, "messages": full_messages, "stream": True}) as resp:
                    collected = []
                    for line in resp.iter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    c = data["message"]["content"]
                                    collected.append(c)
                                    sys.stdout.write(c)
                                    sys.stdout.flush()
                            except json.JSONDecodeError:
                                pass
                    full = "".join(collected)
                    memory.add_assistant(full)
                    print()
                    return full
        except Exception as e:
            msg = f"\n[!] Ollama error: {e}"
            print(colored(msg, "31"))
            memory.add_assistant(msg)
            return msg

    def _generate(self, memory, messages):
        try:
            if self.llm is not None:
                r = self.llm.create_chat_completion(messages, max_tokens=1024, temperature=0.7)
                content = r["choices"][0]["message"]["content"]
            elif self.use_ollama:
                import requests
                fm = [{"role": m["role"], "content": m["content"]} for m in messages]
                r = requests.post("http://localhost:11434/api/chat",
                    json={"model": self.ollama_model, "messages": fm, "stream": False}, timeout=120)
                content = r.json()["message"]["content"]
            else:
                content = "[!] No AI engine available"
            memory.add_assistant(content)
            print(content)
            return content
        except Exception as e:
            msg = f"[!] Error: {e}"
            print(colored(msg, "31"))
            memory.add_assistant(msg)
            return msg

    def get_info(self):
        if self.llm is not None:
            if self.model_name and "cyber-omni" in self.model_name.lower():
                return f"CYBER-OMNI Fine-Tuned: {self.model_name}"
            return f"Local model: {self.model_name}"
        elif self.use_ollama:
            return f"Ollama: {self.ollama_model}"
        return "No model loaded"
