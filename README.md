# Projet Data-Driven Decision Making - Olist Brazil

## Équipe
- **Hatim Brahim** 
- **Belhaj Hamza**

## Objectif du Projet
Optimiser la rétention client de la plateforme Olist en prédisant les retards de livraison et en automatisant des décisions marketing proactives.

## Installation & Utilisation
1. Cloner le dépôt : `git clone https://github.com/brahimhatim265/DATA-DRIVEN-DECISION-MAKING.git`
2. Créer un environnement virtuel : `python -m venv venv`
3. Activer l'environnement : `venv\Scripts\activate`
4. Installer les dépendances : `pip install -r requirements.txt`

## Structure du Projet
- `/data`: Données brutes et transformées (non suivies par Git)
- `/notebooks`: Analyses exploratoires et modèles
- `/docs`: Business Case, Plan A/B Test et KPI Tree
- `/src`: Code source du Dashboard Streamlit

## Acquisition des Données
Pour faire fonctionner ce projet, vous devez :
1. Télécharger le dataset Olist sur Kaggle : [Lien Kaggle Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
2. Télécharger les données IBGE : [Lien Kaggle IBGE](https://www.kaggle.com/datasets/gabrielrs3/economy-and-population-of-cities-in-brazil-ibge) 
3. Extraire et placer tous les fichiers `.csv` et `.xlsx` dans le dossier `data/raw/`.
