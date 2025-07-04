#!/bin/bash

# AC4A Services Startup Script
# This script starts all required services for the AC4A application

set -e  # Exit on any error
set -x  # Print commands

# Configuration
REDIS_PORT=6379
BACKEND_PORT=5002
FRONTEND_PORT=5173
SCREENSHOT_PORT=8080
BROWSER_DEBUG_PORT=9222
VNC_PORT=6080
NOVNC_PORT=6081
GAME_DEMO_PORT=5000

# Logging configuration (will be set after LOG_DIR is created)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to log messages to file and optionally display errors
log_message() {
    local log_file="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" >> "$log_file"
}

# Function to start a service with logging
start_service_with_logging() {
    local service_name="$1"
    local log_file="$2"
    local command="$3"
    
    # Print status to stderr so it doesn't interfere with return value
    print_status "Starting $service_name (logs: $log_file)" >&2
    
    # Ensure log file exists and is writable
    touch "$log_file"
    chmod 644 "$log_file"
    
    # Add startup message to log
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting $service_name" >> "$log_file"
    
    # Start the service with proper logging using nohup
    nohup bash -c "$command" >> "$log_file" 2>&1 &
    local pid=$!
    
    # Add PID to log
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $service_name started with PID: $pid" >> "$log_file"
    
    # Return only the PID
    echo "$pid"
}

# Function to check for errors in log files
check_log_errors() {
    local log_file="$1"
    local service_name="$2"
    
    if [ -f "$log_file" ]; then
        # Check for common error patterns
        if grep -i "error\|exception\|traceback\|failed\|fatal" "$log_file" >/dev/null 2>&1; then
            print_error "Errors detected in $service_name logs:"
            grep -i "error\|exception\|traceback\|failed\|fatal" "$log_file" | tail -5 | while read line; do
                echo -e "  ${RED}$line${NC}"
            done
        fi
    fi
}

# Function to check if a port is in use
check_port() {
    local port=$1
    # Try multiple methods to check port availability
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    elif ss -tlnp | grep ":$port " >/dev/null 2>&1; then
        return 0  # Port is in use
    elif netstat -tlnp 2>/dev/null | grep ":$port " >/dev/null; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill processes using a specific port
kill_port_processes() {
    local port=$1
    local service_name=$2
    
    print_status "Killing processes using port $port for $service_name..."
    
    # Try to find and kill processes using the port
    local pids=$(lsof -ti :$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        print_status "Found processes using port $port: $pids"
        echo $pids | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    # Also try to kill common process patterns
    case $service_name in
        *"frontend"*|*"vite"*)
            pkill -f "vite" 2>/dev/null || true
            pkill -f "npm.*run.*dev" 2>/dev/null || true
            ;;
        *"backend"*|*"python"*)
            pkill -f "python.*app.py" 2>/dev/null || true
            ;;
        *"redis"*)
            # Don't kill system Redis service
            ;;
    esac
    
    sleep 2
}

# Function to wait for a service to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready on $host:$port..."
    
    while [ $attempt -le $max_attempts ]; do
        if check_port $port; then
            print_success "$service_name is ready on port $port"
            return 0
        fi
        
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start on port $port after $max_attempts attempts"
    return 1
}

# Function to cleanup processes on exit
cleanup() {
    print_status "Cleaning up processes..."
    
    # Kill Redis
    if [ "$REDIS_SYSTEM_SERVICE" = "true" ]; then
        print_status "Redis is running as system service - not stopping it"
    elif [ ! -z "$REDIS_PID" ]; then
        print_status "Stopping Redis server (PID: $REDIS_PID)"
        kill $REDIS_PID 2>/dev/null || true
    fi
    
    # Kill backend server
    if [ ! -z "$BACKEND_PID" ]; then
        print_status "Stopping backend server (PID: $BACKEND_PID)"
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    # Kill frontend server
    if [ ! -z "$FRONTEND_PID" ]; then
        print_status "Stopping frontend server (PID: $FRONTEND_PID)"
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Kill screenshot server
    if [ ! -z "$SCREENSHOT_PID" ]; then
        print_status "Stopping screenshot server (PID: $SCREENSHOT_PID)"
        kill $SCREENSHOT_PID 2>/dev/null || true
    fi
    
    # Kill game demo server
    if [ ! -z "$GAME_DEMO_PID" ]; then
        print_status "Stopping TicTacToe game demo server (PID: $GAME_DEMO_PID)"
        kill $GAME_DEMO_PID 2>/dev/null || true
    fi
    
    # Kill browser processes
    if [ ! -z "$BROWSER_PID" ]; then
        print_status "Stopping browser (PID: $BROWSER_PID)"
        kill $BROWSER_PID 2>/dev/null || true
    fi
    
    # Kill VNC processes
    if [ ! -z "$VNC_PID" ]; then
        print_status "Stopping VNC server (PID: $VNC_PID)"
        kill $VNC_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$NOVNC_PID" ]; then
        print_status "Stopping noVNC (PID: $NOVNC_PID)"
        kill $NOVNC_PID 2>/dev/null || true
    fi
    
    # Kill any remaining Python processes related to our app
    pkill -f "python.*app.py" 2>/dev/null || true
    pkill -f "python.*run_web.py" 2>/dev/null || true
    
    print_success "Cleanup completed"
    exit 0
}

