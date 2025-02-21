import subprocess
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.utils import secure_filename
import os
import moviepy.editor as mp
import speech_recognition as sr
import sqlite3
from googletrans import Translator

# Install necessary packages
subprocess.run(["pip", "install", "Flask", "moviepy", "SpeechRecognition", "googletrans==4.0.0-rc1"])

class VideoSummarizerApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'your_secret_key_here'  # Change this to a secure secret key
        self.app.config['UPLOAD_FOLDER'] = 'uploads'
        self.app.config['OUTPUT_FOLDER'] = 'outputs'
        os.makedirs(self.app.config['OUTPUT_FOLDER'], exist_ok=True)
        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)
        self.setup_routes()
        self.setup_database()

    def setup_routes(self):
        self.app.route('/')(self.login)  # Direct '/' route to login page
        self.app.route('/index')(self.index)  # '/index' route for the main page
        self.app.route('/summarize', methods=['POST'])(self.summarize)
        self.app.route('/login', methods=['GET', 'POST'])(self.login)
        self.app.route('/logout')(self.logout)
        self.app.route('/signup', methods=['GET', 'POST'])(self.signup)
        self.app.route('/contact')(self.contact)
        self.app.route('/contact', methods=['POST'])(self.handle_contact)
        self.app.route('/about')(self.about)
        self.app.route('/about', methods=['POST'])(self.handle_about)

    def setup_database(self):
        self.app.before_request(self.before_request)

    def before_request(self):
        g.conn = sqlite3.connect('database.db')
        g.cursor = g.conn.cursor()
        g.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')

    def run(self):
        self.app.run(debug=True)

    def index(self):
        if 'username' in session:
            return render_template('index.html', username=session['username'])
        return redirect(url_for('login'))

    def summarize(self):
        if 'username' not in session:
            return redirect(url_for('login'))

        video_file = request.files['videoFile']
        summary = ''

        if video_file:
            video_filename = secure_filename(video_file.filename)
            video_path = os.path.join(self.app.config['UPLOAD_FOLDER'], video_filename)
            video_file.save(video_path)

            try:
                if video_filename.endswith('.mp4'):
                    language = request.form.get('language')
                    if language == 'english':
                        # English video summarization
                        video = mp.VideoFileClip(video_path)
                        audio_file = video.audio
                        audio_file.write_audiofile("temp.wav")
                        r = sr.Recognizer()

                        with sr.AudioFile("temp.wav") as source:
                            data = r.record(source)

                        english_text = r.recognize_google(data, language="en-US")  # Recognize English speech
                        summary = english_text  # Store the recognized English speech as the summary
                    elif language == 'urdu':
                        # Urdu video summarization
                        video = mp.VideoFileClip(video_path)
                        audio_file = video.audio
                        audio_file.write_audiofile("temp.wav")
                        r = sr.Recognizer()

                        with sr.AudioFile("temp.wav") as source:
                            data = r.record(source)

                        urdu_text = r.recognize_google(data, language="ur-PK")  # Recognize Urdu speech
                        summary = urdu_text  # Store the recognized Urdu speech as the summary

                    print(summary, ":SUMMARY")

            except Exception as e:
                # Handle exceptions, print or log the error
                print(f"Error: {e}")

        return render_template('index.html', username=session['username'], summary=summary)

    def login(self):
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = self.get_user(username, password)
            if user:
                session['username'] = username
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password', 'error')
        return render_template('login.html')

    def get_user(self, username, password):
        g.cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        return g.cursor.fetchone()

    def signup(self):
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if self.create_user(username, password):
                flash('Account created successfully', 'success')
                return redirect(url_for('login'))
            else:
                flash('Username already exists', 'error')
        return render_template('signup.html')

    def create_user(self, username, password):
        try:
            g.cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            g.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def logout(self):
        session.pop('username', None)
        return redirect(url_for('login'))

    def contact(self):
        return render_template('contact.html')

    def handle_contact(self):
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            message = request.form['message']
            # Process the message, send email, store in database, etc.
            flash('Your message has been sent!', 'success')
        return redirect(url_for('contact'))

    def about(self):
        # Example about method
        return render_template('about.html')

    def handle_about(self):
        # Example handle_about method
        pass

if __name__ == '__main__':
    app_instance = VideoSummarizerApp()
    app_instance.run()
