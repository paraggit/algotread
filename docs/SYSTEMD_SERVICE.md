# AlgoTread Systemd Service Deployment Guide

This guide explains how to set up and manage AlgoTread as a Linux systemd service.

## Prerequisites

- Linux system with systemd (Ubuntu 16.04+, Debian 8+, CentOS 7+, etc.)
- AlgoTread installed and configured
- Python environment set up with uv
- `.env` file configured with all required credentials

## Installation Steps

### 1. Configure the Service File

Edit `deployment/algotread.service` and update the following placeholders:

```bash
# Replace these values:
User=YOUR_USERNAME              # Your Linux username (e.g., trader)
Group=YOUR_GROUP                # Your Linux group (e.g., trader)
WorkingDirectory=/path/to/algotread              # Full path to algotread directory
Environment="PATH=/path/to/algotread/.venv/bin:..." # Full path to virtual environment
EnvironmentFile=/path/to/algotread/.env          # Full path to .env file
ExecStart=/path/to/algotread/.venv/bin/python -m src.main  # Full path to Python
ReadWritePaths=/path/to/algotread/data /path/to/algotread/logs  # Full paths
```

**Example configuration:**
```bash
User=trader
Group=trader
WorkingDirectory=/home/trader/algotread
Environment="PATH=/home/trader/algotread/.venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/trader/algotread/.env
ExecStart=/home/trader/algotread/.venv/bin/python -m src.main
ReadWritePaths=/home/trader/algotread/data /home/trader/algotread/logs
```

### 2. Copy Service File to Systemd

```bash
# Copy the service file to systemd directory
sudo cp deployment/algotread.service /etc/systemd/system/

# Set proper permissions
sudo chmod 644 /etc/systemd/system/algotread.service

# Reload systemd to recognize the new service
sudo systemctl daemon-reload
```

### 3. Enable and Start the Service

```bash
# Enable service to start on boot
sudo systemctl enable algotread

# Start the service
sudo systemctl start algotread

# Check status
sudo systemctl status algotread
```

## Service Management Commands

### Basic Operations

```bash
# Start the service
sudo systemctl start algotread

# Stop the service
sudo systemctl stop algotread

# Restart the service
sudo systemctl restart algotread

# Reload configuration (if service supports it)
sudo systemctl reload algotread

# Check service status
sudo systemctl status algotread

# Enable service (start on boot)
sudo systemctl enable algotread

# Disable service (don't start on boot)
sudo systemctl disable algotread
```

### Monitoring and Logs

```bash
# View real-time logs
sudo journalctl -u algotread -f

# View logs from today
sudo journalctl -u algotread --since today

# View last 100 lines
sudo journalctl -u algotread -n 100

# View logs with timestamps
sudo journalctl -u algotread -o short-precise

# View logs between specific times
sudo journalctl -u algotread --since "2024-01-01 09:00:00" --until "2024-01-01 15:30:00"

# Export logs to file
sudo journalctl -u algotread > algotread.log
```

### Troubleshooting

```bash
# Check if service is enabled
sudo systemctl is-enabled algotread

# Check if service is active
sudo systemctl is-active algotread

# View service configuration
sudo systemctl cat algotread

# Check for errors
sudo systemctl status algotread -l

# View failed services
sudo systemctl --failed
```

## Service Features

### Automatic Restart

The service is configured to automatically restart on failure:
- **Restart Policy**: `on-failure`
- **Restart Delay**: 10 seconds
- **Max Restarts**: 5 attempts within 200 seconds

### Security Hardening

The service includes several security features:
- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated /tmp directory
- `ProtectSystem=strict` - Read-only system directories
- `ProtectHome=read-only` - Read-only home directories
- `ReadWritePaths` - Only specified directories are writable

### Resource Limits

- **Memory Limit**: 2GB (adjust based on your needs)
- **CPU Quota**: 200% (2 CPU cores)

### Graceful Shutdown

- **Timeout**: 30 seconds for graceful shutdown
- **Kill Mode**: Mixed (SIGTERM first, then SIGKILL)

## Configuration Tips

### 1. Adjust Resource Limits

Edit the service file to change resource limits:

```bash
# Edit service file
sudo nano /etc/systemd/system/algotread.service

# Modify these lines:
MemoryLimit=4G        # Increase memory limit
CPUQuota=400%         # Use 4 CPU cores

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart algotread
```