# Register cleanup function to run on script exit
trap cleanup EXIT INT TERM

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create log directory immediately with absolute path
LOG_DIR="$(pwd)/logs"
mkdir -p "$LOG_DIR"
if [ ! -d "$LOG_DIR" ]; then
    echo "Failed to create log directory: $LOG_DIR"
    exit 1
fi

# Define log file paths after LOG_DIR is created
REDIS_LOG="$LOG_DIR/redis.log"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
GAME_DEMO_LOG="$LOG_DIR/game_demo.log"
BROWSER_LOG="$LOG_DIR/browser.log"
SCREENSHOT_LOG="$LOG_DIR/screenshot.log"

# Initialize log files with headers
echo "$(date '+%Y-%m-%d %H:%M:%S') - AC4A Services Log - Redis" > $REDIS_LOG
echo "$(date '+%Y-%m-%d %H:%M:%S') - AC4A Services Log - Backend" > $BACKEND_LOG
echo "$(date '+%Y-%m-%d %H:%M:%S') - AC4A Services Log - Frontend" > $FRONTEND_LOG
echo "$(date '+%Y-%m-%d %H:%M:%S') - AC4A Services Log - Game Demo" > $GAME_DEMO_LOG
echo "$(date '+%Y-%m-%d %H:%M:%S') - AC4A Services Log - Browser" > $BROWSER_LOG
echo "$(date '+%Y-%m-%d %H:%M:%S') - AC4A Services Log - Screenshot" > $SCREENSHOT_LOG

print_status "Starting AC4A services..."
print_status "Log directory: $LOG_DIR"

# Clean up any existing processes from previous runs
print_status "Cleaning up any existing processes from previous runs..."
pkill -f "python.*app.py" 2>/dev/null || true
pkill -f "npm.*run.*dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "node.*vite" 2>/dev/null || true

# Wait a moment for processes to terminate
sleep 2

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed"
    print_status "Installing Python3..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y python3 python3-venv python3-pip
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3 python3-pip
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3 python3-pip
        else
            print_error "Could not install Python3 automatically. Please install Python3 manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install python3
        else
            print_error "Homebrew not found. Please install Python3 manually or install Homebrew first."
            exit 1
        fi
    else
        print_error "Unsupported OS. Please install Python3 manually."
        exit 1
    fi
    
    print_success "Python3 installed"
else
    print_success "Python3 is already installed: $(python3 --version)"
fi

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "Not in a virtual environment. Creating one..."
    
    # Check if venv exists
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    print_status "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
else
    print_success "Already in virtual environment: $VIRTUAL_ENV"
fi

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    print_error "Redis server is not installed"
    print_status "Installing Redis server..."
    
    # Detect OS and install Redis
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            # Ubuntu/Debian
            sudo apt-get update
            sudo apt-get install -y redis-server
        elif command -v yum &> /dev/null; then
            # CentOS/RHEL
            sudo yum install -y redis
        elif command -v dnf &> /dev/null; then
            # Fedora
            sudo dnf install -y redis
        else
            print_error "Could not install Redis automatically. Please install Redis manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install redis
        else
            print_error "Homebrew not found. Please install Redis manually or install Homebrew first."
            exit 1
        fi
    else
        print_error "Unsupported OS. Please install Redis manually."
        exit 1
    fi
    
    print_success "Redis server installed"
else
    print_success "Redis server is already installed"
fi

