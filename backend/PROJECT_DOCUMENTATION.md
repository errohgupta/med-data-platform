# MedData Platform - Project Documentation

## 1. System Overview
MedData Platform is a comprehensive enterprise workforce management system designed for distributed data annotation teams. It connects administrators with remote employees, managing project assignments, quality control, payments, and community engagement in a unified environment.

## 2. Technology Stack
- **Backend**: Python (FastAPI)
- **Database**: SQLite (Production-ready schema with Foreign Keys)
- **Frontend**: HTML5, CSS3 (Modern Glassmorphism Design), Vanilla JavaScript
- **Communication**: WebSockets (Real-time Chat), REST APIs
- **Authentication**: JWT (JSON Web Tokens) with Bcrypt hashing

## 3. User Roles & Modules

### 3.1 Administrator (Master Role)
- **Staff Management**:
  - View all registered employees with status (Active/Banned/Verified).
  - Actions: Ban/Activate users, Reset passwords, View detailed profiles.
  - KYC Verification: Approve/Reject Aadhar & Pan card submissions.
- **Project Management**:
  - Create new data annotation projects.
  - Assign projects to specific employees with defined salary, security deposit, and deadlines.
  - Review & Finalize user submissions (Approve/Reject work batches).
- **Financial Control**:
  - View pending withdrawal requests.
  - Process payouts (Approve/Reject) with automatic TDS calculation.
  - View platform-wide financial analytics.
- **Community Moderation**:
  - Review pending community posts.
  - Approve for public view or Reject with feedback reason.
- **Support System**:
  - Real-time chat dashboard to support multiple employees simultaneously.
  - Broadcast system-wide announcements.

### 3.2 Employee (Data Specialist)
- **Dashboard**:
  - Personal stats: Earnings, Integrity Score, Speed Rank, Login Streak.
  - Gamification: XP Progress, Level badges, Daily Challenges.
- **Workstation**:
  - specialized interface for image data annotation.
  - Sequence-driven workflow with auto-save.
  - Batch submission for review.
- **Wallet & Payments**:
  - Real-time wallet balance tracking.
  - Detailed transaction history (Earnings, Bonuses, Withdrawals).
  - Withdrawal Request: Standard (NEFT) or Instant Payout options.
- **Community Hub**:
  - Share updates with colleagues (Text posts).
  - View peer posts (Like/Comment).
  - Status tracking: See own Pending/Rejected posts with Admin feedback.
- **Profile & Settings**:
  - KYC Upload (Aadhar/PAN).
  - Update Bank Details for payouts.
  - View personal support chat history.

## 4. Key Functional Features

### Authentication & Security
- **Secure Login**: JWT-based session management.
- **Ban Logic**: Instant session termination for banned users; API access blocked immediately.
- **Audit Logs**: Comprehensive logging of critical actions (Financials, Bans, Data Edits).

### Real-Time Communication
- **Support Chat**: 
  - Direct WebSocket connection between Employee and Admin.
  - Persistent chat history stored in database.
  - "admin_feedback" loop for rejected content.
- **Notifications**: Toast notifications for system events.

### Financial Engine
- **Earnings Logic**: 
  - Project completion fees.
  - Login Bonuses (Daily + Streak milestones).
- **Withdrawals**:
  - Minimum processing thresholds.
  - Tax (TDS) deduction logic.
  - Status tracking (Pending -> Approved/Rejected).

### Gamification Layer
- **XP System**: Earn XP for tasks and logins.
- **Leaderboard**: Global ranking based on earnings/performance.
- **Challenges**: Time-limited tasks (e.g., "Complete 50 Images") with bonus rewards.

## 5. Deployment Requirements

To host this project, ensure the following environment:

### System Requirements
- **OS**: Linux (Ubuntu 20.04+) or Windows Server
- **Python**: Version 3.9+
- **Disk Space**: Min 10GB (for image storage)
- **RAM**: Min 2GB

### Environment Variables (.env)
```ini
SECRET_KEY=your_secure_random_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
WITHDRAWAL_MIN_AMOUNT=500
WITHDRAWAL_MAX_AMOUNT=50000
```

### Installation Steps
1. Install Python 3.x
2. Install dependencies: `pip install -r requirements.txt`
3. Initialize Database: `python setup_database.py`
4. Run Server: `uvicorn main:app --host 0.0.0.0 --port 8000`
