from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
import os
import re

app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///otp_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# বাংলাদেশ সময় (GMT+6)
BD_TZ = timezone(timedelta(hours=6))

def get_bd_time():
    return datetime.now(BD_TZ).strftime("%Y-%m-%d %I:%M:%S %p")

# Database Model
class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=True)      # প্রেরক (যে নম্বর থেকে এসএমএস এসেছে)
    target = db.Column(db.String(50), nullable=True)      # প্রাপক (যে নম্বরে এসএমএস গিয়েছে)
    otp_code = db.Column(db.String(20), nullable=True)
    arrival_time = db.Column(db.String(50), nullable=True)
    raw_message = db.Column(db.Text, nullable=True)

# টেবিল তৈরি
with app.app_context():
    db.create_all()
    print("✅ Database created!")

@app.route('/')
def index():
    return render_template('index.html')

def convert_word_otp_to_number(text):
    """Four-Eight-Seven-Eight-Zero-Zero -> 487800"""
    word_map = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'ZERO': '0', 'ONE': '1', 'TWO': '2', 'THREE': '3', 'FOUR': '4',
        'FIVE': '5', 'SIX': '6', 'SEVEN': '7', 'EIGHT': '8', 'NINE': '9'
    }
    
    # প্যাটার্ন: Four-Eight-Seven-Eight-Zero-Zero বা Seven-Five-One-Six-Seven-Four
    pattern = r'(?:[A-Za-z]+-?){4,}'
    matches = re.findall(pattern, text)
    
    for match in matches:
        parts = match.split('-')
        number = ''
        for part in parts:
            part_clean = part.strip()
            if part_clean.lower() in word_map:
                number += word_map[part_clean.lower()]
        if len(number) >= 4:
            return number
    return None

@app.route('/api/receive', methods=['POST'])
def receive_otp():
    # JSON ডাটা পার্স করা
    if request.is_json:
        data = request.json
        sender = data.get('sender') or data.get('mobile_number') or data.get('from')
        target = data.get('target') or data.get('to')
        message = data.get('otp_code') or data.get('content') or data.get('message')
    else:
        sender = request.form.get('sender') or request.form.get('mobile_number') or request.form.get('from')
        target = request.form.get('target') or request.form.get('to')
        message = request.form.get('otp_code') or request.form.get('content') or request.form.get('message')
    
    # OTP রূপান্তর (শব্দ থেকে সংখ্যায়)
    otp_number = convert_word_otp_to_number(message) if message else None
    
    # যদি OTP না পাওয়া যায়, তাহলে পুরো মেসেজের সংখ্যা খোঁজা
    if not otp_number and message:
        numeric_otp = re.search(r'\b\d{4,6}\b', message)
        if numeric_otp:
            otp_number = numeric_otp.group()
    
    # ডিফল্ট মান নির্ধারণ
    final_sender = sender if sender else 'Unknown'
    final_target = target if target else 'Unknown'
    bd_time = datetime.now(BD_TZ).strftime("%Y-%m-%d %I:%M:%S %p")
    
    # ডাটাবেসে সেভ করা
    new_otp = OTP(
        sender=final_sender,
        target=final_target,
        otp_code=otp_number or 'Not found',
        arrival_time=bd_time,
        raw_message=message
    )
    db.session.add(new_otp)
    db.session.commit()
    
    # লগে দেখানো
    print(f"📤 Sender: {final_sender}")
    print(f"📥 Target: {final_target}")
    print(f"🔢 OTP: {otp_number}")
    print(f"⏰ Time: {bd_time}")
    print("---")
    
    return jsonify({
        "status": "success", 
        "sender": final_sender,
        "target": final_target,
        "otp": otp_number,
        "time": bd_time
    }), 200

@app.route('/api/get_otps', methods=['GET'])
def get_otps():
    otps = OTP.query.order_by(OTP.id.desc()).all()
    output = []
    for otp in otps:
        output.append({
            "id": otp.id,
            "sender": otp.sender,
            "target": otp.target,
            "otp_code": otp.otp_code,
            "arrival_time": otp.arrival_time
        })
    return jsonify(output)

@app.route('/api/delete/<int:id>', methods=['DELETE'])
def delete_otp(id):
    otp = OTP.query.get(id)
    if otp:
        db.session.delete(otp)
        db.session.commit()
        return jsonify({"status": "deleted"}), 200
    return jsonify({"status": "not found"}), 404

@app.route('/api/delete_all', methods=['DELETE'])
def delete_all():
    db.session.query(OTP).delete()
    db.session.commit()
    return jsonify({"status": "all deleted"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
