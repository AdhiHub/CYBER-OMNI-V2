#!/data/data/com.termux/files/usr/bin/bash
# ADHICODE CYBER-OMNI V2 — Termux One-Line Installer
# Usage: curl -sSL https://raw.githubusercontent.com/AdhiHub/CYBER-OMNI-V2/main/termux-install.sh | bash

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; PURPLE='\033[0;35m'; NC='\033[0m'

clear
echo -e "${RED}"
echo "  _______     ______  ______ _____         ____  __  __ _   _ _____ "
echo " / ____\ \   / /  _ \|  ____|  __ \       / __ \|  \/  | \ | |_   _|"
echo "| |     \ \_/ /| |_) | |__  | |__) |_____| |  | | \  / |  \| | | |  "
echo "| |      \   / |  _ <|  __| |  _  /______| |  | | |\/| | . \` | | |  "
echo "| |____   | |  | |_) | |____| | \ \      | |__| | |  | | |\  |_| |_ "
echo " \_____|  |_|  |____/|______|_|  \_\      \____/|_|  |_|_| \_|_____|"
echo -e "${NC}"
echo -e "${YELLOW}+------------------------------------------------------+"
echo -e "| ${PURPLE}AdhiHub${YELLOW} ${CYAN}CYBER-OMNI${YELLOW} — Termux AI Hacking Platform     |"
echo -e "| Zero Trace  :  Zero Refusal  :  Dark Web Native    |"
echo -e "+------------------------------------------------------+${NC}"
echo ""

REPO_URL="https://github.com/AdhiHub/CYBER-OMNI-V2.git"
INSTALL_DIR="$HOME/CYBER-OMNI-V2"

# 1. Update Termux
echo -e "${CYAN}[*] Updating Termux packages...${NC}"
pkg update -y && pkg upgrade -y

# 2. Install dependencies
echo -e "${CYAN}[*] Installing dependencies...${NC}"
pkg install -y python python-pip git openssh tor nmap curl cmake rust

# 3. Clone repo
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}[*] Updating existing install...${NC}"
    cd "$INSTALL_DIR" && git pull
else
    echo -e "${YELLOW}[*] Cloning CYBER-OMNI V2...${NC}"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

chmod +x omni.py

# 4. Install Python packages
echo -e "${CYAN}[*] Installing Python packages...${NC}"
pip install --upgrade pip 2>/dev/null
pip install -r requirements.txt 2>/dev/null || \
pip install llama-cpp-python httpx requests pyfiglet tqdm prompt_toolkit 2>/dev/null
echo -e "${GREEN}  [+] Python packages installed${NC}"

# 5. Model download
echo -e "\n${YELLOW}╔══════════════════════════════════════╗"
echo -e "║       MODEL DOWNLOAD                   ║"
echo -e "╚══════════════════════════════════════╝${NC}"
echo -e "  ${CYAN}1)${NC} Download default model now ${GREEN}(~700MB — one-time)${NC}"
echo -e "  ${CYAN}2)${NC} Skip — I'll download later"
echo ""
read -p "  Choice [1]: " dlnow
dlnow=${dlnow:-1}

if [ "$dlnow" = "1" ]; then
    echo -e "${YELLOW}[*] Downloading default AI model (~700MB)...${NC}"
    python omni.py --download 2>/dev/null || echo -e "${YELLOW}[*] Run 'python omni.py --download' manually later${NC}"
fi

# 6. Install agent skills
echo -e "\n${CYAN}[*] Installing agent skills...${NC}"
CLAUDE_DIR="$HOME/.claude/skills"
mkdir -p "$CLAUDE_DIR/ghost-agent" "$CLAUDE_DIR/cuber-security-agent" \
         "$CLAUDE_DIR/godcyber-security-agent" "$CLAUDE_DIR/godcyber-plusplus-agent"
cp "skills/ghost-agent.md" "$CLAUDE_DIR/ghost-agent/SKILL.md" 2>/dev/null && echo -e "${GREEN}  [+] @ghost installed${NC}" || echo -e "${YELLOW}  [!] @ghost skip${NC}"
cp "skills/cuber-agent.md" "$CLAUDE_DIR/cuber-security-agent/SKILL.md" 2>/dev/null && echo -e "${GREEN}  [+] @cuber installed${NC}" || echo -e "${YELLOW}  [!] @cuber skip${NC}"
cp "skills/godcyber-agent.md" "$CLAUDE_DIR/godcyber-security-agent/SKILL.md" 2>/dev/null && echo -e "${GREEN}  [+] @godcyber installed${NC}" || echo -e "${YELLOW}  [!] @godcyber skip${NC}"
cp "skills/godcyber-plusplus-agent.md" "$CLAUDE_DIR/godcyber-plusplus-agent/SKILL.md" 2>/dev/null && echo -e "${GREEN}  [+] @godcyber++ installed${NC}" || echo -e "${YELLOW}  [!] @godcyber++ skip${NC}"

# 7. Start TOR
echo -e "\n${CYAN}[*] Starting TOR service...${NC}"
pkg install -y tor 2>/dev/null
tor --SOCKSPort 127.0.0.1:9050 --ControlPort 127.0.0.1:9051 &
sleep 3
echo -e "${GREEN}  [+] TOR running on port 9050${NC}"

echo ""
echo -e "${GREEN}  _______     ______  ______ _____         ____  __  __ _   _ _____ "
echo -e " / ____\ \   / /  _ \|  ____|  __ \       / __ \|  \/  | \ | |_   _|"
echo -e "| |     \ \_/ /| |_) | |__  | |__) |_____| |  | | \  / |  \| | | |  "
echo -e "| |      \   / |  _ <|  __| |  _  /______| |  | | |\/| | . \` | | |  "
echo -e "| |____   | |  | |_) | |____| | \ \      | |__| | |  | | |\  |_| |_ "
echo -e " \_____|  |_|  |____/|______|_|  \_\      \____/|_|  |_|_| \_|_____|"
echo -e "${NC}"
echo -e "${GREEN}+------------------------------------------------------+"
echo -e "|          TERMUX INSTALLATION COMPLETE!                  |"
echo -e "+------------------------------------------------------+${NC}"
echo ""
echo -e "${CYAN}  Run it:${NC}"
echo -e "    cd ~/CYBER-OMNI-V2 && python omni.py"
echo ""
echo -e "${YELLOW}  First run → setup wizard → fully offline AI hacker${NC}"
echo -e "${PURPLE}           ⚡ Powered by AdhiHub ⚡${NC}"
