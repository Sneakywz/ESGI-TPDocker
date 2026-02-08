"""
Backend FastAPI pour la stack 3-tiers Docker
Fournit:
- Un endpoint de health check (/health)
- Un endpoint pour récupérer des utilisateurs depuis PostgreSQL (/api/users)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import List, Dict
import httpx
import json

app = FastAPI(title="Backend API", version="1.0.0")

# Configuration CORS pour permettre au frontend d'appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les origines autorisées
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Récupération des variables d'environnement pour la connexion à la BDD
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "myapp")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def get_db_connection():
    """Crée une connexion à la base de données PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Erreur de connexion à la BDD: {e}")
        raise


def init_database():
    """Initialise la base de données avec une table users si elle n'existe pas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Création de la table users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insertion de données de test si la table est vide
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()['count']

        if count == 0:
            sample_users = [
                ("Alice Dupont", "alice@example.com"),
                ("Bob Martin", "bob@example.com"),
                ("Charlie Durand", "charlie@example.com"),
                ("Diana Leroy", "diana@example.com")
            ]

            cursor.executemany(
                "INSERT INTO users (name, email) VALUES (%s, %s)",
                sample_users
            )

        conn.commit()
        cursor.close()
        conn.close()
        print("Base de données initialisée avec succès")

    except Exception as e:
        print(f"Erreur lors de l'initialisation de la BDD: {e}")


@app.on_event("startup")
async def startup_event():
    """Événement de démarrage : initialisation de la BDD"""
    print("Démarrage de l'API...")
    print(f"Connexion à la BDD: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    init_database()


@app.get("/")
def root():
    """Endpoint racine"""
    return {
        "message": "Bienvenue sur l'API Backend",
        "endpoints": {
            "health": "/health",
            "users": "/api/users"
        }
    }


@app.get("/health")
def health_check():
    """
    Endpoint de health check
    Vérifie que l'API est opérationnelle et peut se connecter à la BDD
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()

        return {
            "status": "healthy",
            "database": "connected",
            "message": "API et BDD opérationnelles"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


@app.get("/api/users")
def get_users():
    """
    Récupère la liste des utilisateurs depuis la base de données

    Returns:
        Dictionnaire avec success, count et liste d'utilisateurs
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, email, created_at
            FROM users
            ORDER BY created_at DESC
        """)

        users = cursor.fetchall()
        cursor.close()
        conn.close()

        return {
            "success": True,
            "count": len(users),
            "users": users
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des utilisateurs: {str(e)}"
        )


