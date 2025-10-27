from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, TypeVar, Generic, Literal
import json
import uuid
import asyncio
from ..database import get_redis_client
from ..websocket_manager import manager

# Generic type for API response data
T = TypeVar('T')

# Standardized API Response model
class APIResponse(BaseModel, Generic[T]):
    status: Literal['success', 'error']
    message: str
    data: T

router = APIRouter(
    prefix="/poll",
    tags=["poll"]
)

# Pydantic models
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

class VoteData(BaseModel):
    option_id: str
    new_vote_count: int
    option_value: str

@router.post("/", response_model=APIResponse[PollResponse])
async def create_poll(poll: PollCreate):
    """Create a new poll"""
    redis_client = get_redis_client()
    
    # Generate unique poll ID
    poll_id = str(uuid.uuid4())
    
    # Create options with unique IDs and initialize vote counts
    options = []
    for option_value in poll.options:
        option_id = str(uuid.uuid4())
        options.append({
            "id": option_id,
            "value": option_value,
            "vote": 0
        })
    
    # Store poll data in Redis
    poll_data = {
        "question": poll.question,
        "description": poll.description,
        "options": options
    }
    
    # Store in Redis with key "poll:{id}"
    redis_client.hset(f"poll:{poll_id}", mapping={
        "question": poll.question,
        "description": poll.description or "",
        "options": json.dumps(options)
    })
    
    # Add to polls list for easy retrieval
    redis_client.sadd("polls", poll_id)
    
    poll_response = PollResponse(
        id=poll_id,
        question=poll.question,
        description=poll.description,
        options=[PollOption(**opt) for opt in options]
    )
    
    # Broadcast new poll creation to all connected clients
    new_poll_notification = {
        "type": "new_poll",
        "poll": {
            "id": poll_id,
            "question": poll.question,
            "description": poll.description,
            "options": options
        }
    }
    
    # Use asyncio.create_task to run the broadcast without blocking the response
    asyncio.create_task(manager.broadcast_to_all(new_poll_notification))
    
    return APIResponse[PollResponse](
        status="success",
        message="Poll created successfully",
        data=poll_response
    )

@router.get("/{poll_id}", response_model=APIResponse[PollResponse])
async def get_poll(poll_id: str):
    """Get a specific poll by ID"""
    redis_client = get_redis_client()
    
    # Check if poll exists
    if not redis_client.exists(f"poll:{poll_id}"):
        raise HTTPException(status_code=404, detail="Poll not found")
    
    # Retrieve poll data
    poll_data = redis_client.hgetall(f"poll:{poll_id}")
    options_data = json.loads(poll_data["options"])
    
    poll_response = PollResponse(
        id=poll_id,
        question=poll_data["question"],
        description=poll_data.get("description") or None,
        options=[PollOption(**opt) for opt in options_data]
    )
    
    return APIResponse[PollResponse](
        status="success",
        message="Poll retrieved successfully",
        data=poll_response
    )

@router.post("/{poll_id}/vote", response_model=APIResponse[VoteData])
async def vote_on_poll(poll_id: str, vote: VoteRequest):
    """Vote on a poll"""
    redis_client = get_redis_client()
    
    # Check if poll exists
    if not redis_client.exists(f"poll:{poll_id}"):
        raise HTTPException(status_code=404, detail="Poll not found")
    
    # Get current poll data
    poll_data = redis_client.hgetall(f"poll:{poll_id}")
    options = json.loads(poll_data["options"])
    
    # Find the option by ID and increment vote
    option_found = False
    for option in options:
        if option["id"] == vote.option_id:
            option["vote"] += 1
            option_found = True
            break
    
    if not option_found:
        raise HTTPException(status_code=400, detail="Invalid option ID")
    
    # Update options in Redis
    redis_client.hset(f"poll:{poll_id}", "options", json.dumps(options))
    
    # Find the voted option for response
    voted_option = next(opt for opt in options if opt["id"] == vote.option_id)
    
    # Broadcast vote update to all connected clients for this poll
    vote_update = {
        "type": "vote_update",
        "poll_id": poll_id,
        "option_id": vote.option_id,
        "new_vote_count": voted_option["vote"],
        "option_value": voted_option["value"],
        "all_options": options
    }
    
    # Use asyncio.create_task to run the broadcast without blocking the response
    asyncio.create_task(manager.broadcast_to_poll(vote_update, poll_id))
    
    vote_data = VoteData(
        option_id=vote.option_id,
        new_vote_count=voted_option["vote"],
        option_value=voted_option["value"]
    )
    
    return APIResponse[VoteData](
        status="success",
        message=f"Vote recorded for '{voted_option['value']}'",
        data=vote_data
    )

@router.get("/", response_model=APIResponse[List[PollResponse]])
async def get_all_polls():
    """Get all polls"""
    redis_client = get_redis_client()
    
    # Get all poll IDs
    poll_ids = redis_client.smembers("polls")
    
    polls = []
    for poll_id in poll_ids:
        if redis_client.exists(f"poll:{poll_id}"):
            poll_data = redis_client.hgetall(f"poll:{poll_id}")
            options_data = json.loads(poll_data["options"])
            polls.append(PollResponse(
                id=poll_id,
                question=poll_data["question"],
                description=poll_data.get("description") or None,
                options=[PollOption(**opt) for opt in options_data]
            ))
    
    return APIResponse[List[PollResponse]](
        status="success",
        message=f"Retrieved {len(polls)} polls successfully",
        data=polls
    )

class DeleteData(BaseModel):
    poll_id: str

@router.delete("/{poll_id}", response_model=APIResponse[DeleteData])
async def delete_poll(poll_id: str):
    """Delete a poll"""
    redis_client = get_redis_client()
    
    # Check if poll exists
    if not redis_client.exists(f"poll:{poll_id}"):
        raise HTTPException(status_code=404, detail="Poll not found")
    
    # Delete poll data
    redis_client.delete(f"poll:{poll_id}")
    redis_client.srem("polls", poll_id)
    
    # Broadcast poll deletion to all connected clients
    poll_deleted_notification = {
        "type": "poll_deleted",
        "poll_id": poll_id
    }
    
    # Use asyncio.create_task to run the broadcast without blocking the response
    asyncio.create_task(manager.broadcast_to_all(poll_deleted_notification))
    
    delete_data = DeleteData(poll_id=poll_id)
    
    return APIResponse[DeleteData](
        status="success",
        message=f"Poll {poll_id} deleted successfully",
        data=delete_data
    )