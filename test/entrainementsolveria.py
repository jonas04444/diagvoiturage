from ortools.sat.python import cp_model

class service_agent:

    def __init__(self, num_service=None, type_service="matin"):
        self.voyages = []
        self.num_service = num_service
        self.type_service = type_service

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
        debut_service = min(v.hdebut for v in self.voyages)
        fin_service = max(v.hfin for v in self.voyages)
        duree = fin_service - debut_service

        result = f"Service {self.num_service} ({self.type_service.upper()}): {len(voyages_chronologiques)} voyages\n"
        result += f"  Début: {voyage.minutes_to_time(debut_service)}, Fin: {voyage.minutes_to_time(fin_service)}\n"

        for v in voyages_chronologiques:
            result += f"  • Voyage {v.num_voyage}: {v.arret_debut} → {v.arret_fin} "
            result += f"({voyage.minutes_to_time(v.hdebut)} - {voyage.minutes_to_time(v.hfin)})\n"

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
    def minutes_to_time(minutes):
        return f"{minutes // 60:02d}h{minutes % 60:02d}"


def valider_service(voyages, battement_minimum, verifier_arrets=True):
    if len(voyages) <= 1:
        return True, list(voyages)

    voyages_ordonnes = sorted(voyages, key=lambda v: v.hdebut)

    for i in range(len(voyages_ordonnes) - 1):
        if not voyages_compatibles(
            voyages_ordonnes[i],
            voyages_ordonnes[i + 1],
            voyages_ordonnes,
            battement_minimum,
            verifier_arrets
        ):
            return False, []

    return True, voyages_ordonnes

def voyages_compatibles(v1, v2, voyages, battement_minimum, verifier_arrets=True):
    if v2.hdebut < v1.hfin:
        return False

    temps_entre = v2.hdebut - v1.hfin
    if temps_entre < battement_minimum:
        return False

    if not verifier_arrets:
        return True

    if v1.arret_fin_id() == v2.arret_debut_id():
        return True

    #voyage pont hlp
    for vp in voyages:
        if vp is v1 or vp is v2:
            continue

        if (v1.hfin <= vp.hdebut and vp.hfin <= v2.hdebut and
                v1.arret_fin_id() == vp.arret_debut_id() and
                vp.arret_fin_id() == v2.arret_debut_id()
        ):
            return True

    return False

def solvertest(listes, battement_minimum, verifier_arrets=True, max_solutions = 10,
               max_services_matin = None, max_services_apres_midi = None,
               heure_debut_apres_midi = 660, heure_fin_matin = 1080,duree_max_service=540):

    model = cp_model.CpModel()
    n = len(listes)

    if max_services_matin is None:
        max_services_matin = n
    if max_services_apres_midi is None:
        max_services_apres_midi = n

    max_services_total =  max_services_matin + max_services_apres_midi
    service = [model.NewIntVar(0, max_services_total -1, f"service{i}") for i in range(n)]

    service_utilise = []

    for s in range(max_services_total):
        b = model.NewBoolVar(f"service_{s}_utilise")
        service_utilise.append(b)

        affectations = []
        for i in range(n):
            a = model.NewBoolVar(f"voyage_{i}_dans_service_{s}")
            model.Add(service[i] == s).OnlyEnforceIf(a)
            model.Add(service[i] != s).OnlyEnforceIf(a.Not())
            affectations.append(a)

        model.Add(sum(affectations) >= 1).OnlyEnforceIf(b)
        model.Add(sum(affectations) == 0).OnlyEnforceIf(b.Not())

    model.Minimize(sum(service_utilise))

    for i in range(n):
        for j in range(i+1, n):
            vi = listes[i]
            vj = listes[j]

            if vi.hdebut < vj.hfin and vj.hdebut < vi.hfin:
                model.Add(service[i] != service[j])
                continue

            if vi.hfin <= vj.hdebut:
                if not voyages_compatibles(vi, vj, listes, battement_minimum, verifier_arrets):
                    model.Add(service[i] != service[j])

            if vj.hfin <= vi.hdebut:
                if not voyages_compatibles(vj, vi, listes, battement_minimum, verifier_arrets):
                    model.Add(service[i] != service[j])

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return []

    services = {}
    for i in range(n):
        s = solver.Value(service[i])
        services.setdefault(s, []).append(listes[i])

    resultat = []
    for s, voyages_service in services.items():
        valide, ordre = valider_service(voyages_service, battement_minimum, verifier_arrets)
        if valide:
            type_service = "matin" if s < max_services_matin else "apres_midi"
            sa = service_agent(s, type_service)
            for v in ordre:
                sa.ajout_voyages(v)
            resultat.append(sa)

    return [resultat]


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
        8,
        "CEN18",
        "GOCAR",
        "6:00",
        "6:18"
    )
    voyage9 = voyage(
        "A1",
        9,
        "GOCAR",
        "CEN05",
        "7:00",
        "7:21"
    )
    voyage10 = voyage(
        "A1",
        10,
        "CEN18",
        "GOCAR",
        "6:30",
        "6:48"
    )
    voyage11 = voyage(
        "A1",
        11,
        "GOCAR",
        "CEN05",
        "7:30",
        "7:51"
    )
    voyage12 = voyage(
        "A1",
        12,
        "CEN18",
        "GOCAR",
        "7:00",
        "7:18"
    )

    listes = [voyage1, voyage2, voyage3, voyage4, voyage5, voyage6, voyage7, voyage8,
              voyage9, voyage10, voyage11, voyage12]
    BM = 5
    solutions = solvertest(
        listes,
        BM,
        True,
        10,
        max_services_matin=2,
        max_services_apres_midi=None,
        heure_debut_apres_midi=660,
        heure_fin_matin=1080,
        duree_max_service=540)

    for idx, services in enumerate(solutions, 1):
        print("\n" + "#" * 70)
        print(f"SOLUTION {idx}")
        print("#" * 70)

        for s in services:
            print(s)


