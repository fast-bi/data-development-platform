import os
import traceback
import logging
import requests
import subprocess
import sqlite3
import contextlib
import re
from flask import Flask, request, render_template, jsonify, session, current_app, redirect, flash, url_for
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.config import Config
from app.create_database import setup_database
from app.utils import set_user_status, login_required, set_session, get_user_status, DB_PATH
from datetime import datetime, timedelta
from functools import wraps
from utils.mail_handler import MailSender
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired

logger = logging.getLogger(__name__)

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

def get_external_ip():
    try:
        response = requests.get('https://api.ipify.org')
        return response.text
    except requests.RequestException:
        return None

def check_user_session():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' in session:
                username = session['username']
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT status, last_activity FROM users WHERE username = ?', (username,))
                    result = cursor.fetchone()
                    if result:
                        status, last_activity = result
                        if status == 'active':
                            last_activity_time = datetime.fromisoformat(last_activity)
                            if datetime.utcnow() - last_activity_time > timedelta(hours=3):
                                set_user_status(username, 'passive')
                                session.clear()
                                flash('Your session has expired due to inactivity.', 'info')
                                return redirect(url_for('app_frontend_bp.login'))
                            else:
                                cursor.execute('UPDATE users SET last_activity = ? WHERE username = ?', 
                                            (datetime.utcnow().isoformat(), username))
                                conn.commit()
                        elif status != 'active':
                            session.clear()
                            flash('Your session is no longer active.', 'info')
                            return redirect(url_for('app_frontend_bp.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def auth_and_session_check():
    def decorator(f):
        @wraps(f)
        @login_required
        @check_user_session()
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def setup_frontend_routes(bp, limiter):

    setup_database()
    mail_sender = MailSender()

    def get_active_user():
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT username FROM users WHERE status = "active"')
            result = cursor.fetchone()
            return result[0] if result else None

    def set_user_status(username, status):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET status = ? WHERE username = ?', (status, username))
            conn.commit()

    def login_user(username):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('BEGIN EXCLUSIVE TRANSACTION')
            try:
                # Check if there's any active user
                cursor.execute('SELECT username FROM users WHERE status = "active"')
                active_user = cursor.fetchone()
                if active_user:
                    if active_user[0] != username:
                        conn.rollback()
                        return False, "Another user is currently active."
                
                # Update the user's status to active
                cursor.execute('UPDATE users SET status = "active", last_activity = ? WHERE username = ?', 
                            (datetime.utcnow().isoformat(), username))
                conn.commit()
                return True, None
            except sqlite3.Error as e:
                conn.rollback()
                current_app.logger.error(f"Database error in login_user: {e}")
                return False, "An error occurred. Please try again later."

    @bp.route('/wizard', methods=['GET', 'POST'])
    #@csrf.exempt
    @auth_and_session_check()
    def tenant_wizard():
        bearer_auth = current_app.config['SECRET_KEY']
        metadata_collector = current_app.metadata_collector

        # Get the latest versions
        versions = metadata_collector.get_latest_versions()

        # Process versions for display, for system_infra_services
        system_infra_services = []
        if versions and 'system_infra_services' in versions:
            for service_name, service_data in versions['system_infra_services'].items():
                system_infra_services.append({
                    'name': service_name,
                    'versions': service_data['versions']
                })

        # Process versions for display, for data_services and fastbi_data_services
        data_fastbi_data_services = []
        if versions:
            if 'data_services' in versions:
                for service_name, service_data in versions['data_services'].items():
                    data_fastbi_data_services.append({
                        'name': service_name,
                        'versions': service_data['versions'],
                        'category': 'data_services'
                    })
            if 'fastbi_data_services' in versions:
                for service_name, service_data in versions['fastbi_data_services'].items():
                    data_fastbi_data_services.append({
                        'name': service_name,
                        'versions': service_data['versions'],
                        'category': 'fastbi_data_services'
                    })

        external_ip = get_external_ip()

        return render_template('wizard.html', 
                            bearer_auth=bearer_auth, 
                            system_infra_services=system_infra_services,
                            data_fastbi_data_services=data_fastbi_data_services,
                            external_ip = external_ip,
                            username=session.get('username'))
    
    @bp.route('/about', methods=['GET'])
    #@csrf.exempt
    @auth_and_session_check()
    def about():
        bearer_auth = current_app.config['SECRET_KEY']
        return render_template('about.html', username=session.get('username'), bearer_auth=bearer_auth)
    
    @bp.route('/contacts', methods=['GET'])
    #@csrf.exempt
    @auth_and_session_check()
    def contacts():
        bearer_auth = current_app.config['SECRET_KEY']
        return render_template('contacts.html', username=session.get('username'), bearer_auth=bearer_auth)
    
    @bp.route('/')
    #@csrf.exempt
    @auth_and_session_check()
    def index():
        bearer_auth = current_app.config['SECRET_KEY']
        return render_template('index.html', username=session.get('username'), bearer_auth=bearer_auth)

    @bp.route('/logout')
    #@csrf.exempt
    @auth_and_session_check()
    def logout():
        username = session.get('username')
        if username:
            set_user_status(username, 'logoff')
        session.clear()
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('app_frontend_bp.login'))

    @bp.route('/login', methods=['GET', 'POST'])
    @limiter.limit("5 per minute")
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data
            remember_me = form.remember_me.data

            # Check if username is valid
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                flash('Invalid username format', 'error')
                return render_template('login.html', form=form)

            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT username, password, email, status FROM users WHERE username = ?', (username,))
                    account = cursor.fetchone()

                if not account:
                    flash('Username does not exist', 'error')
                    return render_template('login.html', form=form)

                try:
                    ph = PasswordHasher()
                    ph.verify(account[1], password)
                except VerifyMismatchError:
                    flash('Incorrect password', 'error')
                    return render_template('login.html', form=form)

                success, message = login_user(username)
                if not success:
                    flash(message, 'error')
                    return render_template('login.html', form=form)

                session['username'] = username
                session['email'] = account[2]
                if remember_me:
                    session.permanent = True  # Use this if you want to implement "remember me" functionality
                flash('Login successful!', 'success')
                return redirect(url_for('app_frontend_bp.index'))

            except sqlite3.Error as e:
                current_app.logger.error(f"Database error: {e}")
                flash('An error occurred. Please try again later.', 'error')
                return render_template('login.html', form=form)
            except Exception as e:
                current_app.logger.error(f"Unexpected error in login: {e}")
                flash('An unexpected error occurred. Please try again later.', 'error')
                return render_template('login.html', form=form)

        return render_template('login.html', form=form)


    @bp.route('/register', methods=['GET', 'POST'])
    #@csrf.exempt
    def register():
        frontend_register = current_app.config['FRONTEND_REGISTER']
        
        # Convert the string value to a boolean
        is_registration_enabled = frontend_register.lower() == 'true'
        
        if not is_registration_enabled:
            return render_template('register_disabled.html')
        
        if request.method == 'GET':
            return render_template('register.html')
        
        try:
            # Store data to variables 
            password = request.form.get('password')
            confirm_password = request.form.get('confirm-password')
            username = request.form.get('username')
            email = request.form.get('email')

            # Verify data
            if len(password) < 8:
                flash('Your password must be 8 or more characters', 'error')
                return render_template('register.html')
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('register.html')
            if not re.match(r'^[a-zA-Z0-9]+$', username):
                flash('Username must only be letters and numbers', 'error')
                return render_template('register.html')
            if not 3 < len(username) < 26:
                flash('Username must be between 4 and 25 characters', 'error')
                return render_template('register.html')

            # Check if username already exists
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
                if cursor.fetchone():
                    flash('Username already exists', 'error')
                    return render_template('register.html')

            # Create password hash
            pw = PasswordHasher()
            hashed_password = pw.hash(password)

            # Insert new user
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                            (username, hashed_password, email))
                conn.commit()

            # Log the user in
            set_session(username=username, email=email)
            flash('Registration successful! You are now logged in.', 'success')
            return redirect(url_for('app_frontend_bp.index'))

        except sqlite3.Error as e:
            current_app.logger.error(f"Database error during registration: {e}")
            flash('An error occurred during registration. Please try again later.', 'error')
            return render_template('register.html')
        except Exception as e:
            current_app.logger.error(f"Unexpected error during registration: {e}")
            flash('An unexpected error occurred. Please try again later.', 'error')
            return render_template('register.html')
        
    @bp.record_once
    def on_register(state):
        mail_sender.init_app(state.app)

    @bp.route('/send_email', methods=['POST'])
    #@csrf.exempt
    @auth_and_session_check()
    def send_email():
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        html_body = f"""
        <h3>New message from {name}</h3>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Subject:</strong> {subject}</p>
        <p><strong>Message:</strong></p>
        <p>{message}</p>
        """

        subject = f"New Contact Form Submission: {subject}"
        recipient = "support@fast.bi"

        result = mail_sender.send_email(subject, html_body, recipient)

        if "successfully" in result:
            return jsonify({"status": "success", "message": "Email sent successfully"})
        else:
            logger.error(result)
            return jsonify({"status": "error", "message": "Failed to send email. Please try again later."}), 500
