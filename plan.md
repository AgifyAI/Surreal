# Plan RAG pour Gestion d'Emails Avocat

## 🎯 Objectif
Créer un système RAG performant permettant à un agent IA de récupérer le contexte pertinent depuis l'historique complet des emails d'un avocat pour générer des réponses personnalisées et précises.

## 🏗️ Architecture Globale

**Stack Technique : SurrealDB**
- Base multi-modèle (document + graphe + vector search)
- Requêtes unifiées pour filtrage métadonnées + recherche sémantique
- Pas besoin de plusieurs systèmes → simplicité et rapidité

---

## 📋 ROADMAP

### Phase 1 : Modélisation des Données (Semaine 1)

#### 1.1 Schéma Email Principal
```surrealql
DEFINE TABLE email SCHEMAFULL;
DEFINE FIELD id ON email TYPE record;
DEFINE FIELD subject ON email TYPE string;
DEFINE FIELD body ON email TYPE string;
DEFINE FIELD body_embedding ON email TYPE array<float>;
DEFINE FIELD sender_email ON email TYPE string;
DEFINE FIELD sender_name ON email TYPE string;
DEFINE FIELD recipients ON email TYPE array<string>;
DEFINE FIELD cc ON email TYPE array<string>;
DEFINE FIELD date ON email TYPE datetime;
DEFINE FIELD thread_id ON email TYPE string;
DEFINE FIELD message_id ON email TYPE string;
DEFINE FIELD in_reply_to ON email TYPE option<string>;

-- Métadonnées critiques pour filtrage
DEFINE FIELD category ON email TYPE option<string>;
  -- Valeurs : "client", "confrere", "expert_medical", "tribunal", "autre"
DEFINE FIELD client_id ON email TYPE option<string>;
DEFINE FIELD dossier_id ON email TYPE option<string>;
DEFINE FIELD priority ON email TYPE option<string>;
DEFINE FIELD tags ON email TYPE array<string>;
DEFINE FIELD has_attachments ON email TYPE bool;
DEFINE FIELD language ON email TYPE string DEFAULT "fr";

-- Index pour recherche rapide
DEFINE INDEX idx_sender ON email FIELDS sender_email;
DEFINE INDEX idx_date ON email FIELDS date;
DEFINE INDEX idx_thread ON email FIELDS thread_id;
DEFINE INDEX idx_category ON email FIELDS category;
DEFINE INDEX idx_client ON email FIELDS client_id;
DEFINE INDEX idx_dossier ON email FIELDS dossier_id;
```

#### 1.2 Index Vector Search
```surrealql
-- Index HNSW pour recherche sémantique rapide
DEFINE INDEX idx_email_embedding ON email FIELDS body_embedding
  MTREE DIMENSION 1536 TYPE F32;
```

#### 1.3 Relations Graphe
```surrealql
-- Thread : emails du même fil de discussion
DEFINE TABLE thread_member TYPE RELATION
  FROM email TO email;

-- Reply : réponse directe à un email
DEFINE TABLE replies_to TYPE RELATION
  FROM email TO email;

-- Involves : personnes impliquées
DEFINE TABLE person SCHEMAFULL;
DEFINE FIELD email ON person TYPE string;
DEFINE FIELD name ON person TYPE string;
DEFINE FIELD role ON person TYPE string;
  -- "client", "confrere", "expert", "tribunal"

DEFINE TABLE involves TYPE RELATION
  FROM email TO person;

-- Related_case : emails liés au même dossier
DEFINE TABLE dossier SCHEMAFULL;
DEFINE FIELD id ON dossier TYPE string;
DEFINE FIELD client_name ON dossier TYPE string;
DEFINE FIELD description ON dossier TYPE string;

DEFINE TABLE related_to_case TYPE RELATION
  FROM email TO dossier;
```

---

### Phase 2 : Pipeline d'Ingestion (Semaine 1-2)

#### 2.1 Extraction des Emails
```
1. Connexion à la boîte email (IMAP/Gmail API)
2. Extraction des emails avec métadonnées complètes
3. Parsing du contenu (sujet + body)
4. Détection de la langue
5. Extraction des pièces jointes (noms/types)
```

#### 2.2 Enrichissement des Métadonnées
```python
# Classification automatique
def classify_email(email):
    # 1. Règles basées sur l'expéditeur
    if sender in client_database:
        category = "client"
        client_id = get_client_id(sender)
    elif sender in confrere_domains:
        category = "confrere"
    elif is_medical_expert(sender):
        category = "expert_medical"

    # 2. Extraction du dossier_id depuis le sujet/body
    dossier_id = extract_case_reference(subject, body)

    # 3. Tags automatiques (NER)
    tags = extract_keywords(body)

    return {
        "category": category,
        "client_id": client_id,
        "dossier_id": dossier_id,
        "tags": tags
    }
```

