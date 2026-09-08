/**
 * Histogram - Core Application JavaScript
 * Handles likes, comments, saves, follows, search, sharing, toasts, and modals.
 */

// Toast Alert System
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}

// Copy to Clipboard
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            showToast("Link copied to clipboard!", "success");
        }).catch(() => fallbackCopy(text));
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        document.execCommand('copy');
        showToast("Link copied to clipboard!", "success");
    } catch (err) {
        showToast("Failed to copy link", "error");
    }
    document.body.removeChild(textArea);
}

// Like / Unlike Post
async function toggleLike(postId, btnElement) {
    try {
        const response = await fetch(`/api/posts/${postId}/like`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) throw new Error("Failed to toggle like");
        const data = await response.json();

        // Update button appearance
        const iconSvg = btnElement.querySelector('svg');
        const countSpan = document.getElementById(`likes-count-${postId}`);

        if (data.liked) {
            btnElement.classList.add('liked');
            if (iconSvg) {
                iconSvg.setAttribute('fill', 'currentColor');
            }
        } else {
            btnElement.classList.remove('liked');
            if (iconSvg) {
                iconSvg.setAttribute('fill', 'none');
            }
        }

        if (countSpan) {
            countSpan.textContent = `${data.likes_count} like${data.likes_count === 1 ? '' : 's'}`;
        }
    } catch (error) {
        console.error("Like error:", error);
        showToast("Could not update like", "error");
    }
}

// Double tap media to like
function setupDoubleTapLike(mediaBox, postId) {
    let lastTap = 0;
    mediaBox.addEventListener('click', (e) => {
        const currentTime = new Date().getTime();
        const tapLength = currentTime - lastTap;
        if (tapLength < 350 && tapLength > 0) {
            // Trigger heart burst
            const heartBurst = mediaBox.querySelector('.heart-burst');
            if (heartBurst) {
                heartBurst.classList.add('animate');
                setTimeout(() => heartBurst.classList.remove('animate'), 600);
            }
            // Trigger like
            const likeBtn = document.querySelector(`.action-btn-like[data-post-id="${postId}"]`);
            if (likeBtn && !likeBtn.classList.contains('liked')) {
                toggleLike(postId, likeBtn);
            }
            e.preventDefault();
        }
        lastTap = currentTime;
    });
}

