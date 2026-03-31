from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='etudiant') # admin ou etudiant
    
    # Infos Profil (Point 1)
    photo = db.Column(db.String(200), default='default_avatar.png')
    filiere = db.Column(db.String(100), default='Polytechnique (UL)')
    niveau = db.Column(db.String(20), default='L3')
    bio = db.Column(db.Text, nullable=True)
    
    # Paramètres (Point 2)
    theme_color = db.Column(db.String(20), default='#38bdf8') 
    langue = db.Column(db.String(5), default='fr')
    
    # Relations
    notes = db.relationship('Note', backref='etudiant', lazy=True)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_ue = db.Column(db.String(100), nullable=False)
    valeur = db.Column(db.Float, default=0.0)
    coefficient = db.Column(db.Float, default=1.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    date_envoyee = db.Column(db.DateTime, default=datetime.utcnow)
    lu = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))