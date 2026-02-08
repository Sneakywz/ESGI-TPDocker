-- ========================================
-- Script d'initialisation PostgreSQL
-- Exécuté automatiquement au premier démarrage
-- ========================================

-- Création d'un utilisateur admin supplémentaire (optionnel)
-- Décommentez si vous voulez un deuxième utilisateur
-- CREATE USER admin WITH PASSWORD 'admin123';
-- GRANT ALL PRIVILEGES ON DATABASE myapp TO admin;

-- Message de confirmation dans les logs
SELECT 'Base de données initialisée avec succès !' AS message;

-- Activer des extensions PostgreSQL utiles (optionnel)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- Génération d'UUIDs
-- CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- Recherche full-text

-- Création de la table champions pour League of Legends
CREATE TABLE IF NOT EXISTS champions (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    title VARCHAR(200),
    blurb TEXT,
    image_full VARCHAR(100),
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_champions_name ON champions(name);

-- Message de confirmation
SELECT 'Table champions créée avec succès !' AS message;

-- Note : La table "users" sera créée automatiquement
-- par le backend FastAPI au premier démarrage
