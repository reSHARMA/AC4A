# AC4A: Access Control for Agents

AC4A is a comprehensive framework for managing access control permissions for agents. This repository consists of a Python backend and a React-based frontend, providing a user-friendly interface for policy management and enforcement demo.

## Project Structure

```
.
├── src/                    # Core policy system implementation
│   ├── policy_system/      # Policy system components
│   ├── utils/             # Utility functions
│   ├── prompts.py         # System prompts and templates
│   └── app.py             # Core application logic
│
└── web/                   # Web application
    ├── frontend/          # React frontend
    ├── api/               # API endpoints
    ├── agent/             # Agent-related functionality
    ├── templates/         # HTML templates
    ├── static/            # Static assets
    ├── utils/             # Web utilities
    └── app.py             # Web server implementation
```

## Available Applications

The system includes several demo applications to showcase the access control framework:

- **Calendar**: Manage and schedule events
- **Wallet**: Handle financial transactions and balances
- **TravelBooking**: Book and manage travel arrangements
- **ContactManager**: Store and manage contact information

Example tasks for these applications can be found in `tasks.md`, which contains various scenarios to test the access control system.

## Prerequisites

### Backend Requirements
- Python 3.x
- Redis Server
- Required Python packages (see `web/requirements.txt`)

### Frontend Requirements
- Node.js
- npm

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/reSHARMA/AC4A.git
   cd AC4A
   ```

2. **Install Redis**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install redis-server
   
   # macOS
   brew install redis
   ```

3. **Install Backend Dependencies**
   ```bash
   cd web
   pip install -r requirements.txt
   ```

4. **Install Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   ```

## Running the Project

### Quick Start
Use the comprehensive startup script to launch all services:
```bash
./start_services.sh
```

This will automatically:
- Check and install required dependencies (Python3, pip, Node.js, Redis, unzip)
- Create and activate a Python virtual environment
- Install Python dependencies from `web/requirements.txt`
- Install frontend dependencies from `web/frontend/package.json`
- Start Redis server (system service or user process)
- Start the backend server on port 5002
- Start the frontend development server on port 5173
- Start TicTacToe game demo on port 5000 (if available)
- Start browser services with VNC and screenshot capabilities
- Monitor all services and display status
- Provide individual log files for each service

### Service Endpoints
After running `start_services.sh`, the following services will be available:
- **Frontend**: `http://localhost:5173`
- **Backend API**: `http://localhost:5002`
- **TicTacToe Demo**: `http://localhost:5000`
- **Browser VNC**: `http://localhost:6080/vnc.html`
- **Browser Debug**: `http://localhost:9222`
- **Screenshot API**: `http://localhost:8080`
- **Redis**: `localhost:6379`

### Log Files
Individual log files are created in the `logs/` directory:
- `logs/backend.log` - Backend server logs
- `logs/frontend.log` - Frontend server logs
- `logs/game_demo.log` - TicTacToe demo logs
- `logs/browser.log` - Browser services logs
- `logs/redis.log` - Redis server logs

### Manual Start (Alternative)
If you prefer to start services manually:

1. **Start Redis Server**
   ```bash
   redis-server --daemonize yes
   ```

2. **Start the Backend Server**
   ```bash
   cd web
   python app.py
   ```

3. **Start the Frontend Development Server**
   ```bash
   cd web/frontend
   npm run dev
   ```

## Features

- Permission Management System
- Agent Access Control
- Interactive Permission Editor
- Real-time Permission Enforcement
- Comprehensive Logging System
- Multiple Demo Applications (Calendar, Wallet, TravelBooking, ContactManager)

## Development

### GitHub Codespaces (WIP)
This project is configured to work with GitHub Codespaces. To get started:

1. Click the "Code" button in the repository
2. Select "Open with Codespaces"
3. Choose "New codespace"

The codespace will automatically:
- Set up a Python 3.11 environment
- Install Node.js 18.x
- Install Redis
- Install all Python dependencies from `web/requirements.txt`
- Install all frontend dependencies in `web/frontend`
- Configure VS Code with recommended extensions

The development environment will be ready to use. Simply run:
```bash
./start_services.sh
```

This will start all services with:
- Frontend running on port 5173
- Backend running on port 5002
- TicTacToe demo on port 5000
- Browser VNC on port 6080
- Screenshot API on port 8080
- Redis running on port 6379

### Testing
- Backend tests are located in `src/tests/`
- Frontend tests are located in `web/frontend/tests/`

### Debugging
- Use `web/debug_app.py` for debugging purposes
- Logs are stored in `web/debug.log` and `web/log`

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request