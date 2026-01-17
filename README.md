# 🏥 MedData Enterprise Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-Real--time-FF6B6B?style=for-the-badge&logo=socket.io&logoColor=white)
![License](https://img.shields.io/badge/License-Private-red?style=for-the-badge)

**A comprehensive enterprise workforce management platform for distributed data annotation teams.**

[Features](#-features) • [Tech Stack](#-tech-stack) • [Installation](#-installation) • [Architecture](#-architecture) • [Screenshots](#-screenshots)

</div>

---

## 🚀 Features

### 👔 Admin Dashboard
- **Staff Management** – View, ban/activate users, verify KYC documents
- **Project Assignment** – Create projects, assign to employees with deadlines & pricing
- **Financial Control** – Process withdrawals, TDS calculations, analytics
- **Community Moderation** – Approve/reject posts with feedback
- **Real-time Support** – WebSocket-powered chat with employees

### 👨‍💻 Employee Portal
- **Modern Mobile UI** – Bottom navigation, glassmorphism design
- **Gamification** – XP system, levels, leaderboards, daily challenges
- **Workstation** – Image annotation with auto-save
- **Wallet** – Real-time balance, transaction history, withdrawals
- **Community Hub** – Share updates, interact with peers

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.9+, FastAPI, Uvicorn |
| **Database** | SQLite with SQLAlchemy ORM |
| **Frontend** | HTML5, CSS3 (Glassmorphism), Vanilla JS |
| **Auth** | JWT + Bcrypt |
| **Real-time** | WebSockets |
| **Deployment** | Render.com / Docker |

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/errohgupta/med-data-platform.git
cd med-data-platform/backend

# Install dependencies
pip install -r requirements.txt

# Initialize the database
python setup_database.py

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Environment Variables

Create a `.env` file in the `backend` folder:

```env
SECRET_KEY=your_secure_random_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
WITHDRAWAL_MIN_AMOUNT=500
WITHDRAWAL_MAX_AMOUNT=50000
```

---

## 🏗 Architecture

```
med-data-platform/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth_utils.py        # JWT authentication
│   ├── database.py          # Database connection
│   ├── setup_database.py    # DB initialization
│   ├── templates/           # Jinja2 HTML templates
│   │   ├── admin.html       # Admin dashboard
│   │   ├── employee_landing.html
│   │   └── workstation.html
│   └── static/              # CSS, JS assets
└── frontend/                # Future React/Vue app
```

---

## 📸 Screenshots

<details>
<summary>Click to expand</summary>

### Employee Dashboard (Mobile)
- Modern bottom navigation bar
- Glassmorphism card design
- Real-time wallet balance

### Admin Dashboard
- Staff management table
- Financial analytics
- Chat support panel

</details>

---

## 🔐 Security Features

- **JWT Authentication** with token refresh
- **Bcrypt Password Hashing**
- **Role-based Access Control** (Admin/Employee)
- **Session Termination** on ban
- **Audit Logging** for critical actions

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/token` | Login & get JWT |
| `GET` | `/api/profile` | Get user profile |
| `GET` | `/api/projects` | List user projects |
| `POST` | `/api/withdraw` | Request withdrawal |
| `WS` | `/ws/support/{user_id}` | Real-time chat |

---

## 🤝 Contributing

This is a private enterprise project. For access or collaboration inquiries, please contact the repository owner.

---

## 📄 License

This project is proprietary software. All rights reserved.

---

<div align="center">

**Built with ❤️ using Python & FastAPI**

</div>
