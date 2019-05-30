from random import randint
from sqlalchemy.exc import IntegrityError
from faker import Faker
from .models import User, Post, Follow
from . import db


def users(count=100):
    fake = Faker()
    i = 0
    while i < count:
        u = User(email=fake.email(),
                 username=fake.user_name(),
                 password="password",
                 confirmed=True,
                 name=fake.name(),
                 location=fake.city(),
                 about_me=fake.text(),
                 member_since=fake.past_date())
        db.session.add(u)
        try:
            db.session.commit()
            i += 1
        except IntegrityError:
            db.session.rollback()


def posts(count=100):
    fake = Faker()
    user_count = User.query.count()
    for i in range(count):
        u = User.query.offset(randint(0, user_count - 1)).first()
        p = Post(body=fake.text(),
                 timestamp=fake.past_datetime(),
                 author=u)
        db.session.add(p)
    db.session.commit()


def follow(count=100):
    fake = Faker()
    user_count = User.query.count()
    for i in range(count):
        user_id = randint(1, user_count-1)
        f = Follow(follower_id=user_id, followed_id=user_count-user_id)
        try:
            db.session.add(f)
            db.session.commit()
        except:
            db.session.rollback()