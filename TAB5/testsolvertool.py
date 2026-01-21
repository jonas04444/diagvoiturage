"""
Solveur d'assignation de voyages aux services
============================================

Ce module utilise OR-Tools (Google) pour résoudre le problème d'assignation
de voyages à des services de transport en commun.

Contraintes gérées:
- Au moins 5 minutes entre chaque voyage
- Enchaînement des arrêts (un voyage commence où le précédent se termine)
- Respect des limites horaires de chaque service
- Gestion des services coupés (avec pause)
- Répartition équitable des voyages selon la durée des services

Utilisation:
    from solver import VoyageSolver, afficher_proposition
    from objet import voyage, service_agent

    # Créer vos voyages
    voyages = [voyage(...), voyage(...), ...]

    # Créer vos services avec leurs limites
    services = [service_agent(...), ...]

    # Résoudre
    solver = VoyageSolver(voyages, services)
    solutions = solver.resoudre(max_solutions=10)

    # Afficher
    for i, prop in enumerate(solutions, 1):
        afficher_proposition(prop, i)
"""

from ortools.sat.python import cp_model
from objet import service_agent, voyage, proposition,hlp

class SolutionCollector(cp_model.CpSolverSolutionCallback):
    """Collecte toutes les solutions trouvées par le solveur."""

    def __init__(self, variables, voyages, services, max_solutions=100):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._variables = variables  # variables[v][s] = 1 si voyage v assigné au service s
        self._voyages = voyages
        self._services = services
        self._solutions = []
        self._max_solutions = max_solutions
        self._solution_count = 0

    def on_solution_callback(self):
        if self._solution_count >= self._max_solutions:
            self.StopSearch()
            return

        # Créer une nouvelle proposition pour cette solution
        prop = proposition()

        for s_idx, service in enumerate(self._services):
            # Créer une copie du service pour cette solution
            new_service = service_agent(
                num_service=service.num_service,
                type_service=service.type_service
            )
            new_service.set_limites(service.heure_debut, service.heure_fin)
            if service.type_service == "coupé":
                new_service.set_coupure(service.heure_debut_coupure, service.heure_fin_coupure)

            # Ajouter les voyages assignés à ce service
            voyages_assignes = []
            for v_idx, v in enumerate(self._voyages):
                if self.Value(self._variables[v_idx][s_idx]) == 1:
                    voyages_assignes.append(v)

            # Trier par heure de début et ajouter au service
            voyages_assignes.sort(key=lambda x: x.hdebut)
            for v in voyages_assignes:
                new_service.ajouter_voyage(v)

            prop.ajout_service(new_service)

        self._solutions.append(prop)
        self._solution_count += 1

    def get_solutions(self):
        return self._solutions

    def solution_count(self):
        return self._solution_count


