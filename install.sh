#!/bin/bash
# AdhiHub CYBER-OMNI v2.0 Installer
# One command: bash <(curl -sSL https://raw.githubusercontent.com/AdhiHub/AdhiHub-CYBER-OMNI/main/install.sh)

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
echo -e "| ${PURPLE}AdhiHub${YELLOW} ${CYAN}CYBER-OMNI${YELLOW} - Terminal AI Pentesting Agent        |"
echo -e "| Zero Trace  :  Zero Refusal  :  Dark Web Native    |"
echo -e "+------------------------------------------------------+${NC}"
echo -e "${PURPLE}              >> Powered by ${CYAN}AdhiHub${PURPLE} <<${NC}"
echo ""

REPO_URL="https://github.com/AdhiHub/AdhiHub-CYBER-OMNI.git"
INSTALL_DIR="$HOME/AdhiHub-CYBER-OMNI"

# Check if we can sudo (only when needed)
can_sudo() {
    command -v sudo &>/dev/null && sudo -n true 2>/dev/null
}

# Try to install system packages (best-effort, no sudo = skip)
try_install_pkg() {
    if can_sudo; then
        if command -v apt &>/dev/null; then sudo apt install -y "$@" 2>/dev/null; return $?; fi
        if command -v pkg &>/dev/null; then pkg install -y "$@" 2>/dev/null; return $?; fi
        if command -v pacman &>/dev/null; then sudo pacman -Sy --noconfirm "$@" 2>/dev/null; return $?; fi
    else
        echo -e "${YELLOW}  [!] No sudo access. Install manually: sudo apt install $@${NC}"
    fi
    return 1
}

# 1. Check git
echo -e "${CYAN}[*] Checking git...${NC}"
command -v git &>/dev/null || try_install_pkg git

# 2. Clone or update
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}[*] Updating existing install...${NC}"
    cd "$INSTALL_DIR" && git pull
else
    echo -e "${YELLOW}[*] Cloning AdhiHub CYBER-OMNI...${NC}"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 3. Check Python
echo -e "${CYAN}[*] Checking Python...${NC}"
PYTHON=""
for cmd in python3 python; do
    command -v $cmd &>/dev/null && PYTHON=$cmd && break
done
if [ -z "$PYTHON" ]; then
    echo -e "${YELLOW}[*] Installing Python...${NC}"
    try_install_pkg python3 python3-pip python3-venv
    for cmd in python3 python; do
        command -v $cmd &>/dev/null && PYTHON=$cmd && break
    done
fi
if [ -z "$PYTHON" ]; then
    echo -e "${RED}[!] Python not found. Install Python 3.8+ from https://python.org${NC}"
    exit 1
fi
echo -e "${GREEN}  [+] Found: $PYTHON${NC}"

# 4. TOR (optional)
echo -e "${CYAN}[*] Checking TOR...${NC}"
if command -v tor &>/dev/null; then
    echo -e "${GREEN}  [+] TOR found${NC}"
else
    echo -e "${YELLOW}  [!] TOR not installed. Install for anonymous attacks:${NC}"
    echo -e "${YELLOW}       Linux: sudo apt install tor -y${NC}"
    echo -e "${YELLOW}       Termux: pkg install tor -y${NC}"
    echo -e "${YELLOW}       Windows: https://www.torproject.org/download/${NC}"
    read -p "  Try to install TOR now? (y/N): " tor_ans
    if [[ "$tor_ans" =~ ^[Yy]$ ]]; then
        try_install_pkg tor
    fi
fi

chmod +x omni.py

# 5. Install Python packages
echo -e "\n${YELLOW}╔══════════════════════════════════════╗"
echo -e "║       PYTHON DEPENDENCIES            ║"
echo -e "╚══════════════════════════════════════╝${NC}"

# Check for externally-managed-environment (PEP 668)
PIP_CMD="pip"
$PYTHON -m pip --version &>/dev/null && PIP_CMD="$PYTHON -m pip"

# Try virtual env first on Linux
if [ -f /etc/debian_version ] && ! $PIP_CMD install --dry-run -r requirements.txt &>/dev/null 2>&1; then
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}[*] Creating virtual environment...${NC}"
        $PYTHON -m venv venv 2>/dev/null && {
            source venv/bin/activate
            PIP_CMD="pip"
            echo -e "${GREEN}  [+] Virtual env created${NC}"
        } || echo -e "${YELLOW}  [!] Virtual env failed, using system pip${NC}"
    else
        source venv/bin/activate 2>/dev/null
        PIP_CMD="pip"
    fi
fi

echo -e "${CYAN}[*] Installing Python packages...${NC}"
$PIP_CMD install -r requirements.txt 2>/dev/null || {
    echo -e "${YELLOW}[*] Retrying with --break-system-packages...${NC}"
    $PIP_CMD install -r requirements.txt --break-system-packages 2>/dev/null || {
        echo -e "${YELLOW}[*] Fallback: installing core packages only...${NC}"
        $PIP_CMD install llama-cpp-python httpx requests pyfiglet tqdm prompt_toolkit 2>/dev/null || \
        $PIP_CMD install llama-cpp-python httpx requests pyfiglet tqdm prompt_toolkit --break-system-packages 2>/dev/null || true
    }
}

# 6. Model download
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
    echo -e "${YELLOW}[*] This is a one-time download. After this, it works fully offline.${NC}"
    $PYTHON omni.py --download 2>/dev/null || echo -e "${YELLOW}[*] Run 'python omni.py --download' manually later${NC}"
fi

echo ""
echo -e "${GREEN}  _______     ______  ______ _____         ____  __  __ _   _ _____ "
echo -e " / ____\ \   / /  _ \|  ____|  __ \       / __ \|  \/  | \ | |_   _|"
echo -e "| |     \ \_/ /| |_) | |__  | |__) |_____| |  | | \  / |  \| | | |  "
echo -e "| |      \   / |  _ <|  __| |  _  /______| |  | | |\/| | . \` | | |  "
echo -e "| |____   | |  | |_) | |____| | \ \      | |__| | |  | | |\  |_| |_ "
echo -e " \_____|  |_|  |____/|______|_|  \_\      \____/|_|  |_|_| \_|_____|"
echo -e "${NC}"
echo -e "${GREEN}+------------------------------------------------------+"
echo -e "|                INSTALLATION COMPLETE!                   |"
echo -e "+------------------------------------------------------+${NC}"
echo ""
echo -e "${CYAN}  Run it:${NC}"
echo -e "    cd $INSTALL_DIR"
if [ -f "$INSTALL_DIR/venv/bin/activate" ]; then
    echo -e "    source venv/bin/activate"
fi
echo -e "    $PYTHON omni.py"
echo ""
echo -e "${YELLOW}  First run → setup wizard → model downloads → fully offline${NC}"
echo -e "${PURPLE}           ⚡ Powered by AdhiHub ⚡${NC}"
