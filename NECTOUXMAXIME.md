# TP Docker - Stack 3-tiers
**Nom :** NECTOUX
**Prenom :** Maxime
**Date :** 06/02/2026
**Lien GitHub :** 

---

## Table des matieres
1. [Introduction et choix techniques](#1-introduction-et-choix-techniques)
2. [Phase 1 : Docker Run](#2-phase-1--docker-run)
3. [Phase 2 : Reseau dedie](#3-phase-2--reseau-dedie)
4. [Phase 3 : Docker Compose](#4-phase-3--docker-compose)
5. [Apport personnel](#5-apport-personnel)
6. [Conclusion](#6-conclusion)

---

## 1. Introduction et choix techniques

### 1.1 Stack technique choisie

| Composant | Technologie | Version |
|-----------|-------------|---------|
| **Backend** | Python (FastAPI) | 3.11 |
| **Frontend** | Vue.js + Vite | 3.5 |
| **Base de donnees** | PostgreSQL | 16 Alpine |
| **Serveur Web** | Nginx | Alpine |

### 1.2 Justification des choix

#### Pourquoi Python (FastAPI) ?
J'ai choisi FastAPI parce que c'est un framework Python que je trouve assez intuitif pour creer des APIs. Ce qui m'a convaincu c'est qu'il genere automatiquement une page de documentation Swagger sur `/docs`, du coup je peux tester mes endpoints directement dans le navigateur sans avoir besoin de Postman. Le code du backend (les endpoints, la connexion a la BDD, etc.) a ete genere par IA, mais toute la partie Docker c'est moi qui l'ai faite.

#### Pourquoi Vue.js ?
Pour le frontend, j'ai utilise Vue.js avec Vite. Je trouvais ca pratique d'avoir le HTML, le JS et le CSS dans un seul fichier `.vue`. Le code Vue.js a ete genere par IA, mais c'est moi qui ai ecrit le Dockerfile multi-stage et la config Nginx pour servir l'application.

#### Pourquoi PostgreSQL ?
J'ai pris PostgreSQL parce que c'est la BDD relationnelle que je connais le mieux. L'image Docker officielle `postgres:16-alpine` est legere et se configure facilement avec des variables d'environnement. J'ai aussi cree un Dockerfile personnalise pour y ajouter un script d'initialisation SQL, ce que j'explique plus loin dans le rapport.

### 1.3 Flux reseau et dependances

```
┌─────────────┐
│  Navigateur │  (Client HTTP)
└──────┬──────┘
       │
       │ 1. HTTP GET http://localhost:8080
       │    Recuperation des fichiers HTML/CSS/JS
       ▼
┌─────────────────┐
│   Frontend      │  (Nginx sur port 80)
│   Vue.js        │  Sert les fichiers statiques
└─────────────────┘
       │
       │ 2. Le JS du navigateur fait un fetch()
       │    vers http://localhost:8000/api/users
       ▼
┌─────────────────┐
│   Backend       │  (FastAPI sur port 8000)
│   Python        │  API REST
└────────┬────────┘
         │
         │ 3. Connexion PostgreSQL
         │    psycopg2 via DB_HOST:5432
         ▼
┌─────────────────┐
│   Database      │  (PostgreSQL sur port 5432)
│   PostgreSQL    │  Stockage des donnees
└─────────────────┘
```

**Explication des flux :**

L'idee c'est que le frontend ne parle jamais directement a la base de donnees. C'est une architecture en 3 couches classique :
- Le **navigateur** charge les fichiers HTML/JS/CSS depuis Nginx
- Le **code JavaScript** qui tourne dans le navigateur fait des requetes HTTP vers le backend
- Le **backend** est le seul a avoir acces a la BDD, il execute les requetes SQL et renvoie les resultats en JSON

J'ai compris que ce decoupage est important pour la securite : si le frontend pouvait taper directement dans la BDD, n'importe qui pourrait lire ou modifier les donnees depuis son navigateur.

---

## 2. Phase 1 : Docker Run

### 2.1 Preparation du Backend

#### Dockerfile Backend
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Explication de chaque instruction :**
- `FROM python:3.11-slim` : J'ai choisi l'image "slim" de Python 3.11 pour avoir une base legere. Elle contient juste le necessaire pour faire tourner Python.
- `WORKDIR /app` : Je definis `/app` comme repertoire de travail. Toutes les commandes suivantes s'executent depuis ce dossier.
- `RUN apt-get install ...` : J'installe les dependances systeme dont `psycopg2` a besoin pour se compiler (gcc, libpq-dev) et `curl` pour le healthcheck. J'ai mis le `rm -rf /var/lib/apt/lists/*` a la fin pour nettoyer le cache apt et reduire la taille de l'image.
- `COPY requirements.txt .` : Je copie d'abord le fichier de dependances tout seul. L'astuce c'est que si ce fichier ne change pas entre deux builds, Docker reutilise le cache et ne reinstalle pas tout. Ca accelere pas mal les builds.
- `RUN pip install ...` : Installation des librairies Python.
- `COPY . .` : La je copie tout le code source dans le conteneur.
- `EXPOSE 8000` : C'est juste informatif, ca dit que le conteneur ecoute sur le port 8000 mais ca n'ouvre pas reellement le port.
- `CMD [...]` : La commande qui lance le serveur. Le `--host 0.0.0.0` est necessaire pour que le serveur ecoute sur toutes les interfaces, sinon il n'est pas accessible depuis l'exterieur du conteneur.

#### Build de l'image backend
```bash
cd backend
docker build -t mon-backend:v1 .
```

### 2.2 Preparation du Frontend

#### Dockerfile Frontend (Multi-stage)
```dockerfile
# STAGE 1 : Construction de l'application Vue.js
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# STAGE 2 : Serveur Nginx leger
FROM nginx:alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
```

**Explication du multi-stage build :**
- **Stage 1 (Builder)** : J'utilise une image Node.js pour installer les dependances npm et builder l'application Vue.js. Le `npm run build` genere des fichiers statiques dans `dist/`. A ce stade l'image fait environ 500 MB.
- **Stage 2 (Production)** : Je repars d'une image Nginx toute legere et je copie uniquement les fichiers buildes depuis le stage 1. L'image finale fait environ 25 MB seulement.
- **Pourquoi j'ai fait ca** : L'image finale ne contient que Nginx et les fichiers statiques, pas Node.js ni les `node_modules`. On passe de 500 MB a 25 MB, c'est quand meme un sacre gain.

#### Build de l'image frontend
```bash
cd frontend
docker build -t mon-frontend:v1 .
```

### 2.3 Lancement de la base de donnees

#### Commande utilisee
```bash
docker run -d \
  --name ma-db \
  -e POSTGRES_DB=myapp \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -v postgres-data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:16-alpine
```

**Explication des flags :**
- `-d` : Lance le conteneur en arriere-plan. Sans ca, mon terminal resterait bloque sur les logs.
- `--name ma-db` : Je donne un nom au conteneur pour le retrouver facilement avec `docker ps` ou `docker logs`.
- `-e POSTGRES_DB=myapp` : Variable d'environnement qui dit a PostgreSQL de creer une base "myapp" au premier demarrage.
- `-v postgres-data:/var/lib/postgresql/data` : Je monte un volume Docker pour persister les donnees. Sans ca, tout serait perdu a chaque suppression du conteneur.
- `-p 5432:5432` : Je mappe le port 5432 de ma machine vers le port 5432 du conteneur pour pouvoir me connecter a la BDD depuis l'exterieur.

#### Verification de la connexion
```bash
docker logs ma-db
docker exec -it ma-db psql -U postgres -d myapp -c "\dt"
```

### 2.4 Recuperation de l'IP du conteneur BDD

**Pourquoi cette etape est necessaire ?**

C'est la que j'ai decouvert un truc : sur le reseau bridge par defaut de Docker, les conteneurs ne se trouvent pas par leur nom. Il n'y a pas de DNS interne. Du coup le seul moyen pour que le backend parle a la BDD, c'est de connaitre son adresse IP. C'est pour ca que je dois faire un `docker inspect` pour recuperer l'IP avant de lancer le backend.

```bash
docker inspect ma-db | grep IPAddress
```

**IP obtenue :** `172.17.0.X`

### 2.5 Lancement du Backend

#### Commande utilisee
```bash
docker run -d \
  --name mon-backend \
  -e DB_HOST=172.17.0.2 \
  -e DB_PORT=5432 \
  -e DB_NAME=myapp \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -p 8000:8000 \
  mon-backend:v1
```

#### Tests des endpoints
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/users
```

### 2.6 Lancement du Frontend

#### Commande utilisee
```bash
docker run -d \
  --name mon-frontend \
  -p 8080:80 \
  mon-frontend:v1
```

### 2.7 Probleme rencontre et solution

**Probleme :** Le frontend ne pouvait pas contacter le backend avec `localhost:8000`.

**Ce que j'ai compris :**
Ca m'a pris un moment pour comprendre le probleme. Le code JavaScript du frontend s'execute dans mon navigateur, pas dans le conteneur Docker. Quand le JS fait un `fetch("http://localhost:8000")`, le `localhost` pointe vers ma machine, pas vers le conteneur backend. Le conteneur Nginx ne fait que servir les fichiers statiques, il ne fait pas de proxy.

**Ce que j'ai fait pour corriger :**
J'ai remplace `localhost` par l'IP de ma machine hote dans le code du frontend. Comme ca, le navigateur envoie ses requetes vers la bonne adresse, et le mapping de port `-p 8000:8000` redirige vers le conteneur backend.

### 2.8 Etat final de la Phase 1

```bash
docker ps
```

---

## 3. Phase 2 : Reseau dedie

### 3.1 Theorie : Reseaux Docker

**Difference entre bridge par defaut et bridge personnalise :**

| Critere | Bridge par defaut | Bridge personnalise |
|---------|-------------------|---------------------|
| Resolution DNS | Non. Il faut utiliser les adresses IP. | Oui. Les conteneurs se trouvent par leur nom. |
| Isolation | Faible. Tous les conteneurs partagent le meme reseau. | Forte. Seuls les conteneurs du meme reseau communiquent. |
| Communication | Par IP uniquement (ex: 172.17.0.2). | Par nom de conteneur (ex: "db"). |

### 3.2 Creation du reseau

```bash
docker network create ma-stack-network
```

#### Inspection du reseau
```bash
docker network inspect ma-stack-network
```

**Ce que j'observe :**
- **Subnet :** 172.18.0.0/16 -- c'est la plage d'IP attribuee au reseau
- **Gateway :** 172.18.0.1 -- la passerelle par defaut
- **Driver :** bridge -- le type de reseau, isole du reseau hote

### 3.3 Relancement des conteneurs

#### Base de donnees
```bash
docker run -d \
  --name db \
  --network ma-stack-network \
  -e POSTGRES_DB=myapp \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -v postgres-data:/var/lib/postgresql/data \
  postgres:16-alpine
```

**Ce que j'ai change par rapport a la Phase 1 :**
- J'ai ajoute `--network ma-stack-network` pour connecter le conteneur au reseau personnalise
- J'ai retire le `-p 5432:5432` parce que la BDD n'a plus besoin d'etre accessible depuis l'exterieur. Seul le backend y accede et il est sur le meme reseau.
- J'ai renomme le conteneur en `db` pour suivre les conventions Docker Compose

#### Backend
```bash
docker run -d \
  --name backend \
  --network ma-stack-network \
  -e DB_HOST=db \
  -e DB_PORT=5432 \
  -e DB_NAME=myapp \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -p 8000:8000 \
  mon-backend:v1
```

**Le changement le plus important :**
`DB_HOST=db` au lieu de `DB_HOST=172.17.0.2`. Grace au reseau personnalise, je n'ai plus besoin de l'IP. Docker resout automatiquement le nom "db" vers l'IP du conteneur de la BDD. C'est quand meme bien plus pratique.

#### Frontend
```bash
docker run -d \
  --name frontend \
  --network ma-stack-network \
  -p 8080:80 \
  mon-frontend:v1
```

### 3.4 Test de la resolution DNS

```bash
docker exec backend ping db -c 3
```

**Ce que j'ai constate :**
Quand je fais `ping db` depuis le conteneur backend, Docker resout le nom "db" en l'IP du conteneur PostgreSQL. C'est le serveur DNS integre de Docker qui gere ca. Ce mecanisme ne marche que sur les reseaux personnalises, pas sur le bridge par defaut. C'est pour ca que ca ne marchait pas en Phase 1 quand j'essayais d'utiliser le nom du conteneur.

### 3.5 Inspection finale

```bash
docker network inspect ma-stack-network
```

### 3.6 Avantages du reseau personnalise

Apres avoir fait les deux phases, voici ce que je retiens comme avantages du reseau personnalise :

1. **Resolution DNS automatique** : Plus besoin de faire `docker inspect` pour chercher les IP. J'utilise directement le nom du conteneur.
2. **Meilleure securite** : La BDD n'est plus exposee sur ma machine. Seuls les conteneurs sur le meme reseau peuvent y acceder.
3. **Configuration stable** : Si un conteneur redemarre et change d'IP, le DNS continue de marcher. Pas besoin de mettre a jour les IP a la main.
4. **Isolation** : Les conteneurs d'un reseau ne peuvent pas parler a ceux d'un autre reseau. Ca permet d'isoler differentes applications sur la meme machine.

---

## 4. Phase 3 : Docker Compose

### 4.1 Le fichier docker-compose.yml

C'est le fichier que j'ai ecrit pour remplacer toutes les commandes `docker run` des phases precedentes :

```yaml
version: '3.8'

services:
  db:
    build:
      context: ./database
      dockerfile: Dockerfile
    container_name: stack-db
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: stack-backend
    environment:
      DB_HOST: db
      DB_PORT: 5432
      DB_NAME: myapp
      DB_USER: postgres
      DB_PASSWORD: postgres
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - app-network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: stack-frontend
    ports:
      - "8080:80"
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:80"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - app-network
    restart: unless-stopped

volumes:
  postgres_data:
    driver: local

networks:
  app-network:
    driver: bridge
```

### 4.2 Explication section par section

#### Services
Dans Docker Compose, un **service** correspond a un conteneur. Chaque service a un nom (`db`, `backend`, `frontend`) qui sert aussi de nom DNS sur le reseau. C'est comme ce que j'ai fait en Phase 2 avec `--name` et `--network`, mais tout est regroupe dans un seul fichier.

#### Base de donnees
- **build vs image** : J'ai utilise `build` avec mon Dockerfile personnalise au lieu de `image: postgres:16-alpine`. Ca me permet d'inclure le script `init.sql` qui cree les tables au premier demarrage.
- **healthcheck** : J'ai configure un healthcheck avec `pg_isready` qui verifie toutes les 10 secondes que PostgreSQL est pret. C'est important parce que le backend a besoin que la BDD soit operationnelle avant de demarrer. Sans ca, j'avais des erreurs de connexion au lancement.

#### Backend
- **depends_on** : Ca dit a Compose de demarrer la BDD avant le backend.
- **condition: service_healthy** : Le backend ne demarre que quand le healthcheck de la BDD passe. Sans cette condition, `depends_on` attend juste que le conteneur soit lance, pas que PostgreSQL soit reellement pret.
- **start_period: 40s** : Je donne 40 secondes au backend pour demarrer avant de commencer les healthchecks. Ca evite de le marquer "unhealthy" pendant qu'il s'initialise.

#### Frontend
Le frontend depend du backend avec la meme logique de healthcheck. Son propre healthcheck verifie que Nginx repond sur le port 80.

#### Volumes
La section `volumes` en bas declare le volume `postgres_data`. C'est ce qui persiste les donnees de la BDD. Un `docker compose down` garde les volumes, mais `docker compose down -v` les supprime.

#### Networks
J'ai declare le reseau `app-network` explicitement. Compose le cree automatiquement au demarrage. Tous les services sont dessus et peuvent communiquer par leur nom.

### 4.3 Lancement de la stack

```bash
docker compose up --build -d
```

**Ordre de demarrage que j'ai observe :**
1. `db` : La BDD demarre en premier et attend d'etre "healthy"
2. `backend` : Demarre une fois que la BDD est prete
3. `frontend` : Demarre en dernier, une fois que le backend repond

C'est quand meme beaucoup plus simple qu'en Phase 1 ou je devais lancer chaque conteneur un par un dans le bon ordre.

### 4.4 Verification

```bash
docker compose ps
```

```bash
docker compose logs
```

### 4.5 Tests de l'application

**Tests des endpoints :**
```bash
curl http://localhost:8000/health
# Reponse : {"status":"healthy","database":"connected","message":"API et BDD operationnelles"}

curl http://localhost:8000/api/users
# Reponse : {"success":true,"count":4,"users":[...]}
```

### 4.6 Test de persistance des donnees

```bash
docker compose down
docker compose up -d
```

**Question :** Les donnees sont-elles conservees ?
**Reponse :** Oui. J'ai verifie : apres un `down` puis un `up`, les donnees sont toujours la. C'est grace au volume nomme `postgres_data` qui existe sur le disque de ma machine, independamment du conteneur.

### 4.7 Test de suppression complete

```bash
docker compose down -v
```

**Question :** Que se passe-t-il au prochain demarrage ?
**Reponse :** Le `-v` supprime les volumes. Quand je relance la stack, PostgreSQL recree une base vide et re-execute le `init.sql`. Les donnees ajoutees via l'API sont perdues. Les utilisateurs de test sont recrees automatiquement par le backend.

### 4.8 Comparaison des 3 phases

| Critere | Phase 1 | Phase 2 | Phase 3 |
|---------|---------|---------|---------|
| **Nombre de commandes** | ~10 (build, inspect, run pour chaque conteneur) | ~7 (creation reseau + run sans inspect) | 1 seule (`docker compose up --build -d`) |
| **Resolution DNS** | Non. `docker inspect` obligatoire. | Oui, par nom de conteneur. | Oui, automatique. |
| **Gestion reseau** | Bridge par defaut, pas d'isolation | Reseau personnalise cree a la main | Reseau cree automatiquement |
| **Ordre de demarrage** | Manuel, il faut faire attention. | Manuel aussi. | Automatique avec `depends_on` + `healthcheck`. |
| **Facilite de maintenance** | Galere. Faut se souvenir de tout. | Mieux, mais encore beaucoup de commandes. | Tout dans un fichier YAML versionne. |

---

## 5. Apport personnel

### 5.1 Mon experience avec Docker et ce que ce TP a change

J'utilise Docker depuis un bon moment, autant au travail que pour mes projets perso. Au boulot, Docker fait partie de l'environnement de dev : on lance les BDD, les APIs et les outils en conteneurs pour que tout le monde ait le meme setup. Pour mes projets perso, j'ai aussi pris le reflexe de tout containeriser pour eviter les classiques "ca marche sur ma machine mais pas sur la tienne".

Le truc, c'est que j'avais une **mauvaise habitude** : je mettais souvent **plusieurs services dans un seul conteneur**. Par exemple, pour un projet perso, j'avais un conteneur avec Node.js et MongoDB dedans, les deux lances par un script d'entrypoint. Pour un autre projet au travail, j'avais mis un backend Python et Redis dans le meme conteneur en utilisant `supervisord` pour gerer les deux processus.

Ca marchait, mais avec le recul je me rends compte que c'etait pas du tout la bonne approche. Voici pourquoi :

1. **Un conteneur = un processus** : Docker est fait pour isoler un seul processus par conteneur. Quand on en met plusieurs, on perd tout l'interet de l'isolation. Si MongoDB plante, ca embarque Node.js avec.

2. **On peut pas scaler independamment** : Si mon backend a besoin de plus de puissance, je suis oblige de dupliquer tout le conteneur, y compris la BDD. Ca n'a aucun sens et ca pose des problemes de coherence des donnees.

3. **Les logs sont un enfer** : Quand tout est dans le meme conteneur, les logs de tous les services se melangent. Pour debugger un probleme sur le backend, il faut filtrer au milieu des logs de la BDD. C'est penible.

4. **Les healthchecks sont limites** : Je peux verifier que le conteneur tourne, mais pas que chaque service a l'interieur fonctionne correctement. Si la BDD plante mais que le processus principal tourne encore, Docker pense que tout va bien.

5. **Les images sont enormes** : L'image contient Python + les libs Python + PostgreSQL + les outils PostgreSQL + supervisord... Ca fait des images de 1 Go facilement.

6. **Le redemarrage casse tout** : Si je veux redemarrer uniquement le backend, c'est impossible. Tout le conteneur redemarre, et la BDD subit un arret brutal qui peut corrompre les donnees.

Ce TP m'a vraiment fait prendre conscience de tout ca. La progression en 3 phases est bien faite :
- En Phase 1, j'ai vu les galeres du reseau bridge par defaut (pas de DNS, IP qui changent)
- En Phase 2, j'ai compris l'interet d'un reseau dedie (DNS automatique, isolation, pas besoin d'exposer la BDD)
- En Phase 3, j'ai vu comment Docker Compose simplifie tout en un fichier avec en plus les healthchecks et l'ordre de demarrage

Maintenant je structure tous mes projets avec un service par conteneur et un `docker-compose.yml`. C'est plus propre, plus facile a maintenir, et je peux enfin scaler ou redemarrer chaque service independamment.

### 5.2 Integration de l'API League of Legends

Pour montrer une utilisation concrete de la stack 3-tiers, j'ai integre l'API **Data Dragon** de Riot Games (League of Legends). L'idee c'etait d'aller au-dela des donnees de test et d'avoir une vraie application qui recupere des donnees depuis une API externe.

Le code Python et Vue.js a ete genere par IA, mais c'est moi qui ai fait toute la partie Docker : les Dockerfiles, le docker-compose, la configuration reseau, le script SQL d'initialisation.

#### Ce qui a ete ajoute

**Cote backend (FastAPI) :**
- Un endpoint `/api/champions/sync` qui appelle l'API Data Dragon pour recuperer les 169 champions de LoL
- Un endpoint `/api/champions` qui renvoie les champions stockes en BDD
- Un endpoint `/api/champions/{id}/details` qui va chercher les competences et stats d'un champion

**Cote base de donnees :**
- Une table `champions` avec les colonnes : id, name, title, blurb, image_full, tags
- Un index sur le nom pour accelerer les recherches
- Tout ca dans le script `init.sql` qui s'execute automatiquement au premier demarrage

**Cote frontend (Vue.js) :**
- Un systeme d'onglets pour naviguer entre le health check et les champions
- Un bouton "Synchroniser" qui recupere les champions depuis l'API via le backend
- Une grille de cartes avec l'image, le nom et le titre de chaque champion
- Un modal avec les details complets quand on clique sur un champion

#### Le flux complet

```
Utilisateur -> Frontend (Vue.js) -> Backend (FastAPI) -> API Riot Games (Data Dragon)
                                                      -> PostgreSQL (stockage)
```

Le backend fait le lien entre l'API Riot et la BDD. Il recupere les donnees, les stocke en PostgreSQL, et les sert au frontend. Les donnees sont en cache dans la BDD, du coup on ne spamme pas l'API Riot a chaque requete.

#### Ce que ca montre

- Le backend peut acceder a Internet depuis le conteneur Docker pour appeler l'API Riot, tout en communiquant avec la BDD sur le reseau interne
- La clause `ON CONFLICT DO UPDATE` en SQL evite les doublons quand on resynchronise
- L'architecture 3-tiers fonctionne avec des vraies donnees, pas juste des exemples

### 5.3 Dockerfile personnalise pour PostgreSQL

J'ai aussi cree un Dockerfile personnalise pour PostgreSQL au lieu d'utiliser l'image officielle directement :

```dockerfile
FROM postgres:16-alpine

ENV POSTGRES_DB=myapp \
    POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=postgres

COPY init.sql /docker-entrypoint-initdb.d/

EXPOSE 5432
```

L'astuce c'est le dossier `/docker-entrypoint-initdb.d/`. C'est un dossier special de l'image PostgreSQL : tous les fichiers `.sql` qu'on met dedans sont executes automatiquement au premier demarrage. Ca me permet de creer la table `champions` sans intervention manuelle.

J'ai prefere cette approche plutot que de creer les tables depuis le code Python parce que :
- La structure de la BDD est definie dans un fichier SQL clair et separe
- Le script s'execute meme si le backend n'est pas encore demarre
- C'est reproductible : n'importe qui qui clone le projet aura la meme structure de BDD

---

## 6. Conclusion

### Ce que j'ai appris

**Sur Docker :**
- Le principe "un conteneur = un processus" et pourquoi c'est important (j'en ai fait l'experience en faisant l'inverse pendant longtemps)
- Comment optimiser les images avec les multi-stage builds (de 500 MB a 25 MB pour le frontend)
- L'astuce du cache Docker en copiant `requirements.txt` avant le code source
- La difference entre `EXPOSE` (informatif) et `-p` (mapping de port effectif)

**Sur les reseaux Docker :**
- Le bridge par defaut n'a pas de DNS, il faut utiliser les IP
- Les reseaux personnalises offrent le DNS, l'isolation et une config plus simple
- La BDD ne devrait pas etre exposee sur la machine hote, seul le backend doit y acceder

**Sur Docker Compose :**
- Un seul fichier YAML remplace toutes les commandes `docker run`
- Les `depends_on` avec `healthcheck` garantissent un demarrage propre
- Les volumes nommes persistent les donnees meme quand on supprime les conteneurs
- Attention au `docker compose down -v` qui supprime aussi les volumes

### Difficultes rencontrees

1. **Le probleme frontend/backend en Phase 1** : J'ai galere a comprendre pourquoi `localhost:8000` ne marchait pas depuis le frontend. Il m'a fallu un moment pour comprendre que le JS s'execute dans le navigateur et pas dans le conteneur.

2. **L'ordre de demarrage** : En Phase 1 et 2, le backend plantait si je le lancais avant que PostgreSQL soit pret. En Phase 3, les healthchecks reglent le probleme mais j'ai du tester plusieurs valeurs de `start_period` et `interval` pour trouver le bon equilibre.

3. **La resolution DNS en Phase 1** : J'ai essaye `DB_HOST=ma-db` sur le reseau par defaut et ca ne marchait pas. J'ai perdu du temps avant de comprendre qu'il fallait un reseau personnalise pour avoir le DNS.

### Solutions trouvees

1. Utiliser l'IP de la machine hote pour le frontend
2. Utiliser `depends_on` avec `condition: service_healthy` et configurer les healthchecks
3. Creer un reseau personnalise avec `docker network create`

### Ameliorations possibles

1. **Reverse proxy Nginx** : Ajouter un Nginx en front qui redirige `/api` vers le backend et `/` vers le frontend, pour eviter les problemes de CORS
2. **Fichier .env** : Externaliser les mots de passe dans un fichier `.env` au lieu de les mettre en dur dans le `docker-compose.yml`
3. **Monitoring** : Ajouter Prometheus et Grafana pour surveiller les metriques de la stack

---

## Annexes

### Commandes Docker utiles

```bash
# Nettoyage complet
docker system prune -a --volumes

# Voir l'utilisation disque
docker system df

# Logs en temps reel
docker compose logs -f

# Rebuild un service
docker compose build backend
docker compose up -d backend

# Entrer dans un conteneur
docker compose exec backend sh
```

### Ressources utilisees

1. Documentation officielle Docker : https://docs.docker.com/
2. Documentation Docker Compose : https://docs.docker.com/compose/
3. Documentation FastAPI : https://fastapi.tiangolo.com/
4. Documentation Vue.js : https://vuejs.org/
5. API Data Dragon (Riot Games) : https://developer.riotgames.com/docs/lol#data-dragon

---

**Fin du rapport**
