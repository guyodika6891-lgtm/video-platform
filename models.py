from datetime import datetime
from flask_login import UserMixin
from extensions import db


# ---------- Many-to-many helpers ----------
likes = db.Table(
    "likes",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("video_id", db.Integer, db.ForeignKey("videos.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=datetime.utcnow),
)

subscriptions = db.Table(
    "subscriptions",
    db.Column("subscriber_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("channel_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=datetime.utcnow),
)

watch_later = db.Table(
    "watch_later",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("video_id", db.Integer, db.ForeignKey("videos.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=datetime.utcnow),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(500))
    banner_url = db.Column(db.String(500))
    bio = db.Column(db.Text, default="")
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    videos = db.relationship(
        "Video", backref="owner", lazy="dynamic", cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", backref="author", lazy="dynamic", cascade="all, delete-orphan"
    )

    # subscriptions where this user is the subscriber
    subscriptions = db.relationship(
        "User",
        secondary=subscriptions,
        primaryjoin=id == subscriptions.c.subscriber_id,
        secondaryjoin=id == subscriptions.c.channel_id,
        backref="subscribers",
    )

    @property
    def subscriber_count(self):
        return len(self.subscribers)

    @property
    def total_views(self):
        return sum(v.views for v in self.videos)


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(40), default="Other", index=True)

    # Storage: either local filename or Cloudinary URLs
    filename = db.Column(db.String(500))            # local fallback
    video_url = db.Column(db.String(500))           # cloud URL
    thumbnail_url = db.Column(db.String(500))       # cloud thumbnail
    public_id = db.Column(db.String(200))           # cloudinary id (for delete)

    views = db.Column(db.Integer, default=0, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    comments = db.relationship(
        "Comment", backref="video", lazy="dynamic", cascade="all, delete-orphan"
    )
    likers = db.relationship("User", secondary=likes, lazy="dynamic")

    @property
    def like_count(self):
        return self.likers.count()

    @property
    def comment_count(self):
        return self.comments.count()

    @property
    def play_url(self):
        return self.video_url or f"/uploads/{self.filename}"

    @property
    def thumb(self):
        return self.thumbnail_url or "/static/img/placeholder.jpg"


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)


class WatchHistory(db.Model):
    __tablename__ = "watch_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False)
    watched_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    video = db.relationship("Video")
    user = db.relationship("User")