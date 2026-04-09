from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
# Render Database Connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target = db.Column(db.String(20))
    sender = db.Column(db.String(50))
    message = db.Column(db.Text)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

# অ্যাপ থেকে ওটিপি রিসিভ করার এপিআই
@app.route('/api/receive', methods=['POST'])
def receive():
    data = request.json
    new_otp = OTP(target=data['target'], sender=data['sender'], message=data['message'])
    db.session.add(new_otp)
    db.session.commit()
    return "Success", 200

# পাইথন বা টেম্পারমানকি স্ক্রিপ্টের জন্য ওটিপি লিস্ট
@app.route('/api/get_otps')
def get_otps():
    otps = OTP.query.order_by(OTP.id.desc()).all()
    return jsonify([{'id': o.id, 'target': o.target, 'sender': o.sender, 'message': o.message} for o in otps])

# ওটিপি ডিলিট করার এপিআই
@app.route('/api/delete/<int:id>', methods=['POST'])
def delete(id):
    otp = OTP.query.get(id)
    if otp:
        db.session.delete(otp)
        db.session.commit()
    return "Deleted", 200

if __name__ == '__main__':
    app.run()
