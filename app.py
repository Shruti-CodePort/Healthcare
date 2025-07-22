# app.py
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session, json, send_from_directory,abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from validators import Validator
import os
from werkzeug.utils import secure_filename
from functools import wraps
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta, time, date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_utils import generate_reset_token, verify_reset_token, send_reset_email
import calendar
import secrets

app = Flask(__name__)
app.secret_key = 'Shruti'

mysql = MySQL(app)
# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'healthcare'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'devg18046@gmail.com'
app.config['MAIL_PASSWORD'] = '16 digit password'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

# Token Configuration
app.config['SECURITY_PASSWORD_SALT'] = 'Shruti_Mishra'

# Add these configurations for file uploads
UPLOAD_FOLDER = 'static/uploads/surgeries'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILES = 1

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

UPLOAD_FOLDER_PROOF = 'static/uploads/payment_proofs'
MAX_FILES = 1

app.config['UPLOAD_FOLDER_PROOF'] = UPLOAD_FOLDER_PROOF
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# User class for Flask-Login
class User:
    def __init__(self, id, full_name, email):
        self.id = id
        self.full_name = full_name
        self.email = email
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)

# Login manager loader function
@login_manager.user_loader
def load_user(user_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(user_data['id'], user_data['full_name'], user_data['email'])
        return None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None
    finally:
        if 'cursor' in locals():
            mysql.connection.commit()
            cursor.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_started')
def get_started():
    return render_template('get_started.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            # Get form data
            full_name = request.form.get('fullName')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirmPassword')
            
            # Validate all fields are present
            if not all([full_name, email, password, confirm_password]):
                flash('All fields are required', 'error')
                return render_template('sign_up.html')
            
            # Perform validations
            validator = Validator()
            
            # Validate email
            email_errors = validator.validate_email(email)
            if email_errors:
                for error in email_errors:
                    flash(error, 'error')
                return render_template('sign_up.html')
            
            # Validate password
            password_errors = validator.validate_password(password, confirm_password)
            if password_errors:
                for error in password_errors:
                    flash(error, 'error')
                return render_template('sign_up.html')
            
            # Validate name
            name_errors = validator.validate_name(full_name)
            if name_errors:
                for error in name_errors:
                    flash(error, 'error')
                return render_template('sign_up.html')
            
            cursor = mysql.connection.cursor()
            
            # Check if email exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('Email already registered', 'error')
                return render_template('sign_up.html')
            
            # Create new user
            password_hash = generate_password_hash(password)
            insert_query = """
                INSERT INTO users (full_name, email, password_hash)
                VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (full_name, email, password_hash))
            mysql.connection.commit()
            cursor.close()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        except mysql.connector.Error as err:
            print(f"Database Error: {err}")
            flash('An error occurred during registration', 'error')
            return render_template('sign_up.html')
            
        finally:
            if 'cursor' in locals():
                mysql.connection.commit()
                cursor.close()
    
    return render_template('sign_up.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        validator = Validator()
        email_errors = validator.validate_email(email)
        if email_errors:
            for error in email_errors:
                flash(error, 'error')
            return render_template('forgot_password.html')
        
        cursor = mysql.connection.cursor()
        
        try:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user:
                token = generate_reset_token(email)
                reset_url = url_for(
                    'reset_password',
                    token=token,
                    _external=True
                )
                
                if send_reset_email(email, reset_url):
                    flash('Password reset instructions have been sent to your email.', 'success')
                else:
                    flash('Error sending email. Please try again later.', 'error')
            else:
                flash('If an account exists with this email, you will receive password reset instructions.', 'info')
                
        except Exception as e:
            print(f"Error in forgot password: {str(e)}")
            flash('An error occurred. Please try again later.', 'error')
        finally:
            mysql.connection.commit()
            cursor.close()
            
        return redirect(url_for('login'))
        
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = verify_reset_token(token)
        if not email:
            flash('The password reset link is invalid or has expired.', 'error')
            app.logger.warning(f"Invalid or expired password reset token attempted")
            return redirect(url_for('forgot_password'))
        
        if request.method == 'POST':
            password = request.form.get('password')
            confirm_password = request.form.get('confirmPassword')
            
            if not password or not confirm_password:
                flash('Please fill in all password fields', 'error')
                return render_template('reset_password.html')
            
            validator = Validator()
            password_errors = validator.validate_password(password, confirm_password)
            if password_errors:
                for error in password_errors:
                    flash(error, 'error')
                return render_template('reset_password.html')                
            
            cursor = mysql.connection.cursor()
            
            try:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                
                if not user:
                    flash('Account not found', 'error')
                    return redirect(url_for('forgot_password'))
                
                password_hash = generate_password_hash(password)
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE email = %s",
                    (password_hash, email)
                )
                mysql.connection.commit()
                
                flash('Your password has been updated! Please login.', 'success')
                return redirect(url_for('login'))
                
            finally:
                mysql.connection.commit()
                cursor.close()
        
        return render_template('reset_password.html')
        
    except Exception as e:
        app.logger.error(f"Unexpected error in reset password route: {str(e)}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('forgot_password'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not email or not password:
                flash('Please provide both email and password', 'error')
                return render_template('login.html')

            cursor = mysql.connection.cursor()
            
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user_data = cursor.fetchone()
            
            if user_data and check_password_hash(user_data['password_hash'], password):
                user = User(user_data['id'], user_data['full_name'], user_data['email'])
                login_user(user)
                
                # Check if user has health details
                cursor.execute("SELECT id FROM health_details WHERE user_id = %s", (user_data['id'],))
                has_health_details = cursor.fetchone()
                
                if not has_health_details:
                    return redirect(url_for('personal_health_details'))
                
                session['name'] = user_data['full_name']
                session['email'] = user_data['email']
                flash('Login successful!', 'success')
                
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password', 'error')
                return render_template('login.html')
                
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return render_template('login.html')
            
        finally:
            if 'cursor' in locals():
                mysql.connection.commit()
                cursor.close()
            
    return render_template('login.html')

@app.route('/personal-health-details', methods=['GET', 'POST'])
@login_required
def personal_health_details():
    if request.method == 'POST':
        try:
            user_id = current_user.id
            patient_name = request.form.get('patientName')
            dob = request.form.get('dob')
            contact_no = request.form.get('contactNo')
            
            # Get values based on radio button selections
            has_previous_illnesses = request.form.get('hasPreviousIllnesses') == 'yes'
            has_current_medications = request.form.get('hasCurrentMedications') == 'yes'
            has_known_allergies = request.form.get('hasKnownAllergies') == 'yes'
            has_previous_surgeries = request.form.get('hasPreviousSurgeries') == 'yes'
            
            # Get the text values
            previous_illnesses = request.form.get('previousIllness') if has_previous_illnesses else None
            current_medications = request.form.get('currentMedications') if has_current_medications else None
            known_allergies = request.form.get('knownAllergies') if has_known_allergies else None
            previous_surgeries = request.form.get('previousSurgeries') if has_previous_surgeries else None
            
            document_path = None

            cursor = mysql.connection.cursor()

            if dob:
                try:
                    dob = datetime.strptime(dob, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format', 'error')
                    return redirect(url_for('personal_health_details'))
            
            # Check for existing record to get current document path
            cursor.execute("SELECT id, document_path FROM health_details WHERE user_id = %s", (user_id,))
            existing_record = cursor.fetchone()
            current_document_path = existing_record['document_path'] if existing_record else None
            
            # Handle file uploads
            if has_previous_surgeries:
                file = request.files.get('surgeryFiles')
                
                # If a new file is uploaded
                if file and file.filename != '':
                    if not allowed_file(file.filename):
                        flash('Only PDF files are allowed', 'error')
                        return redirect(request.url)
                    
                    # Save new file
                    filename = secure_filename(file.filename)
                    absolute_path = os.path.join(os.path.abspath(app.config['UPLOAD_FOLDER']), f"{user_id}_{filename}")
                    file.save(absolute_path)
                    document_path = absolute_path
                else:
                    # Keep existing document if no new file uploaded
                    document_path = current_document_path
            else:
                # If "No" selected for surgeries, set document_path to None
                document_path = None
            
            # Update health details
            if existing_record:
                cursor.execute("""
                    UPDATE health_details 
                    SET patient_name = %s, date_of_birth = %s, contact_number = %s,
                        previous_illnesses = %s, current_medications = %s,
                        known_allergies = %s, previous_surgeries = %s,
                        document_path = %s
                    WHERE user_id = %s
                """, (patient_name, dob, contact_no, previous_illnesses, current_medications,
                      known_allergies, previous_surgeries, document_path, user_id))
            else:
                cursor.execute("""
                    INSERT INTO health_details 
                    (user_id, patient_name, date_of_birth, contact_number, 
                     previous_illnesses, current_medications, known_allergies, previous_surgeries, document_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, patient_name, dob, contact_no, previous_illnesses,
                      current_medications, known_allergies, previous_surgeries, document_path))

            mysql.connection.commit()
            flash('Health details updated successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            app.logger.error(f"Error updating health details: {str(e)}")
            flash('An error occurred while updating health details', 'error')
            return redirect(url_for('personal_health_details'))

        finally:
            if 'cursor' in locals():
                mysql.connection.commit()
                cursor.close()
    # GET request - fetch existing data
    try:
        cursor = mysql.connection.cursor()
        
        # Fetch health details
        cursor.execute("SELECT * FROM health_details WHERE user_id = %s", (current_user.id,))
        health_details = cursor.fetchone()
        
        # Prepare document information
        uploaded_documents = []
        if health_details and health_details['document_path'] and os.path.exists(health_details['document_path']):
            file_name = os.path.basename(health_details['document_path'])
            uploaded_documents.append({
                'file_name': file_name,
                'uploaded_at': health_details['created_at']
            })
        
        return render_template('personal_health_details.html', 
                            health_details=health_details,
                            uploaded_documents=uploaded_documents)

    except Exception as e:
        app.logger.error(f"Error fetching health details: {str(e)}")
        flash('An error occurred while loading health details', 'error')
        return redirect(url_for('dashboard'))

    finally:
        if 'cursor' in locals():
            mysql.connection.commit()
            cursor.close()

@app.route('/serve-document/<path:file_path>')
@login_required
def serve_document(file_path):
    # Security check - make sure the file belongs to the current user
    if str(current_user.id) not in file_path:
        abort(403)  # Forbidden
    
    # Ensure the path is safe
    safe_path = os.path.normpath(file_path)
    filename = os.path.basename(safe_path)
    
    directory = os.path.dirname(safe_path)
    return send_from_directory(directory, filename)     

@app.route('/save_health_metrics', methods=['POST'])
@login_required
def save_health_metrics():
    try:
        user_id = current_user.id
        
        # Get form data
        bp_monitored = request.form.get('bp-monitor') == 'yes'
        systolic = request.form.get('systolic') if bp_monitored else None
        diastolic = request.form.get('diastolic') if bp_monitored else None
        
        sugar_monitored = request.form.get('sugar-monitor') == 'yes'
        blood_sugar = request.form.get('blood-sugar') if sugar_monitored else None
        
        temp_monitored = request.form.get('temp-monitor') == 'yes'
        body_temp = request.form.get('body-temp') if temp_monitored else None
        
        glucose_monitored = request.form.get('glucose-monitor') == 'yes'
        glucose_level = request.form.get('glucose-level') if glucose_monitored else None

        cursor = mysql.connection.cursor()

        # Check if user already has health metrics
        cursor.execute("SELECT id FROM health_metrics WHERE user_id = %s", (user_id,))
        existing_record = cursor.fetchone()

        if existing_record:
            # Update existing record
            cursor.execute("""
                UPDATE health_metrics 
                SET bp_monitored = %s, systolic = %s, diastolic = %s,
                    sugar_monitored = %s, blood_sugar = %s,
                    temp_monitored = %s, body_temp = %s,
                    glucose_monitored = %s, glucose_level = %s
                WHERE user_id = %s
            """, (bp_monitored, systolic, diastolic, sugar_monitored, blood_sugar,
                  temp_monitored, body_temp, glucose_monitored, glucose_level, user_id))
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO health_metrics 
                (user_id, bp_monitored, systolic, diastolic, sugar_monitored, blood_sugar,
                 temp_monitored, body_temp, glucose_monitored, glucose_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, bp_monitored, systolic, diastolic, sugar_monitored, blood_sugar,
                  temp_monitored, body_temp, glucose_monitored, glucose_level))

        mysql.connection.commit()
        flash('Health metrics updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    except Exception as e:
        print(f"Error saving health metrics: {e}")
        flash('An error occurred while saving health metrics', 'error')
        return redirect(url_for('dashboard'))

    finally:
        if 'cursor' in locals():
            mysql.connection.commit()
            cursor.close()
                        
@app.route('/dashboard')
@login_required
def dashboard():
    try:
        user_id = current_user.id
        cursor = mysql.connection.cursor()
        
        # Fetch user and health data
        cursor.execute("""
            SELECT 
                u.id,
                u.full_name,
                u.email,
                h.patient_name,
                h.date_of_birth,
                h.contact_number,
                h.previous_illnesses,
                h.current_medications,
                h.known_allergies,
                h.previous_surgeries,
                h.document_path,
                h.created_at,
                hm.*
            FROM users u
            LEFT JOIN health_details h ON u.id = h.user_id
            LEFT JOIN health_metrics hm ON u.id = hm.user_id
            WHERE u.id = %s
        """, (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            logout_user()
            flash('User not found.', 'error')
            return redirect(url_for('login'))

        # Create patient ID with proper formatting
        patient_id = f"#{user_data['id']:05d}" if user_data['id'] else "N/A"
        
        # Create health_details dictionary
        health_details = {
            'patient_name': user_data.get('patient_name'),
            'date_of_birth': user_data.get('date_of_birth'),
            'contact_number': user_data.get('contact_number'),
            'previous_illnesses': user_data.get('previous_illnesses'),
            'current_medications': user_data.get('current_medications'),
            'known_allergies': user_data.get('known_allergies'),
            'previous_surgeries': user_data.get('previous_surgeries'),
            'document_path': user_data.get('document_path'),
            'created_at': user_data.get('created_at')
        }

        # Check for document existence and get filename
        document_name = None
        has_document = False
        if health_details.get('document_path') and os.path.exists(health_details['document_path']):
            document_name = os.path.basename(health_details['document_path'])
            has_document = True

        # Fetch surgery documents
        cursor.execute("""
            SELECT id, file_name, file_path, uploaded_at 
            FROM surgery_documents 
            WHERE user_id = %s 
            ORDER BY uploaded_at DESC
        """, (user_id,))
        surgery_documents = cursor.fetchall()
        
        # Fetch verified doctors
        cursor.execute("""
            SELECT id, name, specialty, qualification, experience_years, is_online
            FROM doctors
            WHERE is_verified = TRUE
            ORDER BY is_online DESC, name ASC
        """)
        verified_doctors = cursor.fetchall()
        
        return render_template('dashboard.html',
                             name=user_data.get('full_name', ''),
                             email=user_data.get('email', ''),
                             patient_id=patient_id,
                             health_details=health_details,
                             health_metrics=user_data,
                             surgery_documents=surgery_documents,
                             verified_doctors=verified_doctors,
                             has_document=has_document,
                             document_name=document_name)
                             
    except Exception as e:
        print(f"Dashboard error: {e}")
        flash('An error occurred while loading the dashboard', 'error')
        return redirect(url_for('login'))
        
    finally:
        if 'cursor' in locals():
            mysql.connection.commit()
            cursor.close()

@app.route('/api/doctor-schedule/<int:doctor_id>', methods=['GET'])
@login_required
def get_doctor_schedule(doctor_id):
    cur = None
    try:
        start_date = request.args.get('start_date')
        if start_date:
            # Handle ISO format date properly
            # Replace Z with +00:00 for proper parsing
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            start_date = start_date.date()
        else:
            start_date = date.today()
        
        end_date = start_date + timedelta(days=7)
        
        cur = mysql.connection.cursor()
        
        cur.execute("""
            SELECT is_verified, is_online 
            FROM doctors 
            WHERE id = %s
        """, [doctor_id])
        
        doctor = cur.fetchone()
        if not doctor or not doctor['is_verified']:
            flash('Doctor not found or not verified', 'error')
            return redirect(url_for('consultation'))
        
        if not doctor['is_online']:
            flash('Doctor is currently offline', 'error')
            return redirect(url_for('consultation'))

        # Fix: Escape the % characters by doubling them
        cur.execute("""
            SELECT 
                da.id,
                DATE_FORMAT(da.schedule_date, '%%Y-%%m-%%d') as schedule_date,
                TIME_FORMAT(da.start_time, '%%H:%%i') as start_time,
                TIME_FORMAT(da.end_time, '%%H:%%i') as end_time,
                da.slot_duration,
                CASE 
                    WHEN a.id IS NULL THEN TRUE
                    WHEN a.status = 'cancelled' THEN TRUE
                    ELSE FALSE
                END as is_available
            FROM doctor_availability da
            LEFT JOIN appointments a 
                ON da.id = a.availability_id
                AND a.status IN ('scheduled', 'pending_approval')
            WHERE da.doctor_id = %s
            AND da.schedule_date >= %s
            AND da.schedule_date < %s
            ORDER BY da.schedule_date, da.start_time
        """, [doctor_id, start_date, end_date])
        
        schedules = cur.fetchall()
        return jsonify(schedules)
        
    except Exception as e:
        # Better error handling - return JSON error for AJAX requests
        print(f"Error fetching doctor schedule: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
    finally:
        if cur:
            cur.close()

@app.route('/api/book-appointment', methods=['POST'])
@login_required
def book_appointment():
    cur = None
    try:
        data = request.get_json()
        print(f"Request data: {data}")
        
        if not data:
            print("Invalid request data - empty or not JSON")
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400
            
        availability_id = data.get('availability_id')
        doctor_id = data.get('doctor_id')
        print(f"availability_id: {availability_id}, doctor_id: {doctor_id}")
        
        if not availability_id or not doctor_id:
            print(f"Missing parameters - availability_id: {availability_id}, doctor_id: {doctor_id}")
            return jsonify({'success': False, 'message': 'Missing required parameters'}), 400
            
        cur = mysql.connection.cursor()
        
        # Check if the current user already has a pending or scheduled appointment for this slot
        cur.execute("""
            SELECT a.id
            FROM appointments a
            WHERE a.availability_id = %s 
            AND a.doctor_id = %s
            AND a.patient_id = %s
            AND a.status IN ('pending_approval', 'scheduled')
        """, (availability_id, doctor_id, current_user.id))
        
        existing_appointment = cur.fetchone()
        if existing_appointment:
            return jsonify({'success': False, 'message': 'You already have a pending or confirmed appointment for this slot'}), 400
            
        # Check if the slot exists and is available
        cur.execute("""
            SELECT 
                da.id, 
                da.schedule_date, 
                da.start_time,
                da.end_time,
                da.is_available
            FROM doctor_availability da
            WHERE da.id = %s AND da.doctor_id = %s AND da.is_available = TRUE
            FOR UPDATE
        """, (availability_id, doctor_id))
        
        slot = cur.fetchone()
        print(f"Query result for slot: {slot}")
        
        if not slot:
            return jsonify({'success': False, 'message': 'Unavailable slot'}), 400
            
        # Insert the appointment with 'pending_approval' status
        cur.execute("""
            INSERT INTO appointments 
            (availability_id, patient_id, doctor_id, appointment_date, appointment_time, status)
            VALUES (%s, %s, %s, %s, %s, 'pending_approval')
        """, (availability_id, current_user.id, doctor_id, slot['schedule_date'], slot['start_time']))
        
        # Update the availability of the slot
        cur.execute("""
            UPDATE doctor_availability 
            SET is_available = FALSE 
            WHERE id = %s
        """, (availability_id,))
        
        # Get the last inserted ID
        appointment_id = cur.lastrowid
        
        mysql.connection.commit()
        
        return jsonify({
            'success': True,
            'message': 'Appointment request sent successfully',
            'appointmentId': appointment_id
        })
        
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error booking appointment: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to book appointment'
        }), 500
        
    finally:
        if cur:
            cur.close()
            
@app.route('/api/appointment-status/<int:appointment_id>', methods=['GET'])
def get_appointment_status(appointment_id):
    if not current_user.is_authenticated:
        # For API requests, return a JSON response instead of redirecting
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        cur = mysql.connection.cursor()
        
        # Get the appointment status
        cur.execute("""
            SELECT status, availability_id FROM appointments 
            WHERE id = %s AND patient_id = %s
        """, [appointment_id, current_user.id])
        
        appointment = cur.fetchone()
        cur.close()
        
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
            
        return jsonify({
            'status': appointment['status'],
            'availability_id': appointment['availability_id']
        })
        
    except Exception as e:
        app.logger.error(f"Error getting appointment status: {str(e)}")
        return jsonify({'error': f'Error getting appointment status: {str(e)}'}), 500
        
@app.route('/api/pending-appointments/<int:doctor_id>', methods=['GET'])
@login_required
def get_pending_appointments(doctor_id):
    cur = None
    try:
        cur = mysql.connection.cursor()
        
        # Query to get the current user's pending appointments for this doctor
        cur.execute("""
            SELECT 
                a.id,
                a.doctor_id,
                a.availability_id,
                DATE_FORMAT(a.appointment_date, '%%Y-%%m-%%d') as appointment_date,
                TIME_FORMAT(a.appointment_time, '%%H:%%i') as appointment_time,
                TIME_FORMAT(ADDTIME(a.appointment_time, SEC_TO_TIME(da.slot_duration * 60)), '%%H:%%i') as end_time
            FROM appointments a
            JOIN doctor_availability da ON da.id = a.availability_id
            WHERE a.doctor_id = %s
            AND a.patient_id = %s
            AND a.status = 'pending_approval'
            ORDER BY a.appointment_date, a.appointment_time
        """, [doctor_id, current_user.id])
        
        appointments = cur.fetchall()
        return jsonify({'appointments': appointments})
        
    except Exception as e:
        print(f"Error fetching pending appointments: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
    finally:
        if cur:
            cur.close()

@app.route('/api/patient/payment-requests', methods=['GET'])
def get_patient_payment_requests():
    import datetime
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        cur = mysql.connection.cursor()
        
        # Get all payment requests for the current patient with appointment details
        cur.execute("""
            SELECT pr.id, pr.appointment_id, pr.amount, pr.upi_id, pr.status,
                    pr.request_date, pr.payment_date, pr.transaction_id, pr.payment_proof, pr.is_verified,
                    a.appointment_date, a.appointment_time, a.status as appointment_status,
                    d.name as doctor_name, d.specialty
            FROM payment_requests pr
            JOIN appointments a ON pr.appointment_id = a.id
            JOIN doctors d ON pr.doctor_id = d.id
            WHERE pr.patient_id = %s
            ORDER BY pr.request_date DESC
        """, [current_user.id])
        
        payment_requests_raw = cur.fetchall()
        cur.close()
        
        # Convert datetime and timedelta objects to strings for JSON serialization
        payment_requests = []
        for request in payment_requests_raw:
            serializable_request = {}
            for key, value in request.items():
                if isinstance(value, datetime.timedelta):
                    # Convert TIME to string in format HH:MM:SS
                    serializable_request[key] = str(value)
                elif isinstance(value, datetime.datetime):
                    # Convert datetime to ISO format string
                    serializable_request[key] = value.isoformat()
                elif isinstance(value, datetime.date):
                    # Convert date to ISO format string
                    serializable_request[key] = value.isoformat()
                else:
                    serializable_request[key] = value
            payment_requests.append(serializable_request)
        
        return jsonify({'payment_requests': payment_requests})
        
    except Exception as e:
        app.logger.error(f"Error getting payment requests: {str(e)}")
        return jsonify({'error': f'Error getting payment requests: {str(e)}'}), 500
    
@app.route('/api/patient/submit-payment', methods=['POST'])
def submit_payment():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Import necessary modules
    import os
    import time
    from datetime import datetime
    from werkzeug.utils import secure_filename
    
    payment_request_id = request.form.get('payment_request_id')
    transaction_id = request.form.get('transaction_id')
    
    # Check if payment proof file is included
    if 'payment_proof' not in request.files:
        return jsonify({'error': 'Payment proof is required'}), 400
        
    payment_proof = request.files['payment_proof']
    
    # If user submits without selecting file
    if payment_proof.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    # Check if it's an allowed file type
    if payment_proof and allowed_file(payment_proof.filename):
        try:
            # Create a secure filename
            filename = secure_filename(payment_proof.filename)
            # Add timestamp to avoid filename conflicts
            filename = f"{int(time.time())}_{filename}"
            # Save the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER_PROOF'], filename)
            payment_proof.save(file_path)
            
            # Get current timestamp for payment_date
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Update the payment request in the database
            cur = mysql.connection.cursor()
            cur.execute("""
                UPDATE payment_requests
                SET status = 'paid', 
                    payment_date = %s,
                    transaction_id = %s,
                    payment_proof = %s
                WHERE id = %s AND patient_id = %s
            """, [current_time, transaction_id, filename, payment_request_id, current_user.id])
            
            mysql.connection.commit()
            affected_rows = cur.rowcount
            cur.close()
            
            if affected_rows == 0:
                return jsonify({'error': 'Payment request not found or not authorized'}), 404
                
            return jsonify({'success': True, 'message': 'Payment submitted successfully'})
            
        except Exception as e:
            app.logger.error(f"Error submitting payment: {str(e)}")
            return jsonify({'error': f'Error submitting payment: {str(e)}'}), 500
    else:
        return jsonify({'error': 'File type not allowed'}), 400

# Helper function to check allowed file types
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/patient/billing')
@login_required
def patient_billing():
    # This just returns the main template
    # The content will be loaded via JavaScript
    return render_template('dashboard.html', active_tab='billing')         

@app.route('/patient_video_consultation')
@login_required
def patient_video_consultation():
    patient_id = current_user.id
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        # Get patient information
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT u.* 
            FROM users u 
            WHERE u.id = %s
        """, [patient_id])
        patient = cur.fetchone()
        
        if not patient:
            if is_ajax:
                return jsonify({"error": "Patient profile not found"}), 404
            flash('Patient profile not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Get current date
        current_date = datetime.now().date()
        current_time = datetime.now().time()
        
        # Get upcoming appointments with payment verification info
        cur.execute("""
            SELECT a.*, 
                   u.full_name as doctor_name,
                   IFNULL(pr.is_verified, FALSE) as is_payment_verified,
                   DATE_FORMAT(a.appointment_date, '%d %b, %Y') as formatted_date
            FROM appointments a
            JOIN users u ON a.doctor_id = u.id
            LEFT JOIN payment_requests pr ON a.id = pr.appointment_id
            WHERE a.patient_id = %s 
            AND a.status = 'scheduled'
            ORDER BY a.appointment_date ASC, a.appointment_time ASC
        """, [patient_id])
        upcoming_appointments = cur.fetchall()
        
        # Get past appointments with payment verification info
        cur.execute("""
            SELECT a.*, 
                   u.full_name as doctor_name,
                   IFNULL(pr.is_verified, FALSE) as is_payment_verified,
                   DATE_FORMAT(a.appointment_date, '%d %b, %Y') as formatted_date
            FROM appointments a
            JOIN users u ON a.doctor_id = u.id
            LEFT JOIN payment_requests pr ON a.id = pr.appointment_id
            WHERE a.patient_id = %s 
            AND (a.status = 'completed' OR a.status = 'cancelled')
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
            LIMIT 10
        """, [patient_id])
        past_appointments = cur.fetchall()
        
        # Process appointments to add formatted time and check if joinable
        for appointments in [upcoming_appointments, past_appointments]:
            for appointment in appointments:
                # Format time
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
                
                # Add appointment_datetime_str for comparisons
                if isinstance(appointment['appointment_date'], datetime):
                    appointment['appointment_datetime_str'] = appointment['appointment_date'].strftime('%Y-%m-%d')
                else:
                    # If it's a date object
                    appointment['appointment_datetime_str'] = appointment['appointment_date'].strftime('%Y-%m-%d')
                
                # Check if appointment is today
                is_today = False
                if isinstance(appointment['appointment_date'], datetime):
                    is_today = appointment['appointment_date'].date() == current_date
                else:
                    is_today = appointment['appointment_date'] == current_date
                
                # Check if appointment is joinable (within 5 minutes before start time)
                is_joinable = False
                if is_today and appointment['status'] == 'scheduled':
                    appointment_time = appointment['appointment_time']
                    if isinstance(appointment_time, timedelta):
                        total_seconds = int(appointment_time.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        appointment_time = time(hours, minutes)
                    
                    appointment_datetime = datetime.combine(current_date, appointment_time)
                    time_diff = (appointment_datetime - datetime.now()).total_seconds() / 60
                    is_joinable = time_diff <= 5 and time_diff > -30  # can join 5 minutes before and up to 30 minutes after
                
                appointment['is_joinable'] = is_joinable
        
        cur.close()
        
        # For AJAX requests, return JSON data
        if is_ajax:
            return jsonify({
                "upcoming_appointments": upcoming_appointments,
                "past_appointments": past_appointments
            })
        
        # For regular requests, render the template
        return render_template(
            'patient_video_consultation.html',
            active_page='video_consultation',
            patient=patient,
            upcoming_appointments=upcoming_appointments,
            past_appointments=past_appointments
        )
        
    except Exception as e:
        app.logger.error(f"Error loading patient video consultation page: {str(e)}")
        if is_ajax:
            return jsonify({"error": f"An error occurred: {str(e)}"}), 500
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('dashboard'))

# Add a new API endpoint to get appointments data
@app.route('/api/patient/appointments')
@login_required
def api_patient_appointments():
    patient_id = current_user.id
    
    try:
        # Get current date and time
        current_date = datetime.now().date()
        
        # Get all appointments with payment verification info
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT a.*, 
           u.full_name as doctor_name,
           IFNULL(pr.is_verified, FALSE) as is_payment_verified,
           DATE_FORMAT(a.appointment_date, '%d %b, %Y') as formatted_date
    FROM appointments a
    JOIN users u ON a.doctor_id = u.id
    LEFT JOIN payment_requests pr ON a.id = pr.appointment_id
    WHERE a.patient_id = %s 
    ORDER BY a.appointment_date ASC, a.appointment_time ASC
        """, [patient_id])
        
        column_names = [desc[0] for desc in cur.description]
        result = cur.fetchall()
        
        # Simple approach to convert to list of dicts
        appointments = []
        for row in result:
            # Create a dict with all string values to avoid formatting issues
            appointment = {}
            
            for i, col_name in enumerate(column_names):
                value = row[i]
                
                # Convert any complex types to strings
                if isinstance(value, bytes):
                    try:
                        appointment[col_name] = value.decode('utf-8')
                    except:
                        appointment[col_name] = str(value)
                elif isinstance(value, (datetime, date, time, timedelta)):
                    appointment[col_name] = str(value)
                else:
                    appointment[col_name] = value
            
            # Manually create formatted_time from the string time
            if 'appointment_time' in appointment:
                time_str = appointment['appointment_time']
                if isinstance(time_str, str) and ':' in time_str:
                    try:
                        # Parse the time string (e.g., "14:30:00")
                        parts = time_str.split(':')
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        
                        # Format as 12-hour time
                        period = "AM" if hours < 12 else "PM"
                        adjusted_hours = hours if hours <= 12 else hours - 12
                        if adjusted_hours == 0:
                            adjusted_hours = 12
                            
                        appointment['formatted_time'] = f"{adjusted_hours}:{minutes:02d} {period}"
                    except Exception as e:
                        # Fallback
                        appointment['formatted_time'] = time_str
                else:
                    appointment['formatted_time'] = str(time_str)
            
            # Add appointment_datetime_str for comparisons
            if 'appointment_date' in appointment:
                date_str = appointment['appointment_date']
                if isinstance(date_str, str):
                    appointment['appointment_datetime_str'] = date_str
                    
                    # Try to determine if today
                    try:
                        # Try to parse the date - handle common formats
                        if '-' in date_str:
                            date_obj = datetime.strptime(date_str.split(' ')[0], '%Y-%m-%d').date()
                        else:
                            # Try the formatted_date format
                            date_obj = datetime.strptime(appointment['formatted_date'], '%d %b, %Y').date()
                        
                        is_today = date_obj == current_date
                    except:
                        is_today = False
                else:
                    appointment['appointment_datetime_str'] = str(date_str)
                    is_today = False
            else:
                appointment['appointment_datetime_str'] = ''
                is_today = False
            
            # Determine if joinable (simplified)
            is_joinable = False
            if is_today and appointment.get('status') == 'scheduled':
                # Set to True if it's today and scheduled - JavaScript will handle exact timing
                is_joinable = True
            
            appointment['is_joinable'] = is_joinable
            
            appointments.append(appointment)
        
        cur.close()
        
        return jsonify(appointments)
        
    except Exception as e:
        app.logger.error(f"Error getting patient appointments: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
        
# Add an API endpoint to end a session
@app.route('/api/end-session/<int:appointment_id>', methods=['POST'])
@login_required
def api_end_session(appointment_id):
    user_id = session.get('id')
    
    try:
        # Update appointment status to completed
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE appointments 
            SET status = 'completed', 
                session_ended = %s
            WHERE id = %s AND (doctor_id = %s OR patient_id = %s)
        """, [datetime.now(), appointment_id, user_id, user_id])
        
        if cur.rowcount == 0:
            return jsonify({"error": "Appointment not found or not authorized"}), 404
            
        mysql.connection.commit()
        cur.close()
        
        return jsonify({"success": True, "message": "Session ended successfully"})
        
    except Exception as e:
        app.logger.error(f"Error ending session: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
          
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

def convert_timedelta_to_time(td):
    if not td:
        return None
    # Convert timedelta to time object
    seconds = td.total_seconds()
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return time(hours, minutes)

if __name__ == '__main__':
    app.run(debug=True,port=5002)