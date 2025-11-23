# News Broadcasting to Telegram

## Overview

AlgoTread includes a command-line tool to fetch news and broadcast it to your Telegram channel with automatic deduplication to avoid repeating news.

## Quick Start

```bash
# Broadcast latest news
uv run -m scripts.broadcast_news

# Broadcast news for specific stocks
uv run -m scripts.broadcast_news --symbols RELIANCE,TCS,INFY

# Limit to 5 articles
uv run -m scripts.broadcast_news --max 5
```

## Features

- **Automatic Deduplication**: Tracks sent news URLs to avoid repeating
- **Symbol Filtering**: Filter news for specific stocks
- **Configurable Limits**: Control how many articles to send
- **Persistent History**: Maintains history across runs
- **Force Mode**: Override deduplication when needed
- **Statistics**: View broadcast statistics

## Configuration

Ensure your `.env` file has:

```bash
# News Configuration
NEWS_ENABLED=true
NEWS_SOURCES=economic_times,google_news,nse_announcements

# Telegram Configuration
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Command Options

### Basic Usage

```bash
# Broadcast latest news (default: 10 articles)
uv run -m scripts.broadcast_news
```

### Filter by Symbols

```bash
# Get news for specific stocks
uv run -m scripts.broadcast_news --symbols RELIANCE,TCS,INFY
```

### Limit Articles

```bash
# Send only 5 articles
uv run -m scripts.broadcast_news --max 5

# Send up to 20 articles
uv run -m scripts.broadcast_news --max 20
```

### Force Mode

```bash
# Send all articles, ignoring deduplication
uv run -m scripts.broadcast_news --force
```

### Statistics

```bash
# View broadcast statistics
uv run -m scripts.broadcast_news --stats
```

### Clear History

```bash
# Clear sent news history (use with caution)
uv run -m scripts.broadcast_news --clear-history
```

### Verbose Logging

```bash
# Enable detailed logging
uv run -m scripts.broadcast_news --verbose
```

## How It Works

### 1. Deduplication

The broadcaster maintains a file (`data/sent_news.json`) that tracks URLs of sent articles:

```json
{
  "sent_urls": [
    "https://economictimes.indiatimes.com/article1",
    "https://news.google.com/article2"
  ],
  "last_updated": "2024-01-15T10:30:00"
}
```

Only articles with new URLs are sent to Telegram.

### 2. Message Formatting

Each news article is formatted with:
- **Emoji** based on source (📰 Economic Times, 🌐 Google News, 📢 NSE)
- **Title** in bold
- **Summary** (limited to 200 characters)
- **Stock symbols** as hashtags (e.g., #RELIANCE)
- **Source link** and timestamp

Example message:
```
📰 **Reliance Industries announces Q3 results**

Strong quarterly results beat analyst estimates. Revenue up 15% YoY...

📊 #RELIANCE

🔗 Economic Times
🕐 2024-01-15 10:30
```

### 3. Rate Limiting

- 0.5 second delay between messages to avoid Telegram rate limits
- Respects news source rate limits via caching

## Automation

### Using Cron

Schedule regular news broadcasts:

```bash
# Edit crontab
crontab -e

# Broadcast news every hour during market hours (9 AM - 4 PM)
0 9-16 * * 1-5 cd /path/to/algotread && uv run -m scripts.broadcast_news --max 5

# Broadcast morning news at 9:15 AM
15 9 * * 1-5 cd /path/to/algotread && uv run -m scripts.broadcast_news --max 10

# Broadcast afternoon update at 2 PM
0 14 * * 1-5 cd /path/to/algotread && uv run -m scripts.broadcast_news --max 5
```

### Using Systemd Timer

Create a systemd timer for automated broadcasts:

```ini
# /etc/systemd/system/algotread-news.timer
[Unit]
Description=AlgoTread News Broadcast Timer

[Timer]
OnCalendar=Mon-Fri 09:15:00
OnCalendar=Mon-Fri 12:00:00
OnCalendar=Mon-Fri 15:00:00

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/algotread-news.service
[Unit]
Description=AlgoTread News Broadcast

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/path/to/algotread
Environment="PATH=/path/to/algotread/.venv/bin:/usr/bin:/bin"
ExecStart=/path/to/algotread/.venv/bin/python -m scripts.broadcast_news --max 10
```

Enable the timer:
```bash
sudo systemctl enable algotread-news.timer
sudo systemctl start algotread-news.timer
```

## Examples

### Morning Market Brief

```bash
# Send top 10 news articles at market open
uv run -m scripts.broadcast_news --max 10
```

### Stock-Specific Updates

```bash
# Monitor specific stocks throughout the day
uv run -m scripts.broadcast_news --symbols RELIANCE,TCS --max 3
```

### Force Resend

```bash
# Resend all recent news (useful for testing)
uv run -m scripts.broadcast_news --force --max 5
```

## Troubleshooting

### No Articles Sent

**Problem**: Command runs but no articles are sent

**Solutions**:
1. Check if news is enabled: `NEWS_ENABLED=true`
2. Verify Telegram is configured: `TELEGRAM_ENABLED=true`
3. Check if articles are new: `uv run -m scripts.broadcast_news --stats`
4. Use force mode to test: `uv run -m scripts.broadcast_news --force --max 1`

### Telegram Rate Limit

**Problem**: "Too Many Requests" error

**Solutions**:
1. Reduce `--max` value
2. Increase delay in `news_broadcaster.py`
3. Space out cron jobs more

### Duplicate Messages

**Problem**: Same news sent multiple times

**Solutions**:
1. Check if history file exists: `ls data/sent_news.json`
2. Verify file permissions
3. Don't use `--force` in automated scripts

### History File Issues

**Problem**: History file corrupted or missing

**Solutions**:
```bash
# Clear and rebuild history
uv run -m scripts.broadcast_news --clear-history

# Check stats
uv run -m scripts.broadcast_news --stats
```

## Best Practices

1. **Start Small**: Begin with `--max 5` to avoid flooding your channel
2. **Use Filters**: Filter by symbols for focused updates
3. **Schedule Wisely**: Don't broadcast too frequently (hourly is reasonable)
4. **Monitor Stats**: Regularly check `--stats` to ensure deduplication works
5. **Test First**: Use `--force --max 1` to test formatting
6. **Backup History**: Backup `data/sent_news.json` periodically

## Integration with Trading System

The news broadcaster can be integrated with your trading workflow:

```python
from src.notifications.news_broadcaster import NewsBroadcaster

# In your trading system
broadcaster = NewsBroadcaster(news_fetcher, telegram)

# Broadcast news for your watchlist
broadcaster.broadcast_news(
    symbols=config.watchlist,
    max_articles=5
)
```

## Message Format Customization

To customize message formatting, edit `src/notifications/news_broadcaster.py`:

```python
def _format_news_message(self, article: NewsArticle) -> str:
    # Customize emoji, format, length, etc.
    pass
```

## Security Considerations

- **Bot Token**: Keep your Telegram bot token secure
- **Chat ID**: Ensure chat ID is correct (channel or group)
- **History File**: Protect `data/sent_news.json` from unauthorized access
- **Rate Limits**: Respect Telegram's rate limits

## Support

For issues or questions:
- Check logs: `uv run -m scripts.broadcast_news --verbose`
- View stats: `uv run -m scripts.broadcast_news --stats`
- Test connection: `uv run -m scripts.broadcast_news --force --max 1`
