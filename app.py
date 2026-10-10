import os
import sqlite3
import threading
import smtplib
from email.message import EmailMessage
import requests
from datetime import datetime
import markupsafe
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_fallback_secret")

limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])

DB_FILE = "messages.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        email TEXT,
                        subject TEXT,
                        message TEXT,
                        ip TEXT,
                        created_at TEXT,
                        email_sent INTEGER DEFAULT 0,
                        telegram_sent INTEGER DEFAULT 0,
                        is_read INTEGER DEFAULT 0
                    )''')
        conn.commit()

init_db()

def send_email(name, email, subject, message, timestamp):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    receiver = os.environ.get("RECEIVER_EMAIL")
    
    if not all([gmail_user, gmail_password, receiver]):
        print("Skipping email: Missing credentials")
        return False
        
    try:
        # Email to Owner
        msg = EmailMessage()
        msg.set_content(f"New message from {name} ({email}) at {timestamp}:\n\n{message}")
        msg['Subject'] = f"Portfolio Contact: {subject}"
        msg['From'] = gmail_user
        msg['To'] = receiver
        msg['Reply-To'] = email

        # Auto-reply to Visitor
        reply_msg = EmailMessage()
        reply_msg.set_content(f"Hi {name},\n\nThank you for reaching out! I have received your message regarding '{subject}' and will get back to you soon.\n\nBest regards,\nKeerthi V")
        reply_msg['Subject'] = "Thank you for contacting Keerthi V"
        reply_msg['From'] = gmail_user
        reply_msg['To'] = email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
            server.send_message(reply_msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_telegram(name, email, subject, message):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not all([bot_token, chat_id]):
        print("Skipping Telegram: Missing credentials")
        return False
        
    text = f"<b>New Portfolio Message</b>\n<b>Name:</b> {name}\n<b>Email:</b> {email}\n<b>Subject:</b> {subject}\n<b>Message:</b> {message}"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        response = requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'})
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def background_tasks(msg_id, name, email, subject, message, timestamp):
    email_success = send_email(name, email, subject, message, timestamp)
    tg_success = send_telegram(name, email, subject, message)
    
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE messages SET email_sent=?, telegram_sent=? WHERE id=?", 
                 (int(email_success), int(tg_success), msg_id))
        conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/contact', methods=['POST'])
@limiter.limit("5 per hour")
def contact():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
        
    honeypot = data.get('website', '')
    if honeypot:
        return jsonify({'success': True}), 200 # Fake success for bots
        
    name = markupsafe.escape(data.get('name', '').strip())
    email = markupsafe.escape(data.get('email', '').strip())
    subject = markupsafe.escape(data.get('subject', '').strip())
    message = markupsafe.escape(data.get('message', '').strip())
    
    if not all([name, email, subject, message]):
        return jsonify({'error': 'All fields are required.'}), 400
        
    if len(message) < 10 or len(message) > 2000:
        return jsonify({'error': 'Message must be between 10 and 2000 characters.'}), 400
        
    if '@' not in email or '.' not in email:
        return jsonify({'error': 'Invalid email address.'}), 400
        
    ip = request.remote_addr
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO messages (name, email, subject, message, ip, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                 (name, email, subject, message, ip, timestamp))
        conn.commit()
        msg_id = c.lastrowid
        
    threading.Thread(target=background_tasks, args=(msg_id, name, email, subject, message, timestamp)).start()
    
    return jsonify({'success': True, 'message': 'Your message has been sent successfully!'}), 200

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
        
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM messages ORDER BY created_at DESC")
        messages = c.fetchall()
        
    return render_template('admin.html', messages=messages)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == os.environ.get("ADMIN_PASSWORD"):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('admin_login.html', error='Invalid password')
    return render_template('admin_login.html')

@app.route('/admin/mark_read/<int:msg_id>', methods=['POST'])
def mark_read(msg_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE messages SET is_read=1 WHERE id=?", (msg_id,))
        conn.commit()
        
    return jsonify({'success': True})

@app.route('/admin/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
