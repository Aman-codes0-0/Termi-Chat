from fastapi import WebSocket
from typing import Dict, List
import json
from datetime import datetime
import asyncio

class RoomManager:
    def __init__(self):
        # room_id -> list of (WebSocket, username)
        self.active_connections: Dict[str, List[tuple[WebSocket, str]]] = {}
        # room_id -> list of message dicts {"sender": ..., "text": ..., "time": ...}
        self.room_messages: Dict[str, List[Dict[str, str]]] = {}
        # recipient -> sender -> count
        self.unread_counts: Dict[str, Dict[str, int]] = {}

    def get_unread_count(self, recipient: str, sender: str) -> int:
        return self.unread_counts.get(recipient, {}).get(sender, 0)
        
    def reset_unread_count(self, recipient: str, sender: str):
        if recipient in self.unread_counts and sender in self.unread_counts[recipient]:
            self.unread_counts[recipient][sender] = 0

    async def connect(self, websocket: WebSocket, room_id: str, username: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
            if room_id not in self.room_messages:
                self.room_messages[room_id] = []
        
        self.active_connections[room_id].append((websocket, username))
        
        # Reset unread count for this user
        users = room_id.split('_')
        if len(users) == 2:
            other_user = users[0] if users[1] == username else users[1]
            self.reset_unread_count(username, other_user)
        
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
            self.active_connections[room_id] = [(ws, u) for ws, u in self.active_connections[room_id] if ws != websocket]
            
            # Check if there are unread messages
            has_unread = False
            users = room_id.split('_')
            if len(users) == 2:
                u1, u2 = users
                if self.get_unread_count(u1, u2) > 0 or self.get_unread_count(u2, u1) > 0:
                    has_unread = True

            # If room is empty, destroy it
            if not self.active_connections[room_id]:
                print(f"Room {room_id} is empty.")
                del self.active_connections[room_id]
                if not has_unread and room_id in self.room_messages:
                    print("No unread messages, destroying chat session.")
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
            
        sender = message.get("sender")
        users_in_room = set()
        
        if room_id in self.active_connections:
            disconnected_websockets = []
            for connection, user in self.active_connections[room_id]:
                users_in_room.add(user)
                try:
                    await connection.send_text(json.dumps(message, ensure_ascii=False))
                except Exception:
                    disconnected_websockets.append(connection)
            
            # Remove disconnected
            if disconnected_websockets:
                self.active_connections[room_id] = [(ws, u) for ws, u in self.active_connections[room_id] if ws not in disconnected_websockets]

        # Increment unread count if target user is not in the room
        if sender and sender != "System":
            users = room_id.split('_')
            if len(users) == 2:
                target_user = users[0] if users[1] == sender else users[1]
                if target_user not in users_in_room:
                    if target_user not in self.unread_counts:
                        self.unread_counts[target_user] = {}
                    self.unread_counts[target_user][sender] = self.unread_counts[target_user].get(sender, 0) + 1

room_manager = RoomManager()
