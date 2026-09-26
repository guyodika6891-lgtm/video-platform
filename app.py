import os
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, abort, send_from_directory, jsonify
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import desc, or_

from config import Config
from extensions import db, login_manager, csrf
from models import (
    User, Video, Comment, WatchHistory,
    likes, subscriptions, watch_later
)
from forms import (
    RegisterForm, LoginForm, UploadForm, EditVideoForm,
    CommentForm, SettingsForm
)
from utils import (
    init_cloudinary, upload_to_cloudinary, delete_from_cloudinary,
    humanize, time_ago
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        db.create_all()
        init_cloudinary()

    # Jinja helpers
    app.jinja_env.filters["humanize"] = humanize
    app.jinja_env.filters["time_ago"] = time_ago

    register_routes(app)
    register_errors(app)
    return app


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )


def register_errors(app):
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("500.html"), 500


def register_routes(app):

    # ---------------- Home ----------------
    @app.route("/")
    def index():
        category = request.args.get("category", "").strip()
        q = request.args.get("q", "").strip()

        query = Video.query
        if category:
            query = query.filter(Video.category == category)
        if q:
            like = f"%{q}%"
            query = query.filter(or_(
                Video.title.ilike(like),
                Video.description.ilike(like),
            ))
        videos = query.order_by(Video.created_at.desc()).limit(60).all()
        trending = (
            Video.query
            .filter(Video.created_at >= datetime.utcnow() - timedelta(days=7))
            .order_by(Video.views.desc())
            .limit(6).all()
        )
        return render_template(
            "index.html", videos=videos, trending=trending,
            category=category, q=q, categories=Config.CATEGORIES
        )

    # ---------------- Trending ----------------
    @app.route("/trending")
    def trending():
        videos = Video.query.order_by(Video.views.desc()).limit(60).all()
        return render_template("trending.html", videos=videos)

    # ---------------- Subscriptions feed ----------------
    @app.route("/subscriptions")
    @login_required
    def subscriptions_feed():
        channels = current_user.subscriptions
        ids = [c.id for c in channels]
        videos = (
            Video.query.filter(Video.user_id.in_(ids))
            .order_by(Video.created_at.desc()).limit(60).all()
            if ids else []
        )
        return render_template("subscriptions.html", videos=videos, channels=channels)

    # ---------------- Watch Later ----------------
    @app.route("/watch-later")
    @login_required
    def watch_later_page():
        videos = (
            Video.query.join(watch_later, watch_later.c.video_id == Video.id)
            .filter(watch_later.c.user_id == current_user.id)
            .order_by(watch_later.c.created_at.desc()).all()
        )
        return render_template("watch_later.html", videos=videos)

    @app.route("/watch-later/toggle/<int:video_id>", methods=["POST"])
    @login_required
    def toggle_watch_later(video_id):
        video = Video.query.get_or_404(video_id)
        exists = db.session.query(watch_later).filter_by(
            user_id=current_user.id, video_id=video.id
        ).first()
        if exists:
            db.session.execute(
                watch_later.delete().where(
                    (watch_later.c.user_id == current_user.id) &
                    (watch_later.c.video_id == video.id)
                )
            )
            state = "removed"
        else:
            db.session.execute(watch_later.insert().values(
                user_id=current_user.id, video_id=video.id
            ))
            state = "added"
        db.session.commit()
        return jsonify({"state": state})

    # ---------------- History ----------------
    @app.route("/history")
    @login_required
    def history():
        rows = (
            WatchHistory.query.filter_by(user_id=current_user.id)
            .order_by(WatchHistory.watched_at.desc()).limit(100).all()
        )
        # Deduplicate by video
        seen, videos = set(), []
        for r in rows:
            if r.video_id not in seen and r.video:
                seen.add(r.video_id)
                videos.append(r.video)
        return render_template("history.html", videos=videos)

    @app.route("/history/clear", methods=["POST"])
    @login_required
    def clear_history():
        WatchHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash("History cleared.", "info")
        return redirect(url_for("history"))

    # ---------------- Auth ----------------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        form = RegisterForm()
        if form.validate_on_submit():
            username = form.username.data.strip()
            email = form.email.data.strip().lower()
            if User.query.filter(
                (User.username == username) | (User.email == email)
            ).first():
                flash("Username or email already taken.", "danger")
            else:
                user = User(
                    username=username,
                    email=email,
                    password=generate_password_hash(form.password.data),
                    is_admin=(User.query.count() == 0),  # first user = admin
                )
                db.session.add(user)
                db.session.commit()
                login_user(user)
                flash("Welcome to VideoHub!", "success")
                return redirect(url_for("index"))
        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data.strip()).first()
            if user and check_password_hash(user.password, form.password.data):
                login_user(user, remember=True)
                next_url = request.args.get("next")
                flash(f"Welcome back, {user.username}!", "success")
                return redirect(next_url or url_for("index"))
            flash("Invalid username or password.", "danger")
        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("index"))

    # ---------------- Upload ----------------
    @app.route("/upload", methods=["GET", "POST"])
    @login_required
    def upload():
        form = UploadForm()
        form.category.choices = [(c, c) for c in Config.CATEGORIES]
        if form.validate_on_submit():
            file = request.files.get("video")
            if not file or file.filename == "":
                flash("Please choose a video file.", "danger")
                return redirect(url_for("upload"))
            if not allowed_file(file.filename):
                flash("Only mp4, webm, ogg, mov allowed.", "danger")
                return redirect(url_for("upload"))

            video_url = thumbnail_url = public_id = filename = None

            if app.config["USE_CLOUDINARY"]:
                try:
                    video_url, thumbnail_url, public_id = upload_to_cloudinary(file)
                except Exception as e:
                    flash(f"Cloud upload failed: {e}", "danger")
                    return redirect(url_for("upload"))
            else:
                ext = file.filename.rsplit(".", 1)[1].lower()
                filename = secure_filename(f"{current_user.id}_{uuid.uuid4().hex}.{ext}")
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            video = Video(
                title=form.title.data.strip(),
                description=form.description.data or "",
                category=form.category.data,
                filename=filename,
                video_url=video_url,
                thumbnail_url=thumbnail_url,
                public_id=public_id,
                user_id=current_user.id,
            )
            db.session.add(video)
            db.session.commit()
            flash("Video uploaded successfully!", "success")
            return redirect(url_for("watch", video_id=video.id))
        return render_template("upload.html", form=form)

    # ---------------- Edit ----------------
    @app.route("/video/<int:video_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_video(video_id):
        video = Video.query.get_or_404(video_id)
        if video.user_id != current_user.id and not current_user.is_admin:
            abort(403)
        form = EditVideoForm(obj=video)
        form.category.choices = [(c, c) for c in Config.CATEGORIES]
        if form.validate_on_submit():
            video.title = form.title.data.strip()
            video.description = form.description.data or ""
            video.category = form.category.data
            db.session.commit()
            flash("Video updated.", "success")
            return redirect(url_for("watch", video_id=video.id))
        return render_template("edit_video.html", form=form, video=video)

    # ---------------- Delete ----------------
    @app.route("/video/<int:video_id>/delete", methods=["POST"])
    @login_required
    def delete_video(video_id):
        video = Video.query.get_or_404(video_id)
        if video.user_id != current_user.id and not current_user.is_admin:
            abort(403)
        if video.public_id:
            delete_from_cloudinary(video.public_id)
        elif video.filename:
            try:
                os.remove(os.path.join(app.config["UPLOAD_FOLDER"], video.filename))
            except OSError:
                pass
        db.session.delete(video)
        db.session.commit()
        flash("Video deleted.", "info")
        return redirect(url_for("index"))

    # ---------------- Watch ----------------
    @app.route("/watch/<int:video_id>")
    def watch(video_id):
        video = Video.query.get_or_404(video_id)
        video.views = (video.views or 0) + 1

        if current_user.is_authenticated:
            db.session.add(WatchHistory(user_id=current_user.id, video_id=video.id))

        db.session.commit()

        comments = video.comments.order_by(Comment.created_at.desc()).all()
        related = (
            Video.query
            .filter(Video.id != video.id, Video.category == video.category)
            .order_by(Video.views.desc()).limit(10).all()
        )
        if len(related) < 6:
            extra = (
                Video.query.filter(Video.id != video.id)
                .order_by(Video.created_at.desc()).limit(10 - len(related)).all()
            )
            related.extend(extra)

        liked = (
            current_user.is_authenticated
            and video.likers.filter_by(id=current_user.id).first() is not None
        )
        in_wl = False
        if current_user.is_authenticated:
            in_wl = db.session.query(watch_later).filter_by(
                user_id=current_user.id, video_id=video.id
            ).first() is not None

        form = CommentForm()
        return render_template(
            "watch.html", video=video, comments=comments,
            related=related, liked=liked, in_watch_later=in_wl, form=form
        )

    # ---------------- Local file serve ----------------
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # ---------------- Like / Unlike (AJAX) ----------------
    @app.route("/video/<int:video_id>/like", methods=["POST"])
    @login_required
    def like_video(video_id):
        video = Video.query.get_or_404(video_id)
        already = video.likers.filter_by(id=current_user.id).first()
        if already:
            db.session.execute(likes.delete().where(
                (likes.c.user_id == current_user.id) &
                (likes.c.video_id == video.id)
            ))
            state = "unliked"
        else:
            db.session.execute(likes.insert().values(
                user_id=current_user.id, video_id=video.id
            ))
            state = "liked"
        db.session.commit()
        return jsonify({"state": state, "count": video.like_count})

    # ---------------- Comments ----------------
    @app.route("/video/<int:video_id>/comment", methods=["POST"])
    @login_required
    def post_comment(video_id):
        video = Video.query.get_or_404(video_id)
        form = CommentForm()
        if form.validate_on_submit():
            c = Comment(body=form.body.data.strip(),
                        user_id=current_user.id, video_id=video.id)
            db.session.add(c)
            db.session.commit()
            flash("Comment posted.", "success")
        return redirect(url_for("watch", video_id=video.id) + "#comments")

    @app.route("/comment/<int:comment_id>/delete", methods=["POST"])
    @login_required
    def delete_comment(comment_id):
        c = Comment.query.get_or_404(comment_id)
        if c.user_id != current_user.id and not current_user.is_admin:
            abort(403)
        vid = c.video_id
        db.session.delete(c)
        db.session.commit()
        return redirect(url_for("watch", video_id=vid) + "#comments")

    # ---------------- Subscribe ----------------
    @app.route("/channel/<username>/subscribe", methods=["POST"])
    @login_required
    def toggle_subscribe(username):
        channel = User.query.filter_by(username=username).first_or_404()
        if channel.id == current_user.id:
            return jsonify({"error": "cannot subscribe to yourself"}), 400

        exists = db.session.query(subscriptions).filter_by(
            subscriber_id=current_user.id, channel_id=channel.id
        ).first()
        if exists:
            db.session.execute(subscriptions.delete().where(
                (subscriptions.c.subscriber_id == current_user.id) &
                (subscriptions.c.channel_id == channel.id)
            ))
            state = "unsubscribed"
        else:
            db.session.execute(subscriptions.insert().values(
                subscriber_id=current_user.id, channel_id=channel.id
            ))
            state = "subscribed"
        db.session.commit()
        return jsonify({"state": state, "count": channel.subscriber_count})

    # ---------------- Channel page ----------------
    @app.route("/channel/<username>")
    def channel(username):
        user = User.query.filter_by(username=username).first_or_404()
        videos = user.videos.order_by(Video.created_at.desc()).all()
        is_sub = (
            current_user.is_authenticated
            and current_user.id != user.id
            and db.session.query(subscriptions).filter_by(
                subscriber_id=current_user.id, channel_id=user.id
            ).first() is not None
        )
        return render_template(
            "channel.html", user=user, videos=videos, is_sub=is_sub
        )

    # ---------------- Search page (optional explicit route) ----------------
    @app.route("/search")
    def search():
        q = request.args.get("q", "").strip()
        return redirect(url_for("index", q=q))

    # ---------------- Settings ----------------
    @app.route("/settings", methods=["GET", "POST"])
    @login_required
    def settings():
        form = SettingsForm(obj=current_user)
        if form.validate_on_submit():
            current_user.bio = form.bio.data or ""
            current_user.avatar_url = form.avatar_url.data or ""
            current_user.banner_url = form.banner_url.data or ""
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("settings"))
        return render_template("settings.html", form=form)

    # ---------------- Admin ----------------
    @app.route("/admin")
    @login_required
    @admin_required
    def admin():
        stats = {
            "users": User.query.count(),
            "videos": Video.query.count(),
            "views": db.session.query(db.func.sum(Video.views)).scalar() or 0,
            "comments": Comment.query.count(),
        }
        users = User.query.order_by(User.created_at.desc()).limit(50).all()
        videos = Video.query.order_by(Video.created_at.desc()).limit(50).all()
        return render_template("admin.html", stats=stats, users=users, videos=videos)

    @app.route("/admin/user/<int:user_id>/toggle-admin", methods=["POST"])
    @login_required
    @admin_required
    def toggle_admin(user_id):
        u = User.query.get_or_404(user_id)
        if u.id == current_user.id:
            flash("You can't change your own admin status.", "warning")
        else:
            u.is_admin = not u.is_admin
            db.session.commit()
            flash(f"{u.username} admin={u.is_admin}", "info")
        return redirect(url_for("admin"))

    # ---------------- Health ----------------
    @app.route("/healthz")
    def healthz():
        return {"status": "ok", "time": datetime.utcnow().isoformat()}


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)