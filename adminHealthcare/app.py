from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, send_file, g
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# Configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key_change_this'),
    MYSQL_HOST=os.environ.get('MYSQL_HOST', 'localhost'),
    MYSQL_USER=os.environ.get('MYSQL_USER', 'root'),
    MYSQL_PASSWORD=os.environ.get('MYSQL_PASSWORD', 'root'),
    MYSQL_DB=os.environ.get('MYSQL_DB', 'healthcare'),
    MYSQL_CURSORCLASS='DictCursor',  # This enables dictionary results
    UPLOAD_FOLDER='uploads'
)

mysql = MySQL(app)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Database utility functions
def get_db():
    if 'db' not in g:
        g.db = mysql.connection.cursor()
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_cursor():
    return mysql.connection.cursor()

def get_admin_by_email(email):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT * FROM admins WHERE email = %s", (email,))
        return cur.fetchone()
    finally:
        cur.close()

# Routes
@app.route('/')
def index():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        admin = get_admin_by_email(email)
        
        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_id'] = admin['id']
            session['admin_name'] = admin['full_name']
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
            
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        
        if get_admin_by_email(email):
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO admins (full_name, email, password_hash, created_at) VALUES (%s, %s, %s, NOW())",
                (full_name, email, generate_password_hash(password))
            )
            mysql.connection.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Registration failed. Please try again.', 'error')
            return redirect(url_for('register'))
        finally:
            cur.close()
        
    return render_template('register.html')

# Dashboard route - redirects to admin dashboard for now
@app.route('/dashboard')
@login_required
def dashboard():
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Get all doctors
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT d.*, 
               COUNT(v.id) as verification_count,
               MAX(v.verified_at) as last_verification_date
        FROM doctors d
        LEFT JOIN verification_logs v ON d.id = v.doctor_id
        GROUP BY d.id
        ORDER BY d.created_at DESC
    """)
    doctors = cur.fetchall()
    cur.close()
    
    # Count statistics
    total_doctors = len(doctors)
    verified_doctors = sum(1 for doctor in doctors if doctor['is_verified'])
    pending_doctors = total_doctors - verified_doctors
    
    return render_template('admin/dashboard.html', 
                          doctors=doctors,
                          stats={
                              'total': total_doctors,
                              'verified': verified_doctors,
                              'pending': pending_doctors
                          })

@app.route('/admin/doctor/<int:doctor_id>')
@login_required
def admin_view_doctor(doctor_id):
    # Get doctor details
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM doctors WHERE id = %s", [doctor_id])
    doctor = cur.fetchone()
    
    if not doctor:
        flash('Doctor not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Get verification history
    cur.execute("""
        SELECT vl.*, a.full_name as admin_name 
        FROM verification_logs vl
        JOIN admins a ON vl.admin_id = a.id
        WHERE vl.doctor_id = %s
        ORDER BY vl.verified_at DESC
    """, [doctor_id])
    verification_history = cur.fetchall()
    cur.close()
    
    return render_template('admin/doctor_details.html', 
                          doctor=doctor,
                          verification_history=verification_history)

@app.route('/admin/verify/<int:doctor_id>', methods=['POST'])
@login_required
def verify_doctor(doctor_id):
    action = request.form.get('action', 'verify')
    notes = request.form.get('notes', '')
    admin_id = session.get('admin_id')  # Get the actual admin ID from session
    
    try:
        # Update doctor verification status
        cur = mysql.connection.cursor()
        is_verified = True if action == 'verify' else False
        cur.execute("UPDATE doctors SET is_verified = %s WHERE id = %s", 
                   [is_verified, doctor_id])
        
        # Log the verification action
        cur.execute("""
            INSERT INTO verification_logs
            (doctor_id, admin_id, verification_notes, action_type, verified_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, [doctor_id, admin_id, notes, action])
        
        mysql.connection.commit()
        cur.close()
        
        action_text = "verified" if is_verified else "unverified"
        flash(f'Doctor successfully {action_text}!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin_view_doctor', doctor_id=doctor_id))

@app.route('/admin/download-document/<int:doctor_id>')
@login_required
def download_doctor_document(doctor_id):
    # Get the document filename from the database
    cur = mysql.connection.cursor()
    cur.execute("SELECT verification_documents FROM doctors WHERE id = %s", [doctor_id])
    doctor = cur.fetchone()
    cur.close()
    
    if not doctor or not doctor['verification_documents']:
        flash('Document not found', 'error')
        return redirect(url_for('admin_view_doctor', doctor_id=doctor_id))
    
    # Path where doctor documents are actually stored
    # Adjust this path to match your actual structure where doctor files are stored
    file_path = os.path.join('C:/doctorManage/static/uploads/qualifications', doctor['verification_documents'])
    
    # Check if file exists
    if not os.path.exists(file_path):
        flash('Document file not found on server', 'error')
        return redirect(url_for('admin_view_doctor', doctor_id=doctor_id))
    
    # Return the file as an attachment (forces download)
    return send_file(file_path, as_attachment=True)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=False)