#!/bin/bash
# Quick fix for Telegram chat ID

echo "Updating TELEGRAM_CHAT_ID in .env file..."

# Backup .env
cp .env .env.backup

# Update the chat ID
sed -i.tmp 's/^TELEGRAM_CHAT_ID=nsetread/TELEGRAM_CHAT_ID=-1003380851320/' .env

# Remove temp file
rm -f .env.tmp

echo "✅ Updated TELEGRAM_CHAT_ID to -1003380851320"
echo ""
echo "Verification:"
grep "TELEGRAM_CHAT_ID" .env | head -1
echo ""
echo "Backup saved to .env.backup"
