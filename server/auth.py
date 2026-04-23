import bcrypt
import uuid
from typing import Dict, Optional, Tuple

# In-memory user database
# username -> {"password": hashed_password, "theme": theme_name}
users_db: Dict[str, dict] = {}

# In-memory sessions
# token -> username
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
    if username in users_db:
        return False
    users_db[username] = {
        "password": get_password_hash(password),
        "theme": "default"
    }
    return True

def authenticate_user(username: str, password: str) -> Optional[Tuple[str, str]]:
    if username not in users_db:
        return None
    user_data = users_db[username]
    if not verify_password(password, user_data["password"]):
        return None
    
    # Generate session token
    token = str(uuid.uuid4())
    sessions[token] = username
    return token, user_data.get("theme", "default")

def get_username_from_token(token: str) -> Optional[str]:
    return sessions.get(token)

def update_user_theme(username: str, theme: str) -> bool:
    if username in users_db:
        users_db[username]["theme"] = theme
        return True
    return False
