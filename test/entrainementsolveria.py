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
        result = f"service {self.num_service}: {len(self.voyages)} voyages, "
        result += f"duree totale: {duree} min ({duree//60}h{duree%60:02d})\n"

        for v in self.voyages_chronologiques:
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

voyage1 = voyage(
    "A1",
    1,
    "GOCAR",
    "CEN05",
    "5:00",
    "5:21"
    )
voyage2 = voyage(
    "A1",
    2,
    "CEN18",
    "GOCAR",
    "4:30",
    "4:48"
    )
voyage3 = voyage(
    "A1",
    6,
    "CEN18",
    "GOCAR",
    "5:30",
    "5:48"
    )
voyage4 = voyage(
    "A1",
    3,
    "GOCAR",
    "CEN05",
    "5:30",
    "5:51"
    )
voyage5 = voyage(
    "A1",
    4,
    "CEN18",
    "GOCAR",
    "5:00",
    "5:18"
    )

listes = [voyage1, voyage2, voyage3, voyage4, voyage5]

def solvertest(listes, battement_minimum, verifier_arrets=False, max_solutions = 10):

    if not listes:
        return []

    model = cp_model.CpModel()
    n = len(listes)

    voyage_vars = [model.NewIntVar(1,n,f'service_{i}') for i in range(n)]

    positions = [model.NewIntVar(0,n-1,f'position_{i}') for i in range(n)]

    for i in range (n):
        for j in range (n):
            if i == j:
                continue
            voyage_i = listes[i]
            voyage_j = listes[j]

            meme_service = model.NewBoolVar(f"meme_service_{i}_{j}")
            model.Add(voyage_vars[i] == voyage_vars[j]).OnlyEnforceIf(meme_service)
            model.Add(voyage_vars[i] != voyage_vars[j]).OnlyEnforceIf(meme_service.Not())

            chevauchement = (
                voyage_i.hdebut < voyage_j.hfin and
                voyage_j.hdebut < voyage_i.hfin
            )

            if chevauchement:
                model.Add(meme_service == 0)

            suit_directement = model.NewBoolVar(f"suit_{i}_{j}")
            model.Add(positions[i] == positions[j]).OnlyEnforceIf(suit_directement)
            model.Add(positions[i] != positions[j]).OnlyEnforceIf(suit_directement.Not())

            model.AddImplication(suit_directement, meme_service)

            temps_battement = voyage_j.hdebut - voyage_i.hfin
            arret_compatible =  (voyage_i.arret_fin_id() == voyage_j.arret_debut_id())

            peut_suivre = (
                voyage_i.hfin < voyage_j.hdebut and
                temps_battement >= battement_minimum
            )

            if verifier_arrets:
                peut_suivre = peut_suivre and arret_compatible

            if not peut_suivre:
                model.Add(suit_directement == 0)

    for i in range(n):
        for j in range(n):
            meme_service = model.NewBoolVar(f"check_pos_{i}_{j}")
            model.Add(voyage_vars[i] == voyage_vars[j]).OnlyEnforceIf(meme_service)
            model.Add(voyage_vars[i] != voyage_vars[j]).OnlyEnforceIf(meme_service.Not())
            model.Add(positions[i] != positions[j]).OnlyEnforceIf(meme_service)

    for i in range(n):
        clauses = []
        for j in range(n):
            meme_service_pos_zero = model.NewBoolVar(f"meme_service_pos0_{i}_{j}")
            model.Add(voyage_vars[i] == voyage_vars[j]).OnlyEnforceIf(meme_service_pos_zero)
            model.Add(positions[j] == 0).OnlyEnforceIf(meme_service_pos_zero)
            clauses.append(meme_service_pos_zero)
        model.AddBoolOr(clauses)

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

    solution_collector = SolutionCollector(voyage_vars + positions, max_solutions)

    solver = cp_model.CpSolver()
    status = solver.Solve(model, solution_collector)

    toutes_solutions = []

    for sol_idx, solution in enumerate(solution_collector.solutions, 1):

        services_dict = {}

        for i in range (n):
            num_service = solution[i]

            if num_service not in services_dict:
                services_dict[num_service] = []

            services_dict[num_service].append(listes[i])

        services_crees = []
        for num_service in sorted(services_dict.keys()):
            nouveau_service = service_agent(num_service=num_service)

            voyages_chronologiques = sorted(services_dict[num_service], key=lambda v: v.hdebut)

            for v in voyages_chronologiques:
                nouveau_service.ajout_voyages(v)

            services_crees.append(nouveau_service)

        toutes_solutions.append(services_crees)

        print("=" * 70)
        print("RÉSUMÉ")
        print("=" * 70)
        print(f"Total solutions trouvées: {len(toutes_solutions)}")
        if toutes_solutions:
            nb_services = [len(sol) for sol in toutes_solutions]
            print(f"Services min/max par solution: {min(nb_services)} / {max(nb_services)}")
        print("=" * 70)

    return toutes_solutions

BM = 5

solvertest(listes,BM)
