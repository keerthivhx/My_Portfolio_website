# Keerthi V - Personal Portfolio

A production-ready personal portfolio website built with HTML5, CSS3, Vanilla JS, and Flask.

## Features
- Modern Dark/Light theme toggle
- Real-time contact form with SQLite backup, Email, and Telegram notifications
- Secure Admin Inbox
- Responsive, mobile-first design

## Setup & Run Locally
1. Create a virtual environment: `python -m venv venv`
2. Activate it: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
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

> **Note**: Drop your PDF resume inside the `static/` folder and name it `resume.pdf`.