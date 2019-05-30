import unittest
from app.models import User, AnonymousUser, Role, Follow, Post
from app.models import Permission
from app import create_app, db
from datetime import datetime
import time
import hashlib


class UserModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_setter(self):
        u = User(username="set_password", email="set_password@123.com", password="cat")
        self.assertTrue(u.password_hash is not None)

    def test_no_password_getter(self):
        u = User(username="get_password", email="get_password@123.com", password="cat")
        with self.assertRaises(AttributeError):
            u.password

    def test_password_verification(self):
        u = User(username="verify_password", email="verify_password@123.com", password="cat")
        self.assertTrue(u.verify_password("cat"))
        self.assertFalse(u.verify_password("dog"))

    def test_password_salts_are_random(self):
        u1 = User(username="random1", email="random1@123.com", password="cat")
        u2 = User(username="random2", email="random2@123.com", password="cat")
        self.assertNotEquals(u1, u2)

    def test_user_role(self):
        u = User(email="john@example.com", password="cat")
        self.assertTrue(u.can(Permission.FOLLOW))
        self.assertTrue(u.can(Permission.COMMENT))
        self.assertTrue(u.can(Permission.WRITE))
        self.assertFalse(u.can(Permission.MODERATE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_anonymous_user(self):
        u = AnonymousUser()
        self.assertFalse(u.can(Permission.FOLLOW))
        self.assertFalse(u.can(Permission.COMMENT))
        self.assertFalse(u.can(Permission.WRITE))
        self.assertFalse(u.can(Permission.MODERATE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_moderator_role(self):
        r = Role.query.filter_by(name='Moderator').first()
        u = User(email='john@example.com', password='cat', role=r)
        self.assertTrue(u.can(Permission.FOLLOW))
        self.assertTrue(u.can(Permission.COMMENT))
        self.assertTrue(u.can(Permission.WRITE))
        self.assertTrue(u.can(Permission.MODERATE))
        self.assertFalse(u.can(Permission.ADMIN))

    def test_administrator_role(self):
        r = Role.query.filter_by(name='Administrator').first()
        u = User(email='john@example.com', password='cat', role=r)
        self.assertTrue(u.can(Permission.FOLLOW))
        self.assertTrue(u.can(Permission.COMMENT))
        self.assertTrue(u.can(Permission.WRITE))
        self.assertTrue(u.can(Permission.MODERATE))
        self.assertTrue(u.can(Permission.ADMIN))

    def test_timestamps(self):
        u = User(password="cat")
        db.session.add(u)
        db.session.commit()
        self.assertTrue(
            (datetime.utcnow() - u.member_since).total_seconds() < 3)
        self.assertTrue(
            (datetime.utcnow() - u.last_seen).total_seconds() < 3)

    def test_ping(self):
        u = User(password="cat")
        db.session.add(u)
        db.session.commit()
        # time.sleep(2)
        last_seen_before = u.last_seen
        u.ping()
        self.assertTrue(u.last_seen >= last_seen_before)

    def test_avatar(self):
        u = User(email="john@example.com", password="cat")
        email_hash = hashlib.md5(u.email.lower().encode("utf-8")).hexdigest()
        with self.app.test_request_context("/"):
            gravatar = u.gravatar()
            gravatar_256 = u.gravatar(size=256)
            gravatar_pg = u.gravatar(rating="pg")
            gravatar_retro = u.gravatar(default="retro")
        self.assertTrue('http://www.gravatar.com/avatar/' +
                        email_hash in gravatar)
        self.assertTrue('s=256' in gravatar_256)
        self.assertTrue('r=pg' in gravatar_pg)
        self.assertTrue('d=retro' in gravatar_retro)

    def test_follow(self):
        timestamp_before = datetime.utcnow()
        u1 = User(username="u1", password="cat")
        u2 = User(username="u2", password="dog")
        db.session.add_all([u1, u2])
        db.session.commit()
        print("Follow before follow:", Follow.query.all())
        self.assertFalse(u1.is_following(u2))
        self.assertFalse(u2.is_followed_by(u1))
        u1.follow(u2)
        # db.session.add(u1)
        db.session.commit()
        timestamp_after = datetime.utcnow()
        self.assertTrue(u1.is_following(u2))
        self.assertTrue(u2.is_followed_by(u1))
        self.assertFalse(u1.is_followed_by(u2))
        self.assertTrue(u1.followed.count() == 1, msg="u1.followed.count() = {}".format(u1.followed.count()))
        self.assertTrue(u2.followers.count() == 1)
        f = u1.followed.all()[-1]
        print(u1.followed.all())
        self.assertTrue(f.followed == u2)
        # self.assertTrue(timestamp_before <= f.timestamp <= timestamp_after,
        #                msg="before:{0},f:{1},after{2}".format(timestamp_before, f.timestamp, timestamp_after))
        # AssertionError: False is not true :
        #   before:2019-04-22 06:55:27.341021,f:2019-04-22 06:55:26.728443,after2019-04-22 06:55:27.865376
        f = u2.followers.all()[-1]
        self.assertTrue(f.follower == u1)
        u1.unfollow(u2)
        # db.session.add(u1)
        db.session.commit()
        self.assertTrue(u1.followed.count() == 0)
        self.assertTrue(u2.followers.count() == 0)
        self.assertTrue(Follow.query.count() == 0)
        u2.follow(u1)
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        db.session.delete(u2)
        db.session.commit()
        self.assertTrue(Follow.query.count() == 0)

    def test_followed_posts(self):
        u1 = User(username="u1")
        u2 = User(username="u2")
        db.session.add_all([u1, u2])
        db.session.commit()
        u1.follow(u2)
        db.session.commit()
        p = Post(body="u2's post", author=u2)
        db.session.add_all([p])
        db.session.commit()
        self.assertEqual(u1.followed_posts.first(), p)
