import os
import re
import json
import glob
from core.utils import colored


class KnowledgeBase:
    def __init__(self, knowledge_dir=None):
        if knowledge_dir:
            self.kb_dir = knowledge_dir
        else:
            self.kb_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")
        self.index_file = os.path.join(self.kb_dir, "index.json")
        self.documents = {}
        self.index = {}
        os.makedirs(self.kb_dir, exist_ok=True)
        self._load_index()

    def _load_index(self):
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file) as f:
                    data = json.load(f)
                    self.index = data.get("index", {})
                    self.documents = data.get("documents", {})
            except Exception:
                self.index = {}
                self.documents = {}

    def _save_index(self):
        with open(self.index_file, "w") as f:
            json.dump({"index": self.index, "documents": self.documents}, f, indent=2)

    def _chunk_text(self, text, max_chars=500):
        chunks = []
        paragraphs = text.split("\n\n")
        current = ""
        for p in paragraphs:
            if len(current) + len(p) < max_chars:
                current += p + "\n\n"
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = p + "\n\n"
        if current.strip():
            chunks.append(current.strip())
        return chunks if chunks else [text[:max_chars]]

    def _extract_text(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".txt":
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception as e:
                return f"[Error reading: {e}]"

        elif ext == ".md":
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception as e:
                return f"[Error reading: {e}]"

        elif ext == ".pdf":
            try:
                import subprocess
                result = subprocess.run(["pdftotext", filepath, "-"], capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout
            except Exception:
                pass
            try:
                import pdfminer.high_level
                text = pdfminer.high_level.extract_text(filepath)
                return text
            except Exception:
                pass
            return f"[PDF extraction requires: pip install pdfminer.six]"

        elif ext in (".py", ".js", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".conf", ".ini", ".cfg"):
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception as e:
                return f"[Error reading: {e}]"

        else:
            return f"[Unsupported format: {ext}]"

    def _tokenize(self, text):
        return set(re.findall(r'\b[a-zA-Z0-9_]{3,}\b', text.lower()))

    def ingest_file(self, filepath):
        if not os.path.exists(filepath):
            print(colored(f"  [!] File not found: {filepath}", "31"))
            return False

        name = os.path.basename(filepath)
        print(colored(f"  [*] Ingesting: {name}...", "33"))

        text = self._extract_text(filepath)
        if text.startswith("[Error") or text.startswith("[Unsupported") or text.startswith("[PDF"):
            print(colored(f"  [!] {text}", "31"))
            return False

        chunks = self._chunk_text(text)
        tokens = self._tokenize(text)

        self.documents[name] = {
            "path": filepath,
            "size": os.path.getsize(filepath),
            "chunks": len(chunks),
            "tokens": len(tokens),
            "content_preview": text[:200]
        }

        for token in tokens:
            if token not in self.index:
                self.index[token] = []
            self.index[token].append(name)

        self._save_index()
        print(colored(f"  [+] Ingested: {name}", "32"))
        print(colored(f"      {len(chunks)} chunks, {len(tokens)} unique terms", "36"))
        return True

    def ingest_directory(self, directory):
        if not os.path.isdir(directory):
            print(colored(f"  [!] Directory not found: {directory}", "31"))
            return 0

        count = 0
        for ext in ("*.txt", "*.md", "*.pdf", "*.py", "*.js", "*.html", "*.json", "*.xml", "*.conf", "*.ini"):
            for fp in glob.glob(os.path.join(directory, ext)):
                if self.ingest_file(fp):
                    count += 1
        return count

    def search(self, query, top_k=5):
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = {}
        for token in query_tokens:
            if token in self.index:
                for doc_name in self.index[token]:
                    scores[doc_name] = scores.get(doc_name, 0) + 1

        ranked = sorted(scores.items(), key=lambda x: -x[1])
        results = []
        for doc_name, score in ranked[:top_k]:
            preview = self.documents.get(doc_name, {}).get("content_preview", "")
            results.append({
                "document": doc_name,
                "score": score,
                "preview": preview
            })
        return results

    def retrieve_context(self, query, max_chars=2000):
        results = self.search(query, top_k=3)
        if not results:
            return ""

        context_parts = []
        total = 0
        for r in results:
            text = f"From '{r['document']}' (relevance: {r['score']}):\n{r['preview']}\n"
            if total + len(text) > max_chars:
                break
            context_parts.append(text)
            total += len(text)

        return "\n".join(context_parts)

    def list_documents(self):
        if not self.documents:
            print(colored("  No documents in knowledge base.", "33"))
            print(colored("  Use /learn <file> to add knowledge.", "33"))
            return

        print(colored(f"\n  Knowledge Base ({len(self.documents)} documents):", "36"))
        for name, info in sorted(self.documents.items()):
            size = info["size"]
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/1024/1024:.1f} MB"
            print(colored(f"    \u25CF {name}", "32"))
            print(f"      {size_str}, {info['chunks']} chunks, {info['tokens']} terms")

    def clear(self):
        self.documents = {}
        self.index = {}
        self._save_index()
        print(colored("  [+] Knowledge base cleared.", "32"))


def learn_file(path):
    kb = KnowledgeBase()
    if os.path.isdir(path):
        count = kb.ingest_directory(path)
        if count > 0:
            print(colored(f"  [+] Ingested {count} files from {path}", "32"))
        else:
            print(colored(f"  [!] No supported files found in {path}", "31"))
    else:
        kb.ingest_file(path)

    print(colored(f"\n  Total documents: {len(kb.documents)}", "36"))
    print(colored(f"  Total terms indexed: {len(kb.index)}", "36"))


def query_knowledge(query):
    kb = KnowledgeBase()
    context = kb.retrieve_context(query)
    if context:
        print(colored(f"\n  [Knowledge Base Results]\n", "33"))
        print(context)
    else:
        print(colored("  No relevant knowledge found.", "33"))
    return context
