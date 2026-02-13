# Guide de Déploiement - Strava Analytics

## 🚀 Déploiement sur Streamlit Community Cloud

### Étape 1 : Prérequis

- Compte GitHub avec le repository `strava-analytics`
- Compte Streamlit Community Cloud (gratuit)
- Application Strava créée sur https://www.strava.com/settings/api

### Étape 2 : Préparer l'application Strava

1. Aller sur https://www.strava.com/settings/api
2. Créer une nouvelle application ou modifier l'existante
3. **IMPORTANT** : Ajouter l'URL de callback de production dans "Authorization Callback Domain"
   - Format : `votre-app.streamlit.app`
   - Exemple : `strava-analytics.streamlit.app`
4. Noter le **Client ID** et **Client Secret**

### Étape 3 : Déployer sur Streamlit Cloud

1. Aller sur https://streamlit.io/cloud
2. Cliquer sur "New app"
3. Sélectionner le repository : `StephRoos/strava-analytics`
4. Branch : `main`
5. Main file path : `app/Home.py`
6. Cliquer sur "Deploy"

### Étape 4 : Configurer les Secrets

1. Dans le dashboard Streamlit Cloud, aller dans les paramètres de l'app
2. Cliquer sur "Secrets"
3. Copier le contenu de `.streamlit/secrets.toml.example`
4. Remplacer les valeurs par vos vraies credentials :

```toml
STRAVA_CLIENT_ID = "202151"  # Votre vrai Client ID
STRAVA_CLIENT_SECRET = "xxxxx"  # Votre vrai Client Secret
DATABASE_URL = "sqlite:///./data/strava.db"
DEBUG = false
LOG_LEVEL = "INFO"
AUTO_SYNC_ENABLED = true
SYNC_STREAM_DATA_DAYS = 90
MIN_ACTIVITIES_FOR_ML = 50
```

5. Sauvegarder

### Étape 5 : Mettre à jour l'URL de callback Strava

1. Retourner sur https://www.strava.com/settings/api
2. Dans "Authorization Callback Domain", ajouter :
   - `votre-app.streamlit.app` (remplacer par votre vraie URL)
3. Sauvegarder

### Étape 6 : Tester

1. Visiter votre application : `https://votre-app.streamlit.app`
2. Cliquer sur "Se connecter avec Strava"
3. Autoriser l'accès
4. Synchroniser les données
5. Explorer vos analytics !

## ⚠️ Limitations importantes

### Base de données SQLite sur Streamlit Cloud

**Problème** : Streamlit Cloud utilise un système de fichiers éphémère. Les données sont perdues lors du redémarrage de l'app.

**Solutions** :

#### Option 1 : Accepter les données temporaires (simple)
- Les données restent tant que l'app n'est pas redéployée
- Resynchroniser après chaque redémarrage
- Convient pour usage personnel occasionnel

#### Option 2 : Migrer vers PostgreSQL (recommandé pour production)

1. **Créer une base PostgreSQL gratuite sur Supabase** :
   - Aller sur https://supabase.com
   - Créer un projet gratuit
   - Copier la connection string PostgreSQL

2. **Mettre à jour DATABASE_URL** dans les secrets :
   ```toml
   DATABASE_URL = "postgresql://user:pass@host:5432/database"
   ```

3. **Modifier le code** (si nécessaire) :
   - SQLAlchemy supporte PostgreSQL nativement
   - Aucune modification majeure nécessaire normalement

#### Option 3 : Utiliser un volume persistant

Streamlit Community Cloud ne supporte pas les volumes persistants sur le plan gratuit.

## 🔄 Mises à jour automatiques

Streamlit Cloud redéploie automatiquement l'app à chaque `git push` sur `main`.

## 📊 Monitoring

1. **Logs** : Visibles dans le dashboard Streamlit Cloud
2. **Métriques** : Analytics basiques disponibles
3. **Erreurs** : Notifications par email si l'app crash

## 🔒 Sécurité

- ✅ Secrets jamais committés dans Git
- ✅ HTTPS automatique sur Streamlit Cloud
- ✅ OAuth tokens stockés en base de données
- ⚠️ SQLite en production = données temporaires

## 💰 Coûts

**Streamlit Community Cloud (Free Tier)** :
- 1 app publique gratuite
- Ressources limitées mais suffisantes
- Redémarrage automatique si inactif > 7 jours

**Pour plus de ressources** :
- Streamlit Cloud Pro : $20-$100/mois
- Ou déployer sur AWS/GCP/Azure avec Docker

## 🐛 Dépannage

### L'app ne démarre pas
- Vérifier les logs dans le dashboard
- Vérifier que `requirements.txt` est présent
- Vérifier que les secrets sont configurés

### OAuth ne fonctionne pas
- Vérifier l'URL de callback sur Strava
- Vérifier `STRAVA_CLIENT_ID` et `STRAVA_CLIENT_SECRET`
- L'URL doit correspondre exactement

### Données perdues après redémarrage
- Normal avec SQLite sur Streamlit Cloud
- Migrer vers PostgreSQL pour persistance

## 📚 Ressources

- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Strava API Docs](https://developers.strava.com/)
- [Supabase PostgreSQL](https://supabase.com/docs/guides/database)