### 2. Change Restart Policy

```bash
# For production (always restart):
Restart=always

# For development (restart only on failure):
Restart=on-failure

# Never restart:
Restart=no
```

### 3. Environment Variables

You can add additional environment variables:

```bash
Environment="LOG_LEVEL=DEBUG"
Environment="TRADING_MODE=paper"
```

Or use the EnvironmentFile for all variables (recommended):

```bash
EnvironmentFile=/path/to/algotread/.env
```

## Trading Hours Configuration

### Option 1: Using Systemd Timers

Create a timer to start/stop trading during market hours:

```bash
# Create timer file: /etc/systemd/system/algotread.timer
[Unit]
Description=AlgoTread Trading Hours Timer

[Timer]
OnCalendar=Mon-Fri 09:15:00
OnCalendar=Mon-Fri 15:30:00

[Install]
WantedBy=timers.target
```

### Option 2: Using Cron

```bash
# Edit crontab
crontab -e

# Start at 9:15 AM on weekdays
15 9 * * 1-5 sudo systemctl start algotread

# Stop at 3:30 PM on weekdays
30 15 * * 1-5 sudo systemctl stop algotread
```

### Option 3: Built-in Time Filters

AlgoTread has built-in time filters, so you can keep the service running 24/7 and it will only trade during configured hours.

## Monitoring and Alerts

### 1. Service Status Monitoring

Create a monitoring script:

```bash
#!/bin/bash
# /usr/local/bin/check-algotread.sh

if ! systemctl is-active --quiet algotread; then
    echo "AlgoTread service is down!" | mail -s "AlgoTread Alert" your@email.com
    sudo systemctl start algotread
fi
```

Add to crontab:
```bash
*/5 * * * * /usr/local/bin/check-algotread.sh
```

### 2. Log Rotation

Create logrotate configuration:

```bash
# /etc/logrotate.d/algotread
/home/trader/algotread/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0640 trader trader
}
```

## Backup and Recovery

### Backup Configuration

```bash
# Backup service file
sudo cp /etc/systemd/system/algotread.service ~/algotread-service.backup

# Backup .env file
cp /path/to/algotread/.env ~/algotread-env.backup

# Backup data directory
tar -czf ~/algotread-data-$(date +%Y%m%d).tar.gz /path/to/algotread/data
```

### Recovery

```bash
# Restore service file
sudo cp ~/algotread-service.backup /etc/systemd/system/algotread.service
sudo systemctl daemon-reload

# Restore .env
cp ~/algotread-env.backup /path/to/algotread/.env

# Restore data
tar -xzf ~/algotread-data-YYYYMMDD.tar.gz -C /
```

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop algotread
sudo systemctl disable algotread

# Remove service file
sudo rm /etc/systemd/system/algotread.service

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

## Common Issues

### Issue: Service fails to start

**Check logs:**
```bash
sudo journalctl -u algotread -n 50
```

**Common causes:**
- Incorrect paths in service file
- Missing .env file
- Python environment not activated
- Permission issues

### Issue: Service starts but crashes

**Check:**
- API credentials in .env
- Network connectivity
- Python dependencies installed
- Sufficient disk space

### Issue: High memory usage

**Solutions:**
- Increase MemoryLimit in service file
- Optimize cache settings in .env
- Reduce number of symbols in watchlist

## Best Practices

1. **Always test in paper trading mode first**
2. **Monitor logs regularly during initial deployment**
3. **Set up alerts for service failures**
4. **Keep backups of configuration files**
5. **Use log rotation to manage disk space**
6. **Review and adjust resource limits based on actual usage**
7. **Keep the service file in version control**
8. **Document any custom modifications**

## Security Considerations

1. **Protect .env file:**
   ```bash
   chmod 600 /path/to/algotread/.env
   ```

2. **Run as non-root user** (already configured in service file)

3. **Restrict network access** if needed using firewall rules

4. **Enable audit logging:**
   ```bash
   sudo systemctl edit algotread
   # Add: AuditWrite=yes
   ```

5. **Regular security updates:**
   ```bash
   uv pip install --upgrade -r requirements.txt
   ```

## Support

For issues or questions:
- Check logs: `sudo journalctl -u algotread -f`
- Review service status: `sudo systemctl status algotread -l`
- Consult main documentation: `README.md`
