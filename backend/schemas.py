from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

# --- AUTH & TOKEN SCHEMAS (NEW) ---
class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: str
    username: str

class TokenData(BaseModel):
    user_id: str
    username: str
    role: str

# --- EMPLOYEE SCHEMAS ---
class EmployeeCreate(BaseModel):
    full_name: str  # Required for proper user identification
    username: Optional[str] = None  # Auto-generated from full_name if not provided
    password: str
    gender: str
    referral_code: Optional[str] = None

class EmployeeResponse(BaseModel):
    id: str
    employee_code: str
    username: str
    full_name: Optional[str] = None  # Added for display purposes
    gender: str
    status: str
    wallet_balance: float
    login_streak: int
    profile_pic: Optional[str] = None

    class Config:
        from_attributes = True

# --- SUPPORT SCHEMAS ---
class SupportMessageRequest(BaseModel):
    message: str

# --- PROJECT & WORKFLOW SCHEMAS ---
class ProjectAssignRequest(BaseModel):
    employee_id: str
    project_id: str
    salary: float
    security_amount: float
    time_limit_hours: Optional[int] = 48
    duration_minutes: Optional[int] = None # New Field for flexible timer

class WorkRequest(BaseModel):
    employee_id: str
    project_id: str
    sequence_index: Optional[int] = None

class SubmissionRequest(BaseModel):
    employee_id: str
    image_id: str
    form_data: Dict[str, Any]

class FinalizeRequest(BaseModel):
    employee_id: str
    project_id: str

class RejectProjectRequest(BaseModel):
    project_id: str
    reason: str

# --- PROFILE UPDATE SCHEMA ---
class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    dob: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    bank_holder_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None

# --- WITHDRAWAL SCHEMAS (NEW) ---
class WithdrawalCreate(BaseModel):
    amount: float
    is_instant: Optional[bool] = False
    method: Optional[str] = "NEFT" # Added to fix 422 error from frontend

class WithdrawalApproveRequest(BaseModel):
    withdrawal_id: str
    approved_by_admin: bool = True
    rejection_reason: Optional[str] = None

class ContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    message: str

class WithdrawalResponse(BaseModel):
    id: str
    employee_id: str
    amount: float
    status: str
    bank_account: str
    requested_at: datetime
    is_instant: bool = False
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # For Admin View
    employee_name: Optional[str] = None 

    class Config:
        from_attributes = True

# --- ANALYTICS ---
class DailyStat(BaseModel):
    date: str
    amount: float
    score: Optional[float] = None

class AnalyticsResponse(BaseModel):
    daily_earnings: List[DailyStat]
    quality_trend: List[DailyStat]
    total_earnings_30d: float
    avg_quality_30d: float
    speed_percentile: int # 0-100
    top_performer_text: str

# --- CHALLENGES ---
class ChallengeResponse(BaseModel):
    id: str
    title: str
    description: str
    target_count: int
    reward_amount: float
    end_date: datetime
    progress: int
    is_completed: bool
    is_claimed: bool

# --- CERTIFICATIONS ---
class CertificationComplete(BaseModel):
    cert_id: str
    score: float

# --- COMMUNITY ---
class CommunityPostResponse(BaseModel):
    id: str
    author_name: str
    content: str
    image_url: Optional[str] = None
    likes_count: int
    comments_count: int
    created_at: datetime
    is_liked: bool = False

class CreatePost(BaseModel):
    content: str

class CreateComment(BaseModel):
    content: str

class CertificationRequest(BaseModel):
    cert_id: str
    score: int