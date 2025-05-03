from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt
from config import Config, DevelopmentConfig
import os

app = Flask(__name__)
app.config.from_object(DevelopmentConfig if os.environ.get('FLASK_ENV') == 'development' else Config)

# MongoDB setup
client = MongoClient(app.config['MONGO_URI'])
db = client.get_database()

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        return None
    return User(user_data)

# Routes
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if db.users.find_one({'email': email}):
            flash('Email already exists', 'error')
            return redirect(url_for('register'))
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_id = db.users.insert_one({
            'username': username,
            'email': email,
            'password': hashed,
            'skills': []
        }).inserted_id
        
        user_data = db.users.find_one({'_id': user_id})
        user = User(user_data)
        login_user(user)
        return redirect(url_for('dashboard'))
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user_data = db.users.find_one({'email': email})
        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password']):
            user = User(user_data)
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_data = db.users.find_one({'_id': ObjectId(current_user.id)})
    skills = user_data.get('skills', [])
    return render_template('dashboard.html', skills=skills)

@app.route('/add_skill', methods=['GET', 'POST'])
@login_required
def add_skill():
    if request.method == 'POST':
        skill_name = request.form['skill_name']
        proficiency = int(request.form['proficiency'])
        category = request.form['category']
        
        db.users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$push': {'skills': {
                'name': skill_name,
                'proficiency': proficiency,
                'category': category
            }}}
        )
        flash('Skill added successfully', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_skill.html')

@app.route('/delete_skill/<skill_id>', methods=['POST'])
@login_required
def delete_skill(skill_id):
    db.users.update_one(
        {'_id': ObjectId(current_user.id)},
        {'$pull': {'skills': {'_id': ObjectId(skill_id)}}}
    )
    flash('Skill deleted successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/profile')
@login_required
def profile():
    user_data = db.users.find_one({'_id': ObjectId(current_user.id)})
    skills = user_data.get('skills', [])
    return render_template('profile.html', user=user_data, skills=skills)

@app.route('/export_profile')
@login_required
def export_profile():
    user_data = db.users.find_one({'_id': ObjectId(current_user.id)})
    skills = user_data.get('skills', [])
    
    # Create a simplified profile for export
    profile_data = {
        'username': user_data['username'],
        'email': user_data['email'],
        'skills': [
            {
                'name': skill['name'],
                'proficiency': skill['proficiency'],
                'category': skill['category']
            }
            for skill in skills
        ]
    }
    
    return jsonify(profile_data)

if __name__ == '__main__':
    app.run(debug=True)