# Poll Website - Server

A high-performance FastAPI backend server for the polling application. This server provides RESTful APIs and WebSocket support for real-time poll management and voting functionality.

## Features

- 🚀 Fast and async FastAPI framework
- 🔌 Real-time WebSocket communication
- 📊 Redis for caching and session management
- 🔄 RESTful API endpoints
- 🛡️ Request validation with Pydantic
- 🐳 Docker containerization support
- ⚡ Uvicorn ASGI server with auto-reload

## Tech Stack

- **Framework**: FastAPI
- **Language**: Python 3.11
- **Database/Cache**: Redis
- **WebSocket**: FastAPI WebSocket support
- **Validation**: Pydantic
- **Server**: Uvicorn
- **Containerization**: Docker & Docker Compose

## Prerequisites

Before you begin, ensure you have the following installed:

### For Local Development

- **Python** 3.11 or higher
- **pip** (Python package manager)
- **Redis** server
- **Git**

### For Docker Development

- **Docker** and **Docker Compose**

## 🚀 Quick Start

### Option 1: Docker Development (Recommended)

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd poll-website/poll-server
   ```

2. **Environment Setup**

   Create a `.env` file:

   ```bash
   cp .env.example .env
   ```

   Configure for Docker environment:

   ```env
   REDIS_URL=redis://redis:6379
   CORS_ORIGINS=["http://localhost:3000","http://localhost:7000"]
   DEBUG=True
   ```

3. **Start with Docker Compose**

   ```bash
   # Build and start all services
   docker compose up --build

   # Or run in detached mode
   docker compose up -d --build
   ```

   This will start:

   - Redis server on port 6379
   - Redis Insight (web UI) on port 8001
   - FastAPI server on port 8000

4. **Verify the installation**

   - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Redis Insight: [http://localhost:8001](http://localhost:8001)

### Option 2: Local Development (Without Docker)

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd poll-website/poll-server
   ```

2. **Create and activate virtual environment**

   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   # On Linux/Mac:
   source venv/bin/activate

   # On Windows:
   # venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Setup Redis**

   **Option A: Install Redis locally**

   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install redis-server
   sudo systemctl start redis-server

   # macOS with Homebrew
   brew install redis
   brew services start redis

   # Or run Redis in foreground
   redis-server
   ```

   **Option B: Use Redis Docker container**

   ```bash
   docker run -d --name redis-server -p 6379:6379 redis:latest
   ```

5. **Environment Setup**

   Create a `.env` file in the root directory:

   ```bash
   cp .env.example .env
   ```

   Configure your environment variables:

   ```env
   REDIS_URL=redis://localhost:6379
   CORS_ORIGINS=["http://localhost:3000","http://localhost:7000"]
   DEBUG=True
   ```

6. **Start the development server**

   ```bash
   # Using the run script
   python run.py

   # Or directly with uvicorn
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Verify the installation**

   Open your browser and navigate to:

   - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Alternative Docs: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### Option 3: Production Docker Build

1. **Build the Docker image**

   ```bash
   docker build -t poll-server .
   ```

2. **Run with external Redis**

   ```bash
   docker run -p 8000:8000 \
     -e REDIS_URL=redis://your-redis-host:6379 \
     -e CORS_ORIGINS='["https://your-frontend-domain.com"]' \
     poll-server
   ```

## 📜 Available Scripts

- `python run.py` - Start development server with auto-reload
- `uvicorn app.main:app --host 0.0.0.0 --port 8000` - Start server manually
- `docker compose up` - Start with Docker Compose
- `docker compose down` - Stop Docker services

## 🏗️ Project Structure

```text
poll-server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # Database/Redis configuration
│   ├── websocket_manager.py # WebSocket connection management
│   └── routers/
│       ├── __init__.py
│       └── poll.py          # Poll-related API endpoints
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile              # Docker image configuration
├── requirements.txt        # Python dependencies
├── run.py                 # Development server launcher
├── .env.example           # Environment variables template
└── README.md
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

**For local development:**

```env
REDIS_URL=redis://localhost:6379
CORS_ORIGINS=["http://localhost:3000","http://localhost:7000"]
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

**For production:**

```env
REDIS_URL=redis://your-redis-host:6379
CORS_ORIGINS=["https://your-frontend-domain.com"]
DEBUG=False
HOST=0.0.0.0
PORT=8000
```

### Redis Configuration

The application uses Redis for:

- Caching poll data
- Managing WebSocket connections
- Session storage
- Real-time data synchronization

### CORS Configuration

Configure CORS origins to allow your frontend application:

```python
CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]
```

## 🌐 API Endpoints

### Health Check

- `GET /health` - Server health status

### Poll Management

- `GET /api/polls` - Get all polls
- `POST /api/polls` - Create a new poll
- `GET /api/polls/{poll_id}` - Get specific poll
- `POST /api/polls/{poll_id}/vote` - Vote on a poll
- `DELETE /api/polls/{poll_id}` - Delete a poll

### WebSocket

- `WS /ws` - WebSocket endpoint for real-time updates

### Interactive Documentation

- `/docs` - Swagger UI documentation
- `/redoc` - ReDoc documentation
