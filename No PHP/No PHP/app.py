# -*- coding: utf-8 -*-
from flask import (
    Flask, render_template, request, redirect, url_for, session, jsonify, flash
)
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta, date # Added date for dob validation
import traceback

# Initialize Flask App
app = Flask(__name__)

# --- Configuration ---
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_very_strong_development_secret_key_!@#$%^')
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'animal_rescue_db')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialize MySQL
mysql = MySQL(app)

# File Upload Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER_ADOPTIONS = os.path.join(BASE_DIR, 'static', 'uploads', 'adoptions')
UPLOAD_FOLDER_ANIMALS = os.path.join(BASE_DIR, 'static', 'uploads', 'animals')
UPLOAD_FOLDER_RESCUES = os.path.join(BASE_DIR, 'static', 'uploads', 'rescues')
RESCUE_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER_ADOPTIONS'] = UPLOAD_FOLDER_ADOPTIONS
app.config['UPLOAD_FOLDER_ANIMALS'] = UPLOAD_FOLDER_ANIMALS
app.config['UPLOAD_FOLDER_RESCUES'] = UPLOAD_FOLDER_RESCUES

# --- Helper Functions ---
def ensure_dir(directory):
    if not os.path.exists(directory):
        try: os.makedirs(directory); print(f"Created: {directory}")
        except OSError as e: print(f"ERROR creating {directory}: {e}"); return False
    return True

if not ensure_dir(UPLOAD_FOLDER_ADOPTIONS): print("WARNING: Adoptions upload folder issue.")
if not ensure_dir(UPLOAD_FOLDER_ANIMALS): print("WARNING: Animals upload folder issue.")
if not ensure_dir(UPLOAD_FOLDER_RESCUES): print("WARNING: Rescues upload folder issue.")

def allowed_file(filename, allowed_set=ALLOWED_EXTENSIONS):
    if not isinstance(filename, str) or not filename: return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

# --- Context Processor ---
@app.context_processor
def inject_current_year_and_now():
    return {'current_year': datetime.utcnow().year, 'now': datetime.utcnow()} # Pass 'now' for min date

# --- Routes ---

@app.route('/')
def index():
    logged_in = 'user_id' in session
    return render_template('index.html', logged_in=logged_in)

