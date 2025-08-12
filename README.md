# AnimalCareHub

## A Full-Stack Web Platform for Animal Adoption, Rescue, and Community Engagement

AnimalCareHub is a comprehensive web application designed to facilitate animal welfare by connecting prospective adopters with available pets, streamlining rescue reporting, and managing community engagement initiatives such as volunteering, fostering, and donations.

Built as a demonstration of modern web development principles, this project leverages Python's Flask framework for robust backend operations, coupled with HTML, CSS, and JavaScript for an intuitive and dynamic frontend experience.

## Live Demo (Optional)

*If your project is deployed, you can provide a link here.*
[https://your-project-live-link.com](https://your-project-live-link.com)

## Screenshots / Demo

*   *(Add a compelling GIF or a series of screenshots showcasing the application's key functionalities, e.g., Homepage, Login, Dashboard, Adoption listings, Animal Posting Form, Rescue Report Form, etc.)*

![AnimalCareHub Homepage Example](_static_screenshot_homepage.png)
![User Dashboard Example](_static_screenshot_dashboard.png)
*(Replace these with actual links to your screenshot images in the repo, e.g., `/docs/homepage.png` or `assets/dashboard.gif` if you create a `docs` or `assets` folder for them).*

## Key Features

*   **User Authentication & Authorization:** Secure user registration, login, and logout functionalities implemented with `Werkzeug Security` for password hashing and session management.
*   **Dynamic User Dashboard:** A personalized hub for logged-in users to track animals they've posted for adoption, monitor their submitted adoption requests, and view their donation history.
*   **Comprehensive Animal Management:**
    *   **Animal Listings:** Browse detailed profiles of animals available for adoption.
    *   **Animal Posting:** Logged-in users can easily post new animals, including uploading images.
    *   **Adoption Requests:** Streamlined process for interested individuals to submit adoption applications for specific animals, complete with file uploads (adopter photo, ID proof).
    *   **Adoption Request Processing:** Owners can accept or reject adoption requests directly from their dashboard, automatically updating animal statuses.
*   **Rescue Reporting:** A dedicated form for users (anonymous or logged-in) to report sightings of animals in distress, including location details and image uploads.
*   **Community Engagement Forms:**
    *   **Vaccination Appointments:** Users can schedule vaccination appointments for their pets.
    *   **Donations:** Facilitates both monetary and product donations, securely recording donor details.
    *   **Volunteer & Foster Applications:** Comprehensive application forms for individuals interested in volunteering or fostering pets, collecting relevant experience and availability.
*   **Interactive Frontend:** Dynamic rendering of data using Flask's Jinja2 templating, supported by CSS for responsive styling and JavaScript for enhanced user interactions and asynchronous data submissions.
*   **Robust Error Handling:** Custom 404 and 500 error pages, alongside extensive `try-except-finally` blocks and Flask's `flash` messages, ensure a resilient application experience and provide informative user feedback.

## Technologies Used

### Backend
*   **Python 3:** The foundational programming language.
*   **Flask:** A lightweight and flexible Python web framework orchestrating application logic, routing, and templating.
*   **Flask-MySQLdb:** Facilitates seamless integration and interaction with the MySQL database.
*   **Werkzeug Security:** Utilized for secure password hashing and secure filename generation for uploaded content.
*   **`python-dotenv`:** (Recommended for local setup) For managing environment variables to keep sensitive configuration separate.

### Frontend
*   **HTML5:** Structured semantic web content, leveraged with Jinja2 for dynamic page rendering.
*   **CSS3:** Applied for comprehensive styling, responsive design, and an appealing user interface.
*   **JavaScript:** Used for client-side validations, interactive elements, and AJAX requests to provide a more dynamic user experience.

### Database
*   **MySQL:** A powerful relational database management system for persistent storage of all application data (users, animals, requests, forms, etc.).
*   **SQL (Structured Query Language):** Employed for designing the database schema, performing all Create, Read, Update, Delete (CRUD) operations, and retrieving complex datasets using `JOIN` clauses and parameterized queries (preventing SQL injection).
*   **Transaction Management:** `mysql.connection.commit()` and `mysql.connection.rollback()` are strategically used to ensure data integrity during multi-step operations.

## Project Structure
AnimalCareHub/
├── .venv/ # Python virtual environment (ignored by Git)
├── static/ # Stores static assets (CSS, JS, images) and uploaded files
│ ├── css/ # Stylesheets
│ ├── image/ # Static images/icons
│ ├── js/ # JavaScript files
│ └── uploads/ # Dynamically uploaded user/animal/rescue files
│ ├── adoptions/
│ ├── animals/
│ └── rescues/
├── templates/ # Jinja2 HTML templates for dynamic content rendering
│ ├── _footer.html # Common footer
│ ├── _navbar.html # Common navigation bar
│ ├── 404.html # Not Found error page
│ ├── 500.html # Internal Server Error page
│ ├── adoption.html # Animal adoption listings
│ ├── base.html # Base template for all pages
│ ├── contact.html # Contact form
│ ├── dashboard.html # User-specific dashboard
│ ├── donate.html # Donation submission form
│ ├── foster.html # Foster application form
│ ├── index.html # Homepage
│ ├── login.html # User login form
│ ├── placeholder.html # Generic content template
│ ├── register.html # User registration form
│ ├── rescue.html # Animal rescue reporting form
│ ├── vaccination.html # Vaccination appointment scheduling
│ └── volunteer.html # Volunteer application form
├── app.py # The main Flask application, containing all routes and logic
├── requirements.txt # List of Python dependencies
├── schema.sql # SQL script to create the necessary database tables
├── .env # Environment variables (ignored by Git for security)
└── .gitignore # Specifies files and directories to be excluded from Git version control
└── README.md # Project documentation

## Setup and Installation

### Prerequisites

Ensure you have the following installed on your system:

*   **Python 3.x** (e.g., Python 3.8 or newer)
*   **pip** (Python package installer)
*   **MySQL Server:** A running instance of MySQL (e.g., through XAMPP, Docker, or a standalone installation).

### 1. Clone the Repository

Start by cloning the project files from GitHub to your local machine:

```bash
git clone https://github.com/Darshit1505/AnimalCareHub.git # Or your specific repo URL
cd AnimalCareHub
2. Set Up a Python Virtual Environment
It's highly recommended to use a virtual environment to manage project dependencies. This keeps them isolated from other Python projects.

python -m venv .venv
# On Windows (Command Prompt/PowerShell):
.\.venv\Scripts\activate
# On Linux/macOS (Bash/Zsh):
source .venv/bin/activate
3. Install Python Dependencies
With your virtual environment activated, install all required Python packages using pip:

pip install -r requirements.txt
requirements.txt Content:

Flask
Flask-MySQLdb
Werkzeug
python-dotenv

4. Database Setup (MySQL)
AnimalCareHub requires a MySQL database.
a. Create the Database:
Connect to your MySQL server as an administrative user (e.g., mysql -u root -p in your terminal or via a tool like phpMyAdmin/MySQL Workbench). Then, execute the following command to create the database:

CREATE DATABASE animal_rescue_db;
b. Import the Database Schema:
Navigate to the AnimalCareHub/ project root in your terminal. Import the provided SQL schema to create all necessary tables:

# For MySQL from your terminal
mysql -u root -p animal_rescue_db < schema.sql
schema.sql Content:

-- schema.sql
-- Run this script against your 'animal_rescue_db' database

-- Table for users (Registration and Login)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for animals posted for adoption
CREATE TABLE IF NOT EXISTS animals (
    animal_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT, -- ID of the user who posted the animal (optional, can be NULL for anonymous posters or if poster is deleted)
    name VARCHAR(100) NOT NULL,
    type VARCHAR(100) NOT NULL,
    age DECIMAL(5,2), -- Allowing for ages like 1.5 years
    description TEXT,
    image_filename VARCHAR(255), -- Relative path to uploaded image
    status ENUM('Available', 'Adopted', 'Withdrawn') DEFAULT 'Available',
    date_posted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Table for adoption requests
CREATE TABLE IF NOT EXISTS adoptions (
    adoption_id INT AUTO_INCREMENT PRIMARY KEY,
    animal_id INT NOT NULL,
    user_id INT, -- ID of the user who made the request
    animal_name VARCHAR(100), -- Snapshot of animal name at time of request
    adopter_name VARCHAR(255) NOT NULL,
    adopter_email VARCHAR(255) NOT NULL,
    status ENUM('Pending', 'Accepted', 'Rejected', 'Unavailable') DEFAULT 'Pending',
    adoption_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    photo_path VARCHAR(255), -- Path to uploaded adopter photo
    aadhaar_path VARCHAR(255), -- Path to uploaded ID proof
    FOREIGN KEY (animal_id) REFERENCES animals(animal_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Table for donations
CREATE TABLE IF NOT EXISTS donations (
    donation_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT, -- ID of logged-in donor, can be NULL for anonymous donations
    donor_name VARCHAR(255) NOT NULL,
    donor_email VARCHAR(255) NOT NULL,
    donor_phone VARCHAR(20),
    donation_type ENUM('Money', 'Products') NOT NULL,
    amount DECIMAL(10,2), -- NULL for product donations
    payment_method VARCHAR(50), -- E.g., 'Cash', 'Online Transfer', 'Card' (NULL for product donations)
    product_details TEXT, -- NULL for money donations
    donation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('Completed', 'Received', 'Pending_Confirmation') DEFAULT 'Received', -- Adjust as needed
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Table for vaccination appointment requests
CREATE TABLE IF NOT EXISTS vaccinations (
    vaccination_id INT AUTO_INCREMENT PRIMARY KEY,
    owner_name VARCHAR(255) NOT NULL,
    pet_name VARCHAR(255) NOT NULL,
    pet_type VARCHAR(100) NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time VARCHAR(50) NOT NULL, -- E.g., "9:00 AM - 10:00 AM"
    status ENUM('Pending', 'Confirmed', 'Completed', 'Cancelled') DEFAULT 'Pending',
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for rescue reports
CREATE TABLE IF NOT EXISTS rescues (
    rescue_id INT AUTO_INCREMENT PRIMARY KEY,
    reporter_user_id INT, -- Can be NULL for anonymous reports
    animal_type VARCHAR(100) NOT NULL,
    location VARCHAR(255) NOT NULL,
    condition_details TEXT,
    image_filename VARCHAR(255), -- Path to uploaded image
    status ENUM('Reported', 'InProgress', 'Rescued', 'Closed') DEFAULT 'Reported',
    report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reporter_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Table for volunteer applications
CREATE TABLE IF NOT EXISTS volunteers (
    volunteer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address VARCHAR(255),
    date_of_birth DATE,
    availability TEXT NOT NULL,
    areas_of_interest TEXT, -- Stores comma-separated interests
    experience TEXT,
    why_volunteer TEXT NOT NULL,
    status ENUM('Pending', 'Reviewed', 'Accepted', 'Rejected') DEFAULT 'Pending',
    application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for foster applications
CREATE TABLE IF NOT EXISTS fosters (
    foster_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address VARCHAR(255) NOT NULL,
    household_info TEXT,
    home_type ENUM('House', 'Apartment', 'Condo', 'Other') NOT NULL,
    has_yard ENUM('Yes', 'No', 'Partial') NOT NULL,
    yard_fenced ENUM('Yes', 'No', 'Partial'), -- NULL if no yard
    can_transport ENUM('Yes', 'No') NOT NULL,
    preferred_animal TEXT, -- Stores comma-separated preferred animal types
    foster_experience TEXT,
    why_foster TEXT NOT NULL,
    status ENUM('Pending', 'Reviewed', 'Accepted', 'Rejected') DEFAULT 'Pending',
    application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for contact messages
CREATE TABLE IF NOT EXISTS contact_messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

5. Configure Application Credentials (.env)
For security, sensitive configurations are best stored as environment variables.
(Create a .env file in your AnimalCareHub/ root directory and paste this content inside. Update values as needed.)

FLASK_SECRET_KEY='your_super_secret_key_here_a_random_string_with_symbols_and_numbers_!@#$%^&*'
MYSQL_HOST='localhost'
MYSQL_USER='root'
MYSQL_PASSWORD='' # Your MySQL root password, if applicable
MYSQL_DB='animal_rescue_db'

6. Create Upload Directories
The application requires specific folders for user-uploaded files. These should be automatically created by the ensure_dir function in app.py when the app runs, but you might need to check permissions if you encounter errors:
AnimalCareHub/static/uploads/adoptions
AnimalCareHub/static/uploads/animals
AnimalCareHub/static/uploads/rescues

Running the Application
After completing the setup steps:

Activate your virtual environment (if not already active).
Windows (Command Prompt/PowerShell): .\.venv\Scripts\activate
Linux/macOS (Bash/Zsh): source .venv/bin/activate

Run the Flask application:
python app.py

Access in Browser: Open your web browser and navigate to the address shown in your terminal (typically http://127.0.0.1:5000 or http://localhost:5000).

Key Learnings & Development Highlights

Building the AnimalCareHub project was an immersive experience that significantly enhanced my skills across the full stack:
Full-Stack Development Mastery: Gained hands-on experience integrating a Python Flask backend with dynamic HTML, CSS, and JavaScript on the frontend, managing the entire data flow and user interaction.
Modular Application Design: Learned to effectively structure a complex web application into logical, reusable components (routes, templates, static assets, helper functions), improving code organization and maintainability.
Robust Data Handling: Implemented comprehensive server-side input validation for all user-submitted forms, coupled with secure filename sanitization and error handling for reliable file uploads.
Database Management Proficiency (SQL): Deepened practical knowledge of relational database schema design (MySQL), executing a wide array of SQL queries (including JOIN operations for complex data retrieval), and managing database transactions (commit/rollback) to ensure data consistency and integrity.
User Authentication & Security: Developed a secure user authentication system including registration, login, logout, password hashing using Werkzeug Security, and session management.
API & Forms Interaction: Designed endpoints to handle various form submissions and file uploads, processing requests and providing dynamic JSON or rendered HTML responses.
Environment & Dependency Management: Gained practical experience in setting up Python virtual environments and managing project dependencies using pip and requirements.txt.

Future Enhancements

Admin Dashboard: Implement a dedicated administrator interface for streamlined management of users, animals, adoption requests, and reports.
Email Notifications: Integrate a system for automated email alerts (e.g., for new adoption requests, application status updates).
Image Optimization: Add server-side image processing to optimize and resize uploaded photos for better performance and storage.
Advanced Search & Filters: Enhance listing pages with more sophisticated search, sorting, and filtering options.
Payment Gateway Integration: For monetary donations, integrate with a real payment gateway (e.g., Stripe, PayPal).
Deployment Automation: Set up Continuous Integration/Continuous Deployment (CI/CD) pipelines for easier and more reliable deployments to cloud platforms.
Test Suite: Develop comprehensive unit and integration tests to ensure code quality and prevent regressions.
License
This project is open-sourced under the MIT License. See the LICENSE.md file in the repository for full details. (Create an empty LICENSE.md file in your root folder for completeness if you haven't already).
Contact
Feel free to connect with me for any questions or collaborations:
GitHub: https://github.com/Darshit1505
Email: darshitrupareliya15@gmail.com#   A n i m a l C a r e H u b 
 
 