# -*- coding: utf-8 -*-
from flask import (
    Flask, render_template, request, redirect, url_for, session, jsonify, flash
)
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
# FIX: Use timezone-aware datetimes instead of deprecated utcnow
from datetime import datetime, timedelta, date, timezone
import traceback
import os


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
    # FIX: Use timezone.utc instead of utcnow()
    now_utc = datetime.now(timezone.utc)
    return {'current_year': now_utc.year, 'now': now_utc} # Pass 'now' for min date


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
    # FIX: Use timezone.utc instead of utcnow()
    now_utc = datetime.now(timezone.utc)
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
    # FIX: Pass timezone-aware object
    return render_template('adoption.html', animals=animals, now=now_utc)


@app.route('/post_animal', methods=['POST'])
def post_animal():
    # Added logging to see what the server receives
    print("\n--- POST /post_animal ---")
    print("Request Form Data:", request.form)
    print("Request Files Data:", request.files)
    print("--- End POST /post_animal ---\n")


    if 'user_id' not in session:
        print("DEBUG: User not logged in for post_animal")
        return jsonify({'success': False, 'message': 'Please log in to post.'}), 401

    user_id=session['user_id']
    # Get data from the form dictionary
    name = request.form.get('animalName')
    animal_type = request.form.get('animalType')
    age_str = request.form.get('animalAge')
    description = request.form.get('animalDescription')
    image_file = request.files.get('animalImage') # Get file from request.files

    image_filename_rel = None
    image_path_full = None
    errors=[]
    age = None # Initialize age outside try block

    # Validation... (keep existing validation)
    # Note: Checks for None or empty string handle required fields from HTML forms well.
    if not name: errors.append('Name is required.')
    if not animal_type: errors.append('Type is required.')
    if not age_str: # Check for empty string/None first
        errors.append('Age is required.')
    else: # Only try conversion if age_str is provided
        try:
             age = float(age_str)
             if age < 0: # Ensure age is non-negative
                 errors.append('Age cannot be negative.')
        except ValueError:
             errors.append('Invalid age format. Must be a number (e.g., 2, 1.5).')

    if not description: errors.append('Description is required.')

    # Image Handling...
    if image_file and image_file.filename!='':
        if not allowed_file(image_file.filename, IMAGE_EXTENSIONS):
             errors.append('Invalid image file type (PNG, JPG, GIF allowed).')
        # If valid file and no errors so far, attempt to save
        else:
             if not errors: # Only try to save if validation passes so far
                try:
                    # FIX: Use timezone.utc instead of utcnow()
                    timestamp=datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f');
                    upload_folder=app.config['UPLOAD_FOLDER_ANIMALS']
                    base_filename=secure_filename(image_file.filename)
                    image_filename=f"animal_{user_id}_{timestamp}_{base_filename}"
                    image_path_full=os.path.join(upload_folder, image_filename)

                    if not ensure_dir(upload_folder):
                         raise OSError("Could not create upload directory.") # Raise error for specific handling

                    image_file.save(image_path_full)
                    image_filename_rel=os.path.join('uploads','animals',image_filename).replace("\\","/")
                    print(f"DEBUG: Image saved to {image_path_full}") # Log success
                except Exception as e:
                    print(f"ERROR image save: {e}"); traceback.print_exc()
                    errors.append(f'Image upload failed: {e}') # Include specific error if possible

    # Process Errors...
    if errors:
        # If an image was partially or fully uploaded but validation failed, try to clean it up
        if image_path_full and os.path.exists(image_path_full):
             try: os.remove(image_path_full); print(f"DEBUG: Cleaned up {image_path_full} after validation failure")
             except OSError as re: print(f"Error cleaning failed upload: {re}")
        print("DEBUG: Post Animal Validation Errors:", errors) # Log errors
        # Return 400 status for validation errors
        return jsonify({'success': False, 'message': " ".join(errors)}), 400


    # DB Insert...
    cur = None
    try:
        cur = mysql.connection.cursor()
        sql="INSERT INTO animals (user_id, name, type, age, description, image_filename, status) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        # Use None for image_filename if no file was uploaded and was optional
        values = (user_id, name, animal_type, age, description, image_filename_rel, 'Available')
        print("DEBUG: Attempting DB INSERT with values:", values)
        cur.execute(sql, values)
        new_animal_id = cur.lastrowid
        mysql.connection.commit()
        print(f"DEBUG: DB INSERT successful, animal_id={new_animal_id}")

        # Assuming image_filename_rel exists, otherwise url_for will handle None
        final_image_url = url_for('static', filename=image_filename_rel) if image_filename_rel else None

        return jsonify({'success': True, 'message': 'Animal posted successfully!', 'animal_id': new_animal_id, 'image_url': final_image_url})
    except Exception as e:
        mysql.connection.rollback()
        print(f"!!! DB Error (Post Animal Insert): {e}"); traceback.print_exc()
        # Cleanup uploaded file if DB insert fails after successful upload
        if image_path_full and os.path.exists(image_path_full):
            try: os.remove(image_path_full); print(f"DEBUG: Cleaned up {image_path_full} after DB error")
            except OSError as re: print(f"Error cleaning DB error upload: {re}")

        # Return 500 status for internal database errors
        return jsonify({'success': False, 'message': f'Database error occurred during posting.'}), 500
    finally:
        if cur: cur.close()