# --- Login, Register, Logout, Dashboard (Keep Existing) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET' and 'user_id' in session:
         flash('Already logged in.', 'info'); return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username'); password = request.form.get('password')
        if not username or not password:
             flash('Username/Password required.', 'danger'); return render_template('login.html', error='Required.')
        cur = None
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
        except Exception as e: print(f"DB Error: {e}"); flash('Login error.', 'danger'); return render_template('login.html')
        finally:
             if cur: cur.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']; session['username'] = user['username']
            flash(f'Welcome back, {user["username"]}!', 'success'); next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard'))
        else: flash('Invalid credentials.', 'danger'); return render_template('login.html', error='Invalid credentials.') # More specific error
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET' and 'user_id' in session:
         flash('Already logged in.', 'info'); return redirect(url_for('dashboard'))
    form_data = {} # Initialize form_data
    if request.method == 'POST':
        form_data = request.form # Store form data for repopulation
        username=request.form.get('username'); email=request.form.get('email')
        password=request.form.get('password'); confirm_password=request.form.get('confirm_password')
        error = None
        if not username: error = "Username is required."
        elif not email: error = "Email is required."
        elif not password: error = "Password is required."
        elif len(password) < 6: error = "Password must be at least 6 characters."
        elif password != confirm_password: error = "Passwords do not match."

        if not error: # Check if user exists only if basic validation passes
            cur = None
            try:
                cur = mysql.connection.cursor()
                cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
                if cur.fetchone():
                    error = "Username or email already registered."
            except Exception as e:
                print(f"DB Error checking user existence: {e}")
                error = "An error occurred during registration check. Please try again."
            finally:
                if cur: cur.close()

        if error:
            flash(error, 'danger');
            return render_template('register.html', error=error, form_data=form_data) # Pass form_data back

        # If no errors, proceed with registration
        cur = None
        try:
            cur = mysql.connection.cursor()
            hashed_password = generate_password_hash(password)
            cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed_password))
            mysql.connection.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            print(f"DB Error inserting user: {e}")
            flash('Registration failed due to a server error. Please try again.', 'danger')
            return render_template('register.html', error="Registration failed.", form_data=form_data) # Pass form_data back
        finally:
            if cur: cur.close()

    # For GET request
    return render_template('register.html', form_data=form_data)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to view the dashboard.', 'warning'); # More specific message
        return redirect(url_for('login', next=request.url))
    user_id = session['user_id']
    animals_posted_with_requests = []
    user_adoption_requests = []
    donation_history = []
    # Initialize error to None
    dashboard_error = None
    cur = None
    try:
        cur = mysql.connection.cursor()
        # Fetch animals posted by user
        sql_animals = "SELECT animal_id, name, type, status, date_posted, image_filename FROM animals WHERE user_id = %s ORDER BY date_posted DESC"
        cur.execute(sql_animals, (user_id,))
        animals_posted = cur.fetchall()

        # Fetch pending requests for each 'Available' animal
        for animal in animals_posted:
            animal['pending_requests'] = []
            if animal['status'] == 'Available':
                cur_req = None # Use separate cursor or ensure proper closing
                try:
                    cur_req = mysql.connection.cursor() # Open new cursor for nested query
                    sql_requests = "SELECT adoption_id, adopter_name, adopter_email, adoption_date, status FROM adoptions WHERE animal_id = %s AND status = %s ORDER BY adoption_date ASC"
                    cur_req.execute(sql_requests, (animal['animal_id'], 'Pending'))
                    animal['pending_requests'] = cur_req.fetchall()
                except Exception as req_e:
                    print(f"DB Error fetching requests for animal {animal['animal_id']}: {req_e}")
                    # Don't stop the whole dashboard, just log the error
                finally:
                    if cur_req: cur_req.close()
            animals_posted_with_requests.append(animal)

        # Fetch user's own adoption requests
        sql_user_adoptions = "SELECT adoption_id, animal_name, status, adoption_date FROM adoptions WHERE user_id = %s ORDER BY adoption_date DESC"
        cur.execute(sql_user_adoptions, (user_id,))
        user_adoption_requests = cur.fetchall()

        # Fetch user's donation history
        sql_donations = "SELECT donation_id, donation_type, amount, product_details, donation_date, status FROM donations WHERE user_id = %s ORDER BY donation_date DESC"
        cur.execute(sql_donations, (user_id,))
        donation_history = cur.fetchall()

    except Exception as e:
        print(f"!!! DB ERROR in /dashboard route: {e}"); traceback.print_exc()
        flash("Error loading dashboard data. Some information may be missing.", "danger")
        # Set error message to display on template
        dashboard_error = "Failed to load complete dashboard data due to a database error."
        # Return potentially incomplete data so the page partially renders
        # Ensure lists are initialized even if queries fail partially
        animals_posted_with_requests = animals_posted_with_requests if 'animals_posted_with_requests' in locals() else []
        user_adoption_requests = user_adoption_requests if 'user_adoption_requests' in locals() else []
        donation_history = donation_history if 'donation_history' in locals() else []
    finally:
        if cur: cur.close()

    # Pass the error variable to the template
    return render_template('dashboard.html',
                           username=session.get('username'),
                           animals_posted=animals_posted_with_requests,
                           adoption_requests=user_adoption_requests,
                           donation_history=donation_history,
                           error=dashboard_error) # Pass the error message


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been successfully logged out.', 'success') # Use success flash
    return redirect(url_for('index'))


# --- Other Routes (Adoption, Post Animal, Submit Adoption, Process Adoption, Donate, Rescue, Educational, Errors - Keep Existing) ---
@app.route('/adoption')
def adoption_page():
    animals = []; cur = None
    # Define 'now' context for templates that might need it (like vaccination)
    now = datetime.utcnow()
    try:
        cur = mysql.connection.cursor()
        sql = "SELECT animal_id, name, type, age, description, image_filename, status, date_posted FROM animals WHERE status = %s ORDER BY date_posted DESC"
        cur.execute(sql, ('Available',))
        animals = cur.fetchall()
        for animal in animals:
             animal['image_url'] = None
             if animal.get('image_filename'):
                 img_path_rel_to_static = os.path.join('uploads', 'animals', os.path.basename(animal['image_filename'])).replace("\\","/")
                 animal['image_url'] = url_for('static', filename=img_path_rel_to_static)
    except Exception as e: print(f"DB Error fetching animals: {e}"); flash("Could not load animals.", "danger")
    finally:
        if cur: cur.close()
    return render_template('adoption.html', animals=animals, now=now) # Pass 'now'

