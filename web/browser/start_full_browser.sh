#!/bin/bash
# Start the full browser stack as in setup.sh: Xvfb, Chromium (Playwright),
# screenshot server, x11vnc, noVNC, and screenshot capture loop.
# Uses existing browser-remote install. Requires local Xvfb/x11vnc (PATH and
# LD_LIBRARY_PATH set below) and conda browser-env.

set -e
INSTALL_DIR="${INSTALL_DIR:-$HOME/browser-remote}"
MINICONDA_DIR="${MINICONDA_DIR:-$HOME/miniconda3}"
ENV_NAME="browser-env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Local builds (no sudo) - same as start_vnc_stack.sh
export PATH="/homes/gws/reshabh/rpm/xvfb/usr/bin:/homes/gws/reshabh/local/x11vnc/bin:$PATH"
export LD_LIBRARY_PATH="/homes/gws/reshabh/local/openssl/install/lib:/homes/gws/reshabh/local/libvncserver/lib64:${LD_LIBRARY_PATH:-}"

echo "Starting full browser stack (real browser like setup.sh)..."

# 1) Free ports: kill existing processes on 9222, 8080, 5900, 6080
for port in 9222 8080 5900 6080; do
  pid=$(lsof -ti :$port 2>/dev/null) || true
  if [ -n "$pid" ]; then
    echo "Stopping process on port $port (PID $pid)"
    kill $pid 2>/dev/null || true
    sleep 1
  fi
done
sleep 2

# 2) Xvfb on :99
if ! pgrep -f "Xvfb :99" >/dev/null 2>&1; then
  echo "Starting Xvfb on :99..."
  Xvfb :99 -screen 0 1024x768x24 &
  XVFB_PID=$!
  sleep 3
  if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "Error: Xvfb failed to start"
    exit 1
  fi
  echo "Xvfb started."
else
  echo "Xvfb :99 already running."
fi

export DISPLAY=:99
touch "$INSTALL_DIR/.Xauthority"
export XAUTHORITY="$INSTALL_DIR/.Xauthority"
xauth -f "$XAUTHORITY" generate :99 . trusted 2>/dev/null || true

# 3) Conda browser-env for node/playwright and python
if [ ! -f "$MINICONDA_DIR/etc/profile.d/conda.sh" ]; then
  echo "Error: Miniconda not found at $MINICONDA_DIR. Run setup.sh first."
  exit 1
fi
source "$MINICONDA_DIR/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

# 4) Launch browser (Playwright Chromium) on display :99
if [ ! -f "$INSTALL_DIR/playwright-project/browser_launcher.js" ]; then
  echo "Error: playwright-project not found. Run setup.sh first."
  exit 1
fi
echo "Launching browser (Playwright Chromium)..."
cd "$INSTALL_DIR/playwright-project"
export PLAYWRIGHT_BROWSERS_PATH="$INSTALL_DIR/playwright-browsers"
node browser_launcher.js &
BROWSER_PID=$!
cd - >/dev/null

sleep 5
if ! kill -0 $BROWSER_PID 2>/dev/null; then
  echo "Error: Browser failed to start"
  exit 1
fi
echo "Browser started (PID $BROWSER_PID)."

# 5) Flask screenshot server on 8080
echo "Starting screenshot server on 8080..."
cd "$INSTALL_DIR"
python3 screenshot_server.py --host 0.0.0.0 --port 8080 --screenshot-path "$INSTALL_DIR/screenshots/latest-preview.png" &
HTTP_PID=$!
cd - >/dev/null
sleep 2
echo "Screenshot server started (PID $HTTP_PID)."

# 6) x11vnc on 5900
echo "Starting x11vnc on 5900..."
nohup x11vnc -display :99 -nopw -forever -shared -auth "$INSTALL_DIR/.Xauthority" >> "$INSTALL_DIR/x11vnc.log" 2>&1 &
VNC_PID=$!
sleep 2
if ! kill -0 $VNC_PID 2>/dev/null; then
  echo "Error: x11vnc failed. Check $INSTALL_DIR/x11vnc.log"
  tail -20 "$INSTALL_DIR/x11vnc.log"
  exit 1
fi
echo "x11vnc started (PID $VNC_PID)."

# 7) noVNC proxy on 6080 (listen on all interfaces)
echo "Starting noVNC proxy on 6080..."
cd "$INSTALL_DIR/noVNC"
nohup ./utils/novnc_proxy --vnc localhost:5900 --listen 0.0.0.0:6080 >> "$INSTALL_DIR/novnc.log" 2>&1 &
NOVNC_PID=$!
cd - >/dev/null
sleep 2
if ! kill -0 $NOVNC_PID 2>/dev/null; then
  echo "Error: noVNC proxy failed. Check $INSTALL_DIR/novnc.log"
  exit 1
fi
echo "noVNC started (PID $NOVNC_PID)."

# 8) Screenshot capture loop (updates latest-preview.png every second)
echo "Starting screenshot capture loop..."
(
  while kill -0 $BROWSER_PID 2>/dev/null; do
    cd "$INSTALL_DIR/playwright-project"
    node screenshot.js "$INSTALL_DIR/screenshots/latest-preview.png" 2>&1 | tee -a "$INSTALL_DIR/screenshots/screenshot.log"
    sleep 1
  done
) &
SCREENSHOT_PID=$!
echo "Screenshot capture started (PID $SCREENSHOT_PID)."

echo ""
echo "Full browser stack is running."
echo "  Browser DevTools: http://localhost:9222"
echo "  noVNC (browser):  http://$(hostname -f 2>/dev/null || echo localhost):6080/vnc_lite.html"
echo "  Screenshot API:   http://localhost:8080"
echo ""
echo "PIDs: browser=$BROWSER_PID screenshot_server=$HTTP_PID x11vnc=$VNC_PID noVNC=$NOVNC_PID capture=$SCREENSHOT_PID"
