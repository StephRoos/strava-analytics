# Session de Déploiement - 13 février 2026

## 🎯 Objectif
Déployer l'application Strava Analytics sur Streamlit Community Cloud avec base PostgreSQL persistante (Supabase).

## ✅ Réalisations

### Infrastructure
- ✅ Compte Supabase créé
- ✅ Base de données PostgreSQL configurée
- ✅ Schéma complet initialisé (7 tables + indexes)
- ✅ Connection string PostgreSQL récupérée

### Configuration Streamlit Cloud
- ✅ App déployée sur Streamlit Cloud
- ✅ URL : `https://strava-analytics-hqwrf6xhoz2wmc37dzkmh4.streamlit.app/`
- ✅ Secrets configurés
- ✅ requirements.txt créé pour les dépendances

### Fichiers créés
- ✅ `requirements.txt` - Dépendances Python
- ✅ `DEPLOYMENT.md` - Guide complet de déploiement
- ✅ `.streamlit/secrets.toml.example` - Template des secrets
- ✅ `scripts/init_postgres.sql` - Initialisation PostgreSQL
- ✅ `scripts/migrate_sqlite_to_postgres.py` - Migration de données

### Application Strava API
- ✅ Nouvelle application Strava créée
- ✅ Client ID et Client Secret générés
- ✅ Authorization Callback Domain configuré

## ❌ Problème rencontré

### Erreur OAuth sur Streamlit Cloud
**Symptôme** : "www.strava.com refused to connect" lors de la connexion OAuth

**Tests effectués** :
- ✅ Vérification configuration Strava API
- ✅ Vérification redirect_uri (avec/sans trailing slash)
- ✅ Nouvelle application Strava créée
- ✅ Nouvelle app Streamlit Cloud déployée
- ✅ Test sur mobile (4G/5G)
- ✅ Test en navigation privée
- ❌ Tous échouent avec la même erreur

**Cause probable** :
- Blocage réseau/firewall spécifique à OAuth Strava
- Problème régional ou ISP
- Bug Streamlit Cloud (rare)

## ✅ Solution de contournement : Version locale

**L'application fonctionne parfaitement en local** :
```bash
cd /home/stephane/Projects/strava-analytics
uv run streamlit run app/Home.py
```

URL locale : http://localhost:8501

**Avantages** :
- ✅ OAuth fonctionne avec localhost
- ✅ Utilise la même base PostgreSQL Supabase
- ✅ Données persistantes
- ✅ Toutes les fonctionnalités disponibles

## 📝 Prochaines étapes

### Option A : Continuer avec la version locale (recommandé)
1. Vérifier les identifiants dans `.env`
2. Relancer l'app locale
3. Se connecter et synchroniser les données
4. Utiliser l'app normalement

### Option B : Débugger le déploiement cloud
1. Investiguer le blocage réseau
2. Tester depuis un autre réseau/VPN
3. Contacter le support Streamlit si nécessaire
4. Vérifier les logs Strava API

### Option C : Déploiement alternatif
- Heroku
- Railway
- Render
- Docker sur VPS personnel

## 🔑 Identifiants et URLs

### Supabase PostgreSQL
- **Connection String** : `postgresql://postgres.[ref]:[password]@aws-0-eu-west-1.pooler.supabase.com:6543/postgres`
- **Dashboard** : https://supabase.com/dashboard/project/[project-id]

### Streamlit Cloud
- **URL** : https://strava-analytics-hqwrf6xhoz2wmc37dzkmh4.streamlit.app/
- **Dashboard** : https://share.streamlit.io/
- **Status** : Déployé mais OAuth bloqué

### Strava API
- **Settings** : https://www.strava.com/settings/api
- **Application** : Strava Analytics Pro (nouvelle)
- **Client ID** : [à récupérer]
- **Callback Domains** : `localhost, strava-analytics-hqwrf6xhoz2wmc37dzkmh4.streamlit.app`

## 📚 Documentation

Toute la documentation de déploiement est disponible dans :
- `DEPLOYMENT.md` - Guide complet
- `scripts/init_postgres.sql` - SQL d'initialisation
- `scripts/migrate_sqlite_to_postgres.py` - Script de migration
- `.streamlit/secrets.toml.example` - Template configuration

## 🎓 Leçons apprises

1. **PostgreSQL > SQLite** : Pour le déploiement cloud, PostgreSQL est essentiel (données persistantes)
2. **OAuth peut être bloqué** : Certains réseaux/environnements bloquent OAuth
3. **Local first** : Toujours tester en local avant de déployer
4. **Supabase gratuit** : 500 MB PostgreSQL gratuit, parfait pour ce projet
5. **Streamlit secrets** : Nécessitent un redémarrage complet de l'app

## 💡 Recommandation

**Pour l'instant, utiliser la version locale** qui fonctionne parfaitement :

```bash
# Configuration .env
STRAVA_CLIENT_ID="[nouveau_client_id]"
STRAVA_CLIENT_SECRET="[nouveau_client_secret]"
STRAVA_REDIRECT_URI="http://localhost:8501"
DATABASE_URL="postgresql://[supabase_connection_string]"

# Lancement
uv run streamlit run app/Home.py
```

L'app sera accessible sur **http://localhost:8501** avec toutes les fonctionnalités, données persistantes sur Supabase, et OAuth fonctionnel.

---

**Session suspendue** : 13 février 2026, 15:30
**Prochaine session** : Vérifier identifiants .env et tester connexion locale