@app.route('/post_animal', methods=['POST'])
def post_animal():
    if 'user_id' not in session: return jsonify({'success': False, 'message': 'Please log in to post.'}), 401
    user_id=session['user_id']; name=request.form.get('animalName'); animal_type=request.form.get('animalType')
    age_str=request.form.get('animalAge'); description=request.form.get('animalDescription')
    image_file=request.files.get('animalImage'); image_filename_rel=None; image_path_full=None
    errors=[]; new_animal_id=None
    # Validation... (keep existing validation)
    if not name: errors.append('Name is required.')
    if not animal_type: errors.append('Type is required.')
    age=None
    if age_str:
        try: age=float(age_str);
        except ValueError: errors.append('Invalid age format.')
    else: errors.append('Age is required.')
    if not description: errors.append('Description is required.')
    # Image Handling... (keep existing)
    if image_file and image_file.filename!='':
        if not allowed_file(image_file.filename, IMAGE_EXTENSIONS): errors.append('Invalid image file type (PNG, JPG, GIF allowed).')
        else:
            if not errors:
                try:
                    timestamp=datetime.now().strftime('%Y%m%d%H%M%S%f'); upload_folder=app.config['UPLOAD_FOLDER_ANIMALS']
                    base_filename=secure_filename(image_file.filename); image_filename=f"animal_{user_id}_{timestamp}_{base_filename}"
                    image_path_full=os.path.join(upload_folder, image_filename)
                    if not ensure_dir(upload_folder): raise OSError("Could not create upload directory.")
                    image_file.save(image_path_full); image_filename_rel=os.path.join('uploads','animals',image_filename).replace("\\","/")
                except Exception as e: print(f"ERROR image save: {e}"); errors.append('Image upload failed.')
    # Process Errors... (keep existing)
    if errors:
        if image_path_full and os.path.exists(image_path_full):
             try: os.remove(image_path_full);
             except OSError as re: print(f"Error cleaning failed upload: {re}")
        return jsonify({'success': False, 'message': " ".join(errors)}), 400
    # DB Insert... (keep existing)
    cur = None
    try:
        cur = mysql.connection.cursor(); sql="INSERT INTO animals (user_id, name, type, age, description, image_filename, status) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (user_id, name, animal_type, age, description, image_filename_rel, 'Available'); cur.execute(sql, values)
        new_animal_id = cur.lastrowid; mysql.connection.commit()
        final_image_url = url_for('static', filename=image_filename_rel) if image_filename_rel else None
        return jsonify({'success': True, 'message': 'Animal posted successfully!', 'animal_id': new_animal_id, 'image_url': final_image_url})
    except Exception as e:
        mysql.connection.rollback(); print(f"!!! DB Error (Post Animal Insert): {e}")
        if image_path_full and os.path.exists(image_path_full):
            try: os.remove(image_path_full);
            except OSError as re: print(f"Error cleaning DB error upload: {re}")
        return jsonify({'success': False, 'message': f'Database error occurred.'}), 500
    finally:
        if cur: cur.close()

@app.route('/submit_adoption/<int:animal_id>', methods=['POST'])
def submit_adoption(animal_id):
    # ... (keep existing submit_adoption logic) ...
    if 'user_id' not in session: return jsonify({'success': False, 'message': 'Please log in.'}), 401
    photo_path_full=None; aadhaar_path_full=None; adopter_name=request.form.get('adopterName'); adopter_email=request.form.get('adopterEmail')
    photo_file=request.files.get('adopterPhoto'); aadhaar_file=request.files.get('adopterAadhaar'); user_id=session['user_id']
    errors=[]
    if not all([adopter_name, adopter_email, photo_file, aadhaar_file]): errors.append("All fields required.")
    if photo_file and not allowed_file(photo_file.filename): errors.append("Invalid photo file type.")
    if aadhaar_file and not allowed_file(aadhaar_file.filename): errors.append("Invalid ID proof file type.")
    animal_name=None; cur_check=None
    try:
        cur_check=mysql.connection.cursor(); cur_check.execute("SELECT name, status FROM animals WHERE animal_id = %s", (animal_id,))
        animal_data=cur_check.fetchone()
        if not animal_data: errors.append("Animal not found.")
        elif animal_data['status']!='Available': errors.append("This animal is no longer available.")
        else: animal_name=animal_data['name']
    except Exception as check_e: print(f"Error checking animal status: {check_e}"); errors.append("Could not verify animal status.")
    finally:
         if cur_check: cur_check.close()
    if errors: return jsonify({'success': False, 'message': " ".join(errors)}), 400
    try:
        timestamp=datetime.now().strftime('%Y%m%d%H%M%S%f'); upload_folder=app.config['UPLOAD_FOLDER_ADOPTIONS']
        if not ensure_dir(upload_folder): raise OSError("Adoption upload dir error.")
        photo_filename=secure_filename(f"photo_{user_id}_{timestamp}_{photo_file.filename}"); photo_path_full=os.path.join(upload_folder, photo_filename); photo_file.save(photo_path_full); photo_path_rel=os.path.join('uploads','adoptions',photo_filename).replace("\\","/")
        aadhaar_filename=secure_filename(f"aadhaar_{user_id}_{timestamp}_{aadhaar_file.filename}"); aadhaar_path_full=os.path.join(upload_folder, aadhaar_filename); aadhaar_file.save(aadhaar_path_full); aadhaar_path_rel=os.path.join('uploads','adoptions',aadhaar_filename).replace("\\","/")
        cur=None
        try:
            cur = mysql.connection.cursor(); sql="INSERT INTO adoptions (animal_id, animal_name, adopter_name, adopter_email, status, photo_path, aadhaar_path, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            values = (animal_id, animal_name, adopter_name, adopter_email, 'Pending', photo_path_rel, aadhaar_path_rel, user_id); cur.execute(sql, values); mysql.connection.commit()
            return jsonify({'success': True, 'message': 'Adoption request submitted successfully!'})
        except Exception as db_error: mysql.connection.rollback(); print(f"!!! DB Error inserting adoption: {db_error}"); raise db_error # Re-raise to trigger outer cleanup
        finally:
            if cur: cur.close()
    except Exception as e:
        print(f"!!! Error submitting adoption request: {e}")
        # Cleanup uploaded files if error occurred after saving them
        if photo_path_full and os.path.exists(photo_path_full):
            try: os.remove(photo_path_full); print(f"DEBUG: Cleaned up photo {photo_path_full}")
            except OSError as re: print(f"Error removing photo file {photo_path_full}: {re}")
        if aadhaar_path_full and os.path.exists(aadhaar_path_full):
            try: os.remove(aadhaar_path_full); print(f"DEBUG: Cleaned up ID proof {aadhaar_path_full}")
            except OSError as re: print(f"Error removing ID proof file {aadhaar_path_full}: {re}")
        return jsonify({'success': False, 'message': f'An internal server error occurred.'}), 500


