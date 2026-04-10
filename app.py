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
    """বর্তমান বাংলাদেশ সময় রিটার্ন করে"""
    return datetime.now(BD_TZ).strftime("%Y-%m-%d %I:%M:%S %p")

# Database Model
class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mobile_number = db.Column(db.String(50), nullable=True)
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

def extract_mobile_number(text):
    """SMS থেকে মোবাইল নম্বর বের করা"""
    # 8801XXXXXXXXX ফরম্যাট
    match = re.search(r'8801[0-9]{9}', text)
    if match:
        return match.group()
    # 01XXXXXXXXX ফরম্যাট
    match = re.search(r'01[0-9]{9}', text)
    if match:
        return match.group()
    return None

@app.route('/api/receive', methods=['POST'])
def receive_otp():
    # ডাটা নেওয়া
    if request.is_json:
        data = request.json
        sender = data.get('mobile_number') or data.get('from') or data.get('sender')
        message = data.get('otp_code') or data.get('content') or data.get('message')
    else:
        sender = request.form.get('mobile_number') or request.form.get('from') or request.form.get('sender')
        message = request.form.get('otp_code') or request.form.get('content') or request.form.get('message')
    
    # OTP রূপান্তর
    otp_number = convert_word_otp_to_number(message) if message else None
    
    # সঠিক মোবাইল নম্বর বের করা
    mobile = None
    
    # 1. প্রথমে sender থেকে নেওয়ার চেষ্টা (যেটা IVAC_BD দিয়ে আসে)
    if sender and sender != 'IVAC_BD' and 'IVAC' not in sender:
        mobile = sender
    
    # 2. যদি sender এ সঠিক নম্বর না থাকে, তাহলে মেসেজের ভেতর খোঁজা
    if not mobile or mobile == 'IVAC_BD':
        mobile = extract_mobile_number(message)
    
    # 3. যদি কিছুই না পাওয়া যায়
    if not mobile:
        mobile = 'Unknown'
    
    # বাংলাদেশ সময়
    bd_time = datetime.now(BD_TZ).strftime("%Y-%m-%d %I:%M:%S %p")
    
    # ডাটাবেসে সেভ করা
    new_otp = OTP(
        mobile_number=mobile,
        otp_code=otp_number or 'Not found',
        arrival_time=bd_time,
        raw_message=message
    )
    db.session.add(new_otp)
    db.session.commit()
    
    print(f"📱 Mobile: {mobile}")
    print(f"🔢 OTP: {otp_number}")
    print(f"⏰ Time: {bd_time}")
    print("---")
    
    return jsonify({
        "status": "success", 
        "mobile": mobile,
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
            "mobile_number": otp.mobile_number,
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