@app.route('/submit_adoption/<int:animal_id>', methods=['POST'])
def submit_adoption(animal_id):
    # Added logging to see what the server receives
    print(f"\n--- POST /submit_adoption/{animal_id} ---")
    print("Request Form Data:", request.form)
    print("Request Files Data:", request.files)
    print("--- End POST /submit_adoption/{animal_id} ---\n")

    if 'user_id' not in session:
        print("DEBUG: User not logged in for submit_adoption")
        return jsonify({'success': False, 'message': 'Please log in to submit an adoption request.'}), 401

    photo_path_full=None; aadhaar_path_full=None; adopter_name=request.form.get('adopterName'); adopter_email=request.form.get('adopterEmail')
    photo_file=request.files.get('adopterPhoto'); aadhaar_file=request.files.get('adopterAadhaar'); user_id=session['user_id']
    errors=[]

    # Added more explicit checks for None or empty strings for required form fields
    if not adopter_name: errors.append("Your full name is required.")
    if not adopter_email: errors.append("Your email address is required.")
    if not photo_file or photo_file.filename == '': errors.append("Your photo upload is required.")
    if not aadhaar_file or aadhaar_file.filename == '': errors.append("Your ID proof upload is required.")


    # Check file types using the refined allowed_file function ONLY if file is provided
    if photo_file and photo_file.filename != '':
        if not allowed_file(photo_file.filename, IMAGE_EXTENSIONS):
             errors.append("Invalid photo file type. Only images (PNG, JPG, GIF) allowed.")
    if aadhaar_file and aadhaar_file.filename != '':
        if not allowed_file(aadhaar_file.filename, ALLOWED_EXTENSIONS): # Images or PDF for ID proof
            errors.append("Invalid ID proof file type. Only images (PNG, JPG, GIF) or PDF allowed.")
    # --- End file type checks ---

    animal_name=None; cur_check=None
    try:
        cur_check=mysql.connection.cursor();
        cur_check.execute("SELECT name, status FROM animals WHERE animal_id = %s", (animal_id,))
        animal_data=cur_check.fetchone()
        if not animal_data: errors.append("Animal not found.")
        elif animal_data['status']!='Available': errors.append("This animal is no longer available for adoption.") # More specific message
        else: animal_name=animal_data['name']
    except Exception as check_e:
        print(f"Error checking animal status: {check_e}"); traceback.print_exc()
        errors.append("Could not verify animal status.") # Don't add DB detail to user error


    # Return validation/check errors BEFORE attempting file save
    if errors:
        print("DEBUG: Submit Adoption Validation Errors:", errors)
        # Distinguish validation error vs. status error slightly for response code
        if "Animal not found" in " ".join(errors): status_code = 404 # Not Found
        elif "animal is no longer available" in " ".join(errors): status_code = 409 # Conflict
        else: status_code = 400 # Bad Request (typical validation fail)
        return jsonify({'success': False, 'message': " ".join(errors)}), status_code

    # If no errors so far, proceed with file saving and DB insert
    try:
        # FIX: Use timezone.utc instead of utcnow() for timestamp
        timestamp=datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f');
        upload_folder=app.config['UPLOAD_FOLDER_ADOPTIONS']
        if not ensure_dir(upload_folder):
             raise OSError("Adoption upload dir error.") # Raise exception if dir creation fails


        # Save photo (checked if file exists earlier in validation)
        photo_filename=secure_filename(f"photo_{user_id}_{timestamp}_{photo_file.filename}")
        photo_path_full=os.path.join(upload_folder, photo_filename)
        photo_file.save(photo_path_full)
        photo_path_rel=os.path.join('uploads','adoptions',photo_filename).replace("\\","/")
        print(f"DEBUG: Photo saved to {photo_path_full}") # Log success


        # Save Aadhaar/ID (checked if file exists earlier in validation)
        aadhaar_filename=secure_filename(f"id_{user_id}_{timestamp}_{aadhaar_file.filename}") # Changed prefix for clarity
        aadhaar_path_full=os.path.join(upload_folder, aadhaar_filename)
        aadhaar_file.save(aadhaar_path_full)
        aadhaar_path_rel=os.path.join('uploads','adoptions',aadhaar_filename).replace("\\","/")
        print(f"DEBUG: ID proof saved to {aadhaar_path_full}") # Log success


        cur=None
        try:
            cur = mysql.connection.cursor()
            sql="INSERT INTO adoptions (animal_id, animal_name, adopter_name, adopter_email, status, photo_path, aadhaar_path, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            values = (animal_id, animal_name, adopter_name, adopter_email, 'Pending', photo_path_rel, aadhaar_path_rel, user_id);
            print("DEBUG: Attempting DB INSERT with values:", values)
            cur.execute(sql, values)
            mysql.connection.commit()
            print(f"DEBUG: DB INSERT successful for adoption on animal_id={animal_id}")

            # Flash success message (this flash message won't directly appear in the AJAX response, but you keep it for potential non-AJAX scenarios or logging)
            # flash('Adoption request submitted successfully!', 'success') # Redundant if relying only on AJAX response message

            # Successful response
            return jsonify({'success': True, 'message': 'Adoption request submitted successfully! We will contact you soon.'}), 200 # Explicitly return 200 for success


        except Exception as db_error:
             mysql.connection.rollback()
             print(f"!!! DB Error inserting adoption: {db_error}"); traceback.print_exc()
             # Raise DB exception so outer 'except' block handles file cleanup
             raise db_error # Re-raise to trigger outer cleanup and 500 error response


    except Exception as e:
        # This outer block catches:
        # - File saving errors (from image_file.save or ensure_dir failures)
        # - Database errors (rethrown from the inner try/except)
        print(f"!!! Unhandled error submitting adoption request: {e}"); traceback.print_exc()

        # Cleanup uploaded files if error occurred after saving them
        # Check if photo_path_full was assigned (meaning file save attempt started) and if file exists
        if photo_path_full and os.path.exists(photo_path_full):
            try: os.remove(photo_path_full); print(f"DEBUG: Cleaned up photo {photo_path_full} after error")
            except OSError as re: print(f"Error removing photo file {photo_path_full}: {re}")

        # Check if aadhaar_path_full was assigned and if file exists
        if aadhaar_path_full and os.path.exists(aadhaar_path_full):
            try: os.remove(aadhaar_path_full); print(f"DEBUG: Cleaned up ID proof {aadhaar_path_full} after error")
            except OSError as re: print(f"Error removing ID proof file {aadhaar_path_full}: {re}")


        # Handle the specific type of error (e.g., if it's an OSError from dir creation)
        if isinstance(e, OSError) and "Adoption upload dir error" in str(e):
             return jsonify({'success': False, 'message': 'Could not process file uploads due to a server directory issue.'}), 500
        elif isinstance(e, mysql.connection.Error): # If it's a database error rethrown
            return jsonify({'success': False, 'message': 'A database error occurred while saving your request. Please try again.'}), 500
        # Any other unhandled exception becomes a generic 500
        else:
             # A validation or animal check error that *escaped* the first block shouldn't happen with the fixes above,
             # but as a fallback, return 500 or a specific message if the error string matches a known validation failure message.
             # More robust: Check if 'e' is one of the messages from the first 'errors' list.
             # But with the primary validation block moved *before* file saving, this outer catch should primarily get file/DB errors.
             print("DEBUG: Falling back to generic 500 for unexpected error:", e)
             return jsonify({'success': False, 'message': 'An internal server error occurred during submission.'}), 500


    # The `finally` block on the inner try/except already closes the cursor if needed.


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
        # If action is accept AND animal status is NOT Available or already Adopted, conflict
        if action=='accept':
             if not animal_status: # Animal doesn't exist? Should not happen if join worked, but defensive
                  return jsonify({'success': False, 'message': 'Cannot process, animal record missing.'}), 404
             if animal_status['status'] != 'Available':
                # More specific message depending on *current* status
                conflict_msg = "Cannot accept: Animal is already adopted." if animal_status['status'] == 'Adopted' else f"Cannot accept: Animal status is currently '{animal_status['status']}'."
                return jsonify({'success': False, 'message': conflict_msg}), 409 # Conflict


        if action=='accept':
            # Before accepting, double-check there aren't other accepted requests for *this specific animal* (shouldn't happen due to logic flow but defensive)
            cur.execute("SELECT COUNT(*) FROM adoptions WHERE animal_id = %s AND status = 'Accepted'", (animal_id,))
            if cur.fetchone()['COUNT(*)'] > 0:
                 # This might indicate concurrent requests; handle gracefully
                 # No need to roll back anything if we haven't changed anything yet
                 return jsonify({'success': False, 'message': 'Another request for this animal has just been accepted.'}), 409 # Conflict


            cur.execute("UPDATE adoptions SET status = 'Accepted' WHERE adoption_id = %s", (adoption_id,))
            cur.execute("UPDATE animals SET status = 'Adopted' WHERE animal_id = %s", (animal_id,))
            # Mark other pending requests for the same animal as unavailable
            # IMPORTANT: Filter should be status='Pending'. We *don't* want to overwrite the status
            # of any request that might have become 'Accepted' just microseconds ago in a different thread.
            # Also no need to check adoption_id != %s, because updating 'Accepted' to 'Accepted' is harmless.
            cur.execute("UPDATE adoptions SET status = 'Unavailable' WHERE animal_id = %s AND status = 'Pending'", (animal_id,))
            mysql.connection.commit();
            return jsonify({'success': True, 'message': 'Adoption accepted! Other pending requests marked as unavailable.'})
        elif action=='reject':
            # Note: Rejecting a request does NOT change the animal's status from 'Available' or 'Adopted'.
            # Rejecting just changes *this specific adoption request's* status.
            cur.execute("UPDATE adoptions SET status = 'Rejected' WHERE adoption_id = %s", (adoption_id,))
            mysql.connection.commit();
            return jsonify({'success': True, 'message': 'Adoption rejected.'})
    except Exception as e:
        mysql.connection.rollback()
        print(f"!!! DB Error process adoption: {e}"); traceback.print_exc()
        # Return 500 for internal database errors
        return jsonify({'success': False,'message': f'Database error occurred processing request.'}), 500
    finally:
        if cur: cur.close()


