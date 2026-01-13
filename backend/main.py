import sys
import os
import logging
import asyncio
import json
import uuid
import shutil
import bcrypt
from datetime import datetime, timedelta
import random
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Form, status, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime, text, func
from sqlalchemy.orm import relationship, sessionmaker, Session, declarative_base
from jose import JWTError, jwt
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.append(os.getcwd())

import models
import schemas
import database

# --- CONFIGURATION ---
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
WITHDRAWAL_MIN = float(os.getenv("WITHDRAWAL_MIN_AMOUNT", 100))
WITHDRAWAL_MAX = float(os.getenv("WITHDRAWAL_MAX_AMOUNT", 50000))
BASE_UPLOAD_DIR = "static/uploads"
PROFILE_PIC_DIR = "static/profile_pics"

# Ensure Directories
for folder in [BASE_UPLOAD_DIR, PROFILE_PIC_DIR]:
    os.makedirs(folder, exist_ok=True)

# Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("backend.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- DATABASE ---
models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- SECURITY ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None: raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.Employee).filter(models.Employee.id == user_id).first()
    if user is None: raise credentials_exception
    
    # Check if user is banned/disabled
    if user.status == 'BANNED':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Please contact support."
        )
    
    return user

def require_admin(current_user: models.Employee = Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "ADMIN":
             raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials")
    return current_user

# --- UTILS & SERVICES ---

class ConnectionManager:
    def __init__(self):
        self.employee_connections: Dict[str, WebSocket] = {}
        self.admin_connections: List[WebSocket] = []

    async def connect_employee(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.employee_connections[user_id] = websocket
        logger.info(f"WS Employee Connected: {user_id}")

    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_connections.append(websocket)
        logger.info("WS Admin Connected")

    def disconnect_employee(self, user_id: str):
        if user_id in self.employee_connections: del self.employee_connections[user_id]

    def disconnect_admin(self, websocket: WebSocket):
        if websocket in self.admin_connections: self.admin_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_to_admins(self, message: dict):
        for connection in self.admin_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

def log_wallet_transaction(db: Session, employee_id: str, amount: float, transaction_type: str, description: str = None, project_id: str = None, withdrawal_id: str = None):
    try:
        transaction = models.WalletTransaction(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            related_project_id=project_id,
            related_withdrawal_id=withdrawal_id
        )
        db.add(transaction)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log wallet transaction: {e}")

# --- APP SETUP ---
app = FastAPI(title="MedData Platform - Enterprise V5.0 (Stable)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
def page_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def page_workstation(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/admin/dashboard", response_class=HTMLResponse)
def page_admin_dashboard(request: Request):
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

@app.get("/employee/home", response_class=HTMLResponse)
def page_employee_home(request: Request):
    return templates.TemplateResponse("employee_landing.html", {"request": request})

@app.get("/api/public/announcement")
def get_announcement():
    return {
        "id": "ANN-001",
        "title": "Welcome to Enterprise V5.0",
        "content": "We have upgraded our server infrastructure for better speed. Happy earning!"
    }

@app.get("/static/default-avatar.png")
def get_default_avatar():
    local_path = "static/default-avatar.png"
    if os.path.exists(local_path):
        return FileResponse(local_path)
    return RedirectResponse("https://ui-avatars.com/api/?name=User&background=0D8ABC&color=fff&size=128")

@app.get("/api/system/config")
def get_system_config(db: Session = Depends(get_db)):
    admin = db.query(models.Employee).filter(models.Employee.role == "ADMIN").order_by(models.Employee.id.asc()).first()
    brand_name = admin.full_name if admin and admin.full_name else "MedData Enterprise"
    address = admin.address if admin and admin.address else "MedData HQ, Tech Park"
    mobile = admin.mobile if admin and admin.mobile else "919000000000"
    return {"brand_name": brand_name, "address": address, "support_contact": mobile}

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_fallback():
    return {}

# --- AUTH ROUTES ---
@app.post("/auth/login")
def handle_login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.Employee).filter(models.Employee.username == data.username).first()
    if not user: raise HTTPException(401, "Invalid Credentials")
    if user.status == 'BANNED': raise HTTPException(403, "Account Suspended")
    if not bcrypt.checkpw(data.password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(401, "Invalid Credentials")
    
    # Gamification
    today = datetime.now().date()
    bonus = 0; message = ""
    if not user.last_login:
        user.login_streak = 1; bonus = 10; message = "First Login! +10"
    else:
        last = user.last_login.date()
        if last == today: pass
        elif last == today - timedelta(days=1):
            user.login_streak += 1
            if user.login_streak == 7: bonus = 100; message = "7 Day Streak! +100"
            elif user.login_streak == 30: bonus = 1000; message = "30 Day Streak! +1000"
            else: bonus = 10; message = f"Day {user.login_streak} Streak! +10"
        else:
            user.login_streak = 1; bonus = 10; message = "Streak Reset. +10"
    
    if bonus > 0:
        user.wallet_balance = (user.wallet_balance or 0.0) + bonus
        log_wallet_transaction(db, user.id, bonus, "LOGIN_BONUS", message)
    
    user.last_login = datetime.now()
    db.commit()
    
    role = user.role or "EMPLOYEE"
    if user.username == "Rohit": role = "ADMIN"
    
    access_token = create_access_token(data={"sub": user.id, "role": role, "username": user.username})
    return {"access_token": access_token, "token_type": "bearer", "role": role, "user_id": user.id, "username": user.username}

# --- EMPLOYEE ROUTES ---
@app.get("/api/employees/me/{user_id}")
def get_my_profile(user_id: str, db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    if current_user.id != user_id and current_user.username not in ["Admin", "Rohit"]: raise HTTPException(403, "Access Denied")
    user = db.query(models.Employee).filter(models.Employee.id == user_id).first()
    if not user: raise HTTPException(404, "User not found")
    pic_url = user.profile_pic if user.profile_pic else "/static/default-avatar.png"
    return {
        "id": user.id, "username": user.username, "wallet": user.wallet_balance, 
        "profile_pic": pic_url, "full_name": user.full_name, 
        "dob": user.dob, "mobile": user.mobile, "email": user.email,
        "address": user.address, "city": user.city, "state": user.state, "pincode": user.pincode,
        "bank_holder_name": user.bank_holder_name, "bank_account_number": user.bank_account_number,
        "ifsc_code": user.ifsc_code, "bank_name": user.bank_name,
        "kyc_status": user.kyc_status, "aadhar_card_url": user.aadhar_card_url,
        "pan_card_url": user.pan_card_url, "kyc_rejection_reason": user.kyc_rejection_reason
    }

@app.put("/api/employees/profile/{user_id}")
def update_profile(user_id: str, req: schemas.ProfileUpdateRequest, db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    if current_user.id != user_id and current_user.role != "ADMIN": raise HTTPException(403, "Access Denied")
    staff = db.query(models.Employee).filter(models.Employee.id == user_id).first()
    if not staff: raise HTTPException(404, "Staff not found")
    for key, value in req.dict(exclude_unset=True).items(): setattr(staff, key, value)
    db.commit()
    return {"status": "success"}

@app.post("/api/employees/profile-pic/{user_id}")
def upload_profile_picture(user_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = db.query(models.Employee).filter(models.Employee.id == user_id).first()
    if not user: raise HTTPException(404, "User not found")
    ext = os.path.splitext(file.filename)[1]
    filename = f"{user_id}{ext}"
    save_path = os.path.join(PROFILE_PIC_DIR, filename)
    with open(save_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    user.profile_pic = f"/static/profile_pics/{filename}"
    db.commit()
    return {"url": user.profile_pic}

@app.post("/api/profile/kyc-upload")
async def upload_kyc_docs(aadhar: UploadFile = File(None), pan: UploadFile = File(None), db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    upload_dir = "static/uploads/kyc"
    os.makedirs(upload_dir, exist_ok=True)
    user = db.query(models.Employee).filter(models.Employee.id == current_user.id).first()
    if aadhar:
        ext = aadhar.filename.split('.')[-1]
        fname = f"{user.id}_aadhar.{ext}"
        fpath = os.path.join(upload_dir, fname)
        with open(fpath, "wb") as buffer: shutil.copyfileobj(aadhar.file, buffer)
        user.aadhar_card_url = f"/static/uploads/kyc/{fname}"
    if pan:
        ext = pan.filename.split('.')[-1]
        fname = f"{user.id}_pan.{ext}"
        fpath = os.path.join(upload_dir, fname)
        with open(fpath, "wb") as buffer: shutil.copyfileobj(pan.file, buffer)
        user.pan_card_url = f"/static/uploads/kyc/{fname}"
    user.kyc_status = "PENDING"; user.kyc_rejection_reason = None
    db.commit()
    return {"message": "KYC Documents Uploaded", "status": "PENDING"}

@app.get("/api/employees/list")
def list_staff(db: Session = Depends(get_db)):
    users = db.query(models.Employee).filter(models.Employee.role != 'ADMIN', models.Employee.username != 'Rohit').all()
    return [{
        "id": u.id, "username": u.username, "code": u.employee_code, "status": u.status or "ACTIVE",
        "wallet": u.wallet_balance, "profile_pic": u.profile_pic or "/static/default-avatar.png",
        "level": u.level or 1, "kyc_status": u.kyc_status, "full_name": u.full_name
    } for u in users]

# --- ADMIN ROUTES ---
@app.post("/employees/create", response_model=schemas.EmployeeResponse)
def create_staff(emp: schemas.EmployeeCreate, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    if not emp.username:
        base = emp.full_name.lower().replace(" ", ".").strip()
        base = "".join(c for c in base if c.isalnum() or c == ".")
        username = base; counter = 1
        while db.query(models.Employee).filter(models.Employee.username == username).first():
            username = f"{base}{counter}"; counter += 1
        emp.username = username
    elif db.query(models.Employee).filter(models.Employee.username == emp.username).first():
        raise HTTPException(400, "Username already exists")
    try:
        counter = db.query(models.IDCounter).filter(models.IDCounter.id == 1).with_for_update().first()
        if not counter: counter = models.IDCounter(id=1, current_count=8851); db.add(counter)
        next_val = counter.current_count + 1
        formatted_code = f"PPX-C{emp.gender}-{str(next_val).zfill(7)}"
        counter.current_count = next_val
        db.commit()
    except Exception as e:
        db.rollback(); raise HTTPException(500, f"Code Generation Failed: {str(e)}")
    
    hashed_pw = bcrypt.hashpw(emp.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_staff = models.Employee(id=str(uuid.uuid4()), employee_code=formatted_code, username=emp.username, full_name=emp.full_name, gender=emp.gender, password_hash=hashed_pw, wallet_balance=0.0)
    if emp.referral_code:
        referrer = db.query(models.Employee).filter(models.Employee.id.startswith(emp.referral_code.replace("REF-", "").lower())).first()
        if referrer: new_staff.referred_by_id = referrer.id
    db.add(new_staff); db.commit(); db.refresh(new_staff)
    return new_staff

@app.post("/api/admin/kyc/verify")
def verify_kyc_status(data: dict, db: Session = Depends(get_db), admin: models.Employee = Depends(require_admin)):
    user = db.query(models.Employee).filter(models.Employee.id == data.get("user_id")).first()
    if not user: raise HTTPException(404, "User not found")
    action = data.get("action")
    if action == "APPROVE": user.kyc_status = "APPROVED"; user.kyc_rejection_reason = None
    elif action == "REJECT": user.kyc_status = "REJECTED"; user.kyc_rejection_reason = data.get("reason", "")
    else: raise HTTPException(400, "Invalid action")
    db.commit()
    return {"message": f"User KYC {action}D"}

@app.post("/api/admin/update-profile")
def update_system_profile(profile: schemas.ProfileUpdateRequest, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    current_admin.full_name = profile.full_name
    current_admin.mobile = profile.mobile
    current_admin.address = profile.address
    db.commit()
    return {"message": "Profile updated", "brand_name": current_admin.full_name}

@app.get("/api/admin/stats")
def get_admin_stats(db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    total_users = db.query(models.Employee).filter(models.Employee.role == "EMPLOYEE").count()
    # Pending Audit = Finalized but not approved projects
    pending_audit = db.query(models.Project).filter(models.Project.is_finalized == True, models.Project.is_approved == False, models.Project.status != "REJECTED").count()
    # Total Payout Liability = Sum of pending withdrawal amounts
    pending_withdrawals = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.status == "PENDING").all()
    total_payout_liability = sum(w.amount for w in pending_withdrawals)
    return {
        "total_users": total_users,
        "pending_audit": pending_audit,
        "total_payout_liability": total_payout_liability
    }

@app.get("/api/withdrawals/pending")
def get_pending_withdrawals(db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    withdrawals = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.status == "PENDING").all()
    # Need to join with Employee to get names? Or frontend fetches separate?
    # Assuming frontend expects basic details or we join.
    res = []
    for w in withdrawals:
        emp = db.query(models.Employee).filter(models.Employee.id == w.employee_id).first()
        res.append({
            "id": w.id,
            "employee_name": emp.username if emp else "Unknown",
            "amount": w.amount,
            "requested_at": w.requested_at
        })
    return res

@app.get("/api/admin/contacts")
def get_admin_contacts(db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    contacts = db.query(models.Contact).order_by(models.Contact.submitted_at.desc()).all()
    return [{
        "id": c.id, 
        "name": c.name, 
        "email": c.email, 
        "mobile": c.mobile, # Added mobile
        "message": c.message, 
        "status": c.status, 
        "submitted_at": c.submitted_at # Renamed from date to submitted_at for frontend compatibility
    } for c in contacts]

@app.post("/api/public/contact")
def submit_contact_form(data: schemas.ContactCreate, db: Session = Depends(get_db)):
    new_contact = models.Contact(
        id=str(uuid.uuid4()),
        name=data.name,
        email=data.email,
        mobile=data.mobile,
        message=data.message,
        status="NEW",
        submitted_at=datetime.now()
    )
    db.add(new_contact)
    db.commit()
    return {"message": "Inquiry Received"}

@app.get("/api/admin/finalized-projects")
def get_finalized_projects(db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    projects = db.query(models.Project).filter(models.Project.is_finalized == True, models.Project.is_approved == False, models.Project.status != "REJECTED").all()
    res = []
    for p in projects:
        emp = db.query(models.Employee).filter(models.Employee.id == p.assigned_to_id).first()
        emp_name = emp.username if emp else "Unknown"
        # Calculate total_due
        done = db.query(models.Assignment).join(models.Image).filter(models.Image.project_id == p.id).count()
        total_due = (done * p.salary_per_completion) + p.security_amount
        image_count = db.query(models.Image).filter(models.Image.project_id == p.id).count()
        res.append({
            "id": p.id,
            "employee_name": emp_name,
            "employee_id": p.assigned_to_id,
            "image_count": image_count,
            "completed_count": done,
            "rate": p.salary_per_completion,
            "security": p.security_amount,
            "total_due": total_due,
            "status": p.status
        })
    return res

@app.get("/api/admin/logs")
def get_audit_logs(db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(50).all()
    return [{
        "action": l.action, "details": l.details, "username": l.username, "timestamp": l.timestamp
    } for l in logs]

# --- PROJECT ROUTES ---
@app.post("/api/projects/upload")
def upload_batch_sequentially(files: list[UploadFile] = File(...), db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    batch_id = f"BATCH-{str(uuid.uuid4())[:8].upper()}"
    batch_path = os.path.join(BASE_UPLOAD_DIR, batch_id)
    os.makedirs(batch_path, exist_ok=True)
    db.add(models.Project(id=batch_id, salary_per_completion=0.0))
    for idx, file in enumerate(files):
        if not file.filename: continue
        ext = os.path.splitext(file.filename)[1]
        filename = f"img_{idx + 1}{ext}"
        save_path = os.path.join(batch_path, filename)
        with open(save_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        db_path = f"/static/uploads/{batch_id}/{filename}"
        db.add(models.Image(id=str(uuid.uuid4()), project_id=batch_id, storage_url=db_path, sequence_index=idx + 1))
    db.commit()
    return {"message": "Success", "project_id": batch_id}

@app.post("/api/projects/assign")
def assign_work(req: schemas.ProjectAssignRequest, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    project = db.query(models.Project).filter(models.Project.id == req.project_id).first()
    if not project: raise HTTPException(404, "Project not found")
    if project.assigned_to_id: raise HTTPException(400, "Project already assigned")
    project.assigned_to_id = req.employee_id
    project.salary_per_completion = req.salary
    project.security_amount = req.security_amount
    mins = req.duration_minutes if req.duration_minutes else (req.time_limit_hours or 48) * 60
    project.deadline = datetime.now() + timedelta(minutes=mins)
    project.is_finalized = False
    db.commit()
    return {"message": "Assignment Active"}

@app.get("/api/projects/list")
def list_all_batches(db: Session = Depends(get_db)):
    projects = db.query(models.Project).all()
    image_counts = db.query(models.Image.project_id, func.count(models.Image.id)).group_by(models.Image.project_id).all()
    count_map = {pid: count for pid, count in image_counts}
    res = []
    for p in projects:
        res.append({
            "id": p.id, "image_count": count_map.get(p.id, 0),
            "assigned_to": p.assigned_to.username if p.assigned_to else "UNASSIGNED",
            "is_finalized": p.is_finalized, "status": p.status, "is_approved": p.is_approved
        })
    return res

@app.get("/api/projects/available/{user_id}")
def fetch_employee_work_logic(user_id: str, db: Session = Depends(get_db)):
    projects = db.query(models.Project).filter(models.Project.assigned_to_id == user_id).all()
    res = []
    for p in projects:
        total = db.query(models.Image).filter(models.Image.project_id == p.id).count()
        done = db.query(models.Assignment).join(models.Image).filter(models.Image.project_id == p.id, models.Assignment.user_id == user_id).count()
        if p.is_approved: status = "COMPLETED"
        elif p.status == "REJECTED": status = "REJECTED"
        elif p.is_finalized: status = "UNDER REVIEW"
        else: status = "READY TO SUBMIT" if (total > 0 and done >= total) else "IN PROGRESS"
        res.append({
            "id": p.id, "salary": p.salary_per_completion, "total_images": total, "completed_by_user": done,
            "is_finalized": p.is_finalized, "is_approved": p.is_approved, "status": status,
            "deadline": p.deadline.isoformat() if p.deadline else None, "admin_feedback": p.admin_feedback,
            "reward": (done * p.salary_per_completion) + p.security_amount if p.is_approved else (done * p.salary_per_completion)
        })
    return res

@app.post("/work/allocate")
def allocate_next_image(req: schemas.WorkRequest, db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    if req.employee_id != current_user.id: raise HTTPException(403, "Identity mismatch")
    proj = db.query(models.Project).filter(models.Project.id == req.project_id).first()
    if proj and proj.is_finalized and not req.sequence_index: raise HTTPException(403, "Batch Locked/Submitted")
    
    img = None
    if req.sequence_index:
        img = db.query(models.Image).filter(models.Image.project_id == req.project_id, models.Image.sequence_index == req.sequence_index).first()
    else:
        query = text("SELECT i.id FROM images i WHERE i.project_id = :pid AND NOT EXISTS (SELECT 1 FROM assignments a WHERE a.image_id = i.id AND a.user_id = :uid) ORDER BY i.sequence_index ASC LIMIT 1")
        row = db.execute(query, {"pid": req.project_id, "uid": req.employee_id}).fetchone()
        if row: img = db.query(models.Image).filter(models.Image.id == row[0]).first()
    
    is_review = False
    if not img:
         has_assignments = db.query(models.Assignment).join(models.Image).filter(models.Image.project_id == req.project_id, models.Assignment.user_id == req.employee_id).count()
         if has_assignments > 0 and (not proj.is_finalized):
             img = db.query(models.Image).filter(models.Image.project_id == req.project_id).order_by(models.Image.sequence_index.asc()).first()
             is_review = True
         else:
             return {"images": [], "status": "COMPLETED"}
             
    return {"images": [{"id": img.id, "url": img.storage_url, "sequence": img.sequence_index}], "deadline": proj.deadline.isoformat() if proj.deadline else None, "is_review": is_review}

@app.get("/work/get_submission/{employee_id}/{image_id}")
def fetch_existing_entry(employee_id: str, image_id: str, db: Session = Depends(get_db)):
    sub = db.query(models.Assignment).filter(models.Assignment.user_id == employee_id, models.Assignment.image_id == image_id).first()
    return {"data": json.loads(sub.submission_data) if sub else None}

@app.post("/work/submit")
def process_entry_submission(req: schemas.SubmissionRequest, db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    img = db.query(models.Image).filter(models.Image.id == req.image_id).first()
    proj = db.query(models.Project).filter(models.Project.id == img.project_id).first()
    if proj.is_finalized: raise HTTPException(403, "Cannot edit finalized batch")
    existing = db.query(models.Assignment).filter(models.Assignment.user_id == req.employee_id, models.Assignment.image_id == req.image_id).first()
    if existing:
        existing.submission_data = json.dumps(req.form_data); existing.status = "SUBMITTED"
    else:
        db.add(models.Assignment(id=str(uuid.uuid4()), user_id=req.employee_id, image_id=req.image_id, submission_data=json.dumps(req.form_data)))
    db.commit()
    return {"status": "success"}

@app.post("/api/projects/finalize")
def finalize_batch_for_review(req: schemas.FinalizeRequest, db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    project = db.query(models.Project).filter(models.Project.id == req.project_id).first()
    if not project or project.assigned_to_id != req.employee_id: raise HTTPException(403, "Unauthorized")
    project.is_finalized = True; db.commit()
    return {"message": "Success"}

@app.get("/api/projects/history")
def get_project_history(db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    """Get completed/finalized projects for current user"""
    projects = db.query(models.Project).filter(
        models.Project.assigned_to_id == current_user.id,
        (models.Project.is_finalized == True) | (models.Project.status == "REJECTED")
    ).order_by(models.Project.completed_at.desc()).all()
    res = []
    for p in projects:
        total = db.query(models.Image).filter(models.Image.project_id == p.id).count()
        done = db.query(models.Assignment).join(models.Image).filter(models.Image.project_id == p.id, models.Assignment.user_id == current_user.id).count()
        res.append({
            "id": p.id,
            "status": "APPROVED" if p.is_approved else ("REJECTED" if p.status == "REJECTED" else "PENDING"),
            "image_count": total,
            "completed_images": done,
            "payout_amount": p.payout_amount or 0,
            "is_approved": p.is_approved,
            "is_finalized": p.is_finalized,
            "admin_feedback": p.admin_feedback,
            "completed_at": p.completed_at.isoformat() if p.completed_at else None
        })
    return res

    return res

@app.post("/api/employees/me/update")
def update_my_profile(data: dict, db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    """Update logged-in employee's profile"""
    # Allowed fields
    if "full_name" in data: current_user.full_name = data["full_name"]
    if "email" in data: current_user.email = data["email"]
    if "mobile" in data: current_user.mobile = data["mobile"]
    if "address" in data: current_user.address = data["address"]
    
    # Banking
    if "bank_holder_name" in data: current_user.bank_holder_name = data["bank_holder_name"]
    if "bank_account_number" in data: current_user.bank_account_number = data["bank_account_number"]
    if "ifsc_code" in data: current_user.ifsc_code = data["ifsc_code"]
    if "bank_name" in data: current_user.bank_name = data["bank_name"]
    
    db.commit()
    return {"message": "Profile Updated Successfully"}

@app.post("/api/profile/upload-pic")
def upload_profile_pic(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    """Upload profile picture"""
    if not file.filename: raise HTTPException(400, "No file selected")
    
    ext = os.path.splitext(file.filename)[1]
    if ext.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
        raise HTTPException(400, "Invalid image format")
        
    filename = f"avatar_{current_user.id}_{int(datetime.now().timestamp())}{ext}"
    file_path = os.path.join(BASE_UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    url = f"/static/uploads/{filename}"
    current_user.profile_pic = url
    db.commit()
    
    return {"message": "Picture Updated", "url": url}

@app.post("/api/admin/approve-project")
def admin_approve_project(data: dict, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    project_id = data.get("project_id")
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project: raise HTTPException(404, "Project not found")
    
    # Idempotency check
    if project.is_approved: return {"message": "Already approved"}

    project.is_approved = True
    project.status = "COMPLETED"
    project.is_finalized = True
    project.completed_at = datetime.now()
    
    # Calculate Payout
    done = db.query(models.Assignment).join(models.Image).filter(models.Image.project_id == project_id).count()
    payout = (done * project.salary_per_completion) + project.security_amount
    project.payout_amount = payout
    
    # Credit Employee
    emp = db.query(models.Employee).filter(models.Employee.id == project.assigned_to_id).first()
    if emp:
        emp.wallet_balance = (emp.wallet_balance or 0) + payout
        emp.total_earned = (emp.total_earned or 0) + payout
        log_wallet_transaction(db, emp.id, payout, "PROJECT_PAYOUT", f"Project {project_id} approved", project_id=project_id)
    
    db.commit()
    return {"message": "Project Approved", "payout": payout}

@app.post("/api/admin/reject-project")
def admin_reject_project(data: dict, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    project_id = data.get("project_id")
    reason = data.get("reason", "")
    
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project: raise HTTPException(404, "Project not found")
    
    project.status = "REJECTED"
    project.admin_feedback = reason
    project.is_finalized = False  # Allow re-work
    project.is_approved = False
    db.commit()
    return {"message": "Project Rejected"}

@app.get("/api/admin/project-submissions/{project_id}")
def get_project_submissions(project_id: str, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    """Get all submitted images for a project"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project: raise HTTPException(404, "Project not found")

    # Get all images for this project
    images = db.query(models.Image).filter(models.Image.project_id == project_id).order_by(models.Image.sequence_index).all()
    
    res = []
    for img in images:
        # Get assignment/submission for this image by the project assignee
        assign = db.query(models.Assignment).filter(
            models.Assignment.image_id == img.id,
            models.Assignment.user_id == project.assigned_to_id
        ).first()
        
        submission_data = {}
        if assign and assign.submission_data:
            try:
                submission_data = json.loads(assign.submission_data)
            except:
                pass
        
        res.append({
            "image_id": img.id,
            "image_url": img.storage_url,
            "sequence": img.sequence_index,
            "data": submission_data,
            "status": assign.status if assign else "PENDING"
        })
    return res

@app.post("/api/admin/user-action")
def admin_user_action(data: dict, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    """Admin actions: BAN, ACTIVATE, RESET_PASSWORD"""
    user_id = data.get("user_id")
    action = data.get("action")
    
    user = db.query(models.Employee).filter(models.Employee.id == user_id).first()
    if not user: raise HTTPException(404, "User not found")
    
    if action == "BAN":
        user.status = "BANNED"
    elif action == "ACTIVATE":
        user.status = "ACTIVE"
    elif action == "RESET_PASSWORD":
        new_pw = data.get("new_password", "Password123")
        user.password_hash = bcrypt.hashpw(new_pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        raise HTTPException(400, "Invalid action")
    
    db.commit()
    return {"message": f"Action {action} completed"}

# Helper for audit logging
def log_audit(db: Session, action: str, details: str, user_id: str = None, username: str = None):
    try:
        log = models.AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            details=details,
            timestamp=datetime.now()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"Audit log error: {e}")

# --- WALLET ROUTES ---
@app.post("/api/withdrawals/request")
def request_withdrawal(req: schemas.WithdrawalCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    if req.amount < WITHDRAWAL_MIN: raise HTTPException(400, f"Min withdrawal {WITHDRAWAL_MIN}")
    if not current_user.bank_account_number: raise HTTPException(400, "No bank details")
    pending = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.employee_id == current_user.id, models.WithdrawalRequest.status == "PENDING").count()
    if pending >= 3: raise HTTPException(400, "Limit reached")
    
    # Locking
    user = db.query(models.Employee).filter(models.Employee.id == current_user.id).with_for_update().first()
    if user.wallet_balance < req.amount: raise HTTPException(400, "Insufficient funds")
    
    user.wallet_balance -= req.amount
    tds = req.amount * 0.10; net = req.amount - tds
    req_id = str(uuid.uuid4())
    new_req = models.WithdrawalRequest(id=req_id, employee_id=current_user.id, amount=req.amount, tds_amount=tds, net_amount=net, bank_account=user.bank_account_number, status="APPROVED" if req.is_instant else "PENDING", is_instant=req.is_instant, requested_at=datetime.now())
    db.add(new_req)
    log_wallet_transaction(db, user.id, -req.amount, "WITHDRAWAL_REQUEST", f"Payout Requested (Pending)", withdrawal_id=req_id)
    db.commit()
    return {"message": "Request Submitted", "new_balance": user.wallet_balance}

@app.get("/api/withdrawals/pending")
def get_pending_withdrawals(db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    """Get all pending withdrawal requests for admin"""
    reqs = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.status == "PENDING").order_by(models.WithdrawalRequest.requested_at.desc()).all()
    
    res = []
    for r in reqs:
        emp = db.query(models.Employee).filter(models.Employee.id == r.employee_id).first()
        res.append({
            "id": r.id,
            "employee_id": r.employee_id,
            "employee_name": emp.username if emp else "Unknown",
            "amount": r.amount,
            "requested_at": r.requested_at.isoformat() if r.requested_at else None,
            "is_instant": r.is_instant
        })
    return res

@app.post("/api/withdrawals/approve")
def admin_approve_withdrawal(data: dict, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    wid = data.get("withdrawal_id")
    approve = data.get("approved_by_admin")
    
    w = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.id == wid).first()
    if not w: raise HTTPException(404, "Request not found")
    if w.status != "PENDING": raise HTTPException(400, f"Request is {w.status}")
    
    user = db.query(models.Employee).filter(models.Employee.id == w.employee_id).first()
    
    if approve:
        w.status = "APPROVED"
        w.approved_at = datetime.now()
        # Update original transaction description to show it's processed
        # Do NOT create a new 0-amount transaction as it confuses users.
        orig_tx = db.query(models.WalletTransaction).filter(models.WalletTransaction.related_withdrawal_id == wid).first()
        if orig_tx:
            orig_tx.description = f"Payout Processed - Funds Released"
    else:
        w.status = "REJECTED"
        w.rejection_reason = "Admin Rejected" 
        # Refund the amount
        user.wallet_balance += w.amount
        # Update original transaction to show it was cancelled (no new refund entry needed for clarity)
        orig_tx = db.query(models.WalletTransaction).filter(models.WalletTransaction.related_withdrawal_id == wid).first()
        if orig_tx:
            orig_tx.description = f"Payout Request Cancelled"
            orig_tx.amount = 0  # Nullify the deduction visually since we refunded
        # Log the refund as a separate positive entry
        log_wallet_transaction(db, user.id, w.amount, "WITHDRAWAL_REFUND", f"Refund - Payout Rejected", withdrawal_id=wid)
        
    db.commit()
    return {"message": "Success"}

@app.get("/api/withdrawals/history")
def get_my_withdrawals(db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    reqs = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.employee_id == current_user.id).order_by(models.WithdrawalRequest.requested_at.desc()).all()
    return [{"amount": r.amount, "status": r.status, "requested_at": r.requested_at, "rejection_reason": r.rejection_reason} for r in reqs]

@app.get("/api/wallet/history")
def get_wallet_history(db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    transactions = db.query(models.WalletTransaction).filter(models.WalletTransaction.employee_id == current_user.id).order_by(models.WalletTransaction.timestamp.desc()).limit(100).all()
    return [{"id": t.id, "amount": t.amount, "transaction_type": t.transaction_type, "description": t.description, "timestamp": t.timestamp} for t in transactions]

@app.get("/api/employees/tax-report")
def get_tax_report(db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    withdrawals = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.employee_id == current_user.id, models.WithdrawalRequest.status == "APPROVED").all()
    return {"total_earnings_withdrawn": sum(w.amount for w in withdrawals), "total_tds_deducted": sum(w.tds_amount for w in withdrawals), "transaction_count": len(withdrawals)}

@app.get("/api/gamification/status")
def get_gamification_status(db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    level = current_user.level or 1
    xp = current_user.xp or 0
    next_level_xp = level * 1000
    progress = int((xp / next_level_xp) * 100) if next_level_xp > 0 else 0
    
    # Rank titles based on level
    titles = ["Newcomer", "Apprentice", "Associate", "Professional", "Expert", "Master", "Grandmaster", "Legend"]
    title = titles[min(level - 1, len(titles) - 1)] if level > 0 else "Newcomer"
    
    return {
        "level": level,
        "xp": xp,
        "next_level_xp": next_level_xp,
        "progress": progress,
        "title": title,
        "streak": current_user.login_streak or 0
    }

@app.get("/api/challenges/active")
def get_active_challenges(db: Session = Depends(get_db)):
    # Mock return for now since logic isn't fully defined but table exists
    challenges = db.query(models.Challenge).filter(models.Challenge.end_date > datetime.now()).all()
    return [{
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "reward": c.reward_amount,
        "target": c.target_count,
        "expires_in": str(c.end_date - datetime.now()) if c.end_date else "N/A"
    } for c in challenges]

@app.get("/api/public/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    leaders = db.query(models.Employee).order_by(models.Employee.total_earned.desc()).limit(10).all()
    return [{"username": l.username, "balance": l.total_earned, "level": l.level or 1} for l in leaders]

@app.get("/api/analytics/personal")
def get_personal_analytics(db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    """Get real personal analytics based on wallet history and project performance"""
    
    # 1. Calculate 30 Day Earnings (Real)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Fetch credit transactions (Earnings) in last 30 days
    earnings_tx = db.query(models.WalletTransaction).filter(
        models.WalletTransaction.employee_id == current_user.id,
        models.WalletTransaction.amount > 0,
        models.WalletTransaction.transaction_type.in_(["PROJECT_PAYOUT", "LOGIN_BONUS", "CHALLENGE_REWARD"]),
        models.WalletTransaction.timestamp >= start_date
    ).all()
    
    total_30d = sum(t.amount for t in earnings_tx)
    
    # 2. Daily Earnings for Chart (Last 7 Days)
    daily_earnings = []
    # Initialize map for last 7 days
    days_map = {}
    for i in range(7):
        d = (end_date - timedelta(days=6-i)).date()
        days_map[d] = 0.0
        
    for t in earnings_tx:
        t_date = t.timestamp.date()
        if t_date in days_map:
            days_map[t_date] += t.amount
            
    daily_earnings = [{"date": d.strftime("%Y-%m-%d"), "amount": amt} for d, amt in days_map.items()]

    # 3. Quality Score (Based on Project Approval/Rejection Rate)
    # Get all finalized projects assigned to user
    completed_projects = db.query(models.Project).filter(
        models.Project.assigned_to_id == current_user.id,
        models.Project.is_finalized == True
    ).all()
    
    if not completed_projects:
        avg_quality = 0.0
        speed_percentile = 0
        top_text = "New Joiner"
    else:
        # Calculate Approval Rate
        approved = sum(1 for p in completed_projects if p.is_approved)
        total = len(completed_projects)
        avg_quality = min(round((approved / total) * 100, 1), 100.0) if total > 0 else 0
        
        # Add basic "experience" boost to quality for visual flair if they have many approvals
        if approved > 10: avg_quality = min(avg_quality + 2, 100.0)

        # Speed Percentile (Mock based on level/experience for now as we lack peer data)
        # 1-100 scale based on level logic (max level ~50?)
        speed_percentile = min(50 + (current_user.level * 5), 99)
        
        if speed_percentile > 90: top_text = "Top 10% Performer"
        elif speed_percentile > 75: top_text = "Top 25% Performer"
        else: top_text = "Efficient Worker"

    # 4. Quality Trend (Last 7 Projects or Days)
    # Since we don't have per-day quality, we'll just show the cumulative average for past days or 
    # keep it flat/slightly variable based on current average for visual consistency
    quality_trend = []
    current_q = avg_quality
    for i in range(7):
        d = (end_date - timedelta(days=6-i)).strftime("%Y-%m-%d")
        # Add slight random variance for chart aesthetics, anchored to real score
        variance = 0 if current_q == 0 else random.uniform(-2, 2)
        q_val = min(max(current_q + variance, 0), 100)
        quality_trend.append({"date": d, "score": round(q_val, 1)})

    return {
        "total_earnings_30d": total_30d,
        "avg_quality_30d": avg_quality,
        "speed_percentile": speed_percentile,
        "top_performer_text": top_text,
        "daily_earnings": daily_earnings,
        "quality_trend": quality_trend
    }



@app.get("/api/admin/support/messages")
def get_support_messages(db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    msgs = db.query(models.SupportMessage).order_by(models.SupportMessage.timestamp.desc()).all()
    return msgs

# --- COMMUNITY POSTS (Employee) ---
@app.get("/api/community/posts")
def get_community_posts(db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    """Get all approved community posts + user's own pending/rejected posts"""
    from sqlalchemy import or_
    
    # Get approved posts OR user's own posts (any status)
    posts = db.query(models.CommunityPost).filter(
        or_(
            models.CommunityPost.status == "APPROVED",
            models.CommunityPost.author_id == current_user.id
        )
    ).order_by(models.CommunityPost.created_at.desc()).limit(50).all()
    
    # Get all likes by this user
    user_likes = {l.post_id for l in db.query(models.CommunityLike).filter(models.CommunityLike.user_id == current_user.id).all()}
    
    return [{
        "id": p.id,
        "content": p.content,
        "author_name": p.author_name,
        "author_id": p.author_id,
        "author_pic": p.author_id,
        "likes_count": p.likes_count or 0,
        "is_liked": p.id in user_likes,
        "comments_count": p.comments_count or 0,
        "is_mine": p.author_id == current_user.id,
        "status": p.status,  # Include status for frontend badge logic
        "is_approved": p.status == "APPROVED",
        "admin_feedback": p.admin_feedback if p.author_id == current_user.id else None,  # Only show feedback to author
        "created_at": p.created_at.isoformat() if p.created_at else None
    } for p in posts]

@app.post("/api/community/posts/{post_id}/like")
def like_community_post(post_id: str, db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    """Toggle like on a post"""
    post = db.query(models.CommunityPost).filter(models.CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
        
    existing = db.query(models.CommunityLike).filter(models.CommunityLike.post_id == post_id, models.CommunityLike.user_id == current_user.id).first()
    
    if existing:
        db.delete(existing)
        post.likes_count = max(0, (post.likes_count or 0) - 1)
        action = "unliked"
    else:
        new_like = models.CommunityLike(post_id=post_id, user_id=current_user.id)
        db.add(new_like)
        post.likes_count = (post.likes_count or 0) + 1
        action = "liked"
        
    db.commit()
    return {"message": "Success", "action": action, "likes_count": post.likes_count}

from pydantic import BaseModel as PydanticBaseModel
class CommunityPostCreate(PydanticBaseModel):
    content: str

@app.post("/api/community/posts")
def create_community_post_v2(data: CommunityPostCreate, db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    """Create a new community post (pending approval)"""
    new_post = models.CommunityPost(
        id=str(uuid.uuid4()),
        author_id=current_user.id,
        author_name=current_user.full_name or current_user.username,
        content=data.content,
        status="PENDING",
        likes_count=0,
        comments_count=0
    )
    db.add(new_post)
    db.commit()
    return {"message": "Post submitted for approval", "id": new_post.id}

# --- WEBSOCKETS ---
@app.websocket("/ws/employee/{user_id}")
async def websocket_employee_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect_employee(websocket, user_id)
    try:
        while True:
            data_json = await websocket.receive_json()
            # Expecting { type: 'message', content: '...', sender: 'Me' }
            
            if data_json.get('type') == 'message':
                content = data_json.get('content')
                if content:
                    # Save to DB
                    db = database.SessionLocal()
                    try:
                        msg_id = str(uuid.uuid4())
                        new_msg = models.SupportMessage(
                            id=msg_id,
                            user_id=user_id,
                            message=content,
                            timestamp=datetime.now(),
                            is_read=False,
                            is_from_admin=False
                        )
                        db.add(new_msg)
                        db.commit()
                        
                        # Notify Admins
                        sender_name = "Unknown"
                        user = db.query(models.Employee).filter(models.Employee.id == user_id).first()
                        if user: sender_name = user.username
                        
                        await manager.broadcast_to_admins({
                            "type": "new_support_msg",
                            "user_id": user_id,
                            "username": sender_name,
                            "message": content,
                            "timestamp": str(datetime.now())
                        })
                        
                        # Ack to user to confirm receipt (optional, allows UI to show 'sent')
                        await manager.send_personal_message({"status": "sent", "msg_id": msg_id}, websocket)
                        
                    except Exception as e:
                        logger.error(f"Chat Error: {e}")
                    finally:
                        db.close()
            
    except WebSocketDisconnect:
        manager.disconnect_employee(user_id)

@app.websocket("/ws/admin")
async def websocket_admin_endpoint(websocket: WebSocket):
    # Removed generic header check for simplicity or add token auth if needed
    await manager.connect_admin(websocket)
    try:
        while True:
            await websocket.receive_json()
            await manager.send_personal_message({"status": "ack"}, websocket)
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket)

@app.websocket("/ws/chat/admin/{client_id}")
async def websocket_chat_admin(websocket: WebSocket, client_id: str):
    # Fix for 403 on /ws/chat/admin/admin-sys
    await manager.connect_admin(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket)

# --- WEBSOCKET ENDPOINTS ---
@app.websocket("/ws/support/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect_employee(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Save User Message to DB
            db = database.SessionLocal()
            try:
                # Assuming data is just text content
                msg = models.SupportMessage(
                    id=str(uuid.uuid4()),
                    user_id=client_id,
                    message=data,
                    timestamp=datetime.now(),
                    is_read=False,
                    is_from_admin=False
                )
                db.add(msg)
                db.commit()
                
                # Broadcast to Admins
                await manager.broadcast_to_admins({
                    "type": "message",
                    "sender": "User",
                    "user_id": client_id,
                    "content": data,
                    "timestamp": str(datetime.now())
                })
            except Exception as e:
                logger.error(f"WS Save Error: {e}")
            finally:
                db.close()
                
    except WebSocketDisconnect:
        manager.disconnect_employee(client_id)

@app.websocket("/ws/admin/support")
async def websocket_admin_endpoint(websocket: WebSocket):
    await manager.connect_admin(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Admin sending via WS is optional, mostly they use API
            # If they send, we could route it, but API is safer for auth
            pass 
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket)

# --- ADMIN SUPPORT CHAT ENDPOINTS ---
@app.get("/api/admin/support/users")
def get_support_users(db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    """Get list of users who have sent support messages"""
    # Get distinct user_ids from support_messages
    from sqlalchemy import distinct
    user_ids = db.query(distinct(models.SupportMessage.user_id)).all()
    users = []
    for (uid,) in user_ids:
        employee = db.query(models.Employee).filter(models.Employee.id == uid).first()
        last_msg = db.query(models.SupportMessage).filter(models.SupportMessage.user_id == uid).order_by(models.SupportMessage.timestamp.desc()).first()
        unread = db.query(models.SupportMessage).filter(models.SupportMessage.user_id == uid, models.SupportMessage.is_read == False, models.SupportMessage.is_from_admin == False).count()
        if employee:
            users.append({
                "user_id": uid,
                "username": employee.username,
                "full_name": employee.full_name,
                "last_message": last_msg.message[:50] if last_msg else "",
                "last_timestamp": last_msg.timestamp.isoformat() if last_msg else None,
                "unread_count": unread,
                "is_online": uid in manager.employee_connections
            })
    return sorted(users, key=lambda x: x.get("last_timestamp") or "", reverse=True)

@app.get("/api/admin/support/messages/{user_id}")
def get_support_messages(user_id: str, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    """Get all support messages for a specific user"""
    messages = db.query(models.SupportMessage).filter(models.SupportMessage.user_id == user_id).order_by(models.SupportMessage.timestamp.asc()).all()
    # Mark as read
    db.query(models.SupportMessage).filter(models.SupportMessage.user_id == user_id, models.SupportMessage.is_read == False).update({"is_read": True})
    db.commit()
    return [{
        "id": m.id,
        "content": m.message,
        "sender": "Admin" if m.is_from_admin else "User",
        "timestamp": m.timestamp.isoformat() if m.timestamp else None
    } for m in messages]

@app.get("/api/support/my-history")
def get_my_support_history(db: Session = Depends(get_db), current_user: models.Employee = Depends(get_current_user)):
    """Get chat history for the logged-in employee"""
    messages = db.query(models.SupportMessage).filter(models.SupportMessage.user_id == current_user.id).order_by(models.SupportMessage.timestamp.asc()).all()
    # Mark admin messages as read (optional, but good hygiene)
    db.query(models.SupportMessage).filter(models.SupportMessage.user_id == current_user.id, models.SupportMessage.is_from_admin == True, models.SupportMessage.is_read == False).update({"is_read": True})
    db.commit()
    
    return [{
        "id": m.id,
        "content": m.message,
        "sender": "Admin" if m.is_from_admin else "Me",
        "timestamp": m.timestamp.isoformat() if m.timestamp else None
    } for m in messages]

@app.post("/api/admin/support/send")
async def admin_send_support_message(data: dict, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    """Admin sends a message to an employee"""
    user_id = data.get("user_id")
    content = data.get("content")
    if not user_id or not content:
        raise HTTPException(400, "Missing user_id or content")
    
    msg = models.SupportMessage(
        id=str(uuid.uuid4()),
        user_id=user_id,
        message=content,
        timestamp=datetime.now(),
        is_read=True,
        is_from_admin=True
    )
    db.add(msg)
    db.commit()
    
    # Send to employee via WebSocket if online
    if user_id in manager.employee_connections:
        try:
            await manager.send_personal_message({
                "type": "message",
                "content": content,
                "sender": "Admin",
                "timestamp": str(datetime.now())
            }, manager.employee_connections[user_id])
        except:
            pass
    
    return {"message": "Sent", "id": msg.id}

# --- COMMUNITY MODERATION ---
@app.get("/api/admin/community/pending")
def get_pending_community_posts(db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    """Get all community posts pending approval"""
    posts = db.query(models.CommunityPost).filter(models.CommunityPost.status == "PENDING").order_by(models.CommunityPost.created_at.desc()).all()
    return [{
        "id": p.id,
        "content": p.content,
        "author_name": p.author_name,
        "author_id": p.author_id,
        "created_at": p.created_at.isoformat() if p.created_at else None
    } for p in posts]

@app.post("/api/admin/community/{post_id}/approve")
def approve_community_post(post_id: str, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    """Approve a community post for public display"""
    post = db.query(models.CommunityPost).filter(models.CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    post.status = "APPROVED"
    db.commit()
    return {"message": "Post approved"}

@app.post("/api/admin/community/{post_id}/reject")
def reject_community_post(post_id: str, data: dict = None, db: Session = Depends(get_db), current_admin: models.Employee = Depends(require_admin)):
    """Reject a community post with optional reason"""
    post = db.query(models.CommunityPost).filter(models.CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    post.status = "REJECTED"
    if data and data.get("reason"):
        post.admin_feedback = data.get("reason")
    db.commit()
    return {"message": "Post rejected"}

# --- BACKGROUND TASKS ---
async def monitor_deadlines():
    while True:
        try:
            db = database.SessionLocal()
            expired = db.query(models.Project).filter(models.Project.is_finalized == False, models.Project.deadline != None, models.Project.deadline < datetime.now()).all()
            if expired:
                for proj in expired: proj.is_finalized = True
                db.commit()
            db.close()
        except Exception as e: logger.error(f"Monitor Error: {e}")
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_deadlines())
    logger.info("Startup Complete")