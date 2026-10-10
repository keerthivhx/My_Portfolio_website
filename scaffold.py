import os

base_dir = r"c:\Users\keert\OneDrive\Desktop\Projects\portfolio"

files = {
    "requirements.txt": """Flask==3.0.0
Flask-Limiter==3.5.0
python-dotenv==1.0.0
gunicorn==21.2.0
requests==2.31.0
markupsafe==2.1.3""",

    "Procfile": "web: gunicorn app:app",

    ".env.example": """GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
RECEIVER_EMAIL=your_email@gmail.com
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
ADMIN_PASSWORD=secure_admin_password
SECRET_KEY=generate_a_secure_random_key""",

    ".env": """GMAIL_USER=fake@gmail.com
GMAIL_APP_PASSWORD=fake
RECEIVER_EMAIL=fake@gmail.com
TELEGRAM_BOT_TOKEN=fake
TELEGRAM_CHAT_ID=fake
ADMIN_PASSWORD=admin
SECRET_KEY=dev_secret_key""",

    ".gitignore": """__pycache__/
*.pyc
.env
messages.db
venv/
.venv/""",

    "README.md": """# Keerthi V - Personal Portfolio

A production-ready personal portfolio website built with HTML5, CSS3, Vanilla JS, and Flask.

## Features
- Modern Dark/Light theme toggle
- Real-time contact form with SQLite backup, Email, and Telegram notifications
- Secure Admin Inbox
- Responsive, mobile-first design

## Setup & Run Locally
1. Create a virtual environment: `python -m venv venv`
2. Activate it: `venv\\Scripts\\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your details.
5. Create a `static/resume.pdf` file with your resume.
6. Run the app: `python app.py`

## Getting Credentials
- **Gmail App Password**: Go to Google Account -> Security -> 2-Step Verification -> App passwords. Generate a new one.
- **Telegram Bot**: Open Telegram, search for `@BotFather`, send `/newbot`. Copy the HTTP API token. To get your chat ID, search for `@userinfobot` and start a chat.

## Deployment (Render)
1. Push this repository to GitHub.
2. Create a new Web Service on Render, connect your repository.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. Add all the Environment Variables from your `.env` to the Render dashboard.

> **Note**: Drop your PDF resume inside the `static/` folder and name it `resume.pdf`.""",

    "app.py": """import os
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
        msg.set_content(f"New message from {name} ({email}) at {timestamp}:\\n\\n{message}")
        msg['Subject'] = f"Portfolio Contact: {subject}"
        msg['From'] = gmail_user
        msg['To'] = receiver
        msg['Reply-To'] = email

        # Auto-reply to Visitor
        reply_msg = EmailMessage()
        reply_msg.set_content(f"Hi {name},\\n\\nThank you for reaching out! I have received your message regarding '{subject}' and will get back to you soon.\\n\\nBest regards,\\nKeerthi V")
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
        
    text = f"<b>New Portfolio Message</b>\\n<b>Name:</b> {name}\\n<b>Email:</b> {email}\\n<b>Subject:</b> {subject}\\n<b>Message:</b> {message}"
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
""",

    "templates/index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Keerthi V - AI/ML Engineer Portfolio">
    <meta property="og:title" content="Keerthi V | AI/ML Engineer">
    <meta property="og:description" content="AI/ML Engineering student specializing in Python, Scikit-learn, and TensorFlow.">
    <title>Keerthi V - Portfolio</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav id="navbar">
        <div class="nav-content">
            <a href="#" class="logo">Keerthi V</a>
            <ul class="nav-links">
                <li><a href="#home">Home</a></li>
                <li><a href="#about">About</a></li>
                <li><a href="#skills">Skills</a></li>
                <li><a href="#experience">Experience</a></li>
                <li><a href="#projects">Projects</a></li>
                <li><a href="#certifications">Certifications</a></li>
                <li><a href="#contact">Contact</a></li>
            </ul>
            <button id="theme-toggle" aria-label="Toggle dark/light mode">🌓</button>
            <div class="hamburger">
                <span class="bar"></span>
                <span class="bar"></span>
                <span class="bar"></span>
            </div>
        </div>
    </nav>

    <header id="home" class="hero section">
        <div class="hero-content reveal">
            <h1>Hi, I'm Keerthi V</h1>
            <h2 class="typing-container">I am a <span id="typing-text"></span><span class="cursor">|</span></h2>
            <p>AI/ML Engineer | Python | TensorFlow | Scikit-learn | NLP | Generative AI</p>
            <p class="location">📍 Bengaluru, Karnataka, India</p>
            <div class="social-links">
                <a href="https://linkedin.com/in/keerthi-v409955292" target="_blank" rel="noopener">LinkedIn</a>
                <a href="https://github.com/keerthivhx" target="_blank" rel="noopener">GitHub</a>
                <a href="{{ url_for('static', filename='resume.pdf') }}" class="btn" download>Download Resume</a>
            </div>
        </div>
    </header>

    <section id="about" class="section">
        <div class="container reveal">
            <h2>About Me</h2>
            <p>AI/ML Engineering student with hands-on experience developing, training and evaluating machine learning models using Python, Scikit-learn, TensorFlow and Keras. Skilled in data preprocessing, feature engineering and building REST APIs with Flask. Exposure to Neural Networks, NLP, Generative AI and Computer Vision. Completed 3 internships and works in Agile teams.</p>
            
            <div class="education">
                <h3>Education</h3>
                <ul>
                    <li><strong>B.E. in AI and ML</strong> - Brindavan College of Engineering, Bengaluru (Expected 2026) | CGPA: 8.55/10</li>
                    <li><strong>PUC (PCMB)</strong> - JSS PU College (2022) | 87%</li>
                </ul>
            </div>
        </div>
    </section>

    <section id="skills" class="section">
        <div class="container reveal">
            <h2>Skills</h2>
            <div class="skills-grid">
                <div class="skill-category">
                    <h3>Languages</h3>
                    <div class="chips"><span class="chip">Python</span><span class="chip">Java</span><span class="chip">C</span></div>
                </div>
                <div class="skill-category">
                    <h3>ML and DL</h3>
                    <div class="chips"><span class="chip">Scikit-learn</span><span class="chip">TensorFlow</span><span class="chip">Keras</span><span class="chip">PyTorch (familiar)</span><span class="chip">Pandas</span><span class="chip">NumPy</span><span class="chip">Matplotlib</span><span class="chip">Seaborn</span></div>
                </div>
                <div class="skill-category">
                    <h3>Algorithms</h3>
                    <div class="chips"><span class="chip">Decision Tree</span><span class="chip">Random Forest</span><span class="chip">Logistic Regression</span><span class="chip">K-Means</span><span class="chip">Neural Networks</span></div>
                </div>
                <div class="skill-category">
                    <h3>Web and APIs</h3>
                    <div class="chips"><span class="chip">Flask</span><span class="chip">REST APIs</span><span class="chip">HTML5</span><span class="chip">CSS3</span></div>
                </div>
                <div class="skill-category">
                    <h3>Data Viz</h3>
                    <div class="chips"><span class="chip">Power BI</span><span class="chip">Tableau</span><span class="chip">Excel</span></div>
                </div>
                <div class="skill-category">
                    <h3>Tools</h3>
                    <div class="chips"><span class="chip">Git</span><span class="chip">GitHub</span><span class="chip">Linux</span><span class="chip">Shell scripting</span><span class="chip">Jupyter</span><span class="chip">Google Colab</span></div>
                </div>
                <div class="skill-category">
                    <h3>Concepts</h3>
                    <div class="chips"><span class="chip">DSA</span><span class="chip">OOP</span><span class="chip">DBMS</span><span class="chip">SDLC</span><span class="chip">Agile</span></div>
                </div>
            </div>
        </div>
    </section>

    <section id="experience" class="section bg-alt">
        <div class="container reveal">
            <h2>Experience</h2>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <h3>Software Development Intern</h3>
                        <h4>Bluestock Fintech</h4>
                        <span class="date">Sept 2025 - Oct 2025</span>
                        <p>Worked in an Agile team on a Python fintech application, fixed 15+ critical production bugs, applied OOP and modular design, took part in code reviews.</p>
                    </div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <h3>Web Development Intern</h3>
                        <h4>SkillCraft Technology</h4>
                        <span class="date">Mar 2026 - Apr 2026</span>
                        <p>Built responsive, mobile-first interfaces with HTML5 and CSS3, optimised UI across screen sizes.</p>
                    </div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <h3>Python Programming Intern</h3>
                        <h4>CodSoft</h4>
                        <span class="date">Nov 2024 - Dec 2024</span>
                        <p>Built an expense tracker and automation scripts using OOP and Git.</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section id="projects" class="section">
        <div class="container reveal">
            <h2>Projects</h2>
            <div class="projects-grid">
                <div class="project-card">
                    <h3>First AI Agent</h3>
                    <p>Conversational NLP chatbot trained with TensorFlow/Keras for intent classification, served through a Flask REST API.</p>
                    <div class="tags"><span class="chip small">TensorFlow</span><span class="chip small">Flask</span><span class="chip small">NLP</span></div>
                    <a href="https://github.com/keerthivhx/First_Ai_Agent" target="_blank" class="btn small">GitHub Repo</a>
                </div>
                <div class="project-card">
                    <h3>Cancer Detection</h3>
                    <p>Supervised ML classification model with full preprocessing, EDA, hyperparameter tuning and evaluation.</p>
                    <div class="tags"><span class="chip small">Scikit-learn</span><span class="chip small">ML</span></div>
                    <a href="https://github.com/keerthivhx/Cancer_trained_data" target="_blank" class="btn small">GitHub Repo</a>
                </div>
                <div class="project-card">
                    <h3>Student Performance Prediction</h3>
                    <p>Model using Decision Tree, Random Forest and Logistic Regression with cross-validation.</p>
                    <div class="tags"><span class="chip small">Decision Tree</span><span class="chip small">Random Forest</span></div>
                    <a href="https://github.com/keerthivhx/student_perfamonce_trained_model" target="_blank" class="btn small">GitHub Repo</a>
                </div>
                <div class="project-card">
                    <h3>SkillIt</h3>
                    <p>AI career guidance system using Flask and Scikit-learn with a classification-based recommendation engine.</p>
                    <div class="tags"><span class="chip small">Flask</span><span class="chip small">Scikit-learn</span></div>
                    <span class="btn small case-study">Case Study</span>
                </div>
                <div class="project-card">
                    <h3>ClassLink</h3>
                    <p>Interactive UI application led by a 4-member Agile team.</p>
                    <div class="tags"><span class="chip small">Agile</span><span class="chip small">UI/UX</span></div>
                </div>
            </div>
        </div>
    </section>

    <section id="certifications" class="section bg-alt">
        <div class="container reveal">
            <h2>Certifications</h2>
            <ul class="cert-list">
                <li>IBM SkillsBuild AI Fundamentals</li>
                <li>Google Cloud Skills Boost (Intro to Generative AI, Intro to LLMs)</li>
                <li>Infosys Springboard (Deep Learning, NLP, Computer Vision 101, Data Science, RPA)</li>
                <li>CodSoft Python Crash Course</li>
                <li>Great Learning Python Fundamentals</li>
                <li>SAP Launchpad Program</li>
            </ul>
        </div>
    </section>

    <section id="contact" class="section">
        <div class="container reveal">
            <h2>Contact Me</h2>
            <p>Email: <a href="mailto:your_email@gmail.com">your_email@gmail.com</a> | Phone: +91 91130 44942</p>
            <div class="form-container">
                <form id="contact-form">
                    <input type="text" name="website" id="website" class="honeypot" tabindex="-1" autocomplete="off">
                    <div class="form-group">
                        <label for="name">Name</label>
                        <input type="text" id="name" name="name" required>
                    </div>
                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="subject">Subject</label>
                        <input type="text" id="subject" name="subject" required>
                    </div>
                    <div class="form-group">
                        <label for="message">Message</label>
                        <textarea id="message" name="message" rows="5" minlength="10" maxlength="2000" required></textarea>
                    </div>
                    <button type="submit" id="submit-btn">
                        <span class="btn-text">Send Message</span>
                        <span class="spinner hidden"></span>
                    </button>
                    <div id="form-feedback" class="hidden"></div>
                </form>
            </div>
        </div>
    </section>

    <footer>
        <p>&copy; 2026 Keerthi V. Built with Flask & Vanilla JS.</p>
    </footer>

    <script src="{{ url_for('static', filename='js/script.js') }}"></script>
</body>
</html>
""",

    "templates/admin_login.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Admin Login - Keerthi V</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <style>
        .login-container { max-width: 400px; margin: 100px auto; padding: 2rem; background: var(--bg-alt); border-radius: 8px; }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>Admin Login</h2>
        {% if error %}
        <p style="color: var(--error-color);">{{ error }}</p>
        {% endif %}
        <form method="POST">
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit" class="btn">Login</button>
        </form>
    </div>
</body>
</html>""",

    "templates/admin.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Admin Dashboard - Keerthi V</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <style>
        .dashboard { padding: 2rem; max-width: 1200px; margin: 0 auto; }
        .msg-card { background: var(--bg-alt); padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid var(--primary-color); }
        .msg-card.read { border-left-color: var(--text-muted); opacity: 0.8; }
        .meta { font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1rem; }
    </style>
</head>
<body>
    <nav id="navbar" style="position: static;">
        <div class="nav-content">
            <span class="logo">Admin Dashboard</span>
            <a href="{{ url_for('logout') }}" class="btn small">Logout</a>
        </div>
    </nav>
    <div class="dashboard">
        <h2>Messages Inbox</h2>
        {% for msg in messages %}
        <div class="msg-card {% if msg['is_read'] %}read{% endif %}" id="msg-{{ msg['id'] }}">
            <h3>{{ msg['subject'] }}</h3>
            <div class="meta">
                From: {{ msg['name'] }} ({{ msg['email'] }}) | IP: {{ msg['ip'] }} | Date: {{ msg['created_at'] }} <br>
                Status: Email {% if msg['email_sent'] %}✅{% else %}❌{% endif %} | Telegram {% if msg['telegram_sent'] %}✅{% else %}❌{% endif %}
            </div>
            <p>{{ msg['message'] }}</p>
            {% if not msg['is_read'] %}
            <button onclick="markRead({{ msg['id'] }})" class="btn small">Mark as Read</button>
            {% endif %}
        </div>
        {% else %}
        <p>No messages found.</p>
        {% endfor %}
    </div>
    <script>
        function markRead(id) {
            fetch(`/admin/mark_read/${id}`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                }
            });
        }
    </script>
