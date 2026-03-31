import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            weeks_pregnant INTEGER DEFAULT 0,
            blood_group TEXT,
            phone TEXT,
            village TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS health_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            symptoms TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            risk_score INTEGER DEFAULT 0,
            recommendations TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS nutrition_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            food_item TEXT NOT NULL,
            meal_type TEXT DEFAULT 'other',
            calories INTEGER DEFAULT 0,
            iron_mg REAL DEFAULT 0,
            calcium_mg REAL DEFAULT 0,
            protein_g REAL DEFAULT 0,
            folic_acid_mcg REAL DEFAULT 0,
            logged_date DATE DEFAULT (date('now')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            title TEXT NOT NULL,
            description TEXT,
            reminder_type TEXT DEFAULT 'medication',
            due_date TEXT,
            due_time TEXT,
            is_completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')

    # Seed a default user if none exists
    existing = cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    if existing == 0:
        cursor.execute('''
            INSERT INTO users (name, age, weeks_pregnant, blood_group, phone, village)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Lakshmi', 26, 24, 'B+', '9876543210', 'Kottayam'))

    conn.commit()
    conn.close()
