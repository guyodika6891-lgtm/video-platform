import os
import cloudinary
import cloudinary.uploader
from flask import current_app


def init_cloudinary():
    if current_app.config["USE_CLOUDINARY"]:
        cloudinary.config(
            cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
            api_key=current_app.config["CLOUDINARY_API_KEY"],
            api_secret=current_app.config["CLOUDINARY_API_SECRET"],
            secure=True,
        )


def upload_to_cloudinary(file_storage):
    """Upload video to Cloudinary, return (video_url, thumbnail_url, public_id)."""
    result = cloudinary.uploader.upload_large(
        file_storage,
        resource_type="video",
        folder="videohub",
        chunk_size=6_000_000,
    )
    video_url = result["secure_url"]
    public_id = result["public_id"]

    # Generate JPG thumbnail from first frame
    thumbnail_url = cloudinary.CloudinaryImage(public_id).build_url(
        resource_type="video",
        format="jpg",
        transformation=[
            {"width": 640, "height": 360, "crop": "fill"},
            {"start_offset": "0"},
        ],
        secure=True,
    )
    return video_url, thumbnail_url, public_id


def delete_from_cloudinary(public_id):
    try:
        cloudinary.uploader.destroy(public_id, resource_type="video")
    except Exception:
        pass


def humanize(n):
    n = n or 0
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def time_ago(dt):
    from datetime import datetime
    if not dt:
        return ""
    delta = datetime.utcnow() - dt
    s = int(delta.total_seconds())
    if s < 60:
        return "just now"
    if s < 3600:
        return f"{s//60}m ago"
    if s < 86400:
        return f"{s//3600}h ago"
    if s < 2592000:
        return f"{s//86400}d ago"
    if s < 31536000:
        return f"{s//2592000}mo ago"
    return f"{s//31536000}y ago"