#### 2.3 Génération des Embeddings
```python
# Utiliser un modèle français optimisé
model = "text-embedding-3-large"  # OpenAI
# OU
model = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# Créer embedding du contenu complet
content = f"Sujet: {subject}\n\nCorps: {body}"
embedding = generate_embedding(content)
```

#### 2.4 Construction du Graphe
```python
# 1. Lier les emails du même thread
if thread_id:
    link_to_thread(email_id, thread_id)

# 2. Lier les réponses
if in_reply_to:
    create_relation(email_id, "replies_to", in_reply_to)

# 3. Lier aux personnes
for person_email in [sender] + recipients:
    person_id = get_or_create_person(person_email)
    create_relation(email_id, "involves", person_id)

# 4. Lier au dossier
if dossier_id:
    dossier = get_or_create_dossier(dossier_id)
    create_relation(email_id, "related_to_case", dossier)
```

---

### Phase 3 : Requêtes RAG (Semaine 2)

#### 3.1 Recherche Vector Search Pure
```surrealql
-- Recherche sémantique dans tous les emails
LET $query_embedding = <embedding de la requête>;
LET $results = SELECT *,
    vector::similarity::cosine(body_embedding, $query_embedding) AS similarity
FROM email
WHERE body_embedding <|20,1536|> $query_embedding
ORDER BY similarity DESC
LIMIT 10;
```

#### 3.2 Recherche Filtrée par Métadonnées
```surrealql
-- Emails d'un client spécifique
LET $results = SELECT *,
    vector::similarity::cosine(body_embedding, $query_embedding) AS similarity
FROM email
WHERE client_id = $client_id
  AND body_embedding <|20,1536|> $query_embedding
ORDER BY similarity DESC
LIMIT 10;

-- Emails d'une catégorie
WHERE category = "expert_medical"
  AND body_embedding <|20,1536|> $query_embedding

-- Emails d'un dossier
WHERE dossier_id = $dossier_id
  AND body_embedding <|20,1536|> $query_embedding

-- Emails d'un expéditeur spécifique
WHERE sender_email = $sender
  AND body_embedding <|20,1536|> $query_embedding
```

#### 3.3 Graph RAG - Recherche Contextualisée
```surrealql
-- Trouver tous les emails d'un thread pertinent
LET $relevant_emails = (/* vector search */);
LET $expanded = SELECT * FROM $relevant_emails->thread_member;

-- Trouver tous les emails impliquant les mêmes personnes
LET $same_people = SELECT * FROM $relevant_emails->involves<-involves;

-- Trouver tous les emails du même dossier
LET $same_case = SELECT * FROM $relevant_emails->related_to_case<-related_to_case;

-- Combiner : emails similaires + contexte graphe
LET $final_context = array::union(
    $relevant_emails,
    $expanded,
    $same_people,
    $same_case
) | array::unique();
```

#### 3.4 Stratégie RAG Hybride (Recommandée)
```python
def retrieve_context(query, filters=None):
    # Étape 1 : Vector Search avec filtres
    query_embedding = generate_embedding(query)

    similar_emails = vector_search(
        embedding=query_embedding,
        filters=filters,  # category, client_id, sender, etc.
        top_k=5
    )

    # Étape 2 : Graph Expansion
    expanded_context = []
    for email in similar_emails:
        # Ajouter les emails du même thread
        thread_emails = get_thread_emails(email.thread_id)

        # Ajouter les emails liés au même dossier
        case_emails = get_case_emails(email.dossier_id, limit=3)

        # Ajouter les emails précédents/suivants dans la conversation
        conversation_emails = get_conversation_chain(email)

        expanded_context.extend([
            thread_emails,
            case_emails,
            conversation_emails
        ])

    # Étape 3 : Déduplication et tri par pertinence
    final_context = deduplicate_and_rank(
        similar_emails + expanded_context,
        query_embedding
    )

    return final_context[:20]  # Top 20 emails les plus pertinents
```

---

### Phase 4 : API pour l'Agent IA (Semaine 2-3)

