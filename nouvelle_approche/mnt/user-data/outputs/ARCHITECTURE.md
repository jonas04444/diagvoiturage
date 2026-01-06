# 🏗️ Architecture et Intégration des Modules

## 📊 Vue d'ensemble

Voici comment tous vos modules s'intègrent ensemble :

```
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION PRINCIPALE                    │
│                   (votre interface ou main.py)               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ importe
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    tab5_ortools.py                           │
│              (Interface graphique améliorée)                 │
│                                                              │
│  • Timeline visuelle des services                           │
│  • Création manuelle de services                            │
│  • Bouton "🤖 Optimiser (OR-Tools)"                        │
│  • Gestion des voyages assignés                             │
└──────┬──────────────────────┬──────────────────┬───────────┘
       │                      │                   │
       │ importe              │ importe           │ importe
       ▼                      ▼                   ▼
┌──────────────┐    ┌────────────────┐    ┌─────────────────┐
│ objet.py     │    │tabelauCSV.py   │    │gestion_voiture  │
│              │    │                │    │      .py        │
│ • voyage     │    │• TableauCSV    │    │                 │
│ • service_   │    │• Chargement    │    │• Optimisateur   │
│   agent      │    │  CSV           │    │  Services       │
│              │    │• Selection     │    │• OR-Tools       │
│• time_to_    │    │  voyages       │    │  CP-SAT         │
│  minutes()   │    │                │    │• optimiser_     │
│• minutes_to_ │    │                │    │  affectation()  │
│  time()      │    │                │    │                 │
└──────────────┘    └────────────────┘    └─────────────────┘
```

---

## 🔗 Flux de Données

### 1️⃣ Chargement des voyages (tabelauCSV.py)

```python
# L'utilisateur clique sur "📂 Charger voyages CSV"
window_tableau_csv(callback=callback_chargement)

# tabelauCSV lit le CSV et crée des objets voyage
for ligne in csv:
    v = voyage(
        num_ligne=ligne['Ligne'],
        num_voyage=ligne['Voy.'],
        arret_debut=ligne['De'],
        arret_fin=ligne['À'],
        heure_debut=ligne['Début'],
        heure_fin=ligne['Fin']
    )
    objets_voyages.append(v)

# Appelle le callback avec les voyages
callback(objets_voyages, matrice_donnees)
```

### 2️⃣ Création de services (tab5_ortools.py)

```python
# L'utilisateur crée un service
service = service_agent(
    num_service=1,
    type_service="matin"
)

# Ajoute des contraintes horaires
service.heure_debut_max = 6 * 60   # 06:00
service.heure_fin_max = 14 * 60    # 14:00

# Ajoute des voyages manuellement
service.ajout_voyages(voyage1)
service.ajout_voyages(voyage2)
```

### 3️⃣ Optimisation avec OR-Tools (gestion_voiture.py)

```python
# L'utilisateur clique sur "🤖 Optimiser (OR-Tools)"
success, resultats = optimiser_affectation(
    voyages=voyages_non_assignes,
    services=services_existants,
    battement_min=5,
    battement_max=50,
    verifier_arrets=True,
    temps_limite=60
)

# OR-Tools résout le problème et met à jour les services
if success:
    # Les voyages sont automatiquement ajoutés aux services
    print(f"{resultats['nb_affectes']} voyages affectés")
```

---

## 📁 Dépendances des Fichiers

### objet.py (Base - Aucune dépendance)
```python
# Définit les classes de base
class voyage:
    # Représente un voyage de bus
    # Méthodes : time_to_minutes(), minutes_to_time(), etc.

class service_agent:
    # Représente un service d'agent
    # Contient une liste de voyages
```

### tabelauCSV.py
```python
# Dépendances
import customtkinter
from objet import voyage  # ✅ Nécessite objet.py

# Fournit
class TableauCSV:
    # Widget de sélection de voyages
    
class window_tableau_csv:
    # Fenêtre popup pour charger CSV
    # Callback : callback(objets_voyages, matrice_donnees)
```

### gestion_voiture.py
```python
# Dépendances
from ortools.sat.python import cp_model  # ✅ pip install ortools
from objet import voyage, service_agent  # ✅ Nécessite objet.py

# Fournit
class OptimisateurServices:
    # Classe principale d'optimisation
    
def optimiser_affectation(...):
    # Interface simple pour l'optimisation
```