@app.route('/process_adoption', methods=['POST'])
def process_adoption_request():
    # ... (keep existing process_adoption_request logic) ...
    if 'user_id' not in session: return jsonify({'success': False, 'message': 'Authentication required.'}), 401
    poster_user_id=session['user_id']; adoption_id=request.form.get('adoption_id', type=int); action=request.form.get('action')
    if not adoption_id or action not in ['accept', 'reject']: return jsonify({'success': False, 'message': 'Invalid data provided.'}), 400
    cur=None; animal_id=None
    try:
        cur=mysql.connection.cursor()
        sql_get_info = "SELECT a.animal_id, an.user_id AS animal_owner_id FROM adoptions a JOIN animals an ON a.animal_id = an.animal_id WHERE a.adoption_id = %s"
        cur.execute(sql_get_info, (adoption_id,))
        info=cur.fetchone()
        if not info: return jsonify({'success': False, 'message': 'Adoption request not found.'}), 404
        animal_id=info['animal_id']; animal_owner_id=info['animal_owner_id']
        if animal_owner_id != poster_user_id: return jsonify({'success': False, 'message': 'You are not authorized to process this request.'}), 403
        # Check if animal is still available before accepting
        cur.execute("SELECT status FROM animals WHERE animal_id = %s", (animal_id,))
        animal_status = cur.fetchone()
        if action=='accept' and animal_status and animal_status['status'] != 'Available':
             return jsonify({'success': False, 'message': 'Cannot accept, animal is no longer available.'}), 409 # Conflict

        if action=='accept':
            cur.execute("UPDATE adoptions SET status = 'Accepted' WHERE adoption_id = %s", (adoption_id,))
            cur.execute("UPDATE animals SET status = 'Adopted' WHERE animal_id = %s", (animal_id,))
            # Mark other pending requests for the same animal as unavailable
            cur.execute("UPDATE adoptions SET status = 'Unavailable' WHERE animal_id = %s AND status = 'Pending' AND adoption_id != %s", (animal_id, adoption_id))
            mysql.connection.commit();
            return jsonify({'success': True, 'message': 'Adoption accepted!'})
        elif action=='reject':
            cur.execute("UPDATE adoptions SET status = 'Rejected' WHERE adoption_id = %s", (adoption_id,))
            mysql.connection.commit();
            return jsonify({'success': True, 'message': 'Adoption rejected.'})
    except Exception as e: mysql.connection.rollback(); print(f"!!! DB Error process adoption: {e}"); traceback.print_exc(); return jsonify({'success': False,'message': f'Database error occurred processing request.'}), 500
    finally:
        if cur: cur.close()


