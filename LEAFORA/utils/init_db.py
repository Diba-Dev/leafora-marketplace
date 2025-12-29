from db import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# ==========================================
# DATABASE STRUCTURE
# ==========================================
# 1. USERS - User authentication and profiles
# 2. BOOKS - Book listings and inventory
# 3. ORDERS - Purchase and rental transactions
# 4. REVIEWS - Book ratings and comments
# 5. NOTIFICATIONS - User messaging system
# ==========================================

# ==========================================
# 1. USERS TABLE
# Purpose: Store user accounts, authentication, and profile information
# ==========================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Set super admin role for default admin
cursor.execute("""
UPDATE users
SET role = 'super_admin'
WHERE email = 'admin@email.com'
""")

# ==========================================
# 2. BOOKS TABLE
# Purpose: Store book listings with details, pricing, and ownership
# ==========================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER,
    title TEXT,
    author TEXT,
    category TEXT,
    description TEXT,
    condition TEXT,
    buy_price INTEGER,
    rent_price INTEGER,
    location TEXT,
    image TEXT,
    created_at TEXT,
    FOREIGN KEY (owner_id) REFERENCES users(id)
)
""")

# ==========================================
# 3. ORDERS TABLE
# Purpose: Track all book purchases and rental transactions
# ==========================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER,
    buyer_id INTEGER,
    order_type TEXT CHECK(order_type IN ('buy','rent')),
    rent_months INTEGER,
    total_price REAL,
    status TEXT DEFAULT 'pending',
    transaction_code TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (buyer_id) REFERENCES users(id)
)
""")

# ==========================================
# 4. REVIEWS TABLE
# Purpose: Store user ratings and comments for books
# ==========================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER,
    user_id INTEGER,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(book_id, user_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

# ==========================================
# 5. NOTIFICATIONS TABLE
# Purpose: Manage user-to-user messaging and order status updates
# ==========================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    book_id INTEGER,
    order_id INTEGER,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sender_id) REFERENCES users(id),
    FOREIGN KEY(receiver_id) REFERENCES users(id),
    FOREIGN KEY(book_id) REFERENCES books(id),
    FOREIGN KEY(order_id) REFERENCES orders(id)
)
""")

# Update notification status for completed transactions
cursor.execute("""
UPDATE notifications
SET status = 'done'
WHERE message LIKE '%has been accepted%'
OR message LIKE '%has been rejected%'
""")

conn.commit()
conn.close()

print("Database initialized successfully!")
