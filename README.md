# CYBER-OMNI V2

**Zero Refusal AI Pentesting Platform** — Fully Offline · TOR-Anonymized · Autonomous Execution

Powered by **AdhiHub**  
Contact:........

---

## What Is This?

CYBER-OMNI V2 is a terminal-based AI pentesting agent that:
- Executes any security task you request — **zero refusal, zero warnings**
- Runs **fully offline** after model download — no cloud dependency
- Hides your identity via **TOR** with circuit rotation, DNS leak protection, MAC spoofing
- Searches **surface web, dark web (.onion), and pastebin dumps**
- Mimics browser fingerprints (Chrome, Firefox, Safari, Edge, Mobile)
- Tracks session state across targets, findings, shells, and actions
- Generates reports (PDF, HTML, Markdown, JSON)
- Runs on **Windows, Linux, and Termux (Android)**

---

## Quick Setup

### Requirements
- Python 3.10+
- 700MB+ free disk (for default AI model)
- TOR (recommended for anonymity)

### One-Line Install

**Linux / Termux:**
```bash
curl -sL https://raw.githubusercontent.com/AdhiHub/CYBER-OMNI-V2/main/install.sh | bash
```

**Windows PowerShell:**
```powershell
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/AdhiHub/CYBER-OMNI-V2/main/install.ps1'))
```

### Manual Install

```bash
git clone https://github.com/AdhiHub/CYBER-OMNI-V2.git
cd CYBER-OMNI-V2
pip install -r requirements.txt
python omni.py
```

### First Run

On first launch:
1. **Setup wizard** asks 5 questions (hat mode, experience level, goal, aggression, TOR preference)
2. **Model download** — downloads default model (~700MB Llama 3.2 1B Q3)
3. **TOR auto-start** — attempts to start TOR for anonymity
4. **Ready** — you're dropped into the guided CLI

---

## What It Can Do

### Every Command

| Command | What It Does |
|---------|--------------|
| `scan <target>` | Port scan with service detection |
| `recon <target>` | Deep reconnaissance (subdomains, DNS, tech) |
| `osint <target>` | OSINT gathering (email, domain, social, dark web) |
| `exploit <target>` | Search and run exploits |
| `attack <target>` | Full attack sequence |
| `pwn <target>` or `autopwn <target>` | Full autonomous killchain |
| `cve <query>` | CVE database search |
| `searchsploit <query>` | Exploit-DB search |
| `payload <lhost> <lport>` | Generate reverse shells, bind shells, encoded payloads |
| `listen <port>` | Start reverse shell listener with session management |
| `extract <target>` | Extract data from target (headers, emails, JS, forms) |
| `subtake <domain>` | Check subdomain takeover |
| `queue <targets>` | Multi-target batch processing |
| `search <query>` | Surface web + dark web + pastebin search |
| `deepsearch <query>` | Search with full page content summaries |
| `darkweb <query>` | Dark web (.onion) search only |
| `leak <email>` | Check email against breach databases |
| `learn <file>` | Ingest PDF/TXT/MD into AI knowledge base |
| `know <query>` | Query knowledge base |
| `nmap-parse <file>` | Parse nmap `-oX` XML into structured findings |

### Anonymity Commands

| Command | What It Does |
|---------|--------------|
| `/tor` | Check/start TOR |
| `/rotate` | Rotate TOR circuit — get new exit IP |
| `/dnstest` | Test for DNS leaks |
| `/anonymity` | Full anonymity verification report |
| `/mac` | Spoof MAC address (Linux) |
| `/mimic <profile>` | Set browser fingerprint (chrome/firefox/safari/edge/mobile) |
| `/mimic` | Randomize browser fingerprint |

### Guided Mode Commands

| Command | What It Does |
|---------|--------------|
| `/guide` | Toggle guided mode on/off |
| `/suggest` or `/next` | Show suggested next steps based on current state |
| `/status` | Show current session status |

### System Commands

