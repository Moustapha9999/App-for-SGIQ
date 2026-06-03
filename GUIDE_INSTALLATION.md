Guide d'installation SGIQ — étape par étape

Étape 1 — Prérequis





Windows 10/11



Python 3.12+ (testé avec 3.13)



Vérifier : py -3 --version

Étape 2 — Ouvrir le projet

cd C:\Users\sallm\Projects\sgiq

Étape 3 — Environnement virtuel

py -3 -m venv .venv
.\.venv\Scripts\activate

Étape 4 — Installer les dépendances

pip install -r requirements.txt

Étape 5 — Initialiser la base de données

python -c "from database.connection import init_db, SessionLocal; from services.seed import seed_if_empty; init_db(); s=SessionLocal(); seed_if_empty(s); s.commit(); s.close()"

Fichier créé : data/sgiq.db

Étape 6 — Lancer l'application

streamlit run app.py

Ouvrir : http://localhost:8501

Étape 7 — Se connecter







Rôle



Username



Mot de passe





Admin



admin



admin123

Étape 8 — Configurer l'e-mail (optionnel)





Menu Paramètres → onglet E-mail



Exemple Gmail : smtp.gmail.com, port 587, TLS activé



Utiliser un mot de passe d'application

Étape 9 — Sauvegardes





Automatique : toutes les 24 h au lancement



Manuelle : Paramètres → Sauvegardes → « Sauvegarder maintenant »



Dossier : data/backups/

Étape 10 — Production PostgreSQL

Créer .env :

DATABASE_URL=postgresql://user:password@localhost:5432/sgiq

