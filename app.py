from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import re

app = Flask(__name__)

# Database Configuration - SQLite ব্যবহার করছি (সহজ ও নির্ভরযোগ্য)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///otp_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Model
class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target = db.Column(db.String(20), nullable=True)  # nullable True করলাম
    sender = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.String(50), default=lambda: datetime.now().strftime("%I:%M:%S %p"))

# টেবিল তৈরি করা (এটা নিশ্চিত করবে যে টেবিল আছে)
with app.app_context():
    db.create_all()
    print("✅ Database and tables created successfully!")

@app.route('/')
def index():
    return render_template('index.html')

# OTP শব্দ থেকে সংখ্যায় রূপান্তরের ফাংশন
def convert_word_otp_to_number(text):
    """Four-Eight-Seven-Eight-Zero-Zero -> 487800"""
    word_map = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'ZERO': '0', 'ONE': '1', 'TWO': '2', 'THREE': '3', 'FOUR': '4',
        'FIVE': '5', 'SIX': '6', 'SEVEN': '7', 'EIGHT': '8', 'NINE': '9'
    }
    
    # প্যাটার্ন: Four-Eight-Seven-Eight-Zero-Zero
    pattern = r'(?:[A-Z][a-z]+-?){4,}'
    match = re.findall(pattern, text)
    
    for m in match:
        parts = m.split('-')
        number = ''
        for part in parts:
            if part in word_map:
                number += word_map[part]
        if len(number) >= 4:
            return number
    return None

# API to receive OTP from SmsForwarder
@app.route('/api/receive', methods=['POST', 'GET'])
def receive_otp():
    # JSON body থেকে ডাটা নেওয়া
    if request.is_json:
        data = request.json
        sender = data.get('mobile_number') or data.get('from') or data.get('sender')
        message = data.get('otp_code') or data.get('content') or data.get('message')
        timestamp = data.get('arrival_time') or data.get('timestamp')
    else:
        # Form data থেকে নেওয়া
        sender = request.form.get('mobile_number') or request.form.get('from') or request.form.get('sender')
        message = request.form.get('otp_code') or request.form.get('content') or request.form.get('message')
        timestamp = request.form.get('arrival_time') or request.form.get('timestamp')
    
    # যদি message এ শব্দের OTP থাকে, তাহলে সংখ্যায় রূপান্তর
    converted_otp = convert_word_otp_to_number(message) if message else None
    
    # ডাটাবেসে সেভ করা
    new_otp = OTP(
        target=converted_otp,  # রূপান্তরিত OTP সংখ্যা
        sender=sender or 'Unknown',
        message=message or 'No message',
        timestamp=datetime.now().strftime("%I:%M:%S %p")
    )
    db.session.add(new_otp)
    db.session.commit()
    
    print(f"✅ Received: {sender} -> OTP: {converted_otp}")
    
    return jsonify({"status": "success", "otp": converted_otp}), 200

# API to get all OTPs for Dashboard
@app.route('/api/get_otps', methods=['GET'])
def get_otps():
    otps = OTP.query.order_by(OTP.id.desc()).all()
    output = []
    for otp in otps:
        output.append({
            "id": otp.id,
            "target": otp.target,
            "sender": otp.sender,
            "message": otp.message,
            "timestamp": otp.timestamp
        })
    return jsonify(output)

# API to delete single OTP
@app.route('/api/delete/<int:id>', methods=['DELETE'])
def delete_otp(id):
    otp = OTP.query.get(id)
    if otp:
        db.session.delete(otp)
        db.session.commit()
        return jsonify({"status": "deleted"}), 200
    return jsonify({"status": "not found"}), 404

# API to delete all OTPs
@app.route('/api/delete_all', methods=['DELETE'])
def delete_all():
    db.session.query(OTP).delete()
    db.session.commit()
    return jsonify({"status": "all deleted"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