@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    """
    Récupère un utilisateur spécifique par son ID

    Args:
        user_id: ID de l'utilisateur

    Returns:
        Informations de l'utilisateur
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = %s",
            (user_id,)
        )

        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail=f"Utilisateur {user_id} non trouvé"
            )

        return {
            "success": True,
            "user": user
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération de l'utilisateur: {str(e)}"
        )


# ========================================
# ENDPOINTS LEAGUE OF LEGENDS
# ========================================

# URL de l'API Data Dragon de Riot Games
LOL_API_URL = "https://ddragon.leagueoflegends.com/cdn/14.1.1/data/fr_FR/champion.json"
LOL_IMAGE_URL = "https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/"


@app.get("/api/champions/sync")
async def sync_champions():
    """
    Synchronise les champions depuis l'API League of Legends
    et les stocke dans la base de données PostgreSQL
    """
    try:
        # Appel à l'API Data Dragon
        async with httpx.AsyncClient() as client:
            response = await client.get(LOL_API_URL, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        champions_data = data.get("data", {})

        # Connexion à la base de données
        conn = get_db_connection()
        cursor = conn.cursor()

        # Création de la table si elle n'existe pas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS champions (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                title VARCHAR(200),
                blurb TEXT,
                image_full VARCHAR(100),
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        synced_count = 0
        for champ_id, champ_info in champions_data.items():
            cursor.execute("""
                INSERT INTO champions (id, name, title, blurb, image_full, tags)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    title = EXCLUDED.title,
                    blurb = EXCLUDED.blurb,
                    image_full = EXCLUDED.image_full,
                    tags = EXCLUDED.tags
            """, (
                champ_id,
                champ_info.get("name"),
                champ_info.get("title"),
                champ_info.get("blurb"),
                champ_info["image"].get("full"),
                json.dumps(champ_info.get("tags", []))
            ))
            synced_count += 1

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "success": True,
            "message": f"{synced_count} champions synchronisés avec succès",
            "count": synced_count
        }

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erreur lors de l'appel à l'API LoL: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la synchronisation: {str(e)}"
        )


@app.get("/api/champions")
def get_champions():
    """
    Récupère la liste des champions depuis la base de données

    Returns:
        Liste des champions LoL avec leurs informations
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, title, blurb, image_full, tags, created_at
            FROM champions
            ORDER BY name ASC
        """)

        champions = cursor.fetchall()
        cursor.close()
        conn.close()

        # Parser les tags JSON
        for champion in champions:
            if champion.get('tags'):
                champion['tags'] = json.loads(champion['tags'])

        return {
            "success": True,
            "count": len(champions),
            "image_base_url": LOL_IMAGE_URL,
            "champions": champions
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des champions: {str(e)}"
        )


@app.get("/api/champions/{champion_id}")
def get_champion(champion_id: str):
    """
    Récupère un champion spécifique par son ID

    Args:
        champion_id: ID du champion (ex: "Ahri")

    Returns:
        Informations du champion
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT id, name, title, blurb, image_full, tags, created_at
            FROM champions WHERE id = %s""",
            (champion_id,)
        )

        champion = cursor.fetchone()
        cursor.close()
        conn.close()

        if champion is None:
            raise HTTPException(
                status_code=404,
                detail=f"Champion {champion_id} non trouvé"
            )

        # Parser les tags JSON
        if champion.get('tags'):
            champion['tags'] = json.loads(champion['tags'])

        return {
            "success": True,
            "image_base_url": LOL_IMAGE_URL,
            "champion": champion
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération du champion: {str(e)}"
        )


@app.get("/api/champions/{champion_id}/details")
async def get_champion_details(champion_id: str):
    """
    Récupère les détails complets d'un champion depuis l'API LoL
    Inclut les compétences (spells) et les statistiques

    Args:
        champion_id: ID du champion (ex: "Ahri")

    Returns:
        Détails complets du champion avec compétences
    """
    try:
        # URL pour récupérer les détails complets
        detail_url = f"https://ddragon.leagueoflegends.com/cdn/14.1.1/data/fr_FR/champion/{champion_id}.json"

        async with httpx.AsyncClient() as client:
            response = await client.get(detail_url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        # Les données sont dans data['data'][champion_id]
        champion_data = data.get('data', {}).get(champion_id, {})

        if not champion_data:
            raise HTTPException(
                status_code=404,
                detail=f"Champion {champion_id} non trouvé dans l'API"
            )

        # Extraire les compétences
        spells = []
        for spell in champion_data.get('spells', []):
            spells.append({
                'id': spell.get('id'),
                'name': spell.get('name'),
                'description': spell.get('description'),
                'image': spell.get('image', {}).get('full'),
                'cooldown': spell.get('cooldownBurn'),
                'cost': spell.get('costBurn')
            })

        # Passive
        passive = champion_data.get('passive', {})
        passive_info = {
            'name': passive.get('name'),
            'description': passive.get('description'),
            'image': passive.get('image', {}).get('full')
        }

        # Statistiques
        stats = champion_data.get('stats', {})

        return {
            "success": True,
            "champion": {
                "id": champion_data.get('id'),
                "name": champion_data.get('name'),
                "title": champion_data.get('title'),
                "lore": champion_data.get('lore'),
                "image_full": champion_data.get('image', {}).get('full'),
                "tags": champion_data.get('tags', []),
                "passive": passive_info,
                "spells": spells,
                "stats": {
                    "hp": stats.get('hp'),
                    "mp": stats.get('mp'),
                    "armor": stats.get('armor'),
                    "attackdamage": stats.get('attackdamage'),
                    "attackspeed": stats.get('attackspeed')
                }
            },
            "image_base_url": LOL_IMAGE_URL,
            "spell_image_url": "https://ddragon.leagueoflegends.com/cdn/14.1.1/img/spell/"
        }

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erreur lors de l'appel à l'API LoL: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des détails: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
