#!/bin/bash
# Start only the VNC + noVNC stack (no browser). Use this when you already have
# browser-remote/noVNC set up and just need something on port 6080 so the
# frontend noVNC iframe can connect.
# Requires: Xvfb, x11vnc, noVNC - with libs in ~/local (openssl, libvncserver).

set -e
INSTALL_DIR="${INSTALL_DIR:-$HOME/browser-remote}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Paths for local builds (no sudo)
export PATH="/homes/gws/reshabh/rpm/xvfb/usr/bin:/homes/gws/reshabh/local/x11vnc/bin:$PATH"
export LD_LIBRARY_PATH="/homes/gws/reshabh/local/openssl/install/lib:/homes/gws/reshabh/local/libvncserver/lib64:${LD_LIBRARY_PATH:-}"

mkdir -p "$INSTALL_DIR/screenshots"
cd "$INSTALL_DIR"

# 1) Xvfb on :99
if ! pgrep -f "Xvfb :99" >/dev/null 2>&1; then
  echo "Starting Xvfb on :99..."
  Xvfb :99 -screen 0 1024x768x24 &
  sleep 3
  if ! pgrep -f "Xvfb :99" >/dev/null 2>&1; then
    echo "Error: Xvfb failed to start (check LD_LIBRARY_PATH for libcrypto)"
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

# 2) x11vnc on 5900
if lsof -i :5900 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Port 5900 already in use (x11vnc?)."
else
  echo "Starting x11vnc on 5900..."
  nohup x11vnc -display :99 -nopw -forever -shared -auth "$INSTALL_DIR/.Xauthority" >> "$INSTALL_DIR/x11vnc.log" 2>&1 &
  sleep 2
  if lsof -i :5900 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "x11vnc started on 5900."
  else
    echo "Error: x11vnc failed. Check $INSTALL_DIR/x11vnc.log"
    tail -15 "$INSTALL_DIR/x11vnc.log"
    exit 1
  fi
fi

# 3) noVNC proxy on 6080 (listen on all interfaces for remote access)
if lsof -i :6080 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Port 6080 already in use (noVNC?)."
else
  echo "Starting noVNC proxy on 6080..."
  cd "$INSTALL_DIR/noVNC"
  nohup ./utils/novnc_proxy --vnc localhost:5900 --listen 0.0.0.0:6080 >> "$INSTALL_DIR/novnc.log" 2>&1 &
  sleep 2
  cd - >/dev/null
  if lsof -i :6080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "noVNC proxy started on 6080."
  else
    echo "Error: noVNC proxy failed. Check $INSTALL_DIR/novnc.log"
    tail -15 "$INSTALL_DIR/novnc.log"
    exit 1
  fi
fi

echo ""
echo "VNC stack is running:"
echo "  VNC server:    localhost:5900"
echo "  noVNC (web):   http://$(hostname -f 2>/dev/null || echo localhost):6080/vnc_lite.html"
echo "  (Use the same host as your frontend, e.g. http://<this-host>:6080/...)"
