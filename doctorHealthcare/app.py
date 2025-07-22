from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, jsonify, send_file, send_from_directory
from flask_login import LoginManager, current_user, login_required, UserMixin
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
from datetime import datetime, timedelta, date, time  # Make sure 'time' is imported
import json
import calendar
from flask_paginate import Pagination
import MySQLdb.cursors
import secrets
import time
import time as time_module

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'healthcare'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize MySQL
mysql = MySQL(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

UPLOAD_FOLDER = 'static/uploads/qualifications'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Decorator for login requirement
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please login first!', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to check if doctor is verified
def verification_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please login first!', 'danger')
            return redirect(url_for('login'))
            
        # Check verification status
        cur = mysql.connection.cursor()
        cur.execute("SELECT is_verified FROM doctors WHERE id = %s", [session['id']])
        doctor = cur.fetchone()
        cur.close()
        
        if not doctor or not doctor['is_verified']:
            flash('Access restricted. Your account needs to be verified first.', 'warning')
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

# Add this helper function near the top of the file, after imports
def convert_timedelta_to_time(time_value):
    """Convert timedelta or time objects to time objects"""
    if isinstance(time_value, timedelta):
        # Convert timedelta to time
        hours = int(time_value.total_seconds() // 3600)
        minutes = int((time_value.total_seconds() % 3600) // 60)
        return time(hour=hours, minute=minutes)
    elif isinstance(time_value, time):
        return time_value
    return None

class User(UserMixin):
    def __init__(self, id, name, email, password, specialty, license_number, qualification, experience_years, verification_documents, is_verified, is_online):
        self.id = id
        self.name = name
        self.email = email
        self.password = password
        self.specialty = specialty
        self.license_number = license_number
        self.qualification = qualification
        self.experience_years = experience_years
        self.verification_documents = verification_documents
        self.is_verified = is_verified
        self.is_online = is_online
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM doctors WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        
        if user_data:
            return User(
                user_data['id'], user_data['name'], user_data['email'], user_data['password'],
                user_data['specialty'], user_data['license_number'], user_data['qualification'],
                user_data['experience_years'], user_data['verification_documents'],
                user_data['is_verified'], user_data['is_online']
            )
        return None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None
    finally:
        if 'cursor' in locals():
            cursor.close()
# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        email = request.form['email']
        password = request.form['password']
        
        # Check if account exists in the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM doctors WHERE email = %s", [email])
        doctor = cur.fetchone()
        cur.close()
        
        # If account exists and password is correct
        if doctor and check_password_hash(doctor['password'], password):
            # Create session data
            session['logged_in'] = True
            session['id'] = doctor['id']
            session['name'] = doctor['name']
            session['email'] = doctor['email']
            session['is_verified'] = doctor['is_verified']
            
            # Update doctor's online status
            cur = mysql.connection.cursor()
            cur.execute("UPDATE doctors SET is_online = TRUE WHERE id = %s", [doctor['id']])
            mysql.connection.commit()
            cur.close()
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            specialty = request.form['specialty']
            license_number = request.form['license_number']
            qualification = request.form.get('qualification', '')
            experience_years = request.form['experience_years']
            
            # Check if email already exists
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM doctors WHERE email = %s", [email])
            existing_doctor = cur.fetchone()
            cur.close()
            
            if existing_doctor:
                flash('Email already registered!', 'danger')
                return redirect(url_for('register'))
            
            # Handle file upload
            qualification_file = request.files['qualification_docs']
            
            if qualification_file and allowed_file(qualification_file.filename):
                filename = secure_filename(qualification_file.filename)
                unique_filename = f"{email}_{int(time.time())}.{filename.rsplit('.', 1)[1].lower()}"
                
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                qualification_file.save(file_path)
                
                hashed_password = generate_password_hash(password)
                # Changed qualification_document to verification_documents to match schema
                cur = mysql.connection.cursor()
                query = """
                    INSERT INTO doctors (name, email, password, specialty, 
                                       license_number, qualification, experience_years, 
                                       verification_documents, is_verified, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, NOW())
                """
                values = (name, email, hashed_password, specialty,
                         license_number, qualification, experience_years, unique_filename)
                
                cur.execute(query, values)
                mysql.connection.commit()
                cur.close()
                
                flash('Registration successful! Your account is pending verification by an administrator.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Please upload a valid qualification document (PDF, DOC, DOCX, JPG, JPEG, PNG).', 'danger')
                
        except Exception as e:
            print("Error:", str(e))
            mysql.connection.rollback()
            flash('Registration failed: ' + str(e), 'danger')
            
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get doctor data
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM doctors WHERE id = %s", [session['id']])
    doctor = cur.fetchone()
    cur.close()
    
    if not doctor:
        flash('Account not found!', 'danger')
        session.clear()
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', doctor=doctor)

@app.route('/logout')
def logout():
    if 'id' in session:
        # Update doctor's online status
        cur = mysql.connection.cursor()
        cur.execute("UPDATE doctors SET is_online = FALSE WHERE id = %s", [session['id']])
        mysql.connection.commit()
        cur.close()
    
    # Clear session
    session.clear()
    flash('You have been logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    # Get doctor data
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM doctors WHERE id = %s", [session['id']])
    doctor = cur.fetchone()
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            specialty = request.form['specialty']
            license_number = request.form['license_number']
            qualification = request.form.get('qualification', '')
            experience_years = request.form['experience_years']
            
            # If doctor is already verified, set verification to pending on profile changes
            reset_verification = doctor['is_verified'] and (
                specialty != doctor['specialty'] or
                license_number != doctor['license_number'] or
                qualification != doctor['qualification'] or
                int(experience_years) != doctor['experience_years'] or
                'verification_documents' in request.files and 
                request.files['verification_documents'].filename != ''
            )
            
            # Initialize update query and values
            update_query = """
                UPDATE doctors SET name = %s, specialty = %s, license_number = %s, 
                qualification = %s, experience_years = %s
            """
            update_values = [name, specialty, license_number, qualification, experience_years]
            
            # Handle verification document update if file is uploaded
            if 'verification_documents' in request.files:
                verification_file = request.files['verification_documents']
                
                if verification_file and verification_file.filename != '' and allowed_file(verification_file.filename):
                    # Delete old file if it exists
                    if doctor['verification_documents']:
                        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], doctor['verification_documents'])
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    # Save new file
                    filename = secure_filename(verification_file.filename)
                    unique_filename = f"{session['email']}_{int(time.time())}.{filename.rsplit('.', 1)[1].lower()}"
                    
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    verification_file.save(file_path)
                    
                    # Update query to include file
                    update_query += ", verification_documents = %s"
                    update_values.append(unique_filename)
            
            # Reset verification status if needed
            if reset_verification:
                update_query += ", is_verified = FALSE"
                
            # Complete the query with WHERE clause and timestamp
            update_query += ", updated_at = NOW() WHERE id = %s"
            update_values.append(session['id'])
            
            # Execute the update
            cur.execute(update_query, update_values)
            mysql.connection.commit()
            
            if reset_verification:
                flash('Profile updated successfully! Your verification status has been reset and is pending review.', 'warning')
                session['is_verified'] = False
            else:
                flash('Profile updated successfully!', 'success')
                
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            print("Error:", str(e))
            mysql.connection.rollback()
            flash('Profile update failed: ' + str(e), 'danger')
    
    cur.close()
    return render_template('update_profile.html', doctor=doctor)

@app.route('/appointments', methods=['GET', 'POST'])
@login_required
@verification_required
def appointments():
    cur = None
    try:
        # Get doctor details
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM doctors WHERE id = %s", [session['id']])
        doctor = cur.fetchone()

        if request.method == 'POST':
            try:
                # Get form data
                schedule_date = request.form['schedule_date']
                start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
                
                # Calculate end time (30 minutes after start time)
                end_time = (datetime.combine(datetime.today(), start_time) + 
                          timedelta(minutes=30)).time()
                
                # Check if date is in the past
                if datetime.strptime(schedule_date, '%Y-%m-%d').date() < datetime.today().date():
                    flash('Cannot schedule appointments in the past', 'danger')
                    return redirect(url_for('appointments'))
                
                # Check for overlapping schedules
                cur.execute("""
                    SELECT COUNT(*) as count 
                    FROM doctor_availability 
                    WHERE doctor_id = %s 
                    AND schedule_date = %s
                    AND ((start_time <= %s AND end_time > %s)
                         OR (start_time < %s AND end_time >= %s)
                         OR (start_time >= %s AND end_time <= %s))
                """, [session['id'], schedule_date, start_time, start_time, 
                      end_time, end_time, start_time, end_time])
                
                if cur.fetchone()['count'] > 0:
                    flash('This time slot overlaps with an existing schedule', 'danger')
                    return redirect(url_for('appointments'))
                
                # Insert new schedule with fixed 30-minute duration
                cur.execute("""
                    INSERT INTO doctor_availability 
                    (doctor_id, schedule_date, start_time, end_time, slot_duration, is_available)
                    VALUES (%s, %s, %s, %s, 30, TRUE)
                """, [session['id'], schedule_date, start_time, end_time])
                
                mysql.connection.commit()
                flash('Schedule added successfully', 'success')
                return redirect(url_for('appointments'))
                
            except ValueError:
                flash('Invalid time format', 'danger')
                return redirect(url_for('appointments'))
                
            except Exception as e:
                print(f"Error adding availability: {str(e)}")
                mysql.connection.rollback()
                flash('Failed to add schedule. Please try again.', 'danger')
                return redirect(url_for('appointments'))

        # For GET request, fetch current availability schedule with appointment counts
        cur.execute("""
            SELECT 
                da.id,
                da.schedule_date,
                da.start_time,
                da.end_time,
                da.slot_duration,
                da.is_available,
                COUNT(a.id) as booked_appointments
            FROM doctor_availability da
            LEFT JOIN appointments a ON 
                da.doctor_id = a.doctor_id 
                AND da.schedule_date = a.appointment_date 
                AND da.start_time = a.appointment_time 
                AND a.status = 'scheduled'
            WHERE da.doctor_id = %s
            AND da.schedule_date >= CURDATE()
            GROUP BY 
                da.id,
                da.schedule_date,
                da.start_time,
                da.end_time,
                da.slot_duration,
                da.is_available
            ORDER BY da.schedule_date, da.start_time
        """, [session['id']])
        schedules = cur.fetchall()

        # Format schedules for template
        formatted_schedules = []
        for schedule in schedules:
            start_time = convert_timedelta_to_time(schedule['start_time'])
            end_time = convert_timedelta_to_time(schedule['end_time'])
            
            formatted_schedules.append({
                'id': schedule['id'],
                'schedule_date': schedule['schedule_date'],
                'start_time': start_time.strftime('%H:%M') if start_time else '',
                'end_time': end_time.strftime('%H:%M') if end_time else '',
                'duration': schedule['slot_duration'],
                'is_available': schedule['is_available'],
                'booked_appointments': schedule['booked_appointments']
            })

        return render_template('appointments.html',
                             doctor=doctor,
                             schedules=formatted_schedules)

    except Exception as e:
        print(f"Error in appointments route: {str(e)}")
        flash('Failed to load schedule data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))

    finally:
        if cur:
            cur.close()

@app.route('/appointments/delete/<int:schedule_id>', methods=['POST'])
@login_required
@verification_required
def delete_appointment(schedule_id):
    cur = None
    try:
        cur = mysql.connection.cursor()
        
        # Check if schedule exists and belongs to the doctor
        cur.execute("""
            SELECT id FROM doctor_availability 
            WHERE id = %s AND doctor_id = %s
        """, [schedule_id, session['id']])
        
        if not cur.fetchone():
            flash('Schedule not found or unauthorized', 'danger')
            return redirect(url_for('appointments'))
        
        # Delete the schedule
        cur.execute("""
            DELETE FROM doctor_availability 
            WHERE id = %s AND doctor_id = %s
        """, [schedule_id, session['id']])
        
        mysql.connection.commit()
        flash('Schedule deleted successfully', 'success')
        
    except Exception as e:
        print(f"Error deleting availability: {str(e)}")
        flash('Failed to delete schedule. Please try again.', 'danger')
        mysql.connection.rollback()
        
    finally:
        if cur:
            cur.close()
    
    return redirect(url_for('appointments'))

@app.route('/api/availability', methods=['GET'])
@login_required
@verification_required
def get_availability():
    cur = None
    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Get doctor details
        cur.execute("SELECT * FROM doctors WHERE id = %s", [session['id']])
        doctor = cur.fetchone()
        
        # Get schedules and appointments - updated to use availability_id from appointments table
        cur.execute("""
            SELECT da.id, da.schedule_date, da.start_time, da.end_time, da.slot_duration, 
                   COALESCE(a.status, 'available') as slot_status,
                   COALESCE(a.patient_id, 0) as patient_id
            FROM doctor_availability da
            LEFT JOIN appointments a ON da.id = a.availability_id AND da.doctor_id = a.doctor_id
            WHERE da.doctor_id = %s AND da.schedule_date >= CURDATE() AND da.is_available = TRUE
            ORDER BY da.schedule_date, da.start_time
        """, [session['id']])
        schedules = cur.fetchall()
        
        # Format schedules for template
        formatted_schedules = []
        for schedule in schedules:
            start_time = convert_timedelta_to_time(schedule['start_time'])
            end_time = convert_timedelta_to_time(schedule['end_time'])
            formatted_schedules.append({
                'id': schedule['id'],
                'schedule_date': schedule['schedule_date'],
                'start_time': start_time.strftime('%H:%M') if start_time else '',
                'end_time': end_time.strftime('%H:%M') if end_time else '',
                'duration': schedule['slot_duration'],
                'status': schedule['slot_status'],
                'is_available': schedule['slot_status'] == 'available' or schedule['slot_status'] == 'pending_approval',
                'patient_id': schedule['patient_id']
            })
            
        return render_template('appointments.html', doctor=doctor, schedules=formatted_schedules)
    
    except Exception as e:
        print(f"Error fetching availability: {str(e)}")
        flash('Failed to load schedules. Please try again.', 'danger')
        return redirect(url_for('appointments'))
    
    finally:
        if cur:
            cur.close()
            
@app.route('/appointments/delete/<int:id>', methods=['POST'])
@login_required
@verification_required
def delete_schedule(id):
    cur = None
    try:
        cur = mysql.connection.cursor()
        
        # Check if there are any appointments for this schedule
        cur.execute("""
            SELECT COUNT(*) 
            FROM appointments 
            WHERE doctor_id = %s
            AND availability_id = %s
            AND status = 'scheduled'
        """, [session['id'], id])
        
        if cur.fetchone()[0] > 0:
            flash('Cannot delete schedule with existing appointments', 'danger')
            return redirect(url_for('appointments'))
            
        # Delete the schedule
        cur.execute("DELETE FROM doctor_availability WHERE id = %s AND doctor_id = %s", 
                   [id, session['id']])
        mysql.connection.commit()
        
        flash('Schedule deleted successfully', 'success')
    except Exception as e:
        print(f"Error deleting schedule: {str(e)}")
        flash('Failed to delete schedule', 'danger')
        mysql.connection.rollback()
    finally:
        if cur:
            cur.close()
    return redirect(url_for('appointments'))

@app.route('/patients')
@login_required
@verification_required
def patients():
    current_filter = request.args.get('filter', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of patients per page
    
    # Get doctor information
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM doctors WHERE id = %s", [session['id']])
    doctor = cur.fetchone()
    
    if not doctor:
        flash('Account not found!', 'danger')
        session.clear()
        return redirect(url_for('login'))
    
    # Filter logic
    if current_filter == 'recent':
        # Get patients with recent appointments
        cur.execute("""
            SELECT DISTINCT u.id, u.full_name AS name, 
            MAX(hd.contact_number) as contact_number, 
            MAX(hd.date_of_birth) as date_of_birth,
            (SELECT a.appointment_date FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND a.status = 'completed'
             ORDER BY a.appointment_date DESC LIMIT 1) AS last_appointment_date,
            (SELECT a.appointment_time FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND a.status = 'completed'
             ORDER BY a.appointment_date DESC LIMIT 1) AS last_appointment_time,
            (SELECT a.appointment_date FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND (a.status = 'scheduled' OR a.status = 'pending_approval')
             ORDER BY a.appointment_date ASC LIMIT 1) AS next_appointment_date,
            (SELECT a.appointment_time FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND (a.status = 'scheduled' OR a.status = 'pending_approval')
             ORDER BY a.appointment_date ASC LIMIT 1) AS next_appointment_time
            FROM users u
            INNER JOIN appointments a ON u.id = a.patient_id
            LEFT JOIN health_details hd ON u.id = hd.user_id
            WHERE a.doctor_id = %s AND a.status = 'completed'
            GROUP BY u.id, u.full_name
            ORDER BY last_appointment_date DESC
            LIMIT %s OFFSET %s
        """, (session['id'], session['id'], session['id'], session['id'], session['id'], per_page, (page-1)*per_page))
    elif current_filter == 'upcoming':
        # Get patients with upcoming appointments
        cur.execute("""
            SELECT DISTINCT u.id, u.full_name AS name, 
            MAX(hd.contact_number) as contact_number, 
            MAX(hd.date_of_birth) as date_of_birth,
            (SELECT a.appointment_date FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND a.status = 'completed'
             ORDER BY a.appointment_date DESC LIMIT 1) AS last_appointment_date,
            (SELECT a.appointment_time FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND a.status = 'completed'
             ORDER BY a.appointment_date DESC LIMIT 1) AS last_appointment_time,
            (SELECT a.appointment_date FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND (a.status = 'scheduled' OR a.status = 'pending_approval')
             ORDER BY a.appointment_date ASC LIMIT 1) AS next_appointment_date,
            (SELECT a.appointment_time FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND (a.status = 'scheduled' OR a.status = 'pending_approval')
             ORDER BY a.appointment_date ASC LIMIT 1) AS next_appointment_time
            FROM users u
            INNER JOIN appointments a ON u.id = a.patient_id
            LEFT JOIN health_details hd ON u.id = hd.user_id
            WHERE a.doctor_id = %s AND (a.status = 'scheduled' OR a.status = 'pending_approval')
            GROUP BY u.id, u.full_name
            ORDER BY next_appointment_date ASC
            LIMIT %s OFFSET %s
        """, (session['id'], session['id'], session['id'], session['id'], session['id'], per_page, (page-1)*per_page))
    else:
        # Get all patients
        cur.execute("""
            SELECT DISTINCT u.id, u.full_name AS name, 
            MAX(hd.contact_number) as contact_number, 
            MAX(hd.date_of_birth) as date_of_birth,
            (SELECT a.appointment_date FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND a.status = 'completed'
             ORDER BY a.appointment_date DESC LIMIT 1) AS last_appointment_date,
            (SELECT a.appointment_time FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND a.status = 'completed'
             ORDER BY a.appointment_date DESC LIMIT 1) AS last_appointment_time,
            (SELECT a.appointment_date FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND (a.status = 'scheduled' OR a.status = 'pending_approval')
             ORDER BY a.appointment_date ASC LIMIT 1) AS next_appointment_date,
            (SELECT a.appointment_time FROM appointments a 
             WHERE a.patient_id = u.id AND a.doctor_id = %s AND (a.status = 'scheduled' OR a.status = 'pending_approval')
             ORDER BY a.appointment_date ASC LIMIT 1) AS next_appointment_time
            FROM users u
            INNER JOIN appointments a ON u.id = a.patient_id
            LEFT JOIN health_details hd ON u.id = hd.user_id
            WHERE a.doctor_id = %s
            GROUP BY u.id, u.full_name
            ORDER BY u.full_name
            LIMIT %s OFFSET %s
        """, (session['id'], session['id'], session['id'], session['id'], session['id'], per_page, (page-1)*per_page))
    
    patients_data = cur.fetchall()
    
    # Count total patients for pagination
    if current_filter == 'recent':
        cur.execute("""
            SELECT COUNT(DISTINCT u.id) AS total FROM users u
            INNER JOIN appointments a ON u.id = a.patient_id
            WHERE a.doctor_id = %s AND a.status = 'completed'
        """, [session['id']])
    elif current_filter == 'upcoming':
        cur.execute("""
            SELECT COUNT(DISTINCT u.id) AS total FROM users u
            INNER JOIN appointments a ON u.id = a.patient_id
            WHERE a.doctor_id = %s AND (a.status = 'scheduled' OR a.status = 'pending_approval')
        """, [session['id']])
    else:
        cur.execute("""
            SELECT COUNT(DISTINCT u.id) AS total FROM users u
            INNER JOIN appointments a ON u.id = a.patient_id
            WHERE a.doctor_id = %s
        """, [session['id']])
    
    result = cur.fetchone()
    total_count = result['total']
    total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
    
    # Process the patients data
    patients = []
    for patient in patients_data:
        # Function to format timedelta as HH:MM
        def format_timedelta(td):
            if td is None:
                return None
            # Total seconds in the timedelta
            total_seconds = int(td.total_seconds())
            # Extract hours and minutes
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}"
        
        patient_info = {
            'id': patient['id'],
            'name': patient['name'],
            'contact_number': patient['contact_number'] if patient['contact_number'] else 'Not provided',
            'date_of_birth': patient['date_of_birth'].strftime('%Y-%m-%d') if patient['date_of_birth'] else 'Not provided',
            'last_appointment': {
                'appointment_date': patient['last_appointment_date'].strftime('%Y-%m-%d') if patient.get('last_appointment_date') else None,
                'appointment_time': format_timedelta(patient['last_appointment_time']) if patient.get('last_appointment_time') else None
            } if patient.get('last_appointment_date') else None,
            'next_appointment': {
                'appointment_date': patient['next_appointment_date'].strftime('%Y-%m-%d') if patient.get('next_appointment_date') else None,
                'appointment_time': format_timedelta(patient['next_appointment_time']) if patient.get('next_appointment_time') else None
            } if patient.get('next_appointment_date') else None
        }
        patients.append(patient_info)
    
    # Pagination info
    pagination = {
        'page': page,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1,
        'next_num': page + 1,
        'total_pages': total_pages
    }
    
    cur.close()
    
    return render_template('patients.html', doctor=doctor, patients=patients, pagination=pagination, current_filter=current_filter)

@app.route('/api/patients/<int:patient_id>')
@login_required
@verification_required
def get_patient_details(patient_id):
    cur = mysql.connection.cursor()
    
    # Get patient basic info by joining users and health_details
    cur.execute("""
        SELECT 
            u.id, 
            u.full_name as name, 
            u.email, 
            hd.date_of_birth, 
            hd.contact_number,
            hd.previous_illnesses, 
            hd.current_medications, 
            hd.known_allergies, 
            hd.previous_surgeries,
            hd.document_path,
            hd.patient_name
        FROM users u
        LEFT JOIN health_details hd ON u.id = hd.user_id
        WHERE u.id = %s
    """, [patient_id])
    patient = cur.fetchone()
    
    if not patient:
        cur.close()
        return jsonify({'error': 'Patient not found'}), 404
    
    # Format date
    if patient['date_of_birth']:
        patient['date_of_birth'] = patient['date_of_birth'].strftime('%Y-%m-%d')
    
    # Get appointments
    cur.execute("""
        SELECT id, appointment_date, 
               TIME_FORMAT(appointment_time, '%%H:%%i') as formatted_time, 
               status
        FROM appointments
        WHERE patient_id = %s AND doctor_id = %s
        ORDER BY appointment_date DESC, appointment_time DESC
    """, [patient_id, session['id']])
    appointments = cur.fetchall()
    
    # Prepare document information
    document_info = {
        'has_document': False,
        'file_name': ''
    }
    
    if patient['document_path'] and os.path.exists(patient['document_path']):
        document_info['has_document'] = True
        document_info['file_name'] = os.path.basename(patient['document_path'])
    
    # Construct response
    response = {
        'id': patient['id'],
        'name': patient['patient_name'] or patient['name'],  # Use patient_name from health_details if available
        'email': patient['email'],
        'contact_number': patient['contact_number'] or 'Not provided',
        'date_of_birth': patient['date_of_birth'] or 'Not provided',
        'medical_history': {
            'previous_illnesses': patient['previous_illnesses'],
            'current_medications': patient['current_medications'],
            'known_allergies': patient['known_allergies'],
            'previous_surgeries': patient['previous_surgeries']
        },
        'appointments': [
            {
                'id': appt['id'],
                'appointment_date': appt['appointment_date'].strftime('%Y-%m-%d'),
                'appointment_time': appt['formatted_time'],
                'status': appt['status']
            } for appt in appointments
        ],
        'document_info': document_info
    }
    
    cur.close()
    
    return jsonify(response)
    
@app.route('/download-surgery-document/<int:patient_id>')
@login_required
@verification_required
def download_surgery_document(patient_id):
    # Verify this patient belongs to the doctor
    cur = mysql.connection.cursor()
    
    # First verify patient is associated with this doctor
    cur.execute("""
        SELECT COUNT(*) as count
        FROM appointments
        WHERE patient_id = %s AND doctor_id = %s
        LIMIT 1
    """, [patient_id, session['id']])
    
    result = cur.fetchone()
    
    if not result or result['count'] == 0:
        cur.close()
        flash('Access denied or patient not found', 'danger')
        return redirect(url_for('patients'))
    
    # Now get the document path
    cur.execute("""
        SELECT document_path
        FROM health_details
        WHERE user_id = %s
    """, [patient_id])
    
    health_details = cur.fetchone()
    cur.close()
    
    if not health_details or not health_details['document_path'] or not os.path.exists(health_details['document_path']):
        flash('Document not found', 'danger')
        return redirect(url_for('patients'))
    
    file_path = health_details['document_path']
    filename = os.path.basename(file_path)
    
    try:
        return send_file(file_path, 
                         download_name=filename, 
                         as_attachment=True)
    except Exception as e:
        app.logger.error(f"Error downloading file: {str(e)}")
        flash('Error downloading document', 'danger')
        return redirect(url_for('patients'))

@app.route('/view-surgery-document/<int:patient_id>')
@login_required
@verification_required
def view_surgery_document(patient_id):
    # Verify this patient belongs to the doctor
    cur = mysql.connection.cursor()
    
    # First verify patient is associated with this doctor
    cur.execute("""
        SELECT COUNT(*) as count
        FROM appointments
        WHERE patient_id = %s AND doctor_id = %s
        LIMIT 1
    """, [patient_id, session['id']])
    
    result = cur.fetchone()
    
    if not result or result['count'] == 0:
        cur.close()
        flash('Access denied or patient not found', 'danger')
        return redirect(url_for('patients'))
    
    # Now get the document path
    cur.execute("""
        SELECT document_path
        FROM health_details
        WHERE user_id = %s
    """, [patient_id])
    
    health_details = cur.fetchone()
    cur.close()
    
    if not health_details or not health_details['document_path'] or not os.path.exists(health_details['document_path']):
        flash('Document not found', 'danger')
        return redirect(url_for('patients'))
    
    file_path = health_details['document_path']
    
    try:
        return send_file(file_path, mimetype='application/pdf')
    except Exception as e:
        app.logger.error(f"Error viewing file: {str(e)}")
        flash('Error viewing document', 'danger')
        return redirect(url_for('patients'))
      
@app.route('/patients/search')
@login_required
@verification_required
def search_patients():
    query = request.args.get('q', '')
    
    if len(query) < 3:
        return jsonify({'patients': []})
    
    cur = mysql.connection.cursor()
    
    cur.execute("""
        SELECT DISTINCT u.id, u.full_name AS name, hd.contact_number
        FROM users u
        INNER JOIN appointments a ON u.id = a.patient_id
        LEFT JOIN health_details hd ON u.id = hd.user_id
        WHERE a.doctor_id = %s AND u.full_name LIKE %s
        GROUP BY u.id
        LIMIT 10
    """, [session['id'], f'%{query}%'])
    
    patients = cur.fetchall()
    
    cur.close()
    
    return jsonify({'patients': patients})

@app.route('/api/doctor/upi-details', methods=['GET'])
@login_required
@verification_required
def get_doctor_upi_details():
    doctor_id = session['id']
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, upi_id, is_verified, created_at
        FROM doctor_upi_details
        WHERE doctor_id = %s
    """, [doctor_id])
    
    upi_details = cur.fetchall()
    cur.close()
    
    return jsonify({
        'success': True,
        'upi_details': upi_details
    })

# Register new UPI ID for doctor
@app.route('/api/doctor/register-upi', methods=['POST'])
@login_required
@verification_required
def register_doctor_upi():
    doctor_id = session['id']
    data = request.get_json()
    
    if not data or 'upi_id' not in data:
        return jsonify({'success': False, 'error': 'UPI ID is required'}), 400
    
    upi_id = data['upi_id']
    
    # Simple validation
    if not upi_id or '@' not in upi_id:
        return jsonify({'success': False, 'error': 'Invalid UPI ID format'}), 400
    
    try:
        cur = mysql.connection.cursor()
        
        # Check if UPI ID already exists for this doctor
        cur.execute("SELECT id FROM doctor_upi_details WHERE doctor_id = %s AND upi_id = %s", 
                    [doctor_id, upi_id])
        existing = cur.fetchone()
        
        if existing:
            return jsonify({'success': True, 'message': 'UPI ID already registered'}), 200
        
        # Insert new UPI ID
        cur.execute("""
            INSERT INTO doctor_upi_details (doctor_id, upi_id)
            VALUES (%s, %s)
        """, [doctor_id, upi_id])
        
        mysql.connection.commit()
        newly_inserted_id = cur.lastrowid
        cur.close()
        
        return jsonify({
            'success': True,
            'upi_id': upi_id,
            'id': newly_inserted_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Send payment request to patient
@app.route('/api/send-payment-request', methods=['POST'])
@login_required
@verification_required
def send_payment_request():
    doctor_id = session['id']
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['patient_id', 'appointment_id', 'upi_id', 'amount', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
    
    patient_id = data['patient_id']
    appointment_id = data['appointment_id']
    upi_id = data['upi_id']
    amount = data['amount']
    description = data['description']
    
    try:
        cur = mysql.connection.cursor()
        
        # Verify UPI ID belongs to the doctor
        cur.execute("SELECT id FROM doctor_upi_details WHERE doctor_id = %s AND upi_id = %s", 
                    [doctor_id, upi_id])
        upi_check = cur.fetchone()
        
        if not upi_check:
            return jsonify({'success': False, 'error': 'Invalid UPI ID'}), 400
        
        # Verify appointment exists and belongs to this doctor and patient
        cur.execute("""
            SELECT id FROM appointments 
            WHERE id = %s AND doctor_id = %s AND patient_id = %s
        """, [appointment_id, doctor_id, patient_id])
        appointment = cur.fetchone()
        
        if not appointment:
            return jsonify({'success': False, 'error': 'Invalid appointment'}), 400
        
        # Check if payment request already exists for this appointment
        cur.execute("""
            SELECT id, status FROM payment_requests 
            WHERE appointment_id = %s AND status = 'pending'
        """, [appointment_id])
        existing_request = cur.fetchone()
        
        if existing_request:
            return jsonify({
                'success': False, 
                'error': 'A pending payment request already exists for this appointment'
            }), 400
        
        # Create new payment request
        cur.execute("""
            INSERT INTO payment_requests 
            (appointment_id, doctor_id, patient_id, amount, upi_id, status, request_date) 
            VALUES (%s, %s, %s, %s, %s, 'pending', %s)
        """, [appointment_id, doctor_id, patient_id, amount, upi_id, datetime.now()])
        
        mysql.connection.commit()
        request_id = cur.lastrowid
        cur.close()
        
        return jsonify({
            'success': True,
            'message': 'Payment request sent successfully',
            'request_id': request_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
# Update appointment status (approve/reject)
@app.route('/api/update-appointment-status', methods=['POST'])
@login_required
@verification_required
def update_appointment_status():
    doctor_id = session['id']
    data = request.get_json()
    
    if not data or 'appointment_id' not in data or 'status' not in data:
        return jsonify({'success': False, 'error': 'Appointment ID and status are required'}), 400
    
    appointment_id = data['appointment_id']
    new_status = data['status']
    
    # Validate status
    valid_statuses = ['scheduled', 'cancelled', 'completed']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'error': f'Invalid status value: {new_status}'}), 400
    
    try:
        cur = mysql.connection.cursor()  # Use dictionary cursor
        
        # Verify appointment exists and belongs to this doctor
        cur.execute("""
            SELECT a.id, a.patient_id, a.status, u.full_name as patient_name 
            FROM appointments a
            JOIN users u ON a.patient_id = u.id
            WHERE a.id = %s AND a.doctor_id = %s
        """, [appointment_id, doctor_id])
        
        appointment = cur.fetchone()
        
        if not appointment:
            return jsonify({'success': False, 'error': 'Invalid appointment'}), 400
        
        # If already in this status, just return success
        if appointment['status'] == new_status:
            return jsonify({'success': True, 'message': f'Appointment already {new_status}'}), 200
        
        # Update appointment status
        cur.execute("UPDATE appointments SET status = %s WHERE id = %s", [new_status, appointment_id])
        
        # Commit changes
        mysql.connection.commit()
        cur.close()
        
        # Log the successful update
        print(f"Successfully updated appointment {appointment_id} to status {new_status}")
        
        return jsonify({
            'success': True,
            'message': f'Appointment status updated to {new_status}'
        })
        
    except Exception as e:
        # Add better logging for debugging
        import traceback
        print(f"Error in update_appointment_status: {str(e)}")
        print(traceback.format_exc())
        
        # Make sure to rollback in case of error
        mysql.connection.rollback()
        if 'cur' in locals() and cur:
            cur.close()
            
        return jsonify({'success': False, 'error': str(e)}), 500
# Check payment status
@app.route('/api/check-payment-status/<int:request_id>', methods=['GET'])
@login_required
@verification_required
def check_payment_status(request_id):
    user_id = session['id']
    
    try:
        cur = mysql.connection.cursor()
        
        # Get payment request details
        cur.execute("""
            SELECT * FROM payment_requests 
            WHERE id = %s AND (patient_id = %s OR doctor_id = %s)
        """, [request_id, user_id, user_id])
        
        payment_request = cur.fetchone()
        cur.close()
        
        if not payment_request:
            return jsonify({'success': False, 'error': 'Payment request not found'}), 404
        
        return jsonify({
            'success': True,
            'payment_request': payment_request
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Update payment status (for patients to mark as paid or for doctors to confirm payment)
@app.route('/api/payment-requests/<int:patient_id>', methods=['GET'])
@login_required
@verification_required
def get_patient_payment_requests(patient_id):
    try:
        from datetime import datetime, date  # Import both datetime and date
        user_id = session['id']
        
        # Create a cursor
        cur = mysql.connection.cursor()
        
        # Determine if the user is a doctor
        cur.execute("SELECT id FROM doctors WHERE id = %s", [user_id])
        is_doctor = cur.fetchone() is not None
        
        if is_doctor:
            # For doctors
            cur.execute("""
                SELECT * FROM payment_requests 
                WHERE patient_id = %s AND doctor_id = %s
                ORDER BY request_date DESC
            """, [patient_id, user_id])
        else:
            # For patients
            cur.execute("""
                SELECT * FROM payment_requests 
                WHERE patient_id = %s
                ORDER BY request_date DESC
            """, [patient_id])
        
        # Process results
        payment_requests = []
        for row in cur.fetchall():
            # Convert row to dictionary if it's not already
            if not isinstance(row, dict):
                payment_request = {}
                for i, col_name in enumerate(cur.description):
                    payment_request[col_name[0]] = row[i]
            else:
                payment_request = dict(row)
                
            # Handle datetime objects for JSON serialization
            for key, value in payment_request.items():
                if isinstance(value, (datetime, date)):  # Use a tuple of types
                    payment_request[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    
            payment_requests.append(payment_request)
        
        cur.close()
        
        return jsonify({
            'success': True,
            'payment_requests': payment_requests
        })
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500# Update payment status (for patients to mark as paid or for doctors to confirm payment)

@app.route('/api/update-payment-status/<int:request_id>', methods=['POST'])
@login_required
@verification_required
def update_payment_status(request_id):
    try:
        user_id = session['id']
        
        # Fetch user_type directly from database without storing in session
        cur = mysql.connection.cursor()
        cur.execute("SELECT user_type FROM users WHERE id = %s", [user_id])
        result = cur.fetchone()
        
        if not result:
            return jsonify({'success': False, 'error': 'User not found'}), 404
            
        user_type = result['user_type']
        
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        
        new_status = data['status']
        transaction_id = data.get('transaction_id', None)
        
        # Validate status based on user type
        if user_type == 'patient' and new_status not in ['paid', 'cancelled']:
            return jsonify({'success': False, 'error': 'Invalid status for patient'}), 400
        
        if user_type == 'doctor' and new_status not in ['confirmed', 'failed']:
            return jsonify({'success': False, 'error': 'Invalid status for doctor'}), 400
        
        # Get payment request details
        cur.execute("""
            SELECT * FROM payment_requests 
            WHERE id = %s AND (patient_id = %s OR doctor_id = %s)
        """, [request_id, user_id, user_id])
        
        payment_request = cur.fetchone()
        
        if not payment_request:
            return jsonify({'success': False, 'error': 'Payment request not found'}), 404
        
        # For patients marking as paid
        if user_type == 'patient' and user_id == payment_request['patient_id']:
            if payment_request['status'] != 'pending':
                return jsonify({'success': False, 'error': 'Cannot update non-pending payment'}), 400
            
            # Update payment status
            if new_status == 'paid':
                cur.execute("""
                    UPDATE payment_requests 
                    SET status = %s, payment_date = %s, transaction_id = %s 
                    WHERE id = %s
                """, [new_status, datetime.now(), transaction_id, request_id])
                
                # Notify doctor
                cur.execute("""
                    INSERT INTO notifications 
                    (user_id, type, title, message, related_id, created_at) 
                    VALUES (%s, 'payment_update', 'Payment Received', %s, %s, %s)
                """, [
                    payment_request['doctor_id'],
                    f"Payment of ₹{payment_request['amount']} has been marked as paid",
                    request_id,
                    datetime.now()
                ])
            else:  # cancelled
                cur.execute("UPDATE payment_requests SET status = %s WHERE id = %s", 
                           ['cancelled', request_id])
                
                # Notify doctor
                cur.execute("""
                    INSERT INTO notifications 
                    (user_id, type, title, message, related_id, created_at) 
                    VALUES (%s, 'payment_update', 'Payment Cancelled', %s, %s, %s)
                """, [
                    payment_request['doctor_id'],
                    f"Payment request of ₹{payment_request['amount']} has been cancelled by the patient",
                    request_id,
                    datetime.now()
                ])
        
        # For doctors confirming payment
        elif user_type == 'doctor' and user_id == payment_request['doctor_id']:
            if payment_request['status'] != 'paid':
                return jsonify({'success': False, 'error': 'Can only confirm paid payments'}), 400
            
            final_status = 'confirmed' if new_status == 'confirmed' else 'failed'
            
            cur.execute("UPDATE payment_requests SET status = %s WHERE id = %s", 
                       [final_status, request_id])
            
            # Notify patient
            notification_title = "Payment Confirmed" if final_status == 'confirmed' else "Payment Failed"
            notification_message = f"Your payment of ₹{payment_request['amount']} has been {final_status}"
            
            cur.execute("""
                INSERT INTO notifications 
                (user_id, type, title, message, related_id, created_at) 
                VALUES (%s, 'payment_update', %s, %s, %s, %s)
            """, [
                payment_request['patient_id'],
                notification_title,
                notification_message,
                request_id,
                datetime.now()
            ])
        
        else:
            return jsonify({'success': False, 'error': 'Unauthorized to update this payment'}), 403
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({
            'success': True,
            'message': f'Payment status updated to {new_status}',
            'request_id': request_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
       
@app.route('/api/patient-appointment-status/<int:patient_id>', methods=['GET'])
@login_required
@verification_required
def check_patient_appointment_status(patient_id):
    cur = mysql.connection.cursor()
    
    # Check if there are any pending appointment requests
    cur.execute("""
        SELECT COUNT(*) as count
        FROM appointments
        WHERE patient_id = %s AND doctor_id = %s AND status = 'pending_approval'
    """, [patient_id, session['id']])
    
    result = cur.fetchone()
    has_pending = result and result['count'] > 0
    
    cur.close()
    return jsonify({
        'has_pending_appointments': has_pending
    })

@app.route('/api/payment-details/<int:payment_id>', methods=['GET'])
@login_required
def get_payment_details(payment_id):
    try:
        cur = mysql.connection.cursor()
        
        # First check if the current user is authorized to view this payment
        # For doctors, they should be the doctor associated with the payment
        # For patients, they should be the patient associated with the payment
        
        cur.execute("""
            SELECT pr.*, a.appointment_date, a.appointment_time, 
                   d.name as doctor_name, p.full_name as patient_name
            FROM payment_requests pr
            JOIN appointments a ON pr.appointment_id = a.id
            JOIN doctors d ON pr.doctor_id = d.id
            JOIN users p ON pr.patient_id = p.id
            WHERE pr.id = %s AND (pr.doctor_id = %s OR pr.patient_id = %s)
        """, [payment_id, session['id'], session['id']])
        
        payment = cur.fetchone()
        
        if not payment:
            return jsonify({'success': False, 'error': 'Payment not found or unauthorized'}), 404
        
        # Format dates for JSON serialization
        serializable_payment = {}
        for key, value in payment.items():
            # Make sure to check the proper type with isinstance
            if isinstance(value, timedelta) or isinstance(value, timedelta):
                # Convert TIME to string in format HH:MM:SS
                serializable_payment[key] = str(value)
            elif isinstance(value, (datetime, date, date, datetime)):
                # Convert datetime to ISO format string
                serializable_payment[key] = value.isoformat()
            else:
                serializable_payment[key] = value
        
        return jsonify({'success': True, 'payment': serializable_payment})
        
    except Exception as e:
        app.logger.error(f"Error getting payment details: {str(e)}")
        return jsonify({'success': False, 'error': f'Error getting payment details: {str(e)}'}), 500
    
@app.route('/api/verify-payment', methods=['POST'])
@login_required
def verify_payment():  
    try:
        data = request.json
        payment_id = data.get('payment_id')
        appointment_id = data.get('appointment_id')
        is_verified = data.get('is_verified', False)
        
        cur = mysql.connection.cursor()
        
        user_id = session.get('id') 
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID not found in session'}), 401
        
        # Check if the current user is the doctor for this payment
        cur.execute("""
            SELECT pr.id, pr.patient_id FROM payment_requests pr
            WHERE pr.id = %s AND pr.doctor_id = %s
        """, [payment_id, session['id']])
        
        payment_result = cur.fetchone()
        if not payment_result:
            return jsonify({'success': False, 'error': 'Unauthorized to verify this payment'}), 403
        
        patient_id = payment_result['patient_id']
        
        # Update the payment status based on verification decision
        if is_verified:
            # If payment is verified, set is_verified flag to TRUE
            cur.execute("""
                UPDATE payment_requests
                SET is_verified = TRUE
                WHERE id = %s
            """, [payment_id])
        else:
            # If payment is rejected, revert status to pending and clear payment details
            cur.execute("""
                UPDATE payment_requests
                SET status = 'pending', 
                    payment_date = NULL,
                    transaction_id = NULL,
                    payment_proof = NULL,
                    is_verified = FALSE
                WHERE id = %s
            """, [payment_id])
        
        mysql.connection.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Payment verification updated',
            'patient_id': patient_id  # Return patient_id for UI updates
        })
        
    except Exception as e:
        app.logger.error(f"Error verifying payment: {str(e)}")
        return jsonify({'success': False, 'error': f'Error verifying payment: {str(e)}'}), 500

@app.route('/api/appointment/<int:appointment_id>', methods=['GET'])
@login_required
def get_appointment_details(appointment_id):
    try:
        cur = mysql.connection.cursor()
        
        user_id = session.get('id')
        # Get appointment details if the user is authorized (patient or doctor)
        cur.execute("""
            SELECT a.* FROM appointments a
            WHERE a.id = %s AND (a.patient_id = %s OR a.doctor_id = %s)
        """, [appointment_id, user_id, user_id])
        
        appointment = cur.fetchone()
        
        if not appointment:
            return jsonify({'success': False, 'error': 'Appointment not found or unauthorized'}), 404
        
        # Format dates for JSON serialization
        serializable_appointment = {}
        for key, value in appointment.items():
            if isinstance(value, timedelta):
                # Convert TIME to string in format HH:MM:SS
                serializable_appointment[key] = str(value)
            elif isinstance(value, (datetime, date)):
                # Convert datetime to ISO format string
                serializable_appointment[key] = value.isoformat()
            else:
                serializable_appointment[key] = value
        
        return jsonify({'success': True, 'appointment': serializable_appointment})
        
    except Exception as e:
        app.logger.error(f"Error getting appointment details: {str(e)}")
        return jsonify({'success': False, 'error': f'Error getting appointment details: {str(e)}'}), 500

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """
    Serve uploaded files using absolute path to access files across different directories
    """
    # Define the absolute path to your uploads folder
    absolute_upload_path = 'C:\\healthcareManagement\\static\\uploads\\payment_proofs'
    
    # Log the path we're checking and the requested filename
    app.logger.info(f"Looking for file: {filename} in {absolute_upload_path}")
    
    # Check if file exists in the absolute path
    file_path = os.path.join(absolute_upload_path, filename)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        app.logger.info(f"Found file at: {file_path}")
        return send_from_directory(absolute_upload_path, filename)
    
    # If file not found
    app.logger.error(f"File not found: {filename}")
    return f"File not found: {filename}", 404

# Add a direct route specifically for files in the payment_proofs folder
@app.route('/payment_proofs/<path:filename>')
def payment_proof_direct(filename):
    """
    Direct route to payment proofs with absolute path
    """
    absolute_path = 'C:\\healthcareManagement\\static\\uploads\\payment_proofs'
    return send_from_directory(absolute_path, filename)

@app.route('/doctor_video_consultation')
@login_required
@verification_required
def doctor_video_consultation(): 
    doctor_id = session['id']
    
    try:
        # Get doctor information
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT d.*, u.email 
            FROM doctors d 
            JOIN users u ON d.id = u.id 
            WHERE d.id = %s
        """, [doctor_id])
        doctor = cur.fetchone()
        
        if not doctor:
            flash('Doctor profile not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Get current date and time
        current_date = datetime.now().date()
        current_time = datetime.now().time()
        
        # Debug logging
        app.logger.info(f"Current date: {current_date}, current time: {current_time}")
        
        # Get current and upcoming appointments for today with payment verification info
        cur.execute("""
            SELECT a.*, u.full_name as patient_name,
                   CASE 
                       WHEN a.appointment_date = %s AND a.appointment_time <= %s AND a.appointment_time >= DATE_SUB(%s, INTERVAL 30 MINUTE)
                       THEN TRUE 
                       ELSE FALSE 
                   END as is_current,
                   CASE
                       WHEN a.appointment_date < %s OR (a.appointment_date = %s AND a.appointment_time < DATE_SUB(%s, INTERVAL 30 MINUTE))
                       THEN TRUE
                       ELSE FALSE
                   END as is_expired,
                   IFNULL(pr.is_verified, FALSE) as is_payment_verified
            FROM appointments a
            JOIN users u ON a.patient_id = u.id
            LEFT JOIN payment_requests pr ON a.id = pr.appointment_id
            WHERE a.doctor_id = %s 
            AND a.appointment_date = %s
            AND a.status = 'scheduled'
            ORDER BY a.appointment_time ASC
        """, [current_date, current_time, current_time, current_date, current_date, current_time, doctor_id, current_date])
        current_appointments = cur.fetchall()
        
        # Debug logging
        app.logger.info(f"Found {len(current_appointments)} current appointments")
        
        # Convert time objects to formatted strings to avoid timedelta issues
        for appointment in current_appointments:
            # Debug each appointment
            app.logger.info(f"Processing appointment {appointment['id']}")
            
            if isinstance(appointment['appointment_time'], timedelta):
                # Convert timedelta to formatted string
                total_seconds = int(appointment['appointment_time'].total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                
                # Format time as HH:MM AM/PM
                period = "AM" if hours < 12 else "PM"
                if hours == 0:
                    hours = 12
                elif hours > 12:
                    hours -= 12
                
                appointment['formatted_time'] = f"{hours}:{minutes:02d} {period}"
            else:
                # If it's a datetime.time object
                appointment['formatted_time'] = appointment['appointment_time'].strftime('%I:%M %p')
            
            # Convert appointment_date to a formatted string for HTML data attribute
            if isinstance(appointment['appointment_date'], datetime):
                appointment['appointment_datetime_str'] = appointment['appointment_date'].strftime('%Y-%m-%d')
            else:
                # If it's a date object
                appointment['appointment_datetime_str'] = appointment['appointment_date'].strftime('%Y-%m-%d')
        
        # Get all appointments (past, current, and future) with payment verification info
        cur.execute("""
            SELECT a.*, u.full_name as patient_name,
                   CASE 
                       WHEN a.appointment_date = %s AND a.appointment_time <= %s AND a.appointment_time >= DATE_SUB(%s, INTERVAL 30 MINUTE)
                       THEN TRUE 
                       ELSE FALSE 
                   END as is_current,
                   CASE
                       WHEN a.appointment_date < %s OR (a.appointment_date = %s AND a.appointment_time < DATE_SUB(%s, INTERVAL 30 MINUTE))
                       THEN TRUE
                       ELSE FALSE
                   END as is_expired,
                   IFNULL(pr.is_verified, FALSE) as is_payment_verified
            FROM appointments a
            JOIN users u ON a.patient_id = u.id
            LEFT JOIN payment_requests pr ON a.id = pr.appointment_id
            WHERE a.doctor_id = %s
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
            LIMIT 20
        """, [current_date, current_time, current_time, current_date, current_date, current_time, doctor_id])
        all_appointments = cur.fetchall()
        
        # Convert time objects for all appointments too
        for appointment in all_appointments:
            if isinstance(appointment['appointment_time'], timedelta):
                # Convert timedelta to formatted string
                total_seconds = int(appointment['appointment_time'].total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                
                # Format time as HH:MM AM/PM
                period = "AM" if hours < 12 else "PM"
                if hours == 0:
                    hours = 12
                elif hours > 12:
                    hours -= 12
                
                appointment['formatted_time'] = f"{hours}:{minutes:02d} {period}"
            else:
                # If it's a datetime.time object
                appointment['formatted_time'] = appointment['appointment_time'].strftime('%I:%M %p')
            
            # Format appointment date
            if isinstance(appointment['appointment_date'], datetime):
                appointment['formatted_date'] = appointment['appointment_date'].strftime('%d %b, %Y')
                appointment['appointment_datetime_str'] = appointment['appointment_date'].strftime('%Y-%m-%d')
            else:
                # If it's already a date object
                appointment['formatted_date'] = appointment['appointment_date'].strftime('%d %b, %Y')
                appointment['appointment_datetime_str'] = appointment['appointment_date'].strftime('%Y-%m-%d')
            
            # Add check for joinable status
            current_datetime = datetime.now()
            
            # Convert appointment date and time to a datetime object
            if isinstance(appointment['appointment_date'], datetime):
                appointment_date = appointment['appointment_date'].date()
            else:
                appointment_date = appointment['appointment_date']
                
            if isinstance(appointment['appointment_time'], timedelta):
                hours = int(appointment['appointment_time'].total_seconds() // 3600)
                minutes = int((appointment['appointment_time'].total_seconds() % 3600) // 60)
                seconds = int(appointment['appointment_time'].total_seconds() % 60)
                appointment_time = time(hours, minutes, seconds)
            else:
                appointment_time = appointment['appointment_time']
                
            appointment_datetime = datetime.combine(appointment_date, appointment_time)
            
            # Appointment is joinable 5 minutes before until 30 minutes after
            join_start_time = appointment_datetime - timedelta(minutes=5)
            join_end_time = appointment_datetime + timedelta(minutes=30)
            
            appointment['is_joinable'] = join_start_time <= current_datetime <= join_end_time
            appointment['is_expired'] = current_datetime > join_end_time
        
        cur.close()
        
        app.logger.info("Successfully prepared data for doctor video consultation template")
        
        return render_template(
            'doctor_video_consultation.html',
            active_page='video_consultation',
            doctor=doctor,
            current_appointments=current_appointments,
            all_appointments=all_appointments
        )
        
    except Exception as e:
        app.logger.error(f"Error loading video consultation page: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('dashboard'))
       
from datetime import datetime, timedelta, time  # Make sure 'time' is imported
import secrets

@app.route('/video-room/<int:appointment_id>')
@login_required
def video_room(appointment_id):
    user_id = session.get('id')
    if not user_id:
        flash('You must be logged in to access this page', 'error')
        return redirect(url_for('login'))
    
    try:
        app.logger.info(f"Video room requested for appointment {appointment_id} by user {user_id}")
        
        # Get appointment details
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT a.*, 
                   u_patient.full_name as patient_name,
                   u_doctor.full_name as doctor_name,
                   a.session_token
            FROM appointments a
            JOIN users u_patient ON a.patient_id = u_patient.id
            JOIN users u_doctor ON a.doctor_id = u_doctor.id
            WHERE a.id = %s AND (a.doctor_id = %s OR a.patient_id = %s)
        """, [appointment_id, user_id, user_id])
        appointment = cur.fetchone()
        
        if not appointment:
            app.logger.warning(f"Appointment {appointment_id} not found or unauthorized for user {user_id}")
            flash('Appointment not found or you are not authorized to access it', 'error')
            return redirect(url_for('dashboard'))
        
        app.logger.info(f"Found appointment: {appointment['id']} with status {appointment['status']}")
        
        # Check if appointment is scheduled
        if appointment['status'] != 'scheduled':
            app.logger.warning(f"Appointment {appointment_id} is not currently scheduled (status: {appointment['status']})")
            flash('This appointment is not currently scheduled', 'error')
            return redirect(url_for('dashboard'))
        
        # Get current date and time for comparison
        current_datetime = datetime.now()
        current_date = current_datetime.date()
        current_time = current_datetime.time()
        
        app.logger.info(f"Current date/time: {current_datetime}")
        
        # Check if appointment is for today
        appointment_date = appointment['appointment_date']
        if isinstance(appointment_date, datetime):
            appointment_date = appointment_date.date()
        
        app.logger.info(f"Appointment date: {appointment_date}")
        
        if appointment_date != current_date:
            app.logger.warning(f"Appointment {appointment_id} is not for today (date: {appointment_date})")
            flash('This appointment is not scheduled for today', 'warning')
            return redirect(url_for('dashboard'))
        
        # Get appointment time as datetime.time object for comparison
        appointment_time = appointment['appointment_time']
        if isinstance(appointment_time, timedelta):
            total_seconds = int(appointment_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            appointment_time = time(hours, minutes)
        
        app.logger.info(f"Appointment time: {appointment_time}")
        
        # Calculate time difference
        appointment_datetime = datetime.combine(appointment_date, appointment_time)
        time_diff = (appointment_datetime - current_datetime).total_seconds() / 60
        
        app.logger.info(f"Time difference: {time_diff} minutes")
        
        # Only allow access if we're within 5 minutes before appointment time or after it starts
        if time_diff > 5:
            app.logger.warning(f"Too early to join: {time_diff} minutes before appointment")
            flash(f'You can join this consultation 5 minutes before the scheduled time', 'warning')
            return redirect(url_for('dashboard'))
        
        # Generate a room ID based on appointment ID (consistent for both doctor and patient)
        room_id = f"healthcare-appointment-{appointment_id}"
        
        # Check if user is doctor or patient and set name accordingly
        is_doctor = (appointment['doctor_id'] == user_id)
        user_name = appointment['doctor_name'] if is_doctor else appointment['patient_name']
        
        app.logger.info(f"User role: {'doctor' if is_doctor else 'patient'}, name: {user_name}")
        
        # Create or retrieve a session token
        if not appointment['session_token']:
            # Generate a unique session token
            session_token = secrets.token_urlsafe(16)
            
            # Store the token and update session_started time
            cur.execute("""
                UPDATE appointments 
                SET session_token = %s, session_started = %s
                WHERE id = %s
            """, [session_token, current_datetime, appointment_id])
            mysql.connection.commit()
            app.logger.info(f"Created new session token for appointment {appointment_id}")
        else:
            session_token = appointment['session_token']
            app.logger.info(f"Using existing session token for appointment {appointment_id}")
        
        # Format appointment time for display if needed
        if isinstance(appointment['appointment_time'], timedelta):
            total_seconds = int(appointment['appointment_time'].total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            period = "AM" if hours < 12 else "PM"
            if hours == 0:
                hours = 12
            elif hours > 12:
                hours -= 12
            
            appointment['formatted_time'] = f"{hours}:{minutes:02d} {period}"
        else:
            # If it's a datetime.time object
            appointment['formatted_time'] = appointment['appointment_time'].strftime('%I:%M %p')
        
        cur.close()
        
        app.logger.info(f"Rendering video room for appointment {appointment_id}")
        
        # Render the appropriate template
        template = 'video_room.html'
        return render_template(
            template,
            appointment=appointment,
            room_id=room_id,
            user_name=user_name,
            is_doctor=is_doctor,
            session_token=session_token,
            active_page='video_consultation'
        )
        
    except Exception as e:
        app.logger.error(f"Error loading video room: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('dashboard'))
       
@app.route('/api/store-chat', methods=['POST'])
@login_required
def store_chat_message():
    if not request.is_json:
        return jsonify({"error": "Invalid request format"}), 400
    
    data = request.json
    appointment_id = data.get('appointment_id')
    message = data.get('message')
    is_prescription = data.get('is_prescription', False)
    
    if not all([appointment_id, message]):
        return jsonify({"error": "Missing required fields"}), 400
    
    user_id = session.get('id')
    
    try:
        # Verify this user is part of this appointment
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT * FROM appointments 
            WHERE id = %s AND (doctor_id = %s OR patient_id = %s)
        """, [appointment_id, user_id, user_id])
        appointment = cur.fetchone()
        
        if not appointment:
            return jsonify({"error": "Unauthorized access to this appointment"}), 403
        
        # Store the chat message
        cur.execute("""
            INSERT INTO consultation_chats 
            (appointment_id, sender_id, message, is_prescription)
            VALUES (%s, %s, %s, %s)
        """, [appointment_id, user_id, message, is_prescription])
        mysql.connection.commit()
        
        return jsonify({"success": True, "message_id": cur.lastrowid}), 200
        
    except Exception as e:
        app.logger.error(f"Error storing chat message: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/end-session/<int:appointment_id>', methods=['POST'])
@login_required
def end_session(appointment_id):
    user_id = session.get('id')
    
    try:
        # Verify this user is part of this appointment
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT * FROM appointments 
            WHERE id = %s AND (doctor_id = %s OR patient_id = %s)
        """, [appointment_id, user_id, user_id])
        appointment = cur.fetchone()
        
        if not appointment:
            return jsonify({"error": "Unauthorized access to this appointment"}), 403
        
        # Update the appointment to mark session as ended
        cur.execute("""
            UPDATE appointments 
            SET session_ended = %s, status = 'completed'
            WHERE id = %s
        """, [datetime.now(), appointment_id])
        mysql.connection.commit()
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        app.logger.error(f"Error ending session: {str(e)}")
        return jsonify({"error": str(e)}), 500
                   
@app.route('/analytics')
@login_required
@verification_required
def analytics():
    cur = None
    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Get doctor details
        cur.execute("SELECT * FROM doctors WHERE id = %s", [session['id']])
        doctor = cur.fetchone()
        
        # Get total appointments count
        cur.execute("""
            SELECT 
                COUNT(*) as total_appointments,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_appointments,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_appointments,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_appointments,
                COUNT(DISTINCT patient_id) as total_patients
            FROM appointments 
            WHERE doctor_id = %s
        """, [session['id']])
        stats = cur.fetchone()
        
        # Get appointments by month
        cur.execute("""
            SELECT 
                DATE_FORMAT(appointment_date, '%Y-%m') as month,
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled
            FROM appointments
            WHERE doctor_id = %s 
            AND appointment_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            GROUP BY month
            ORDER BY month DESC
        """, [session['id']])
        monthly_stats = cur.fetchall()
        
        # Get appointments by day of week
        cur.execute("""
            SELECT 
                DAYNAME(appointment_date) as day_of_week,
                COUNT(*) as count
            FROM appointments
            WHERE doctor_id = %s 
            AND appointment_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
            GROUP BY day_of_week
            ORDER BY FIELD(day_of_week, 
                'Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                'Friday', 'Saturday', 'Sunday')
        """, [session['id']])
        daily_stats = cur.fetchall()
        
        # Get patient demographics
        cur.execute("""
            SELECT 
                COUNT(DISTINCT a.patient_id) as patient_count,
                COUNT(DISTINCT CASE WHEN a.status = 'completed' THEN a.patient_id END) as returning_patients
            FROM appointments a
            WHERE a.doctor_id = %s
        """, [session['id']])
        patient_stats = cur.fetchone()
        
        return render_template('analytics.html',
                             doctor=doctor,
                             stats=stats,
                             monthly_stats=monthly_stats,
                             daily_stats=daily_stats,
                             patient_stats=patient_stats)
                             
    except Exception as e:
        print(f"Error in analytics route: {str(e)}")
        flash('Failed to load analytics data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
        
    finally:
        if cur:
            cur.close()

if __name__ == '__main__':
    app.run(debug=True, port=5001)