@app.route('/vaccination', methods=['GET', 'POST'])
def vaccination_page():
    form_data = None # Initialize
    if request.method == 'POST':
        form_data = request.form # Capture form data
        owner_name = form_data.get('owner_name')
        pet_name = form_data.get('pet_name')
        pet_type = form_data.get('pet_type')
        appointment_date_str = form_data.get('appointment_date')
        appointment_time = form_data.get('appointment_time')
        errors = []

        # --- Basic Validation ---
        if not owner_name: errors.append("Owner name is required.")
        if not pet_name: errors.append("Pet name is required.")
        if not pet_type: errors.append("Pet type is required.")
        if not appointment_date_str: errors.append("Appointment date is required.")
        if not appointment_time: errors.append("Appointment time slot is required.")

        # Validate date format and ensure it's not in the past
        appointment_date = None
        if appointment_date_str:
            try:
                appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
                if appointment_date < date.today():
                    errors.append("Appointment date cannot be in the past.")
            except ValueError:
                errors.append("Invalid date format. Please use YYYY-MM-DD.")

        if errors:
            for error in errors: flash(error, 'danger')
            # Pass form_data back to repopulate
            return render_template('vaccination.html', form_data=form_data, page_title="Schedule Vaccination")
        # --- End Validation ---

        cur = None
        try:
            cur = mysql.connection.cursor()
            sql = "INSERT INTO vaccinations (owner_name, pet_name, pet_type, appointment_date, appointment_time, status) VALUES (%s, %s, %s, %s, %s, %s)"
            values = (owner_name, pet_name, pet_type, appointment_date, appointment_time, 'Pending')
            cur.execute(sql, values)
            mysql.connection.commit()
            flash(f"Appointment requested for {pet_name} on {appointment_date_str} ({appointment_time}). We will contact you to confirm.", 'success')
            return redirect(url_for('vaccination_page')) # Redirect to clear form
        except Exception as e:
            mysql.connection.rollback()
            print(f"!!! DB Error (Vaccination Insert): {e}"); traceback.print_exc()
            flash("There was an error booking the appointment. Please try again.", 'danger')
            # Pass form_data back on DB error too
            return render_template('vaccination.html', form_data=form_data, page_title="Schedule Vaccination")
        finally:
            if cur: cur.close()

    # For GET request
    return render_template('vaccination.html', form_data=None, page_title="Schedule Vaccination") # Pass None initially


