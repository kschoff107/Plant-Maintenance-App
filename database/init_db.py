import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime

def get_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plant_maintenance.db')

def init_database():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'technician',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create spare_parts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spare_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            vendor_description TEXT,
            storage_location TEXT,
            storage_bin TEXT,
            rounding_value INTEGER,
            maximum_stock INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Add new columns if they don't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE spare_parts ADD COLUMN rounding_value INTEGER')
    except:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE spare_parts ADD COLUMN maximum_stock INTEGER')
    except:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE spare_parts ADD COLUMN quantity_available INTEGER DEFAULT 0')
    except:
        pass  # Column already exists

    # Create equipment table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_number TEXT NOT NULL,
            description TEXT NOT NULL,
            manufacturer TEXT,
            model_number TEXT,
            serial_number TEXT,
            location TEXT,
            installation_date TEXT,
            status TEXT DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create locations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            location_type TEXT DEFAULT 'Area',
            status TEXT DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create work_orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_order_number TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            equipment_id INTEGER,
            location_code TEXT,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Open',
            assigned_to INTEGER,
            created_by INTEGER,
            maintenance_schedule_id INTEGER,
            due_date TEXT,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            FOREIGN KEY (location_code) REFERENCES locations (location_code),
            FOREIGN KEY (assigned_to) REFERENCES users (id),
            FOREIGN KEY (created_by) REFERENCES users (id),
            FOREIGN KEY (maintenance_schedule_id) REFERENCES maintenance_schedules (id)
        )
    ''')

    # Add maintenance_schedule_id column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE work_orders ADD COLUMN maintenance_schedule_id INTEGER')
    except:
        pass  # Column already exists

    # Create work_order_parts table for tracking spare parts issued to work orders
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_order_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_order_id INTEGER NOT NULL,
            spare_part_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            transacted_by INTEGER,
            transacted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (work_order_id) REFERENCES work_orders (id),
            FOREIGN KEY (spare_part_id) REFERENCES spare_parts (id),
            FOREIGN KEY (transacted_by) REFERENCES users (id)
        )
    ''')

    # Create maintenance_schedules table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            equipment_id INTEGER NOT NULL,
            schedule_type TEXT NOT NULL,
            frequency TEXT,
            meter_interval INTEGER,
            meter_unit TEXT,
            last_performed_date TEXT,
            last_meter_reading INTEGER,
            next_due_date TEXT,
            next_due_meter INTEGER,
            priority TEXT DEFAULT 'Medium',
            estimated_duration INTEGER,
            instructions TEXT,
            status TEXT DEFAULT 'Active',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')

    # Add schedule_id column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE maintenance_schedules ADD COLUMN schedule_id TEXT')
    except:
        pass  # Column already exists

    # Create meter_readings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meter_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER NOT NULL,
            reading_value INTEGER NOT NULL,
            reading_unit TEXT,
            recorded_by INTEGER,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (equipment_id) REFERENCES equipment (id),
            FOREIGN KEY (recorded_by) REFERENCES users (id)
        )
    ''')

    # Check if admin user exists, if not create default admin
    cursor.execute('SELECT id FROM users WHERE username = ?', ('Admin',))
    if cursor.fetchone() is None:
        admin_password_hash = generate_password_hash('Admin1')
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, created_at)
            VALUES (?, ?, ?, ?)
        ''', ('Admin', admin_password_hash, 'admin', datetime.now()))
        print('Default admin user created (username: Admin, password: Admin1)')

    # Create SCHEDULE system user for auto-generated work orders
    cursor.execute('SELECT id FROM users WHERE username = ?', ('SCHEDULE',))
    if cursor.fetchone() is None:
        # Use a random hash - this user cannot login
        schedule_password_hash = generate_password_hash('SYSTEM_USER_NO_LOGIN')
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, created_at)
            VALUES (?, ?, ?, ?)
        ''', ('SCHEDULE', schedule_password_hash, 'system', datetime.now()))
        print('SCHEDULE system user created')

    conn.commit()
    conn.close()
    print(f'Database initialized at: {db_path}')

def get_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == '__main__':
    init_database()