class VoyageSolver:
    """Solveur pour assigner les voyages aux services."""

    def __init__(self, voyages_disponibles, services, temps_minimum_entre_voyages=5):
        """
        Args:
            voyages_disponibles: Liste des voyages à assigner
            services: Liste des services (service_agent) avec leurs limites définies
            temps_minimum_entre_voyages: Temps minimum en minutes entre deux voyages (défaut: 5)
        """
        self.voyages = voyages_disponibles
        self.services = services
        self.temps_min = temps_minimum_entre_voyages
        self.model = cp_model.CpModel()
        self.variables = {}

    def _creer_variables(self):
        """Crée les variables de décision."""
        # x[v][s] = 1 si le voyage v est assigné au service s
        self.x = {}
        for v_idx in range(len(self.voyages)):
            self.x[v_idx] = {}
            for s_idx in range(len(self.services)):
                self.x[v_idx][s_idx] = self.model.NewBoolVar(f'x_{v_idx}_{s_idx}')

        # Variables d'ordre: order[v][s] = position du voyage v dans le service s
        self.order = {}
        max_voyages = len(self.voyages)
        for v_idx in range(len(self.voyages)):
            self.order[v_idx] = {}
            for s_idx in range(len(self.services)):
                self.order[v_idx][s_idx] = self.model.NewIntVar(0, max_voyages, f'order_{v_idx}_{s_idx}')

    def _contrainte_voyage_unique(self):
        """Chaque voyage est assigné à exactement un service."""
        for v_idx in range(len(self.voyages)):
            self.model.Add(sum(self.x[v_idx][s_idx] for s_idx in range(len(self.services))) == 1)

    def _contrainte_limites_service(self):
        """Les voyages doivent respecter les limites horaires du service."""
        for v_idx, v in enumerate(self.voyages):
            for s_idx, s in enumerate(self.services):
                # Si le voyage est assigné à ce service, il doit respecter les limites
                if s.heure_debut is not None:
                    # Si x[v][s] = 1, alors v.hdebut >= s.heure_debut
                    self.model.Add(v.hdebut >= s.heure_debut).OnlyEnforceIf(self.x[v_idx][s_idx])

                if s.heure_fin is not None:
                    # Si x[v][s] = 1, alors v.hfin <= s.heure_fin
                    self.model.Add(v.hfin <= s.heure_fin).OnlyEnforceIf(self.x[v_idx][s_idx])

                # Contrainte de coupure pour les services coupés
                if s.type_service == "coupé" and s.heure_debut_coupure is not None:
                    # Le voyage ne doit pas chevaucher la coupure
                    # Soit il finit avant la coupure, soit il commence après
                    finit_avant = self.model.NewBoolVar(f'finit_avant_{v_idx}_{s_idx}')
                    commence_apres = self.model.NewBoolVar(f'commence_apres_{v_idx}_{s_idx}')

                    self.model.Add(v.hfin <= s.heure_debut_coupure).OnlyEnforceIf(finit_avant)
                    self.model.Add(v.hfin > s.heure_debut_coupure).OnlyEnforceIf(finit_avant.Not())
                    self.model.Add(v.hdebut >= s.heure_fin_coupure).OnlyEnforceIf(commence_apres)
                    self.model.Add(v.hdebut < s.heure_fin_coupure).OnlyEnforceIf(commence_apres.Not())

                    # Si assigné à ce service, une des deux conditions doit être vraie
                    self.model.AddBoolOr([finit_avant, commence_apres]).OnlyEnforceIf(self.x[v_idx][s_idx])

    def _contrainte_enchainement_arrets(self):
        """
        Un voyage doit commencer là où se termine le précédent.
        Compare les 3 premiers caractères des arrêts.
        """
        for s_idx in range(len(self.services)):
            for v1_idx, v1 in enumerate(self.voyages):
                for v2_idx, v2 in enumerate(self.voyages):
                    if v1_idx == v2_idx:
                        continue

                    # Si v1 et v2 sont dans le même service et v1 est juste avant v2
                    both_in_service = self.model.NewBoolVar(f'both_{v1_idx}_{v2_idx}_{s_idx}')
                    self.model.AddBoolAnd([
                        self.x[v1_idx][s_idx],
                        self.x[v2_idx][s_idx]
                    ]).OnlyEnforceIf(both_in_service)
                    self.model.AddBoolOr([
                        self.x[v1_idx][s_idx].Not(),
                        self.x[v2_idx][s_idx].Not()
                    ]).OnlyEnforceIf(both_in_service.Not())

                    # v1 est chronologiquement avant v2 et directement consécutif
                    if v1.hfin <= v2.hdebut:
                        # Vérifier qu'il y a au moins 5 minutes entre les voyages
                        if v2.hdebut - v1.hfin < self.temps_min:
                            # Pas assez de temps entre ces deux voyages
                            # Ils ne peuvent pas être consécutifs dans le même service
                            # On vérifie s'il y a un voyage entre les deux
                            pass

                        # Vérifier l'enchaînement des arrêts
                        arret_fin_v1 = v1.arret_fin_id()
                        arret_debut_v2 = v2.arret_debut_id()

                        if arret_fin_v1 != arret_debut_v2:
                            # Ces voyages ne peuvent pas se suivre directement
                            # On doit vérifier qu'il y a un voyage entre eux
                            v1_before_v2 = self.model.NewBoolVar(f'v1_{v1_idx}_before_v2_{v2_idx}_s{s_idx}')

                            # v1 est juste avant v2 si aucun autre voyage n'est entre eux
                            intermediaires = []
                            for v3_idx, v3 in enumerate(self.voyages):
                                if v3_idx != v1_idx and v3_idx != v2_idx:
                                    if v1.hfin <= v3.hdebut and v3.hfin <= v2.hdebut:
                                        intermediaires.append(self.x[v3_idx][s_idx])

                            if not intermediaires:
                                # Pas de voyage intermédiaire possible
                                # Si les deux sont dans le même service, c'est interdit
                                self.model.AddBoolOr([
                                    self.x[v1_idx][s_idx].Not(),
                                    self.x[v2_idx][s_idx].Not()
                                ])

    def _contrainte_temps_minimum(self):
        """Au moins 5 minutes entre chaque voyage consécutif dans un service."""
        for s_idx in range(len(self.services)):
            for v1_idx, v1 in enumerate(self.voyages):
                for v2_idx, v2 in enumerate(self.voyages):
                    if v1_idx >= v2_idx:
                        continue

                    # Si v1 finit après le début de v2 - temps_min, ils ne peuvent pas
                    # être tous les deux dans le même service (chevauchement ou trop proche)
                    if v1.hfin > v2.hdebut - self.temps_min and v1.hdebut < v2.hfin:
                        # Chevauchement ou moins de 5 min d'écart
                        self.model.AddBoolOr([
                            self.x[v1_idx][s_idx].Not(),
                            self.x[v2_idx][s_idx].Not()
                        ])

    def _contrainte_repartition_equitable(self):
        """
        Répartir équitablement les voyages selon la durée des services.
        """
        # Calculer la durée totale et la durée de chaque service
        durees = []
        for s in self.services:
            if s.heure_debut is not None and s.heure_fin is not None:
                duree = s.heure_fin - s.heure_debut
                if s.type_service == "coupé" and s.heure_debut_coupure is not None:
                    duree -= (s.heure_fin_coupure - s.heure_debut_coupure)
                durees.append(duree)
            else:
                durees.append(480)  # 8h par défaut

        duree_totale = sum(durees)
        nb_voyages = len(self.voyages)

        # Calculer le nombre idéal de voyages par service
        nb_ideal = []
        for d in durees:
            ratio = d / duree_totale
            nb_ideal.append(int(nb_voyages * ratio))

        # Ajuster pour que la somme = nb_voyages
        while sum(nb_ideal) < nb_voyages:
            # Ajouter au service le plus long
            idx_max = durees.index(max(durees))
            nb_ideal[idx_max] += 1

        # Ajouter une contrainte souple (minimiser l'écart à l'idéal)
        ecarts = []
        for s_idx in range(len(self.services)):
            nb_voyages_service = sum(self.x[v_idx][s_idx] for v_idx in range(len(self.voyages)))
            ecart = self.model.NewIntVar(0, nb_voyages, f'ecart_{s_idx}')
            self.model.AddAbsEquality(ecart, nb_voyages_service - nb_ideal[s_idx])
            ecarts.append(ecart)

        # Minimiser la somme des écarts
        self.model.Minimize(sum(ecarts))

    def resoudre(self, max_solutions=10, timeout_seconds=60):
        """
        Résout le problème et retourne les solutions.

        Args:
            max_solutions: Nombre maximum de solutions à collecter
            timeout_seconds: Temps maximum de résolution en secondes

        Returns:
            Liste d'objets proposition contenant les solutions
        """
        self._creer_variables()
        self._contrainte_voyage_unique()
        self._contrainte_limites_service()
        self._contrainte_temps_minimum()
        self._contrainte_enchainement_arrets()
        self._contrainte_repartition_equitable()

        # Créer le solveur
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = timeout_seconds
        solver.parameters.enumerate_all_solutions = True

        # Collecter les solutions
        collector = SolutionCollector(self.x, self.voyages, self.services, max_solutions)

        status = solver.Solve(self.model, collector)

        print(f"Statut: {solver.StatusName(status)}")
        print(f"Nombre de solutions trouvées: {collector.solution_count()}")

        return collector.get_solutions()