@app.route('/donate', methods=['GET', 'POST'])
def donate_page():
    form_data = {} # Initialize
    if request.method == 'POST':
        form_data = request.form # Capture data
        # --- Basic Validation ---
        donor_name = form_data.get('donor_name')
        donor_email = form_data.get('donor_email')
        donation_type = form_data.get('donation_type')
        amount = form_data.get('amount')
        product_details = form_data.get('product_details')
        payment_method = form_data.get('payment_method') # Only relevant for money

        errors = []
        if not donor_name: errors.append("Your name is required.")
        if not donor_email: errors.append("Your email is required.")
        if not donation_type: errors.append("Please select a donation type.")

        amount_float = None
        if donation_type == 'Money':
            if not amount: errors.append("Amount is required for monetary donations.")
            else:
                try:
                    amount_float = float(amount)
                    if amount_float <= 0: errors.append("Donation amount must be positive.")
                except ValueError: errors.append("Invalid amount format.")
            if not payment_method: errors.append("Payment method is required for monetary donations.")
        elif donation_type == 'Products':
            if not product_details: errors.append("Product details are required for product donations.")

        if errors:
            for error in errors: flash(error, 'danger')
            return render_template('donate.html', form_data=form_data, page_title="Make a Donation")
        # --- End Validation ---

        # --- Database Insertion ---
        cur = None
        try:
            cur = mysql.connection.cursor()
            sql = """
                INSERT INTO donations (user_id, donor_name, donor_email, donor_phone,
                                     donation_type, amount, payment_method, product_details, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Get user_id if logged in, otherwise None
            user_id = session.get('user_id')
            donor_phone = form_data.get('donor_phone')

            # Prepare values, using None for fields not applicable to the donation type
            values = (
                user_id,
                donor_name,
                donor_email,
                donor_phone if donor_phone else None,
                donation_type,
                amount_float if donation_type == 'Money' else None,
                payment_method if donation_type == 'Money' else None,
                product_details if donation_type == 'Products' else None,
                'Completed' if donation_type == 'Money' else 'Received' # Example statuses
            )
            cur.execute(sql, values)
            mysql.connection.commit()
            flash('Thank you for your generous donation!', 'success')
            return redirect(url_for('donate_page')) # Redirect after successful submission
        except Exception as e:
            mysql.connection.rollback()
            print(f"!!! DB Error (Donation Insert): {e}"); traceback.print_exc()
            flash("We encountered an error recording your donation. Please try again.", 'danger')
            return render_template('donate.html', form_data=form_data, page_title="Make a Donation")
        finally:
            if cur: cur.close()
        # --- End Database Insertion ---

    # For GET request
    return render_template('donate.html', form_data=form_data, page_title="Make a Donation")


@app.route('/rescue', methods=['GET', 'POST'])
def rescue_page():
    form_data = None # Initialize
    if request.method == 'POST':
        form_data = request.form # Capture data
        reporter_user_id = session.get('user_id')
        animal_type_select = form_data.get('animalType')
        other_animal_type = form_data.get('otherAnimalType')
        location = form_data.get('location')
        condition_details = form_data.get('condition_details') # Get optional field
        image_file = request.files.get('animalImage')
        image_filename_rel = None
        image_path_full = None

        # --- Validation ---
        final_animal_type = animal_type_select
        if animal_type_select == 'Other':
            if not other_animal_type:
                flash('Please specify the type of animal if selecting "Other".', 'danger')
                return render_template('rescue.html', form_data=form_data, page_title="Report Animal Sighting")
            final_animal_type = other_animal_type.strip()

        errors = []
        if not final_animal_type: errors.append("Animal type is required.")
        if not location: errors.append("Location is required.")
        if not image_file or image_file.filename == '': errors.append("An image upload is required.")
        elif not allowed_file(image_file.filename, RESCUE_ALLOWED_EXTENSIONS):
             errors.append("Invalid image file type (jpg, png, gif allowed).")

        if errors:
            for error in errors: flash(error, 'danger')
            return render_template('rescue.html', form_data=form_data, page_title="Report Animal Sighting")
        # --- End Validation ---

        # --- Image Saving ---
        try:
            timestamp=datetime.now().strftime('%Y%m%d%H%M%S%f'); upload_folder=app.config['UPLOAD_FOLDER_RESCUES']
            base_filename=secure_filename(image_file.filename); user_prefix=f"{reporter_user_id}_" if reporter_user_id else "anon_"
            image_filename=f"rescue_{user_prefix}{timestamp}_{base_filename}"; image_path_full=os.path.join(upload_folder, image_filename)
            if not ensure_dir(upload_folder): raise OSError("Rescue upload directory error.")
            image_file.save(image_path_full); image_filename_rel=os.path.join('uploads','rescues',image_filename).replace("\\","/")
        except Exception as e:
             print(f"!!! ERROR saving rescue image: {e}"); traceback.print_exc(); flash('Image upload failed.', 'danger')
             return render_template('rescue.html', form_data=form_data, page_title="Report Animal Sighting")
        # --- End Image Saving ---

        # --- Database Insertion ---
        cur = None
        try:
            cur = mysql.connection.cursor()
            # Added condition_details to SQL insert
            sql = "INSERT INTO rescues (animal_type, location, condition_details, image_filename, reporter_user_id, status) VALUES (%s, %s, %s, %s, %s, %s)"
            values = (final_animal_type, location, condition_details if condition_details else None, image_filename_rel, reporter_user_id, 'Reported')
            cur.execute(sql, values)
            mysql.connection.commit()
            flash('Rescue report submitted successfully! Thank you for your help.', 'success')
            return redirect(url_for('rescue_page')) # Redirect after success
        except Exception as e:
            mysql.connection.rollback(); print(f"!!! DB Error (Rescue Insert): {e}"); traceback.print_exc()
            # Cleanup image if DB insert fails
            if image_path_full and os.path.exists(image_path_full):
                try: os.remove(image_path_full)
                except OSError as re: print(f"Error cleaning failed rescue image: {re}")
            flash("An error occurred while submitting the report. Please try again.", 'danger')
            return render_template('rescue.html', form_data=form_data, page_title="Report Animal Sighting")
        finally:
            if cur: cur.close()
        # --- End Database Insertion ---

    # For GET request
    return render_template('rescue.html', form_data=None, page_title="Report Animal Sighting")


# --- Volunteer Route (Handles GET and POST) ---
@app.route('/volunteer', methods=['GET', 'POST'])
def volunteer_page():
    form_data = {} # Initialize for GET requests
    if request.method == 'POST':
        form_data = request.form # Capture form data for validation/repopulation
        # --- Retrieve form data ---
        name = form_data.get('volunteer_name')
        email = form_data.get('volunteer_email')
        phone = form_data.get('volunteer_phone')
        address = form_data.get('volunteer_address')
        dob_str = form_data.get('volunteer_dob')
        availability = form_data.get('volunteer_availability')
        # Handle multiple interests if using checkboxes (adjust HTML if needed)
        interests = ", ".join(request.form.getlist('volunteer_interests')) # Example for checkboxes
        experience = form_data.get('volunteer_experience')
        why_volunteer = form_data.get('volunteer_why')

        # --- Basic Validation ---
        errors = []
        if not name: errors.append("Name is required.")
        if not email: errors.append("Email is required.")
        # Add more robust email validation if needed
        if not availability: errors.append("Availability information is required.")
        if not interests: errors.append("Please select at least one area of interest.")
        if not why_volunteer: errors.append("Please tell us why you'd like to volunteer.")

        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                # Optional: Age check (e.g., must be over 18)
                # today = date.today()
                # age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                # if age < 18: errors.append("Volunteers must typically be 18 or older.")
            except ValueError:
                errors.append("Invalid Date of Birth format.")
        # else: errors.append("Date of Birth is required.") # Optional based on your policy

        if errors:
            for error in errors: flash(error, 'danger')
            return render_template('volunteer.html', form_data=form_data, page_title="Volunteer With Us")
        # --- End Validation ---

        # --- Database Insertion ---
        cur = None
        try:
            cur = mysql.connection.cursor()
            sql = """
                INSERT INTO volunteers (name, email, phone, address, date_of_birth, availability,
                                      areas_of_interest, experience, why_volunteer, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                name, email, phone if phone else None, address if address else None,
                dob, availability, interests, experience if experience else None,
                why_volunteer, 'Pending' # Default status
            )
            cur.execute(sql, values)
            mysql.connection.commit()
            flash('Thank you for applying to volunteer! We will review your application and be in touch.', 'success')
            return redirect(url_for('volunteer_page')) # Redirect after success
        except mysql.connection.IntegrityError: # Catch duplicate email error
             mysql.connection.rollback()
             flash('An application with this email address already exists.', 'warning')
             return render_template('volunteer.html', form_data=form_data, page_title="Volunteer With Us")
        except Exception as e:
            mysql.connection.rollback()
            print(f"!!! DB Error (Volunteer Insert): {e}"); traceback.print_exc()
            flash("An error occurred submitting your application. Please try again.", 'danger')
            return render_template('volunteer.html', form_data=form_data, page_title="Volunteer With Us")
        finally:
            if cur: cur.close()
        # --- End Database Insertion ---

    # For GET request
    return render_template('volunteer.html', form_data=form_data, page_title="Volunteer With Us")


