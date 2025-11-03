# Web Animation Setup Guide

## Overview

The web animation feature (`-as web_map` and `-as web_stats`) starts a local HTTP server on **port 41967** and displays the simulation in your web browser using the Chart.js-based interface.

## Default Port

**Fixed Port**: `41967`

This port was chosen to allow consistent firewall and SSH port forwarding configuration. If port 41967 is already in use, the system will automatically fall back to a random available port.

## Setup Instructions

### For Local Use (Direct Display)

If running on a machine with a display, simply run:

```bash
python -m ridehail config.config -as web_map   # For map visualization
python -m ridehail config.config -as web_stats # For statistics charts
```

The browser will open automatically to `http://localhost:41967`.

### For Remote Use via SSH

If running on a remote server via SSH, you need to configure:

#### 1. Firewall Configuration (Optional - for external access)

If you want to access the web interface from outside the server:

```bash
# Ubuntu/Debian with ufw
sudo ufw allow 41967/tcp

# Or with iptables
sudo iptables -A INPUT -p tcp --dport 41967 -j ACCEPT
```

**Security Note**: Only open the firewall if you need external access. SSH port forwarding (below) is more secure for personal use.

#### 2. SSH Port Forwarding (Recommended)

Forward the remote port to your local machine:

```bash
# From your local machine:
ssh -L 41967:localhost:41967 user@remote-host

# Then run the simulation on remote server:
python -m ridehail config.config -as web_map

# Open in your local browser:
http://localhost:41967
```

The URL with auto-load parameters will be shown in the terminal output:
```
http://localhost:41967/?chartType=map&autoLoad=cli_config.json
```

#### 3. Persistent SSH Tunnel (Alternative)

To keep the tunnel open in the background:

```bash
# Create persistent tunnel
ssh -fNL 41967:localhost:41967 user@remote-host

# Check if tunnel is running
ps aux | grep "ssh.*41967"

# Close tunnel when done
pkill -f "ssh.*41967"
```

## Usage

### Basic Commands

```bash
# Map visualization
python -m ridehail test.config -as web_map

# Statistics charts
python -m ridehail metro.config -as web_stats
```

### Example Session Output

```
Ridehail Web Browser Animation
==================================================
Loading configuration: test.config
Visualization type: map

Starting local web server...
  Server: http://localhost:41967
  Lab directory: /home/user/ridehail-simulation/docs/lab

Opening browser...

==================================================
Simulation running in browser
==================================================

View at: http://localhost:41967

For SSH access, use port forwarding:
  ssh -L 41967:localhost:41967 user@host

The simulation is running in your web browser.
Use the browser controls to interact with the simulation.

Press Ctrl+C to stop the server and exit...
```

## Troubleshooting

### Port Already in Use

If port 41967 is already in use, the system will automatically select an alternative port and display it in the output:

```
[web_browser.py:105] WARNING - Default port 41967 is in use, finding alternative port
[web_browser.py:112] INFO - Using alternative port 54321

View at: http://localhost:54321
```

Update your SSH port forwarding to use the alternative port:
```bash
ssh -L 54321:localhost:54321 user@remote-host
```

### Browser Doesn't Open on SSH

This is expected behavior. The browser launch will fail silently when no display is available. Simply:

1. Note the URL shown in the terminal output
2. Access it through SSH port forwarding (see above)
3. Open the URL in your local browser

### Firewall Blocking Connections

If using external access and connections are blocked:

```bash
# Check firewall status
sudo ufw status

# Verify port is open
sudo netstat -tuln | grep 41967
# or
sudo ss -tuln | grep 41967

# Check if server is running
curl http://localhost:41967
```

## Technical Details

### Architecture

```
CLI (ridehail) → WebBrowserAnimation → HTTP Server (port 41967)
                                           ↓
                                      Browser ← User
```

### Configuration Auto-Load

The web interface automatically:
1. Loads configuration from `/config/cli_config.json`
2. Sets the chart type (map or stats)
3. Starts the simulation
4. Displays real-time results

### Security Considerations

- **Local only**: Server binds to `localhost` (127.0.0.1) by default
- **No authentication**: Anyone with access to the port can view the simulation
- **Temporary files**: Config files are created in `docs/lab/config/` and cleaned up on exit
- **SSH forwarding**: More secure than opening firewall for personal use

## Phase 2: Browser Auto-Load ✅ **COMPLETE**

**Status**: Implemented and ready for testing

When you access `http://localhost:41967/?chartType=map&autoLoad=cli_config.json`, the browser now:
- ✅ Parses URL parameters to detect CLI mode
- ✅ Loads configuration file from server automatically
- ✅ Infers scale and applies settings to UI
- ✅ Sets chart type (map or stats) based on URL parameter
- ✅ Displays "[CLI Mode]" indicator in the title bar (green)
- ✅ Auto-starts the simulation after 500ms delay
- ✅ Shows success notification when config loads

### What Happens Automatically

1. **URL is parsed**: `?chartType=map&autoLoad=cli_config.json`
2. **Config is fetched**: `./config/cli_config.json` loaded from server
3. **Settings applied**: All simulation parameters updated
4. **UI updated**: Sliders, checkboxes, radio buttons reflect loaded config
5. **Scale inferred**: Automatically detects village/town/city scale
6. **Simulation starts**: FAB button clicked automatically
7. **Visual feedback**: Green "[CLI Mode]" text in title bar

## See Also

- [Web Animation Integration Design Document](web-animation-integration.md) - Complete technical specification
- [Main README](../README.md) - Project overview and installation
- [CLAUDE.md](../CLAUDE.md) - Project guidance for development
