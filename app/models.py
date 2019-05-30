from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from . import login_manager
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
import itsdangerous.exc
from flask import current_app, g, request, url_for
from datetime import datetime
import hashlib
from markdown import markdown
import bleach
from .exceptions import ValidationError


@login_manager.user_loader
def load_user(user_id):
    """
    flask_login 调用，传入用户唯一标识，返回用户对象
    :param user_id:
    :return User():
    """
    return User.query.get(int(user_id))


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer,)
    users = db.relationship("User", backref="role", lazy="dynamic")

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def __repr__(self):
        return "<Role {}>".format(self.name)

    def add_permission(self, perm):
        self.permissions = self.permissions | perm

    def remove_permission(self, perm):
        perm = ~perm
        self.permissions = self.permissions & perm

    def reset_permission(self):
        self.permissions = 0

    def has_permission(self, perm):
        return (self.permissions & perm) == perm

    @staticmethod
    def insert_roles():
        roles = {
            "User": [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            "Moderator": [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE,
                          Permission.MODERATE],
            "Administrator": [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE,
                              Permission.MODERATE, Permission.ADMIN]
        }
        default_role = "User"
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permission()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()


class Follow(db.Model):
    __tablename__ = "follows"
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())

    def __repr__(self):
        return "<Follow follower:{} followed:{}>".format(self.follower_id, self.followed_id)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))  # 真实姓名
    location = db.Column(db.String(64))  # 所在地
    about_me = db.Column(db.Text())  # 自我介绍
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)  # 注册日期
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)  # 最后登陆日期
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship("Post", backref="author", lazy="dynamic")
    followed = db.relationship("Follow",
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref("follower", lazy="joined"),
                               lazy="dynamic",
                               cascade="all, delete-orphan")
    followers = db.relationship("Follow",
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref("followed", lazy="joined"),
                                lazy="dynamic",
                                cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="author", lazy="dynamic")

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config["FLASKY_ADMIN"]:
                self.role = Role.query.filter_by(name="Administrator").first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()

    def __repr__(self):
        return "<User {}>".format(self.username)

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"confirm": self.id}).decode("utf-8")

    def confirm(self, token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token.encode("utf-8"))
        except itsdangerous.exc.SignatureExpired:
            return False
        except itsdangerous.exc.BadData:
            return False
        if data.get("confirm") != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_password_token(self, expiration=3600):
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"action": "reset_pwd", "email": self.email, "id": self.id}).decode("utf-8")

    def confirm_reset_password(self, token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token.encode("utf-8"))
        except itsdangerous.exc.SignatureExpired:
            return False
        except itsdangerous.exc.BadData:
            return False
        if data.get("action") == "reset_pwd":
            user = self.query.filter_by(email=data.get("email"), id=data.get("id")).first()
            if user:
                g.user = user
                return True
        return False

    def generate_change_email_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        self.confirmed = False  # 把数据库中确认位修改为未确认的状态
        db.session.add(self)
        db.session.commit()
        return s.dumps({"action": "change_email", "email": self.email,
                        "id": self.id, "new_email": new_email}).decode("utf-8")

    def confirm_change_email(self, token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token.encode("utf-8"))
        except itsdangerous.exc.SignatureExpired:
            return False
        except itsdangerous.exc.BadData:
            return False
        if data.get("action") == "change_pwd":
            user = self.query.filter_by(email=data.get("email"), id=data.get("id")).first()
            if user:
                g.user = user
                return data.get("new_email")
        return False

    def change_email(self, new_email):
        self.email = new_email
        self.avatar_hash = self.gravatar_hash()
        self.confirmed = True
        db.session.add(self)
        return True

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode("utf-8")).hexdigest()

    def ping(self):
        """
        更新最近登录时间 lastseen
        :return:
        """
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def gravatar(self, size=100, default="identicon", rating="g"):
        if request.is_secure:
            url = "https://secure.gravatar.com/avatar"
        else:
            url = "http://www.gravatar.com/avatar"
        email_hash = self.avatar_hash or self.gravatar_hash()
        return "{url}/{hash}?s={size}&d={default}&r={rating}".format(url=url, hash=email_hash, size=size,
                                                                     default=default, rating=rating)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower_id=self.id, followed_id=user.id)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id).\
            filter(Follow.follower_id == self.id)

    def generate_auth_token(self, expiration=600):
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"id": self.id}).decode()

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data["id"])

    def to_json(self):
        json_user = {
            "url": url_for("api.get_user", id=self.id),
            "username": self.username,
            "member_since": self.member_since,
            "last_seen": self.last_seen,
            "posts_url": url_for("api.get_user_posts", id=self.id),
            "followed_posts_url": url_for("api.get_user_followed_posts", id=self.id),
            "post_count": self.posts.count()
        }
        return json_user


class AnonymousUser(AnonymousUserMixin):
    def can(self, perm):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


class Permission:
    FOLLOW = 1  # 关注用户
    COMMENT = 2  # 在他人文章评论
    WRITE = 4  # 写文章
    MODERATE = 8  # 管理他人评论
    ADMIN = 16  # 管理员权限


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow())
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    body_html = db.Column(db.Text)
    comments = db.relationship("Comment", backref="post", lazy="dynamic", order_by="Comment.timestamp")

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ["a", "abbr", "acronym", "b", "blockquote", "code",
                        "em", "i", "li", "ol", "pre", "strong", "ul", "h1",
                        "h2", "h3", "p"]
        target.body_html = bleach.linkify(bleach.clean(markdown(value, output_format="html"),
                                                       tags=allowed_tags, strip=True))

    def to_json(self):
        json_post = {
            "url": url_for("api.get_post", id=self.id),
            "body": self.body,
            "body_html": self.body_html,
            "timestamp": self.timestamp,
            "author_url": url_for("api.get_user", id=self.author_id),
            "comments_url": url_for("api.get_posts_comments", id=self.id),
            "comment_count": self.comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get("body")
        if body is None or body == "":
            raise ValidationError("post does not have a body")
        return Post(body=body)

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))
    disabled = db.Column(db.Boolean, default=False)

    @staticmethod
    def on_change_body(target, value, oldvalue, initiator):
        allowed_tags = ["a", "abbr", "acronym", "b", "blockquote", "code",
                        "em", "i", "li", "ol", "pre", "strong", "ul", "h1",
                        "h2", "h3", "p"]
        target.body_html = bleach.linkify(bleach.clean(markdown(value, output_format="html"),
                                                       tags=allowed_tags, strip=True))

    def to_json(self):
        json_comment = {
            "url": url_for("api.get_comment", id=self.id),
            "body": self.body,
            "body_html": self.body_html,
            "timestamp": self.timestamp,
            "author_url": url_for("api.get_user", id=self.author_id),
            "post_url": url_for("api.get_post", id=self.post_id),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get("body")
        if body is None or body == "":
            raise ValidationError("comment does not have body")
        return Comment(body=body)


db.event.listen(Post.body, "set", Post.on_changed_body)
db.event.listen(Comment.body, "set", Comment.on_change_body)


