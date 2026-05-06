const API_URL = window.location.origin;
const WS_URL = API_URL.replace('http', 'ws');

let token = null;
let username = null;
let targetUsername = null;
let socket = null;
let friends = [];
let pendingRequests = [];

// DOM Elements
const authScreen = document.getElementById('auth-screen');
const chatScreen = document.getElementById('chat-screen');
const messagesContainer = document.getElementById('messages-container');
const messageInput = document.getElementById('message-input');
const authError = document.getElementById('auth-error');
const friendsList = document.getElementById('friends-list');
const userSearchInput = document.getElementById('user-search-input');
const searchResultsSidebar = document.getElementById('search-results-sidebar');
const pendingList = document.getElementById('pending-list');

// Navigation
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

// Auth Logic
async function handleAuth(type) {
    const u = document.getElementById('username').value;
    const p = document.getElementById('password').value;

    if (!u || !p) {
        authError.textContent = "Please fill all fields";
        return;
    }

    try {
        const response = await fetch(`${API_URL}/${type}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
        });

        const data = await response.json();

        if (response.ok) {
            if (type === 'login') {
                token = data.access_token;
                username = u;
                document.getElementById('user-display-name').textContent = username;
                await loadFriends();
                await loadPendingRequests();
                showScreen('chat-screen');
                startPolling();
            } else {
                authError.textContent = "Registered! Now login.";
                authError.style.color = "var(--success)";
            }
        } else {
            authError.textContent = data.detail || "Error occurred";
        }
    } catch (e) {
        authError.textContent = "Server connection failed";
    }
}

document.getElementById('login-btn').onclick = () => handleAuth('login');
document.getElementById('register-btn').onclick = () => handleAuth('register');

const passwordInput = document.getElementById('password');
const togglePasswordBtn = document.getElementById('toggle-password');

togglePasswordBtn.onclick = () => {
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordInput.setAttribute('type', type);
    togglePasswordBtn.textContent = type === 'password' ? '👁️' : '🔒';
};

// Friends Management
async function loadFriends() {
    try {
        const response = await fetch(`${API_URL}/friends`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        friends = data.friends || [];
        renderFriendsList();
    } catch (e) {
        console.error("Failed to load friends", e);
    }
}

async function loadPendingRequests() {
    try {
        const response = await fetch(`${API_URL}/pending-requests`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        pendingRequests = data.requests || [];
        renderPendingList();
    } catch (e) {
        console.error("Failed to load requests", e);
    }
}

function renderFriendsList() {
    friendsList.innerHTML = '';
    
    if (friends.length === 0) {
        friendsList.innerHTML = '<p class="empty-list">No friends yet. Search above!</p>';
        return;
    }

    friends.forEach(friendObj => {
        let friend, isOnline = false, unreadCount = 0;
        
        if (typeof friendObj === 'string') {
            friend = friendObj;
        } else {
            friend = friendObj.username;
            isOnline = friendObj.is_online;
            unreadCount = friendObj.unread_count;
        }
        
        const div = document.createElement('div');
        div.className = `friend-item ${targetUsername === friend ? 'active' : ''}`;
        
        let unreadBadge = unreadCount > 0 && targetUsername !== friend 
            ? `<span class="unread-badge">${unreadCount}</span>` 
            : '';
            
        let statusDot = isOnline 
            ? `<span class="status-dot online" title="Online"></span>` 
            : `<span class="status-dot offline" title="Offline"></span>`;

        div.innerHTML = `
            <div class="friend-avatar">
                ${friend[0].toUpperCase()}
                ${statusDot}
            </div>
            <div class="friend-info">
                <div class="friend-name-container">
                    <span class="friend-name">${friend}</span>
                    ${unreadBadge}
                </div>
            </div>
        `;
        div.onclick = () => {
            friendObj.unread_count = 0; // Optimistic reset
            startChat(friend);
            renderFriendsList(); // Refresh UI to hide badge
        };
        friendsList.appendChild(div);
    });
}

function renderPendingList() {
    const badge = document.getElementById('notif-badge');
    pendingList.innerHTML = '';
    
    if (pendingRequests.length === 0) {
        document.getElementById('pending-section').style.display = 'none';
        badge.style.display = 'none';
        return;
    }

    document.getElementById('pending-section').style.display = 'block';
    badge.style.display = 'flex';
    badge.textContent = pendingRequests.length;

    pendingRequests.forEach(requester => {
        const div = document.createElement('div');
        div.className = 'pending-item';
        div.innerHTML = `
            <span class="pending-name">${requester}</span>
            <div class="pending-actions">
                <button class="btn-accept" title="Accept">Accept</button>
            </div>
        `;
        div.querySelector('.btn-accept').onclick = () => acceptRequest(requester);
        pendingList.appendChild(div);
    });
}

document.getElementById('notif-bell').onclick = () => {
    document.getElementById('pending-section').scrollIntoView({ behavior: 'smooth' });
};

// User Search
userSearchInput.oninput = async (e) => {
    const query = e.target.value.trim();
    if (query.length < 2) {
        searchResultsSidebar.innerHTML = '';
        return;
    }

    try {
        const response = await fetch(`${API_URL}/search-users?q=${query}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        renderSearchResults(data.results);
    } catch (e) {
        console.error("Search failed", e);
    }
};

function renderSearchResults(results) {
    searchResultsSidebar.innerHTML = '';
    if (results.length === 0) {
        searchResultsSidebar.innerHTML = '<div class="search-result-sidebar-item">No users found</div>';
        return;
    }

    results.forEach(result => {
        const div = document.createElement('div');
        div.className = 'search-result-sidebar-item';
        const isFriend = friends.includes(result);
        const isPending = pendingRequests.includes(result);
        
        div.innerHTML = `
            <span>${result} ${result === username ? '(You)' : ''}</span>
            <div class="search-actions">
                ${isFriend || result === username ? `<button class="chat-now-btn" title="Chat Now">💬</button>` : ''}
                ${(!isFriend && result !== username) ? `<button class="add-friend-btn" title="Send Request">✉️</button>` : ''}
            </div>
        `;
        
        const chatBtn = div.querySelector('.chat-now-btn');
        if (chatBtn) {
            chatBtn.onclick = (e) => {
                e.stopPropagation();
                searchResultsSidebar.innerHTML = '';
                userSearchInput.value = '';
                startChat(result);
            };
        }
        
        const addBtn = div.querySelector('.add-friend-btn');
        if (addBtn) {
            addBtn.onclick = (e) => {
                e.stopPropagation();
                sendRequest(result);
            };
        }
        
        searchResultsSidebar.appendChild(div);
    });
}

async function sendRequest(toUser) {
    try {
        const response = await fetch(`${API_URL}/send-request`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ to_user: toUser })
        });
        if (response.ok) {
            searchResultsSidebar.innerHTML = '<div class="search-result-sidebar-item">Request sent!</div>';
            setTimeout(() => {
                searchResultsSidebar.innerHTML = '';
                userSearchInput.value = '';
            }, 1000);
        }
    } catch (e) {
        console.error("Failed to send request", e);
    }
}

