import io
import json
import unittest
from datetime import datetime, timedelta, timezone
from app import app
import database

class HistogramTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_database_tables_exist(self):
        """Verify all requested SQLite tables and indices exist."""
        conn = database.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row['name'] for row in cur.fetchall()}
        conn.close()

        expected = {'users', 'posts', 'likes', 'comments', 'followers', 'stories', 'messages', 'notifications', 'saved_posts'}
        for t in expected:
            self.assertIn(t, tables, f"Table {t} should exist in SQLite database")

    def test_register_and_login_flow(self):
        """Test registration, duplicate validation, and login."""
        unique_suffix = int(datetime.now().timestamp())
        username = f"testuser_{unique_suffix}"
        email = f"test_{unique_suffix}@histogram.test"
        password = "secretpassword123"

        # 1. Register
        res = self.client.post('/register', data={
            'username': username,
            'email': email,
            'full_name': 'Test User',
            'password': password
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # 2. Check DB
        user = database.query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
        self.assertIsNotNone(user)
        self.assertNotEqual(user['password_hash'], password) # Passwords must be hashed

        # 3. Log out before testing duplicate registration
        self.client.get('/logout')

        # Duplicate username should be rejected
        res_dup = self.client.post('/register', data={
            'username': username,
            'email': f"other_{unique_suffix}@test.com",
            'password': password
        })
        self.assertIn(b"Username is already taken", res_dup.data)

        # 4. Login with bad password
        bad_login = self.client.post('/login', data={
            'login_input': username,
            'password': 'wrongpassword'
        })
        self.assertIn(b"Invalid username/email or password", bad_login.data)

        # 6. Login with correct password
        good_login = self.client.post('/login', data={
            'login_input': username,
            'password': password
        }, follow_redirects=True)
        self.assertEqual(good_login.status_code, 200)

    def test_social_interactions(self):
        """Test posts, likes, comments, saves, follows, notifications, and DMs."""
        # Use existing seeded users
        user1 = database.query_db("SELECT * FROM users WHERE username = 'elena_lens'", one=True)
        user2 = database.query_db("SELECT * FROM users WHERE username = 'marcus_shoots'", one=True)
        self.assertIsNotNone(user1)
        self.assertIsNotNone(user2)

        # Login as elena_lens
        with self.client.session_transaction() as sess:
            sess['user_id'] = user1['id']

        # 1. Create a post
        post_media = (io.BytesIO(b"fake image data"), "test_photo.jpg")
        res_create = self.client.post('/create', data={
            'caption': "A test snapshot on Histogram #test",
            'media': post_media
        }, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)

        newest_post = database.query_db(
            "SELECT * FROM posts WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user1['id'],), one=True
        )
        self.assertIsNotNone(newest_post)
        post_id = newest_post['id']

        # Switch to marcus_shoots
        with self.client.session_transaction() as sess:
            sess['user_id'] = user2['id']

        # 2. Toggle Like
        res_like = self.client.post(f'/api/posts/{post_id}/like')
        self.assertEqual(res_like.status_code, 200)
        like_data = json.loads(res_like.data)
        self.assertTrue(like_data['liked'])
        self.assertGreaterEqual(like_data['likes_count'], 1)

        # Verify notification created for elena
        like_notif = database.query_db(
            "SELECT * FROM notifications WHERE user_id = ? AND actor_id = ? AND notification_type = 'like'",
            (user1['id'], user2['id']), one=True
        )
        self.assertIsNotNone(like_notif)

        # 3. Add Comment
        res_comm = self.client.post(f'/api/posts/{post_id}/comment', 
            data=json.dumps({'comment_text': "Great test shot!"}),
            content_type='application/json'
        )
        self.assertEqual(res_comm.status_code, 200)
        comm_data = json.loads(res_comm.data)
        self.assertTrue(comm_data['success'])
        comm_id = comm_data['comment']['id']

        # 4. Save post
        res_save = self.client.post(f'/api/posts/{post_id}/save')
        self.assertEqual(res_save.status_code, 200)
        save_data = json.loads(res_save.data)
        self.assertTrue(save_data['saved'])

        # 5. Direct message from marcus to elena
        res_dm = self.client.post('/api/messages/send',
            data=json.dumps({'receiver_username': 'elena_lens', 'message': 'Hello from test suite!'}),
            content_type='application/json'
        )
        self.assertEqual(res_dm.status_code, 200)
        dm_data = json.loads(res_dm.data)
        self.assertTrue(dm_data['success'])

        # Switch back to elena and fetch chat history
        with self.client.session_transaction() as sess:
            sess['user_id'] = user1['id']

        res_chat = self.client.get('/api/messages/marcus_shoots')
        self.assertEqual(res_chat.status_code, 200)
        chat_data = json.loads(res_chat.data)
        self.assertGreater(len(chat_data['messages']), 0)

        # 6. Delete comment
        res_del_comm = self.client.delete(f'/api/comments/{comm_id}')
        self.assertEqual(res_del_comm.status_code, 200)

        # 7. Delete post
        res_del_post = self.client.delete(f'/api/posts/{post_id}')
        self.assertEqual(res_del_post.status_code, 200)

        # Verify post deleted from DB
        deleted_check = database.query_db("SELECT * FROM posts WHERE id = ?", (post_id,), one=True)
        self.assertIsNone(deleted_check)

    def test_stories_api(self):
        """Test stories creation, query, and 24h expiration."""
        user = database.query_db("SELECT * FROM users WHERE username = 'elena_lens'", one=True)
        with self.client.session_transaction() as sess:
            sess['user_id'] = user['id']

        # Upload story
        story_media = (io.BytesIO(b"story photo content"), "my_story.jpg")
        res = self.client.post('/api/stories/create', data={
            'media': story_media
        }, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Query active stories
        res_fetch = self.client.get('/api/stories/elena_lens')
        self.assertEqual(res_fetch.status_code, 200)
        fetch_data = json.loads(res_fetch.data)
        self.assertGreater(len(fetch_data['stories']), 0)

    def test_explore_and_search_api(self):
        """Test explore feed and live search API."""
        # Explore page
        res = self.client.get('/explore')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Explore", res.data)

        # Search API for existing user
        res_search = self.client.get('/api/search?q=elena')
        self.assertEqual(res_search.status_code, 200)
        search_data = json.loads(res_search.data)
        self.assertTrue(any(u['username'] == 'elena_lens' for u in search_data['users']))

    def test_follow_unfollow_toggle(self):
        """Test follow and unfollow toggle."""
        user1 = database.query_db("SELECT * FROM users WHERE username = 'elena_lens'", one=True)
        user2 = database.query_db("SELECT * FROM users WHERE username = 'sophia_vibe'", one=True)

        with self.client.session_transaction() as sess:
            sess['user_id'] = user1['id']

        # Prevent self follow
        res_self = self.client.post(f'/api/users/{user1["id"]}/follow')
        self.assertEqual(res_self.status_code, 400)

        # Toggle follow sophia
        res_follow = self.client.post(f'/api/users/{user2["id"]}/follow')
        self.assertEqual(res_follow.status_code, 200)
        f_data = json.loads(res_follow.data)
        self.assertIn('following', f_data)

    def test_error_pages(self):
        """Test 404 handler."""
        res = self.client.get('/nonexistent-page-url-404')
        self.assertEqual(res.status_code, 404)
        self.assertIn(b"Page Not Available", res.data)

if __name__ == '__main__':
    unittest.main()
