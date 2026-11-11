# 🚀 GUIDE DE DÉMARRAGE RAPIDE

## ⚡ Installation en 3 minutes

### 1. Installer OR-Tools
```bash
pip install ortools --break-system-packages
```

### 2. Placer les fichiers
```
votre_projet/
├── objet.py                    # VOS FICHIERS EXISTANTS
├── tableauCSV.py               # VOS FICHIERS EXISTANTS
├── gestion_voiture.py          # ✅ NOUVEAU
├── tab5_ortools.py             # ✅ NOUVEAU
└── README_gestion_voiture.md   # ✅ DOCUMENTATION
```

### 3. Tester
```bash
# Test du module de base
python gestion_voiture.py

# Test de comparaison
python exemple_comparaison.py

# Lancer l'interface graphique
python tab5_ortools.py
```

---

## 📝 Premier Exemple (5 lignes de code)

```python
from gestion_voiture import optimiser_affectation
from objet import voyage, service_agent

# Créer des voyages
voyages = [
    voyage("25", "V1", "Gare", "Centre", "06:00", "07:00"),
    voyage("25", "V2", "Centre", "Nord", "07:10", "08:00"),
]

# Créer des services
services = [
    service_agent(num_service=1, type_service="matin"),
]

# Optimiser !
success, resultats = optimiser_affectation(voyages, services)

if success:
    print(f"✅ {resultats['nb_affectes']} voyages affectés !")
```

---

## 🎯 Utilisation avec votre code existant

### Option 1 : Remplacer l'algorithme glouton

Dans votre fichier principal :

```python
# AVANT
from tab5 import Tab5CreationManuelle

# APRÈS
from tab5_ortools import Tab5CreationManuelle
```

C'est tout ! 🎉

### Option 2 : Utiliser les deux (mode hybride)

```python
import tkinter as tk
from tab5 import Tab5CreationManuelle as Tab5Glouton
from tab5_ortools import Tab5CreationManuelle as Tab5ORTools

root = tk.Tk()

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# Onglet avec algorithme glouton
tab_glouton = Tab5Glouton(notebook)
notebook.add(tab_glouton, text="Création Manuelle (Glouton)")

# Onglet avec OR-Tools
tab_ortools = Tab5ORTools(notebook)
notebook.add(tab_ortools, text="Création Manuelle (OR-Tools)")

root.mainloop()
```

---

## 🔧 Configuration Rapide

### Paramètres par défaut (recommandés)
```python
optimiser_affectation(
    voyages=voyages,
    services=services,
    battement_min=5,        # 5 minutes minimum entre voyages
    battement_max=50,       # 50 minutes maximum
    verifier_arrets=True,   # Vérifier compatibilité des arrêts
    temps_limite=60         # 60 secondes max
)
```

### Paramètres relaxés (plus de solutions)
```python
optimiser_affectation(
    voyages=voyages,
    services=services,
    battement_min=3,        # Plus permissif
    battement_max=None,     # Pas de limite max
    verifier_arrets=False,  # Ne pas vérifier les arrêts
    temps_limite=120        # Plus de temps pour optimiser
)
```

### Paramètres stricts (qualité maximale)
```python
optimiser_affectation(
    voyages=voyages,
    services=services,
    battement_min=10,       # Plus de temps entre voyages
    battement_max=30,       # Temps mort limité
    verifier_arrets=True,   # Vérifier les arrêts
    temps_limite=180        # Beaucoup de temps pour optimiser
)
```

---

## 🎨 Interface Graphique - Guide Visual

### 1. Charger les voyages
![Bouton: 📂 Charger voyages CSV]

### 2. Créer des services
![Bouton: ➕ Nouveau Service]
- Choisir le type (matin/après-midi)
- Définir contraintes horaires (ex: 06:00 - 14:00)

### 3. Optimiser avec OR-Tools
![Bouton: 🤖 Optimiser (OR-Tools)]
- Configurer les paramètres
- Cliquer "🚀 Lancer l'optimisation OR-Tools"
- Attendre 10-60 secondes
- ✅ Résultat affiché !

### 4. Ajuster manuellement (optionnel)
- Sélectionner un service (bouton ✏️)
- Ajouter/retirer des voyages
- Éditer les contraintes (bouton ⏰)

### 5. Exporter
![Bouton: 💾 Exporter Planning]

---

## 💡 Conseils Pratiques

### Quand utiliser l'algorithme glouton ?
- Prototypage rapide
- Moins de 50 voyages
- Solution "suffisamment bonne" acceptable

### Quand utiliser OR-Tools ?
- Planning final de production
- Plus de 50 voyages
- Besoin d'optimisation maximale
- OK d'attendre 1-2 minutes

### Workflow recommandé
1. Créer les services manuellement
2. Ajouter manuellement quelques voyages "évidents"
3. Lancer OR-Tools pour compléter automatiquement
4. Ajuster manuellement si besoin
5. Exporter

---

## 🐛 Problèmes Courants

### "Module 'ortools' not found"
```bash
pip install ortools --break-system-packages
```

### "Aucune solution trouvée"
- Vérifier que les contraintes horaires sont cohérentes
- Augmenter le battement max
- Créer plus de services
- Désactiver la vérification des arrêts

### OR-Tools trop lent
- Réduire le temps limite à 30s
- Filtrer les voyages (par ligne ou période)
- Utiliser l'algorithme glouton pour un premier essai

---

## 📊 Voir les Résultats

### Dans le terminal
L'optimisation affiche automatiquement :
```
🚀 LANCEMENT DE L'OPTIMISATION OR-TOOLS
======================================================================
📊 Création des variables...
   ✓ 20 voyages × 3 services

🔧 Ajout des contraintes de base...
   ✓ Un voyage → Un service maximum

⏰ Ajout des contraintes temporelles...
   ✓ 12 paires incompatibles identifiées

...

✅ SOLUTION TROUVÉE !
======================================================================

📊 STATISTIQUES:
   Voyages affectés: 18 / 20
   Objectif: 18
   Temps: 2.34s
   Status: OPTIMAL
```

### Dans l'interface
- Timeline visuelle mise à jour
- Statistiques du service
- Liste détaillée des voyages

---

## 📚 Documentation Complète

- **README_gestion_voiture.md** : Documentation complète du module
- **AMELIORATIONS.md** : Détails des améliorations apportées
- **exemple_comparaison.py** : Tests et benchmarks

---

## ✅ Checklist de Démarrage

- [ ] OR-Tools installé
- [ ] Fichiers copiés dans le projet
- [ ] Test de `gestion_voiture.py` réussi
- [ ] Test de `exemple_comparaison.py` réussi
- [ ] Interface graphique testée
- [ ] Premier planning créé avec succès

---

## 🎉 Félicitations !

Vous êtes maintenant prêt à utiliser OR-Tools pour optimiser vos plannings de voyages !

**Prochaine étape :** Lire `README_gestion_voiture.md` pour des cas d'usage avancés.

---

**Temps de lecture :** 5 minutes  
**Temps de mise en place :** 10 minutes  
**Niveau :** Débutant ✅