@app.route('/vaccination', methods=['GET', 'POST'])
def vaccination_page():
    form_data = {} # Initialize form_data as a dictionary to store POST data
    if request.method == 'POST':
        form_data = request.form # Capture form data for repopulation
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
            # Note: The `date` object comparison `appointment_date < date.today()` correctly ignores time zones.


        if errors:
            # If validation errors, flash and render template with existing form data
            for error in errors: flash(error, 'danger')
            # FIX: Pass now (timezone-aware) for datepicker min attribute
            return render_template('vaccination.html', form_data=form_data, page_title="Schedule Vaccination", now=datetime.now(timezone.utc))
        # --- End Validation ---

        cur = None
        try:
            cur = mysql.connection.cursor()
            # Store appointment_date as a DATE type in MySQL. Pass a Python date object.
            sql = "INSERT INTO vaccinations (owner_name, pet_name, pet_type, appointment_date, appointment_time, status) VALUES (%s, %s, %s, %s, %s, %s)"
            values = (owner_name, pet_name, pet_type, appointment_date, appointment_time, 'Pending')
            cur.execute(sql, values)
            mysql.connection.commit()
            flash(f"Appointment requested for {pet_name} on {appointment_date_str} ({appointment_time}). We will contact you to confirm.", 'success')
            return redirect(url_for('vaccination_page')) # Redirect after successful submission (GET request)
        except Exception as e:
            mysql.connection.rollback()
            print(f"!!! DB Error (Vaccination Insert): {e}"); traceback.print_exc()
            flash("There was an error booking the appointment. Please try again.", 'danger')
            # Pass form_data and now back on DB error too
            return render_template('vaccination.html', form_data=form_data, page_title="Schedule Vaccination", now=datetime.now(timezone.utc))
        finally:
            if cur: cur.close()

    # For GET request (or initial page load before POST)
    # FIX: Pass now (timezone-aware) for datepicker min attribute
    return render_template('vaccination.html', form_data=form_data, page_title="Schedule Vaccination", now=datetime.now(timezone.utc)) # Pass empty form_data initially


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
        donor_phone = form_data.get('donor_phone')

        errors = []
        if not donor_name: errors.append("Your name is required.")
        if not donor_email: errors.append("Your email is required.")
        if not donation_type: errors.append("Please select a donation type.")

        amount_float = None # Initialize to None
        if donation_type == 'Money':
            if not amount: errors.append("Amount is required for monetary donations.")
            else:
                try:
                    amount_float = float(amount)
                    if amount_float <= 0: errors.append("Donation amount must be positive.")
                except ValueError: errors.append("Invalid amount format. Must be a number.")
            # Payment method required check (if it's a select/radio, browser 'required' handles None/empty string)
            if payment_method is None or payment_method == '': errors.append("Payment method is required for monetary donations.")

        elif donation_type == 'Products':
            # Check product_details only if the type is Products
            if not product_details or not product_details.strip(): errors.append("Product details are required for product donations.")

        if errors:
            # Flash errors and return the template with collected form data
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


            # Prepare values based on donation type. Ensure `None` for fields not applicable.
            values = (
                user_id,
                donor_name,
                donor_email,
                donor_phone if donor_phone and donor_phone.strip() else None, # Store None if phone is empty or just whitespace
                donation_type,
                amount_float if donation_type == 'Money' else None, # Only store amount for Money type
                payment_method if donation_type == 'Money' else None, # Only store payment_method for Money type
                product_details if donation_type == 'Products' and product_details and product_details.strip() else None, # Only store product_details for Products if provided
                # Set initial status - 'Completed' for Money, 'Received' or 'Pending_Confirmation' for Products might make sense.
                # For this code, assuming 'Completed' means processed payment, 'Received' means details recorded.
                'Completed' if donation_type == 'Money' and amount_float else 'Received' # Example status logic, adjust as needed
                # Note: A real money donation would need integration with a payment gateway here, updating status after successful payment confirmation.
            )
            cur.execute(sql, values)
            mysql.connection.commit()
            flash('Thank you for your generous donation! Your contribution is greatly appreciated.', 'success')
            # Redirect to the GET version of the page to clear the form and show success message clearly
            return redirect(url_for('donate_page'))
        except Exception as e:
            mysql.connection.rollback()
            print(f"!!! DB Error (Donation Insert): {e}"); traceback.print_exc()
            flash("We encountered an error recording your donation. Please try again.", 'danger')
            # Render template with collected data on DB error
            return render_template('donate.html', form_data=form_data, page_title="Make a Donation")
        finally:
            if cur: cur.close()
        # --- End Database Insertion ---

    # For GET request
    # Pass empty form_data dictionary so the template doesn't try to access non-existent keys
    return render_template('donate.html', form_data=form_data, page_title="Make a Donation")


