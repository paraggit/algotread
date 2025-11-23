#!/bin/bash
# Install AlgoTread News Broadcasting Timer

set -e

echo "Installing AlgoTread News Broadcasting Timer..."

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Get current user
CURRENT_USER=$(whoami)
PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"

echo "Configuration:"
echo "  User: $CURRENT_USER"
echo "  Project: $PROJECT_DIR"
echo "  Python: $PYTHON_PATH"

# Create service file
SERVICE_FILE="/tmp/algotread-news.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=AlgoTread News Broadcast Service
After=network.target

[Service]
Type=oneshot
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PYTHON_PATH -m scripts.broadcast_news --max 10

StandardOutput=journal
StandardError=journal
SyslogIdentifier=algotread-news
EOF

# Create timer file
TIMER_FILE="/tmp/algotread-news.timer"
cat > "$TIMER_FILE" << EOF
[Unit]
Description=AlgoTread News Broadcast Timer
Requires=algotread-news.service

[Timer]
# Run every hour during market hours (9 AM - 4 PM, Mon-Fri)
OnCalendar=Mon-Fri *-*-* 09..16:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Install files
echo "Installing systemd files..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/
sudo cp "$TIMER_FILE" /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/algotread-news.service
sudo chmod 644 /etc/systemd/system/algotread-news.timer

# Reload systemd
sudo systemctl daemon-reload

echo "✅ Installation complete!"
echo ""
echo "To enable and start the timer:"
echo "  sudo systemctl enable algotread-news.timer"
echo "  sudo systemctl start algotread-news.timer"
echo ""
echo "To check timer status:"
echo "  sudo systemctl status algotread-news.timer"
echo "  systemctl list-timers algotread-news.timer"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u algotread-news -f"
echo ""

# Ask if user wants to enable
read -p "Enable and start the timer now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl enable algotread-news.timer
    sudo systemctl start algotread-news.timer
    echo ""
    echo "Timer status:"
    systemctl list-timers algotread-news.timer
fi

# Cleanup
rm "$SERVICE_FILE" "$TIMER_FILE"
