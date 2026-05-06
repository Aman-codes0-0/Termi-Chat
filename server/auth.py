import sqlite3
import bcrypt
import uuid
import json
from typing import Dict, Optional, Tuple, List

# Database initialization
DB_PATH = "database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Users table
    # friends: list of accepted friends
    # pending_requests: list of usernames who sent a request to this user
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            theme TEXT DEFAULT 'default',
            friends TEXT DEFAULT '[]',
            pending_requests TEXT DEFAULT '[]'
        )
    ''')
    conn.commit()
    conn.close()

# Run initialization
init_db()

# In-memory sessions (still ephemeral)
sessions: Dict[str, str] = {}

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte_enc)

def create_user(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        hashed_password = get_password_hash(password)
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> Optional[Tuple[str, str]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password, theme FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    hashed_password, theme = row
    if not verify_password(password, hashed_password):
        return None
    
    token = str(uuid.uuid4())
    sessions[token] = username
    return token, theme

def get_username_from_token(token: str) -> Optional[str]:
    return sessions.get(token)

def update_user_theme(username: str, theme: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET theme = ? WHERE username = ?", (theme, username))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def send_friend_request(from_user: str, to_user: str) -> bool:
    if from_user == to_user: return False
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if target user exists
    cursor.execute("SELECT pending_requests, friends FROM users WHERE username = ?", (to_user,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    pending = json.loads(row[0])
    friends = json.loads(row[1])
    
    if from_user not in pending and from_user not in friends:
        pending.append(from_user)
        cursor.execute("UPDATE users SET pending_requests = ? WHERE username = ?", (json.dumps(pending), to_user))
        conn.commit()
    
    conn.close()
    return True

def accept_friend_request(username: str, requester: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Remove from pending of current user
    cursor.execute("SELECT pending_requests, friends FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    
    pending = json.loads(row[0])
    friends = json.loads(row[1])
    
    if requester in pending:
        pending.remove(requester)
        if requester not in friends:
            friends.append(requester)
        
        cursor.execute("UPDATE users SET pending_requests = ?, friends = ? WHERE username = ?", 
                       (json.dumps(pending), json.dumps(friends), username))
        
        # Also add current user to requester's friends list
        cursor.execute("SELECT friends FROM users WHERE username = ?", (requester,))
        req_row = cursor.fetchone()
        if req_row:
            req_friends = json.loads(req_row[0])
            if username not in req_friends:
                req_friends.append(username)
            cursor.execute("UPDATE users SET friends = ? WHERE username = ?", (json.dumps(req_friends), requester))
            
        conn.commit()
        conn.close()
        return True
        
    conn.close()
    return False

def get_pending_requests(username: str) -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT pending_requests FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []

def get_friends(username: str) -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT friends FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []

def search_users(query: str, current_user: str) -> List[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username LIKE ? LIMIT 10", (f"%{query}%",))
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results
