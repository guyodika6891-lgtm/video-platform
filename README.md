# 🎬 VideoHub — Flask Video Platform

A simple video sharing platform built with **Flask**, **SQLAlchemy**, **Flask-Login**, and **Bootstrap 5**.

## ✨ Features
- User registration & login
- Upload videos (mp4, webm, ogg, mov — up to 200 MB)
- Watch videos with HTML5 player
- Search videos
- View counter
- Delete your own videos
- Responsive Bootstrap 5 UI

## 🧰 Tech Stack
- Python 3.11 / Flask 3
- Flask-SQLAlchemy
- Flask-Login
- Bootstrap 5
- Gunicorn (production)

## 🖥️ Run Locally

```bash
git clone https://github.com/guyodika6891-lgtm/video-platform.git
cd video-platform

python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

Visit **http://127.0.0.1:5000**

## 🚀 Deploy to Render.com

1. Push repo to GitHub.
2. Go to https://render.com → **New → Blueprint**.
3. Connect your GitHub repo — Render reads `render.yaml`.
4. Wait for build → done.

Or manually:
- **New → Web Service**
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT`
- Add env `SECRET_KEY` (generate).
- Add a **PostgreSQL** database and set `DATABASE_URL`.

## ⚠️ Storage Note
Render's filesystem is **ephemeral**. Uploaded files disappear after restarts.
For production, store uploads on:
- Cloudinary (free tier)
- AWS S3 / Cloudflare R2
- Render Disk (paid)

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 GUYO DIKA
