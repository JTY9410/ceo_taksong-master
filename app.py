from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
import pandas as pd
from datetime import datetime
from database import init_db, get_db, reset_monthly_data, reset_all_data, reset_customer_data

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database on startup
with app.app_context():
    init_db()

# --- Authentication Routes ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['username'] = user['username']
            session['role'] = user['role']
            flash('로그인 성공!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('잘못된 사용자 이름 또는 비밀번호입니다.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('role', None)
    flash('로그아웃 되었습니다.', 'info')
    return redirect(url_for('login'))

# --- Dashboard Route ---
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- Admin Routes (Placeholder) ---
@app.route('/admin')
def admin():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('admin.html')

@app.route('/admin/users')
def admin_users():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, name, role, note FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
def add_user():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    
    username = request.form['username']
    password = request.form['password']
    name = request.form['name']
    role = request.form['role']
    note = request.form.get('note', '')

    hashed_password = generate_password_hash(password)

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, name, role, note) VALUES (?, ?, ?, ?, ?)",
                       (username, hashed_password, name, role, note))
        conn.commit()
        flash('사용자가 성공적으로 추가되었습니다.', 'success')
    except sqlite3.IntegrityError:
        flash('이미 존재하는 사용자 이름입니다.', 'danger')
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/edit', methods=['POST'])
def edit_user():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    
    user_id = request.form['id']
    username = request.form['username']
    password = request.form.get('password') # Password might not be changed
    name = request.form['name']
    role = request.form['role']
    note = request.form.get('note', '')

    conn = get_db()
    cursor = conn.cursor()
    try:
        if password:
            hashed_password = generate_password_hash(password)
            cursor.execute("UPDATE users SET username = ?, password = ?, name = ?, role = ?, note = ? WHERE id = ?",
                           (username, hashed_password, name, role, note, user_id))
        else:
            cursor.execute("UPDATE users SET username = ?, name = ?, role = ?, note = ? WHERE id = ?",
                           (username, name, role, note, user_id))
        conn.commit()
        flash('사용자 정보가 성공적으로 수정되었습니다.', 'success')
    except sqlite3.IntegrityError:
        flash('이미 존재하는 사용자 이름입니다.', 'danger')
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete', methods=['POST'])
def delete_user():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    
    user_id = request.form['id']

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        flash('사용자가 성공적으로 삭제되었습니다.', 'success')
    except Exception as e:
        flash(f'사용자 삭제 중 오류 발생: {e}', 'danger')
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/customers')
def admin_customers():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers")
    customers = cursor.fetchall()
    conn.close()
    return render_template('admin_customers.html', customers=customers)

@app.route('/admin/reset_db', methods=['POST'])
def admin_reset_db():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    
    reset_type = request.form.get('reset_type')
    
    if reset_type == 'monthly':
        year = request.form.get('year', type=int)
        month = request.form.get('month', type=int)
        if year and month:
            from database import reset_monthly_data
            reset_monthly_data(year, month)
            flash(f'{year}년 {month}월 데이터가 초기화되었습니다.', 'success')
        else:
            flash('년도와 월을 정확히 입력해주세요.', 'danger')
    elif reset_type == 'all':
        from database import reset_all_data
        reset_all_data()
        flash('모든 데이터가 초기화되었습니다.', 'success')
    else:
        flash('잘못된 초기화 요청입니다.', 'danger')
        
    return redirect(url_for('admin'))

@app.route('/admin/customers/add', methods=['POST'])
def add_customer():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO customers (category, account_id, company_name, contact_number, created_at, status, business_registration_number, representative_name, manager_name, manager_contact, manager_email, customer_memo, transaction_type, head_office_memo, invoice_issue_type, payment_cycle, fuel_misc_cost, liability_insurance_tax_invoice) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (request.form.get('category'), request.form['account_id'], request.form.get('company_name'), request.form.get('contact_number'), request.form.get('created_at'), request.form.get('status'), request.form.get('business_registration_number'), request.form.get('representative_name'), request.form.get('manager_name'), request.form.get('manager_contact'), request.form.get('manager_email'), request.form.get('customer_memo'), request.form.get('transaction_type'), request.form.get('head_office_memo'), request.form.get('invoice_issue_type'), request.form.get('payment_cycle'), request.form.get('fuel_misc_cost'), request.form.get('liability_insurance_tax_invoice')))
        conn.commit()
        flash('고객사가 성공적으로 추가되었습니다.', 'success')
    except sqlite3.IntegrityError:
        flash('이미 존재하는 계정 아이디입니다.', 'danger')
    except Exception as e:
        flash(f'고객사 추가 중 오류 발생: {e}', 'danger')
    conn.close()
    return redirect(url_for('admin_customers'))

@app.route('/admin/customers/edit', methods=['POST'])
def edit_customer():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE customers SET category = ?, account_id = ?, company_name = ?, contact_number = ?, created_at = ?, status = ?, business_registration_number = ?, representative_name = ?, manager_name = ?, manager_contact = ?, manager_email = ?, customer_memo = ?, transaction_type = ?, head_office_memo = ?, invoice_issue_type = ?, payment_cycle = ?, fuel_misc_cost = ?, liability_insurance_tax_invoice = ? WHERE id = ?",
                       (request.form.get('category'), request.form['account_id'], request.form.get('company_name'), request.form.get('contact_number'), request.form.get('created_at'), request.form.get('status'), request.form.get('business_registration_number'), request.form.get('representative_name'), request.form.get('manager_name'), request.form.get('manager_contact'), request.form.get('manager_email'), request.form.get('customer_memo'), request.form.get('transaction_type'), request.form.get('head_office_memo'), request.form.get('invoice_issue_type'), request.form.get('payment_cycle'), request.form.get('fuel_misc_cost'), request.form.get('liability_insurance_tax_invoice'), request.form['id']))
        conn.commit()
        flash('고객사 정보가 성공적으로 수정되었습니다.', 'success')
    except sqlite3.IntegrityError:
        flash('이미 존재하는 계정 아이디입니다.', 'danger')
    except Exception as e:
        flash(f'고객사 수정 중 오류 발생: {e}', 'danger')
    conn.close()
    return redirect(url_for('admin_customers'))

