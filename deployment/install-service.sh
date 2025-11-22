#!/bin/bash
# AlgoTread Service Installation Script
# This script automates the installation of AlgoTread as a systemd service

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}AlgoTread Systemd Service Installation${NC}"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root${NC}"
    echo "Run as your regular user. The script will use sudo when needed."
    exit 1
fi

# Check if systemd is available
if ! command -v systemctl &> /dev/null; then
    echo -e "${RED}Error: systemd is not available on this system${NC}"
    exit 1
fi

# Get current user and group
CURRENT_USER=$(whoami)
CURRENT_GROUP=$(id -gn)

echo "Configuration:"
echo "  User: $CURRENT_USER"
echo "  Group: $CURRENT_GROUP"
echo "  Project Directory: $PROJECT_DIR"
echo ""

# Check if .env file exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create and configure .env file before installing the service"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo -e "${YELLOW}Warning: Virtual environment not found${NC}"
    echo "Creating virtual environment..."
    cd "$PROJECT_DIR"
    uv venv
    uv pip install -e .
fi

# Get Python path
PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
if [ ! -f "$PYTHON_PATH" ]; then
    echo -e "${RED}Error: Python not found in virtual environment${NC}"
    exit 1
fi

# Create data and logs directories if they don't exist
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/logs"

echo -e "${GREEN}Creating service file...${NC}"

# Create service file from template
SERVICE_FILE="/tmp/algotread.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=AlgoTread - Automated Intraday Trading System
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_GROUP
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"

# Load environment variables from .env file
EnvironmentFile=$PROJECT_DIR/.env

# Main command to run the trading system
ExecStart=$PYTHON_PATH -m src.main

# Restart policy
Restart=on-failure
RestartSec=10
StartLimitInterval=200
StartLimitBurst=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=algotread

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$PROJECT_DIR/data $PROJECT_DIR/logs

# Resource limits
MemoryLimit=2G
CPUQuota=200%

# Graceful shutdown
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}Installing service...${NC}"

# Copy service file to systemd directory
sudo cp "$SERVICE_FILE" /etc/systemd/system/algotread.service
sudo chmod 644 /etc/systemd/system/algotread.service

# Reload systemd
sudo systemctl daemon-reload

echo -e "${GREEN}Service installed successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Enable service to start on boot:"
echo "     ${YELLOW}sudo systemctl enable algotread${NC}"
echo ""
echo "  2. Start the service:"
echo "     ${YELLOW}sudo systemctl start algotread${NC}"
echo ""
echo "  3. Check service status:"
echo "     ${YELLOW}sudo systemctl status algotread${NC}"
echo ""
echo "  4. View logs:"
echo "     ${YELLOW}sudo journalctl -u algotread -f${NC}"
echo ""

# Ask if user wants to enable and start the service
read -p "Do you want to enable and start the service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Enabling service...${NC}"
    sudo systemctl enable algotread
    
    echo -e "${GREEN}Starting service...${NC}"
    sudo systemctl start algotread
    
    sleep 2
    
    echo ""
    echo -e "${GREEN}Service status:${NC}"
    sudo systemctl status algotread --no-pager
    
    echo ""
    echo -e "${GREEN}Recent logs:${NC}"
    sudo journalctl -u algotread -n 20 --no-pager
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo "For more information, see: docs/SYSTEMD_SERVICE.md"

# Clean up
rm "$SERVICE_FILE"
