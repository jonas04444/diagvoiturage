# 🚗 Gestion Voiture - Module d'Optimisation OR-Tools

## 📋 Description

Module d'optimisation avancé pour l'affectation de voyages aux services d'agents, utilisant Google OR-Tools CP-SAT Solver.

## ✨ Fonctionnalités

### Module `gestion_voiture.py`

**Optimisation avec OR-Tools CP-SAT :**
- ✅ Maximisation du nombre de voyages affectés
- ✅ Respect des contraintes horaires des services
- ✅ Gestion du battement min/max entre voyages
- ✅ Vérification de la compatibilité des arrêts
- ✅ Garantie de non-chevauchement temporel
- ✅ Conservation des voyages déjà affectés
- ✅ Résolution parallèle (multi-threading)

### Module `tab5_ortools.py`

**Interface graphique améliorée :**
- 📊 Timeline visuelle des services
- ➕ Création manuelle de services
- 🔒 Tracking des voyages assignés (non réutilisables)
- ⏰ Contraintes horaires éditables
- 🤖 Optimisation automatique avec OR-Tools
- ❌ Suppression de voyages d'un service
- 💾 Export CSV du planning

## 📦 Installation

### Prérequis

```bash
pip install ortools customtkinter numpy --break-system-packages
```

### Structure des fichiers

```
projet/
├── gestion_voiture.py       # ✅ Module d'optimisation OR-Tools
├── tab5_ortools.py           # ✅ Interface graphique
├── tableauCSV.py             # Chargement CSV
├── objet.py                  # Classes voyage et service_agent
└── README_gestion_voiture.md # Ce fichier
```

## 🚀 Utilisation

### 1. Utilisation du module `gestion_voiture.py` seul

```python
from gestion_voiture import optimiser_affectation
from objet import voyage, service_agent

# Créer des voyages
voyages = [
    voyage("25", "V1", "Station A", "Station B", "06:00", "07:00"),
    voyage("25", "V2", "Station B", "Station C", "07:10", "08:00"),
    # ...
]

# Créer des services
services = [
    service_agent(num_service=1, type_service="matin"),
    service_agent(num_service=2, type_service="matin"),
]

# Ajouter des contraintes horaires (optionnel)
services[0].heure_debut_max = 6 * 60   # 06:00
services[0].heure_fin_max = 14 * 60    # 14:00

# Lancer l'optimisation
success, resultats = optimiser_affectation(
    voyages=voyages,
    services=services,
    battement_min=5,       # Battement minimum en minutes
    battement_max=50,      # Battement maximum (None = pas de limite)
    verifier_arrets=True,  # Vérifier compatibilité des arrêts
    temps_limite=60        # Temps limite en secondes
)

if success:
    print("✅ Optimisation réussie !")
    print(f"Voyages affectés : {resultats['nb_affectes']}")
    print(f"Temps : {resultats['temps']:.2f}s")
    
    # Les voyages sont automatiquement ajoutés aux services
    for service in services:
        print(service)
else:
    print("❌ Aucune solution trouvée")
```

### 2. Utilisation de l'interface graphique

```python
# Lancer l'interface
python tab5_ortools.py
```

**Workflow typique :**

1. **Charger les voyages** : Bouton "📂 Charger voyages CSV"
2. **Créer des services** : Bouton "➕ Nouveau Service"
   - Définir le type (matin/après-midi)
   - Définir les contraintes horaires (optionnel)
3. **Ajouter des voyages manuellement** :
   - Sélectionner des voyages (cocher ✓)
   - Cliquer "➡️ Ajouter au service"
4. **Optimiser automatiquement** : Bouton "🤖 Optimiser (OR-Tools)"
   - Configurer les paramètres
   - Lancer l'optimisation
5. **Exporter** : Bouton "💾 Exporter Planning"

## 🔧 Paramètres d'optimisation

### Battement minimum (`battement_min`)
- Temps minimum en minutes entre deux voyages consécutifs
- Permet au conducteur de se déplacer entre arrêts
- **Recommandé** : 5-10 minutes

### Battement maximum (`battement_max`)
- Temps maximum en minutes entre deux voyages consécutifs
- Évite les temps morts trop longs
- **Recommandé** : 30-50 minutes
- `None` = pas de limite

### Vérification des arrêts (`verifier_arrets`)
- Si `True`, vérifie que l'arrêt de fin d'un voyage correspond à l'arrêt de début du suivant
- Utilise les 3 premiers caractères de l'arrêt pour la comparaison
- **Recommandé** : `True` pour plus de réalisme

### Temps limite (`temps_limite`)
- Temps maximum de résolution en secondes
- OR-Tools retourne la meilleure solution trouvée dans ce temps
- **Recommandé** : 60-120 secondes pour de gros problèmes

## 📊 Performance

**Comparaison Algorithme Glouton vs OR-Tools :**

| Critère | Glouton | OR-Tools |
|---------|---------|----------|
| **Rapidité** | ⚡ Très rapide (< 1s) | 🐢 Plus lent (10-60s) |
| **Qualité** | 😐 Solution correcte | ⭐ Solution optimale |
| **Garantie** | ❌ Pas d'optimalité | ✅ Optimal si temps suffisant |
| **Contraintes** | ⚠️ Limitées | ✅ Toutes respectées |

**Cas d'usage :**
- **Glouton** : Prototypage rapide, petits problèmes (<50 voyages)
- **OR-Tools** : Production, grands problèmes, solution optimale requise

## 🎯 Exemples de contraintes