# Check if pip is available
if ! command -v pip &> /dev/null; then
    print_error "pip is not available"
    print_status "Installing pip..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y python3-pip
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-pip
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3-pip
        else
            print_error "Could not install pip automatically. Please install pip manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install python3
        else
            print_error "Homebrew not found. Please install pip manually or install Homebrew first."
            exit 1
        fi
    else
        print_error "Unsupported OS. Please install pip manually."
        exit 1
    fi
    
    print_success "pip installed"
else
    print_success "pip is already installed: $(pip --version)"
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
if [ -f "web/requirements.txt" ]; then
    pip install -r web/requirements.txt
    print_success "Python dependencies installed"
else
    print_error "requirements.txt not found at web/requirements.txt"
    exit 1
fi

# Check if Node.js and npm are installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed"
    print_status "Installing Node.js..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - try to install Node.js
        if command -v curl &> /dev/null; then
            curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
            sudo apt-get install -y nodejs
        else
            print_error "curl not found. Please install Node.js manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install node
        else
            print_error "Homebrew not found. Please install Node.js manually or install Homebrew first."
            exit 1
        fi
    else
        print_error "Unsupported OS. Please install Node.js manually."
        exit 1
    fi
    
    print_success "Node.js installed"
else
    print_success "Node.js is already installed: $(node --version)"
fi

# Install frontend dependencies
print_status "Installing frontend dependencies..."
if [ -f "web/frontend/package.json" ]; then
    cd web/frontend
    npm install
    cd ../..
    print_success "Frontend dependencies installed"
else
    print_warning "package.json not found at web/frontend/package.json"
fi

# Check if Redis is already running
if check_port $REDIS_PORT; then
    print_warning "Redis is already running on port $REDIS_PORT"
    # Check if it's a system service or user process
    if sudo systemctl is-active --quiet redis-server; then
        print_status "Redis is running as a system service"
        REDIS_SYSTEM_SERVICE=true
        REDIS_PID=""
    else
        REDIS_PID=$(pgrep redis-server | head -1)
        REDIS_SYSTEM_SERVICE=false
    fi
else
    print_status "Starting Redis server on port $REDIS_PORT..."
    # Try to start as system service first
    if sudo systemctl start redis-server 2>/dev/null; then
        print_success "Redis started as system service"
        REDIS_SYSTEM_SERVICE=true
        REDIS_PID=""
    else
        # Fallback to user process
        redis-server --daemonize yes --port $REDIS_PORT
        sleep 2  # Give Redis time to start
        REDIS_PID=$(pgrep redis-server | head -1)
        REDIS_SYSTEM_SERVICE=false
        print_success "Redis server started as user process with PID: $REDIS_PID"
    fi
fi

# Wait for Redis to be ready using redis-cli ping
print_status "Waiting for Redis to be ready on localhost:$REDIS_PORT..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if redis-cli -p $REDIS_PORT ping >/dev/null 2>&1; then
        print_success "Redis is ready on port $REDIS_PORT"
        break
    fi
    
    echo -n "."
    sleep 1
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    print_error "Redis failed to respond on port $REDIS_PORT after $max_attempts attempts"
    print_status "Checking Redis status..."
    if [ ! -z "$REDIS_PID" ]; then
        print_status "Redis process exists with PID: $REDIS_PID"
        if kill -0 $REDIS_PID 2>/dev/null; then
            print_status "Redis process is running"
        else
            print_error "Redis process is not running"
        fi
    fi
    print_status "Trying to start Redis in foreground mode for debugging..."
    redis-server --port $REDIS_PORT &
    REDIS_PID=$!
    sleep 3
    if redis-cli -p $REDIS_PORT ping >/dev/null 2>&1; then
        print_success "Redis is now ready on port $REDIS_PORT"
    else
        print_error "Redis still not responding. Please check Redis installation and configuration."
        exit 1
    fi
fi

# Check if backend port is available
if check_port $BACKEND_PORT; then
    print_warning "Backend port $BACKEND_PORT is already in use"
    kill_port_processes $BACKEND_PORT "backend"
    if check_port $BACKEND_PORT; then
        print_error "Backend port $BACKEND_PORT is still in use after cleanup"
        exit 1
    fi
fi

# Start backend server
cd web
BACKEND_PID=$(start_service_with_logging "Backend server" "$BACKEND_LOG" "PORT=$BACKEND_PORT python app.py")
cd ..