def afficher_proposition(prop, numero=1):
    """Affiche une proposition de manière lisible."""
    print(f"\n{'='*60}")
    print(f"PROPOSITION {numero}")
    print('='*60)

    total_voyages = 0
    for service in prop.service:
        print(service)
        total_voyages += len(service.get_voyages())
        print()

    print(f"Total: {total_voyages} voyages assignés")


def filtrer_voyages_non_assignes(tous_les_voyages, services_existants):
    """
    Filtre les voyages qui ne sont pas encore assignés à un service.

    Args:
        tous_les_voyages: Liste de tous les voyages
        services_existants: Liste des services qui ont déjà des voyages assignés

    Returns:
        Liste des voyages non assignés
    """
    # Collecter tous les voyages déjà assignés
    voyages_assignes = set()
    for service in services_existants:
        for v in service.get_voyages():
            # Identifier par num_voyage et num_ligne
            voyages_assignes.add((v.num_ligne, v.num_voyage))

    # Retourner les voyages non assignés
    return [v for v in tous_les_voyages
            if (v.num_ligne, v.num_voyage) not in voyages_assignes]


def creer_services_vides(configs):
    """
    Crée une liste de services vides à partir d'une configuration.

    Args:
        configs: Liste de dictionnaires avec les clés:
            - num_service: Numéro du service
            - type_service: "matin", "apres-midi", "coupé", etc.
            - heure_debut: Heure de début (format "HH:MM")
            - heure_fin: Heure de fin (format "HH:MM")
            - heure_debut_coupure: (optionnel) Début de coupure
            - heure_fin_coupure: (optionnel) Fin de coupure

    Returns:
        Liste d'objets service_agent configurés
    """
    services = []
    for cfg in configs:
        s = service_agent(
            num_service=cfg.get('num_service'),
            type_service=cfg.get('type_service', 'matin')
        )

        # Convertir les heures en minutes
        h_debut = voyage.time_to_minutes(cfg['heure_debut'])
        h_fin = voyage.time_to_minutes(cfg['heure_fin'])
        s.set_limites(h_debut, h_fin)

        # Gérer la coupure si présente
        if 'heure_debut_coupure' in cfg and 'heure_fin_coupure' in cfg:
            h_coup_debut = voyage.time_to_minutes(cfg['heure_debut_coupure'])
            h_coup_fin = voyage.time_to_minutes(cfg['heure_fin_coupure'])
            s.set_coupure(h_coup_debut, h_coup_fin)

        services.append(s)

    return services


