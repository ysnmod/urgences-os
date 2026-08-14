# 🏥 Urgences OS — Plateforme Intelligente de Régulation & Triage des Urgences

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?style=flat&logo=Python&logoColor=white)](https://www.python.org)
[![XGBoost](https://img.shields.io/badge/Machine%20Learning-XGBoost-EB6420.svg?style=flat)](https://xgboost.readthedocs.io)
[![HL7 v2.5.1](https://img.shields.io/badge/Interoperability-HL7%20v2.5.1%20ORU%5ER01-blue.svg?style=flat)](https://www.hl7.org)
[![WebSockets](https://img.shields.io/badge/Real--Time-WebSockets-010101.svg?style=flat&logo=socketdotio&logoColor=white)](https://websockets.readthedocs.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat)](LICENSE)

**Urgences OS** est une plateforme web d'ingénierie e-santé complète conçue pour optimiser en temps réel le flux de patients, le triage clinique et la gestion logistique des lits au sein des services d'urgences hospitaliers.

Elle associe un **moteur prédictif d'IA clinique**, une **passerelle d'interopérabilité hospitalière (HL7 v2.5.1 ORU^R01)** et une **architecture réactive temps réel par WebSockets**.

---

## 📸 Aperçu de la Plateforme (Interface Utilisateur)

### 1. Accueil & Authentification Sécurisée (RBAC)
| Page d'Accueil & Présentation | Connexion Multi-Rôles (Médecin, Infirmier, Admin) |
| :---: | :---: |
| ![Homepage](docs/screenshots/homepage.png) | ![Login](docs/screenshots/loginpage.png) |

---

### 2. Parcours Patient & Triage Intelligent par IA
| Module d'Admission & File d'Attente | Triage Clinique & Prédiction CCMU (XGBoost) |
| :---: | :---: |
| ![Admission](docs/screenshots/module_acceuil.png) | ![Triage IA](docs/screenshots/module_triage.png) |

---

### 3. Dossier Médical, Soins & Surveillance Continue
| Dossier Patient, Prescriptions & Examens | Supervision du Monitoring & Alertes Temps Réel |
| :---: | :---: |
| ![Soins Médicaux](docs/screenshots/module_soins_medical.png) | ![Monitoring](docs/screenshots/module_monitoring.png) |

---

### 4. Pilotage Opérationnel, Gestion des Lits & RH
| Tableau de Bord Analytique & KPI | Cartographie des Lits en Temps Réel |
| :---: | :---: |
| ![Tableau de bord](docs/screenshots/admin_tableaudebord.png) | ![Gestion des Lits](docs/screenshots/admin_ressourceslits.png) |

| Gestion des Utilisateurs & Habilitations RH |
| :---: |
| ![Gestion RH](docs/screenshots/admin_gestionRH.png) |

---

## 🌟 Fonctionnalités Majeures

* **⚡ Supervision Temps Réel (WebSockets) :** Diffusion bidirectionnelle continue des événements cliniques (admissions, constantes vitales, transferts, alertes de dégradation) sans rechargement manuel.
* **🩺 Interopérabilité Biomédicale (HL7 v2.5.1) :** Passerelle d'ingestion directe des trames d'observation `ORU^R01` depuis les moniteurs patients (segments `MSH`, `PID`, `PV1`, `OBR`, `OBX` avec codes standards LOINC) et génération d'acquittements normalisés `ACK^R01`.
* **🧠 Aide à la Décision Clinique par IA :**
  * **Triage automatique CCMU :** Classification de la gravité clinique (niveaux 1 à 5) par modèle **XGBoost**.
  * **Détection précoce de détérioration :** Calcul dynamique du risque d'instabilité hémodynamique et respiratoire (inspiré du score **NEWS2**).
  * **Garde-fous cliniques déterministes :** Règles médicales strictes (ex: plancher de détresse vitale CCMU 5 si Glasgow $\le$ 7 ou $\text{SpO}_2 < 75\%$) encadrant systématiquement les prédictions algorithmiques.
* **🚑 Coordination Pré-Hospitalière (SAMU/SMUR) :** Transmission anticipée des constantes et du bilan médical depuis les ambulances avant l'arrivée au centre d'urgences.
* **🛏️ Gestion Dynamique des Lits & Salles :** Cartographie interactive des box de soins, déchocage et hospitalisation courte durée.
* **📋 Traçabilité & Audit Médical :** Journalisation complète conforme aux exigences de sécurité et traçabilité des actes de soins.

---

## 🏗️ Architecture du Système

```
                                    +-----------------------------------------+
                                    |    Moniteurs Patients & Simulateurs     |
                                    |  (Émission HL7 v2.5.1 ORU^R01 / MLLP)   |
                                    +-----------------------------------------+
                                                         |
                                                         v
+-----------------------+           +-----------------------------------------+
| Interface Web Soignants|<========>|          Serveur Backend FastAPI         |
|  (SPA React / Babel)  | WebSockets| - Passerelle Interopérabilité HL7 (OBX) |
|                       |  HTTP REST| - Moteur d'Inférence IA (XGBoost)       |
+-----------------------+           | - Contrôle d'Accès par Rôles (RBAC)     |
                                    +-----------------------------------------+
                                                         |
                                                         v
                                    +-----------------------------------------+
                                    |   Base de Données Relationnelle / ORM   |
                                    | (Patients, Séjours, Constantes, Audit)  |
                                    +-----------------------------------------+
```

---

## 📁 Structure du Projet

```text
├── app/
│   ├── models/            # Modèles SQLAlchemy (Base, Patients, Séjours, Lits, etc.)
│   ├── routes/            # Points d'accès API (Triage, Monitoring, HL7, Auth, SAMU)
│   ├── schemas/           # Schémas de validation Pydantic
│   └── utils/             # Utilitaires & Passerelle/Parser HL7 v2.5.1
├── docs/
│   └── screenshots/       # Captures d'écran de l'interface clinique et administration
├── models/
│   ├── artifacts/         # Modèles prédictifs sérialisés (XGBoost, Wait Time, NEWS2)
│   ├── features.py        # Feature engineering clinique (Shock Index, Delta Features)
│   └── train_ccmu_v2.py   # Pipeline d'entraînement du modèle de triage
├── scripts/
│   ├── monitor_simulator.py   # Simulateur temps réel de moniteurs multiparamétriques (HL7)
│   ├── seed_device_bridge.py  # Initialisation du compte de passerelle biomédicale
│   └── import_medicaments.py  # Import du référentiel médicamenteux
├── static/                # Librairies frontend locales, polices et styles
├── app.html               # Application principale de régulation des urgences
├── simulateur.html        # Interface de monitoring multiparamétrique interactif
├── run.py                 # Script de démarrage du backend FastAPI
└── serve.py               # Serveur HTTP pour les interfaces frontend
```

---

## 🚀 Démarrage Rapide

### 1. Prérequis

* Python 3.10 ou supérieur
* Git

### 2. Installation

```bash
# Cloner le dépôt
git clone https://github.com/ysnmod/urgences-os.git
cd urgences-os

# Créer et activer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate  # Sur Windows: .venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Initialisation de la Base de Données

```bash
# Initialiser les tables et les comptes par défaut
python3 -c "from app.models.base import Base, engine, upgrade_database; from app.routes.main import seed_data; Base.metadata.create_all(bind=engine); upgrade_database(); seed_data()"

# Créer le compte passerelle biomédicale
python3 scripts/seed_device_bridge.py
```

### 4. Lancement de l'Application

Dans deux terminaux séparés :

* **Terminal 1 — Backend FastAPI :**
  ```bash
  python3 run.py
  # API active sur http://127.0.0.1:8000 (Documentation Swagger : http://127.0.0.1:8000/docs)
  ```

* **Terminal 2 — Frontend Web :**
  ```bash
  python3 serve.py 3000
  # Application accessible sur http://localhost:3000/
  # Simulateur de monitoring : http://localhost:3000/simulateur.html
  ```

---

## 📡 Passerelle d'Interopérabilité HL7 (ORU^R01)

Urgences OS expose un endpoint dédié à l'ingestion de trames biomédicales standardisées :

* **Endpoint :** `POST /api/hl7/oru-r01`
* **Content-Type :** `text/plain` ou `application/hl7-v2`
* **Exemple de trame d'observation :**

```hl7
MSH|^~\&|MONITOR_PHILIPS_MP50|URGENCES_SIMULATOR|URGENCES_SERVER|CHU_HOSPITAL|20260814213500||ORU^R01|MSG20260814001|P|2.5.1
PID|1||PAT_12^^^URGENCES||EL_IDRISSI^Karim|||U
PV1|1|E|DECHO-1^URGENCES|||||||||||||||SEJ_12
OBR|1||MON_001|VITAL_SIGNS_PANEL^Vital Signs Monitoring^LN|||20260814213500
OBX|1|NM|8867-4^Heart rate^LN||88|/min|60-100|N|||F
OBX|2|NM|8480-6^Systolic blood pressure^LN||125|mm[Hg]|90-140|N|||F
OBX|3|NM|8462-4^Diastolic blood pressure^LN||78|mm[Hg]|60-90|N|||F
OBX|4|NM|2708-6^Oxygen saturation^LN||97|%|95-100|N|||F
OBX|5|NM|8310-5^Body temperature^LN||37.2|Cel|36.0-37.5|N|||F
OBX|6|NM|9279-1^Respiratory rate^LN||18|/min|12-20|N|||F
```

* **Réponse d'acquittement automatique :**

```hl7
MSH|^~\&|URGENCES_SERVER|CHU_HOSPITAL|MONITOR|URGENCES_OS|20260814213501||ACK^R01|ACK20260814001|P|2.5.1
MSA|AA|MSG20260814001|Constantes vitales enregistrees avec succes pour sejour 12
```

---

## 👨‍💻 Auteur

**Yassine ASRI** — Ingénieur d'État en Génie Digital en Santé  
*École Supérieure de Génie Biomédical et des Technologies de la Santé (ESM6ISS) / UM6SS*  
* GitHub : [@ysnmod](https://github.com/ysnmod)  
* Email : yassine.asri.2002@gmail.com  

---

## 📜 Licence

Ce projet est distribué sous licence MIT.