### Exemple 1 : Service du matin strict
```python
service_matin = service_agent(num_service=1, type_service="matin")
service_matin.heure_debut_max = 4 * 60   # 04:00
service_matin.heure_fin_max = 14 * 60    # 14:00
```

### Exemple 2 : Service de l'après-midi
```python
service_am = service_agent(num_service=2, type_service="apres_midi")
service_am.heure_debut_max = 12 * 60   # 12:00
service_am.heure_fin_max = 22 * 60     # 22:00
```

### Exemple 3 : Service sans contraintes
```python
service_libre = service_agent(num_service=3, type_service="matin")
# Pas de heure_debut_max ni heure_fin_max définis
```

## 🐛 Dépannage

### Problème : OR-Tools ne trouve pas de solution

**Causes possibles :**
1. Contraintes trop strictes
2. Battement maximum trop court
3. Pas assez de services pour tous les voyages

**Solutions :**
- Augmenter le temps limite
- Assouplir le battement maximum
- Créer plus de services
- Désactiver la vérification des arrêts si peu pertinente

### Problème : ImportError pour gestion_voiture

**Solution :**
```bash
# S'assurer que tous les fichiers sont dans le même dossier
ls -la
# Vérifier que gestion_voiture.py existe

# Tester l'import
python -c "from gestion_voiture import optimiser_affectation; print('OK')"
```

### Problème : OR-Tools trop lent

**Solutions :**
- Réduire le nombre de voyages (filtrer par ligne/période)
- Réduire le temps limite (accepter une solution sub-optimale)
- Utiliser l'algorithme glouton pour un premier essai

## 📝 Format CSV attendu

Le fichier CSV doit contenir les colonnes suivantes :

```csv
Ligne,Voy.,Début,Fin,De,À,Js srv
25,V1,06:00,07:00,Station A,Station B,LMaMeJV
25,V2,07:10,08:00,Station B,Station C,LMaMeJV
35,V3,06:30,07:30,Station A,Station D,LMaMeJV
```

**Colonnes obligatoires :**
- `Ligne` : Numéro de ligne
- `Voy.` : Numéro de voyage
- `Début` : Heure de début (HH:MM)
- `Fin` : Heure de fin (HH:MM)
- `De` : Arrêt de départ
- `À` : Arrêt d'arrivée
- `Js srv` : Jours de service (optionnel)

## 🔬 Test du module

Pour tester `gestion_voiture.py` :

```bash
python gestion_voiture.py
```

Ceci lance un test avec des voyages et services de démonstration.

## 📚 Documentation API

### Classe `OptimisateurServices`

```python
class OptimisateurServices:
    def __init__(self, voyages, services, battement_min=5, 
                 battement_max=50, verifier_arrets=True, 
                 temps_limite=60):
        """
        Args:
            voyages: Liste des objets voyage à affecter
            services: Liste des objets service_agent
            battement_min: Battement minimum en minutes
            battement_max: Battement maximum (None = pas de limite)
            verifier_arrets: Vérifier compatibilité des arrêts
            temps_limite: Temps limite en secondes
        """
    
    def resoudre(self) -> Tuple[bool, Dict]:
        """
        Returns:
            (success, resultats) où resultats contient:
                - status: Statut CP-SAT
                - affectations: {service_id: [voyage_indices]}
                - nb_affectes: Nombre total de voyages affectés
                - temps: Temps de résolution en secondes
                - objectif: Valeur de l'objectif
        """
```

### Fonction `optimiser_affectation`

Interface simplifiée pour une utilisation rapide.

```python
def optimiser_affectation(voyages, services, battement_min=5,
                         battement_max=50, verifier_arrets=True,
                         temps_limite=60) -> Tuple[bool, Dict]:
    """
    Lance l'optimisation et applique automatiquement la solution.
    
    Returns:
        (success, resultats)
    """
```

## 🎓 Concepts OR-Tools

### CP-SAT (Constraint Programming - SAT)

OR-Tools CP-SAT est un solveur de programmation par contraintes qui :
- Transforme le problème en SAT (Satisfiability)
- Utilise des techniques avancées (propagation de contraintes, backtracking)
- Garantit l'optimalité si le temps le permet
- Peut trouver des solutions approchées rapidement

### Variables de décision

Dans notre modèle : `x[i,j] = 1` si le voyage `i` est affecté au service `j`

### Contraintes

1. **Unicité** : Un voyage → Un service maximum
2. **Temporelle** : Pas de chevauchement dans un même service
3. **Battement** : Temps entre voyages respecté
4. **Arrêts** : Compatibilité des arrêts (optionnel)
5. **Horaires** : Respect des plages horaires des services
6. **Verrouillage** : Voyages déjà affectés non modifiables

### Objectif

Maximiser : Σ x[i,j] pour tous i,j (nombre total de voyages affectés)

## 📞 Support

Pour toute question ou problème :
1. Vérifier ce README
2. Tester avec l'exemple fourni
3. Vérifier les logs de la console (print statements)

## 🔄 Améliorations futures possibles

- [ ] Optimisation multi-objectifs (coût, équité, etc.)
- [ ] Prise en compte des pauses réglementaires
- [ ] Interface de visualisation Gantt améliorée
- [ ] Export vers d'autres formats (JSON, Excel)
- [ ] Analyse post-optimisation (statistiques détaillées)
- [ ] Sauvegarde/chargement de solutions

---

**Version** : 1.0  
**Auteur** : Développé avec OR-Tools CP-SAT  
**Date** : Janvier 2026