</body>
</html>""",

    "static/css/style.css": """:root {
    --bg-color: #121212;
    --bg-alt: #1e1e1e;
    --text-color: #e0e0e0;
    --text-muted: #a0a0a0;
    --primary-color: #00ff88;
    --primary-hover: #00cc6a;
    --card-bg: #2a2a2a;
    --error-color: #ff5555;
    --success-color: #55ff55;
    --nav-bg: rgba(18, 18, 18, 0.95);
    transition: background-color 0.3s, color 0.3s;
}

[data-theme="light"] {
    --bg-color: #f5f5f5;
    --bg-alt: #ffffff;
    --text-color: #333333;
    --text-muted: #666666;
    --primary-color: #0077ff;
    --primary-hover: #0055cc;
    --card-bg: #ffffff;
    --nav-bg: rgba(255, 255, 255, 0.95);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background-color: var(--bg-color);
    color: var(--text-color);
    line-height: 1.6;
    overflow-x: hidden;
}

/* Typography */
h1, h2, h3, h4 { color: var(--text-color); margin-bottom: 1rem; }
a { color: var(--primary-color); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Navbar */
#navbar {
    position: fixed;
    top: 0; width: 100%;
    background: var(--nav-bg);
    backdrop-filter: blur(10px);
    z-index: 1000;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}
