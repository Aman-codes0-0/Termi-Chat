from fastapi import WebSocket
from typing import Dict, List
import json
from datetime import datetime
import asyncio

class RoomManager:
    def __init__(self):
        # room_id -> list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # room_id -> list of message dicts {"sender": ..., "text": ..., "time": ...}
        self.room_messages: Dict[str, List[Dict[str, str]]] = {}

    async def connect(self, websocket: WebSocket, room_id: str, username: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
            self.room_messages[room_id] = []
        
        self.active_connections[room_id].append(websocket)
        
        # Send previous messages in this session
        for msg in self.room_messages[room_id]:
            await websocket.send_text(json.dumps(msg, ensure_ascii=False))
            
        # Broadcast that user joined
        await self.broadcast(room_id, {
            "sender": "System",
            "text": f"{username} joined the chat",
            "time": datetime.now().strftime("%H:%M")
        })

    def disconnect(self, websocket: WebSocket, room_id: str, username: str):
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                self.active_connections[room_id].remove(websocket)
            
            # If room is empty, destroy it
            if not self.active_connections[room_id]:
                print(f"Room {room_id} is empty. Destroying chat session.")
                del self.active_connections[room_id]
                if room_id in self.room_messages:
                    del self.room_messages[room_id]
            else:
                # Still people in room, broadcast leave asynchronously
                asyncio.create_task(self.broadcast(room_id, {
                    "sender": "System",
                    "text": f"{username} left the chat",
                    "time": datetime.now().strftime("%H:%M")
                }))

    async def broadcast(self, room_id: str, message: dict):
        # System messages and user messages are stored as long as the room exists
        if room_id in self.room_messages:
            self.room_messages[room_id].append(message)
            
        if room_id in self.active_connections:
            disconnected_websockets = []
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_text(json.dumps(message, ensure_ascii=False))
                except Exception:
                    disconnected_websockets.append(connection)
            
            for ws in disconnected_websockets:
                if ws in self.active_connections[room_id]:
                    self.active_connections[room_id].remove(ws)

room_manager = RoomManager()