def resumer_propositions(propositions):
    """Affiche un résumé de toutes les propositions."""
    print(f"\n{'='*60}")
    print(f"RÉSUMÉ: {len(propositions)} proposition(s) trouvée(s)")
    print('='*60)

    for i, prop in enumerate(propositions, 1):
        total = sum(len(s.get_voyages()) for s in prop.service)
        repartition = [len(s.get_voyages()) for s in prop.service]
        print(f"  Proposition {i}: {total} voyages - Répartition: {repartition}")


# ============================================================
# GESTION DES HLP (Haut Le Pied)
# ============================================================

# ============================================================
# GESTION DES HLP (Haut Le Pied)
# ============================================================

from objet import hlp


def detecter_hlp_necessaires(prop):
    """
    Analyse une proposition et détecte les HLP nécessaires.

    Returns:
        Liste de dictionnaires décrivant chaque HLP nécessaire
    """
    hlp_requis = []

    for service in prop.service:
        voyages = sorted(service.get_voyages(), key=lambda v: v.hdebut)

        for i in range(len(voyages) - 1):
            v1 = voyages[i]
            v2 = voyages[i + 1]

            arret_fin = v1.arret_fin_id()
            arret_debut = v2.arret_debut_id()

            if arret_fin != arret_debut:
                hlp_requis.append({
                    'service': service,
                    'voyage_avant': v1,
                    'voyage_apres': v2,
                    'arret_depart': v1.arret_fin,  # ← c'était bon
                    'arret_arrivee': v2.arret_debut,  # ← CORRIGÉ : arret_debut au lieu de arret_depart
                    'temps_disponible': v2.hdebut - v1.hfin,
                    'heure_debut_possible': v1.hfin
                })

    return hlp_requis


