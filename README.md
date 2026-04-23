# Ephemeral Terminal-Based Messaging Application

A fully terminal-based, real-time messaging application where privacy is the ultimate feature. Messages are stored strictly in memory and exist only as long as an active session is running. Once all users leave the chat room, the room and all of its messages are automatically and permanently destroyed.

## 🌟 Key Features

* **Terminal UI**: A sleek, modern Textual-based interface that runs entirely in your terminal.
* **Ephemeral By Design**: No database. No file storage. Messages are held purely in RAM.
* **Session-Based Persistence**: Messages exist and are visible to users only while at least one person remains in the room. 
* **Auto-Cleanup**: The moment the chat room becomes empty (all users disconnect), the room and its entire history are wiped from memory.
* **Secure Authentication**: User passwords are securely hashed using `bcrypt`.
* **Real-Time Communication**: Powered by WebSockets and FastAPI for instant message delivery.
* **10+ Custom Themes**: Personalize your chat experience with built-in themes like Dracula, Nord, Gruvbox, and more. Use the **Themes** button or press `Ctrl+T` to switch!
* **Ephemeral File Sharing**: Send images, videos, or any other files securely through RAM.
* **Full Emoji Support**: Express yourself with an interactive emoji picker (`Ctrl+E`) or use shortcodes like `:smile:` or `:fire:` which auto-replace as you type.

## 🧰 Tech Stack

* **Frontend**: Python + [Textual](https://textual.textualize.io/)
* **Backend**: [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
* **Communication**: WebSockets
* **Security**: `bcrypt` (Password Hashing)

## 📁 Project Structure

```text
tui-chat/
├── server/
│   ├── main.py           # FastAPI application and WebSocket routing
│   ├── auth.py           # In-memory user registration and bcrypt login
│   ├── room_manager.py   # WebSocket connection and ephemeral state management
│   └── models.py         # Pydantic models for request validation
│
├── client/
│   ├── app.py            # Main Textual application entry point
│   ├── app.tcss          # UI styling and layout rules
│   ├── screens.py        # Login, Target Selection, and Chat UI screens
│   └── websocket_handler.py # Async WebSocket client logic
│
└── requirements.txt      # Project dependencies
```

## 🚀 Getting Started

### Prerequisites
* Python 3.8+
* A terminal emulator that supports rich colors (e.g., standard modern terminals)

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
*The backend must be running for the client to work.*

### 3. Running the Terminal Client

Open a second terminal window and run the client convenience script:

```bash
./run_client.sh
```

### 4. How to Test the Chat

1. Start the backend server.
2. Open two separate terminal windows and run the client in both.
3. In Terminal A: Register a new user (e.g., `user1`), then login.
4. In Terminal B: Register a new user (e.g., `user2`), then login.
5. In Terminal A: Start a chat targeting `user2`.
6. In Terminal B: Start a chat targeting `user1`.
7. You are now in a synchronized, ephemeral chat room! Send messages back and forth.
8. To test the ephemeral feature: Have both users close the app. The server console will output `Room user1_user2 is empty. Destroying chat session.`, confirming the memory has been securely wiped.

## ⚠️ Limitations & Notes
* Because the system uses purely in-memory data structures, restarting the FastAPI server will delete all registered users and active chat rooms.
* This project is a demonstration of privacy-first, ephemeral architecture and is built entirely to run on volatile RAM.
