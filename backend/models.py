from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime

# 1. Counter Table
class IDCounter(Base):
    __tablename__ = "id_counter"
    id = Column(Integer, primary_key=True, index=True)
    current_count = Column(Integer, nullable=False, default=8851)

# 2. Employees Table
class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(String, primary_key=True, index=True) 
    employee_code = Column(String, unique=True, index=True) 
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    gender = Column(String)
    wallet_balance = Column(Float, default=0.0)
    status = Column(String, default="ACTIVE") # ACTIVE, BANNED
    role = Column(String, default="EMPLOYEE") # ADMIN, EMPLOYEE
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    referred_by_id = Column(String, nullable=True)
    certification_id = Column(String, nullable=True)
    
    # Gamification
    last_login = Column(DateTime, nullable=True)
    login_streak = Column(Integer, default=0)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    total_earned = Column(Float, default=0.0)

    profile_pic = Column(String, nullable=True)
    
    # KYC
    full_name = Column(String, nullable=True)
    dob = Column(String, nullable=True)
    mobile = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True)

    # KYC Details
    kyc_status = Column(String, default="NOT_UPLOADED") # NOT_UPLOADED, PENDING, APPROVED, REJECTED
    aadhar_card_url = Column(String, nullable=True)
    pan_card_url = Column(String, nullable=True)
    kyc_rejection_reason = Column(String, nullable=True)
    
    # Banking
    bank_holder_name = Column(String, nullable=True)
    bank_account_number = Column(String, nullable=True)
    ifsc_code = Column(String, nullable=True)
    bank_name = Column(String, nullable=True)
    bank_branch = Column(String, nullable=True)

    # Relationships
    assignments = relationship("Assignment", back_populates="employee")
    assigned_projects = relationship("Project", back_populates="assigned_to")
    withdrawals = relationship("WithdrawalRequest", back_populates="employee")
    wallet_transactions = relationship("WalletTransaction", back_populates="employee")

# 3. Withdrawal Requests (FIXED: Inherits from Base)
class WithdrawalRequest(Base): 
    __tablename__ = "withdrawal_requests"

    id = Column(String, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    amount = Column(Float, nullable=False) # Gross Amount
    tds_amount = Column(Float, default=0.0)
    net_amount = Column(Float, default=0.0)
    
    bank_account = Column(String, nullable=False)
    status = Column(String, default="PENDING", index=True) # PENDING, APPROVED, REJECTED
    is_instant = Column(Boolean, default=False)
    
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String, nullable=True) # Admin Username
    rejection_reason = Column(String, nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="withdrawals")

# NEW: Wallet Transaction History Model
class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    
    id = Column(String, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    amount = Column(Float, nullable=False)  # Positive for credit, negative for debit
    transaction_type = Column(String, nullable=False)  # "LOGIN_BONUS", "PROJECT_PAYOUT", "WITHDRAWAL", "CHALLENGE_REWARD", "SECURITY_REFUND"
    description = Column(String, nullable=True)
    related_project_id = Column(String, nullable=True)
    related_withdrawal_id = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    employee = relationship("Employee", back_populates="wallet_transactions")

# Contact/Lead Model
class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    mobile = Column(String, nullable=True)
    message = Column(String, nullable=True)
    status = Column(String, default="NEW")  # NEW, CONTACTED, CLOSED
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())


# 4. Projects Table
class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    salary_per_completion = Column(Float, nullable=False, default=0.0)
    security_amount = Column(Float, default=0.0)
    time_limit_hours = Column(Integer, default=48)
    
    assigned_to_id = Column(String, ForeignKey("employees.id"), nullable=True) 
    deadline = Column(DateTime, nullable=True)
    status = Column(String, default="IN_PROGRESS") # IN_PROGRESS, SUBMITTED, COMPLETED
    
    is_finalized = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    security_refunded = Column(Boolean, default=False)
    admin_feedback = Column(String, nullable=True) # For Rejection Comments
    completed_at = Column(DateTime, nullable=True)
    payout_amount = Column(Float, default=0.0) # Actual amount paid out
    
    images = relationship("Image", back_populates="project")
    assigned_to = relationship("Employee", back_populates="assigned_projects")

# 5. Images Table
class Image(Base):
    __tablename__ = "images"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"))
    storage_url = Column(String)
    sequence_index = Column(Integer)

    project = relationship("Project", back_populates="images")
    assignments = relationship("Assignment", back_populates="image")

# 6. Assignments Table
class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("employees.id"))
    image_id = Column(String, ForeignKey("images.id"))
    status = Column(String, default="SUBMITTED") 
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submission_data = Column(String, nullable=True)

    employee = relationship("Employee", back_populates="assignments")
    image = relationship("Image", back_populates="assignments")

# 7. Support Messages (NEW)
class SupportMessage(Base):
    __tablename__ = "support_messages"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("employees.id"))
    message = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False)
    is_from_admin = Column(Boolean, default=False)
    
    sender = relationship("Employee")

# 8. Contact Us Submissions
class ContactSubmission(Base):
    __tablename__ = "contact_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, nullable=True)
    mobile = Column(String)
    message = Column(String)
    status = Column(String, default="NEW")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 8. Challenges
class Challenge(Base):
    __tablename__ = "challenges"
    id = Column(String, primary_key=True)
    title = Column(String)
    description = Column(String)
    target_count = Column(Integer)
    reward_amount = Column(Float)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

class UserChallengeClaim(Base):
    __tablename__ = "user_challenge_claims"
    user_id = Column(String, primary_key=True)
    challenge_id = Column(String, primary_key=True)
    claimed_at = Column(DateTime, default=datetime.utcnow)

# 9. System Announcements
class Announcement(Base):
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 10. Community
class CommunityPost(Base):
    __tablename__ = "community_posts"
    id = Column(String, primary_key=True)
    author_id = Column(String)
    author_name = Column(String)
    content = Column(String)
    image_url = Column(String, nullable=True)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    is_approved = Column(Boolean, default=False)
    status = Column(String, default="PENDING") # PENDING, APPROVED, REJECTED
    admin_feedback = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CommunityLike(Base):
    __tablename__ = "community_likes"
    post_id = Column(String, primary_key=True)
    user_id = Column(String, primary_key=True)

class CommunityComment(Base):
    __tablename__ = "community_comments"
    id = Column(String, primary_key=True)
    post_id = Column(String)
    user_id = Column(String)
    user_name = Column(String)
    content = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("employees.id"), nullable=True) # Nullable for system events or failed logins
    username = Column(String, nullable=True) # Snapshot in case user is deleted
    action = Column(String, index=True)
    details = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Blockchain / Tamper Proof
    prev_hash = Column(String, nullable=True)
    block_hash = Column(String, nullable=True)