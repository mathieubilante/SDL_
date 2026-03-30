import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# --- Initialisation Flask ---
app = Flask(__name__)
app.secret_key = "SDL_SECRET_KEY_2026" 

# --- Configuration base de données ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'sdl_database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Modèles de Données ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    date_naissance = db.Column(db.String(20))
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    filiere = db.Column(db.String(100))
    semestre = db.Column(db.Integer)
    notes = db.relationship('Grade', backref='student', lazy=True)

# NOUVEAU : Table pour les notes que l'Admin gère pour tout le monde
class MatiereOfficielle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100))
    note = db.Column(db.Float, default=0.0)
    coefficient = db.Column(db.Float, default=1.0)

class Grade(db.Model): # Simulations persos des élèves
    id = db.Column(db.Integer, primary_key=True)
    matiere = db.Column(db.String(100))
    valeur = db.Column(db.Float)
    coefficient = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    matiere = db.Column(db.String(100))
    duree_minutes = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=db.func.now())

with app.app_context():
    db.create_all()

# --- ROUTES D'AUTHENTIFICATION ---

@app.route('/inscription')
def login_page():
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    nom = request.form.get('nom')
    email = request.form.get('email')
    filiere = request.form.get('filiere')
    semestre = request.form.get('semestre')

    if User.query.filter_by(email=email).first():
        flash("Email déjà utilisé.", "error")
        return redirect(url_for('login_page'))

    username = nom.split()[0].lower() + str(random.randint(10, 99))
    password_plain = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    
    new_user = User(
        nom=nom, email=email, username=username,
        password=generate_password_hash(password_plain),
        filiere=filiere, semestre=int(semestre)
    )
    db.session.add(new_user)
    db.session.commit()
    return render_template('success.html', user=username, password=password_plain)

@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        user_input = request.form.get('username')
        pass_input = request.form.get('password')

        # Connexion Admin (Code simple pour ton test)
        if user_input == "AdminSDL" and pass_input == "SDL2026":
            session['user_id'] = 'ADMIN'
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))

        user = User.query.filter_by(username=user_input).first()
        if user and check_password_hash(user.password, pass_input):
            session['user_id'] = user.id
            session['role'] = 'etudiant'
            return redirect(url_for('index'))
        
        flash("Identifiants incorrects", "error")
    return render_template('connexion.html')

# --- ESPACE ADMIN (MODIFIÉ POUR ADMIS.HTML) ---

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('connexion'))
    matieres = MatiereOfficielle.query.all()
    # On crée un faux user pour que {{ user.semestre }} ne plante pas dans admis.html
    user_fake = {'semestre': 'En cours'}
    return render_template('admis.html', matieres=matieres, user=user_fake)

@app.route('/admin/add_matiere', methods=['POST'])
def admin_add_matiere():
    if session.get('role') != 'admin': return redirect(url_for('connexion'))
    nom = request.form.get('nom')
    coeff = float(request.form.get('coeff', 1))
    note = float(request.form.get('note', 0))
    
    new_m = MatiereOfficielle(nom=nom, coefficient=coeff, note=note)
    db.session.add(new_m)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_all_notes', methods=['POST'])
def admin_update_all_notes():
    if session.get('role') != 'admin': return redirect(url_for('connexion'))
    matieres = MatiereOfficielle.query.all()
    for m in matieres:
        note_val = request.form.get(f'note_{m.id}')
        coeff_val = request.form.get(f'coeff_{m.id}')
        if note_val is not None: m.note = float(note_val)
        if coeff_val is not None: m.coefficient = float(coeff_val)
    db.session.commit()
    flash("Notes publiées !")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_matiere/<int:id>')
def admin_delete_matiere(id):
    if session.get('role') != 'admin': return redirect(url_for('connexion'))
    m = MatiereOfficielle.query.get(id)
    if m:
        db.session.delete(m)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

# --- ROUTES ÉTUDIANT (PRÉDICTION / COURS / INDEX) ---

@app.route('/')
@app.route('/index')
def index():
    if 'user_id' not in session: return redirect(url_for('connexion'))
    user = User.query.get(session['user_id'])
    matieres = MatiereOfficielle.query.all() # L'étudiant voit les notes de l'admin
    return render_template('index.html', user=user, matieres=matieres)

@app.route('/cours')
def cours():
    if 'user_id' not in session: return redirect(url_for('connexion'))
    user = User.query.get(session['user_id'])
    return render_template('cours.html', user=user)

@app.route('/prediction')
def prediction():
    if 'user_id' not in session: return redirect(url_for('connexion'))
    user = User.query.get(session['user_id'])
    matieres = MatiereOfficielle.query.all()
    return render_template('prediction.html', user=user, matieres=matieres)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('connexion'))

@app.route('/programmer')
def programmer():
    if 'user_id' not in session: 
        return redirect(url_for('connexion'))
    user = User.query.get(session['user_id'])
    # On récupère aussi les sessions de révision pour les afficher sur le planning
    sessions_revision = StudySession.query.filter_by(user_id=user.id).all()
    return render_template('planning.html', user=user, sessions=sessions_revision)

if __name__ == '__main__':
    app.run(debug=True, port=5001)