// Save / Bookmark Post
async function toggleSave(postId, btnElement) {
    try {
        const response = await fetch(`/api/posts/${postId}/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) throw new Error("Failed to toggle save");
        const data = await response.json();

        const iconSvg = btnElement.querySelector('svg');
        if (data.saved) {
            btnElement.classList.add('saved');
            if (iconSvg) iconSvg.setAttribute('fill', 'currentColor');
            showToast("Saved to your collection", "info");
        } else {
            btnElement.classList.remove('saved');
            if (iconSvg) iconSvg.setAttribute('fill', 'none');
            showToast("Removed from saved posts", "info");
        }
    } catch (error) {
        console.error("Save error:", error);
        showToast("Could not save post", "error");
    }
}

// Submit Comment via AJAX
async function handleCommentSubmit(event, postId) {
    event.preventDefault();
    const form = event.target;
    const input = form.querySelector('.comment-input');
    const text = input.value.trim();

    if (!text) return;

    try {
        const response = await fetch(`/api/posts/${postId}/comment`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ comment_text: text })
        });

        if (!response.ok) throw new Error("Failed to post comment");
        const data = await response.json();

        input.value = '';

        // Update comment counter
        const countSpan = document.getElementById(`comments-count-${postId}`);
        if (countSpan) {
            countSpan.textContent = `${data.comments_count} comment${data.comments_count === 1 ? '' : 's'}`;
        }

        // Prepend / append to comment list if container exists
        const previewList = document.getElementById(`preview-comments-${postId}`);
        if (previewList) {
            const commentItem = document.createElement('div');
            commentItem.className = 'preview-comment-item';
            commentItem.id = `comment-${data.comment.id}`;
            commentItem.innerHTML = `
                <div>
                    <a href="/profile/${data.comment.user.username}" class="comment-author-name">${data.comment.user.username}</a>
                    <span>${escapeHtml(data.comment.comment_text)}</span>
                </div>
                <button class="comment-delete-btn" onclick="deleteComment(${data.comment.id}, ${postId})">×</button>
            `;
            previewList.appendChild(commentItem);
        }

        const detailList = document.getElementById('detail-comments-list');
        if (detailList) {
            const row = document.createElement('div');
            row.className = 'comment-row';
            row.id = `comment-${data.comment.id}`;
            row.innerHTML = `
                <img src="/uploads/profiles/${data.comment.user.profile_picture}" class="comment-avatar" alt="">
                <div class="comment-bubble">
                    <div style="font-size:0.92rem;">
                        <a href="/profile/${data.comment.user.username}" style="font-weight:700;margin-right:6px;">${data.comment.user.username}</a>
                        ${escapeHtml(data.comment.comment_text)}
                    </div>
                    <div class="comment-meta">
                        <span>just now</span>
                        <button class="comment-delete-btn" onclick="deleteComment(${data.comment.id}, ${postId})">Delete</button>
                    </div>
                </div>
            `;
            detailList.appendChild(row);
            detailList.scrollTop = detailList.scrollHeight;
        }

        showToast("Comment posted!", "success");
    } catch (error) {
        console.error("Comment error:", error);
        showToast("Failed to post comment", "error");
    }
}

// Delete Comment
async function deleteComment(commentId, postId) {
    if (!confirm("Delete this comment?")) return;

    try {
        const response = await fetch(`/api/comments/${commentId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error("Failed to delete comment");
        const data = await response.json();

        const commentEl = document.getElementById(`comment-${commentId}`);
        if (commentEl) commentEl.remove();

        const countSpan = document.getElementById(`comments-count-${postId}`);
        if (countSpan) {
            countSpan.textContent = `${data.comments_count} comment${data.comments_count === 1 ? '' : 's'}`;
        }

        showToast("Comment deleted", "info");
    } catch (error) {
        console.error("Delete comment error:", error);
        showToast("Could not delete comment", "error");
    }
}

// Follow / Unfollow Toggle
async function toggleFollow(userId, btnElement) {
    try {
        const response = await fetch(`/api/users/${userId}/follow`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) throw new Error("Failed to follow/unfollow");
        const data = await response.json();

        if (data.following) {
            btnElement.classList.add('following');
            btnElement.textContent = "Following";
            showToast("Following user", "success");
        } else {
            btnElement.classList.remove('following');
            btnElement.textContent = "Follow";
            showToast("Unfollowed user", "info");
        }

        const followersCountEl = document.getElementById('profile-followers-count');
        if (followersCountEl) {
            followersCountEl.textContent = data.followers_count;
        }
    } catch (error) {
        console.error("Follow error:", error);
        showToast("Could not complete follow action", "error");
    }
}

// Delete Post
async function deletePost(postId) {
    if (!confirm("Are you sure you want to permanently delete this post?")) return;

    try {
        const response = await fetch(`/api/posts/${postId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error("Failed to delete post");

        showToast("Post deleted successfully", "success");
        setTimeout(() => {
            window.location.href = "/";
        }, 800);
    } catch (error) {
        console.error("Delete post error:", error);
        showToast("Could not delete post", "error");
    }
}

// Live Search with Debounce
let searchTimeout = null;
function handleSearchInput(query) {
    clearTimeout(searchTimeout);
    const dropdown = document.getElementById('search-results-dropdown');
    if (!dropdown) return;

    if (!query.trim()) {
        dropdown.classList.remove('active');
        dropdown.innerHTML = '';
        return;
    }

    searchTimeout = setTimeout(async () => {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) return;
            const data = await response.json();

            let html = '';
            if (data.users.length === 0 && data.posts.length === 0) {
                html = '<div style="padding:16px;text-align:center;color:var(--text-dim);">No results found</div>';
            } else {
                if (data.users.length > 0) {
                    html += '<div style="font-size:0.75rem;font-weight:700;color:var(--text-dim);margin-bottom:8px;text-transform:uppercase;">Users</div>';
                    data.users.forEach(u => {
                        html += `
                            <a href="/profile/${u.username}" class="suggestion-item" style="padding:8px 6px;border-radius:8px;display:flex;align-items:center;gap:10px;">
                                <img src="/uploads/profiles/${u.profile_picture}" class="suggestion-avatar" alt="">
                                <div class="suggestion-meta">
                                    <span class="suggestion-name">${u.username}</span>
                                    <span class="suggestion-sub">${u.full_name || ''}</span>
                                </div>
                            </a>
                        `;
                    });
                }
                if (data.posts.length > 0) {
                    html += '<div style="font-size:0.75rem;font-weight:700;color:var(--text-dim);margin:12px 0 8px 0;text-transform:uppercase;">Posts</div>';
                    html += '<div style="display:grid;grid-template-columns:repeat(3, 1fr);gap:8px;">';
                    data.posts.forEach(p => {
                        html += `
                            <a href="/post/${p.id}" style="aspect-ratio:1/1;border-radius:6px;overflow:hidden;background:#000;">
                                <img src="/uploads/posts/${p.media_path}" style="width:100%;height:100%;object-fit:cover;" alt="">
                            </a>
                        `;
                    });
                    html += '</div>';
                }
            }

            dropdown.innerHTML = html;
            dropdown.classList.add('active');
        } catch (err) {
            console.error("Search error:", err);
        }
    }, 250);
}

// Followers / Following Modal
async function openUsersModal(title, endpoint) {
    const modal = document.getElementById('universal-modal');
    const modalTitle = document.getElementById('universal-modal-title');
    const modalBody = document.getElementById('universal-modal-body');

    if (!modal || !modalTitle || !modalBody) return;

    modalTitle.textContent = title;
    modalBody.innerHTML = '<div style="text-align:center;padding:24px;color:var(--text-dim);">Loading...</div>';
    modal.classList.add('active');

    try {
        const res = await fetch(endpoint);
        const data = await res.json();

        if (!data.users || data.users.length === 0) {
            modalBody.innerHTML = '<div style="text-align:center;padding:24px;color:var(--text-dim);">No users found</div>';
            return;
        }

        let html = '<div style="display:flex;flex-direction:column;gap:12px;">';
        data.users.forEach(u => {
            html += `
                <div style="display:flex;align-items:center;justify-content:space-between;">
                    <a href="/profile/${u.username}" style="display:flex;align-items:center;gap:12px;">
                        <img src="/uploads/profiles/${u.profile_picture}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;" alt="">
                        <div>
                            <div style="font-weight:600;font-size:0.9rem;">${u.username}</div>
                            <div style="font-size:0.8rem;color:var(--text-dim);">${u.full_name || ''}</div>
                        </div>
                    </a>
                    <button class="btn-follow ${u.is_following ? 'following' : ''}" onclick="toggleFollow(${u.id}, this)">
                        ${u.is_following ? 'Following' : 'Follow'}
                    </button>
                </div>
            `;
        });
        html += '</div>';
        modalBody.innerHTML = html;
    } catch (e) {
        modalBody.innerHTML = '<div style="text-align:center;padding:24px;color:var(--accent-red);">Failed to load users</div>';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
}

// Background unread badges poller
function pollUnreadBadges() {
    setInterval(async () => {
        try {
            const res = await fetch('/api/notifications/unread-count');
            if (!res.ok) return;
            const data = await res.json();

            // Update notifications badge
            const notifBadges = document.querySelectorAll('.badge-notifications');
            notifBadges.forEach(b => {
                if (data.unread_notifications > 0) {
                    b.textContent = data.unread_notifications;
                    b.style.display = 'inline-block';
                } else {
                    b.style.display = 'none';
                }
            });

            // Update messages badge
            const msgBadges = document.querySelectorAll('.badge-messages');
            msgBadges.forEach(b => {
                if (data.unread_messages > 0) {
                    b.textContent = data.unread_messages;
                    b.style.display = 'inline-block';
                } else {
                    b.style.display = 'none';
                }
            });
        } catch (e) {
            // Silently ignore background poll errors
        }
    }, 15000);
}

// Utility HTML escape
function escapeHtml(string) {
    const entityMap = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
        '/': '&#x2F;'
    };
    return String(string).replace(/[&<>"'\/]/g, s => entityMap[s]);
}

// Initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    // Setup double-taps
    document.querySelectorAll('.post-media-box').forEach(box => {
        const postId = box.getAttribute('data-post-id');
        if (postId) setupDoubleTapLike(box, postId);
    });

    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('search-results-dropdown');
        const searchInput = document.getElementById('search-input');
        if (dropdown && searchInput && !dropdown.contains(e.target) && !searchInput.contains(e.target)) {
            dropdown.classList.remove('active');
        }
    });

    // Start background badge poller
    pollUnreadBadges();
});
