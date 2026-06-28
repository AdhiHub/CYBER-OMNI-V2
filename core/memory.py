class ConversationMemory:
    def __init__(self, max_turns=20, system_prompt=None):
        self.max_turns = max_turns
        self.messages = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def add_user(self, content):
        self.messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant(self, content):
        self.messages.append({"role": "assistant", "content": content})
        self._trim()

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})
        self._trim()

    def _trim(self):
        if len(self.messages) > self.max_turns + 1:
            system = [m for m in self.messages if m["role"] == "system"]
            others = [m for m in self.messages if m["role"] != "system"][-(self.max_turns):]
            self.messages = system + others

    def get_messages(self):
        return self.messages

    def clear(self, system_prompt=None):
        self.messages = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def get_context(self):
        lines = []
        for m in self.messages:
            role = "User" if m["role"] == "user" else "Assistant" if m["role"] == "assistant" else "System"
            lines.append(f"{role}: {m['content']}")
        return "\n".join(lines)