def afficher_hlp_requis(hlp_requis):
    """Affiche les HLP nécessaires."""
    if not hlp_requis:
        print("\n✓ Aucun HLP nécessaire.")
        return

    print(f"\n⚠ {len(hlp_requis)} HLP nécessaire(s):")
    print("-" * 50)

    for i, h in enumerate(hlp_requis, 1):
        v1 = h['voyage_avant']
        v2 = h['voyage_apres']
        print(f"\n  HLP #{i} - Service {h['service'].num_service}:")
        print(f"    Après:  Voyage {v1.num_voyage} finit à {v1.arret_fin} ({voyage.minutes_to_time(v1.hfin)})")
        print(
            f"    Avant:  Voyage {v2.num_voyage} part de {v2.arret_debut} ({voyage.minutes_to_time(v2.hdebut)})")  # ← CORRIGÉ
        print(f"    Trajet: {h['arret_depart']} → {h['arret_arrivee']}")
        print(f"    Temps disponible: {h['temps_disponible']} min")

def configurer_hlp_interactif(hlp_requis):
    """
    Demande à l'utilisateur de configurer les HLP.

    Returns:
        True si tous les HLP ont été configurés, False sinon
    """
    if not hlp_requis:
        return True

    afficher_hlp_requis(hlp_requis)

    print("\n" + "=" * 50)
    reponse = input("Voulez-vous configurer ces HLP ? (o/n): ").strip().lower()

    if reponse != 'o':
        print("Configuration annulée.")
        return False

    for i, h in enumerate(hlp_requis, 1):
        print(f"\nHLP #{i}: {h['arret_depart']} → {h['arret_arrivee']}")
        print(f"  Temps disponible: {h['temps_disponible']} min (5 min de battement recommandées)")

        duree_max = h['temps_disponible'] - 5

        while True:
            reponse = input(f"  Durée du HLP en minutes (max {duree_max}, 'n' pour ignorer): ").strip()

            if reponse.lower() == 'n':
                print("  → HLP ignoré")
                break

            try:
                duree = int(reponse)
                if duree <= 0:
                    print("  ✗ La durée doit être positive")
                elif duree > duree_max:
                    print(f"  ✗ Trop long ! Maximum: {duree_max} min")
                else:
                    # Créer et ajouter le HLP au service
                    nouveau_hlp = hlp(
                        arret_depart=h['arret_depart'],
                        arret_arrivee=h['arret_arrivee'],
                        duree=duree,
                        heure_debut=h['heure_debut_possible']
                    )
                    h['service'].ajouter_hlp(nouveau_hlp)
                    print(f"  ✓ HLP ajouté ({duree} min)")
                    break
            except ValueError:
                print("  ✗ Entrez un nombre valide")

    return True


def analyser_et_configurer_proposition(prop, numero=1):
    """
    Affiche une proposition, détecte les HLP et permet de les configurer.
    """
    afficher_proposition(prop, numero)

    hlp_requis = detecter_hlp_necessaires(prop)

    if hlp_requis:
        configurer_hlp_interactif(hlp_requis)

        # Réafficher avec les HLP
        print("\n" + "=" * 60)
        print("PROPOSITION MISE À JOUR:")
        print("=" * 60)
        afficher_proposition(prop, numero)
    else:
        print("\n✓ Tous les enchaînements sont valides, aucun HLP nécessaire.")

    return prop

