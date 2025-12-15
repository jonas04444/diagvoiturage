from ortools.sat.python import cp_model

class voyage:
    def __init__(self, num_ligne, num_voyage, arret_debut, arret_fin, heure_debut, heure_fin):
        self.num_ligne = (num_ligne)
        self.num_voyage = num_voyage
        self.arret_debut = arret_debut
        self.arret_fin = arret_fin
        self.hdebut = heure_debut
        self.hfin = heure_fin

    def arret_debut_id(self):
        return self.arret_debut[:3]

    def arret_fin_id(self):
        return self.arret_fin[:3]

    def time_to_minutes(time_str):
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

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

def solvertest():
    model = cp_model.CpModel()

    voyage_vars = [model.NewBoolVar(f'voyages_{i}') for i in range(len(listes))]

    for i in range(len(listes)):
        for j in range(len(listes)):
            if i != j:
                if listes[i].hfin < listes[j].hdebut:
                    print(f"ok: voyage", listes[i].num_ligne, listes[i].num_voyage, "peut précéder voyage", listes[j].num_ligne, listes[j].num_voyage)
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

solvertest()