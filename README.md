# Histogram 📸

**Histogram** is a complete, modern, production-quality social media web application inspired by Instagram, crafted with its own original branding, UI design system, and clean codebase.

---

## 🌟 Key Features

1. **Original Visual Identity & Branding**:
   - Camera aperture + spectral frequency histogram emblem.
   - Polished, responsive dark theme with vibrant cyan, indigo, and magenta gradients.
   - Micro-interactions: double-tap heart burst animation, story ring glow, toast alerts.

2. **Full-Featured Authentication**:
   - User registration with validation (username format, email format, password requirements).
   - Secure login with `werkzeug.security` password hashing (passwords are never stored in plain text).
   - Session-based authentication with protected routes (`@login_required`).

3. **Home Feed & Stories**:
   - Top 24-Hour Stories carousel with interactive full-screen story player (progress bars, auto-advance, tap left/right to skip, pause on hold).
   - Dynamic feed prioritizing followed accounts with automatic explore fallback.
   - Like/unlike with real-time counters and heart burst animation.
   - Comments thread with instant AJAX submission and delete permissions.
   - Save / Bookmark posts into personal collections.
   - Native Share button with automatic clipboard copy & toast feedback.

4. **Explore & Search**:
   - Live debounced search across creators, hashtags, and captions.
   - Responsive 3-column media grid with hover stats (likes and comments).

5. **Profiles & Follow System**:
   - Detailed user statistics (posts count, followers, following).
   - Clickable followers and following counters opening interactive modals with quick follow/unfollow actions.
   - Posts Grid tab and private Saved Posts tab for profile owner.
   - Edit Profile page to update avatar, display name, bio, and email.

6. **Direct Messages (DMs)**:
   - Instagram-style split-pane chat interface.
   - Live background polling for real-time messaging without full-page reloads.
   - Message bubbles with timestamps and unread badges.

7. **Activity Notifications**:
   - Notifications for likes, comments, new followers, and direct messages.
   - Live unread badge count poller on desktop sidebar and mobile navigation bar.

8. **Media Handling & Security**:
   - Media validation (MIME types, extensions: JPG, PNG, GIF, WEBP, MP4, WEBM).
   - UUID-based unique filenames stored under `uploads/`.
   - Parameterized SQL queries preventing SQL injection.

---

## 🏗️ Project Structure

```text
histogram/
├── app.py                     # Main Flask application, routes, APIs, and error handlers
├── database.py                # SQLite connection, schema, indexes, and query helpers
├── seed_data.py               # Generates sample creators, posts, stories, comments, & DMs
├── test_histogram.py          # Unit test suite verifying endpoints, auth, and database actions
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
├── histogram.db               # SQLite database (auto-created on startup)
│
├── uploads/                   # Uploaded media storage
│   ├── profiles/              # User avatars
│   ├── posts/                 # Post photos and videos
│   └── stories/               # 24-hour expiring stories
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Core layout (desktop sidebar, mobile bottom bar, modals)
│   ├── login.html             # Login screen with quick demo credentials
│   ├── register.html          # Signup screen
│   ├── home.html              # Stories bar, home feed, and suggestions panel
│   ├── explore.html           # Search bar and explore grid
│   ├── profile.html           # User profile, stats, posts grid, and saved tab
│   ├── post.html              # Single post view with comments thread
│   ├── create.html            # Post uploader with live preview & caption editor
│   ├── messages.html          # Direct messages interface
│   ├── notifications.html     # Notifications activity feed
│   ├── edit_profile.html      # Profile picture and bio editor
│   ├── 404.html               # Custom 404 error page
│   ├── 403.html               # Custom 403 error page
│   └── 500.html               # Custom 500 error page
│
└── static/
    ├── css/
    │   └── style.css          # Custom dark-mode design system & responsive layout
    ├── js/
    │   ├── app.js             # Likes, comments, saves, follows, search, modals, toasts
    │   ├── stories.js         # Full-screen story player with progress bars
    │   └── messages.js        # Direct messages live client
    └── images/
        ├── logo.svg           # Original Histogram vector logo
        └── default_avatar.svg # Default avatar placeholder
```

---

## 🚀 Quick Start Instructions

### 1. Requirements
Ensure Python 3.9+ is installed.

### 2. Install Dependencies
```bash
cd c:\Users\jagan\OneDrive\Desktop\histogram
pip install -r requirements.txt
```

### 3. Initialize & Seed Demo Data (Optional but Recommended)
Populate realistic photography creator accounts, sample posts, stories, comments, and messages:
```bash
python seed_data.py
```

### 4. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 🔑 Demo Accounts

Use any of these pre-configured accounts to test interactions right away:

| Username | Password | Role |
| :--- | :--- | :--- |
| **`elena_lens`** | `password123` | Street & Architecture Photographer |
| **`marcus_shoots`** | `password123` | Cyberpunk & Night Scapes |
| **`aurora_wild`** | `password123` | Nature & Alpine Explorer |
| **`neon_drifter`** | `password123` | Visual Artist & Synthwave |
| **`sophia_vibe`** | `password123` | Studio Portraits & 35mm Film |

*Or register a new account directly from the signup page!*

---

## 🧪 Running Automated Tests

A comprehensive unit test suite is included to verify database schema, registration, password hashing, post creation, like toggles, comment deletion, story expiration, and DMs:
```bash
python test_histogram.py
```