# Wait for backend to be ready
wait_for_service localhost $BACKEND_PORT "Backend server"
check_log_errors "$BACKEND_LOG" "Backend server"

# Check if frontend port is available
if check_port $FRONTEND_PORT; then
    print_warning "Frontend port $FRONTEND_PORT is already in use"
    kill_port_processes $FRONTEND_PORT "frontend"
    if check_port $FRONTEND_PORT; then
        print_error "Frontend port $FRONTEND_PORT is still in use after cleanup"
        exit 1
    fi
fi

# Start frontend server
cd web/frontend
FRONTEND_PID=$(start_service_with_logging "Frontend server" "$FRONTEND_LOG" "VITE_PORT=$BACKEND_PORT npm run dev")
cd ../..

# Wait for frontend to be ready
wait_for_service localhost $FRONTEND_PORT "Frontend server"
check_log_errors "$FRONTEND_LOG" "Frontend server"

# Start TicTacToe game demo server
if [ -f "web/browser/demo/tictactoe/backend/app.py" ]; then
    # Check if game demo port is available
    if check_port $GAME_DEMO_PORT; then
        print_warning "Game demo port $GAME_DEMO_PORT is already in use"
        kill_port_processes $GAME_DEMO_PORT "game demo"
        if check_port $GAME_DEMO_PORT; then
            print_error "Game demo port $GAME_DEMO_PORT is still in use after cleanup"
            exit 1
        fi
    fi
    
    cd web/browser/demo/tictactoe/backend
    GAME_DEMO_PID=$(start_service_with_logging "TicTacToe game demo server" "$GAME_DEMO_LOG" "PORT=$GAME_DEMO_PORT python app.py")
    cd ../../../..
    
    # Wait for game demo server to be ready
    wait_for_service localhost $GAME_DEMO_PORT "TicTacToe game demo"
    check_log_errors "$GAME_DEMO_LOG" "TicTacToe game demo"
else
    print_warning "TicTacToe game demo backend not found at web/browser/demo/tictactoe/backend/app.py"
    GAME_DEMO_PID=""
fi

# Optional: Start browser services if setup.sh exists
# Ensure we're in the root directory
cd "$SCRIPT_DIR"
print_status "Checking for setup.sh at: $(pwd)/web/browser/setup.sh"
if [ -f "$(pwd)/web/browser/setup.sh" ]; then
    print_status "Found setup.sh, making it executable and starting browser services..."
    chmod +x "$(pwd)/web/browser/setup.sh"
    cd web/browser
    
    # Create a wrapper script to handle conda installation properly
    cat > setup_wrapper.sh << 'EOF'
#!/bin/bash
# Wrapper script to handle conda installation before running setup.sh

set -x

MINICONDA_DIR="$HOME/miniconda3"

# Install required system packages
echo "Installing required system packages..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y unzip wget curl
elif command -v yum &> /dev/null; then
    sudo yum install -y unzip wget curl
elif command -v dnf &> /dev/null; then
    sudo dnf install -y unzip wget curl
else
    echo "Warning: Could not install unzip automatically. Please install unzip manually."
fi

# Install Miniconda if it doesn't exist or if conda.sh is missing
if [ ! -d "$MINICONDA_DIR" ] || [ ! -f "$MINICONDA_DIR/etc/profile.d/conda.sh" ]; then
    if [ ! -d "$MINICONDA_DIR" ]; then
        echo "Installing Miniconda..."
    else
        echo "Miniconda directory exists but conda.sh is missing. Reinstalling..."
        rm -rf "$MINICONDA_DIR"
    fi
    
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
    bash miniconda.sh -b -p "$MINICONDA_DIR"
    rm miniconda.sh
    
    # Initialize conda
    source "$MINICONDA_DIR/etc/profile.d/conda.sh"
    conda init bash
    
    echo "Miniconda installation completed"
else
    echo "Miniconda already exists at $MINICONDA_DIR"
fi

# Source conda
echo "Sourcing conda from $MINICONDA_DIR/etc/profile.d/conda.sh"
source "$MINICONDA_DIR/etc/profile.d/conda.sh"

