from numpy.ma.core import append
from ortools.sat.python import cp_model

class service:
    def __init__(self):
        self.voyages = []

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

for i in listes:
    print(f"voyage {i}",i.num_ligne, i.hdebut, i.hfin)

def solvertest(battement_minimum):
    model = cp_model.CpModel()

    n = len(listes)

    voyage_vars = [model.NewIntVar(0,n,f'service_{i}')for i in range(n)]
    positions = [model.NewIntVar( 0, n, f'ordre_{i}') for i in range(n)]


    for i in range(len(listes)):
        for j in range(len(listes)):
            if i != j:

                temps_battement = listes[j].hdebut - listes[i].hfin
                arret_compatible = (
                    listes[i].arret_fin_id()==
                    listes[j].arret_debut_id()
                )

                meme_service = model.NewBoolVar(f'meme_service_{i}_{j}')
                model.Add(voyage_vars[i] == voyage_vars[j]).OnlyEnforceIf(meme_service)
                model.add(voyage_vars[i] != voyage_vars[j]).OnlyEnforceIf(meme_service.Not())

                suit = model.NewBoolVar(f'suit_{i}_{j}')
                model.Add(positions[j] == positions[i] + 1).OnlyEnforceIf(suit)
                model.Add(positions[j] != positions[i] + 1).OnlyEnforceIf(suit.Not())

                model.AddImplication(suit, meme_service)

                if (listes[i].hfin < listes[j].hdebut and
                        temps_battement >= battement_minimum and
                        arret_compatible):
                    pass
                else:
                    model.add(suit == 0)

    for i in range(n):
        model.add(voyage_vars[i] > 0)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL:
        print("solution trouvée")
        services = {}
        for i in range(n):
            num_services = solver.Value(voyage_vars[i])
            order = solver.Value(positions[i])
            if num_services not in services:
                services[num_services] = []
            services[num_services].append((order,i, listes[i]))

        for num_service in sorted(services.keys()):
            if num_service > 0:
                voyages_tries = sorted(services[num_service], key=lambda x: x[0])
                print(f"service {num_service}")
                for ordre, idx, v in voyages_tries:
                    print(f"  {ordre}. Voyage {v.num_voyage}: {v.arret_debut} → {v.arret_fin} "
                          f"({voyage.minutes_to_time(v.hdebut)} - {voyage.minutes_to_time(v.hfin)})")
    else:
        print("non solution")


BM = 5
solvertest(BM)
