import sqlite3

DB_NAME = "star_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, stars_qty INTEGER, upi_id TEXT, status TEXT DEFAULT 'Pending', charge_id TEXT, req_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (user_id, username, first_name))
    conn.commit()
    conn.close()

def create_request(user_id, stars_qty, upi_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO requests (user_id, stars_qty, upi_id, status) VALUES (?, ?, ?, 'Pending')", (user_id, stars_qty, upi_id))
    req_id = c.lastrowid
    conn.commit()
    conn.close()
    return req_id

def mark_request_paid(req_id, charge_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT status FROM requests WHERE charge_id = ?", (charge_id,))
    if c.fetchone():
        conn.close()
        return False
    c.execute("UPDATE requests SET status = 'Paid', charge_id = ? WHERE id = ?", (charge_id, req_id))
    conn.commit()
    conn.close()
    return True

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM requests")
    total_reqs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM requests WHERE status = 'Pending'")
    pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM requests WHERE status = 'Paid'")
    paid = c.fetchone()[0]
    conn.close()
    return total_users, total_reqs, pending, paid
0

