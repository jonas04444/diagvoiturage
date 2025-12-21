from ortools.sat.python import cp_model

class service_agent:

    def __init__(self, num_service=None, type_service="matin"):
        self.voyages = []
        self.num_service = num_service
        self.type_service = type_service  # "matin" ou "apres_midi"

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

    def duree_services_maximum(self, duree_maximum):
        duree = self.duree_services()
        if duree > duree_maximum:
            return False
        return True

    def __str__(self):
        if not self.voyages:
            return f"Service {self.num_service} ({self.type_service}): vide"

        voyages_chronologiques = sorted(self.voyages, key=lambda v: v.hdebut)
        duree = self.duree_services()

        debut_service = min(v.hdebut for v in self.voyages)
        fin_service = max(v.hfin for v in self.voyages)

        result = f"Service {self.num_service} ({self.type_service.upper()}): {len(voyages_chronologiques)} voyages, "
        result += f"duree totale: {duree} min ({duree // 60}h{duree % 60:02d})\n"
        result += f"  Début service: {voyage.minutes_to_time(debut_service)}, Fin service: {voyage.minutes_to_time(fin_service)}\n"

        for v in voyages_chronologiques:
            hdebut_str = voyage.minutes_to_time(v.hdebut)
            hfin_str = voyage.minutes_to_time(v.hfin)
            result += f"  • Voyage {v.num_voyage}: {v.arret_debut} → {v.arret_fin} "
            result += f"({hdebut_str} - {hfin_str})\n"

        return result.rstrip()


class voyage:

    def __init__(self, num_ligne, num_voyage, arret_debut, arret_fin, heure_debut, heure_fin):
        self.num_ligne = (num_ligne)
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
    if len(voyages) == 0:
        return True, []
    if len(voyages) == 1:
        return True, list(voyages)

    voyages_list = list(voyages)
    for i in range(len(voyages_list)):
        for j in range(i + 1, len(voyages_list)):
            vi = voyages_list[i]
            vj = voyages_list[j]
            if vi.hdebut < vj.hfin and vj.hdebut < vi.hfin:
                return False, []

    def contruire_chaine(chaine_actuelle, restants):
        if not restants:
            return True, chaine_actuelle

        dernier = chaine_actuelle[-1] if chaine_actuelle else None

        if dernier is None:
            voyage_plus_tot = min(restants, key=lambda x: x.hdebut)
            nouveau_restants = restants.copy()
            nouveau_restants.remove(voyage_plus_tot)
            valide, resultat = contruire_chaine([voyage_plus_tot], nouveau_restants)

            if valide:
                return True, resultat

        else:
            for v in sorted(restants, key=lambda x: x.hdebut):
                chevauche = False
                for v_existant in chaine_actuelle:
                    if v.hdebut < v_existant.hfin and v_existant.hdebut < v.hfin:
                        chevauche = True
                        break

                if chevauche:
                    continue

                peut_suivre_directement = False
                peut_suivre_avec_pont = False
                v_pont_candidat = None

                if v.hdebut >= dernier.hfin:
                    temps_entre = v.hdebut - dernier.hfin
                    if temps_entre >= battement_minimum:
                        if not verifier_arrets or dernier.arret_fin_id() == v.arret_debut_id():
                            peut_suivre_directement = True
                        else:
                            for v_pont in restants:
                                if v_pont.hdebut == v:
                                    continue

                                if (dernier.hfin <= v_pont.hdebut and v_pont.hfin <= v.hdebut and
                                        dernier.arret_fin_id() == v_pont.arret_debut_id() and
                                        v_pont.arret_fin_id() == v.arret_debut_id()):
                                    peut_suivre_avec_pont = True
                                    v_pont_candidat = v_pont
                                    break

                if peut_suivre_directement:
                    nouveau_restants = restants.copy()
                    nouveau_restants.remove(v)
                    valide, resultat = contruire_chaine(chaine_actuelle + [v], nouveau_restants)
                    if valide:
                        return True, resultat

                if peut_suivre_avec_pont and v_pont_candidat:
                    nouveau_restants = restants.copy()
                    nouveau_restants.remove(v_pont_candidat)
                    nouveau_restants.remove(v)

                    valide, resultat = contruire_chaine(chaine_actuelle + [v_pont_candidat, v], nouveau_restants)
                    if valide:
                        return True, resultat

        return False, []

    valide, chaine = contruire_chaine([], set(voyages_list))
    return valide, chaine


