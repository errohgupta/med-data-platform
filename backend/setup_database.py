import sqlite3
import os
import bcrypt
import uuid

# Configuration
DB_FILE = "medical_platform.db"

def create_tables(cursor):
    """Initializes the database schema with Withdrawal, KYC, Banking, and Project fields."""
    print("--- Initializing Enterprise V4.3 Schema (Phase 1 Security) ---")
    
    # Enable Foreign Key Support
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. ID Counter Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS id_counter (
        id INTEGER PRIMARY KEY,
        current_count INTEGER NOT NULL
    )
    ''')
    cursor.execute("INSERT OR IGNORE INTO id_counter (id, current_count) VALUES (1, 8851)")

    # 2. Employees Table
    # 2. Employees Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id TEXT PRIMARY KEY,
        employee_code TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        gender TEXT NOT NULL,
        wallet_balance REAL DEFAULT 0.0,
        status TEXT DEFAULT 'ACTIVE',
        role TEXT DEFAULT 'EMPLOYEE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Gamification & Referrals --
        referred_by_id TEXT,
        certification_id TEXT,
        last_login TIMESTAMP,
        login_streak INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        total_earned REAL DEFAULT 0.0,
        
        profile_pic TEXT,
        
        -- Personal & KYC Details --
        full_name TEXT,
        dob TEXT,
        mobile TEXT,
        email TEXT,
        
        -- Physical Address --
        address TEXT,
        city TEXT,
        state TEXT,
        pincode TEXT,
        
        -- KYC Documents --
        kyc_status TEXT DEFAULT 'NOT_UPLOADED',
        aadhar_card_url TEXT,
        pan_card_url TEXT,
        kyc_rejection_reason TEXT,
        
        -- Indian Banking Details --
        bank_holder_name TEXT,
        bank_account_number TEXT,
        ifsc_code TEXT,
        bank_name TEXT,
        bank_branch TEXT
    )''')

    # 3. Projects Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        salary_per_completion REAL NOT NULL DEFAULT 0.0,
        security_amount REAL DEFAULT 0.0,
        time_limit_hours INTEGER DEFAULT 48,
        
        assigned_to_id TEXT,
        deadline TIMESTAMP,
        
        is_finalized BOOLEAN DEFAULT 0,
        is_approved BOOLEAN DEFAULT 0,
        security_refunded BOOLEAN DEFAULT 0,
        
        status TEXT DEFAULT 'PENDING',
        admin_feedback TEXT,
        completed_at TIMESTAMP,
        payout_amount REAL DEFAULT 0.0,
        
        FOREIGN KEY (assigned_to_id) REFERENCES employees (id)
    )''')

    # 4. Images Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS images (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        storage_url TEXT NOT NULL,
        sequence_index INTEGER NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )''')

    # 5. Assignments Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS assignments (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        image_id TEXT NOT NULL,
        status TEXT DEFAULT 'SUBMITTED',
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        submission_data TEXT,
        FOREIGN KEY (user_id) REFERENCES employees (id),
        FOREIGN KEY (image_id) REFERENCES images (id),
        UNIQUE(user_id, image_id)
    )''')

    # 6. Withdrawal Requests Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS withdrawal_requests (
        id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL,
        amount REAL NOT NULL,
        tds_amount REAL DEFAULT 0.0,
        net_amount REAL DEFAULT 0.0,
        bank_account TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING',
        is_instant BOOLEAN DEFAULT 0,
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP,
        approved_by TEXT,
        rejection_reason TEXT,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    )''')
    
    # 7. Wallet Transactions (NEW)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wallet_transactions (
        id TEXT PRIMARY KEY,
        employee_id TEXT NOT NULL,
        amount REAL NOT NULL,
        transaction_type TEXT NOT NULL,
        description TEXT,
        related_project_id TEXT,
        related_withdrawal_id TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    )''')
    
    # 8. Community Tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS community_posts (
        id TEXT PRIMARY KEY,
        author_id TEXT,
        author_name TEXT,
        content TEXT,
        image_url TEXT,
        likes_count INTEGER DEFAULT 0,
        comments_count INTEGER DEFAULT 0,
        is_approved BOOLEAN DEFAULT 0,
        status TEXT DEFAULT 'PENDING',
        admin_feedback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS community_likes (post_id TEXT, user_id TEXT, PRIMARY KEY(post_id, user_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS community_comments (id TEXT PRIMARY KEY, post_id TEXT, user_id TEXT, user_name TEXT, content TEXT, created_at TIMESTAMP)''')
    
    # 9. Audit Logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        username TEXT,
        action TEXT,
        details TEXT,
        ip_address TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        prev_hash TEXT,
        block_hash TEXT,
        FOREIGN KEY (user_id) REFERENCES employees (id)
    )''')
    
    # 10. Announcements
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create Indices for Performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_withdrawal_employee ON withdrawal_requests(employee_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_withdrawal_status ON withdrawal_requests(status)")

    print("✅ All database tables created successfully.")

def insert_seed_user(cursor, username, password, gender, emp_code, is_admin=False):
    """Hashes passwords and seeds initial master and employee data."""
    cursor.execute("SELECT username FROM employees WHERE username = ?", (username,))
    if cursor.fetchone():
        return

    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    user_id = str(uuid.uuid4())
    
    cursor.execute('''
    INSERT INTO employees (id, employee_code, username, gender, password_hash, wallet_balance, status)
    VALUES (?, ?, ?, ?, ?, 0.0, 'ACTIVE')
    ''', (user_id, emp_code, username, gender, hashed))
    
    print(f"✅ Created User: {username} (Code: {emp_code})")

def main():
    # Uncomment next line to wipe DB for fresh install
    # if os.path.exists(DB_FILE): os.remove(DB_FILE)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        create_tables(cursor)

        # SEED DATA
        insert_seed_user(cursor, "Rohit", "admin01", "M", "ADMIN-01", is_admin=True)
        insert_seed_user(cursor, "Admin", "admin123", "M", "MASTER-ADMIN", is_admin=True)
        insert_seed_user(cursor, "Vipin", "vipin01", "M", "PPX-CM-0008851")

        conn.commit()
        print("\n🚀 Database setup complete. You can now run 'uvicorn main:app --reload'")
        
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()