#### 4.1 Endpoints Principaux
```
POST /api/rag/search
{
  "query": "Quel est le dernier email du client Martin concernant l'accident?",
  "filters": {
    "client_id": "martin_123",
    "category": "client",
    "dossier_id": "accident_2024_001"
  },
  "top_k": 10,
  "include_graph_context": true
}

Response:
{
  "results": [
    {
      "email_id": "...",
      "subject": "...",
      "body": "...",
      "sender": "...",
      "date": "...",
      "similarity_score": 0.89,
      "context_type": "direct_match" | "thread_member" | "same_case"
    }
  ],
  "total_results": 10
}
```

#### 4.2 Modes de Recherche
```python
# Mode 1 : Recherche globale
GET /api/rag/search?q=expertise+médicale&top_k=10

# Mode 2 : Recherche filtrée par expéditeur
GET /api/rag/search?q=rapport&sender=expert@medical.fr

# Mode 3 : Recherche par dossier
GET /api/rag/search?q=dernières+nouvelles&dossier_id=123

# Mode 4 : Recherche par catégorie
GET /api/rag/search?q=délai&category=tribunal

# Mode 5 : Recherche avec expansion graphe
GET /api/rag/search?q=négociation&expand_graph=true
```

---

### Phase 5 : Optimisations & Qualité (Semaine 3-4)

#### 5.1 Amélioration de la Pertinence
```
✅ Ré-ranking des résultats avec un cross-encoder
✅ Boost des emails récents (weighted by date)
✅ Prise en compte du contexte conversationnel
✅ Détection des emails importants (flagged, high priority)
```

#### 5.2 Gestion des Performances
```
✅ Cache des embeddings générés
✅ Pagination des résultats
✅ Index optimisés (HNSW parameters tuning)
✅ Batch processing pour l'ingestion
```

#### 5.3 Monitoring
```
✅ Latence des requêtes RAG
✅ Qualité des résultats (feedback loop)
✅ Taux d'utilisation des filtres
✅ Coverage des métadonnées
```

---

## 🔧 Stack Technique Détaillée

### Base de Données
- **SurrealDB** (v2.0+)
  - Vector search intégré (HNSW)
  - Graphe natif
  - Requêtes SQL-like puissantes

### Embeddings
- **Option 1 (Recommandée)** : OpenAI `text-embedding-3-large` (1536 dim)
  - Meilleure qualité pour le français
  - API simple
- **Option 2** : Sentence Transformers multilingue (768 dim)
  - Self-hosted
  - Coût réduit

### Pipeline d'Ingestion
- **Python** avec :
  - `imaplib` ou Gmail API
  - `email` library pour parsing
  - `langdetect` pour la langue
  - `spacy` pour NER (extraction tags)

### API
- **FastAPI** (Python)
  - Endpoints async
  - Documentation auto Swagger
  - Validation Pydantic

---

## 📊 Métriques de Succès

1. **Pertinence** : 90%+ des requêtes retournent au moins 1 email utile dans le top 5
2. **Latence** : < 500ms pour une requête RAG complète (vector + graph)
3. **Coverage** : 95%+ des emails ont des métadonnées complètes
4. **Utilisation** : L'agent IA utilise le RAG pour 80%+ des réponses

---

## 🚀 Démarrage Rapide (MVP - 1 semaine)

### Jour 1-2 : Setup + Ingestion Basique
- Setup SurrealDB
- Créer schéma email basique (sans graphe)
- Pipeline d'ingestion simple (emails + embeddings)
- Ingérer 100 premiers emails

### Jour 3-4 : Vector Search
- Implémenter recherche sémantique pure
- API endpoint de base
- Tests de pertinence

### Jour 5 : Métadonnées + Filtres
- Ajouter classification automatique (category)
- Implémenter filtres (sender, category)
- Tests de recherche filtrée

### Jour 6-7 : Graph RAG
- Ajouter relations (threads, replies_to)
- Implémenter expansion graphe
- Tests end-to-end avec agent IA

---

## 🎯 Prochaines Étapes Immédiates

1. ✅ **Valider ce plan** avec vous
2. 🔨 **Setup environnement** SurrealDB
3. 📧 **Accès à la boîte email** de test
4. 🚀 **Démarrer Phase 1** : Modélisation

---

## 💡 Points d'Attention

⚠️ **Confidentialité** : Tous les emails sont sensibles (secret professionnel)
- Chiffrement at rest
- Accès restreint à la base
- Logs anonymisés

⚠️ **Qualité des métadonnées** : Crucial pour le filtrage
- Valider classification automatique
- Permettre correction manuelle si besoin
- Feedback loop pour amélioration continue

⚠️ **Évolutivité** : Anticiper la croissance
- 10 000+ emails → HNSW index essentiel
- Archivage des vieux emails (> 5 ans)
- Stratégie de backup régulier
