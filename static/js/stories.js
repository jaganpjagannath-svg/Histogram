/**
 * Histogram - Stories Viewer & Creator
 * Handles full-screen story playback, progress timers, and story uploading.
 */

let currentStories = [];
let currentStoryIndex = 0;
let storyTimer = null;
let storyProgressInterval = null;
let storyStartTime = 0;
let storyPausedAt = 0;
let isStoryPaused = false;
const STORY_DURATION = 5000; // 5 seconds per story

// Open Story Player
async function openStoryViewer(username) {
    try {
        const response = await fetch(`/api/stories/${username}`);
        if (!response.ok) throw new Error("Could not load stories");
        const data = await response.json();

        if (!data.stories || data.stories.length === 0) {
            showToast("No active stories available", "info");
            return;
        }

        currentStories = data.stories;
        currentStoryIndex = 0;

        // Setup Player Modal UI
        const modal = document.getElementById('story-player-modal');
        const userAvatar = document.getElementById('story-player-avatar');
        const userName = document.getElementById('story-player-username');
        const progressContainer = document.getElementById('story-progress-container');

        userAvatar.src = `/uploads/profiles/${data.user.profile_picture}`;
        userName.textContent = data.user.username;
        userName.href = `/profile/${data.user.username}`;

        // Build Progress Bar Segments
        progressContainer.innerHTML = '';
        currentStories.forEach((_, idx) => {
            const seg = document.createElement('div');
            seg.className = 'story-progress-segment';
            seg.innerHTML = `<div class="story-progress-fill" id="story-fill-${idx}"></div>`;
            progressContainer.appendChild(seg);
        });

        modal.classList.add('active');
        playStory(0);
    } catch (err) {
        console.error("Story load error:", err);
        showToast("Unable to open story", "error");
    }
}

// Play Story at Index
function playStory(index) {
    if (index < 0 || index >= currentStories.length) {
        closeStoryViewer();
        return;
    }

    currentStoryIndex = index;
    const story = currentStories[index];
    const mediaContainer = document.getElementById('story-media-render');
    const timeLabel = document.getElementById('story-player-time');

    // Update time
    if (timeLabel && story.created_at) {
        timeLabel.textContent = formatStoryTime(story.created_at);
    }

    // Clear previous timer & intervals
    clearStoryTimers();

    // Render Media (Image or Video)
    mediaContainer.innerHTML = '';
    if (story.media_type === 'video') {
        const video = document.createElement('video');
        video.src = `/uploads/stories/${story.media_path}`;
        video.autoplay = true;
        video.playsInline = true;
        video.muted = false;
        video.style.maxWidth = '100%';
        video.style.maxHeight = '100%';
        video.style.objectFit = 'contain';
        mediaContainer.appendChild(video);

        video.onloadedmetadata = () => {
            const duration = Math.max(video.duration * 1000, STORY_DURATION);
            startStoryProgress(duration);
        };
        video.onended = () => {
            nextStory();
        };
    } else {
        const img = document.createElement('img');
        img.src = `/uploads/stories/${story.media_path}`;
        img.style.maxWidth = '100%';
        img.style.maxHeight = '100%';
        img.style.objectFit = 'contain';
        mediaContainer.appendChild(img);
        startStoryProgress(STORY_DURATION);
    }

    // Update Progress Bars fill
    currentStories.forEach((_, idx) => {
        const fill = document.getElementById(`story-fill-${idx}`);
        if (fill) {
            if (idx < currentStoryIndex) {
                fill.style.width = '100%';
            } else if (idx > currentStoryIndex) {
                fill.style.width = '0%';
            }
        }
    });
}

function startStoryProgress(duration) {
    const fill = document.getElementById(`story-fill-${currentStoryIndex}`);
    if (!fill) return;

    storyStartTime = Date.now();
    let elapsed = 0;

    storyProgressInterval = setInterval(() => {
        if (isStoryPaused) return;

        elapsed = Date.now() - storyStartTime;
        const pct = Math.min((elapsed / duration) * 100, 100);
        fill.style.width = `${pct}%`;

        if (pct >= 100) {
            clearInterval(storyProgressInterval);
            nextStory();
        }
    }, 40);
}

function clearStoryTimers() {
    if (storyProgressInterval) {
        clearInterval(storyProgressInterval);
        storyProgressInterval = null;
    }
}

function nextStory() {
    if (currentStoryIndex + 1 < currentStories.length) {
        playStory(currentStoryIndex + 1);
    } else {
        closeStoryViewer();
    }
}

function prevStory() {
    if (currentStoryIndex > 0) {
        playStory(currentStoryIndex - 1);
    } else {
        playStory(0);
    }
}

function pauseStory() {
    isStoryPaused = true;
    const mediaContainer = document.getElementById('story-media-render');
    const video = mediaContainer.querySelector('video');
    if (video) video.pause();
}

function resumeStory() {
    if (!isStoryPaused) return;
    isStoryPaused = false;
    const mediaContainer = document.getElementById('story-media-render');
    const video = mediaContainer.querySelector('video');
    if (video) video.play();
}

function closeStoryViewer() {
    clearStoryTimers();
    currentStories = [];
    currentStoryIndex = 0;
    const modal = document.getElementById('story-player-modal');
    if (modal) modal.classList.remove('active');
    const mediaContainer = document.getElementById('story-media-render');
    if (mediaContainer) mediaContainer.innerHTML = '';
}

function formatStoryTime(dateStr) {
    try {
        const dt = new Date(dateStr.replace(' ', 'T') + 'Z');
        const diff = Math.floor((new Date() - dt) / 1000);
        if (diff < 3600) return `${Math.floor(diff / 60)}m`;
        return `${Math.floor(diff / 3600)}h`;
    } catch (e) {
        return '';
    }
}

// Upload Story Modal Functions
function openCreateStoryModal() {
    const modal = document.getElementById('create-story-modal');
    if (modal) modal.classList.add('active');
}

async function uploadStorySubmit(event) {
    event.preventDefault();
    const fileInput = document.getElementById('story-file-input');
    if (!fileInput.files || fileInput.files.length === 0) {
        showToast("Please choose a photo or video", "error");
        return;
    }

    const formData = new FormData();
    formData.append('media', fileInput.files[0]);

    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading...";

    try {
        const response = await fetch('/api/stories/create', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Upload failed");
        const data = await response.json();

        showToast("Story uploaded successfully!", "success");
        closeModal('create-story-modal');

        // Reload to update stories bar
        setTimeout(() => window.location.reload(), 600);
    } catch (err) {
        console.error("Story upload error:", err);
        showToast("Failed to upload story", "error");
        submitBtn.disabled = false;
        submitBtn.textContent = "Share Story";
    }
}

// Story Viewer keyboard & hold handlers
document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('keydown', (e) => {
        const modal = document.getElementById('story-player-modal');
        if (modal && modal.classList.contains('active')) {
            if (e.key === 'Escape') closeStoryViewer();
            if (e.key === 'ArrowRight') nextStory();
            if (e.key === 'ArrowLeft') prevStory();
        }
    });

    const storyFrame = document.querySelector('.story-frame');
    if (storyFrame) {
        storyFrame.addEventListener('mousedown', pauseStory);
        storyFrame.addEventListener('mouseup', resumeStory);
        storyFrame.addEventListener('touchstart', pauseStory, { passive: true });
        storyFrame.addEventListener('touchend', resumeStory);
    }
});
