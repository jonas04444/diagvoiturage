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
        result += f"duree totale: {duree} min ({duree//60}h{duree%60:02d})\n"

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

def solvertest(listes, battement_minimum, verifier_arrets=True, max_solutions = 10):

    if not listes:
        return []

    model = cp_model.CpModel()
    n = len(listes)

    service = [model.NewIntVar(0,n-1,f"service{i}") for i in range(n)]

    for i in range (n):
        for j in range (i+1, n):

            vi = listes[i]
            vj = listes[j]

            chevauchement = (
                vi.hdebut < vj.hfin and
                vj.hdebut < vi.hfin
            )

            if chevauchement:
                model.Add(service[i] != service[j])
                continue

            if vj.hfin <= vi.hdebut:
                if vi.hdebut - vj.hfin <= battement_minimum:
                    model.Add(service[i] != service[j])

            if verifier_arrets:
                if vi.hfin <= vj.hdebut:
                    if vi.arret_fin_id() != vj.arret_debut_id():
                        model.Add(service[i] != service[j])

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
    status = solver.Solve(model, solution_collector)

    print(f"\n{'=' * 70}")
    print(f"Statut: {solver.StatusName(status)}")
    print(f"Solutions trouvées: {solution_collector.solution_count()}")
    print(f"{'=' * 70}\n")

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

if __name__ == "__main__":
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
    voyage6 = voyage(
        "A1",
        5,
        "GOCAR",
        "CEN05",
        "6:00",
        "6:21"
    )
    voyage7 = voyage(
        "A1",
        7,
        "GOCAR",
        "CEN05",
        "6:30",
        "6:51"
    )
    voyage8 = voyage(
        "A1",
        4,
        "CEN18",
        "GOCAR",
        "6:00",
        "6:18"
    )
    listes = [voyage1, voyage2, voyage3, voyage4, voyage5, voyage6, voyage7, voyage8]
    BM = 5
    solutions = solvertest(listes, BM)

    for idx, services in enumerate(solutions, 1):
        print("\n" + "#" * 70)
        print(f"SOLUTION {idx}")
        print("#" * 70)

        for s in services:
            print(s)