def solvertest(listes, battement_minimum, verifier_arrets=True, max_solutions=10,
               max_services_matin=None, max_services_apres_midi=None,
               heure_debut_apres_midi=660, heure_fin_matin=1080, duree_max_service=540):
    """
    Résout le problème d'optimisation des services avec distinction matin/après-midi.

    Args:
        listes: Liste des voyages
        battement_minimum: Temps minimum entre deux voyages (minutes)
        verifier_arrets: Vérifier la cohérence des arrêts
        max_solutions: Nombre maximum de solutions à trouver
        max_services_matin: Nombre maximum de services matin (si None, = nombre de voyages)
        max_services_apres_midi: Nombre maximum de services après-midi (si None, = nombre de voyages)
        heure_debut_apres_midi: Heure à partir de laquelle un service après-midi peut commencer (défaut 11h = 660 min)
        heure_fin_matin: Heure max de fin pour un service matin (défaut 18h = 1080 min)
        duree_max_service: Durée maximale d'un service en minutes

    Logique:
        - Service MATIN: doit commencer AVANT heure_debut_apres_midi, peut se terminer jusqu'à heure_fin_matin
        - Service APRÈS-MIDI: doit commencer À PARTIR DE heure_debut_apres_midi
    """

    if not listes:
        return []

    print(f"\n{'=' * 70}")
    print(f"CONFIGURATION:")
    print(f"{'=' * 70}")
    print(f"Heure début après-midi: {heure_debut_apres_midi // 60}h{heure_debut_apres_midi % 60:02d}")
    print(f"Heure fin max matin: {heure_fin_matin // 60}h{heure_fin_matin % 60:02d}")
    print(f"Services matin max: {max_services_matin if max_services_matin else 'automatique'}")
    print(f"Services après-midi max: {max_services_apres_midi if max_services_apres_midi else 'automatique'}")
    print(f"{'=' * 70}\n")

    # Définir les limites de services si non spécifiées
    if max_services_matin is None:
        max_services_matin = len(listes)
    if max_services_apres_midi is None:
        max_services_apres_midi = len(listes)

    model = cp_model.CpModel()
    n = len(listes)

    # Nombre total de services possibles
    max_services_total = max_services_matin + max_services_apres_midi

    # Variables de service pour chaque voyage
    service = [model.NewIntVar(0, max_services_total - 1, f"service{i}") for i in range(n)]

    # Variables pour le nombre maximum de services utilisés dans chaque période
    max_service_utilise_matin = model.NewIntVar(0, max_services_matin - 1, "max_service_utilise_matin")
    max_service_utilise_apres_midi = model.NewIntVar(max_services_matin, max_services_total - 1,
                                                     "max_service_utilise_apres_midi")

    # Début et fin pour chaque service
    debut_service = [model.NewIntVar(0, 24 * 60, f"debut_service{s}") for s in range(max_services_total)]
    fin_service = [model.NewIntVar(0, 24 * 60, f"fin_service{s}") for s in range(max_services_total)]

    # Variables d'affectation
    affectation = {}
    for i in range(n):
        for s in range(max_services_total):
            affectation[(i, s)] = model.NewBoolVar(f"voyage_{i}_service_{s}")
            model.Add(service[i] == s).OnlyEnforceIf(affectation[(i, s)])
            model.Add(service[i] != s).OnlyEnforceIf(affectation[(i, s)].Not())

    # Contraintes sur les services
    for s in range(max_services_total):
        service_utilise = model.NewBoolVar(f"service_{s}_utilise")

        model.Add(sum(affectation[(i, s)] for i in range(n)) >= 1).OnlyEnforceIf(service_utilise)
        model.Add(sum(affectation[(i, s)] for i in range(n)) == 0).OnlyEnforceIf(service_utilise.Not())

        # Calculer le début et la fin du service
        for i in range(n):
            model.Add(debut_service[s] <= listes[i].hdebut).OnlyEnforceIf(affectation[(i, s)])
            model.Add(fin_service[s] >= listes[i].hfin).OnlyEnforceIf(affectation[(i, s)])

        # Contraintes spécifiques selon le type de service
        if s < max_services_matin:
            # Service MATIN : doit commencer avant heure_debut_apres_midi
            model.Add(debut_service[s] < heure_debut_apres_midi).OnlyEnforceIf(service_utilise)
            # Service MATIN : peut se terminer jusqu'à heure_fin_matin
            model.Add(fin_service[s] <= heure_fin_matin).OnlyEnforceIf(service_utilise)
            # Mettre à jour le max_service_utilise_matin
            model.Add(max_service_utilise_matin >= s).OnlyEnforceIf(service_utilise)
        else:
            # Service APRÈS-MIDI : doit commencer à partir de heure_debut_apres_midi
            model.Add(debut_service[s] >= heure_debut_apres_midi).OnlyEnforceIf(service_utilise)
            # Mettre à jour le max_service_utilise_apres_midi
            model.Add(max_service_utilise_apres_midi >= s).OnlyEnforceIf(service_utilise)

        # Durée maximale du service
        duree_service = model.NewIntVar(0, 24 * 60, f"duree_service{s}")
        model.Add(duree_service == fin_service[s] - debut_service[s]).OnlyEnforceIf(service_utilise)
        model.Add(duree_service <= duree_max_service).OnlyEnforceIf(service_utilise)

    # Contraintes entre voyages (chevauchement, battement, arrêts)
    for i in range(n):
        for j in range(i + 1, n):
            vi = listes[i]
            vj = listes[j]

            # Contrainte de chevauchement
            chevauchement = (vi.hdebut < vj.hfin and vj.hdebut < vi.hfin)

            if chevauchement:
                model.Add(service[i] != service[j])
                continue

            # Contrainte qui vérifie si un voyage ne commence pas avant la fin du précédent
            if vj.hfin <= vi.hdebut:
                temps_entre = vi.hdebut - vj.hfin
                if temps_entre < battement_minimum:
                    model.Add(service[i] != service[j])
                    continue

                # Vérification du temps de battement entre deux voyages
                if verifier_arrets and temps_entre >= battement_minimum:
                    peut_connecter = False
                    for k in range(n):
                        if k == i or k == j:
                            continue
                        vk = listes[k]
                        if (vj.hfin <= vk.hdebut and vk.hfin <= vi.hdebut and
                                vj.arret_fin_id() == vk.arret_debut_id() and
                                vk.arret_fin_id() == vi.arret_debut_id()):
                            peut_connecter = True
                            break

                    if (vj.arret_fin_id() != vi.arret_debut_id() and not peut_connecter):
                        model.Add(service[i] != service[j])

            # Suite contrainte battement
            if vi.hfin <= vj.hdebut:
                temps_entre = vj.hdebut - vi.hfin
                if temps_entre < battement_minimum:
                    model.Add(service[i] != service[j])
                    continue

                # Si temps suffisant vérifier les arrêts
                if verifier_arrets and temps_entre >= battement_minimum:
                    peut_connecter = False
                    for k in range(n):
                        if k == i or k == j:
                            continue
                        vk = listes[k]
                        if (vi.hfin <= vk.hdebut and vk.hfin <= vj.hdebut and
                                vi.arret_fin_id() == vk.arret_debut_id() and
                                vk.arret_fin_id() == vj.arret_debut_id()):
                            peut_connecter = True
                            break

                    # Si condition fausse ils ne peuvent pas être sur le même service
                    if (vi.arret_fin_id() != vj.arret_debut_id() and not peut_connecter):
                        model.Add(service[i] != service[j])

    # Objectif: minimiser le nombre de services utilisés
    nb_services_matin = model.NewIntVar(0, max_services_matin, "nb_services_matin")
    nb_services_apres_midi = model.NewIntVar(0, max_services_apres_midi, "nb_services_apres_midi")

    # Calculer le nombre réel de services utilisés
    model.Add(nb_services_matin == max_service_utilise_matin + 1)
    if max_services_apres_midi > 0:
        model.Add(nb_services_apres_midi == max_service_utilise_apres_midi - max_services_matin + 1)

    # Minimiser le nombre total de services
    model.Minimize(nb_services_matin + nb_services_apres_midi)

    class SolutionCollector(cp_model.CpSolverSolutionCallback):
        def __init__(self, variables, limit):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self._variables = variables
            self._solution_count = 0
            self.solution_limit = limit
            self.solutions = []

        def on_solution_callback(self):
            self._solution_count += 1
            solution = [self.value(v) for v in self._variables]
            self.solutions.append(solution)
            if self._solution_count >= self.solution_limit:
                self.StopSearch()

        def solution_count(self):
            return self._solution_count

    solution_collector = SolutionCollector(service, max_solutions)
    solver = cp_model.CpSolver()

    solver.parameters.enumerate_all_solutions = False
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model, solution_collector)

    print(f"\n{'=' * 70}")
    print(f"Status: {solver.StatusName(status)}")
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

        print(f"\n{'#' * 70}")
        print(f"SOLUTION {sol_idx}")
        print(f"{'#' * 70}")

        # Afficher les services
        for num_service in sorted(services_dict.keys()):
            voyages_du_service = services_dict[num_service]
            type_service = "MATIN" if num_service < max_services_matin else "APRÈS-MIDI"

            # Calculer le début et la fin du service
            debut_serv = min(v.hdebut for v in voyages_du_service)
            fin_serv = max(v.hfin for v in voyages_du_service)

            print(f"\nService {num_service} ({type_service}): {len(voyages_du_service)} voyages")
            print(
                f"  Plage horaire: {debut_serv // 60:02d}:{debut_serv % 60:02d} - {fin_serv // 60:02d}:{fin_serv % 60:02d}")

            for v in sorted(voyages_du_service, key=lambda x: x.hdebut):
                print(
                    f"  Voyage {v.num_voyage}: {v.arret_debut_id()} → {v.arret_fin} "
                    f"({v.hdebut // 60:02d}:{v.hdebut % 60:02d} - {v.hfin // 60:02d}:{v.hfin % 60:02d})"
                )

        services_crees = []
        for num_service in sorted(services_dict.keys()):
            voyages_du_service = services_dict[num_service]

            est_valide, ordre_voyages = valider_service(
                voyages_du_service, battement_minimum, verifier_arrets
            )

            if not est_valide:
                print(f"\n⚠️  Service {num_service} pas valide")
                continue

            print(f"✓ Service {num_service} valide avec {len(ordre_voyages)} voyages")

            type_service = "matin" if num_service < max_services_matin else "apres_midi"
            nouveau_service = service_agent(num_service=num_service, type_service=type_service)
            for v in ordre_voyages:
                nouveau_service.ajout_voyages(v)

            services_crees.append(nouveau_service)

        if services_crees:
            toutes_solutions.append(services_crees)

    print(f"\n{'=' * 70}")
    print(f"RÉSUMÉ")
    print(f"{'=' * 70}")
    print(f"Total solutions trouvées: {len(toutes_solutions)}")

    if toutes_solutions:
        for idx, sol in enumerate(toutes_solutions, 1):
            services_matin = [s for s in sol if s.type_service == "matin"]
            services_apres_midi = [s for s in sol if s.type_service == "apres_midi"]

            print(f"\nSolution {idx}:")
            print(f"  - Services matin: {len(services_matin)}")
            print(f"  - Services après-midi: {len(services_apres_midi)}")
            print(f"  - Total: {len(sol)} services")

            if services_matin:
                nb_voyages_matin = [len(s.get_voyages()) for s in services_matin]
                print(f"  - Voyages par service (matin): {nb_voyages_matin}")

            if services_apres_midi:
                nb_voyages_apres_midi = [len(s.get_voyages()) for s in services_apres_midi]
                print(f"  - Voyages par service (après-midi): {nb_voyages_apres_midi}")

    print(f"{'=' * 70}\n")

    return toutes_solutions


