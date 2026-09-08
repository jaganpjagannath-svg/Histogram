import os
import random
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
from PIL import Image, ImageDraw, ImageFont
import database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_DIR = os.path.join(BASE_DIR, 'uploads', 'profiles')
POSTS_DIR = os.path.join(BASE_DIR, 'uploads', 'posts')
STORIES_DIR = os.path.join(BASE_DIR, 'uploads', 'stories')

os.makedirs(PROFILES_DIR, exist_ok=True)
os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(STORIES_DIR, exist_ok=True)

def create_gradient_image(filename, width, height, color_start, color_end, title="", subtitle="", style="landscape"):
    """Generates an aesthetic high-resolution artistic image using Pillow."""
    img = Image.new('RGB', (width, height), color=color_start)
    draw = ImageDraw.Draw(img)

    # Render smooth vertical/diagonal gradient
    r1, g1, b1 = color_start
    r2, g2, b2 = color_end
    for y in range(height):
        ratio = y / height
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Add artistic geometric & photo elements
    if style == "landscape":
        # Sun / Moon
        draw.ellipse([width * 0.35, height * 0.2, width * 0.65, height * 0.5], fill=(255, 240, 200, 180))
        # Mountains / Horizons
        draw.polygon([(0, height), (width * 0.3, height * 0.55), (width * 0.65, height * 0.75), (width, height * 0.48), (width, height)], fill=(15, 23, 42))
        draw.polygon([(0, height), (width * 0.5, height * 0.68), (width, height)], fill=(30, 41, 59))
    elif style == "cyberpunk":
        # Grid lines
        for x in range(0, width, 40):
            draw.line([(x, height // 2), (x * 2 - width // 2, height)], fill=(236, 72, 153), width=2)
        for y in range(height // 2, height, 30):
            draw.line([(0, y), (width, y)], fill=(6, 182, 212), width=1)
        # Neon sun
        draw.ellipse([width * 0.3, height * 0.15, width * 0.7, height * 0.55], fill=(244, 63, 94))
    elif style == "minimal":
        # Circular soft composition
        draw.ellipse([width * 0.2, height * 0.2, width * 0.8, height * 0.8], outline=(255, 255, 255), width=4)
        draw.ellipse([width * 0.35, height * 0.35, width * 0.65, height * 0.65], fill=(56, 189, 248))
    elif style == "portrait":
        # Soft studio glow
        draw.ellipse([width * 0.25, height * 0.2, width * 0.75, height * 0.7], fill=(251, 146, 60))
        draw.polygon([(width * 0.2, height), (width * 0.5, height * 0.6), (width * 0.8, height)], fill=(17, 24, 39))
    elif style == "story":
        # Vertical aesthetic card
        draw.rectangle([40, 40, width - 40, height - 40], outline=(255, 255, 255), width=3)
        draw.ellipse([width * 0.3, height * 0.4, width * 0.7, height * 0.6], fill=(168, 85, 247))

    # Text overlay
    if title:
        # Simple clean label
        draw.rectangle([40, height - 100, width - 40, height - 40], fill=(0, 0, 0, 160))
        # Draw title text
        draw.text((60, height - 88), f"HISTOGRAM • {title.upper()}", fill=(255, 255, 255))
        if subtitle:
            draw.text((60, height - 64), subtitle, fill=(203, 213, 225))

    img.save(filename, 'JPEG', quality=90)
    return filename

def seed():
    database.init_db()
    conn = database.get_db_connection()
    cur = conn.cursor()

    # Clear existing data
    cur.executescript("""
    DELETE FROM notifications;
    DELETE FROM messages;
    DELETE FROM stories;
    DELETE FROM saved_posts;
    DELETE FROM likes;
    DELETE FROM comments;
    DELETE FROM followers;
    DELETE FROM posts;
    DELETE FROM users;
    """)
    conn.commit()

    print("Cleared existing records. Generating realistic demo users...")

    users_data = [
        {
            "username": "elena_lens",
            "email": "elena@histogram.local",
            "full_name": "Elena Rostova",
            "bio": "Visual storyteller & architectural explorer. Chasing light between monolithic shadows. 📍 Berlin",
            "avatar_color": ((14, 165, 233), (99, 102, 241))
        },
        {
            "username": "marcus_shoots",
            "email": "marcus@histogram.local",
            "full_name": "Marcus Chen",
            "bio": "Night photographer & cyberpunk archivist. Tokyo & Seoul after 2 AM. Sony A7R V. 📸",
            "avatar_color": ((236, 72, 153), (168, 85, 247))
        },
        {
            "username": "aurora_wild",
            "email": "aurora@histogram.local",
            "full_name": "Aurora Vance",
            "bio": "National Geographic contributor. Arctic tundras, alpine summits, and wild creatures. 🏔️🦊",
            "avatar_color": ((16, 185, 129), (5, 150, 105))
        },
        {
            "username": "neon_drifter",
            "email": "kai@histogram.local",
            "full_name": "Kai Tanaka",
            "bio": "Generative visual artist & analog synthesizer lover. Color theory enthusiast. 🎨✨",
            "avatar_color": ((245, 158, 11), (239, 68, 68))
        },
        {
            "username": "sophia_vibe",
            "email": "sophia@histogram.local",
            "full_name": "Sophia Rivera",
            "bio": "Editorial portraits & moody film aesthetics. 35mm film advocate. Milan / Paris.",
            "avatar_color": ((217, 70, 239), (79, 70, 229))
        }
    ]

    user_ids = {}
    hashed_pwd = generate_password_hash("password123")

    # Insert users & generate avatar files
    for u in users_data:
        avatar_name = f"avatar_{u['username']}.jpg"
        avatar_path = os.path.join(PROFILES_DIR, avatar_name)
        c1, c2 = u['avatar_color']
        create_gradient_image(avatar_path, 240, 240, c1, c2, title=u['username'][:12], subtitle="", style="minimal")

        cur.execute("""
        INSERT INTO users (username, email, password_hash, full_name, bio, profile_picture, created_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now', '-10 days'))
        """, (u['username'], u['email'], hashed_pwd, u['full_name'], u['bio'], avatar_name))
        user_ids[u['username']] = cur.lastrowid

    conn.commit()
    print(f"Created {len(user_ids)} users.")

    # Followers network
    follows = [
        ("elena_lens", "marcus_shoots"),
        ("elena_lens", "aurora_wild"),
        ("elena_lens", "neon_drifter"),
        ("marcus_shoots", "elena_lens"),
        ("marcus_shoots", "sophia_vibe"),
        ("aurora_wild", "elena_lens"),
        ("aurora_wild", "sophia_vibe"),
        ("neon_drifter", "marcus_shoots"),
        ("neon_drifter", "elena_lens"),
        ("sophia_vibe", "marcus_shoots"),
        ("sophia_vibe", "elena_lens"),
        ("sophia_vibe", "aurora_wild")
    ]

    for f_from, f_to in follows:
        cur.execute("""
        INSERT INTO followers (follower_id, following_id, created_at)
        VALUES (?, ?, datetime('now', '-5 days'))
        """, (user_ids[f_from], user_ids[f_to]))

    conn.commit()
    print("Created follower relationships.")

    # Posts data
    posts_data = [
        {
            "username": "elena_lens",
            "caption": "Minimalist brutalism meets morning mist. The geometry of architecture never fails to inspire. #geometry #architecture #histogram #berlin #composition",
            "style": "landscape",
            "colors": ((30, 41, 59), (14, 165, 233)),
            "title": "Geometry of Shadows",
            "hours_ago": 2
        },
        {
            "username": "marcus_shoots",
            "caption": "Neon rain in Shinjuku. The reflections on wet tarmac tell stories that the daylight erases. Captured on 85mm f/1.4. #cyberpunk #tokyo #nightphotography #street",
            "style": "cyberpunk",
            "colors": ((15, 23, 42), (236, 72, 153)),
            "title": "Shinjuku Nocturne",
            "hours_ago": 5
        },
        {
            "username": "aurora_wild",
            "caption": "First light over the Lofoten archipelago. At -14°C, your shutter button freezes, but moments like this make every frozen second worth it. 🏔️✨ #lofoten #arctic #nature #exploremore",
            "style": "landscape",
            "colors": ((12, 74, 110), (56, 189, 248)),
            "title": "Lofoten Sunrise",
            "hours_ago": 8
        },
        {
            "username": "neon_drifter",
            "caption": "Harmonics in magenta and cyan. Exploring visual frequencies and dynamic ranges. Which color palette resonates with you today? #visualart #histogram #colorstudy #synthwave",
            "style": "minimal",
            "colors": ((88, 28, 135), (244, 63, 94)),
            "title": "Spectral Waveform",
            "hours_ago": 12
        },
        {
            "username": "sophia_vibe",
            "caption": "Golden hour study with natural ambient backlight. No strobes, just the sun through sheer linen. Grain added in darkroom. #filmphotography #portrait #grainisgood #goldenhour",
            "style": "portrait",
            "colors": ((120, 53, 15), (251, 146, 60)),
            "title": "Ambient Glow",
            "hours_ago": 16
        },
        {
            "username": "elena_lens",
            "caption": "Reflections in modern glass. Finding tranquility in symmetrical lines amidst the urban rush. #symmetry #monochrome #urbanexploration",
            "style": "minimal",
            "colors": ((15, 23, 42), (99, 102, 241)),
            "title": "Symmetry & Glass",
            "hours_ago": 24
        },
        {
            "username": "marcus_shoots",
            "caption": "Midnight subway corridors. The quiet moments before the first train of dawn arrives. #neonlights #underground #vibes",
            "style": "cyberpunk",
            "colors": ((17, 24, 39), (16, 185, 129)),
            "title": "Midnight Lines",
            "hours_ago": 30
        }
    ]

    post_ids = []
    for idx, p in enumerate(posts_data):
        img_filename = f"post_{idx+1}_{p['username']}.jpg"
        img_path = os.path.join(POSTS_DIR, img_filename)
        c1, c2 = p['colors']
        create_gradient_image(img_path, 800, 800, c1, c2, title=p['title'], subtitle="HISTOGRAM CURATED", style=p['style'])

        time_delta = f"-{p['hours_ago']} hours"
        cur.execute("""
        INSERT INTO posts (user_id, media_path, media_type, caption, created_at)
        VALUES (?, ?, 'image', ?, datetime('now', ?))
        """, (user_ids[p['username']], img_filename, p['caption'], time_delta))
        p_id = cur.lastrowid
        post_ids.append((p_id, user_ids[p['username']]))

    conn.commit()
    print(f"Created {len(post_ids)} posts with images.")

    # Add Likes & Comments
    sample_comments = [
        "Incredible composition! The dynamic range is stunning.",
        "The lighting here is purely magical ✨",
        "That color grading is top tier! Which lens did you use?",
        "Such a clean shot. Loving this on Histogram!",
        "Stunning tone curve and exposure balance 🔥",
        "This belongs in a gallery. Keep inspiring us!"
    ]

    for p_id, author_id in post_ids:
        # Each post gets 2-4 likes
        likers = [u_id for u_id in user_ids.values() if u_id != author_id]
        chosen_likers = random.sample(likers, k=min(3, len(likers)))
        for liker_id in chosen_likers:
            cur.execute("""
            INSERT OR IGNORE INTO likes (user_id, post_id, created_at)
            VALUES (?, ?, datetime('now', '-1 hours'))
            """, (liker_id, p_id))

            # Add notification for like
            cur.execute("""
            INSERT INTO notifications (user_id, actor_id, notification_type, post_id, is_read, created_at)
            VALUES (?, ?, 'like', ?, 0, datetime('now', '-1 hours'))
            """, (author_id, liker_id, p_id))

        # Each post gets 1-3 comments
        commenters = random.sample(likers, k=min(2, len(likers)))
        for c_id in commenters:
            comm = random.choice(sample_comments)
            cur.execute("""
            INSERT INTO comments (user_id, post_id, comment_text, created_at)
            VALUES (?, ?, ?, datetime('now', '-30 minutes'))
            """, (c_id, p_id, comm))

            # Add notification for comment
            cur.execute("""
            INSERT INTO notifications (user_id, actor_id, notification_type, post_id, is_read, created_at)
            VALUES (?, ?, 'comment', ?, 0, datetime('now', '-30 minutes'))
            """, (author_id, c_id, p_id))

    # Stories (valid 24h)
    story_creators = ["elena_lens", "marcus_shoots", "aurora_wild", "neon_drifter"]
    for sc in story_creators:
        story_filename = f"story_{sc}.jpg"
        story_path = os.path.join(STORIES_DIR, story_filename)
        create_gradient_image(story_path, 600, 1000, (30, 27, 75), (236, 72, 153), title=f"{sc}'s Story", subtitle="Live from the field", style="story")

        cur.execute("""
        INSERT INTO stories (user_id, media_path, media_type, created_at, expires_at)
        VALUES (?, ?, 'image', datetime('now', '-2 hours'), datetime('now', '+22 hours'))
        """, (user_ids[sc], story_filename))

    print(f"Created active 24-hour stories for {len(story_creators)} users.")

    # Direct messages between elena_lens and marcus_shoots
    msgs = [
        (user_ids["elena_lens"], user_ids["marcus_shoots"], "Hey Marcus! Loving your new Shinjuku series!"),
        (user_ids["marcus_shoots"], user_ids["elena_lens"], "Thanks Elena! The rain really elevated the scene. Are you going to the Berlin photo expo next week?"),
        (user_ids["elena_lens"], user_ids["marcus_shoots"], "Yes, absolutely! Presenting some brutalist prints on Thursday.")
    ]

    for s_id, r_id, msg in msgs:
        cur.execute("""
        INSERT INTO messages (sender_id, receiver_id, message, created_at, is_read)
        VALUES (?, ?, ?, datetime('now', '-20 minutes'), 1)
        """, (s_id, r_id, msg))

    # Notifications for follow
    cur.execute("""
    INSERT INTO notifications (user_id, actor_id, notification_type, is_read, created_at)
    VALUES (?, ?, 'follow', 0, datetime('now', '-10 minutes'))
    """, (user_ids["elena_lens"], user_ids["aurora_wild"]))

    conn.commit()
    conn.close()
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed()