# Now run the original setup script with y y input
echo -e 'y\ny' | ./setup.sh
EOF
    
    chmod +x setup_wrapper.sh
    
    # Run the wrapper script
    BROWSER_PID=$(start_service_with_logging "Browser services" "$BROWSER_LOG" "./setup_wrapper.sh")
    cd ../..
    
    # Wait for browser services
    sleep 5
    if [ ! -z "$BROWSER_PID" ] && kill -0 $BROWSER_PID 2>/dev/null; then
        print_success "Browser services started with PID: $BROWSER_PID"
    else
        print_warning "Browser services may not have started properly"
        print_status "Checking browser log for errors..."
        check_log_errors "$BROWSER_LOG" "Browser services"
    fi
else
    print_warning "setup.sh not found at $(pwd)/web/browser/setup.sh"
    print_status "Current directory: $(pwd)"
    print_status "Checking if web/browser directory exists:"
    ls -la web/browser/ 2>/dev/null || print_error "web/browser directory not found"
fi

# Display service status
echo ""
print_success "All services started successfully!"
echo ""
echo "🌐 SERVICE ENDPOINTS"
echo "==================="
echo "Frontend:     http://localhost:$FRONTEND_PORT"
echo "Backend API:  http://localhost:$BACKEND_PORT"
echo "TicTacToe:    http://localhost:$GAME_DEMO_PORT"
echo "Redis:        localhost:$REDIS_PORT"

if [ ! -z "$BROWSER_PID" ] && kill -0 $BROWSER_PID 2>/dev/null; then
    echo "Browser VNC:  http://localhost:$VNC_PORT/vnc.html"
    echo "Browser Debug: http://localhost:$BROWSER_DEBUG_PORT"
    echo "Screenshots:  http://localhost:$SCREENSHOT_PORT"
fi

echo ""
echo "📝 USAGE"
echo "========"
echo "• Press Ctrl+C to stop all services"
echo "• Frontend will auto-reload on changes"
echo "• Backend will auto-reload on changes (if debug=True)"
echo ""
echo "📋 LOG FILES"
echo "============"
echo "Backend:      $BACKEND_LOG"
echo "Frontend:     $FRONTEND_LOG"
if [ ! -z "$GAME_DEMO_PID" ]; then
    echo "TicTacToe:    $GAME_DEMO_LOG"
fi
if [ ! -z "$BROWSER_PID" ]; then
    echo "Browser:      $BROWSER_LOG"
    echo "Screenshot:   $SCREENSHOT_LOG (managed by setup.sh)"
fi
echo ""
echo "💡 TIPS"
echo "======="
echo "• Use 'tail -f <log_file>' to monitor logs in real-time"
echo "• Check logs for detailed error information"
echo "• Only errors are shown in terminal output"
echo "• Screenshot server logs are in the browser log file"

echo ""
print_status "Services are running. Press Ctrl+C to stop all services..."

# Keep script running and monitor processes
while true; do
    # Check if any critical processes have died
    if [ ! -z "$BACKEND_PID" ] && ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "Backend server process died unexpectedly"
        check_log_errors "$BACKEND_LOG" "Backend server"
        exit 1
    fi
    
    if [ ! -z "$FRONTEND_PID" ] && ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_error "Frontend server process died unexpectedly"
        check_log_errors "$FRONTEND_LOG" "Frontend server"
        exit 1
    fi
    
    if [ "$REDIS_SYSTEM_SERVICE" = "true" ]; then
        if ! sudo systemctl is-active --quiet redis-server; then
            print_error "Redis system service died unexpectedly"
            exit 1
        fi
    elif [ ! -z "$REDIS_PID" ] && ! kill -0 $REDIS_PID 2>/dev/null; then
        print_error "Redis server process died unexpectedly"
        exit 1
    fi
    
    if [ ! -z "$GAME_DEMO_PID" ] && ! kill -0 $GAME_DEMO_PID 2>/dev/null; then
        print_error "TicTacToe game demo server process died unexpectedly"
        check_log_errors "$GAME_DEMO_LOG" "TicTacToe game demo"
        exit 1
    fi
    
    # Periodically check for new errors in logs (every 30 seconds)
    if [ $((SECONDS % 30)) -eq 0 ]; then
        check_log_errors "$BACKEND_LOG" "Backend server"
        check_log_errors "$FRONTEND_LOG" "Frontend server"
        if [ ! -z "$GAME_DEMO_PID" ]; then
            check_log_errors "$GAME_DEMO_LOG" "TicTacToe game demo"
        fi
        if [ ! -z "$BROWSER_PID" ]; then
            check_log_errors "$BROWSER_LOG" "Browser services"
        fi
    fi
    
    sleep 5
done 