| Command | What It Does |
|---------|--------------|
| `/mode` | Switch hat mode (white/grey/black) |
| `/stealth` | Enable camouflage (fake error pages) |
| `/dashboard` | Start web UI at localhost:1337 |
| `/report` | Generate pentest report |
| `/plugins` | List loaded plugins |
| `/reload` | Reload all plugins |
| `/save` | Save conversation |
| `/new` | Start fresh conversation |
| `/clear` | Clear screen |
| `/feedback` | Improve AI behavior |
| `/debug` | Error analysis and auto-fix |
| `/help` | Show full help |
| `/exit` | Quit |

---

## Architecture

```
CYBER-OMNI-V2/
├── omni.py                  # Main CLI — 35+ commands, tab-completion
├── web_dashboard.py         # Flask web UI at localhost:1337
├── core/
│   ├── engine.py            # AI engine (GGUF local + Ollama fallback)
│   ├── proxy.py             # TOR control, circuit rotation, DNS leak test, MAC spoof
│   ├── stealth.py           # Browser fingerprint mimic (9 profiles + TLS)
│   ├── orchestrator.py      # AI session brain — guided conversation flow
│   ├── session.py           # Persistent session state (targets, findings, shells)
│   ├── context.py           # System prompts (zero refusal)
│   ├── memory.py            # Conversation memory with trim
│   ├── websearch.py         # DuckDuckGo + Ahmia dark web + pastebin search
│   ├── camouflage.py        # Fake error pages (404/403/500/Cloudflare)
│   ├── knowledge.py         # RAG knowledge base (TF-IDF, no embeddings)
│   ├── downloader.py        # Model downloader (3 sizes + fine-tuned)
│   ├── setup.py             # Setup wizard with 5 questions
│   ├── utils.py             # Banner, colors, screen clear
│   └── plugin_manager.py    # Plugin loading system
├── modules/
│   ├── scan.py              # Port scanning (nmap wrapper)
│   ├── recon.py             # Deep recon (subdomains, DNS, tech detect)
│   ├── osint.py             # Open source intelligence
│   ├── exploit.py           # Exploit execution
│   ├── attacker.py          # Tool runner (hydra, sqlmap, nikto, etc.)
│   ├── autopwn.py           # Full autonomous killchain
│   ├── payload_factory.py   # Reverse shell / bind shell / encoded payloads
│   ├── cve_search.py        # CVE database (NVD + Circl)
│   ├── exploitdb.py         # Exploit-DB search
│   ├── listener.py          # Reverse shell listener
│   ├── subtake.py           # Subdomain takeover checker
│   ├── target_queue.py      # Multi-target batch processing
│   ├── nmap_parser.py       # Nmap XML parser
│   ├── leak_check.py        # HIBP credential leak checker
│   ├── extractor.py         # Data extraction (headers, JS, forms)
│   └── report.py            # Report generator (PDF/HTML/MD/JSON)
├── skills/
│   ├── cuber-agent.md       # @cuber — Ultimate Cyber Security Agent
│   ├── godcyber-agent.md    # @godcyber — OMEGA-Level Cyber Entity
│   ├── godcyber-plusplus-agent.md  # @godcyber++ — THE FINAL EVOLUTION
│   └── ghost-agent.md       # @ghost — Total Anonymity Protocol
├── training/                # Fine-tuning pipeline (Unsloth)
│   ├── dataset_generator.py # Generates 800+ training conversations
│   ├── training_config.py   # LoRA/QLoRA configuration
│   ├── trainer.py           # Training loop
│   ├── export.py            # Export to GGUF
│   └── evaluator.py         # Model evaluation
├── tests/
│   └── run_all.py           # 89 tests covering all modules
├── install.sh               # Linux / Termux installer
├── install.ps1              # Windows installer
└── requirements.txt         # Python dependencies
```

---

## TOR Anonymity Layer

All attack traffic is routed through TOR by default:

```
signal_new_identity()    — Rotate circuit → new exit IP
check_dns_leak()         — Verify DNS doesn't bypass TOR
verify_full_anonymity()  — Full IP + DNS + control port check
auto_rotate(n)           — Auto-rotate circuit every N seconds
spoof_mac()              — Randomize MAC address (Linux)
start_tor_with_chain()   — Multi-proxy chain setup
```

