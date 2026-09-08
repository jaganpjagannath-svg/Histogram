/**
 * Histogram - Direct Messaging Client
 * Handles real-time polling, thread switching, instant message delivery, and auto-scroll.
 */

let activeRecipientUsername = null;
let chatPollingInterval = null;
let lastMessageCount = 0;

function initMessaging(initialUsername = null) {
    activeRecipientUsername = initialUsername;

    if (activeRecipientUsername) {
        startChatPolling();
        scrollToBottom();
    }

    // Enter key submit in message input
    const msgInput = document.getElementById('chat-message-input');
    if (msgInput) {
        msgInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submitDirectMessage();
            }
        });
    }
}

// Select Conversation
function selectConversation(username) {
    activeRecipientUsername = username;
    const layout = document.querySelector('.messages-layout');
    if (layout) layout.classList.add('in-chat');

    // Highlight active in sidebar
    document.querySelectorAll('.conversation-item').forEach(item => {
        if (item.getAttribute('data-username') === username) {
            item.classList.add('active');
            const unread = item.querySelector('.unread-dot');
            if (unread) unread.remove();
        } else {
            item.classList.remove('active');
        }
    });

    loadChatHistory(username);
    startChatPolling();
}

// Load Chat History from API
async function loadChatHistory(username) {
    try {
        const response = await fetch(`/api/messages/${username}`);
        if (!response.ok) throw new Error("Could not load chat");
        const data = await response.json();

        // Update Chat Header
        const headerAvatar = document.getElementById('chat-header-avatar');
        const headerName = document.getElementById('chat-header-name');
        const headerLink = document.getElementById('chat-header-link');
        const chatEmpty = document.getElementById('chat-empty-state');
        const chatActive = document.getElementById('chat-active-state');

        if (chatEmpty) chatEmpty.style.display = 'none';
        if (chatActive) chatActive.style.display = 'flex';

        if (headerAvatar) headerAvatar.src = `/uploads/profiles/${data.target_user.profile_picture}`;
        if (headerName) headerName.textContent = data.target_user.full_name || data.target_user.username;
        if (headerLink) {
            headerLink.href = `/profile/${data.target_user.username}`;
            headerLink.textContent = `@${data.target_user.username}`;
        }

        renderMessages(data.messages);
    } catch (err) {
        console.error("Chat error:", err);
    }
}

// Render Message List
function renderMessages(messages) {
    const container = document.getElementById('chat-messages-container');
    if (!container) return;

    if (messages.length === lastMessageCount) {
        return; // No change
    }

    lastMessageCount = messages.length;
    container.innerHTML = '';

    messages.forEach(msg => {
        const wrapper = document.createElement('div');
        wrapper.className = `message-bubble-wrapper ${msg.is_mine ? 'mine' : 'theirs'}`;
        wrapper.innerHTML = `
            <div class="message-bubble">${escapeHtml(msg.message)}</div>
            <div class="message-time">${formatMsgTime(msg.created_at)}</div>
        `;
        container.appendChild(wrapper);
    });

    scrollToBottom();
}

// Submit Message
async function submitDirectMessage() {
    const input = document.getElementById('chat-message-input');
    if (!input || !activeRecipientUsername) return;

    const messageText = input.value.trim();
    if (!messageText) return;

    input.value = '';

    // Optimistic UI Append
    const container = document.getElementById('chat-messages-container');
    if (container) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-bubble-wrapper mine';
        wrapper.innerHTML = `
            <div class="message-bubble">${escapeHtml(messageText)}</div>
            <div class="message-time">sending...</div>
        `;
        container.appendChild(wrapper);
        scrollToBottom();
    }

    try {
        const response = await fetch('/api/messages/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                receiver_username: activeRecipientUsername,
                message: messageText
            })
        });

        if (!response.ok) throw new Error("Could not send message");
        const data = await response.json();

        // Update optimistic item with real time
        const times = container.querySelectorAll('.message-time');
        if (times.length > 0) {
            times[times.length - 1].textContent = "just now";
        }
    } catch (err) {
        console.error("Send error:", err);
        showToast("Failed to send message", "error");
    }
}

// Real-time Polling
function startChatPolling() {
    if (chatPollingInterval) clearInterval(chatPollingInterval);
    chatPollingInterval = setInterval(() => {
        if (activeRecipientUsername) {
            fetch(`/api/messages/${activeRecipientUsername}`)
                .then(res => res.json())
                .then(data => {
                    if (data && data.messages) {
                        if (data.messages.length > lastMessageCount) {
                            renderMessages(data.messages);
                        }
                    }
                })
                .catch(e => console.error("Poll error", e));
        }
    }, 3000);
}

function scrollToBottom() {
    const container = document.getElementById('chat-messages-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function formatMsgTime(dtStr) {
    if (!dtStr) return '';
    try {
        const parts = dtStr.split(' ');
        if (parts.length > 1) {
            return parts[1].substring(0, 5);
        }
        return dtStr;
    } catch (e) {
        return '';
    }
}

// Mobile back to conversation list
function backToConversations() {
    const layout = document.querySelector('.messages-layout');
    if (layout) layout.classList.remove('in-chat');
    if (chatPollingInterval) clearInterval(chatPollingInterval);
    activeRecipientUsername = null;
}

// Start New Chat Modal
function openNewChatModal() {
    openUsersModal("New Message", "/api/users/following");
}