@app.route('/rescue', methods=['GET', 'POST'])
def rescue_page():
    form_data = {} # Initialize as dictionary for GET
    if request.method == 'POST':
        form_data = request.form # Capture data
        reporter_user_id = session.get('user_id') # Can be None if not logged in
        animal_type_select = form_data.get('animalType')
        other_animal_type = form_data.get('otherAnimalType')
        location = form_data.get('location')
        condition_details = form_data.get('condition_details')
        image_file = request.files.get('animalImage')

        image_filename_rel = None
        image_path_full = None

        # --- Validation ---
        final_animal_type = animal_type_select
        errors = []

        # Handle "Other" animal type logic
        if animal_type_select == 'Other':
            if not other_animal_type or not other_animal_type.strip():
                errors.append('Please specify the type of animal if selecting "Other".')
            else:
                final_animal_type = other_animal_type.strip()
        elif not animal_type_select or not animal_type_select.strip(): # Ensure a type is selected if not "Other"
             errors.append("Animal type is required.")

        # Check location
        if not location or not location.strip(): errors.append("Location is required.")

        # Check image file
        if not image_file or image_file.filename == '':
            errors.append("An image upload is required.") # You can change this to optional if needed
        else:
             # Check file type ONLY if a file was uploaded
             if not allowed_file(image_file.filename, RESCUE_ALLOWED_EXTENSIONS):
                  errors.append(f"Invalid image file type ({', '.join(RESCUE_ALLOWED_EXTENSIONS)} allowed).")

        # If there are validation errors, flash and re-render the template with form data
        if errors:
            for error in errors: flash(error, 'danger')
            return render_template('rescue.html', form_data=form_data, page_title="Report Animal Sighting")
        # --- End Validation ---

        # --- Image Saving ---
        # Proceed with image saving ONLY if validation passed and a file exists
        try:
            # FIX: Use timezone.utc instead of utcnow() for timestamp
            timestamp=datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f');
            upload_folder=app.config['UPLOAD_FOLDER_RESCUES']
            base_filename=secure_filename(image_file.filename)
            user_prefix=f"{reporter_user_id}_" if reporter_user_id else "anon_" # Use anon_ prefix if user is not logged in
            image_filename=f"rescue_{user_prefix}{timestamp}_{base_filename}";
            image_path_full=os.path.join(upload_folder, image_filename)

            if not ensure_dir(upload_folder):
                 raise OSError("Rescue upload directory creation error.") # Raise an exception for better handling

            image_file.save(image_path_full)
            image_filename_rel=os.path.join('uploads','rescues',image_filename).replace("\\","/")
            print(f"DEBUG: Rescue image saved to {image_path_full}") # Log success

        except Exception as e:
             print(f"!!! ERROR saving rescue image: {e}"); traceback.print_exc()
             flash('Image upload failed due to a server error.', 'danger') # More generic error message for user
             # If saving fails here, return the page again with form data and error
             return render_template('rescue.html', form_data=form_data, page_title="Report Animal Sighting")

        # --- End Image Saving ---


        # --- Database Insertion ---
        cur = None
        try:
            cur = mysql.connection.cursor()
            sql = "INSERT INTO rescues (animal_type, location, condition_details, image_filename, reporter_user_id, status) VALUES (%s, %s, %s, %s, %s, %s)"
            # Use None for optional fields if they are empty or just whitespace
            values = (
                final_animal_type,
                location.strip(), # Trim leading/trailing whitespace
                condition_details.strip() if condition_details and condition_details.strip() else None, # Trim optional field or store None
                image_filename_rel,
                reporter_user_id,
                'Reported' # Default status
            )
            print("DEBUG: Attempting DB INSERT for rescue report with values:", values)
            cur.execute(sql, values)
            mysql.connection.commit()
            print(f"DEBUG: DB INSERT successful for rescue report")

            flash('Rescue report submitted successfully! Thank you for your help.', 'success')
            return redirect(url_for('rescue_page')) # Redirect after success to clear form

        except Exception as e:
            mysql.connection.rollback()
            print(f"!!! DB Error (Rescue Insert): {e}"); traceback.print_exc()
            # Cleanup image if DB insert fails
            if image_path_full and os.path.exists(image_path_full):
                try: os.remove(image_path_full); print(f"DEBUG: Cleaned up rescue image {image_path_full} after DB error")
                except OSError as re: print(f"Error cleaning failed rescue image: {re}")

            flash("An error occurred while submitting the report due to a server error. Please try again.", 'danger')
            # Render template with collected form data on DB error
            return render_template('rescue.html', form_data=form_data, page_title="Report Animal Sighting")
        finally:
            if cur: cur.close()
        # --- End Database Insertion ---

    # For GET request
    # Pass empty dictionary so template form fields don't cause errors if form_data is checked directly
    return render_template('rescue.html', form_data=form_data, page_title="Report Animal Sighting")


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
        # request.form.getlist('volunteer_interests') correctly gets list for multi-select/checkbox
        interests_list = request.form.getlist('volunteer_interests')
        interests = ", ".join(interests_list) if interests_list else None # Store as comma-separated string or None

        experience = form_data.get('volunteer_experience')
        why_volunteer = form_data.get('volunteer_why')

        # --- Basic Validation ---
        errors = []
        if not name or not name.strip(): errors.append("Name is required.")
        # Add basic email format validation if needed, in addition to required check
        if not email or not email.strip(): errors.append("Email is required.")
        elif '@' not in email or '.' not in email: errors.append("Please enter a valid email address.") # Basic email format check


        if not availability or not availability.strip(): errors.append("Availability information is required.")

        # Validation for checkboxes - is any option selected? (Adapt if 'Other' with text field is used)
        # Checkboxes return an empty list if none are checked.
        if not interests_list: errors.append("Please select at least one area of interest.")

        if not why_volunteer or not why_volunteer.strip(): errors.append("Please tell us why you'd like to volunteer.")

        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                # Optional: Age check (e.g., must be over 18) - using Python's date objects for robust calculation
                today = date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                # Assuming a typical minimum age requirement
                if age < 18:
                     errors.append("You must be at least 18 years old to volunteer with us.")
            except ValueError:
                errors.append("Invalid Date of Birth format. Please use YYYY-MM-DD.")
        # Note: Depending on your policy, DOB itself might be optional. If so, remove the `else` below.
        # else: errors.append("Date of Birth is required.") # Example if DOB is required

        if errors:
            for error in errors: flash(error, 'danger')
            # Repopulate form data by passing the dictionary
            # Checkboxes need getlist. The form_data passed to render_template
            # allows .get() for text/select/radio and .getlist() for checkboxes.
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
            # Use None for optional fields if they are empty or just whitespace
            values = (
                name.strip(),
                email.strip(),
                phone.strip() if phone and phone.strip() else None,
                address.strip() if address and address.strip() else None,
                dob, # Pass date object directly
                availability.strip(),
                interests, # Pass the comma-separated string or None
                experience.strip() if experience and experience.strip() else None,
                why_volunteer.strip(),
                'Pending' # Default status
            )
            cur.execute(sql, values)
            mysql.connection.commit()
            flash('Thank you for applying to volunteer! We will review your application and be in touch.', 'success')
            return redirect(url_for('volunteer_page')) # Redirect after success to clear form

        except mysql.connection.IntegrityError: # Catch duplicate email or other unique constraint errors
             mysql.connection.rollback()
             # Check specific error message if needed to distinguish unique constraints
             flash('An application with this email address already exists. Please contact us if you need to update your information.', 'warning')
             return render_template('volunteer.html', form_data=form_data, page_title="Volunteer With Us")

        except Exception as e:
            mysql.connection.rollback()
            print(f"!!! DB Error (Volunteer Insert): {e}"); traceback.print_exc()
            flash("An error occurred submitting your application due to a server error. Please try again.", 'danger')
            return render_template('volunteer.html', form_data=form_data, page_title="Volunteer With Us")
        finally:
            if cur: cur.close()
        # --- End Database Insertion ---

    # For GET request, pass form_data as empty dictionary for template access
    return render_template('volunteer.html', form_data=form_data, page_title="Volunteer With Us")


