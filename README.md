# 🎾 PadelFlow

Application web complète pour la gestion et l'organisation de tournois de padel pour les Jeunes Entreprises (JA).

## 📋 Table des matières

- [Présentation](#-présentation)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Technologies](#-technologies)
- [Installation](#-installation)
- [Configuration](#️-configuration)
- [Utilisation](#-utilisation)
- [Structure du projet](#-structure-du-projet)
- [Développement](#-développement)
- [Déploiement](#-déploiement)
- [Contribution](#-contribution)
- [Licence](#-licence)

## 🎯 Présentation

PadelFlow est une plateforme moderne et intuitive conçue pour simplifier l'organisation et la gestion de tournois de padel. Que vous soyez organisateur d'événements, club de padel ou membre d'une Jeune Entreprise, PadelFlow vous offre tous les outils nécessaires pour gérer vos compétitions efficacement.

### Pourquoi PadelFlow ?

- **Gestion simplifiée** : Interface intuitive pour créer et gérer des tournois
- **Suivi en temps réel** : Mise à jour instantanée des scores et classements
- **Expérience utilisateur optimale** : Design moderne et responsive
- **Infrastructure robuste** : Architecture scalable et sécurisée

## ✨ Fonctionnalités

### Gestion des tournois
- Création et configuration de tournois
- Gestion des inscriptions des joueurs
- Organisation des poules et phases éliminatoires
- Calendrier des matchs

### Suivi des matchs
- Saisie des scores en temps réel
- Historique des matchs
- Statistiques détaillées
- Classements automatiques

### Gestion des participants
- Inscription et profils des joueurs
- Gestion des équipes
- Historique des participations

### Administration
- Tableau de bord administrateur
- Gestion des utilisateurs
- Configuration des paramètres

## 🏗 Architecture

Le projet suit une architecture moderne en trois couches :

```
┌─────────────────┐
│   Frontend      │  React/TypeScript
│   (padel-flow)  │
└────────┬────────┘
         │
         │ REST API
         │
┌────────▼────────┐
│   Backend       │  Python/FastAPI
│   (backend)     │
└────────┬────────┘
         │
         │
┌────────▼────────┐
│  Infrastructure │  Terraform/Cloud
│   (infra)       │
└─────────────────┘
```

## 🛠 Technologies

### Frontend
- **Framework** : React native avec TypeScript
- **Build** : Vite
- **Styling** : CSS Modules
- **State Management** : React Context / Redux (à confirmer)

### Backend
- **Framework** : FastAPI (Python)
- **Base de données** : PostgreSQL 
- **ORM** : SQLAlchemy 
- **API** : RESTful

### Infrastructure
- **IaC** : Terraform (HCL)
- **Cloud** : AWS / GCP / Azure (à confirmer)
- **CI/CD** : GitHub Actions

## 📦 Installation

### Prérequis

- Node.js 18+ et npm/yarn
- Python 3.10+
- Docker et Docker Compose (recommandé)
- Git

### Installation locale

1. **Cloner le repository**
```bash
git clone https://github.com/lisandru1208/padelflow.git
cd padelflow
```

2. **Configuration du Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configuration du Frontend**
```bash
cd padel-flow
npm install
# ou
yarn install
```

### Installation avec Docker

```bash
docker-compose up -d
```

## ⚙️ Configuration

### Backend

Créer un fichier `.env` dans le dossier `backend/` :

```env
DATABASE_URL=postgresql://user:password@localhost:5432/padelflow
SECRET_KEY=votre_clé_secrète_super_sécurisée
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False
```

### Frontend

Créer un fichier `.env` dans le dossier `padel-flow/` :

```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=PadelFlow
```

## 🚀 Utilisation

### Développement

**Backend**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**
```bash
cd padel-flow
npm run dev
# ou
yarn dev
```

L'application sera accessible sur :
- Frontend : http://localhost:5173
- Backend API : http://localhost:8000
- Documentation API : http://localhost:8000/docs

### Production

```bash
# Build du frontend
cd padel-flow
npm run build

# Démarrage du backend en production
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📁 Structure du projet

```
padelflow/
│
├── backend/              # API Backend (Python/FastAPI)
│   ├── app/             # Code source de l'application
│   ├── tests/           # Tests unitaires et d'intégration
│   ├── requirements.txt # Dépendances Python
│   └── README.md
│
├── padel-flow/          # Application Frontend (React/TypeScript)
│   ├── src/            # Code source
│   ├── public/         # Fichiers statiques
│   ├── package.json    # Dépendances Node.js
│   └── README.md
│
├── infra/              # Infrastructure as Code (Terraform)
│   ├── modules/        # Modules Terraform réutilisables
│   ├── environments/   # Configurations par environnement
│   └── README.md
│
├── api.json            # Spécifications OpenAPI
├── .gitignore
└── README.md           # Ce fichier
```

## 👨‍💻 Développement

### Standards de code

- **Backend** : Suivre PEP 8 pour Python
- **Frontend** : ESLint + Prettier pour TypeScript/JavaScript
- **Commits** : Conventional Commits

### Tests

**Backend**
```bash
cd backend
pytest
```

**Frontend**
```bash
cd padel-flow
npm run test
```

### Branches

- `main` : Production
- `develop` : Développement
- `feature/*` : Nouvelles fonctionnalités
- `bugfix/*` : Corrections de bugs
- `hotfix/*` : Corrections urgentes

## 🚢 Déploiement

Le déploiement est automatisé via GitHub Actions :

1. Push sur `main` déclenche le déploiement en production
2. Push sur `develop` déclenche le déploiement en staging

### Déploiement manuel

```bash
cd infra
terraform init
terraform plan
terraform apply
```

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Poussez vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

### Guidelines

- Assurez-vous que les tests passent
- Mettez à jour la documentation si nécessaire
- Suivez les standards de code du projet
- Écrivez des messages de commit clairs et descriptifs

## 📝 Licence

Ce projet est sous licence [MIT](LICENSE) - voir le fichier LICENSE pour plus de détails.

## 📧 Contact

Pour toute question ou suggestion :

- **Repository** : [https://github.com/lisandru1208/padelflow](https://github.com/lisandru1208/padelflow)
- **Issues** : [https://github.com/lisandru1208/padelflow/issues](https://github.com/lisandru1208/padelflow/issues)

---

Développé avec ❤️ pour la communauté du padel
