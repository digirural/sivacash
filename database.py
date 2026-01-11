import sqlite3
import hashlib

DB_NAME = "cash_collection.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create Users Table with role and google_id
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT,
            role TEXT DEFAULT 'agent',
            google_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Collections Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            purpose TEXT NOT NULL,
            collection_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_admin_if_not_exists():
    conn = get_db_connection()
    c = conn.cursor()
    # Check if a column 'role' exists, if not this might be a migration scenario (but for now we assume fresh or updated db)
    # Since we use 'CREATE TABLE IF NOT EXISTS', if the table already existed without 'role', this might fail if we don't migrate.
    # For this task, I'll assume I can just run a migration command or the user can delete the db. 
    # But to be safe, let's try to add the columns if they miss.
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'agent'")
    except sqlite3.OperationalError:
        pass # Column likely exists
        
    try:
        c.execute("ALTER TABLE users ADD COLUMN google_id TEXT UNIQUE")
    except sqlite3.OperationalError:
        pass # Column likely exists

    c.execute("SELECT * FROM users WHERE role = 'admin'")
    if not c.fetchone():
        hashed_pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (name, mobile, username, password, role) VALUES (?, ?, ?, ?, ?)",
                  ("Administrator", "0000000000", "admin", hashed_pw, "admin"))
        conn.commit()
        print("Admin user created (username: admin, password: admin123)")
    conn.close()

def create_user(name, mobile, username, password, role='agent', google_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Hash password if provided
    hashed_pw = None
    if password:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        c.execute('INSERT INTO users (name, mobile, username, password, role, google_id) VALUES (?, ?, ?, ?, ?, ?)',
                  (name, mobile, username, hashed_pw, role, google_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_google_id(google_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE google_id = ?', (google_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = c.fetchall()
    conn.close()
    return users

def delete_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    c.execute('DELETE FROM collections WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def reset_password(username, mobile, new_password):
    conn = get_db_connection()
    c = conn.cursor()
    hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
    
    c.execute('SELECT * FROM users WHERE username = ? AND mobile = ?', (username, mobile))
    user = c.fetchone()
    
    if user:
        c.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_pw, user['id']))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def verify_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_pw))
    user = c.fetchone()
    conn.close()
    return user

def add_collection(user_id, amount, purpose, date):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO collections (user_id, amount, purpose, collection_date) VALUES (?, ?, ?, ?)',
              (user_id, amount, purpose, date))
    conn.commit()
    conn.close()

def get_user_collections(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM collections WHERE user_id = ? ORDER BY collection_date DESC, created_at DESC', (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_collections():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT c.*, u.name as user_name 
        FROM collections c 
        JOIN users u ON c.user_id = u.id 
        ORDER BY c.collection_date DESC, c.created_at DESC
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

def get_total_amount_all():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT SUM(amount) FROM collections')
    result = c.fetchone()[0]
    conn.close()
    return result if result else 0.0

def get_total_amount(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT SUM(amount) FROM collections WHERE user_id = ?', (user_id,))
    result = c.fetchone()[0]
    conn.close()
    return result if result else 0.0

if __name__ == "__main__":
    init_db()
    create_admin_if_not_exists()
    print("Database initialized.")