### tab5_ortools.py
```python
# Dépendances
import customtkinter
from tabelauCSV import window_tableau_csv  # ✅ Nécessite tabelauCSV.py
from objet import voyage, service_agent     # ✅ Nécessite objet.py
from gestion_voiture import optimiser_affectation  # ✅ Nécessite gestion_voiture.py

# Fournit
class Tab5CreationManuelle:
    # Interface graphique complète
```

---

## 🎯 Points d'Intégration Critiques

### 1. Callback de tabelauCSV

**Dans tabelauCSV.py :**
```python
if self.master.callback:
    self.master.callback(objet_voyages, self.matrice_donnees)
```

**Dans tab5_ortools.py :**
```python
def callback_chargement(objets_voyages, matrice_donnees):
    self.voyages_disponibles = objets_voyages  # ✅ Liste d'objets voyage
    self.remplir_liste_voyages()

window_tableau_csv(callback=callback_chargement)
```

**✅ Vérifié :** Le callback reçoit bien une liste d'objets `voyage`

---

### 2. Contraintes horaires des services

**Format attendu par gestion_voiture.py :**
```python
service.heure_debut_max = 360  # En minutes (6h00)
service.heure_fin_max = 840    # En minutes (14h00)
```

**Format créé par tab5_ortools.py :**
```python
h, m = int(parts[0]), int(parts[1])
service.heure_debut_max = h * 60 + m  # ✅ Compatible
```

**✅ Vérifié :** Les formats sont compatibles

---

### 3. Structure de l'objet voyage

**Attributs utilisés par gestion_voiture.py :**
- `v.hdebut` : Heure de début en minutes
- `v.hfin` : Heure de fin en minutes
- `v.arret_debut` : Nom de l'arrêt de départ
- `v.arret_fin` : Nom de l'arrêt d'arrivée
- `v.arret_debut_id()` : 3 premiers caractères de l'arrêt de départ
- `v.arret_fin_id()` : 3 premiers caractères de l'arrêt d'arrivée

**Définition dans objet.py :**
```python
class voyage:
    def __init__(self, num_ligne, num_voyage, arret_debut, arret_fin, 
                 heure_debut, heure_fin, js_srv=""):
        self.hdebut = self.time_to_minutes(heure_debut)  # ✅
        self.hfin = self.time_to_minutes(heure_fin)      # ✅
        self.arret_debut = arret_debut                   # ✅
        self.arret_fin = arret_fin                       # ✅
    
    def arret_debut_id(self):
        return self.arret_debut[:3]  # ✅
    
    def arret_fin_id(self):
        return self.arret_fin[:3]    # ✅
```

**✅ Vérifié :** Tous les attributs nécessaires sont présents

---

### 4. Tracking des voyages assignés

**Dans tab5_ortools.py :**
```python
# Dictionnaire pour tracker les voyages assignés
self.voyages_assignes = {}  # {id(voyage): service}

# Lors de l'ajout d'un voyage à un service
self.voyages_assignes[id(voyage)] = service

# Lors de l'optimisation OR-Tools
for j, service in enumerate(self.services):
    for i in resultats['affectations'][j]:
        v = voyages_non_assignes[i]
        self.voyages_assignes[id(v)] = service  # ✅ Mise à jour
```

**✅ Vérifié :** Le tracking est cohérent

---

## 🔄 Workflow Complet Utilisateur

```
1. DÉMARRAGE
   └─> Lancer application
       └─> Tab5CreationManuelle s'affiche

2. CHARGEMENT DES VOYAGES
   └─> Clic "📂 Charger voyages CSV"
       └─> window_tableau_csv s'ouvre (popup)
           └─> Sélection du fichier CSV
               └─> tabelauCSV.charger_csv()
                   └─> Lecture du CSV
                       └─> Création des objets voyage
                           └─> callback(objets_voyages, matrice)
                               └─> Tab5.voyages_disponibles mis à jour
                                   └─> Affichage dans le tableau

3. CRÉATION DES SERVICES
   └─> Clic "➕ Nouveau Service"
       └─> Dialogue de configuration
           └─> Saisie type et contraintes horaires
               └─> Création service_agent
                   └─> Affichage dans la zone centrale

4. AFFECTATION MANUELLE (Optionnel)
   └─> Sélection d'un service (✏️)
       └─> Cocher des voyages dans le tableau gauche
           └─> Clic "➡️ Ajouter au service"
               └─> service.ajout_voyages(v)
                   └─> voyages_assignes[id(v)] = service
                       └─> Mise à jour de l'affichage

5. OPTIMISATION OR-TOOLS
   └─> Clic "🤖 Optimiser (OR-Tools)"
       └─> Dialogue de configuration
           └─> Saisie des paramètres
               └─> optimiser_affectation()
                   └─> OptimisateurServices.resoudre()
                       └─> OR-Tools CP-SAT
                           └─> Solution trouvée
                               └─> Application de la solution
                                   └─> Mise à jour des services
                                       └─> Rafraîchissement de l'affichage

6. EXPORT
   └─> Clic "💾 Exporter Planning"
       └─> Sélection du fichier de sortie
           └─> Écriture CSV avec tous les services
```

