import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

# --- Initialisation Flask ---
app = Flask(__name__)
app.secret_key = "SDL_SECRET_KEY_2026" 

# --- Configuration base de données & Dossiers ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'sdl_database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# --- Dictionnaire de traduction ---
LANGUAGES = {
    'fr': {'dashboard': 'Tableau de Bord', 'modules': 'Modules', 'prediction': 'IA Prédiction', 'deepwork': 'Travail Profond', 'welcome': 'Bienvenue', 'logout': 'Déconnexion', 'profile': 'Mon Profil', 'settings': 'Paramètres'},
    'en': {'dashboard': 'Dashboard', 'modules': 'Units', 'prediction': 'AI Prediction', 'deepwork': 'Deep Work', 'welcome': 'Welcome', 'logout': 'Logout', 'profile': 'Profile', 'settings': 'Settings'}
}

# --- Modèles de Données ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    filiere = db.Column(db.String(100))
    langue = db.Column(db.String(5), default='fr')
    photo = db.Column(db.String(200), default='default_avatar.png')
    semestre = db.Column(db.Integer, default=1)
    grades = db.relationship('Grade', backref='student', lazy=True)
    notifications = db.relationship('Notification', backref='receiver', lazy=True)

class Grade(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    matiere = db.Column(db.String(100))
    valeur = db.Column(db.Float)
    coefficient = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    lu = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class StudySession(db.Model): 
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    matiere = db.Column(db.String(100))
    duree_minutes = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.context_processor
def inject_global_data():
    lang_code = session.get('lang', 'fr')
    return {'texts': LANGUAGES.get(lang_code, LANGUAGES['fr']), 'current_year': datetime.now().year}

# --- ROUTES AUTH & LANGUE ---

@app.route('/set_language/<lang>')
def set_language(lang):
    session['lang'] = lang
    if 'user_id' in session and session['user_id'] != 'ADMIN':
        user = User.query.get(session['user_id'])
        if user:
            user.langue = lang
            db.session.commit()
    return redirect(request.referrer or url_for('index'))

@app.route('/inscription')
def inscription_page():
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    nom = request.form.get('nom')
    email = request.form.get('email')
    if User.query.filter_by(email=email).first():
        flash("Email déjà utilisé.", "error")
        return redirect(url_for('inscription_page'))
    username = nom.split()[0].lower() + str(random.randint(10, 99))
    password_plain = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    new_user = User(nom=nom, email=email, username=username, password=generate_password_hash(password_plain), filiere=request.form.get('filiere'), photo='default_avatar.png')
    db.session.add(new_user)
    db.session.commit()
    return render_template('success.html', user=username, password=password_plain)

@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        user_input = request.form.get('username')
        pass_input = request.form.get('password')
        if user_input == "AdminSDL" and pass_input == "SDL2026":
            session['user_id'] = 'ADMIN'; session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        user = User.query.filter_by(username=user_input).first()
        if user and check_password_hash(user.password, pass_input):
            session['user_id'] = user.id; session['role'] = 'etudiant'; session['lang'] = user.langue
            return redirect(url_for('index'))
        flash("Identifiants incorrects", "error")
    return render_template('connexion.html')

# --- ESPACE ÉTUDIANT ---

@app.route('/')
@app.route('/index')
def index():
    if 'user_id' not in session: return redirect(url_for('connexion'))
    user = User.query.get(session['user_id'])
    matieres = Grade.query.filter_by(user_id=user.id).all()
    notifs = Notification.query.filter_by(user_id=user.id, lu=False).all()
    
    moyenne = 0
    total_coeffs = sum(m.coefficient for m in matieres)
    if total_coeffs > 0:
        moyenne = sum(m.valeur * m.coefficient for m in matieres) / total_coeffs
    return render_template('index.html', user=user, matieres=matieres, notifs=notifs, moyenne=round(moyenne, 2))

@app.route('/profil', methods=['GET', 'POST'])
def profil():
    if 'user_id' not in session: return redirect(url_for('connexion'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        file = request.files.get('photo')
        if file and file.filename != '':
            filename = secure_filename(f"avatar_{user.id}.png")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.photo = filename
        user.nom = request.form.get('nom')
        user.prenom = request.form.get('prenom')
        db.session.commit()
    return render_template('profil.html', user=user)

@app.route('/cours')
def cours():
    if 'user_id' not in session: return redirect(url_for('connexion'))
    return render_template('cours.html', user=User.query.get(session['user_id']))

@app.route('/prediction')
def prediction():
    if 'user_id' not in session: return redirect(url_for('connexion'))
    return render_template('prediction.html', user=User.query.get(session['user_id']))

@app.route('/programmer')
def programmer():
    if 'user_id' not in session: return redirect(url_for('connexion'))
    user = User.query.get(session['user_id'])
    sessions = StudySession.query.filter_by(user_id=user.id).all()
    return render_template('planning.html', user=user, sessions=sessions)

@app.route('/parametres')
def parametres():
    if 'user_id' not in session: return redirect(url_for('connexion'))
    return render_template('parametre.html', user=User.query.get(session['user_id']))

# --- ESPACE ADMIN ---

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('connexion'))
    return render_template('admis.html', etudiants=User.query.all())

@app.route('/admin/add_note', methods=['POST'])
def admin_add_note():
    user_id = request.form.get('user_id')
    new_grade = Grade(matiere=request.form.get('nom'), valeur=float(request.form.get('note')), coefficient=float(request.form.get('coeff')), user_id=user_id)
    db.session.add(new_grade)
    db.session.add(Notification(message=f"Note ajoutée : {new_grade.matiere}", user_id=user_id))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('connexion'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)