@app.route('/admin/customers/delete', methods=['POST'])
def delete_customer():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM customers WHERE id = ?", (request.form['id'],))
        conn.commit()
        flash('고객사가 성공적으로 삭제되었습니다.', 'success')
    except Exception as e:
        flash(f'고객사 삭제 중 오류 발생: {e}', 'danger')
    conn.close()
    return redirect(url_for('admin_customers'))

@app.route('/admin/customers/reset', methods=['POST'])
def reset_customers():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    
    from database import reset_customer_data
    reset_customer_data()
    flash('고객사 데이터가 초기화되었습니다.', 'success')
    return redirect(url_for('admin_customers'))

@app.route('/admin/customers/upload_excel', methods=['POST'])
def upload_customers_excel():
    if not session.get('logged_in') or session.get('role') != '관리자':
        flash('관리자 권한이 필요합니다.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Placeholder for Excel upload logic
    flash('엑셀 업로드 기능은 아직 구현되지 않았습니다.', 'info')
    return redirect(url_for('admin_customers'))

# --- Sales Routes (Placeholder) ---
@app.route('/sales')
def sales():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('sales_main.html')

@app.route('/sales/upload', methods=['GET', 'POST'])
def sales_upload():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        year = request.form.get('year', type=int)
        month = request.form.get('month', type=int)
        excel_file = request.files.get('excel_file')

        if not excel_file or excel_file.filename == '':
            flash('파일을 선택해주세요.', 'danger')
            return redirect(url_for('sales_upload'))

        if excel_file:
            filepath = os.path.join(UPLOAD_FOLDER, excel_file.filename)
            excel_file.save(filepath)

            try:
                df = pd.read_excel(filepath)
                # Convert relevant columns to string to avoid mixed types issues
                df['탁송일'] = df['탁송일'].astype(str)
                df['고객사'] = df['고객사'].astype(str)
                df['운송유형'] = df['운송유형'].astype(str)
                df['계산정리열'] = df['계산정리열'].astype(str)

                # Fill NaN with 0 for numeric columns that are used in calculations
                numeric_cols = ['탁송비', '주유/부대비용 총액', '기타비용(취소/대기등)', '매출 탁송비']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    else:
                        df[col] = 0 # Add column if it doesn't exist and fill with 0

                # Fetch customer categories for sales/cost distinction
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT account_id, category FROM customers")
                customer_categories = {row['account_id']: row['category'] for row in cursor.fetchall()}
                conn.close()

                sales_data_list = []
                cost_data_list = []

                for index, row in df.iterrows():
                    customer_account_id = str(row['고객사'])
                    data_category = customer_categories.get(customer_account_id, '미지정') # Default to '미지정' if not found

                    # Initialize sales and cost for current row
                    sales_value = 0
                    cost_value = 0

                    # Extract values, defaulting to 0 if not present or NaN
                    delivery_fee = row.get('탁송비', 0)
                    fuel_misc_total = row.get('주유/부대비용 총액', 0)
                    other_costs = row.get('기타비용(취소/대기등)', 0)
                    sales_delivery_fee = row.get('매출 탁송비', 0)
                    transport_type = row.get('운송유형', '').strip()
                    calculation_summary = row.get('계산정리열', '').strip()

                    # Sales Calculation Logic
                    if data_category == '매출':
                        if transport_type == 'TP':
                            if calculation_summary == '선지급':
                                sales_value = sales_delivery_fee / 1.1
                            else:
                                sales_value = sales_delivery_fee
                        elif transport_type == '로드' or transport_type == '견인' or transport_type == '책임보험전용' or transport_type == '해상':
                            if calculation_summary == '선지급':
                                # Assuming a '책임보험비' column might exist or needs to be derived
                                # For now, using 0 for '책임보험비' if not explicitly in Excel
                                liability_insurance_fee = row.get('책임보험비', 0) # Placeholder, adjust if column name is different
                                sales_value = (sales_delivery_fee / 1.1) + (liability_insurance_fee / 1.1)
                            elif calculation_summary in ['세금계산서 발행', '세금계산서 발행(책임)']:
                                sales_value = sales_delivery_fee + other_costs + row.get('책임보험비', 0) # Placeholder
                            elif calculation_summary in ['세금계산서 발행(주유기타)', '세금계산서 발행(주유기타,책임)']:
                                sales_value = sales_delivery_fee + fuel_misc_total + other_costs + row.get('책임보험비', 0) # Placeholder
                            elif calculation_summary in ['현금(현지지불)', '현금(현지지불)(책임)']:
                                sales_value = (sales_delivery_fee * 0.2 / 1.1) + (row.get('책임보험비', 0) / 1.1) # Placeholder
                        # Handle '현금(현지지불)' for sales: not reflected in sales calculation
                        if calculation_summary in ['현금(현지지불)', '현금(현지지불)(책임)']:
                            sales_value = 0 # As per requirement, not reflected in sales calculation

                    # Cost Calculation Logic
                    cost_value = (sales_delivery_fee * 0.8) + fuel_misc_total + other_costs

                    processed_row = {
                        'delivery_date': row.get('탁송일', ''),
                        'customer_company': row.get('고객사', ''),
                        'company_name': row.get('상호', ''), # Assuming '상호' column exists or can be derived
                        'vehicle_number': row.get('차량번호', ''),
                        'transport_type': transport_type,
                        'calculation_summary': calculation_summary,
                        'delivery_fee': delivery_fee,
                        'fuel_misc_total': fuel_misc_total,
                        'other_costs': other_costs,
                        'sales_delivery_fee': sales_delivery_fee,
                        'note': row.get('비고', '')
                    }

                    if data_category == '매출':
                        processed_row['sales'] = sales_value
                        sales_data_list.append(processed_row)
                    elif data_category == '비용':
                        processed_row['cost'] = cost_value
                        cost_data_list.append(processed_row)

                session['uploaded_sales_data'] = sales_data_list
                session['uploaded_cost_data'] = cost_data_list
                session['uploaded_year'] = year
                session['uploaded_month'] = month

                flash('엑셀 파일이 성공적으로 업로드 및 처리되었습니다. 데이터를 확인 후 저장해주세요.', 'success')
                return render_template('sales_upload.html',
                                       sales_data=sales_data_list,
                                       cost_data=cost_data_list,
                                       year=year,
                                       month=month)

            except Exception as e:
                flash(f'엑셀 파일 처리 중 오류 발생: {e}', 'danger')
                return redirect(url_for('sales_upload'))

    # For GET request or initial load
    return render_template('sales_upload.html',
                           sales_data=session.pop('uploaded_sales_data', []),
                           cost_data=session.pop('uploaded_cost_data', []),
                           year=session.pop('uploaded_year', datetime.now().year),
                           month=session.pop('uploaded_month', datetime.now().month))

@app.route('/sales/save_uploaded_data', methods=['POST'])
def save_uploaded_data():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    sales_data_list = session.pop('uploaded_sales_data', [])
    cost_data_list = session.pop('uploaded_cost_data', [])
    year = session.pop('uploaded_year', None)
    month = session.pop('uploaded_month', None)

    if not sales_data_list and not cost_data_list:
        flash('저장할 데이터가 없습니다.', 'danger')
        return redirect(url_for('sales_upload'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Save sales data
        for row_data in sales_data_list:
            cursor.execute("INSERT INTO sales_data (year, month, data_type, delivery_date, customer_company, company_name, vehicle_number, transport_type, calculation_summary, delivery_fee, fuel_misc_total, other_costs, sales_delivery_fee, sales, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (year, month, '매출', row_data['delivery_date'], row_data['customer_company'], row_data['company_name'], row_data['vehicle_number'], row_data['transport_type'], row_data['calculation_summary'], row_data['delivery_fee'], row_data['fuel_misc_total'], row_data['other_costs'], row_data['sales_delivery_fee'], row_data['sales'], row_data['note']))
        
        # Save cost data
        for row_data in cost_data_list:
            cursor.execute("INSERT INTO sales_data (year, month, data_type, delivery_date, customer_company, company_name, vehicle_number, transport_type, calculation_summary, delivery_fee, fuel_misc_total, other_costs, sales_delivery_fee, cost, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (year, month, '비용', row_data['delivery_date'], row_data['customer_company'], row_data['company_name'], row_data['vehicle_number'], row_data['transport_type'], row_data['calculation_summary'], row_data['delivery_fee'], row_data['fuel_misc_total'], row_data['other_costs'], row_data['sales_delivery_fee'], row_data['cost'], row_data['note']))
        
        conn.commit()
        flash('데이터가 성공적으로 저장되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'데이터 저장 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('sales_upload'))

@app.route('/sales/other_sales/add', methods=['POST'])
def add_other_sales():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    year = request.form.get('year', type=int)
    month = request.form.get('month', type=int)
    category = request.form.get('category')
    count = request.form.get('count', type=int)
    amount = request.form.get('amount', type=float)
    details = request.form.get('details', '')

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO other_sales (year, month, category, count, amount, details) VALUES (?, ?, ?, ?, ?, ?)",
                       (year, month, category, count, amount, details))
        conn.commit()
        flash('기타 매출이 성공적으로 추가되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'기타 매출 추가 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('sales_monthly_analysis'))

# --- Sales Monthly Analysis ---
@app.route('/sales/monthly_analysis')
def sales_monthly_analysis():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    year = request.args.get('year', type=int, default=datetime.now().year)
    month = request.args.get('month', type=int, default=datetime.now().month)

    conn = get_db()
    cursor = conn.cursor()

    # Fetch sales data
    cursor.execute("SELECT * FROM sales_data WHERE year = ? AND month = ? AND data_type = '매출'", (year, month))
    sales_data_rows = cursor.fetchall()

    # Fetch cost data
    cursor.execute("SELECT * FROM sales_data WHERE year = ? AND month = ? AND data_type = '비용'", (year, month))
    cost_data_rows = cursor.fetchall()

    # Fetch other sales data
    cursor.execute("SELECT * FROM other_sales WHERE year = ? AND month = ?", (year, month))
    other_sales_rows = cursor.fetchall()

    conn.close()

    # Perform analysis
    sales_analysis = []
    cost_analysis = []
    comprehensive_analysis = []

    # 1. 매출 분석
    sales_by_type = {}
    for row in sales_data_rows:
        transport_type = row['transport_type']
        sales_amount = row['sales']
        if transport_type not in sales_by_type:
            sales_by_type[transport_type] = {'count': 0, 'amount': 0}
        sales_by_type[transport_type]['count'] += 1
        sales_by_type[transport_type]['amount'] += sales_amount

    # Add '로드', 'TP'
    for t_type in ['로드', 'TP']:
        if t_type in sales_by_type:
            sales_analysis.append({
                'category': t_type,
                'subcategory': t_type,
                'count': sales_by_type[t_type]['count'],
                'amount': sales_by_type[t_type]['amount'],
                'note': ''
            })
            del sales_by_type[t_type] # Remove processed types

    # Add '기타' (견인, 책임보험, 해상, 기타매출)
    other_category_sales = {'count': 0, 'amount': 0}
    for t_type in ['견인', '책임보험', '해상']:
        if t_type in sales_by_type:
            other_category_sales['count'] += sales_by_type[t_type]['count']
            other_category_sales['amount'] += sales_by_type[t_type]['amount']
            sales_analysis.append({
                'category': '기타',
                'subcategory': t_type,
                'count': sales_by_type[t_type]['count'],
                'amount': sales_by_type[t_type]['amount'],
                'note': ''
            })
            del sales_by_type[t_type]

    # Add other_sales to '기타매출'
    other_sales_total_amount = sum(row['amount'] for row in other_sales_rows)
    other_sales_total_count = sum(row['count'] for row in other_sales_rows)
    if other_sales_total_amount > 0 or other_sales_total_count > 0:
        sales_analysis.append({
            'category': '기타',
            'subcategory': '기타매출',
            'count': other_sales_total_count,
            'amount': other_sales_total_amount,
            'note': ''
        })
        other_category_sales['count'] += other_sales_total_count
        other_category_sales['amount'] += other_sales_total_amount

    # Add any remaining transport types to '기타'
    for t_type, data in sales_by_type.items():
        sales_analysis.append({
            'category': '기타',
            'subcategory': t_type,
            'count': data['count'],
            'amount': data['amount'],
            'note': ''
        })
        other_category_sales['count'] += data['count']
        other_category_sales['amount'] += data['amount']

    # Add '기타' total row if it has data
    if other_category_sales['count'] > 0 or other_category_sales['amount'] > 0:
        sales_analysis.append({
            'category': '기타',
            'subcategory': '계',
            'count': other_category_sales['count'],
            'amount': other_category_sales['amount'],
            'note': ''
        })

    # Add '합계' for sales analysis
    total_sales_count = sum(item['count'] for item in sales_analysis if item['subcategory'] != '계')
    total_sales_amount = sum(item['amount'] for item in sales_analysis if item['subcategory'] != '계')
    sales_analysis.append({
        'category': '합계',
        'subcategory': '',
        'count': total_sales_count,
        'amount': total_sales_amount,
        'note': ''
    })


    # 2. 비용 분석 (Similar structure to sales analysis, but for costs)
    cost_by_type = {}
    for row in cost_data_rows:
        transport_type = row['transport_type']
        cost_amount = row['cost']
        if transport_type not in cost_by_type:
            cost_by_type[transport_type] = {'count': 0, 'amount': 0}
        cost_by_type[transport_type]['count'] += 1
        cost_by_type[transport_type]['amount'] += cost_amount

    # Add '로드', 'TP'
    for t_type in ['로드', 'TP']:
        if t_type in cost_by_type:
            cost_analysis.append({
                'category': t_type,
                'subcategory': t_type,
                'count': cost_by_type[t_type]['count'],
                'amount': cost_by_type[t_type]['amount'],
                'note': ''
            })
            del cost_by_type[t_type]

    # Add '기타' (견인, 책임보험, 해상)
    other_category_costs = {'count': 0, 'amount': 0}
    for t_type in ['견인', '책임보험', '해상']:
        if t_type in cost_by_type:
            other_category_costs['count'] += cost_by_type[t_type]['count']
            other_category_costs['amount'] += cost_by_type[t_type]['amount']
            cost_analysis.append({
                'category': '기타',
                'subcategory': t_type,
                'count': cost_by_type[t_type]['count'],
                'amount': cost_by_type[t_type]['amount'],
                'note': ''
            })
            del cost_by_type[t_type]

    # Add any remaining transport types to '기타'
    for t_type, data in cost_by_type.items():
        cost_analysis.append({
            'category': '기타',
            'subcategory': t_type,
            'count': data['count'],
            'amount': data['amount'],
            'note': ''
        })
        other_category_costs['count'] += data['count']
        other_category_costs['amount'] += data['amount']

    # Add '기타' total row if it has data
    if other_category_costs['count'] > 0 or other_category_costs['amount'] > 0:
        cost_analysis.append({
            'category': '기타',
            'subcategory': '계',
            'count': other_category_costs['count'],
            'amount': other_category_costs['amount'],
            'note': ''
        })

    # Add '합계' for cost analysis
    total_cost_count = sum(item['count'] for item in cost_analysis if item['subcategory'] != '계')
    total_cost_amount = sum(item['amount'] for item in cost_analysis if item['subcategory'] != '계')
    cost_analysis.append({
        'category': '합계',
        'subcategory': '',
        'count': total_cost_count,
        'amount': total_cost_amount,
        'note': ''
    })

    # 3. 종합 분석 (Combine sales and cost data)
    # Create a dictionary to hold combined data for each subcategory
    combined_data = {}

    for item in sales_analysis:
        if item['subcategory'] and item['subcategory'] != '계' and item['category'] != '합계':
            key = item['subcategory']
            if key not in combined_data:
                combined_data[key] = {'count': 0, 'amount': 0}
            combined_data[key]['count'] += item['count']
            combined_data[key]['amount'] += item['amount']

    for item in cost_analysis:
        if item['subcategory'] and item['subcategory'] != '계' and item['category'] != '합계':
            key = item['subcategory']
            if key not in combined_data:
                combined_data[key] = {'count': 0, 'amount': 0}
            combined_data[key]['count'] += item['count']
            combined_data[key]['amount'] += item['amount']

    # Populate comprehensive_analysis list
    for t_type in ['로드', 'TP']:
        if t_type in combined_data:
            comprehensive_analysis.append({
                'type_category': t_type,
                'subcategory': t_type,
                'count': combined_data[t_type]['count'],
                'amount': combined_data[t_type]['amount'],
                'note': ''
            })
            del combined_data[t_type]

    other_comprehensive_total = {'count': 0, 'amount': 0}
    for t_type in ['견인', '책임보험', '해상']:
        if t_type in combined_data:
            comprehensive_analysis.append({
                'type_category': '기타',
                'subcategory': t_type,
                'count': combined_data[t_type]['count'],
                'amount': combined_data[t_type]['amount'],
                'note': ''
            })
            other_comprehensive_total['count'] += combined_data[t_type]['count']
            other_comprehensive_total['amount'] += combined_data[t_type]['amount']
            del combined_data[t_type]

    # Add remaining combined data to '기타'
    for key, data in combined_data.items():
        comprehensive_analysis.append({
            'type_category': '기타',
            'subcategory': key,
            'count': data['count'],
            'amount': data['amount'],
            'note': ''
        })
        other_comprehensive_total['count'] += data['count']
        other_comprehensive_total['amount'] += data['amount']

    if other_comprehensive_total['count'] > 0 or other_comprehensive_total['amount'] > 0:
        comprehensive_analysis.append({
            'type_category': '기타',
            'subcategory': '계',
            'count': other_comprehensive_total['count'],
            'amount': other_comprehensive_total['amount'],
            'note': ''
        })

    total_comprehensive_count = sum(item['count'] for item in comprehensive_analysis if item['subcategory'] != '계')
    total_comprehensive_amount = sum(item['amount'] for item in comprehensive_analysis if item['subcategory'] != '계')
    comprehensive_analysis.append({
        'type_category': '합계',
        'subcategory': '',
        'count': total_comprehensive_count,
        'amount': total_comprehensive_amount,
        'note': ''
    })


    return render_template('sales_monthly_analysis.html',
                           analysis_year=year,
                           analysis_month=month,
                           sales_analysis=sales_analysis,
                           cost_analysis=cost_analysis,
                           comprehensive_analysis=comprehensive_analysis,
                           now=datetime.now())

# --- Sales Customer Analysis ---
@app.route('/sales/customer_analysis')
def sales_customer_analysis():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    # Fetch all customers for the dropdown
    cursor.execute("SELECT account_id, company_name FROM customers")
    customers = cursor.fetchall()

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    customer_account_id = request.args.get('customer_id')

    customer_analysis_results = []
    analysis_year = datetime.now().year
    analysis_month = datetime.now().month

    if start_date_str and end_date_str:
        # Convert date strings to datetime objects for comparison
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        query = "SELECT customer_company, transport_type, sales, cost, calculation_summary FROM sales_data WHERE 1=1"
        params = []

        # Filter by date range
        # Assuming delivery_date is stored as YYYY-MM-DD string
        query += " AND delivery_date BETWEEN ? AND ?"
        params.append(start_date_str)
        params.append(end_date_str)

        if customer_account_id:
            query += " AND customer_company = ?"
            params.append(customer_account_id)

        cursor.execute(query, params)
        sales_data_rows = cursor.fetchall()

        # Group by customer and transport type
        grouped_data = {}
        for row in sales_data_rows:
            company = row['customer_company']
            transport_type = row['transport_type']
            sales_amount = row['sales'] if row['sales'] is not None else 0
            cost_amount = row['cost'] if row['cost'] is not None else 0
            calculation_summary = row['calculation_summary']

            # Exclude '현금(현지지불)' from count and amount calculation for customer analysis
            if calculation_summary in ['현금(현지지불)', '현금(현지지불)(책임)']:
                continue

            if company not in grouped_data:
                grouped_data[company] = {}
            if transport_type not in grouped_data[company]:
                grouped_data[company][transport_type] = {'count': 0, 'amount': 0}
            
            grouped_data[company][transport_type]['count'] += 1
            grouped_data[company][transport_type]['amount'] += (sales_amount - cost_amount) # Assuming amount is net sales

        for company, types in grouped_data.items():
            for t_type, data in types.items():
                customer_analysis_results.append({
                    'company_name': company,
                    'transport_type': t_type,
                    'count': data['count'],
                    'amount': data['amount'],
                    'note': '' # Placeholder for note
                })

    conn.close()

    return render_template('sales_customer_analysis.html',
                           customers=customers,
                           customer_analysis=customer_analysis_results,
                           analysis_year=analysis_year,
                           analysis_month=analysis_month,
                           start_date=start_date_str,
                           end_date=end_date_str)

@app.route('/sales/customer_analysis/detail')
def sales_customer_analysis_detail():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    customer_account_id = request.args.get('customer_id')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not customer_account_id or not start_date_str or not end_date_str:
        return jsonify({'error': 'Missing parameters'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Get company name for display
    cursor.execute("SELECT company_name FROM customers WHERE account_id = ?", (customer_account_id,))
    customer_info = cursor.fetchone()
    company_name = customer_info['company_name'] if customer_info else customer_account_id

    query = "SELECT * FROM sales_data WHERE customer_company = ? AND delivery_date BETWEEN ? AND ?"
    params = [customer_account_id, start_date_str, end_date_str]
    cursor.execute(query, params)
    detail_rows = cursor.fetchall()
    conn.close()

    summary_data = {}
    total_amount_sum = 0

    processed_details = []
    for row in detail_rows:
        transport_type = row['transport_type']
        sales_delivery_fee = row['sales_delivery_fee'] if row['sales_delivery_fee'] is not None else 0
        calculation_summary = row['calculation_summary']

        # Exclude '현금(현지지불)' from summary and total amount calculation
        if calculation_summary in ['현금(현지지불)', '현금(현지지불)(책임)']:
            continue

        # Calculate amount for summary based on calculation_summary
        amount_for_summary = sales_delivery_fee
        if calculation_summary == '선지급':
            amount_for_summary = sales_delivery_fee * 1.1 # Add 10% for 선지급

        if transport_type not in summary_data:
            summary_data[transport_type] = {'count': 0, 'amount': 0}
        summary_data[transport_type]['count'] += 1
        summary_data[transport_type]['amount'] += amount_for_summary
        total_amount_sum += amount_for_summary

        processed_details.append({
            'delivery_date': row['delivery_date'],
            'customer_company': row['customer_company'],
            'vehicle_number': row['vehicle_number'],
            'transport_type': row['transport_type'],
            'delivery_fee': row['delivery_fee'],
            'fuel_misc_total': row['fuel_misc_total'],
            'other_costs': row['other_costs'],
            'sales_delivery_fee': row['sales_delivery_fee'],
            'calculation_summary': row['calculation_summary'],
            'sales': row['sales'],
            'cost': row['cost'],
            'note': row['note']
        })

    # Prepare summary for display
    summary_list = []
    for t_type in ['로드', 'TP', '견인', '책임보험', '해상']:
        if t_type in summary_data:
            summary_list.append({
                'transport_type': t_type,
                'count': summary_data[t_type]['count'],
                'amount': summary_data[t_type]['amount'],
                'note': ''
            })

    # Calculate VAT and total amount
    vat = total_amount_sum * 0.1
    final_total_amount = total_amount_sum + vat

    return jsonify({
        'company_name': company_name,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'summary': summary_list,
        'vat': vat,
        'total_amount': final_total_amount,
        'details': processed_details
    })



# --- Sales Weekly Analysis ---
@app.route('/sales/weekly_analysis')
def sales_weekly_analysis():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    year = request.args.get('year', type=int, default=datetime.now().year)
    month = request.args.get('month', type=int, default=datetime.now().month)
    week = request.args.get('week', type=int, default=1)

    conn = get_db()
    cursor = conn.cursor()

    # Fetch sales data for the given year and month
    # For weekly analysis, we'll need to filter by week number.
    # SQLite's strftime does not directly support week numbers in the same way Python's isocalendar does.
    # A more robust solution would involve storing week numbers during data upload or calculating them on the fly.
    # For simplicity, this implementation will fetch all data for the month and then filter by week in Python.
    # This might be inefficient for very large datasets.
    cursor.execute("SELECT * FROM sales_data WHERE year = ? AND month = ? AND data_type = '매출'", (year, month))
    sales_data_rows = cursor.fetchall()
    conn.close()

    weekly_analysis_results = []
    
    # Group data by company and transport type for the specified week
    grouped_data = {}
    for row in sales_data_rows:
        delivery_date_str = row['delivery_date']
        try:
            delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d')
            # Get ISO week number (Monday as the first day of the week)
            iso_year, iso_week, iso_weekday = delivery_date.isocalendar()
            
            # Adjust week number if the year starts on a Thursday or Friday (ISO 8601)
            # This is a simplified approach; a full ISO week calculation is more complex.
            # For this project, we'll assume a straightforward week number within the year.
            # If the first week of the year has less than 4 days, it belongs to the previous year's last week.
            # Python's isocalendar gives the ISO week number.
            
            # Let's assume week 1 starts on the first Monday of the year or the first day if it's Monday.
            # For simplicity, we'll just use iso_week directly for now.
            current_week = iso_week

            if current_week == week:
                company_name = row['company_name']
                transport_type = row['transport_type']
                sales_amount = row['sales'] if row['sales'] is not None else 0

                key = (company_name, transport_type)
                if key not in grouped_data:
                    grouped_data[key] = {'count': 0, 'sales': 0}
                grouped_data[key]['count'] += 1
                grouped_data[key]['sales'] += sales_amount
        except ValueError:
            # Handle cases where delivery_date is not in YYYY-MM-DD format
            continue

    for (company_name, transport_type), data in grouped_data.items():
        weekly_analysis_results.append({
            'company_name': company_name,
            'transport_type': transport_type,
            'count': data['count'],
            'sales': data['sales'],
            'note': '' # Placeholder for note
        })

    return render_template('sales_weekly_analysis.html',
                           analysis_year=year,
                           analysis_month=month,
                           analysis_week=week,
                           weekly_analysis=weekly_analysis_results,
                           now=datetime.now())

# --- Transport Penalty Management ---
@app.route('/transport/penalty')
def transport_penalty():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    year = request.args.get('year', type=int, default=datetime.now().year)
    month = request.args.get('month', type=int, default=datetime.now().month)
    status = request.args.get('status', '')

    query = "SELECT * FROM penalty_management WHERE 1=1"
    params = []

    if year and month:
        # Assuming 'date' column stores YYYY-MM-DD
        query += " AND strftime('%Y', date) = ? AND strftime('%m', date) = ?"
        params.append(str(year))
        params.append(f'{month:02d}')

    if status:
        query += " AND category = ?"
        params.append(status)

    cursor.execute(query, params)
    penalties = cursor.fetchall()
    conn.close()

    return render_template('transport_penalty.html',
                           penalties=penalties,
                           search_year=year,
                           search_month=month,
                           search_status=status,
                           now=datetime.now())

@app.route('/transport/penalty/add', methods=['POST'])
def add_penalty():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Determine category based on deposit_date
        deposit_date = request.form.get('deposit_date')
        category = '완료' if deposit_date else '미완료'

        cursor.execute("INSERT INTO penalty_management (category, date, vehicle_number, vehicle_type, withdrawal_date, withdrawal_bank, amount, deposit_date, deposit_bank, operation_details, driver_name, driver_phone, company, special_notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (category,
                        request.form.get('date'),
                        request.form.get('vehicle_number'),
                        request.form.get('vehicle_type'),
                        request.form.get('withdrawal_date'),
                        request.form.get('withdrawal_bank'),
                        request.form.get('amount', type=float),
                        deposit_date,
                        request.form.get('deposit_bank'),
                        request.form.get('operation_details'),
                        request.form.get('driver_name'),
                        request.form.get('driver_phone'),
                        request.form.get('company'),
                        request.form.get('special_notes')))
        conn.commit()
        flash('과태료 기록이 성공적으로 추가되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'과태료 기록 추가 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_penalty'))

@app.route('/transport/penalty/edit', methods=['POST'])
def edit_penalty():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        penalty_id = request.form.get('id', type=int)
        deposit_date = request.form.get('deposit_date')
        category = '완료' if deposit_date else '미완료'

        cursor.execute("UPDATE penalty_management SET category = ?, date = ?, vehicle_number = ?, vehicle_type = ?, withdrawal_date = ?, withdrawal_bank = ?, amount = ?, deposit_date = ?, deposit_bank = ?, operation_details = ?, driver_name = ?, driver_phone = ?, company = ?, special_notes = ? WHERE id = ?",
                       (category,
                        request.form.get('date'),
                        request.form.get('vehicle_number'),
                        request.form.get('vehicle_type'),
                        request.form.get('withdrawal_date'),
                        request.form.get('withdrawal_bank'),
                        request.form.get('amount', type=float),
                        deposit_date,
                        request.form.get('deposit_bank'),
                        request.form.get('operation_details'),
                        request.form.get('driver_name'),
                        request.form.get('driver_phone'),
                        request.form.get('company'),
                        request.form.get('special_notes'),
                        penalty_id))
        conn.commit()
        flash('과태료 기록이 성공적으로 수정되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'과태료 기록 수정 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_penalty'))

@app.route('/transport/penalty/delete', methods=['POST'])
def delete_penalty():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        penalty_id = request.form.get('id', type=int)
        cursor.execute("DELETE FROM penalty_management WHERE id = ?", (penalty_id,))
        conn.commit()
        flash('과태료 기록이 성공적으로 삭제되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'과태료 기록 삭제 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_penalty'))

@app.route('/transport/penalty/upload_excel', methods=['POST'])
def upload_penalty_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    flash('과태료 엑셀 업로드 기능은 아직 구현되지 않았습니다.', 'info')
    return redirect(url_for('transport_penalty'))

@app.route('/transport/penalty/save_data', methods=['POST'])
def save_penalty_data():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    flash('과태료 데이터 저장 기능은 아직 구현되지 않았습니다.', 'info')
    return redirect(url_for('transport_penalty'))

# --- Transport Jeju Management ---
@app.route('/transport/jeju')
def transport_jeju():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    year = request.args.get('year', type=int, default=datetime.now().year)
    month = request.args.get('month', type=int, default=datetime.now().month)
    driver_name = request.args.get('driver_name', '')

    query = "SELECT * FROM jeju_transport WHERE 1=1"
    params = []

    if year and month:
        query += " AND strftime('%Y', date) = ? AND strftime('%m', date) = ?"
        params.append(str(year))
        params.append(f'{month:02d}')

    if driver_name:
        query += " AND driver_name = ?"
        params.append(driver_name)

    cursor.execute(query, params)
    jeju_transports = cursor.fetchall()

    # Fetch drivers for the dropdown
    cursor.execute("SELECT name FROM drivers")
    drivers = cursor.fetchall()

    conn.close()

    return render_template('transport_jeju.html',
                           jeju_transports=jeju_transports,
                           drivers=drivers,
                           search_year=year,
                           search_month=month,
                           search_driver_name=driver_name,
                           now=datetime.now())

@app.route('/transport/jeju/add', methods=['POST'])
def add_jeju_transport():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Determine category based on withdrawal_date
        withdrawal_date = request.form.get('withdrawal_date')
        category = '완료' if withdrawal_date else '미완료'

        # Calculate withholding_tax and deposit_amount
        delivery_fee = request.form.get('delivery_fee', type=float, default=0)
        withholding_tax = delivery_fee * 0.033
        deposit_amount = delivery_fee - withholding_tax

        cursor.execute("INSERT INTO jeju_transport (category, date, order_company, withdrawal_date, withdrawal_bank, vehicle_number, driver_name, driver_id_number, driver_phone, driver_bank, driver_account_number, delivery_fee, withholding_tax, deposit_amount, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (category,
                        request.form.get('date'),
                        request.form.get('order_company'),
                        withdrawal_date,
                        request.form.get('withdrawal_bank'),
                        request.form.get('vehicle_number'),
                        request.form.get('driver_name'),
                        request.form.get('driver_id_number'),
                        request.form.get('driver_phone'),
                        request.form.get('driver_bank'),
                        request.form.get('driver_account_number'),
                        delivery_fee,
                        withholding_tax,
                        deposit_amount,
                        request.form.get('note')))
        conn.commit()
        flash('제주탁송 기록이 성공적으로 추가되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'제주탁송 기록 추가 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_jeju'))

@app.route('/transport/jeju/edit', methods=['POST'])
def edit_jeju_transport():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        jeju_id = request.form.get('id', type=int)
        withdrawal_date = request.form.get('withdrawal_date')
        category = '완료' if withdrawal_date else '미완료'

        delivery_fee = request.form.get('delivery_fee', type=float, default=0)
        withholding_tax = delivery_fee * 0.033
        deposit_amount = delivery_fee - withholding_tax

        cursor.execute("UPDATE jeju_transport SET category = ?, date = ?, order_company = ?, withdrawal_date = ?, withdrawal_bank = ?, vehicle_number = ?, driver_name = ?, driver_id_number = ?, driver_phone = ?, driver_bank = ?, driver_account_number = ?, delivery_fee = ?, withholding_tax = ?, deposit_amount = ?, note = ? WHERE id = ?",
                       (category,
                        request.form.get('date'),
                        request.form.get('order_company'),
                        withdrawal_date,
                        request.form.get('withdrawal_bank'),
                        request.form.get('vehicle_number'),
                        request.form.get('driver_name'),
                        request.form.get('driver_id_number'),
                        request.form.get('driver_phone'),
                        request.form.get('driver_bank'),
                        request.form.get('driver_account_number'),
                        delivery_fee,
                        withholding_tax,
                        deposit_amount,
                        request.form.get('note'),
                        jeju_id))
        conn.commit()
        flash('제주탁송 기록이 성공적으로 수정되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'제주탁송 기록 수정 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_jeju'))

@app.route('/transport/jeju/delete', methods=['POST'])
def delete_jeju_transport():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        jeju_id = request.form.get('id', type=int)
        cursor.execute("DELETE FROM jeju_transport WHERE id = ?", (jeju_id,))
        conn.commit()
        flash('제주탁송 기록이 성공적으로 삭제되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'제주탁송 기록 삭제 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_jeju'))

@app.route('/transport/jeju/drivers/add', methods=['POST'])
def add_driver():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO drivers (name, id_number, phone_number, bank_name, account_number) VALUES (?, ?, ?, ?, ?)",
                       (request.form.get('name'),
                        request.form.get('id_number'),
                        request.form.get('phone_number'),
                        request.form.get('bank_name'),
                        request.form.get('account_number')))
        conn.commit()
        flash('기사 데이터가 성공적으로 추가되었습니다.', 'success')
    except sqlite3.IntegrityError:
        flash('이미 존재하는 기사 이름입니다.', 'danger')
    except Exception as e:
        flash(f'기사 데이터 추가 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_jeju'))

@app.route('/transport/jeju/upload_excel', methods=['POST'])
def upload_jeju_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    flash('제주탁송 엑셀 업로드 기능은 아직 구현되지 않았습니다.', 'info')
    return redirect(url_for('transport_jeju'))

@app.route('/transport/jeju/save_data', methods=['POST'])
def save_jeju_data():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    flash('제주탁송 데이터 저장 기능은 아직 구현되지 않았습니다.', 'info')
    return redirect(url_for('transport_jeju'))

# --- Transport Self-car and Wrecker Management ---
@app.route('/transport/selfcar_wrecker')
def transport_selfcar_wrecker():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('transport_selfcar_wrecker.html')



# --- Transport Shipping Fee Management ---
@app.route('/transport/shipping_fee')
def transport_shipping_fee():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    year = request.args.get('year', type=int, default=datetime.now().year)
    month = request.args.get('month', type=int, default=datetime.now().month)

    query = "SELECT * FROM shipping_fee_management WHERE 1=1"
    params = []

    if year and month:
        query += " AND strftime('%Y', date) = ? AND strftime('%m', date) = ?"
        params.append(str(year))
        params.append(f'{month:02d}')

    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()

    return render_template('transport_shipping_fee.html',
                           records=records,
                           search_year=year,
                           search_month=month,
                           now=datetime.now())

@app.route('/transport/shipping_fee/add', methods=['POST'])
def add_shipping_fee():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Determine category based on withdrawal_date
        withdrawal_date = request.form.get('withdrawal_date')
        category = '완료' if withdrawal_date else '미완료'

        # Calculate profit
        billing_amount = request.form.get('billing_amount', type=float, default=0)
        withdrawal_amount = request.form.get('withdrawal_amount', type=float, default=0)
        profit = billing_amount - withdrawal_amount

        cursor.execute("INSERT INTO shipping_fee_management (category, date, withdrawal_date, withdrawal_bank, withdrawal_amount, customer_company, vehicle_number, billing_amount, profit, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (category,
                        request.form.get('date'),
                        withdrawal_date,
                        request.form.get('withdrawal_bank'),
                        withdrawal_amount,
                        request.form.get('customer_company'),
                        request.form.get('vehicle_number'),
                        billing_amount,
                        profit,
                        request.form.get('note')))
        conn.commit()
        flash('선적료 기록이 성공적으로 추가되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'선적료 기록 추가 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_shipping_fee'))

@app.route('/transport/shipping_fee/edit', methods=['POST'])
def edit_shipping_fee():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        record_id = request.form.get('id', type=int)
        withdrawal_date = request.form.get('withdrawal_date')
        category = '완료' if withdrawal_date else '미완료'

        billing_amount = request.form.get('billing_amount', type=float, default=0)
        withdrawal_amount = request.form.get('withdrawal_amount', type=float, default=0)
        profit = billing_amount - withdrawal_amount

        cursor.execute("UPDATE shipping_fee_management SET category = ?, date = ?, withdrawal_date = ?, withdrawal_bank = ?, withdrawal_amount = ?, customer_company = ?, vehicle_number = ?, billing_amount = ?, profit = ?, note = ? WHERE id = ?",
                       (category,
                        request.form.get('date'),
                        withdrawal_date,
                        request.form.get('withdrawal_bank'),
                        withdrawal_amount,
                        request.form.get('customer_company'),
                        request.form.get('vehicle_number'),
                        billing_amount,
                        profit,
                        request.form.get('note'),
                        record_id))
        conn.commit()
        flash('선적료 기록이 성공적으로 수정되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'선적료 기록 수정 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_shipping_fee'))

@app.route('/transport/shipping_fee/delete', methods=['POST'])
def delete_shipping_fee():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        record_id = request.form.get('id', type=int)
        cursor.execute("DELETE FROM shipping_fee_management WHERE id = ?", (record_id,))
        conn.commit()
        flash('선적료 기록이 성공적으로 삭제되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'선적료 기록 삭제 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_shipping_fee'))

@app.route('/transport/shipping_fee/upload_excel', methods=['POST'])
def upload_shipping_fee_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    flash('선적료 엑셀 업로드 기능은 아직 구현되지 않았습니다.', 'info')
    return redirect(url_for('transport_shipping_fee'))

@app.route('/transport/shipping_fee/save_data', methods=['POST'])
def save_shipping_fee_data():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    flash('선적료 데이터 저장 기능은 아직 구현되지 않았습니다.', 'info')
    return redirect(url_for('transport_shipping_fee'))




# --- Transport Special Vehicle Management ---
@app.route('/transport/special_vehicle')
def transport_special_vehicle():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    year = request.args.get('year', type=int, default=datetime.now().year)
    month = request.args.get('month', type=int, default=datetime.now().month)

    query = "SELECT * FROM special_vehicle_management WHERE 1=1"
    params = []

    if year and month:
        query += " AND strftime('%Y', delivery_date) = ? AND strftime('%m', delivery_date) = ?"
        params.append(str(year))
        params.append(f'{month:02d}')

    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()

    return render_template('transport_special_vehicle.html',
                           records=records,
                           search_year=year,
                           search_month=month,
                           now=datetime.now())

@app.route('/transport/special_vehicle/add', methods=['POST'])
def add_special_vehicle():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        # Determine category based on dates
        arrival_date = request.form.get('arrival_date')
        departure_date = request.form.get('departure_date')
        category = '미입고'
        if arrival_date: category = '입고'
        if departure_date: category = '출고'

        cursor.execute("INSERT INTO special_vehicle_management (category, vehicle_source, delivery_date, arrival_date, departure_date, origin, destination, vehicle_number, driver, driver_phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (category,
                        request.form.get('vehicle_source'),
                        request.form.get('delivery_date'),
                        arrival_date,
                        departure_date,
                        request.form.get('origin'),
                        request.form.get('destination'),
                        request.form.get('vehicle_number'),
                        request.form.get('driver'),
                        request.form.get('driver_phone')))
        conn.commit()
        flash('특별차량 기록이 성공적으로 추가되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'특별차량 기록 추가 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_special_vehicle'))

@app.route('/transport/special_vehicle/edit', methods=['POST'])
def edit_special_vehicle():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        record_id = request.form.get('id', type=int)
        arrival_date = request.form.get('arrival_date')
        departure_date = request.form.get('departure_date')
        category = '미입고'
        if arrival_date: category = '입고'
        if departure_date: category = '출고'

        cursor.execute("UPDATE special_vehicle_management SET category = ?, vehicle_source = ?, delivery_date = ?, arrival_date = ?, departure_date = ?, origin = ?, destination = ?, vehicle_number = ?, driver = ?, driver_phone = ? WHERE id = ?",
                       (category,
                        request.form.get('vehicle_source'),
                        request.form.get('delivery_date'),
                        arrival_date,
                        departure_date,
                        request.form.get('origin'),
                        request.form.get('destination'),
                        request.form.get('vehicle_number'),
                        request.form.get('driver'),
                        request.form.get('driver_phone'),
                        record_id))
        conn.commit()
        flash('특별차량 기록이 성공적으로 수정되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'특별차량 기록 수정 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_special_vehicle'))

@app.route('/transport/special_vehicle/delete', methods=['POST'])
def delete_special_vehicle():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        record_id = request.form.get('id', type=int)
        cursor.execute("DELETE FROM special_vehicle_management WHERE id = ?", (record_id,))
        conn.commit()
        flash('특별차량 기록이 성공적으로 삭제되었습니다.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'특별차량 기록 삭제 중 오류 발생: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('transport_special_vehicle'))

@app.route('/transport/special_vehicle/upload_excel', methods=['POST'])
def upload_special_vehicle_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    flash('특별차량 엑셀 업로드 기능은 아직 구현되지 않았습니다.', 'info')
    return redirect(url_for('transport_special_vehicle'))

@app.route('/transport/special_vehicle/save_data', methods=['POST'])
def save_special_vehicle_data():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    flash('특별차량 데이터 저장 기능은 아직 구현되지 않았습니다.', 'info')
    return redirect(url_for('transport_special_vehicle'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5009)