async function acceptRequest(requester) {
    try {
        const response = await fetch(`${API_URL}/accept-request`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ requester: requester })
        });
        if (response.ok) {
            await loadFriends();
            await loadPendingRequests();
        }
    } catch (e) {
        console.error("Failed to accept", e);
    }
}

// Polling for updates
function startPolling() {
    setInterval(() => {
        if (token) {
            loadPendingRequests();
            loadFriends();
        }
    }, 5000); // Check every 5 seconds
}

// Chat Logic
function startChat(friend) {
    if (socket) {
        socket.close();
    }
    targetUsername = friend;
    renderFriendsList();
    document.getElementById('chat-with-display').textContent = `Chatting with ${targetUsername}`;
    messagesContainer.innerHTML = '';
    connectWebSocket();
}

function connectWebSocket() {
    socket = new WebSocket(`${WS_URL}/ws/${token}/${targetUsername}`);

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        addMessage(data);
    };

    socket.onclose = () => {
        console.log("WebSocket closed");
    };
}

function addMessage(msg) {
    const placeholder = messagesContainer.querySelector('.chat-placeholder');
    if (placeholder) placeholder.remove();

    const div = document.createElement('div');
    const isSelf = msg.sender === username;
    const isSystem = msg.sender === 'System';

    div.className = `message ${isSystem ? 'system' : (isSelf ? 'self' : 'other')}`;
    
    if (isSystem) {
        div.textContent = msg.text;
    } else {
        const meta = document.createElement('div');
        meta.className = 'message-meta';
        meta.textContent = `${msg.sender} • ${msg.time}`;
        
        const text = document.createElement('div');
        if (msg.type === 'file') {
            text.innerHTML = `📁 <a href="${API_URL}/download/${msg.file_id}" target="_blank" style="color: inherit;">${msg.filename}</a>`;
        } else {
            text.textContent = msg.text;
        }
        
        div.appendChild(meta);
        div.appendChild(text);
    }

    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function sendMessage() {
    const text = messageInput.value.trim();
    if (text && socket) {
        socket.send(JSON.stringify({
            type: 'text',
            text: text
        }));
        messageInput.value = '';
    }
}

document.getElementById('send-btn').onclick = sendMessage;
messageInput.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };

// Emoji Picker Support
const emojiBtn = document.getElementById('emoji-btn');
const emojiPicker = document.getElementById('emoji-picker');

emojiBtn.onclick = () => {
    emojiPicker.style.display = emojiPicker.style.display === 'none' ? 'grid' : 'none';
};

// Close emoji picker when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.emoji-container')) {
        emojiPicker.style.display = 'none';
    }
});

// Insert emoji into input
document.querySelectorAll('.emoji-picker span').forEach(emoji => {
    emoji.onclick = (e) => {
        messageInput.value += e.target.textContent;
        emojiPicker.style.display = 'none';
        messageInput.focus();
    };
});

// Text-based Emoji Replacement
const EMOJI_MAP = {
    ':smile:': '😀', ':laugh:': '😂', ':heart:': '❤️', ':fire:': '🔥', ':rocket:': '🚀'
};

messageInput.oninput = (e) => {
    let val = e.target.value;
    for (const [code, emoji] of Object.entries(EMOJI_MAP)) {
        if (val.includes(code)) {
            val = val.replace(code, emoji);
        }
    }
    e.target.value = val;
};

// File Upload Logic
const fileUpload = document.getElementById('file-upload');
fileUpload.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file || !socket) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            socket.send(JSON.stringify({
                type: 'file',
                filename: data.filename,
                file_id: data.file_id
            }));
        } else {
            console.error("File upload failed");
        }
    } catch (err) {
        console.error("Error uploading file:", err);
    }
    fileUpload.value = ''; // Reset input
};

// Logout
document.getElementById('logout-btn').onclick = () => {
    location.reload();
};
