from ortools.sat.python import cp_model


class service_agent:

    def __init__(self, num_service=None):
        self.voyages = []
        self.num_service = num_service

    def ajout_voyages(self, voyage):
        self.voyages.append(voyage)

    def get_voyages(self):
        return self.voyages

    def duree_services(self):
        if not self.voyages:
            return 0
        debut = min(v.hdebut for v in self.voyages)
        fin = max(v.hfin for v in self.voyages)
        return fin - debut

    def __str__(self):
        if not self.voyages:
            return f"Service {self.num_service}: vide"

        voyages_chronologiques = sorted(self.voyages, key=lambda v: v.hdebut)
        duree = self.duree_services()

        result = f"service {self.num_service}: {len(voyages_chronologiques)} voyages, "
        result += f"duree totale: {duree} min ({duree // 60}h{duree % 60:02d})\n"

        for v in voyages_chronologiques:
            hdebut_str = voyage.minutes_to_time(v.hdebut)
            hfin_str = voyage.minutes_to_time(v.hfin)
            result += f"  • Voyage {v.num_voyage}: {v.arret_debut} -> {v.arret_fin} "
            result += f"({hdebut_str} - {hfin_str})\n"

        return result.rstrip()


class voyage:

    def __init__(self, num_ligne, num_voyage, arret_debut, arret_fin, heure_debut, heure_fin):
        self.num_ligne = num_ligne
        self.num_voyage = num_voyage
        self.arret_debut = arret_debut
        self.arret_fin = arret_fin
        self.hdebut = self.time_to_minutes(heure_debut)
        self.hfin = self.time_to_minutes(heure_fin)

    def arret_debut_id(self):
        return self.arret_debut[:3]

    def arret_fin_id(self):
        return self.arret_fin[:3]

    @staticmethod
    def time_to_minutes(time_str):
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    @staticmethod
    def minutes_to_time(minutes: int) -> str:
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}h{m:02d}"


def valider_service(voyages, battement_minimum, verifier_arrets=True):
    """
    Valide qu'un ensemble de voyages peut former un service valide.
    Un service est valide si on peut ordonner les voyages de manière à ce que :
    - Les voyages ne se chevauchent pas
    - Le temps entre deux voyages consécutifs >= battement_minimum
    - L'arrêt de fin d'un voyage = l'arrêt de début du suivant (si verifier_arrets)

    Returns:
        (bool, list): (True si valide, ordre des voyages si valide)
    """
    if len(voyages) == 0:
        return True, []
    if len(voyages) == 1:
        return True, list(voyages)

    # Vérifier qu'il n'y a pas de chevauchement
    voyages_list = list(voyages)
    for i in range(len(voyages_list)):
        for j in range(i + 1, len(voyages_list)):
            vi = voyages_list[i]
            vj = voyages_list[j]
            if vi.hdebut < vj.hfin and vj.hdebut < vi.hfin:
                return False, []

    # Essayer de construire une chaîne valide avec backtracking
    # On commence toujours par le voyage le plus tôt
    def construire_chaine(chaine_actuelle, restants):
        if not restants:
            return True, chaine_actuelle

        dernier = chaine_actuelle[-1] if chaine_actuelle else None

        # Si c'est le premier voyage, on commence toujours par le voyage le plus tôt
        if dernier is None:
            # Trouver le voyage avec l'heure de début la plus tôt
            voyage_plus_tot = min(restants, key=lambda x: x.hdebut)
            nouveau_restants = restants.copy()
            nouveau_restants.remove(voyage_plus_tot)
            valide, resultat = construire_chaine([voyage_plus_tot], nouveau_restants)
            if valide:
                return True, resultat
        else:
            # Chercher un voyage qui peut suivre le dernier
            for v in sorted(restants, key=lambda x: x.hdebut):
                # Vérifier que le voyage ne chevauche pas avec ceux déjà dans la chaîne
                chevauche = False
                for v_existant in chaine_actuelle:
                    if v.hdebut < v_existant.hfin and v_existant.hdebut < v.hfin:
                        chevauche = True
                        break

                if chevauche:
                    continue

                # Vérifier les contraintes de temps et d'arrêts
                peut_suivre_directement = False
                peut_suivre_avec_pont = False
                v_pont_candidat = None

                if v.hdebut >= dernier.hfin:
                    temps_entre = v.hdebut - dernier.hfin
                    if temps_entre >= battement_minimum:
                        # Vérifier si les arrêts correspondent directement
                        if not verifier_arrets or dernier.arret_fin_id() == v.arret_debut_id():
                            peut_suivre_directement = True
                        else:
                            # Vérifier s'il existe un voyage dans restants qui peut servir de pont
                            # entre dernier et v
                            for v_pont in restants:
                                if v_pont == v:
                                    continue
                                # Vérifier que v_pont peut être entre dernier et v
                                if (dernier.hfin <= v_pont.hdebut and v_pont.hfin <= v.hdebut and
                                        dernier.arret_fin_id() == v_pont.arret_debut_id() and
                                        v_pont.arret_fin_id() == v.arret_debut_id()):
                                    # v_pont peut servir de pont
                                    peut_suivre_avec_pont = True
                                    v_pont_candidat = v_pont
                                    break

                # Essayer d'abord la connexion directe
                if peut_suivre_directement:
                    nouveau_restants = restants.copy()
                    nouveau_restants.remove(v)
                    valide, resultat = construire_chaine(chaine_actuelle + [v], nouveau_restants)
                    if valide:
                        return True, resultat

                # Ensuite essayer avec un pont si disponible
                if peut_suivre_avec_pont and v_pont_candidat:
                    nouveau_restants = restants.copy()
                    nouveau_restants.remove(v_pont_candidat)
                    nouveau_restants.remove(v)
                    # Ajouter d'abord le pont, puis v
                    valide, resultat = construire_chaine(chaine_actuelle + [v_pont_candidat, v], nouveau_restants)
                    if valide:
                        return True, resultat

        return False, []

    valide, chaine = construire_chaine([], set(voyages_list))
    return valide, chaine


