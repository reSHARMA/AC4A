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
   cd data-policy-lang
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
Use the setup script to start all services:
```bash
./web/browser/setup.sh
```

This will:
- Start Redis server in daemon mode
- Start the backend server
- Start the frontend development server
- Show service status and endpoints

### Manual Start

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
   cd frontend
   npm run dev
   ```

The application will be available at:
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:5000`
- Redis: `localhost:6379`

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

The development environment will be ready to use with:
- Frontend running on port 5173
- Backend running on port 5000
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