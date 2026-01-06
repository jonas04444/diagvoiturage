"""
GESTION_VOITURE.PY - Module d'optimisation avec OR-Tools
Optimise l'affectation des voyages aux services d'agents
"""

from ortools.sat.python import cp_model
from objet import voyage, service_agent
from typing import List, Tuple, Optional, Dict
import time


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Callback pour afficher les solutions trouvées pendant la résolution"""
    
    def __init__(self, limit=5):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._solution_count = 0
        self._solution_limit = limit

    def on_solution_callback(self):
        self._solution_count += 1
        print(f"Solution {self._solution_count} trouvée (objectif: {self.ObjectiveValue()})")
        if self._solution_count >= self._solution_limit:
            self.StopSearch()

    def solution_count(self):
        return self._solution_count


def voyages_compatibles_simple(v1: voyage, v2: voyage, battement_min: int, battement_max: Optional[int] = None) -> bool:
    """
    Vérifie si deux voyages consécutifs sont compatibles (version simplifiée)
    
    Args:
        v1: Premier voyage (doit finir avant v2)
        v2: Deuxième voyage
        battement_min: Battement minimum en minutes
        battement_max: Battement maximum en minutes (None = pas de limite)
    
    Returns:
        True si compatible, False sinon
    """
    if v1.hfin > v2.hdebut:
        return False
    
    battement = v2.hdebut - v1.hfin
    
    if battement < battement_min:
        return False
    
    if battement_max is not None and battement > battement_max:
        return False
    
    return True


def verifier_compatibilite_arrets(v1: voyage, v2: voyage) -> bool:
    """
    Vérifie si les arrêts de deux voyages consécutifs sont compatibles
    Le voyage v1 doit finir au même arrêt (ou proche) où v2 commence
    
    Args:
        v1: Premier voyage
        v2: Deuxième voyage
    
    Returns:
        True si les arrêts sont compatibles
    """
    # Comparer les 3 premiers caractères des arrêts (codes d'arrêt)
    arret_fin_v1 = v1.arret_fin_id()
    arret_debut_v2 = v2.arret_debut_id()
    
    return arret_fin_v1 == arret_debut_v2


class OptimisateurServices:
    """
    Classe pour optimiser l'affectation des voyages aux services avec OR-Tools
    """
    
    def __init__(self, 
                 voyages: List[voyage],
                 services: List[service_agent],
                 battement_min: int = 5,
                 battement_max: Optional[int] = 50,
                 verifier_arrets: bool = True,
                 temps_limite: int = 60):
        """
        Initialise l'optimisateur
        
        Args:
            voyages: Liste des voyages à affecter
            services: Liste des services existants
            battement_min: Battement minimum en minutes
            battement_max: Battement maximum en minutes (None = pas de limite)
            verifier_arrets: Si True, vérifie la compatibilité des arrêts
            temps_limite: Temps limite de résolution en secondes
        """
        self.voyages = voyages
        self.services = services
        self.battement_min = battement_min
        self.battement_max = battement_max
        self.verifier_arrets = verifier_arrets
        self.temps_limite = temps_limite
        
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.variables = {}
        
    def creer_variables(self):
        """Crée les variables de décision pour le modèle"""
        print("📊 Création des variables...")
        
        # Variable x[v][s] = 1 si voyage v est affecté au service s
        self.x = {}
        for i, v in enumerate(self.voyages):
            for j, s in enumerate(self.services):
                self.x[i, j] = self.model.NewBoolVar(f'x_v{i}_s{j}')
        
        print(f"   ✓ {len(self.voyages)} voyages × {len(self.services)} services")
        
    def ajouter_contraintes_base(self):
        """Ajoute les contraintes de base"""
        print("🔧 Ajout des contraintes de base...")
        
        # Contrainte 1: Chaque voyage est affecté à AU PLUS un service
        for i in range(len(self.voyages)):
            self.model.Add(sum(self.x[i, j] for j in range(len(self.services))) <= 1)
        
        print("   ✓ Un voyage → Un service maximum")
        
    def ajouter_contraintes_temporelles(self):
        """Ajoute les contraintes de chevauchement temporel"""
        print("⏰ Ajout des contraintes temporelles...")
        
        nb_contraintes = 0
        
        # Deux voyages du même service ne peuvent pas se chevaucher
        for i in range(len(self.voyages)):
            for k in range(i + 1, len(self.voyages)):
                v1 = self.voyages[i]
                v2 = self.voyages[k]
                
                # Vérifier s'ils se chevauchent
                if not (v1.hfin <= v2.hdebut or v2.hfin <= v1.hdebut):
                    # Ils se chevauchent, ils ne peuvent pas être dans le même service
                    for j in range(len(self.services)):
                        self.model.Add(self.x[i, j] + self.x[k, j] <= 1)
                    nb_contraintes += 1
        
        print(f"   ✓ {nb_contraintes} paires incompatibles identifiées")
        
    def ajouter_contraintes_battement(self):
        """Ajoute les contraintes de battement entre voyages"""
        print("🚗 Ajout des contraintes de battement...")
        
        nb_contraintes = 0
        
        for i in range(len(self.voyages)):
            for k in range(len(self.voyages)):
                if i == k:
                    continue
                
                v1 = self.voyages[i]
                v2 = self.voyages[k]
                
                # Si v1 finit avant v2, vérifier le battement
                if v1.hfin <= v2.hdebut:
                    battement = v2.hdebut - v1.hfin
                    
                    # Battement trop court ou trop long
                    if battement < self.battement_min or (self.battement_max and battement > self.battement_max):
                        for j in range(len(self.services)):
                            # Si v1 est dans le service j, alors v2 ne peut pas y être
                            self.model.AddImplication(self.x[i, j], self.x[k, j].Not())
                        nb_contraintes += 1
        
        print(f"   ✓ {nb_contraintes} incompatibilités de battement")
        
    def ajouter_contraintes_arrets(self):
        """Ajoute les contraintes de compatibilité des arrêts"""
        if not self.verifier_arrets:
            return
        
        print("🚏 Ajout des contraintes d'arrêts...")
        
        nb_contraintes = 0
        
        for i in range(len(self.voyages)):
            for k in range(len(self.voyages)):
                if i == k:
                    continue
                
                v1 = self.voyages[i]
                v2 = self.voyages[k]
                
                # Si v1 finit avant v2
                if v1.hfin <= v2.hdebut:
                    # Vérifier si les arrêts sont incompatibles
                    if not verifier_compatibilite_arrets(v1, v2):
                        for j in range(len(self.services)):
                            self.model.AddImplication(self.x[i, j], self.x[k, j].Not())
                        nb_contraintes += 1
        
        print(f"   ✓ {nb_contraintes} incompatibilités d'arrêts")
        
    def ajouter_contraintes_horaires_services(self):
        """Ajoute les contraintes horaires des services"""
        print("📅 Ajout des contraintes horaires des services...")
        
        nb_contraintes = 0
        
        for j, service in enumerate(self.services):
            h_debut = getattr(service, 'heure_debut_max', None)
            h_fin = getattr(service, 'heure_fin_max', None)
            
            if h_debut is None or h_fin is None:
                continue
            
            for i, v in enumerate(self.voyages):
                # Si le voyage est en dehors des contraintes horaires du service
                if v.hdebut < h_debut or v.hfin > h_fin:
                    # Il ne peut pas être affecté à ce service
                    self.model.Add(self.x[i, j] == 0)
                    nb_contraintes += 1
        
        if nb_contraintes > 0:
            print(f"   ✓ {nb_contraintes} exclusions horaires")
        else:
            print("   ⚠ Aucune contrainte horaire définie")
            
    def ajouter_contraintes_voyages_existants(self):
        """Empêche de réaffecter les voyages déjà dans les services"""
        print("🔒 Verrouillage des voyages existants...")
        
        nb_verrous = 0
        
        for j, service in enumerate(self.services):
            for voyage_existant in service.voyages:
                # Trouver l'index de ce voyage dans la liste
                for i, v in enumerate(self.voyages):
                    if v is voyage_existant:
                        # Forcer cette affectation
                        self.model.Add(self.x[i, j] == 1)
                        nb_verrous += 1
                        break
        
        print(f"   ✓ {nb_verrous} voyages déjà affectés verrouillés")
        
    def definir_objectif(self):
        """Définit la fonction objectif à maximiser"""
        print("🎯 Définition de l'objectif...")
        
        # Objectif: maximiser le nombre de voyages affectés
        self.model.Maximize(
            sum(self.x[i, j] for i in range(len(self.voyages)) for j in range(len(self.services)))
        )
        
        print("   ✓ Maximisation du nombre de voyages affectés")
        
    def resoudre(self) -> Tuple[bool, Dict]:
        """
        Résout le problème d'optimisation
        
        Returns:
            (success, resultats) où resultats contient:
                - status: Statut de la résolution
                - affectations: Dict {service_id: [voyage_indices]}
                - nb_affectes: Nombre de voyages affectés
                - temps: Temps de résolution
        """
        print("\n" + "="*70)
        print("🚀 LANCEMENT DE L'OPTIMISATION OR-TOOLS")
        print("="*70)
        
        debut = time.time()
        
        # Construction du modèle
        self.creer_variables()
        self.ajouter_contraintes_base()
        self.ajouter_contraintes_temporelles()
        self.ajouter_contraintes_battement()
        self.ajouter_contraintes_arrets()
        self.ajouter_contraintes_horaires_services()
        self.ajouter_contraintes_voyages_existants()
        self.definir_objectif()
        
        # Configuration du solver
        self.solver.parameters.max_time_in_seconds = self.temps_limite
        self.solver.parameters.log_search_progress = True
        self.solver.parameters.num_search_workers = 4  # Parallélisation
        
        print(f"\n⚙️ Paramètres du solver:")
        print(f"   Temps limite: {self.temps_limite}s")
        print(f"   Workers: 4")
        
        # Résolution
        print("\n🔍 Résolution en cours...\n")
        status = self.solver.Solve(self.model)
        
        temps_resolution = time.time() - debut
        
        # Analyse des résultats
        resultats = {
            'status': status,
            'affectations': {},
            'nb_affectes': 0,
            'temps': temps_resolution,
            'objectif': 0
        }
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            print("\n✅ SOLUTION TROUVÉE !")
            print("="*70)
            
            # Extraire les affectations
            for j in range(len(self.services)):
                resultats['affectations'][j] = []
                
            for i in range(len(self.voyages)):
                for j in range(len(self.services)):
                    if self.solver.Value(self.x[i, j]) == 1:
                        resultats['affectations'][j].append(i)
                        resultats['nb_affectes'] += 1
            
            resultats['objectif'] = self.solver.ObjectiveValue()
            
            print(f"\n📊 STATISTIQUES:")
            print(f"   Voyages affectés: {resultats['nb_affectes']} / {len(self.voyages)}")
            print(f"   Objectif: {resultats['objectif']}")
            print(f"   Temps: {temps_resolution:.2f}s")
            print(f"   Status: {'OPTIMAL' if status == cp_model.OPTIMAL else 'FEASIBLE'}")
            
            # Détails par service
            print(f"\n📋 AFFECTATIONS PAR SERVICE:")
            for j, service in enumerate(self.services):
                nb = len(resultats['affectations'][j])
                print(f"   Service {service.num_service}: {nb} voyage(s)")
            
            print("="*70)
            return True, resultats
            
        else:
            print("\n❌ AUCUNE SOLUTION TROUVÉE")
            print("="*70)
            print(f"   Status: {self.solver.StatusName(status)}")
            print(f"   Temps: {temps_resolution:.2f}s")
            print("="*70)
            return False, resultats
    
    def appliquer_solution(self, resultats: Dict):
        """
        Applique la solution trouvée aux services
        
        Args:
            resultats: Dictionnaire retourné par resoudre()
        """
        print("\n📝 Application de la solution...")
        
        for j, service in enumerate(self.services):
            voyages_a_ajouter = []
            
            for i in resultats['affectations'][j]:
                v = self.voyages[i]
                # Vérifier que le voyage n'est pas déjà dans le service
                if v not in service.voyages:
                    voyages_a_ajouter.append(v)
            
            # Ajouter les nouveaux voyages
            for v in voyages_a_ajouter:
                service.ajout_voyages(v)
                print(f"   ✓ V{v.num_voyage} → Service {service.num_service}")


def optimiser_affectation(voyages: List[voyage],
                         services: List[service_agent],
                         battement_min: int = 5,
                         battement_max: Optional[int] = 50,
                         verifier_arrets: bool = True,
                         temps_limite: int = 60) -> Tuple[bool, Dict]:
    """
    Fonction principale d'optimisation (interface simplifiée)
    
    Args:
        voyages: Liste des voyages à affecter
        services: Liste des services
        battement_min: Battement minimum en minutes
        battement_max: Battement maximum (None = pas de limite)
        verifier_arrets: Vérifier la compatibilité des arrêts
        temps_limite: Temps limite en secondes
    
    Returns:
        (success, resultats)
    """
    optimiseur = OptimisateurServices(
        voyages=voyages,
        services=services,
        battement_min=battement_min,
        battement_max=battement_max,
        verifier_arrets=verifier_arrets,
        temps_limite=temps_limite
    )
    
    success, resultats = optimiseur.resoudre()
    
    if success:
        optimiseur.appliquer_solution(resultats)
    
    return success, resultats


# ================== TESTS ==================
if __name__ == "__main__":
    print("🧪 Test du module gestion_voiture.py")
    print("="*70)
    
    # Créer des voyages de test
    voyages_test = [
        voyage("25", "V1", "Station A", "Station B", "06:00", "07:00"),
        voyage("25", "V2", "Station B", "Station C", "07:10", "08:00"),
        voyage("35", "V3", "Station A", "Station D", "06:30", "07:30"),
        voyage("25", "V4", "Station C", "Station A", "08:15", "09:00"),
        voyage("43", "V5", "Station E", "Station F", "09:00", "10:00"),
    ]
    
    # Créer des services de test
    services_test = [
        service_agent(num_service=1, type_service="matin"),
        service_agent(num_service=2, type_service="matin"),
    ]
    
    # Ajouter des contraintes horaires
    services_test[0].heure_debut_max = 6 * 60  # 06:00
    services_test[0].heure_fin_max = 10 * 60   # 10:00
    services_test[1].heure_debut_max = 6 * 60
    services_test[1].heure_fin_max = 10 * 60
    
    print(f"\n📊 Configuration du test:")
    print(f"   Voyages: {len(voyages_test)}")
    print(f"   Services: {len(services_test)}")
    
    # Lancer l'optimisation
    success, resultats = optimiser_affectation(
        voyages=voyages_test,
        services=services_test,
        battement_min=5,
        battement_max=50,
        verifier_arrets=True,
        temps_limite=30
    )
    
    # Afficher les résultats
    if success:
        print("\n✅ Test réussi !")
        for service in services_test:
            print(f"\n{service}")
    else:
        print("\n❌ Test échoué - Aucune solution trouvée")
