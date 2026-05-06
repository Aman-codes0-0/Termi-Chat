# Termi-Chat: Cross-Platform Ephemeral Messaging Application

A fully real-time messaging application featuring both a **Terminal UI (TUI)** and a **Web Client**. 
Termi-Chat blends persistent identity management with ephemeral, memory-only chat sessions. 

## 🌟 Key Features

* **Cross-Platform**: Chat seamlessly between the sleek Textual-based Terminal UI and the modern Web interface.
* **Hybrid Data Model**: 
  * **Persistent Identity**: User accounts, themes, and friend networks are stored securely in a local SQLite database (`database.db`).
  * **Ephemeral Chat**: Messages and file transfers are held purely in RAM. Once a chat session ends or the server restarts, the room and its messages are permanently destroyed.
* **Secure Authentication**: User passwords are securely hashed using `bcrypt`.
* **Real-Time Communication**: Powered by WebSockets and FastAPI for instant message delivery and online status tracking.
* **Friend System**: Send, accept, and manage friend requests. Track the online status of your friends in real-time.
* **Custom Themes**: Personalize your TUI chat experience with built-in themes (Dracula, Nord, Gruvbox, etc.).
* **File Sharing**: Send ephemeral images or files securely through RAM.
* **Emoji Support**: Express yourself with an interactive emoji picker or use shortcodes.

## 🧰 Tech Stack

* **TUI Frontend**: Python + [Textual](https://textual.textualize.io/)
* **Web Frontend**: Vanilla HTML/CSS/JS
* **Backend**: [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
* **Communication**: WebSockets
* **Security & Storage**: `bcrypt`, `SQLite`

## 📁 Project Structure

```text
Termi-Chat/
├── server/
│   ├── main.py           # FastAPI application, WebSocket routing, Web Static Files
│   ├── auth.py           # SQLite user registration, friend system, and auth
│   ├── room_manager.py   # WebSocket connection and ephemeral state management
│   └── models.py         # Pydantic models for request validation
│
├── client/
│   ├── app.py            # Main Textual application entry point
│   ├── app.tcss          # UI styling and layout rules
│   └── screens.py        # TUI screens (Login, Main Chat with Split-Screen)
│
├── web/                  # Web Client Files
│   ├── index.html        
│   ├── style.css         
│   └── script.js         
│
├── database.db           # SQLite database (Users, Friends)
├── requirements.txt      # Project dependencies
├── run_server.sh         # Script to run backend
└── run_client.sh         # Script to run TUI client
```

## 🚀 Getting Started

### Prerequisites
* Python 3.8+
* A modern terminal emulator (for TUI client)
* Any modern web browser (for Web client)

### 1. Installation

Clone this repository and set up a virtual environment:

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment (Linux/macOS)
source venv/bin/activate
# Or on Windows:
# venv\Scripts\activate

# Install the required dependencies
pip install -r requirements.txt
```

### 2. Running the Backend Server

Open a terminal and run the server convenience script:

```bash
./run_server.sh
```
*This will start the FastAPI backend on `http://127.0.0.1:8000`. The server must be running for any client to work.*

### 3. Connecting Clients

**Option A: Using the Terminal Client**
Open a second terminal window and run the client convenience script:
```bash
./run_client.sh
```

**Option B: Using the Web Client**
Open your web browser and navigate to:
```
http://127.0.0.1:8000/
```

### 4. How to Test

1. Start the backend server.
2. Open the Web client in a browser and the TUI client in a terminal.
3. Register a new user on both clients.
4. Send a friend request from one user to the other.
5. Accept the friend request.
6. Start chatting! You are now in a synchronized, ephemeral chat room.
7. To test the ephemeral feature: Restart the server. You'll see that accounts and friends persist, but chat messages are completely wiped.
