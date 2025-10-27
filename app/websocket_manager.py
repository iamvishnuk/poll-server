from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store active connections per poll
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store all connections for global broadcasts
        self.all_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, poll_id: str = None):
        """Accept a WebSocket connection and add to appropriate groups"""
        await websocket.accept()
        
        # Add to all connections
        self.all_connections.add(websocket)
        
        # If poll_id is provided, add to poll-specific connections
        if poll_id:
            if poll_id not in self.active_connections:
                self.active_connections[poll_id] = set()
            self.active_connections[poll_id].add(websocket)
            
        logger.info(f"WebSocket connected. Poll: {poll_id}, Total connections: {len(self.all_connections)}")
    
    def disconnect(self, websocket: WebSocket, poll_id: str = None):
        """Remove a WebSocket connection from all groups"""
        # Remove from all connections
        self.all_connections.discard(websocket)
        
        # Remove from poll-specific connections
        if poll_id and poll_id in self.active_connections:
            self.active_connections[poll_id].discard(websocket)
            # Clean up empty poll groups
            if not self.active_connections[poll_id]:
                del self.active_connections[poll_id]
        
        # Also remove from all poll groups if poll_id wasn't specified
        if not poll_id:
            for pid in list(self.active_connections.keys()):
                self.active_connections[pid].discard(websocket)
                if not self.active_connections[pid]:
                    del self.active_connections[pid]
                    
        logger.info(f"WebSocket disconnected. Poll: {poll_id}, Total connections: {len(self.all_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            # Remove broken connection
            self.all_connections.discard(websocket)
    
    async def broadcast_to_poll(self, message: dict, poll_id: str):
        """Broadcast a message to all connections subscribed to a specific poll"""
        if poll_id not in self.active_connections:
            logger.info(f"No connections for poll {poll_id}")
            return
        
        # Create a copy of the set to avoid modification during iteration
        connections = self.active_connections[poll_id].copy()
        broken_connections = set()
        
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to poll {poll_id}: {e}")
                broken_connections.add(connection)
        
        # Remove broken connections
        for broken_conn in broken_connections:
            self.disconnect(broken_conn, poll_id)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all active connections"""
        if not self.all_connections:
            logger.info("No active connections for broadcast")
            return
        
        # Create a copy of the set to avoid modification during iteration
        connections = self.all_connections.copy()
        broken_connections = set()
        
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to all: {e}")
                broken_connections.add(connection)
        
        # Remove broken connections
        for broken_conn in broken_connections:
            self.disconnect(broken_conn)
    
    def get_poll_connection_count(self, poll_id: str) -> int:
        """Get the number of active connections for a specific poll"""
        return len(self.active_connections.get(poll_id, set()))
    
    def get_total_connection_count(self) -> int:
        """Get the total number of active connections"""
        return len(self.all_connections)

# Global instance
manager = ConnectionManager()