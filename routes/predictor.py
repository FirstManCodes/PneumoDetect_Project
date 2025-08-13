import os
import numpy as np
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

predictor = Blueprint('predictor', __name__)

# Load the trained model
MODEL_PATH = 'pneumonia_model.h5'
model = load_model(MODEL_PATH)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@predictor.route('/predict', methods=['GET', 'POST'])
def predict():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            img = image.load_img(filepath, target_size=(150, 150))
            img_array = image.img_to_array(img) / 255.0
            img_array = np.expand_dims(img_array, axis=0)

            prediction = model.predict(img_array)[0][0]
            label = "Pneumonia" if prediction > 0.5 else "Normal"
            confidence = float(prediction if prediction > 0.5 else 1 - prediction)

            return render_template("predict.html", result=label, confidence=round(confidence * 100, 2), image_path=filepath)

        else:
            flash('Allowed image types are -> png, jpg, jpeg')
            return redirect(request.url)

    return render_template("predict.html")