# Exemple d'utilisation
if __name__ == "__main__":
    print("="*60)
    print("EXEMPLE 1: Services matin et après-midi")
    print("="*60)

    # Créer quelques voyages de test
    voyages_test = [
        #voyage("C00A1", 1, "GOGAR", "CEN05", "05:00", "05:21"),
        voyage("C00A1", 2, "CEN18", "GOGAR", "04:30", "04:48"),
        voyage("C00A1", 3, "GOGAR", "CEN05", "05:30", "05:51"),
        voyage("C00A1", 4, "CEN18", "GOGAR", "05:00", "05:18"),
        voyage("C0068", 5, "JUMA2", "CEN05", "16:30", "17:02"),
        voyage("C00A1", 5, "GOGAR", "CEN05", "06:00", "06:21"),
        voyage("C00A1", 6, "CEN18", "GOGAR", "05:30", "05:48"),
        voyage("C00A1", 7, "GOGAR", "CEN05", "06:30", "06:51"),
        voyage("C00A1", 8, "CEN18", "GOGAR", "06:00", "06:18"),
        voyage("C00A1", 9, "GOGAR", "CEN05", "07:00", "07:21"),
        voyage("C00A1", 10, "CEN18", "GOGAR", "06:30", "06:48"),
        voyage("C00A1", 11, "GOGAR", "CEN05", "07:30", "07:51"),
        voyage("C00A1", 12, "CEN18", "GOGAR", "07:00", "07:18"),
        voyage("C00A1", 13, "GOGAR", "CEN05", "08:00", "08:21"),
        voyage("C00A1", 14, "CEN18", "GOGAR", "07:30", "07:48"),
        voyage("C00A1", 15, "GOGAR", "CEN05", "08:30", "08:51"),
        voyage("C00A1", 16, "CEN18", "GOGAR", "08:00", "08:18"),
        voyage("C00A1", 17, "GOGAR", "CEN05", "09:00", "09:21"),
        voyage("C00A1", 18, "CEN18", "GOGAR", "08:30", "08:48"),
        voyage("C00A1", 19, "GOGAR", "CEN05", "09:30", "09:51"),
        voyage("C00A1", 20, "CEN18", "GOGAR", "09:00", "09:18"),
        voyage("C00A1", 21, "GOGAR", "CEN05", "10:00", "10:21"),
        voyage("C00A1", 22, "CEN18", "GOGAR", "09:30", "09:48"),
        voyage("C00A1", 23, "GOGAR", "CEN05", "10:30", "10:51"),
        voyage("C00A1", 24, "CEN18", "GOGAR", "10:00", "10:18"),
        voyage("C00A1", 25, "GOGAR", "CEN05", "11:00", "11:21"),
        voyage("C00A1", 26, "CEN18", "GOGAR", "10:30", "10:48"),
        voyage("C00A1", 27, "GOGAR", "CEN05", "11:30", "11:51"),
        voyage("C00A1", 28, "CEN18", "GOGAR", "11:00", "11:18"),
        voyage("C00A1", 29, "GOGAR", "CEN05", "12:00", "12:21"),
        voyage("C00A1", 30, "CEN18", "GOGAR", "11:30", "11:48"),
        voyage("C00A1", 31, "GOGAR", "CEN05", "12:30", "12:51"),
        voyage("C00A1", 32, "CEN18", "GOGAR", "12:00", "12:18"),
        voyage("C00A1", 33, "GOGAR", "CEN05", "13:00", "13:21"),
        voyage("C00A1", 34, "CEN18", "GOGAR", "12:30", "12:48"),
        ]
    # Créer les services avec la fonction utilitaire
    configs_services = [
        {
            'num_service': 1,
            'type_service': 'matin',
            'heure_debut': '04:00',
            'heure_fin': '23:00'
        },
        {
            'num_service': 2,
            'type_service': 'apres-midi',
            'heure_debut': '04:00',
            'heure_fin': '23:00'
        },
        {
            'num_service': 3,
            'type_service': 'apres-midi',
            'heure_debut': '04:00',
            'heure_fin': '23:00'
        }
    ]
    servicetest = service_agent(1,"matin")
    servicetest.set_limites(voyage.time_to_minutes('04:00'), voyage.time_to_minutes('12:00'))
    v = voyage("C00A1", 1, "GOGAR", "CEN05", "05:00", "05:21")
    servicetest.ajouter_voyage(v)

    tous_service = configs_services + [servicetest]
    services = creer_services_vides(tous_service)

    # Résoudre
    solver = VoyageSolver(voyages_test, services)
    solutions = solver.resoudre(max_solutions=10)

    # Résumé
    resumer_propositions(solutions)

    # Sélection et configuration
    if solutions:
        print("\n" + "=" * 60)
        choix = input(f"Quelle proposition analyser ? (1-{len(solutions)}): ").strip()

        try:
            idx = int(choix) - 1
            if 0 <= idx < len(solutions):
                analyser_et_configurer_proposition(solutions[idx], idx + 1)
            else:
                print("Numéro invalide")
        except ValueError:
            print("Entrez un numéro valide")