# --- Foster Route (Handles GET and POST) ---
@app.route('/foster', methods=['GET', 'POST'])
def foster_page():
    form_data = {} # Initialize as dictionary for GET
    if request.method == 'POST':
        form_data = request.form # Capture data
        # --- Retrieve form data ---
        name = form_data.get('foster_name')
        email = form_data.get('foster_email')
        phone = form_data.get('foster_phone')
        address = form_data.get('foster_address')
        household_info = form_data.get('foster_household')
        home_type = form_data.get('foster_home_type')
        has_yard = form_data.get('foster_has_yard') # Radio value ('Yes', 'No', 'Partial')
        yard_fenced = form_data.get('foster_yard_fenced') # Radio value ('Yes', 'No', 'Partial')
        can_transport = form_data.get('foster_can_transport') # Radio value ('Yes', 'No')
        # Handle multiple preferred animals if using checkboxes
        preferred_animal_list = request.form.getlist('foster_preferred_animal')
        preferred_animal = ", ".join(preferred_animal_list) if preferred_animal_list else None # Store as comma-separated string or None

        foster_experience = form_data.get('foster_experience')
        why_foster = form_data.get('foster_why')

        # --- Basic Validation ---
        errors = []
        if not name or not name.strip(): errors.append("Name is required.")
        if not email or not email.strip(): errors.append("Email is required.")
        elif '@' not in email or '.' not in email: errors.append("Please enter a valid email address.")
        if not phone or not phone.strip(): errors.append("Phone number is required.")
        if not address or not address.strip(): errors.append("Address is required.")

        # Home and yard validation
        valid_home_types = ['House', 'Apartment', 'Condo', 'Other']
        if not home_type or home_type not in valid_home_types: errors.append("Valid home type is required.")

        valid_yard_types = ['Yes', 'No', 'Partial']
        if not has_yard or has_yard not in valid_yard_types:
             errors.append("Please specify if you have a yard (Yes, No, or Partial).")
        elif has_yard in ['Yes', 'Partial']: # Only require fenced status if there is some kind of yard
            valid_fenced_types_for_yard = ['Yes', 'No', 'Partial'] # Match your HTML options
            if not yard_fenced or yard_fenced not in valid_fenced_types_for_yard:
                 errors.append("Please specify if your yard is fenced, not fenced, or partially fenced.")

        valid_transport_types = ['Yes', 'No']
        if not can_transport or can_transport not in valid_transport_types: errors.append("Please indicate if you can provide transport.")


        if not why_foster or not why_foster.strip(): errors.append("Please tell us why you'd like to foster.")

        # Note: No explicit check for `preferred_animal_list` emptiness like in volunteer,
        # as fostering might not have a mandatory "preferred type". If you want it mandatory,
        # add `if not preferred_animal_list: errors.append("Please select at least one preferred animal type.");`

        if errors:
            # Flash errors and render template with collected data
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
            # Use None for optional fields if they are empty or just whitespace
            values = (
                name.strip(),
                email.strip(),
                phone.strip(),
                address.strip(),
                household_info.strip() if household_info and household_info.strip() else None,
                home_type,
                has_yard,
                # Only store yard_fenced value if a yard exists (Yes or Partial)
                yard_fenced if has_yard in ['Yes', 'Partial'] else None,
                can_transport,
                preferred_animal, # Comma-separated string or None
                foster_experience.strip() if foster_experience and foster_experience.strip() else None,
                why_foster.strip(),
                'Pending' # Default status
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
            flash("An error occurred submitting your foster application due to a server error. Please try again.", 'danger')
            return render_template('foster.html', form_data=form_data, page_title="Foster a Pet")
        finally:
            if cur: cur.close()
        # --- End Database Insertion ---

    # For GET request, pass empty form_data dictionary
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
        if not name or not name.strip(): errors.append("Name is required.")
        if not email or not email.strip(): errors.append("Email is required.")
        elif '@' not in email or '.' not in email: errors.append("Please enter a valid email address.")
        if not subject or not subject.strip(): errors.append("Subject is required.")
        if not message or not message.strip(): errors.append("Message cannot be empty.")

        if errors:
            for error in errors: flash(error, 'danger')
            return render_template('contact.html', page_title="Contact Us", form_data=form_data)

        # === Store in Database ===
        cur = None
        try:
            cur = mysql.connection.cursor()
            sql = "INSERT INTO contact_messages (name, email, subject, message) VALUES (%s, %s, %s, %s)"
            values = (
                name.strip(),
                email.strip(),
                subject.strip(),
                message.strip()
            )
            cur.execute(sql, values)
            mysql.connection.commit()
            flash("Thank you for your message! We have received it and will get back to you soon.", 'success')
            return redirect(url_for('contact_page')) # Redirect to clear form
        except Exception as e:
            mysql.connection.rollback()
            print(f"DB Error saving contact message: {e}"); traceback.print_exc()
            flash("Sorry, there was an error submitting your message due to a server issue. Please try again later.", 'danger')
            return render_template('contact.html', page_title="Contact Us", form_data=form_data) # Show form again with error
        finally:
            if cur: cur.close()
        # === End Option 2 ===


    # For GET request, pass empty dictionary
    return render_template('contact.html', page_title="Contact Us", form_data=form_data)


@app.errorhandler(404)
def page_not_found(e):
    print(f"404 Error: Path '{request.path}' not found.") # Add logging
    # FIX: Use timezone-aware object for current year in 404/500 pages
    current_year = datetime.now(timezone.utc).year
    return render_template('404.html', current_year=current_year), 404

@app.errorhandler(500)
def internal_server_error(e):
    print(f"!!! 500 Internal Server Error: {e}")
    traceback.print_exc() # Print detailed traceback to console
    # Optionally log the error to a file here
    # FIX: Use timezone-aware object for current year in 404/500 pages
    current_year = datetime.now(timezone.utc).year
    return render_template('500.html', current_year=current_year), 500

# --- Main Execution ---
if __name__ == '__main__':
    # In production, prefer serving via a production-ready WSGI server like Gunicorn or uWSGI.
    # debug=True should ONLY be used during development.
    app.run(debug=True, host='0.0.0.0', port=5000)