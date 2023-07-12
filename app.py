from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import sqlite3
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.config['SECRET_KEY'] = '1206'

# Database initialization
DATABASE = 'vaccine_booking.db'

def create_tables():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        user_type TEXT NOT NULL,
        gender TEXT NOT NULL,
        date_of_birth DATE NOT NULL,
        phone_number TEXT NOT NULL,
        vaccination_status TEXT NOT NULL,
        address TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vaccination_centers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            timings TEXT NOT NULL,
            availability INTEGER DEFAULT 10
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS booked_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            center_id INTEGER NOT NULL,
            booked_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (center_id) REFERENCES vaccination_centers (id)
        )
    ''')

    # Check if admin user exists
    cursor.execute("SELECT * FROM users WHERE email = 'admin@example.com'")
    admin_user = cursor.fetchone()

    # Create admin user if it doesn't exist
    if not admin_user:
        cursor.execute("INSERT INTO users (name, email, password, user_type, gender, date_of_birth, phone_number, vaccination_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       ('Admin', 'admin@example.com', 'admin@1234', 'admin', 'Male', '1990-01-01', '1234567890', 'Yes'))

    conn.commit()
    conn.close()

# SendGrid configuration
SENDGRID_API_KEY = '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'
SENDER_EMAIL = 'yugeshsundram.aids20@veltechmultitech.org'

def send_email(recipient_email, subject, content):
    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=recipient_email,
        subject=subject,
        plain_text_content=content)

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(str(e))

@app.errorhandler(404)
def page_not_found(error):
    flash('Page not found. Please check the URL.', 'danger')
    return redirect(url_for('index'))


@app.errorhandler(500)
def internal_server_error(error):
    flash('Internal server error. Please try again later.', 'danger')
    return redirect(url_for('index'))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')


# User routes
@app.route('/user/signup', methods=['GET', 'POST'])
def user_signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        gender = request.form['gender']
        date_of_birth = request.form['date_of_birth']
        phone_number = request.form['phone_number']
        vaccination_status = request.form.get('vaccination_status', 'No')
        address = request.form.get('address', '')

        user_type = 'user'

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO users (name, email, password, user_type, gender, date_of_birth, phone_number, vaccination_status, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (name, email, password, user_type, gender, date_of_birth, phone_number, vaccination_status, address)
        )

        conn.commit()
        conn.close()

        # Send welcome email
        subject = 'Welcome to Vaccine Booking'
        content = f'Hi {name},\n\nThank you for registering on Vaccine Booking. We are excited to have you on board!'
        send_email(email, subject, content)

        flash('Registration successful! Please login to continue.', 'success')
        return redirect(url_for('user_login'))

    return render_template('user_signup.html')


@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()

        conn.close()

        if user and user[3] == password:
            flash('Login successful!', 'success')
            session['user_id'] = user[0]
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
            return redirect(url_for('user_login'))
    return render_template('user_login.html')

@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session:
        flash('Please login.', 'danger')
        return redirect(url_for('user_login'))

    user_id = session['user_id']

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM booked_slots WHERE user_id = ?', (user_id,))
    booked_slots = cursor.fetchall()

    cursor.execute('SELECT * FROM vaccination_centers')
    centers = cursor.fetchall()
    vaccination_centers = [dict(id=row[0], name=row[1], timings=row[2], availability=row[3]) for row in centers]

    conn.close()

    return render_template('user_dashboard.html', booked_slots=booked_slots, vaccination_centers=vaccination_centers)

@app.route('/user/logout')
def user_logout():
    session.clear()
    flash('Logout successful!', 'success')
    return redirect(url_for('index'))

@app.route('/vaccination_centers', methods=['GET', 'POST'])
def search_vaccination_centers():
    if request.method == 'POST':
        search_query = request.form['search_query']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM vaccination_centers WHERE name LIKE ?', ('%' + search_query + '%',))
        centers = cursor.fetchall()

        conn.close()

        return render_template('vaccination_centers.html', centers=centers)

    return render_template('vaccination_centers.html')


@app.route('/book_slot/<center_id>', methods=['GET', 'POST'])
def book_slot(center_id):
    if 'user_id' not in session:
        flash('Please login.', 'danger')
        return redirect(url_for('user_login'))

    if request.method == 'POST':
        user_id = session['user_id']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM booked_slots WHERE user_id = ? AND center_id = ?', (user_id, center_id))
        existing_slot = cursor.fetchone()

        if existing_slot:
            flash('You have already booked a slot for this center!', 'danger')
            return redirect(url_for('user_dashboard'))

        cursor.execute('SELECT availability FROM vaccination_centers WHERE id = ?', (center_id,))
        availability = cursor.fetchone()[0]

        if availability <= 0:
            flash('No available slots for this center!', 'danger')
            return redirect(url_for('user_dashboard'))

        cursor.execute('INSERT INTO booked_slots (user_id, center_id) VALUES (?, ?)', (user_id, center_id))
        cursor.execute('UPDATE vaccination_centers SET availability = availability - 1 WHERE id = ?', (center_id,))

        # Retrieve user email from the database
        cursor.execute('SELECT email FROM users WHERE id = ?', (user_id,))
        user_email = cursor.fetchone()[0]

        conn.commit()
        conn.close()

        # Send confirmation email
        subject = 'Slot Booking Confirmation'
        content = f'Thank you for booking a slot. Your booking is confirmed for Center ID: {center_id}.'
        send_email(user_email, subject, content)

        flash('Slot booked successfully!', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('book_slot.html', center_id=center_id)


# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE email = ? AND user_type = ?', (email, 'admin'))
        admin = cursor.fetchone()

        conn.close()

        if admin and admin[3] == password:
            session['admin_id'] = admin[0]
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash('Please login as admin.', 'danger')
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM booked_slots')
    booked_slots = cursor.fetchall()

    cursor.execute('SELECT * FROM vaccination_centers')
    vaccination_centers = cursor.fetchall()

    conn.close()

    return render_template('admin_dashboard.html', booked_slots=booked_slots, vaccination_centers=vaccination_centers)

@app.route('/admin/add_center', methods=['GET', 'POST'])
def add_vaccination_center():
    if 'admin_id' not in session:
        flash('Please login as admin.', 'danger')
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['name']
        timings = request.form['timings']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('INSERT INTO vaccination_centers (name, timings) VALUES (?, ?)', (name, timings))

        conn.commit()
        conn.close()

        flash('Vaccination center added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_vaccination_center.html')

@app.route('/admin/remove_center', methods=['POST'])
def remove_vaccination_center():
    if 'admin_id' not in session:
        flash('Please login as admin.', 'danger')
        return redirect(url_for('admin_login'))

    center_id = request.form['center_id']

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM vaccination_centers WHERE id = ?', (center_id,))

    conn.commit()
    conn.close()

    flash('Vaccination center removed successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# Other routes and functions

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