.nav-content {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
}
.logo { font-size: 1.5rem; font-weight: bold; text-decoration: none; color: var(--text-color); }
.logo:hover { text-decoration: none; }
.nav-links { list-style: none; display: flex; gap: 1.5rem; }
.nav-links a { color: var(--text-color); font-weight: 500; }
.nav-links a:hover { color: var(--primary-color); text-decoration: none; }

#theme-toggle {
    background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-color);
}

.hamburger { display: none; cursor: pointer; }
.bar { display: block; width: 25px; height: 3px; margin: 5px auto; background-color: var(--text-color); transition: all 0.3s; }

/* Sections */
.section { padding: 80px 20px; }
.bg-alt { background-color: var(--bg-alt); }
.container { max-width: 1000px; margin: 0 auto; }

/* Hero */
.hero {
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
}
.hero h1 { font-size: 3rem; margin-bottom: 0.5rem; }
.typing-container { font-size: 1.5rem; color: var(--primary-color); margin-bottom: 1rem; }
.cursor { animation: blink 0.7s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.social-links { margin-top: 2rem; display: flex; gap: 1rem; justify-content: center; align-items: center; }

/* Buttons */
.btn {
    display: inline-block; padding: 0.8rem 1.5rem;
    background: var(--primary-color); color: #fff;
    border: none; border-radius: 4px; font-weight: bold;
    cursor: pointer; transition: background 0.3s;
}
.btn.small { padding: 0.4rem 0.8rem; font-size: 0.9rem; }
.btn:hover { background: var(--primary-hover); text-decoration: none; }
[data-theme="light"] .btn { color: #fff; }

/* Skills */
.skills-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; }
.skill-category { background: var(--card-bg); padding: 1.5rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
.chips { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.chip { background: var(--primary-color); color: #121212; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.9rem; font-weight: 500; }
.chip.small { font-size: 0.8rem; padding: 0.2rem 0.6rem; }
[data-theme="light"] .chip { color: #fff; }

/* Experience Timeline */
.timeline { position: relative; border-left: 2px solid var(--primary-color); padding-left: 20px; margin-left: 10px; }
.timeline-item { margin-bottom: 2rem; position: relative; }
.timeline-dot {
    position: absolute; left: -26px; top: 0;
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--primary-color);
}
.date { display: block; font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.5rem; }

/* Projects */
.projects-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
.project-card {
    background: var(--card-bg); padding: 1.5rem; border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    transition: transform 0.3s, box-shadow 0.3s;
}
.project-card:hover { transform: translateY(-5px); box-shadow: 0 8px 15px rgba(0,0,0,0.2); }
.tags { margin: 1rem 0; }
.case-study { background: var(--text-muted); color: #fff; cursor: default; }

/* Certifications */
.cert-list { list-style-position: inside; }
.cert-list li { margin-bottom: 0.5rem; }

/* Form */
.form-container { background: var(--card-bg); padding: 2rem; border-radius: 8px; }
.form-group { margin-bottom: 1rem; }
label { display: block; margin-bottom: 0.5rem; }
input, textarea {
    width: 100%; padding: 0.8rem;
    background: var(--bg-color); color: var(--text-color);
    border: 1px solid var(--text-muted); border-radius: 4px;
}
input:focus, textarea:focus { outline: none; border-color: var(--primary-color); }
.honeypot { display: none; }
button[type="submit"] { width: 100%; display: flex; justify-content: center; align-items: center; }
.spinner {
    border: 3px solid rgba(255,255,255,0.3); border-radius: 50%;
    border-top: 3px solid #fff; width: 20px; height: 20px;
    animation: spin 1s linear infinite; margin-left: 10px;
}
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.hidden { display: none !important; }
#form-feedback { margin-top: 1rem; padding: 1rem; border-radius: 4px; text-align: center; }
.feedback-success { background: rgba(85, 255, 85, 0.2); color: var(--success-color); }
.feedback-error { background: rgba(255, 85, 85, 0.2); color: var(--error-color); }

/* Reveal Animations */
.reveal { opacity: 0; transform: translateY(30px); transition: all 0.8s ease; }
.reveal.active { opacity: 1; transform: translateY(0); }

/* Mobile Responsive */
@media (max-width: 768px) {
    .nav-links {
        position: fixed; left: -100%; top: 60px;
        flex-direction: column; background: var(--nav-bg);
        width: 100%; text-align: center; transition: 0.3s;
        padding: 2rem 0; box-shadow: 0 10px 10px rgba(0,0,0,0.1);
    }
    .nav-links.active { left: 0; }
    .hamburger { display: block; }
    .hamburger.active .bar:nth-child(2) { opacity: 0; }
    .hamburger.active .bar:nth-child(1) { transform: translateY(8px) rotate(45deg); }
    .hamburger.active .bar:nth-child(3) { transform: translateY(-8px) rotate(-45deg); }
}
""",

    "static/js/script.js": """document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle
    const themeToggle = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);

    themeToggle.addEventListener('click', () => {
        let theme = document.documentElement.getAttribute('data-theme');
        let newTheme = theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    });

    // Mobile Menu
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');
    const navItems = document.querySelectorAll('.nav-links a');

    hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navLinks.classList.toggle('active');
    });

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            hamburger.classList.remove('active');
            navLinks.classList.remove('active');
        });
    });

    // Typing Animation
    const texts = ["AI/ML Engineer", "Python Developer", "Problem Solver"];
    let textIndex = 0;
    let charIndex = 0;
    let isDeleting = false;
    const typingElement = document.getElementById('typing-text');

    function type() {
        const currentText = texts[textIndex];
        
        if (isDeleting) {
            typingElement.textContent = currentText.substring(0, charIndex - 1);
            charIndex--;
        } else {
            typingElement.textContent = currentText.substring(0, charIndex + 1);
            charIndex++;
        }

        let typeSpeed = isDeleting ? 50 : 100;

        if (!isDeleting && charIndex === currentText.length) {
            typeSpeed = 2000;
            isDeleting = true;
        } else if (isDeleting && charIndex === 0) {
            isDeleting = false;
            textIndex = (textIndex + 1) % texts.length;
            typeSpeed = 500;
        }

        setTimeout(type, typeSpeed);
    }
    
    if (typingElement) {
        setTimeout(type, 1000);
    }

    // Scroll Reveal
    const reveals = document.querySelectorAll('.reveal');
    function checkReveal() {
        const windowHeight = window.innerHeight;
        const elementVisible = 100;

        reveals.forEach(reveal => {
            const elementTop = reveal.getBoundingClientRect().top;
            if (elementTop < windowHeight - elementVisible) {
                reveal.classList.add('active');
            }
        });
    }
    window.addEventListener('scroll', checkReveal);
    checkReveal(); // Check on load

    // Smooth scroll for nav links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Form Submit
    const contactForm = document.getElementById('contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = document.getElementById('submit-btn');
            const btnText = submitBtn.querySelector('.btn-text');
            const spinner = submitBtn.querySelector('.spinner');
            const feedback = document.getElementById('form-feedback');
            
            // UI pending state
            submitBtn.disabled = true;
            btnText.textContent = 'Sending...';
            spinner.classList.remove('hidden');
            feedback.classList.add('hidden');
            feedback.className = '';
            
            const formData = new FormData(contactForm);
            const data = Object.fromEntries(formData.entries());
            
            try {
                const response = await fetch('/api/contact', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                feedback.classList.remove('hidden');
                if (response.ok) {
                    feedback.textContent = result.message || 'Message sent successfully!';
                    feedback.classList.add('feedback-success');
                    contactForm.reset();
                } else {
                    feedback.textContent = result.error || 'Failed to send message.';
                    feedback.classList.add('feedback-error');
                }
            } catch (error) {
                feedback.classList.remove('hidden');
                feedback.textContent = 'Network error. Please try again later.';
                feedback.classList.add('feedback-error');
            } finally {
                submitBtn.disabled = false;
                btnText.textContent = 'Send Message';
                spinner.classList.add('hidden');
            }
        });
    }
});
"""
}

# Create directories
os.makedirs(os.path.join(base_dir, "templates"), exist_ok=True)
os.makedirs(os.path.join(base_dir, "static", "css"), exist_ok=True)
os.makedirs(os.path.join(base_dir, "static", "js"), exist_ok=True)
os.makedirs(os.path.join(base_dir, "static", "images"), exist_ok=True)

# Write empty dummy pdf
with open(os.path.join(base_dir, "static", "resume.pdf"), "w") as f:
    f.write("Dummy PDF content")

# Write all files
for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Project generation complete.")
