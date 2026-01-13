# 🚀 Deployment Guide: How to Host MedData Platform for Free

This guide will show you how to host your project on **Render.com** (best free option for Python/FastAPI) so you can access it from anywhere.

## 🤔 Why were .env and .db missing?
This is intentional and correct!
- **.env**: Contains secrets (passwords/keys). You never upload these to GitHub. Instead, you enter them securely in the **Hosting Dashboard**.
- **.db**: Contains local data. You cannot upload "your user data" to the server. The server must create its own fresh database.

---

## 🌍 Step 1: Sign up for Render
1. Go to [https://render.com](https://render.com).
2. Sign up using your **GitHub** account.

## ⚙️ Step 2: Create New Web Service
1. Click **"New +"** → **"Web Service"**.
2. Select your repository: `med-data-platform`.
3. Give it a name (e.g., `my-med-platform`).

## 🛠️ Step 3: Configure Settings
Fill in these settings exactly:

| Setting | Value |
|---------|-------|
| **Region** | Singapore (or closest to you) |
| **Branch** | `main` |
| **Root Directory** | `backend` (Important! We only want to deploy the backend folder) |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python setup_database.py && uvicorn main:app --host 0.0.0.0 --port $PORT` |

> **Note on Start Command**: This command first creates the empty database tables (`setup_database.py`) and then starts the server.

## 🔑 Step 4: Add Environment Variables
Scroll down to **"Environment Variables"** and click **"Add Environment Variable"**. Add these keys and values (you can copy them from your local `.env` file):

| Key | Value (Example) |
|-----|-----------------|
| `SECRET_KEY` | `copy_your_long_random_key_here` |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` |
| `WITHDRAWAL_MIN_AMOUNT` | `500` |
| `PYTHON_VERSION` | `3.9.0` (Optional, Render uses 3.7+ by default) |

## 🚀 Step 5: Deploy!
1. Click **"Create Web Service"**.
2. Render will start building. It might take 3-5 minutes.
3. Once valid, you will see a green **"Live"** badge.
4. Click the URL (e.g., `https://my-med-platform.onrender.com`) to open your app!

---

## ⚠️ Important Note on "Free Tier" Database
Since we are using SQLite (a file-based database) on the free tier:
- **Render's free tier is "Stateless"**. This means if the server restarts (which happens automatically occasionally), **your database might be wiped**.
- This is fine for **demoing** the project to others.
- If you want **permanent** data storage, you would need to upgrade to a paid plan or connect an external PostgreSQL database (Render has a dedicated PostgreSQL service, but the free tier expires after 90 days).

For now, the setup above is perfect for showing your work!