if __name__ == "__main__":
    voyage1 = voyage("A1", 1, "GOCAR", "CEN05", "5:00", "5:21")
    voyage2 = voyage("A1", 2, "CEN18", "GOCAR", "4:30", "4:48")
    voyage3 = voyage("A1", 6, "CEN18", "GOCAR", "5:30", "5:48")
    voyage4 = voyage("A1", 3, "GOCAR", "CEN05", "5:30", "5:51")
    voyage5 = voyage("A1", 4, "CEN18", "GOCAR", "5:00", "5:18")
    voyage6 = voyage("A1", 5, "GOCAR", "CEN05", "6:00", "6:21")
    voyage7 = voyage("A1", 7, "GOCAR", "CEN05", "6:30", "6:51")
    voyage8 = voyage("A1", 8, "CEN18", "GOCAR", "6:00", "6:18")
    voyage9 = voyage("A1", 9, "GOCAR", "CEN05", "7:00", "7:21")
    voyage10 = voyage("A1", 10, "CEN18", "GOCAR", "6:30", "6:48")
    voyage11 = voyage("A1", 11, "GOCAR", "CEN05", "7:30", "7:51")
    voyage12 = voyage("A1", 12, "CEN18", "GOCAR", "7:00", "7:18")

    # Voyages qui peuvent être dans un service matin (si le service commence avant 11h)
    voyage13 = voyage("A1", 13, "GOCAR", "CEN05", "11:00", "11:21")
    voyage14 = voyage("A1", 14, "CEN18", "GOCAR", "12:30", "12:48")
    voyage15 = voyage("A1", 15, "GOCAR", "CEN05", "14:00", "14:21")
    voyage16 = voyage("A1", 16, "CEN18", "GOCAR", "15:30", "15:48")

    # Voyages d'après-midi qui commencent à 11h ou après
    voyage17 = voyage("A1", 17, "CEN18", "GOCAR", "11:00", "11:18")
    voyage18 = voyage("A1", 18, "GOCAR", "CEN05", "13:00", "13:21")

    listes = [voyage1, voyage2, voyage3, voyage4, voyage5, voyage6, voyage7, voyage8,
              voyage9, voyage10, voyage11, voyage12, voyage13, voyage14, voyage15, voyage16,
              voyage17, voyage18]

    BM = 5

    # Exemple: 2 services matin (qui peuvent aller jusqu'à 18h), 1 service après-midi (commence à 11h+)
    print("\n" + "=" * 70)
    print("EXEMPLE: 2 services matin max (commencent avant 11h, finissent max 18h)")
    print("         1 service après-midi max (commence à partir de 11h)")
    print("=" * 70)

    solutions = solvertest(
        listes,
        BM,
        verifier_arrets=True,
        max_solutions=10,
        max_services_matin=2,  # Max 2 services qui commencent avant 11h
        max_services_apres_midi=1,  # Max 1 service qui commence à partir de 11h
        heure_debut_apres_midi=660,  # 11h = 660 minutes
        heure_fin_matin=1080,  # 18h = 1080 minutes (fin max pour services matin)
        duree_max_service=540  # 9h max par service
    )

    # Afficher les détails des services
    for idx, services in enumerate(solutions, 1):
        print("\n" + "#" * 70)
        print(f"DÉTAILS SOLUTION {idx}")
        print("#" * 70)

        for s in services:
            print(s)
            print()