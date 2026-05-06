from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, UploadFile, File
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from .models import UserCreate, UserLogin, Token, ThemeUpdate
from .auth import create_user, authenticate_user, get_username_from_token, update_user_theme, send_friend_request, accept_friend_request, get_pending_requests, get_friends, search_users
from .room_manager import room_manager
import json
import uuid
from datetime import datetime
from typing import Dict

app = FastAPI(title="TUI Chat Ephemeral Server")

# In-memory file storage
# file_id -> {"filename": str, "content": bytes}
ephemeral_files: Dict[str, dict] = {}

# In-memory online tracking
online_users: Dict[str, datetime] = {}

def update_online_status(username: str):
    online_users[username] = datetime.now()


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

@app.get("/friends")
def list_friends(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization.split(" ")[1]
    username = get_username_from_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    update_online_status(username)
    friends = get_friends(username)
    
    result = []
    now = datetime.now()
    for f in friends:
        is_online = False
        if f in online_users:
            if (now - online_users[f]).total_seconds() < 10:
                is_online = True
                
        unread = room_manager.get_unread_count(username, f) # username is the recipient, f is the sender
        
        result.append({
            "username": f,
            "is_online": is_online,
            "unread_count": unread
        })
        
    return {"friends": result}

@app.get("/pending-requests")
def list_pending(authorization: str = Header(...)):
    token = authorization.split(" ")[1]
    username = get_username_from_token(token)
    if not username: raise HTTPException(status_code=401)
    update_online_status(username)
    return {"requests": get_pending_requests(username)}

@app.post("/send-request")
def send_request(data: dict, authorization: str = Header(...)):
    token = authorization.split(" ")[1]
    username = get_username_from_token(token)
    if not username: raise HTTPException(status_code=401)
    if send_friend_request(username, data.get("to_user")):
        return {"message": "Request sent"}
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/accept-request")
def accept_request(data: dict, authorization: str = Header(...)):
    token = authorization.split(" ")[1]
    username = get_username_from_token(token)
    if not username: raise HTTPException(status_code=401)
    if accept_friend_request(username, data.get("requester")):
        return {"message": "Request accepted"}
    raise HTTPException(status_code=400, detail="Failed to accept")

@app.get("/search-users")
def search_registered_users(q: str, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization.split(" ")[1]
    username = get_username_from_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")
    update_online_status(username)
    return {"results": search_users(q, username)}

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

# Serve static files from the 'web' directory
app.mount("/", StaticFiles(directory="web", html=True), name="web")