---

## ✅ Checklist de Compatibilité

### Vérifications avant utilisation

- [x] **objet.py présent** avec classes `voyage` et `service_agent`
- [x] **tabelauCSV.py présent** avec `window_tableau_csv`
- [x] **gestion_voiture.py présent** avec `optimiser_affectation`
- [x] **OR-Tools installé** (`pip install ortools --break-system-packages`)
- [x] **customtkinter installé** (`pip install customtkinter --break-system-packages`)

### Tests de compatibilité

```bash
# Test 1 : Vérifier les imports
python -c "from objet import voyage, service_agent; print('✅ objet.py OK')"

python -c "from gestion_voiture import optimiser_affectation; print('✅ gestion_voiture.py OK')"

# Test 2 : Test d'intégration complet
python test_integration_complete.py

# Test 3 : Test de l'interface
python tab5_ortools.py
```

---

## 🐛 Résolution de Problèmes

### Problème : "No module named 'tabelauCSV'"

**Cause :** Le fichier n'est pas dans le même dossier

**Solution :**
```bash
# Vérifier que le fichier existe
ls tabelauCSV.py

# Vérifier qu'il est dans le bon dossier
pwd
ls -la
```

---

### Problème : "No module named 'ortools'"

**Cause :** OR-Tools non installé

**Solution :**
```bash
pip install ortools --break-system-packages
```

---

### Problème : Voyage pas ajouté au service après optimisation

**Cause possible :** L'objet voyage n'est pas correctement passé

**Vérification :**
```python
# Dans gestion_voiture.py, vérifier que :
service.ajout_voyages(v)  # v est bien un objet voyage

# Dans tab5_ortools.py, vérifier que :
voyages_non_assignes = [
    v for v in self.voyages_disponibles  # v est bien un objet voyage
    if id(v) not in self.voyages_assignes
]
```

---

### Problème : Contraintes horaires non respectées

**Cause :** Format incorrect des contraintes

**Vérification :**
```python
# Les contraintes doivent être en MINUTES
service.heure_debut_max = 6 * 60    # ✅ 360 minutes = 06:00
service.heure_fin_max = 14 * 60     # ✅ 840 minutes = 14:00

# PAS en format "HH:MM"
service.heure_debut_max = "06:00"   # ❌ INCORRECT
```

---

## 📚 Documentation Supplémentaire

- **QUICK_START.md** : Guide de démarrage rapide (5 min)
- **README_gestion_voiture.md** : Documentation complète du module
- **AMELIORATIONS.md** : Détails des améliorations
- **exemple_comparaison.py** : Tests et benchmarks

---

## 🎓 Exemple d'Intégration Minimale

Si vous voulez juste tester que tout fonctionne :

```python
# test_minimal.py
from objet import voyage, service_agent
from gestion_voiture import optimiser_affectation

# 1. Créer des voyages
voyages = [
    voyage("25", "V1", "A", "B", "06:00", "07:00"),
    voyage("25", "V2", "B", "C", "07:10", "08:00"),
]

# 2. Créer un service
services = [service_agent(num_service=1, type_service="matin")]

# 3. Optimiser
success, resultats = optimiser_affectation(voyages, services)

# 4. Vérifier
if success:
    print(f"✅ {resultats['nb_affectes']} voyages affectés")
    for s in services:
        print(s)
else:
    print("❌ Échec")
```

---

**Dernière mise à jour :** Janvier 2026  
**Compatibilité vérifiée avec :** objet.py, tabelauCSV.py, gestion_voiture.py, tab5_ortools.py
