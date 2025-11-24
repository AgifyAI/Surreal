# Déploiement sur Coolify

Guide de déploiement du système RAG Email sur Coolify.

## 🚀 Prérequis

- Un serveur Coolify configuré
- Une clé API OpenAI

## 📝 Étapes de Déploiement

### 1. Créer un Nouveau Projet dans Coolify

1. Connectez-vous à Coolify
2. Créez un nouveau projet : "RAG Email System"

### 2. Ajouter le Service SurrealDB

1. Créer un nouveau service → Database → SurrealDB
2. Configuration :
   - **Port**: 8000 (interne)
   - **User**: root
   - **Password**: root (à changer en production)
   - **Volume**: Activer pour persister les données

### 3. Déployer l'Application RAG

1. Créer un nouveau service → GitHub Repository
2. Configuration :
   - **Repository**: https://github.com/AgifyAI/Surreal
   - **Branch**: main
   - **Build Method**: Dockerfile

### 4. Variables d'Environnement

Ajouter les variables d'environnement suivantes :

```env
# SurrealDB Configuration
SURREALDB_URL=http://surrealdb:8000
SURREALDB_USER=root
SURREALDB_PASSWORD=root
SURREALDB_NAMESPACE=Law IA
SURREALDB_DATABASE=mailify

# OpenAI Configuration
OPENAI_API_KEY=votre_clé_api_ici
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSION=1536

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### 5. Configuration des Ports

- **Port API**: 8000 (à exposer publiquement)
- **Port SurrealDB**: 8000 (interne seulement)

### 6. Health Checks

Coolify détectera automatiquement le health check défini dans le Dockerfile :
- **Endpoint**: `/health`
- **Interval**: 30s

## 🔧 Post-Déploiement

### 1. Appliquer le Schéma

Une fois déployé, appliquer le schéma SurrealDB :

```bash
curl -X POST -u "root:root" \
  -H "surreal-ns: Law IA" \
  -H "surreal-db: mailify" \
  --data-binary @schema.surql \
  https://votre-instance-surrealdb.com/sql
```

### 2. Vérifier l'API

```bash
curl https://votre-instance-rag.com/health
```

Devrait retourner :
```json
{
  "status": "healthy",
  "timestamp": "..."
}
```

### 3. Tester l'Ingestion

```bash
curl -X POST "https://votre-instance-rag.com/api/emails/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Test déploiement",
    "body": "Email de test après déploiement",
    "sender_email": "test@example.com",
    "sender_name": "Test User",
    "recipients": ["avocat@law-firm.fr"]
  }'
```

### 4. Accéder à la Documentation

La documentation Swagger sera disponible sur :
```
https://votre-instance-rag.com/docs
```

## 🔒 Sécurité

### Recommandations de Production

1. **Changer les mots de passe par défaut**
   - SurrealDB root password
   - Utiliser des secrets dans Coolify

2. **Limiter l'accès à SurrealDB**
   - Ne pas exposer le port 8000 de SurrealDB publiquement
   - Utiliser le réseau interne de Coolify

3. **Configurer HTTPS**
   - Activer SSL dans Coolify
   - Utiliser Let's Encrypt

4. **Sauvegardes**
   - Configurer des backups automatiques du volume SurrealDB
   - Exporter régulièrement les données

## 📊 Monitoring

### Logs

Accéder aux logs dans Coolify :
- Logs API : Onglet "Logs" du service RAG
- Logs SurrealDB : Onglet "Logs" du service SurrealDB

### Métriques

Surveiller :
- Utilisation CPU/RAM
- Latence des requêtes API
- Taille de la base de données
- Nombre d'emails ingérés

## 🔄 Mises à Jour

Pour mettre à jour l'application :

1. Pusher les modifications sur GitHub
2. Dans Coolify, cliquer sur "Rebuild" pour le service RAG
3. Coolify reconstruira l'image Docker et redéploiera

## 🐛 Dépannage

### L'API ne démarre pas

1. Vérifier les logs
2. Vérifier que SurrealDB est accessible
3. Vérifier les variables d'environnement

### Erreur de connexion SurrealDB

```bash
# Tester la connexion depuis le conteneur API
curl http://surrealdb:8000/health
```

### Erreur OpenAI API

Vérifier que la clé API est valide et a suffisamment de crédits.

## 📞 Support

- GitHub Issues: https://github.com/AgifyAI/Surreal/issues
- Documentation: README_RAG.md
