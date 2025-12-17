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

    voyage_vars = [model.NewBoolVar(f'voyages_{i}') for i in range(len(listes))]
    positions = [model.NewIntVar( 0, len(listes)-1, f'postion_{i}') for i in range(len(listes))]

    for i in range(len(listes)):
        for j in range(len(listes)):
            if i != j:

                temps_battement = listes[j].hdebut - listes[i].hfin
                arret_compatible = (
                    listes[i].arret_fin_id()==
                    listes[j].arret_debut_id()
                )

                if (listes[i].hfin < listes[j].hdebut and
                        temps_battement > battement_minimum and
                        arret_compatible
                    ):
                    print(
                        f"ok: voyage", listes[i].num_ligne, listes[i].num_voyage,
                        "peut précéder voyage", listes[j].num_ligne, listes[j].num_voyage
                    )
                    suit = model.NewBoolVar(f'suit_{i}_{j}')
                    model.AddImplication(suit, voyage_vars[i])
                    model.AddImplication(suit, voyage_vars[j])

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL:
        print("solution trouvée")
        for i in range(len(voyage_vars)):
            if solver.Value(voyage_vars[i]) == 1:
                print(f"voyage {i}: début={listes[i].hdebut}, fin={listes[i].hfin}")
    else:
        print("non solution")


BM = 5
solvertest(BM)
