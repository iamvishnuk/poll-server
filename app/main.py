from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, TypeVar, Generic, Union, Literal, Any
import uvicorn
import json
import logging
import os
from dotenv import load_dotenv
from .database import redis_conn
from .routers import poll
from .websocket_manager import manager

# Generic type for API response data
T = TypeVar('T')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create FastAPI instance
app = FastAPI(
    title="Poll Server API",
    description="A basic FastAPI server for polling application with Redis storage and WebSocket support",
    version="1.0.0"
)

ALLOWED_ORIGINS = os.getenv('FRONTEND_URL', '').split(',')

app.add_middleware(
    CORSMiddleware, 
    allow_origins=ALLOWED_ORIGINS, 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Custom exception handler for HTTPExceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and return standardized error response"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "data": None
        }
    )

# Custom exception handler for general exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions and return standardized error response"""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "data": None
        }
    )

# Include routers with API versioning
app.include_router(poll.router, prefix="/api/v1")

# Standardized API Response model
class APIResponse(BaseModel, Generic[T]):
    status: Literal['success', 'error']
    message: str
    data: T

# Pydantic models for request/response
class PollOption(BaseModel):
    id: str
    value: str
    vote: int

class PollCreate(BaseModel):
    question: str
    description: Optional[str] = None
    options: List[str]

class PollResponse(BaseModel):
    id: str
    question: str
    description: Optional[str] = None
    options: List[PollOption]

class VoteRequest(BaseModel):
    option_id: str

@app.on_event("startup")
async def startup_event():
    """Test Redis connection on startup"""
    if redis_conn.ping():
        print("✅ Connected to Redis successfully")
    else:
        print("❌ Failed to connect to Redis")

@app.on_event("shutdown")
async def shutdown_event():
    """Close Redis connection on shutdown"""
    redis_conn.close()

class HealthData(BaseModel):
    redis: str

@app.get('/api/v1/health')
async def health_check():
    """Health check endpoint"""
    redis_status = redis_conn.ping()
    health_data = HealthData(redis="connected" if redis_status else "disconnected")
    
    return APIResponse[HealthData](
        status="success" if redis_status else "error",
        message="Service is healthy" if redis_status else "Service is unhealthy - Redis connection failed",
        data=health_data
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """General WebSocket endpoint for all poll updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle ping/pong for connection health
            if message.get("type") == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.websocket("/ws/{poll_id}")
async def websocket_poll_endpoint(websocket: WebSocket, poll_id: str):
    """WebSocket endpoint for specific poll updates"""
    await manager.connect(websocket, poll_id)
    try:
        # Send current poll data when client connects
        from .database import get_redis_client
        redis_client = get_redis_client()
        poll_data = redis_client.hgetall(f"poll:{poll_id}")
        if poll_data:
            options_data = json.loads(poll_data["options"])
            current_poll = {
                "type": "poll_data",
                "poll_id": poll_id,
                "question": poll_data["question"],
                "description": poll_data.get("description") or None,
                "options": options_data
            }
            await manager.send_personal_message(current_poll, websocket)
        
        # Send connection count
        connection_count = manager.get_poll_connection_count(poll_id)
        await manager.broadcast_to_poll({
            "type": "connection_count",
            "poll_id": poll_id,
            "count": connection_count
        }, poll_id)
        
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle ping/pong for connection health
            if message.get("type") == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, poll_id)
        # Update connection count after disconnect
        connection_count = manager.get_poll_connection_count(poll_id)
        await manager.broadcast_to_poll({
            "type": "connection_count",
            "poll_id": poll_id,
            "count": connection_count
        }, poll_id)
    except Exception as e:
        logger.error(f"WebSocket error for poll {poll_id}: {e}")
        manager.disconnect(websocket, poll_id)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)