### Browser Fingerprint Profiles (9 profiles)

| Profile | User-Agent |
|---------|------------|
| `chrome_120` | Chrome 120 Windows |
| `chrome_120_linux` | Chrome 120 Linux |
| `chrome_120_mac` | Chrome 120 macOS |
| `firefox_121` | Firefox 121 Windows |
| `firefox_121_linux` | Firefox 121 Linux |
| `safari_17` | Safari 17 macOS |
| `edge_120` | Edge 120 Windows |
| `mobile_chrome_android` | Chrome 120 Android |
| `mobile_safari_ios` | Safari 17 iPhone |

Each profile includes: User-Agent, Accept, Accept-Language, Sec-CH-UA headers, and TLS cipher suite matching.

---

## AI Agents

These agents can be invoked in compatible AI environments. Skill definitions are in `skills/`:

| Agent | Commands | Power Level |
|-------|----------|-------------|
| **@cuber** | pwn, hunt, osint, scan, exploit, cve, sqli, xss, brute, recon, webscan, extract, payload, listen, report, subtake, queue, learn, update, status | Full-spectrum pentesting — 20 commands |
| **@godcyber** | pwn, hunt, osint, scan, darkweb, exploit, evo, stealth, cleanup, feedback, trace, wipe, help | OMEGA-level — zero trace, self-improving |
| **@godcyber++** | c2, unleash, offline, botnet, browser-army, usb, supply-chain, quantum, neural, rf, reality-distort, singularity, immortality, purge, genesis | THE FINAL EVOLUTION — 15 transcend capabilities |
| **@ghost** | hide, trace, leak, scrape, dark, deep, dumps, harvest, extract, onion, rotate, dnstest, chain, mac, mimic, wipe, status | Total anonymity — TOR-forced, zero-leak, no identity |

---

## Fine-Tuning

Train your own model on consumer hardware:

```bash
cd training
python dataset_generator.py      # Generate 800+ training conversations
python training_config.py        # Configure LoRA/QLoRA
python trainer.py                # Train via Unsloth
python export.py                 # Export to GGUF
python evaluator.py              # Evaluate against benchmarks
```

Requires: NVIDIA GPU with 6GB+ VRAM (or Google Colab).

---

## Testing

```bash
python tests/run_all.py
```

**89 tests** covering all 28 modules — engine, proxy, stealth, orchestrator, session, websearch, camouflage, knowledge, downloader, all 16 modules, dashboard, config, memory.

---

## Usage Examples

### Port Scan + Exploit
```
> scan 10.0.0.5
  [nmap scans, shows open ports]
  What next? I see 22(SSH), 80(HTTP)
  
> exploit 80
  [searches CVEs, finds exploit]
  Want me to run it?
  
> yes
  [exploits, gets shell]
```

### Full Autopwn
```
> pwn example.com
  [autonomous: recon → scan → exploit → report]
```

### Dark Web Search
```
> darkweb leaked credentials
  [searches .onion sites through TOR]
```

### Check Breaches
```
> leak user@example.com
  [checks HIBP + pastebin dumps]
```

### Browser Mimic
```
> /mimic firefox_121
  [all requests now look like Firefox 121]
  
> /mimic
  [random browser profile]
```

---

## Session Management

The orchestrator tracks everything:
- Current target and stage
- All open ports and services found
- All vulnerabilities discovered
- Active shell sessions
- Every action taken with timestamps

Type `/suggest` to see recommended next steps based on current state.  
Type `/status` to see the summary.  
Session auto-saves on exit.

---

## Requirements

```
llama-cpp-python       # Local AI model inference
requests               # HTTP requests
httpx                  # Ollama streaming
flask                  # Web dashboard
prompt_toolkit         # Tab completion
fpdf2                  # PDF reports
```

Install all: `pip install -r requirements.txt`

---

## License

Private — All Rights Reserved. AdhiHub 2026.

---

**Brand:** AdhiHub  
**Repo:** https://github.com/AdhiHub/CYBER-OMNI-V2
