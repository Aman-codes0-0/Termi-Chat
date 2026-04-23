import websockets
import json
import asyncio
from textual.message import Message

class ChatMessageReceived(Message):
    """Message sent when a new chat message is received from the server."""
    def __init__(self, sender: str, text: str, time: str, msg_type: str = "text", file_id: str = None, filename: str = None) -> None:
        self.sender = sender
        self.text = text
        self.time = time
        self.msg_type = msg_type
        self.file_id = file_id
        self.filename = filename
        super().__init__()

class WebSocketClient:
    def __init__(self, app, token: str, target_username: str, server_url: str = "ws://localhost:8000"):
        self.app = app
        self.token = token
        self.target_username = target_username
        self.server_url = server_url
        self.ws = None
        self.receive_task = None

    async def connect(self):
        uri = f"{self.server_url}/ws/{self.token}/{self.target_username}"
        try:
            self.ws = await websockets.connect(uri)
            self.receive_task = asyncio.create_task(self.receive_messages())
            return True
        except Exception as e:
            self.app.log(f"Connection failed: {e}")
            return False

    async def send_message(self, message_data: dict):
        if self.ws:
            await self.ws.send(json.dumps(message_data, ensure_ascii=False))

    async def receive_messages(self):
        try:
            while True:
                if self.ws:
                    message_data = await self.ws.recv()
                    try:
                        message = json.loads(message_data)
                        sender = message.get("sender", "Unknown")
                        text = message.get("text", message_data)
                        time = message.get("time", "")
                        msg_type = message.get("type", "text")
                        file_id = message.get("file_id")
                        filename = message.get("filename")
                    except json.JSONDecodeError:
                        # Fallback for raw text messages
                        sender = "Unknown"
                        text = message_data
                        time = ""
                        msg_type = "text"
                        file_id = None
                        filename = None

                    self.app.post_message(ChatMessageReceived(
                        sender, 
                        text, 
                        time,
                        msg_type,
                        file_id,
                        filename
                    ))
        except websockets.exceptions.ConnectionClosed:
            self.app.log("WebSocket connection closed")
        except Exception as e:
            self.app.log(f"Error receiving message: {e}")

    async def disconnect(self):
        if self.receive_task:
            self.receive_task.cancel()
        if self.ws:
            await self.ws.close()