# --- Foster Route (Handles GET and POST) ---
@app.route('/foster', methods=['GET', 'POST'])
def foster_page():
    form_data = {} # Initialize
    if request.method == 'POST':
        form_data = request.form # Capture data
        # --- Retrieve form data ---
        name = form_data.get('foster_name')
        email = form_data.get('foster_email')
        phone = form_data.get('foster_phone')
        address = form_data.get('foster_address')
        household_info = form_data.get('foster_household')
        home_type = form_data.get('foster_home_type')
        has_yard = form_data.get('foster_has_yard')
        yard_fenced = form_data.get('foster_yard_fenced')
        can_transport = form_data.get('foster_can_transport')
        # Handle multiple preferred animals if using checkboxes
        preferred_animal = ", ".join(request.form.getlist('foster_preferred_animal'))
        foster_experience = form_data.get('foster_experience')
        why_foster = form_data.get('foster_why')

        # --- Basic Validation ---
        errors = []
        if not name: errors.append("Name is required.")
        if not email: errors.append("Email is required.")
        if not phone: errors.append("Phone number is required.")
        if not address: errors.append("Address is required.")
        if not home_type: errors.append("Home type is required.")
        if not has_yard: errors.append("Please specify if you have a yard.")
        if has_yard == 'Yes' and not yard_fenced: errors.append("If you have a yard, please specify if it's fenced.")
        if not can_transport: errors.append("Please indicate if you can provide transport.")
        if not why_foster: errors.append("Please tell us why you'd like to foster.")
        # Validate ENUM values
        if home_type not in ['House', 'Apartment', 'Condo', 'Other']: errors.append("Invalid home type selected.")
        if has_yard not in ['Yes', 'No', 'Partial']: errors.append("Invalid yard selection.")
        if yard_fenced not in ['Yes', 'No', 'Partial', None]: errors.append("Invalid fenced yard selection.") # Allow None if no yard
        if can_transport not in ['Yes', 'No']: errors.append("Invalid transport selection.")

        if errors:
            for error in errors: flash(error, 'danger')
            return render_template('foster.html', form_data=form_data, page_title="Foster a Pet")
        # --- End Validation ---

        # --- Database Insertion ---
        cur = None
        try:
            cur = mysql.connection.cursor()
            sql = """
                INSERT INTO fosters (name, email, phone, address, household_info, home_type,
                                   has_yard, yard_fenced, can_transport, preferred_animal,
                                   foster_experience, why_foster, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                name, email, phone, address, household_info if household_info else None, home_type,
                has_yard, yard_fenced if has_yard == 'Yes' else None, # Only store fenced if yard exists
                can_transport, preferred_animal if preferred_animal else None,
                foster_experience if foster_experience else None, why_foster, 'Pending'
            )
            cur.execute(sql, values)
            mysql.connection.commit()
            flash('Thank you for your interest in fostering! We will review your application and contact you soon.', 'success')
            return redirect(url_for('foster_page')) # Redirect after success
        except mysql.connection.IntegrityError: # Catch duplicate email
             mysql.connection.rollback()
             flash('An application with this email address already exists.', 'warning')
             return render_template('foster.html', form_data=form_data, page_title="Foster a Pet")
        except Exception as e:
            mysql.connection.rollback()
            print(f"!!! DB Error (Foster Insert): {e}"); traceback.print_exc()
            flash("An error occurred submitting your foster application. Please try again.", 'danger')
            return render_template('foster.html', form_data=form_data, page_title="Foster a Pet")
        finally:
            if cur: cur.close()
        # --- End Database Insertion ---

    # For GET request
    return render_template('foster.html', form_data=form_data, page_title="Foster a Pet")


@app.route('/educational')
def educational_page():
    return render_template('placeholder.html', page_title="Pet Care & Adoption Resources")

# Add near other page routes like /volunteer, /foster, etc.

@app.route('/contact', methods=['GET', 'POST'])
def contact_page():
    form_data = {} # Initialize for GET
    if request.method == 'POST':
        form_data = request.form # Capture data for potential repopulation
        name = form_data.get('contact_name')
        email = form_data.get('contact_email')
        subject = form_data.get('contact_subject')
        message = form_data.get('contact_message')

        errors = []
        if not name: errors.append("Name is required.")
        if not email: errors.append("Email is required.")
        if not subject: errors.append("Subject is required.")
        if not message: errors.append("Message cannot be empty.")
        # Add basic email format validation if desired

        if errors:
            for error in errors: flash(error, 'danger')
            return render_template('contact.html', page_title="Contact Us", form_data=form_data)

        # --- Process the contact message ---

        # Option 1: Send an Email (Keep commented out unless you set up Flask-Mail)
        # try:
        #     # send_contact_email(name, email, subject, message)
        #     flash("Thank you for your message! We'll get back to you soon.", 'success')
        #     return redirect(url_for('contact_page'))
        # except Exception as e:
        #     print(f"Error sending contact email: {e}")
        #     flash("Sorry, there was an error sending your message. Please try again later or use the contact details provided.", 'danger')
        #     return render_template('contact.html', page_title="Contact Us", form_data=form_data)

        # === Option 2: Store in Database (ACTIVATE THIS BLOCK) ===
        cur = None
        try:
            cur = mysql.connection.cursor()
            # Using NOW() for received_at which is handled by the DB default
            sql = "INSERT INTO contact_messages (name, email, subject, message) VALUES (%s, %s, %s, %s)"
            cur.execute(sql, (name, email, subject, message))
            mysql.connection.commit()
            flash("Thank you for your message! We have received it and will get back to you soon.", 'success')
            return redirect(url_for('contact_page')) # Redirect to clear form
        except Exception as e:
            mysql.connection.rollback()
            print(f"DB Error saving contact message: {e}")
            flash("Sorry, there was an error submitting your message due to a server issue. Please try again later.", 'danger')
            return render_template('contact.html', page_title="Contact Us", form_data=form_data) # Show form again with error
        finally:
            if cur: cur.close()
        # === End Option 2 ===

        # Option 3: Simple Placeholder (Keep commented out or remove)
        # print(f"--- Contact Form Submitted ---")
        # print(f"Name: {name}")
        # print(f"Email: {email}")
        # print(f"Subject: {subject}")
        # print(f"Message: {message}")
        # print(f"-----------------------------")
        # flash("Thank you for your message! We'll get back to you soon (submission simulated).", 'success')
        # return redirect(url_for('contact_page'))
        # --- End Processing ---

    # For GET request
    return render_template('contact.html', page_title="Contact Us", form_data=form_data)

# --- Make sure you have these imports ---
# from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
# import os, datetime, traceback # etc.


@app.errorhandler(404)
def page_not_found(e):
    print(f"404 Error: Path '{request.path}' not found.") # Add logging
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    print(f"!!! 500 Internal Server Error: {e}")
    traceback.print_exc() # Print detailed traceback to console
    # Optionally log the error to a file here
    return render_template('500.html'), 500

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)