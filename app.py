import os
import uuid
import re
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import database

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'histogram-secure-dev-secret-key-9921')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

# Ensure database and upload directories exist
database.init_db()
for sub in ['profiles', 'posts', 'stories']:
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], sub), exist_ok=True)

# ----------------- Utility & Helper Functions -----------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_media_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in ALLOWED_VIDEO_EXTENSIONS:
        return 'video'
    return 'image'

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return database.query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.template_filter('timeago')
def timeago_filter(dt_str):
    if not dt_str:
        return ""
    try:
        # SQLite CURRENT_TIMESTAMP returns YYYY-MM-DD HH:MM:SS
        if isinstance(dt_str, datetime):
            dt = dt_str
        else:
            dt = datetime.strptime(str(dt_str).split('.')[0], "%Y-%m-%d %H:%M:%S")
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        diff = now - dt
        seconds = int(diff.total_seconds())

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            m = seconds // 60
            return f"{m}m ago"
        elif seconds < 86400:
            h = seconds // 3600
            return f"{h}h ago"
        elif seconds < 604800:
            d = seconds // 86400
            return f"{d}d ago"
        else:
            w = seconds // 604800
            return f"{w}w ago"
    except Exception:
        return str(dt_str)

@app.context_processor
def inject_global_context():
    current_user = get_current_user()
    unread_notifications = 0
    unread_messages = 0
    if current_user:
        n_row = database.query_db(
            "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0",
            (current_user['id'],), one=True
        )
        unread_notifications = n_row['cnt'] if n_row else 0

        m_row = database.query_db(
            "SELECT COUNT(*) as cnt FROM messages WHERE receiver_id = ? AND is_read = 0",
            (current_user['id'],), one=True
        )
        unread_messages = m_row['cnt'] if m_row else 0

    return {
        'current_user': current_user,
        'unread_notifications_count': unread_notifications,
        'unread_messages_count': unread_messages,
        'now_year': datetime.now().year
    }

# ----------------- Media Serving -----------------

@app.route('/uploads/<folder>/<filename>')
def serve_upload(folder, filename):
    if folder not in ['profiles', 'posts', 'stories']:
        abort(404)
    target_dir = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    return send_from_directory(target_dir, filename)

