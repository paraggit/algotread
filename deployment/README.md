# AlgoTread Deployment Files

This directory contains files for deploying AlgoTread as a Linux systemd service.

## Files

- **`algotread.service`** - Systemd service unit file
- **`install-service.sh`** - Automated installation script

## Quick Start

### Automated Installation (Recommended)

```bash
# Run the installation script
cd /path/to/algotread
./deployment/install-service.sh
```

The script will:
1. Check prerequisites
2. Create a configured service file
3. Install it to `/etc/systemd/system/`
4. Optionally enable and start the service

### Manual Installation

1. Edit `algotread.service` and update paths:
   ```bash
   nano deployment/algotread.service
   ```

2. Copy to systemd directory:
   ```bash
   sudo cp deployment/algotread.service /etc/systemd/system/
   sudo chmod 644 /etc/systemd/system/algotread.service
   sudo systemctl daemon-reload
   ```

3. Enable and start:
   ```bash
   sudo systemctl enable algotread
   sudo systemctl start algotread
   ```

## Management Commands

```bash
# Start service
sudo systemctl start algotread

# Stop service
sudo systemctl stop algotread

# Restart service
sudo systemctl restart algotread

# Check status
sudo systemctl status algotread

# View logs
sudo journalctl -u algotread -f
```

## Documentation

See [SYSTEMD_SERVICE.md](../docs/SYSTEMD_SERVICE.md) for complete documentation including:
- Detailed installation instructions
- Service management
- Monitoring and logging
- Troubleshooting
- Security considerations
- Best practices

## Requirements

- Linux system with systemd
- AlgoTread installed and configured
- `.env` file with all credentials
- Python virtual environment set up

## Notes

- The service runs as your user (not root) for security
- Logs are sent to systemd journal
- Service auto-restarts on failure
- Resource limits are configured (2GB RAM, 2 CPU cores)
- Security hardening is enabled

## Support

For issues or questions, see the main documentation or check the logs:
```bash
sudo journalctl -u algotread -n 100
```
