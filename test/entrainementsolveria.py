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

        duree = self.duree_services()
        result = f"service {self.num_service}: {len(self.voyages)} voyages, "
        result += f"duree totale: {duree} min ({duree//60}h{duree%60:02d})\n"

        for v in self.voyages:
            result += f"  • Voyage {v.num_voyage}: {v.arret_debut} → {v.arret_fin}\n"

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
listes = [voyage1, voyage2, voyage3]

def solvertest(battement_minimum, max_solutions):
    model = cp_model.CpModel()

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

    n = len(listes)

    voyage_vars = [model.NewIntVar(0,n,f'service_{i}')for i in range(n)]
    positions = [model.NewIntVar( 0, n, f'ordre_{i}') for i in range(n)]
    #chaine_arret = [model.NewIntVar(0,n,f'arret_{i}') for i in range(n)]


    for i in range(len(listes)):
        for j in range(len(listes)):
            if i != j:
                if i < j:
                    premier_voyage = listes[i]
                temps_battement = listes[j].hdebut - listes[i].hfin
                arret_compatible = (
                    listes[i].arret_fin_id()==
                    listes[j].arret_debut_id()
                )

                if listes[i].hfin < listes[j].hdebut and temps_battement >= battement_minimum:
                    compat_msg = "✓ Compatible" if arret_compatible else "✗ Arrêts incompatibles"
                    print(f"Voyage {listes[i].num_voyage} ({listes[i].arret_fin[:3]}) → Voyage {listes[j].num_voyage} ({listes[j].arret_debut[:3]}): "
                          f"battement={temps_battement}min | {compat_msg}")

                meme_service = model.NewBoolVar(f'meme_service_{i}_{j}')
                model.Add(voyage_vars[i] == voyage_vars[j]).OnlyEnforceIf(meme_service)
                #model.Add(voyage_vars[i] != voyage_vars[j]).OnlyEnforceIf(meme_service.Not())

                suit = model.NewBoolVar(f'suit_{i}_{j}')
                model.Add(positions[j] == positions[i] + 1).OnlyEnforceIf(suit)
                #model.Add(positions[j] != positions[i] + 1).OnlyEnforceIf(suit.Not())

                model.AddImplication(suit, meme_service)

                if (listes[i].hfin < listes[j].hdebut and
                        temps_battement >= battement_minimum and
                        arret_compatible):
                    pass
                else:
                    model.Add(suit == 0)

    for i in range(n):
        model.Add(voyage_vars[i] > 0)

    solution_collector = SolutionCollector(voyage_vars + positions, max_solutions)

    solver = cp_model.CpSolver()

    status = solver.SearchForAllSolutions(model, solution_collector)

    print(f"\n{solution_collector.solution_count()} solutions trouvée")

    for sol_idx, solution in enumerate(solution_collector.solutions, 1):
        print(f"=== PROPOSITION {sol_idx} ===")
        services_dict = {}

        for i in range(n):
            num_services = solution[i]
            order = solution[n + i]
            if num_services not in services_dict:
                services_dict[num_services] = []
            services_dict[num_services].append((order, i, listes[i]))

        services_crees = []
        for num_service in sorted(services_dict.keys()):
            if num_service > 0:
                nouveau_service = service_agent(num_service=num_service)

                voyages_trier = sorted(services_dict[num_service], key=lambda x: x[0])

                for order, idx, v in voyages_trier:
                    nouveau_service.ajout_voyages(v)
                services_crees.append(nouveau_service)

        for service in services_crees:
            print(service)

        print()  # Ligne vide entre les propositions

    if status == cp_model.OPTIMAL:
        print("solution trouvée")

        services_dict = {}

        for i in range(n):
            num_services = solver.Value(voyage_vars[i])
            order = solver.Value(positions[i])
            if num_services not in services_dict:
                services_dict[num_services] = []
            services_dict[num_services].append((order,i, listes[i]))

        services_crees = []
        for num_service in sorted(services_dict.keys()):
            if num_service > 0:
                nouveau_service = service_agent(num_service=num_service)

                voyages_trier = sorted(services_dict[num_service], key=lambda x: x[0])

                for order, idx, v in voyages_trier:
                    nouveau_service.ajout_voyages(v)
                services_crees.append(nouveau_service)

        for service in services_crees:
            print(service)

BM = 5
MS=5
solvertest(BM,MS)
