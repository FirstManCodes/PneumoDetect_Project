from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
import os
import sqlite3
import uuid
from datetime import datetime
import tensorflow as tf
import numpy as np
from PIL import Image

# Flask app configuration
app = Flask(__name__)
app.secret_key = "your_secret_key"
UPLOAD_FOLDER = "static/uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

# Load PneumoDetect Model
MODEL_PATH = r"C:\Users\LENOVO\Downloads\archive Pneumonia Kaggle Data Extract\pneumonia_app\model\pneumonia_model.h5"
model = tf.keras.models.load_model(MODEL_PATH)

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Database setup ---
def init_db():
    conn = sqlite3.connect("pneumodetect.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        filename TEXT,
        prediction TEXT,
        confidence REAL,
        upload_time TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# --- Utility functions ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def predict_image(image_path):
    img = Image.open(image_path).convert('RGB')
    img = img.resize((224, 224))
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    prediction = model.predict(img_array)[0][0]
    confidence = float(prediction) if prediction > 0.5 else 1 - float(prediction)
    label = "Pneumonia" if prediction > 0.5 else "Normal"
    return label, round(confidence * 100, 2)

# --- Routes ---
@app.route('/')
def home():
    return render_template('home.html')

@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(str(uuid.uuid4()) + "_" + file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            label, confidence = predict_image(filepath)

            # Save to history if logged in
            if 'user_id' in session:
                conn = sqlite3.connect("pneumodetect.db")
                c = conn.cursor()
                c.execute("INSERT INTO history (user_id, filename, prediction, confidence, upload_time) VALUES (?, ?, ?, ?, ?)",
                          (session['user_id'], filename, label, confidence, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()

            return render_template('results.html', filename=filename, prediction=label, confidence=confidence)

        else:
            flash('Invalid file type', 'danger')
            return redirect(request.url)

    return render_template('predict.html')

@app.route('/history')
def history():
    if 'user_id' not in session:
        flash('Please log in to view your history', 'warning')
        return redirect(url_for('login'))

    conn = sqlite3.connect("pneumodetect.db")
    c = conn.cursor()
    c.execute("SELECT id, filename, prediction, confidence, upload_time FROM history WHERE user_id = ?", (session['user_id'],))
    records = c.fetchall()
    conn.close()
    return render_template('history.html', records=records)

@app.route('/view_result/<int:record_id>')
def view_result(record_id):
    conn = sqlite3.connect("pneumodetect.db")
    c = conn.cursor()
    c.execute("SELECT filename, prediction, confidence, upload_time FROM history WHERE id = ?", (record_id,))
    record = c.fetchone()
    conn.close()
    if record:
        return render_template('view_result.html', filename=record[0], prediction=record[1], confidence=record[2], upload_time=record[3])
    else:
        return render_template('404.html'), 404

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to view dashboard', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- Authentication ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("pneumodetect.db")
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            flash('Login successful', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("pneumodetect.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        finally:
            conn.close()

    return render_template('register.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# --- Main run ---
if __name__ == '__main__':
    app.run(debug=True)
