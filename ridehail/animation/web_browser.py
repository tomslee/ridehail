"""
Web browser-based animation for ridehail simulation.

This module starts a local HTTP server and opens a browser to view the simulation
using the Chart.js-based web interface from docs/lab/.

Architecture:
    CLI (run.py)
        ↓
    WebBrowserAnimation
        ├─ Start HTTP server (background thread)
        ├─ Convert config to web format (JSON)
        ├─ Open browser to localhost
        └─ Keep alive until user exits

Usage:
    python run.py config.config -a web_map     # Map visualization
    python run.py config.config -a web_stats   # Statistics charts
"""

import http.server
import socketserver
import threading
import webbrowser
import json
import socket
import os
import subprocess
import shutil
import logging
from pathlib import Path
from contextlib import closing

from ridehail.animation.base import RideHailAnimation
from ridehail.atom import Equilibration


class ReusableTCPServer(socketserver.TCPServer):
    """
    TCP Server that allows immediate port reuse.

    Sets SO_REUSEADDR socket option to allow binding to a port that is in
    TIME_WAIT state after a previous server instance closed. This prevents
    "Address already in use" errors when rapidly restarting the server.
    """

    allow_reuse_address = True


class WebBrowserAnimation(RideHailAnimation):
    """
    Base class for web browser animations.

    Starts a local HTTP server serving the docs/lab/ directory and opens
    the browser to view the simulation with Chart.js visualizations.

    Attributes:
        chart_type (str): "map" or "stats" - determines initial view
        port (int): HTTP server port (default 41967, with fallback if in use)
        server (TCPServer): HTTP server instance
        server_thread (Thread): Background thread running the server
        lab_dir (Path): Path to docs/lab/ directory
        config_file (Path): Path to generated config JSON file

    Class Attributes:
        DEFAULT_PORT (int): Default port for HTTP server (41967)
    """

    DEFAULT_PORT = 41967  # Fixed port for easier firewall/SSH forwarding

    def __init__(self, sim, chart_type="map"):
        """
        Initialize web browser animation.

        Args:
            sim: RideHailSimulation instance
            chart_type: "map" for vehicle map, "stats" for statistics charts
        """
        super().__init__(sim)
        self.chart_type = chart_type
        self.port = None
        self.server = None
        self.server_thread = None
        self.config_file = None

        # Find lab directory - supports both development and installed modes
        # Priority:
        #   1. Development mode: docs/lab/ (git repository)
        #   2. Installed mode: ridehail/lab/ (PyPI package)
        module_dir = Path(__file__).parent.parent.parent

        # Check for development mode first (full version with all tabs)
        dev_lab_dir = module_dir / "docs" / "lab"
        if dev_lab_dir.exists() and (dev_lab_dir / "index.html").exists():
            self.lab_dir = dev_lab_dir
            logging.info("Using development lab directory (full version)")
        else:
            # Fall back to installed package location (minimal CLI version)
            pkg_lab_dir = Path(__file__).parent.parent / "lab"
            if pkg_lab_dir.exists() and (pkg_lab_dir / "index.html").exists():
                self.lab_dir = pkg_lab_dir
                logging.info("Using installed package lab directory (minimal CLI version)")
            else:
                # Neither found - show helpful error
                import sys
                print("\n" + "=" * 70, file=sys.stderr)
                print(
                    "ERROR: Web animation requires web interface files.\n"
                    "       Neither development (docs/lab/) nor package (ridehail/lab/)\n"
                    "       directories found. This may indicate a corrupted installation.\n",
                    file=sys.stderr,
                )
                print("=" * 70, file=sys.stderr)
                print("\nTo fix:", file=sys.stderr)
                print("  1. Reinstall: pip install --force-reinstall ridehail[terminal]", file=sys.stderr)
                print("  2. Or use web interface: https://tomslee.github.io/ridehail/\n", file=sys.stderr)
                print("=" * 70 + "\n", file=sys.stderr)
                sys.exit(-1)

        # Check if ridehail wheel exists in dist/
        wheel_dir = self.lab_dir / "dist"
        if not wheel_dir.exists() or not list(wheel_dir.glob("ridehail-*.whl")):
            import sys
            print("\n" + "=" * 70, file=sys.stderr)
            print(
                "ERROR: Web animation requires ridehail wheel file.\n"
                f"       Expected at: {wheel_dir}/ridehail-*.whl\n"
                "       This may indicate a corrupted installation.\n",
                file=sys.stderr,
            )
            print("=" * 70, file=sys.stderr)
            print("\nTo fix:", file=sys.stderr)
            if self.lab_dir == dev_lab_dir:
                # Development mode - needs build
                print("  Run ./build.sh (Linux/Mac) or ./build.ps1 (Windows)", file=sys.stderr)
            else:
                # Installed mode - needs reinstall
                print("  1. Reinstall: pip install --force-reinstall ridehail[terminal]", file=sys.stderr)
                print("  2. Or use web interface: https://tomslee.github.io/ridehail/\n", file=sys.stderr)
            print("=" * 70 + "\n", file=sys.stderr)
            sys.exit(-1)

        logging.info(f"Web browser animation initialized (chart_type={chart_type}, lab_dir={self.lab_dir})")

    def _find_free_port(self):
        """
        Find an available port for the HTTP server.

        First attempts to use the default port (41967) for consistent firewall
        and SSH port forwarding configuration. If that port is already in use,
        falls back to an automatically selected free port.

        Returns:
            int: Available port number (41967 if available, otherwise random)
        """
        # Try the default port first
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                s.bind(("", self.DEFAULT_PORT))
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                logging.info(f"Using default port {self.DEFAULT_PORT}")
                return self.DEFAULT_PORT
        except OSError:
            # Default port is in use, find an available port
            logging.warning(
                f"Default port {self.DEFAULT_PORT} is in use, finding alternative port"
            )
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                s.bind(("", 0))
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                port = s.getsockname()[1]
                logging.info(f"Using alternative port {port}")
                return port

    def _prepare_config(self):
        """
        Convert simulation configuration to web format and write JSON file.

        Maps RideHailConfig (Python/CLI format) to the JavaScript format expected
        by docs/lab/app.js. This matches the parameter mapping in worker.py.

        Returns:
            Path: Path to the generated config JSON file

        Raises:
            IOError: If config directory cannot be created or file cannot be written
        """
        config = self.sim.config

        # Create config directory if it doesn't exist
        config_dir = self.lab_dir / "config"
        config_dir.mkdir(exist_ok=True)

        # Map configuration parameters to web format (camelCase JavaScript style)
        # This mapping matches worker.py desktopToWebConfig()
        web_config = {
            # City and simulation parameters
            "citySize": config.city_size.value,
            "vehicleCount": config.vehicle_count.value,
            "requestRate": config.base_demand.value,
            "maxTripDistance": config.max_trip_distance.value,
            "minTripDistance": config.min_trip_distance.value,
            "inhomogeneity": config.inhomogeneity.value,
            "inhomogeneousDestinations": config.inhomogeneous_destinations.value,
            "idleVehiclesMoving": config.idle_vehicles_moving.value,
            "randomNumberSeed": config.random_number_seed.value,
            "verbosity": config.verbosity.value,
            # Equilibration parameters
            "equilibrate": config.equilibration.value != Equilibration.NONE,  # Derived from equilibration for backward compatibility
            "equilibration": config.equilibration.value.name,  # Enum to string
            "equilibrationInterval": config.equilibration_interval.value,
            "demandElasticity": config.demand_elasticity.value,
            # Economic parameters
            "useCostsAndIncomes": config.use_city_scale.value,
            "price": config.price.value,
            "perKmPrice": config.per_km_price.value,
            "perMinutePrice": config.per_minute_price.value,
            "perKmOpsCost": config.per_km_ops_cost.value,
            "perHourOpportunityCost": config.per_hour_opportunity_cost.value,
            "platformCommission": config.platform_commission.value,
            "reservationWage": config.reservation_wage.value,
            # Time and speed parameters
            "timeBlocks": config.time_blocks.value,
            "meanVehicleSpeed": config.mean_vehicle_speed.value,
            "minutesPerBlock": config.minutes_per_block.value,
            "smoothingWindow": config.smoothing_window.value,
            # Animation parameters
            "animationDelay": config.animation_delay.value
            * 1000,  # Convert seconds to milliseconds
            # Pickup time configuration
            "pickupTime": config.pickup_time.value,
            # Web-specific: indicate this was loaded from CLI
            "cliMode": True,
        }

        # Write JSON config file
        config_file = config_dir / "cli_config.json"

        try:
            with open(config_file, "w") as f:
                json.dump(web_config, f, indent=2)
            logging.info(f"Configuration written to {config_file}")
        except IOError as e:
            logging.error(f"Failed to write config file: {e}")
            raise

        return config_file

    def _start_server(self):
        """
        Start HTTP server in background thread.

        Creates a simple HTTP server serving the docs/lab/ directory on a
        dynamically allocated port. The server runs in a daemon thread so it
        will be automatically terminated when the main program exits.

        The server uses http.server.SimpleHTTPRequestHandler which serves
        static files and automatically handles MIME types.
        """
        # Find available port
        self.port = self._find_free_port()

        # Change to lab directory so server serves it as root
        original_dir = os.getcwd()
        os.chdir(self.lab_dir)

        # Create request handler (will be instantiated for each request)
        handler = http.server.SimpleHTTPRequestHandler

        # Suppress SimpleHTTPRequestHandler logging unless in verbose mode
        if logging.getLogger().level > logging.INFO:
            handler.log_message = lambda *args, **kwargs: None

        try:
            # Create TCP server with socket reuse enabled
            # Using ReusableTCPServer which sets allow_reuse_address = True
            # This prevents "Address already in use" errors when restarting
            self.server = ReusableTCPServer(("", self.port), handler)

            # Start server in background daemon thread
            self.server_thread = threading.Thread(
                target=self.server.serve_forever, daemon=True
            )
            self.server_thread.start()

            logging.info(f"HTTP server started on http://localhost:{self.port}")

        except OSError as e:
            os.chdir(original_dir)
            logging.error(f"Failed to start HTTP server: {e}")
            raise

        # Note: We don't change back to original_dir here because the server
        # needs to stay in lab_dir to serve files correctly

    def _open_browser(self):
        """
        Open web browser to the simulation page in app mode.

        Constructs URL with query parameters to auto-load configuration and
        set the chart type. The browser will automatically load the config
        from /config/cli_config.json and start the simulation.

        URL format:
            http://localhost:PORT/?chartType=map&autoLoad=cli_config.json

        Attempts to open in app mode (without browser chrome) for a cleaner
        interface. Falls back to regular browser window if app mode fails.

        Supports Chrome/Chromium (--app flag) on all platforms.
        """
        url = (
            f"http://localhost:{self.port}/"
            f"?chartType={self.chart_type}"
            f"&autoLoad=cli_config.json"
        )

        try:
            # Try to open in app mode (Chrome/Chromium)
            # App mode removes address bar, bookmarks bar, and most browser UI

            # Try common Chrome/Chromium executables in priority order
            chrome_names = [
                "google-chrome",  # Linux
                "chromium-browser",  # Linux (Chromium)
                "chromium",  # Linux/macOS (Chromium)
                "chrome",  # macOS
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS full path
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",  # Windows 32-bit
            ]

            chrome_path = None
            for name in chrome_names:
                if shutil.which(name) or os.path.exists(name):
                    chrome_path = name
                    break

            if chrome_path:
                # Launch in app mode (minimal UI)
                # Suppress Chrome's stdout/stderr to avoid cluttering terminal
                subprocess.Popen(
                    [
                        chrome_path,
                        f"--app={url}",
                        "--window-size=1400,900",  # Default size
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logging.info(f"Browser opened in app mode to {url}")
            else:
                # Fallback to default browser (with full UI)
                webbrowser.open(url)
                logging.info(f"Browser opened to {url} (app mode not available)")

        except Exception as e:
            # Final fallback: try standard browser open
            try:
                webbrowser.open(url)
                logging.info(f"Browser opened to {url}")
            except Exception as e2:
                logging.error(f"Failed to open browser: {e2}")
                logging.info(f"Please open manually: {url}")

    def animate(self):
        """
        Run the web browser simulation.

        This is the main entry point called by the simulation framework.
        It performs the following steps:

        1. Prepare configuration file (convert and write JSON)
        2. Start HTTP server (background thread)
        3. Open browser to simulation page
        4. Display user instructions
        5. Keep alive until user exits (Ctrl+C)

        The simulation runs entirely in the browser. The CLI stays alive to:
        - Keep the HTTP server running
        - Provide a clear exit point for the user
        - Clean up resources on exit

        Note: The actual simulation execution happens in the browser via
        Pyodide. This Python process just serves the static files.

        Returns:
            None: The web animation doesn't return simulation results as the
                  simulation runs in the browser. Results can be downloaded
                  from the web interface if needed.
        """
        try:
            # Step 1: Prepare configuration
            print("\nRidehail Web Browser Animation")
            print("=" * 50)
            print(
                f"Loading configuration: {self.sim.config.config_file.value or 'default'}"
            )
            print(f"Visualization type: {self.chart_type}")
            print()

            self.config_file = self._prepare_config()

            # Step 2: Start HTTP server
            print("Starting local web server...")
            self._start_server()
            print(f"  Server: http://localhost:{self.port}")
            print(f"  Lab directory: {self.lab_dir}")
            print()

            # Step 3: Open browser
            print("Opening browser...")
            self._open_browser()
            print()

            # Step 4: Display instructions
            print("=" * 50)
            print("Simulation running in browser")
            print("=" * 50)
            print()
            print(f"View at: http://localhost:{self.port}")
            print()

            # Add SSH port forwarding instructions if using default port
            print("For SSH access, use port forwarding:")
            print(f"  ssh -L {self.port}:localhost:{self.port} user@host")
            print()

            print("The simulation is running in your web browser.")
            print("Use the browser controls to interact with the simulation.")
            print()
            print("Press Ctrl+C to stop the server and exit...")
            print()

            # Step 5: Keep alive
            # Wait for KeyboardInterrupt (Ctrl+C)
            # The server runs in a background thread, so we just need to block here
            try:
                while True:
                    # Sleep to avoid busy-waiting
                    threading.Event().wait(1)
            except KeyboardInterrupt:
                print("\n\nShutting down...")

        except Exception as e:
            logging.error(f"Error in web browser animation: {e}")
            raise
        finally:
            # Always clean up, even if there was an error
            self.cleanup()

        # Return None as simulation runs in browser
        return None

    def cleanup(self):
        """
        Cleanup resources: shutdown server and remove temporary files.

        Called automatically on exit (normal or via Ctrl+C). Ensures:
        - HTTP server is properly shut down
        - Temporary config file is removed
        - Process exits cleanly

        This method is safe to call multiple times.
        """
        # Shutdown HTTP server
        if self.server:
            try:
                logging.info("Shutting down HTTP server...")
                self.server.shutdown()
                self.server.server_close()
                logging.info("Server stopped")
            except Exception as e:
                logging.error(f"Error shutting down server: {e}")

        # Remove temporary config file
        if self.config_file and self.config_file.exists():
            try:
                self.config_file.unlink()
                logging.info(f"Removed temporary config file: {self.config_file}")
            except Exception as e:
                logging.error(f"Error removing config file: {e}")

        print("Cleanup complete.")


class WebMapAnimation(WebBrowserAnimation):
    """
    Web browser animation with map visualization.

    Shows the city map with vehicles moving between intersections,
    trip markers (origins and destinations), and real-time statistics.

    Usage:
        python run.py config.config -a web_map
    """

    def __init__(self, sim):
        super().__init__(sim, chart_type="map")
        logging.info("Web map animation initialized")


class WebStatsAnimation(WebBrowserAnimation):
    """
    Web browser animation with statistics charts.

    Shows time-series charts of vehicle phases, trip metrics, and other
    simulation statistics using Chart.js line charts.

    Usage:
        python run.py config.config -a web_stats
    """

    def __init__(self, sim):
        super().__init__(sim, chart_type="stats")
        logging.info("Web stats animation initialized")