def solvertest(listes, battement_minimum, verifier_arrets=True, max_solutions=10,
               nb_services_matin=2, nb_services_apres_midi=2, heure_separation="12:00"):
    """
    Résout le problème d'optimisation pour maximiser le nombre de voyages par service.

    Args:
        listes: Liste des voyages à assigner
        battement_minimum: Temps minimum (en minutes) entre deux voyages consécutifs
        verifier_arrets: Si True, vérifie que les arrêts se connectent correctement
        max_solutions: Nombre maximum de solutions à trouver
        nb_services_matin: Nombre de services imposé pour le matin (None = pas de contrainte)
        nb_services_apres_midi: Nombre de services imposé pour l'après-midi (None = pas de contrainte)
        heure_separation: Heure de séparation matin/après-midi (format "HH:MM", défaut "12:00")

    Returns:
        Liste de solutions, chaque solution étant une liste de services
    """
    if not listes:
        return []

    model = cp_model.CpModel()
    n = len(listes)

    # Variables de décision: service[i] = numéro du service auquel le voyage i est assigné
    # On limite le nombre de services possibles à n (pire cas: un service par voyage)
    max_services = n
    service = [model.NewIntVar(0, max_services - 1, f"service{i}") for i in range(n)]

    # Variable pour le nombre maximum de services utilisés (à minimiser)
    max_service_utilise = model.NewIntVar(0, max_services - 1, "max_service_utilise")

    # Contrainte: max_service_utilise >= service[i] pour tout i
    for i in range(n):
        model.Add(max_service_utilise >= service[i])

    # Contraintes entre paires de voyages
    for i in range(n):
        for j in range(i + 1, n):
            vi = listes[i]
            vj = listes[j]

            # Contrainte 1: Les voyages qui se chevauchent ne peuvent pas être dans le même service
            chevauchement = (
                    vi.hdebut < vj.hfin and
                    vj.hdebut < vi.hfin
            )

            if chevauchement:
                model.Add(service[i] != service[j])
                continue

            # Contrainte 2: Si vj se termine avant vi
            if vj.hfin <= vi.hdebut:
                temps_entre = vi.hdebut - vj.hfin
                # Si le temps entre est insuffisant (< battement_minimum),
                # ils ne peuvent pas être dans le même service
                if temps_entre < battement_minimum:
                    model.Add(service[i] != service[j])
                    continue

                # Si le temps est suffisant ET qu'on vérifie les arrêts
                # Alors ils peuvent être dans le même service seulement si les arrêts correspondent
                # OU s'il existe un autre voyage qui peut les connecter
                if verifier_arrets and temps_entre >= battement_minimum:
                    # Vérifier s'il existe un autre voyage qui peut connecter vj et vi
                    peut_connecter = False
                    for k in range(n):
                        if k == i or k == j:
                            continue
                        vk = listes[k]
                        # Vérifier si vk peut être entre vj et vi
                        if (vj.hfin <= vk.hdebut and vk.hfin <= vi.hdebut and
                                vj.arret_fin_id() == vk.arret_debut_id() and
                                vk.arret_fin_id() == vi.arret_debut_id()):
                            peut_connecter = True
                            break

                    # Si les arrêts ne correspondent pas ET qu'aucun autre voyage ne peut les connecter
                    # alors ils ne peuvent pas être dans le même service
                    if (vj.arret_fin_id() != vi.arret_debut_id() and not peut_connecter):
                        # Empêcher qu'ils soient dans le même service
                        model.Add(service[i] != service[j])

            # Contrainte 3: Si vi se termine avant vj
            if vi.hfin <= vj.hdebut:
                temps_entre = vj.hdebut - vi.hfin
                # Si le temps entre est insuffisant (< battement_minimum),
                # ils ne peuvent pas être dans le même service
                if temps_entre < battement_minimum:
                    model.Add(service[i] != service[j])
                    continue

                # Si le temps est suffisant ET qu'on vérifie les arrêts
                # Alors ils peuvent être dans le même service seulement si les arrêts correspondent
                # OU s'il existe un autre voyage qui peut les connecter
                if verifier_arrets and temps_entre >= battement_minimum:
                    # Vérifier s'il existe un autre voyage qui peut connecter vi et vj
                    peut_connecter = False
                    for k in range(n):
                        if k == i or k == j:
                            continue
                        vk = listes[k]
                        # Vérifier si vk peut être entre vi et vj
                        if (vi.hfin <= vk.hdebut and vk.hfin <= vj.hdebut and
                                vi.arret_fin_id() == vk.arret_debut_id() and
                                vk.arret_fin_id() == vj.arret_debut_id()):
                            peut_connecter = True
                            break

                    # Si les arrêts ne correspondent pas ET qu'aucun autre voyage ne peut les connecter
                    # alors ils ne peuvent pas être dans le même service
                    if (vi.arret_fin_id() != vj.arret_debut_id() and not peut_connecter):
                        # Empêcher qu'ils soient dans le même service
                        model.Add(service[i] != service[j])

    # Contraintes pour matin/après-midi si spécifiées
    heure_separation_minutes = voyage.time_to_minutes(heure_separation)

    if nb_services_matin is not None or nb_services_apres_midi is not None:
        # Variables booléennes : service_matin[j] = True si le service j est du matin
        service_matin = [model.NewBoolVar(f"service_matin_{j}") for j in range(max_services)]
        service_apres_midi = [model.NewBoolVar(f"service_apres_midi_{j}") for j in range(max_services)]

        # Variables pour indiquer si un service est utilisé
        service_utilise = [model.NewBoolVar(f"service_utilise_{j}") for j in range(max_services)]

        # Un service est utilisé s'il contient au moins un voyage
        for j in range(max_services):
            # Si au moins un voyage est assigné au service j, alors service_utilise[j] = True
            voyages_dans_service = []
            for i in range(n):
                voyage_dans_service = model.NewBoolVar(f"voyage_{i}_dans_service_{j}_utilise")
                model.Add(service[i] == j).OnlyEnforceIf(voyage_dans_service)
                model.Add(service[i] != j).OnlyEnforceIf(voyage_dans_service.Not())
                voyages_dans_service.append(voyage_dans_service)

            if voyages_dans_service:
                model.AddBoolOr(voyages_dans_service).OnlyEnforceIf(service_utilise[j])
                model.AddBoolAnd([v.Not() for v in voyages_dans_service]).OnlyEnforceIf(service_utilise[j].Not())
            else:
                model.Add(service_utilise[j] == False)

        # Un service ne peut pas être à la fois matin et après-midi
        # Un service utilisé doit être soit matin soit après-midi
        for j in range(max_services):
            model.AddBoolAnd([service_matin[j].Not(), service_apres_midi[j].Not()])
            # Si le service est utilisé, il doit être soit matin soit après-midi
            model.AddBoolOr([service_matin[j], service_apres_midi[j]]).OnlyEnforceIf(service_utilise[j])
            # Si le service n'est pas utilisé, il n'est ni matin ni après-midi
            model.AddBoolAnd([service_matin[j].Not(), service_apres_midi[j].Not()]).OnlyEnforceIf(
                service_utilise[j].Not())

        # Pour chaque service j, déterminer s'il est du matin ou de l'après-midi
        # Un service est du matin si son premier voyage (le plus tôt) commence avant l'heure de séparation
        for j in range(max_services):
            # Trouver le voyage le plus tôt qui pourrait être dans ce service
            # Un service est du matin si TOUS ses voyages commencent avant la séparation
            # ou si son premier voyage (le plus tôt) commence avant la séparation

            # Variable : le service j a au moins un voyage du matin
            a_voyage_matin = model.NewBoolVar(f"service_{j}_a_voyage_matin")
            # Variable : le service j a au moins un voyage de l'après-midi
            a_voyage_apres_midi = model.NewBoolVar(f"service_{j}_a_voyage_apres_midi")

            # Liste des booléens pour les voyages du matin et de l'après-midi dans ce service
            voyages_matin_dans_service = []
            voyages_apres_midi_dans_service = []

            for i in range(n):
                vi = listes[i]
                voyage_dans_service = model.NewBoolVar(f"voyage_{i}_dans_service_{j}")
                model.Add(service[i] == j).OnlyEnforceIf(voyage_dans_service)
                model.Add(service[i] != j).OnlyEnforceIf(voyage_dans_service.Not())

                if vi.hdebut < heure_separation_minutes:
                    voyages_matin_dans_service.append(voyage_dans_service)
                else:
                    voyages_apres_midi_dans_service.append(voyage_dans_service)

            # Le service a un voyage du matin si au moins un voyage du matin y est assigné
            if voyages_matin_dans_service:
                model.AddBoolOr(voyages_matin_dans_service).OnlyEnforceIf(a_voyage_matin)
                model.AddBoolAnd([v.Not() for v in voyages_matin_dans_service]).OnlyEnforceIf(a_voyage_matin.Not())
            else:
                model.Add(a_voyage_matin == False)

            # Le service a un voyage de l'après-midi si au moins un voyage de l'après-midi y est assigné
            if voyages_apres_midi_dans_service:
                model.AddBoolOr(voyages_apres_midi_dans_service).OnlyEnforceIf(a_voyage_apres_midi)
                model.AddBoolAnd([v.Not() for v in voyages_apres_midi_dans_service]).OnlyEnforceIf(
                    a_voyage_apres_midi.Not())
            else:
                model.Add(a_voyage_apres_midi == False)

            # Règle simplifiée :
            # - Si le service est utilisé ET a des voyages du matin, alors il est du matin
            # - Si le service est utilisé ET n'a pas de voyages du matin, alors il est de l'après-midi
            # Utiliser seulement les implications de base
            model.AddBoolAnd([service_utilise[j], a_voyage_matin]).OnlyEnforceIf(service_matin[j])
            model.AddBoolAnd([service_utilise[j], a_voyage_matin.Not()]).OnlyEnforceIf(service_apres_midi[j])

        # Contrainte sur le nombre de services du matin
        if nb_services_matin is not None:
            model.Add(sum(service_matin) == nb_services_matin)

        # Contrainte sur le nombre de services de l'après-midi
        if nb_services_apres_midi is not None:
            model.Add(sum(service_apres_midi) == nb_services_apres_midi)

    # Objectif: Minimiser le nombre maximum de services utilisés (maximise les voyages par service)
    # En minimisant le maximum, on force le solveur à utiliser le moins de services possible
    model.Minimize(max_service_utilise)

    class SolutionCollector(cp_model.CpSolverSolutionCallback):
        def __init__(self, variables, limit):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self._variables = variables
            self._solution_count = 0
            self.solution_limit = limit
            self.solutions = []

        def on_solution_callback(self):
            self._solution_count += 1
            solution = [self.Value(v) for v in self._variables]
            self.solutions.append(solution)
            if self._solution_count >= self.solution_limit:
                self.StopSearch()

        def solution_count(self):
            return self._solution_count

    solution_collector = SolutionCollector(service, max_solutions)
    solver = cp_model.CpSolver()

    # Configuration du solveur pour trouver plusieurs solutions
    solver.parameters.enumerate_all_solutions = False
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model, solution_collector)

    print(f"\n{'=' * 70}")
    print(f"Statut: {solver.StatusName(status)}")
    print(f"Solutions trouvées: {solution_collector.solution_count()}")
    print(f"{'=' * 70}\n")

    toutes_solutions = []

    for sol_idx, solution in enumerate(solution_collector.solutions, 1):
        services_dict = {}

        for i in range(n):
            num_service = solution[i]
            if num_service not in services_dict:
                services_dict[num_service] = []
            services_dict[num_service].append(listes[i])

        # Debug: afficher les services avant validation
        print(f"\nDEBUG Solution {sol_idx} - Avant validation:")
        for num_service in sorted(services_dict.keys()):
            voyages_du_service = services_dict[num_service]
            print(f"  Service {num_service}: {len(voyages_du_service)} voyages")
            for v in sorted(voyages_du_service, key=lambda x: x.hdebut):
                print(
                    f"    Voyage {v.num_voyage}: {v.arret_debut}->{v.arret_fin} ({v.hdebut // 60:02d}:{v.hdebut % 60:02d}-{v.hfin // 60:02d}:{v.hfin % 60:02d})")

        services_crees = []

        for num_service in sorted(services_dict.keys()):
            voyages_du_service = services_dict[num_service]

            # Valider que ce service peut former une chaîne valide
            est_valide, ordre_voyages = valider_service(
                voyages_du_service, battement_minimum, verifier_arrets
            )

            if not est_valide:
                # Service invalide, on le saute
                print(f"  Service {num_service} REJETÉ (invalide)")
                continue

            print(f"  Service {num_service} VALIDÉ avec {len(ordre_voyages)} voyages")

            nouveau_service = service_agent(num_service=num_service)
            for v in ordre_voyages:
                nouveau_service.ajout_voyages(v)

            services_crees.append(nouveau_service)

        # Ne garder que les solutions avec au moins un service valide
        if services_crees:
            toutes_solutions.append(services_crees)

    print("=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"Total solutions trouvées: {len(toutes_solutions)}")
    if toutes_solutions:
        nb_services = [len(sol) for sol in toutes_solutions]
        print(f"Services min/max par solution: {min(nb_services)} / {max(nb_services)}")

        # Afficher le nombre de voyages par service pour chaque solution
        for idx, sol in enumerate(toutes_solutions, 1):
            nb_voyages_par_service = [len(s.get_voyages()) for s in sol]
            print(f"Solution {idx}: {len(sol)} services, "
                  f"voyages par service: {nb_voyages_par_service}")
    print("=" * 70)

    return toutes_solutions


if __name__ == "__main__":
    voyage1 = voyage("A1", 1, "GOCAR", "CEN05", "5:00", "5:21")
    voyage2 = voyage("A1", 2, "CEN18", "GOCAR", "4:30", "4:48")
    voyage3 = voyage("A1", 6, "CEN18", "GOCAR", "5:30", "5:48")
    voyage4 = voyage("A1", 3, "GOCAR", "CEN05", "5:30", "5:51")
    voyage5 = voyage("A1", 4, "CEN18", "GOCAR", "5:00", "5:18")
    voyage6 = voyage("A1", 5, "GOCAR", "CEN05", "6:00", "6:21")
    voyage7 = voyage("A1", 7, "GOCAR", "CEN05", "6:30", "6:51")
    voyage8 = voyage("A1", 4, "CEN18", "GOCAR", "6:00", "6:18")

    listes = [voyage1, voyage2, voyage3, voyage4, voyage5, voyage6, voyage7, voyage8]
    BM = 5

    # Exemple avec contraintes matin/après-midi
    # Décommenter les lignes suivantes pour tester :
    # solutions = solvertest(listes, BM, nb_services_matin=1, nb_services_apres_midi=1, heure_separation="12:00")

    # Sans contraintes (comportement par défaut)
    solutions = solvertest(listes, BM)

    for idx, services in enumerate(solutions, 1):
        print("\n" + "#" * 70)
        print(f"SOLUTION {idx}")
        print("#" * 70)
        for s in services:
            print(s)

