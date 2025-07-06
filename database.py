import sqlite3
import os

DATABASE = 'data/transport.db'

def init_db():
    if not os.path.exists('data'):
        os.makedirs('data')
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            role TEXT NOT NULL,
            note TEXT
        )
    """)

    # Customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            account_id TEXT UNIQUE NOT NULL,
            company_name TEXT,
            contact_number TEXT,
            created_at TEXT,
            status TEXT,
            business_registration_number TEXT,
            representative_name TEXT,
            manager_name TEXT,
            manager_contact TEXT,
            manager_email TEXT,
            customer_memo TEXT,
            transaction_type TEXT,
            head_office_memo TEXT,
            invoice_issue_type TEXT,
            payment_cycle TEXT,
            fuel_misc_cost TEXT,
            liability_insurance_tax_invoice TEXT
        )
    """)

    # Sales Data table (for uploaded Excel data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER,
            month INTEGER,
            data_type TEXT, -- '매출' or '비용'
            delivery_date TEXT,
            customer_company TEXT,
            company_name TEXT,
            vehicle_number TEXT,
            transport_type TEXT,
            calculation_summary TEXT,
            delivery_fee REAL,
            fuel_misc_total REAL,
            other_costs REAL,
            sales_delivery_fee REAL,
            sales REAL, -- Calculated sales
            cost REAL, -- Calculated cost
            note TEXT
        )
    """)

    # Other Sales table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS other_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER,
            month INTEGER,
            category TEXT,
            count INTEGER,
            amount REAL,
            details TEXT
        )
    """)

    # Penalty Management table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS penalty_management (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, -- '완료' or '미완료'
            date TEXT,
            vehicle_number TEXT,
            vehicle_type TEXT,
            withdrawal_date TEXT,
            withdrawal_bank TEXT,
            amount REAL,
            deposit_date TEXT,
            deposit_bank TEXT,
            operation_details TEXT,
            driver_name TEXT,
            driver_phone TEXT,
            company TEXT,
            special_notes TEXT
        )
    """)

    # Drivers table (for Jeju Transport)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            id_number TEXT,
            phone_number TEXT,
            bank_name TEXT,
            account_number TEXT
        )
    """)
    
    # Insert initial driver data if not exists
    initial_drivers = [
        ('정재경', '600715-2056913', '010-3690-1444', '하나', '13491031461207'),
        ('김기륜', '690908-1002016', '010-5148-8082', '농협', '3120172200371')
    ]
    for driver in initial_drivers:
        try:
            cursor.execute("INSERT INTO drivers (name, id_number, phone_number, bank_name, account_number) VALUES (?, ?, ?, ?, ?)", driver)
        except sqlite3.IntegrityError:
            # Driver already exists, skip
            pass

    # Jeju Transport table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jeju_transport (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, -- '완료' or '미완료'
            date TEXT,
            order_company TEXT,
            withdrawal_date TEXT,
            withdrawal_bank TEXT,
            vehicle_number TEXT,
            driver_name TEXT,
            driver_id_number TEXT,
            driver_phone TEXT,
            driver_bank TEXT,
            driver_account_number TEXT,
            delivery_fee REAL,
            withholding_tax REAL,
            deposit_amount REAL,
            note TEXT
        )
    """)

    # Self-car and Wrecker table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS self_car_wrecker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, -- '완료' or '미완료'
            date TEXT,
            withdrawal_bank TEXT,
            withdrawal_date TEXT,
            customer_name TEXT,
            vehicle_number TEXT,
            driver TEXT,
            phone_number TEXT,
            billing_amount REAL,
            profit REAL,
            actual_payment REAL
        )
    """)

    # Shipping Fee Management table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shipping_fee_management (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, -- '완료' or '미완료'
            date TEXT,
            withdrawal_date TEXT,
            withdrawal_bank TEXT,
            withdrawal_amount REAL,
            customer_company TEXT,
            vehicle_number TEXT,
            billing_amount REAL,
            profit REAL,
            note TEXT
        )
    """)

    # Special Vehicle Management table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS special_vehicle_management (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, -- '미입고', '입고', '출고'
            vehicle_source TEXT,
            delivery_date TEXT,
            arrival_date TEXT,
            departure_date TEXT,
            origin TEXT,
            destination TEXT,
            vehicle_number TEXT,
            driver TEXT,
            driver_phone TEXT
        )
    """)

    conn.commit()
    
    # Add initial admin user
    try:
        from werkzeug.security import generate_password_hash
        # The requirement states '탁송' and 'wecar'
        hashed_password = generate_password_hash('wecar')
        cursor.execute("INSERT INTO users (username, password, name, role) VALUES (?, ?, ?, ?)",
                       ('탁송', hashed_password, '관리자', '관리자'))
        conn.commit()
        print("Initial admin user '탁송' created.")
    except sqlite3.IntegrityError:
        print("Admin user '탁송' already exists.")
    
    conn.close()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # This allows accessing columns by name
    return conn

def reset_monthly_data(year, month):
    conn = get_db()
    cursor = conn.cursor()
    tables_to_reset = ['sales_data', 'other_sales', 'penalty_management', 'jeju_transport', 'self_car_wrecker', 'shipping_fee_management', 'special_vehicle_management']
    for table in tables_to_reset:
        # Assuming 'year' and 'month' columns exist in relevant tables
        # For tables like penalty_management, jeju_transport, etc., we might need to parse date strings
        # For simplicity, this example assumes direct year/month columns or will need adjustment per table.
        # For now, we'll only apply to sales_data and other_sales which explicitly have year/month.
        if table in ['sales_data', 'other_sales']:
            cursor.execute(f"DELETE FROM {table} WHERE year = ? AND month = ?", (year, month))
        # Add more specific conditions for other tables if they don't have direct year/month columns
        # e.g., DELETE FROM penalty_management WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ?
    conn.commit()
    conn.close()

def reset_all_data():
    conn = get_db()
    cursor = conn.cursor()
    tables_to_reset = ['sales_data', 'other_sales', 'penalty_management', 'jeju_transport', 'self_car_wrecker', 'shipping_fee_management', 'special_vehicle_management', 'customers']
    for table in tables_to_reset:
        cursor.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()

def reset_customer_data():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customers")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized and tables created.")
