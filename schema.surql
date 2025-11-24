-- 1.1 Schéma Email Principal
DEFINE TABLE email SCHEMAFULL;
-- REMOVED: DEFINE FIELD id ON email TYPE record; -- System field, cannot be defined explicitly
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

-- 1.2 Index Vector Search
-- Index HNSW pour recherche sémantique rapide
DEFINE INDEX idx_email_embedding ON email FIELDS body_embedding HNSW DIMENSION 1536 DIST COSINE;

-- 1.3 Relations Graphe

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
-- REMOVED: DEFINE FIELD id ON dossier TYPE string; -- System field
DEFINE FIELD client_name ON dossier TYPE string;
DEFINE FIELD description ON dossier TYPE string;

DEFINE TABLE related_to_case TYPE RELATION
  FROM email TO dossier;
