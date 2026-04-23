from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, UploadFile, File
from fastapi.responses import Response
from .models import UserCreate, UserLogin, Token, ThemeUpdate
from .auth import create_user, authenticate_user, get_username_from_token, update_user_theme
from .room_manager import room_manager
import json
import uuid
from datetime import datetime
from typing import Dict

app = FastAPI(title="TUI Chat Ephemeral Server")

# In-memory file storage
# file_id -> {"filename": str, "content": bytes}
ephemeral_files: Dict[str, dict] = {}

@app.post("/register")
def register(user: UserCreate):
    if create_user(user.username, user.password):
        return {"message": "User registered successfully"}
    raise HTTPException(status_code=400, detail="Username already exists")

@app.post("/login", response_model=Token)
def login(user: UserLogin):
    result = authenticate_user(user.username, user.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token, theme = result
    return {"access_token": token, "token_type": "bearer", "theme": theme}

@app.post("/update-theme")
def update_theme(theme_update: ThemeUpdate, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    token = authorization.split(" ")[1]
    username = get_username_from_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    if update_user_theme(username, theme_update.theme):
        return {"message": "Theme updated successfully"}
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    token = authorization.split(" ")[1]
    username = get_username_from_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")

    file_id = str(uuid.uuid4())
    content = await file.read()
    ephemeral_files[file_id] = {
        "filename": file.filename,
        "content": content
    }
    return {"file_id": file_id, "filename": file.filename}

@app.get("/download/{file_id}")
async def download_file(file_id: str):
    if file_id not in ephemeral_files:
        raise HTTPException(status_code=404, detail="File not found or expired")
    
    file_data = ephemeral_files[file_id]
    return Response(
        content=file_data["content"],
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_data['filename']}"}
    )

@app.websocket("/ws/{token}/{target_username}")
async def websocket_endpoint(websocket: WebSocket, token: str, target_username: str):
    username = get_username_from_token(token)
    if not username:
        await websocket.close(code=1008)
        return
    
    room_id = "_".join(sorted([username, target_username]))
    
    await room_manager.connect(websocket, room_id, username)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg_json = json.loads(data)
                text = msg_json.get("text", "")
                msg_type = msg_json.get("type", "text")
                file_id = msg_json.get("file_id")
                filename = msg_json.get("filename")
            except (json.JSONDecodeError, AttributeError):
                # Fallback for old clients or raw text
                text = data
                msg_type = "text"
                file_id = None
                filename = None
            
            message = {
                "sender": username,
                "text": text,
                "type": msg_type,
                "file_id": file_id,
                "filename": filename,
                "time": datetime.now().strftime("%H:%M")
            }
            await room_manager.broadcast(room_id, message)
    except WebSocketDisconnect:
        room_manager.disconnect(websocket, room_id, username)
    except Exception:
        # Handle cases where non-JSON data might be sent
        room_manager.disconnect(websocket, room_id, username)