# ----------------- Authentication Routes -----------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')

        # Validations
        if not username or not email or not password:
            flash("All required fields must be filled out.", "error")
            return render_template('register.html', username=username, email=email, full_name=full_name)

        if not re.match(r'^[a-zA-Z0-9_]{3,25}$', username):
            flash("Username must be 3-25 characters and contain only letters, numbers, and underscores.", "error")
            return render_template('register.html', username=username, email=email, full_name=full_name)

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            flash("Please enter a valid email address.", "error")
            return render_template('register.html', username=username, email=email, full_name=full_name)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template('register.html', username=username, email=email, full_name=full_name)

        # Check duplicates
        existing_user = database.query_db("SELECT id FROM users WHERE username = ?", (username,), one=True)
        if existing_user:
            flash("Username is already taken. Please pick another one.", "error")
            return render_template('register.html', username=username, email=email, full_name=full_name)

        existing_email = database.query_db("SELECT id FROM users WHERE email = ?", (email,), one=True)
        if existing_email:
            flash("An account with this email already exists.", "error")
            return render_template('register.html', username=username, email=email, full_name=full_name)

        hashed_password = generate_password_hash(password)
        new_id = database.execute_db(
            "INSERT INTO users (username, email, password_hash, full_name) VALUES (?, ?, ?, ?)",
            (username, email, hashed_password, full_name)
        )

        session['user_id'] = new_id
        flash(f"Welcome to Histogram, @{username}!", "success")
        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        login_input = request.form.get('login_input', '').strip().lower()
        password = request.form.get('password', '')

        if not login_input or not password:
            flash("Please enter both username/email and password.", "error")
            return render_template('login.html', login_input=login_input)

        user = database.query_db(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (login_input, login_input), one=True
        )

        if not user or not check_password_hash(user['password_hash'], password):
            flash("Invalid username/email or password.", "error")
            return render_template('login.html', login_input=login_input)

        session['user_id'] = user['id']
        flash(f"Welcome back, @{user['username']}!", "success")
        next_url = request.args.get('next')
        return redirect(next_url or url_for('home'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('login'))

# ----------------- Home Feed & Stories -----------------

@app.route('/')
@login_required
def home():
    current_user = get_current_user()
    user_id = current_user['id']

    # 1. Active Stories query (24-hour expiration)
    # Get users who have active stories and who the current user follows or is self
    stories_raw = database.query_db("""
        SELECT s.*, u.username, u.full_name, u.profile_picture
        FROM stories s
        JOIN users u ON s.user_id = u.id
        WHERE s.expires_at > CURRENT_TIMESTAMP
        ORDER BY s.created_at ASC
    """)

    # Group stories by user for the stories carousel
    stories_by_user = {}
    for st in stories_raw:
        u_name = st['username']
        if u_name not in stories_by_user:
            stories_by_user[u_name] = {
                'user_id': st['user_id'],
                'username': st['username'],
                'full_name': st['full_name'],
                'profile_picture': st['profile_picture'],
                'stories': []
            }
        stories_by_user[u_name]['stories'].append(dict(st))

    # 2. Feed Posts Query:
    # Prioritizes posts from users being followed + own posts.
    # If total followed posts is small (< 5), includes recent explore posts so feed is vibrant.
    posts_raw = database.query_db("""
        SELECT p.*, u.username, u.full_name, u.profile_picture,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) AS likes_count,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) AS comments_count,
               EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND user_id = ?) AS is_liked,
               EXISTS(SELECT 1 FROM saved_posts WHERE post_id = p.id AND user_id = ?) AS is_saved
        FROM posts p
        JOIN users u ON p.user_id = u.id
        WHERE p.user_id = ? 
           OR p.user_id IN (SELECT following_id FROM followers WHERE follower_id = ?)
        ORDER BY p.created_at DESC
        LIMIT 30
    """, (user_id, user_id, user_id, user_id))

    # If followed feed is empty or very short, grab popular/recent posts
    posts = [dict(p) for p in posts_raw]
    if len(posts) < 5:
        existing_ids = [p['id'] for p in posts]
        placeholders = f"({','.join('?' for _ in existing_ids)})" if existing_ids else "(-1)"
        supplement_query = f"""
            SELECT p.*, u.username, u.full_name, u.profile_picture,
                   (SELECT COUNT(*) FROM likes WHERE post_id = p.id) AS likes_count,
                   (SELECT COUNT(*) FROM comments WHERE post_id = p.id) AS comments_count,
                   EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND user_id = ?) AS is_liked,
                   EXISTS(SELECT 1 FROM saved_posts WHERE post_id = p.id AND user_id = ?) AS is_saved
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.id NOT IN {placeholders}
            ORDER BY p.created_at DESC
            LIMIT ?
        """
        extra_args = [user_id, user_id] + existing_ids + [30 - len(posts)]
        extra_posts = database.query_db(supplement_query, extra_args)
        posts.extend([dict(p) for p in extra_posts])

    # Fetch top 2 preview comments for each post
    for post in posts:
        comments = database.query_db("""
            SELECT c.*, u.username, u.profile_picture
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id = ?
            ORDER BY c.created_at ASC
            LIMIT 2
        """, (post['id'],))
        post['preview_comments'] = [dict(c) for c in comments]

    # 3. Suggested Users to follow
    suggested_users = database.query_db("""
        SELECT u.id, u.username, u.full_name, u.profile_picture,
               (SELECT COUNT(*) FROM followers WHERE following_id = u.id) as followers_count
        FROM users u
        WHERE u.id != ?
          AND u.id NOT IN (SELECT following_id FROM followers WHERE follower_id = ?)
        ORDER BY followers_count DESC, u.created_at DESC
        LIMIT 5
    """, (user_id, user_id))

    return render_template(
        'home.html',
        stories_by_user=stories_by_user,
        posts=posts,
        suggested_users=suggested_users
    )

# ----------------- Create Post & Stories -----------------

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    current_user = get_current_user()

    if request.method == 'POST':
        caption = request.form.get('caption', '').strip()
        file = request.files.get('media')

        if not file or file.filename == '':
            flash("Please select an image or video to upload.", "error")
            return render_template('create.html', caption=caption)

        if not allowed_file(file.filename):
            flash("Invalid file format. Supported formats: JPG, PNG, GIF, WEBP, MP4, WEBM, MOV.", "error")
            return render_template('create.html', caption=caption)

        ext = file.filename.rsplit('.', 1)[1].lower()
        media_type = get_media_type(file.filename)
        unique_filename = f"post_{uuid.uuid4().hex[:12]}.{ext}"
        destination = os.path.join(app.config['UPLOAD_FOLDER'], 'posts', unique_filename)

        file.save(destination)

        # Insert post record
        post_id = database.execute_db(
            "INSERT INTO posts (user_id, media_path, media_type, caption) VALUES (?, ?, ?, ?)",
            (current_user['id'], unique_filename, media_type, caption)
        )

        flash("Post published successfully!", "success")
        return redirect(url_for('view_post', post_id=post_id))

    return render_template('create.html')

@app.route('/api/stories/create', methods=['POST'])
@login_required
def create_story():
    current_user = get_current_user()
    file = request.files.get('media')

    if not file or file.filename == '':
        return jsonify({'error': 'No media file provided'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file format'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    media_type = get_media_type(file.filename)
    unique_filename = f"story_{uuid.uuid4().hex[:12]}.{ext}"
    destination = os.path.join(app.config['UPLOAD_FOLDER'], 'stories', unique_filename)

    file.save(destination)

    # Expires in 24 hours
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    story_id = database.execute_db(
        "INSERT INTO stories (user_id, media_path, media_type, expires_at) VALUES (?, ?, ?, ?)",
        (current_user['id'], unique_filename, media_type, expires_at)
    )

    return jsonify({
        'success': True,
        'story_id': story_id,
        'media_path': unique_filename,
        'media_type': media_type,
        'expires_at': expires_at
    })

@app.route('/api/stories/<username>')
@login_required
def get_user_stories(username):
    user = database.query_db("SELECT id, username, profile_picture, full_name FROM users WHERE username = ?", (username,), one=True)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    stories = database.query_db("""
        SELECT id, media_path, media_type, created_at, expires_at
        FROM stories
        WHERE user_id = ? AND expires_at > CURRENT_TIMESTAMP
        ORDER BY created_at ASC
    """, (user['id'],))

    return jsonify({
        'user': dict(user),
        'stories': [dict(s) for s in stories]
    })

# ----------------- Post View & Details -----------------

@app.route('/post/<int:post_id>')
def view_post(post_id):
    current_user = get_current_user()
    user_id = current_user['id'] if current_user else 0

    post = database.query_db("""
        SELECT p.*, u.username, u.full_name, u.profile_picture,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) AS likes_count,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) AS comments_count,
               EXISTS(SELECT 1 FROM likes WHERE post_id = p.id AND user_id = ?) AS is_liked,
               EXISTS(SELECT 1 FROM saved_posts WHERE post_id = p.id AND user_id = ?) AS is_saved
        FROM posts p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = ?
    """, (user_id, user_id, post_id), one=True)

    if not post:
        abort(404)

    comments = database.query_db("""
        SELECT c.*, u.username, u.profile_picture
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.post_id = ?
        ORDER BY c.created_at ASC
    """, (post_id,))

    return render_template('post.html', post=dict(post), comments=[dict(c) for c in comments])

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    current_user = get_current_user()
    post = database.query_db("SELECT * FROM posts WHERE id = ?", (post_id,), one=True)

    if not post:
        return jsonify({'error': 'Post not found'}), 404

    if post['user_id'] != current_user['id']:
        return jsonify({'error': 'Unauthorized'}), 403

    # Remove media file
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'posts', post['media_path'])
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error removing post file: {e}")

    database.execute_db("DELETE FROM posts WHERE id = ?", (post_id,))
    return jsonify({'success': True})

# ----------------- Interactions (Likes, Comments, Saves) -----------------

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    current_user = get_current_user()
    user_id = current_user['id']

    post = database.query_db("SELECT id, user_id FROM posts WHERE id = ?", (post_id,), one=True)
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    existing_like = database.query_db(
        "SELECT id FROM likes WHERE user_id = ? AND post_id = ?",
        (user_id, post_id), one=True
    )

    if existing_like:
        database.execute_db("DELETE FROM likes WHERE user_id = ? AND post_id = ?", (user_id, post_id))
        liked = False
    else:
        database.execute_db("INSERT INTO likes (user_id, post_id) VALUES (?, ?)", (user_id, post_id))
        liked = True

        # Send notification to post author if not self
        if post['user_id'] != user_id:
            database.execute_db("""
                INSERT INTO notifications (user_id, actor_id, notification_type, post_id, is_read)
                VALUES (?, ?, 'like', ?, 0)
            """, (post['user_id'], user_id, post_id))

    count_row = database.query_db(
        "SELECT COUNT(*) as count FROM likes WHERE post_id = ?",
        (post_id,), one=True
    )

    return jsonify({
        'liked': liked,
        'likes_count': count_row['count']
    })

@app.route('/api/posts/<int:post_id>/save', methods=['POST'])
@login_required
def toggle_save(post_id):
    current_user = get_current_user()
    user_id = current_user['id']

    post = database.query_db("SELECT id FROM posts WHERE id = ?", (post_id,), one=True)
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    existing_save = database.query_db(
        "SELECT id FROM saved_posts WHERE user_id = ? AND post_id = ?",
        (user_id, post_id), one=True
    )

    if existing_save:
        database.execute_db("DELETE FROM saved_posts WHERE user_id = ? AND post_id = ?", (user_id, post_id))
        saved = False
    else:
        database.execute_db("INSERT INTO saved_posts (user_id, post_id) VALUES (?, ?)", (user_id, post_id))
        saved = True

    return jsonify({'saved': saved})

@app.route('/api/posts/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    current_user = get_current_user()
    data = request.get_json() or {}
    text = data.get('comment_text', '').strip()

    if not text:
        return jsonify({'error': 'Comment text cannot be empty'}), 400

    post = database.query_db("SELECT id, user_id FROM posts WHERE id = ?", (post_id,), one=True)
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    comment_id = database.execute_db(
        "INSERT INTO comments (user_id, post_id, comment_text) VALUES (?, ?, ?)",
        (current_user['id'], post_id, text)
    )

    # Notify author if not self
    if post['user_id'] != current_user['id']:
        database.execute_db("""
            INSERT INTO notifications (user_id, actor_id, notification_type, post_id, is_read)
            VALUES (?, ?, 'comment', ?, 0)
        """, (post['user_id'], current_user['id'], post_id))

    count_row = database.query_db(
        "SELECT COUNT(*) as count FROM comments WHERE post_id = ?",
        (post_id,), one=True
    )

    return jsonify({
        'success': True,
        'comment': {
            'id': comment_id,
            'comment_text': text,
            'created_at': 'just now',
            'user': {
                'id': current_user['id'],
                'username': current_user['username'],
                'profile_picture': current_user['profile_picture']
            }
        },
        'comments_count': count_row['count']
    })

@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    current_user = get_current_user()
    comment = database.query_db("""
        SELECT c.*, p.user_id as post_author_id
        FROM comments c
        JOIN posts p ON c.post_id = p.id
        WHERE c.id = ?
    """, (comment_id,), one=True)

    if not comment:
        return jsonify({'error': 'Comment not found'}), 404

    # Allow comment author OR post author to delete
    if comment['user_id'] != current_user['id'] and comment['post_author_id'] != current_user['id']:
        return jsonify({'error': 'Unauthorized'}), 403

    post_id = comment['post_id']
    database.execute_db("DELETE FROM comments WHERE id = ?", (comment_id,))

    count_row = database.query_db(
        "SELECT COUNT(*) as count FROM comments WHERE post_id = ?",
        (post_id,), one=True
    )

    return jsonify({
        'success': True,
        'comments_count': count_row['count']
    })

# ----------------- Explore & Search -----------------

@app.route('/explore')
def explore():
    current_user = get_current_user()
    user_id = current_user['id'] if current_user else 0

    posts = database.query_db("""
        SELECT p.*, u.username, u.profile_picture,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) AS likes_count,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) AS comments_count
        FROM posts p
        JOIN users u ON p.user_id = u.id
        ORDER BY likes_count DESC, p.created_at DESC
        LIMIT 60
    """)

    return render_template('explore.html', posts=[dict(p) for p in posts])

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'users': [], 'posts': []})

    wildcard = f"%{q}%"
    users = database.query_db("""
        SELECT id, username, full_name, profile_picture, bio,
               (SELECT COUNT(*) FROM followers WHERE following_id = users.id) as followers_count
        FROM users
        WHERE username LIKE ? OR full_name LIKE ?
        LIMIT 10
    """, (wildcard, wildcard))

    posts = database.query_db("""
        SELECT p.id, p.media_path, p.media_type, p.caption, u.username,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) AS likes_count
        FROM posts p
        JOIN users u ON p.user_id = u.id
        WHERE p.caption LIKE ?
        LIMIT 12
    """, (wildcard,))

    return jsonify({
        'users': [dict(u) for u in users],
        'posts': [dict(p) for p in posts]
    })

# ----------------- User Profiles & Follow System -----------------

@app.route('/profile/<username>')
def profile(username):
    current_user = get_current_user()
    current_user_id = current_user['id'] if current_user else 0

    profile_user = database.query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
    if not profile_user:
        abort(404)

    is_self = (current_user and current_user['id'] == profile_user['id'])

    # Counts
    posts_count = database.query_db(
        "SELECT COUNT(*) as count FROM posts WHERE user_id = ?",
        (profile_user['id'],), one=True
    )['count']

    followers_count = database.query_db(
        "SELECT COUNT(*) as count FROM followers WHERE following_id = ?",
        (profile_user['id'],), one=True
    )['count']

    following_count = database.query_db(
        "SELECT COUNT(*) as count FROM followers WHERE follower_id = ?",
        (profile_user['id'],), one=True
    )['count']

    is_following = False
    if current_user and not is_self:
        f_row = database.query_db(
            "SELECT 1 FROM followers WHERE follower_id = ? AND following_id = ?",
            (current_user['id'], profile_user['id']), one=True
        )
        is_following = bool(f_row)

    # Posts
    user_posts = database.query_db("""
        SELECT p.*,
               (SELECT COUNT(*) FROM likes WHERE post_id = p.id) AS likes_count,
               (SELECT COUNT(*) FROM comments WHERE post_id = p.id) AS comments_count
        FROM posts p
        WHERE p.user_id = ?
        ORDER BY p.created_at DESC
    """, (profile_user['id'],))

    # Saved Posts (only for self)
    saved_posts = []
    if is_self:
        saved_posts = database.query_db("""
            SELECT p.*, u.username,
                   (SELECT COUNT(*) FROM likes WHERE post_id = p.id) AS likes_count,
                   (SELECT COUNT(*) FROM comments WHERE post_id = p.id) AS comments_count
            FROM saved_posts sp
            JOIN posts p ON sp.post_id = p.id
            JOIN users u ON p.user_id = u.id
            WHERE sp.user_id = ?
            ORDER BY sp.created_at DESC
        """, (current_user['id'],))

    # Check active stories
    has_active_story = database.query_db("""
        SELECT 1 FROM stories WHERE user_id = ? AND expires_at > CURRENT_TIMESTAMP LIMIT 1
    """, (profile_user['id'],), one=True)

    return render_template(
        'profile.html',
        profile_user=dict(profile_user),
        is_self=is_self,
        is_following=is_following,
        posts_count=posts_count,
        followers_count=followers_count,
        following_count=following_count,
        posts=[dict(p) for p in user_posts],
        saved_posts=[dict(p) for p in saved_posts],
        has_active_story=bool(has_active_story)
    )

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    current_user = get_current_user()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        bio = request.form.get('bio', '').strip()
        email = request.form.get('email', '').strip().lower()
        file = request.files.get('profile_picture')

        if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            flash("Please enter a valid email address.", "error")
            return render_template('edit_profile.html', user=current_user)

        # Check duplicate email if changed
        if email != current_user['email']:
            dup = database.query_db("SELECT id FROM users WHERE email = ? AND id != ?", (email, current_user['id']), one=True)
            if dup:
                flash("This email is already associated with another account.", "error")
                return render_template('edit_profile.html', user=current_user)

        profile_pic_name = current_user['profile_picture']
        if file and file.filename != '':
            if allowed_file(file.filename) and get_media_type(file.filename) == 'image':
                ext = file.filename.rsplit('.', 1)[1].lower()
                profile_pic_name = f"avatar_{current_user['id']}_{uuid.uuid4().hex[:8]}.{ext}"
                dest = os.path.join(app.config['UPLOAD_FOLDER'], 'profiles', profile_pic_name)
                file.save(dest)
            else:
                flash("Invalid profile image format.", "error")
                return render_template('edit_profile.html', user=current_user)

        database.execute_db("""
            UPDATE users SET full_name = ?, bio = ?, email = ?, profile_picture = ?
            WHERE id = ?
        """, (full_name, bio, email, profile_pic_name, current_user['id']))

        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile', username=current_user['username']))

    return render_template('edit_profile.html', user=current_user)

@app.route('/api/users/<int:target_user_id>/follow', methods=['POST'])
@login_required
def toggle_follow(target_user_id):
    current_user = get_current_user()
    follower_id = current_user['id']

    if follower_id == target_user_id:
        return jsonify({'error': 'You cannot follow yourself'}), 400

    target = database.query_db("SELECT id, username FROM users WHERE id = ?", (target_user_id,), one=True)
    if not target:
        return jsonify({'error': 'User not found'}), 404

    existing = database.query_db(
        "SELECT id FROM followers WHERE follower_id = ? AND following_id = ?",
        (follower_id, target_user_id), one=True
    )

    if existing:
        database.execute_db(
            "DELETE FROM followers WHERE follower_id = ? AND following_id = ?",
            (follower_id, target_user_id)
        )
        following = False
    else:
        database.execute_db(
            "INSERT INTO followers (follower_id, following_id) VALUES (?, ?)",
            (follower_id, target_user_id)
        )
        following = True

        # Notification for follow
        database.execute_db("""
            INSERT INTO notifications (user_id, actor_id, notification_type, is_read)
            VALUES (?, ?, 'follow', 0)
        """, (target_user_id, follower_id))

    count_row = database.query_db(
        "SELECT COUNT(*) as count FROM followers WHERE following_id = ?",
        (target_user_id,), one=True
    )

    return jsonify({
        'following': following,
        'followers_count': count_row['count']
    })

@app.route('/api/users/<int:user_id>/followers')
@login_required
def get_followers(user_id):
    current_user = get_current_user()
    followers = database.query_db("""
        SELECT u.id, u.username, u.full_name, u.profile_picture,
               EXISTS(SELECT 1 FROM followers WHERE follower_id = ? AND following_id = u.id) AS is_following
        FROM followers f
        JOIN users u ON f.follower_id = u.id
        WHERE f.following_id = ?
        ORDER BY f.created_at DESC
    """, (current_user['id'], user_id))

    return jsonify({'users': [dict(u) for u in followers]})

@app.route('/api/users/<int:user_id>/following')
@login_required
def get_following(user_id):
    current_user = get_current_user()
    following = database.query_db("""
        SELECT u.id, u.username, u.full_name, u.profile_picture,
               EXISTS(SELECT 1 FROM followers WHERE follower_id = ? AND following_id = u.id) AS is_following
        FROM followers f
        JOIN users u ON f.following_id = u.id
        WHERE f.follower_id = ?
        ORDER BY f.created_at DESC
    """, (current_user['id'], user_id))

    return jsonify({'users': [dict(u) for u in following]})

# ----------------- Direct Messages -----------------

@app.route('/messages')
@app.route('/messages/<username>')
@login_required
def messages_page(username=None):
    current_user = get_current_user()
    user_id = current_user['id']

    # Get conversation list (all users current_user has exchanged messages with)
    conversations = database.query_db("""
        SELECT 
            u.id, u.username, u.full_name, u.profile_picture,
            m.message AS last_message,
            m.created_at AS last_message_time,
            m.sender_id AS last_sender_id,
            (SELECT COUNT(*) FROM messages 
             WHERE sender_id = u.id AND receiver_id = ? AND is_read = 0) AS unread_count
        FROM users u
        JOIN messages m ON m.id = (
            SELECT id FROM messages
            WHERE (sender_id = ? AND receiver_id = u.id)
               OR (sender_id = u.id AND receiver_id = ?)
            ORDER BY created_at DESC LIMIT 1
        )
        WHERE u.id != ?
        ORDER BY m.created_at DESC
    """, (user_id, user_id, user_id, user_id))

    active_user = None
    if username:
        active_user = database.query_db("SELECT id, username, full_name, profile_picture FROM users WHERE username = ?", (username,), one=True)
        if active_user and active_user['id'] != user_id:
            # Mark incoming messages from active_user as read
            database.execute_db("""
                UPDATE messages SET is_read = 1 
                WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
            """, (active_user['id'], user_id))

    return render_template(
        'messages.html',
        conversations=[dict(c) for c in conversations],
        active_user=dict(active_user) if active_user else None
    )

@app.route('/api/messages/<username>')
@login_required
def get_chat_history(username):
    current_user = get_current_user()
    target_user = database.query_db("SELECT id, username, full_name, profile_picture FROM users WHERE username = ?", (username,), one=True)

    if not target_user:
        return jsonify({'error': 'User not found'}), 404

    user_id = current_user['id']
    target_id = target_user['id']

    # Mark as read
    database.execute_db("""
        UPDATE messages SET is_read = 1
        WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
    """, (target_id, user_id))

    chat_messages = database.query_db("""
        SELECT m.*, 
               CASE WHEN m.sender_id = ? THEN 1 ELSE 0 END AS is_mine
        FROM messages m
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.created_at ASC
    """, (user_id, user_id, target_id, target_id, user_id))

    return jsonify({
        'target_user': dict(target_user),
        'messages': [dict(m) for m in chat_messages]
    })

@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    current_user = get_current_user()
    data = request.get_json() or {}
    receiver_username = data.get('receiver_username', '').strip()
    message_text = data.get('message', '').strip()

    if not receiver_username or not message_text:
        return jsonify({'error': 'Recipient and message cannot be empty'}), 400

    receiver = database.query_db("SELECT id, username FROM users WHERE username = ?", (receiver_username,), one=True)
    if not receiver:
        return jsonify({'error': 'Recipient user not found'}), 404

    if receiver['id'] == current_user['id']:
        return jsonify({'error': 'Cannot send message to yourself'}), 400

    msg_id = database.execute_db(
        "INSERT INTO messages (sender_id, receiver_id, message, is_read) VALUES (?, ?, ?, 0)",
        (current_user['id'], receiver['id'], message_text)
    )

    # Insert notification for message
    database.execute_db("""
        INSERT INTO notifications (user_id, actor_id, notification_type, is_read)
        VALUES (?, ?, 'message', 0)
    """, (receiver['id'], current_user['id']))

    return jsonify({
        'success': True,
        'message': {
            'id': msg_id,
            'sender_id': current_user['id'],
            'receiver_id': receiver['id'],
            'message': message_text,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'is_mine': 1
        }
    })

# ----------------- Notifications -----------------

@app.route('/notifications')
@login_required
def notifications_page():
    current_user = get_current_user()
    user_id = current_user['id']

    notifs = database.query_db("""
        SELECT n.*, u.username as actor_username, u.full_name as actor_name, u.profile_picture as actor_avatar,
               p.media_path as post_media, p.media_type as post_media_type
        FROM notifications n
        JOIN users u ON n.actor_id = u.id
        LEFT JOIN posts p ON n.post_id = p.id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC
        LIMIT 50
    """, (user_id,))

    # Mark all notifications as read upon visit
    database.execute_db("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))

    return render_template('notifications.html', notifications=[dict(n) for n in notifs])

@app.route('/api/notifications/unread-count')
def get_unread_count():
    current_user = get_current_user()
    if not current_user:
        return jsonify({'count': 0, 'unread_messages': 0})

    n_row = database.query_db(
        "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0",
        (current_user['id'],), one=True
    )
    m_row = database.query_db(
        "SELECT COUNT(*) as cnt FROM messages WHERE receiver_id = ? AND is_read = 0",
        (current_user['id'],), one=True
    )

    return jsonify({
        'unread_notifications': n_row['cnt'] if n_row else 0,
        'unread_messages': m_row['cnt'] if m_row else 0
    })

# ----------------- Error Handlers -----------------

@app.errorhandler(404)
def not_found_error(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden_error(e):
    return render_template('403.html'), 403

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
