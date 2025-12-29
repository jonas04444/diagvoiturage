from ortools.sat.python import cp_model

# ======================================================
# TON CODE D’ORIGINE — STRICTEMENT INCHANGÉ
# ======================================================

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


def valider_service(voyages, battement_minimum, battement_maximum, verifier_arrets=True,
                    duree_cible=450, tolerance_duree=400):
    if len(voyages) <= 1:
        return True, list(voyages)

    voyages_ordonnes = sorted(voyages, key=lambda v: v.hdebut)

    for i in range(len(voyages_ordonnes) - 1):
        if not voyages_compatibles(
            voyages_ordonnes[i],
            voyages_ordonnes[i + 1],
            voyages_ordonnes,
            battement_minimum,
            battement_maximum,
            verifier_arrets
        ):
            return False, []

    debut = min(v.hdebut for v in voyages_ordonnes)
    fin = max(v.hfin for v in voyages_ordonnes)
    duree = fin - debut

    if abs(duree - duree_cible) > tolerance_duree:
        return False, []

    return True, voyages_ordonnes


def calculer_duree_service(voyages_list):
    if not voyages_list:
        return 0
    debut = min(v.hdebut for v in voyages_list)
    fin = max(v.hfin for v in voyages_list)
    return fin - debut


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    def __init__(self, service, max_solutions=None):
        super().__init__()
        self.service = service
        self.solutions = []
        self.max_solutions = max_solutions

    def OnSolutionCallback(self):
        sol = [self.Value(s) for s in self.service]
        self.solutions.append(sol)
        if self.max_solutions is not None and len(self.solutions) >= self.max_solutions:
            self.StopSearch()


def voyages_compatibles(v1, v2, voyages, battement_minimum, battement_maximum, verifier_arrets=True):
    if v2.hdebut < v1.hfin:
        return False

    temps_entre = v2.hdebut - v1.hfin
    if temps_entre < battement_minimum:
        return False

    if battement_maximum is not None and temps_entre > battement_maximum:
        return False

    if not verifier_arrets:
        return True

    if v1.arret_fin_id() == v2.arret_debut_id():
        return True

    for vp in voyages:
        if vp is v1 or vp is v2:
            continue

        if (v1.hfin <= vp.hdebut and vp.hfin <= v2.hdebut and
                v1.arret_fin_id() == vp.arret_debut_id() and
                vp.arret_fin_id() == v2.arret_debut_id()):
            return True

    return False


def solvertest(listes, battement_minimum, battement_maximum=50, verifier_arrets=True,
               max_solutions=10, max_services_matin=None, max_services_apres_midi=None,
               heure_debut_apres_midi=660, heure_fin_matin=1080, duree_max_service=540):

    model = cp_model.CpModel()
    n = len(listes)

    if max_services_matin is None:
        max_services_matin = n
    if max_services_apres_midi is None:
        max_services_apres_midi = n

    max_services_total = max_services_matin + max_services_apres_midi
    service = [model.NewIntVar(0, max_services_total - 1, f"service{i}") for i in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            vi = listes[i]
            vj = listes[j]

            if vi.hdebut < vj.hfin and vj.hdebut < vi.hfin:
                model.Add(service[i] != service[j])
                continue

            if vi.hfin <= vj.hdebut:
                if not voyages_compatibles(vi, vj, listes, battement_minimum, None, verifier_arrets):
                    model.Add(service[i] != service[j])

            if vj.hfin <= vi.hdebut:
                if not voyages_compatibles(vj, vi, listes, battement_minimum, None, verifier_arrets):
                    model.Add(service[i] != service[j])

    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.max_time_in_seconds = 30

    collector = SolutionCollector(service, max_solutions)
    solver.SearchForAllSolutions(model, collector)

    toutes_les_solutions = []

    for sol in collector.solutions:
        services = {}
        for i, s in enumerate(sol):
            services.setdefault(s, []).append(listes[i])

        resultat = []
        for s, vs in services.items():
            voyage_ordonnes = sorted(vs, key=lambda v: v.hdebut)
            debut = min(v.hdebut for v in voyage_ordonnes)
            type_service = "matin" if debut < heure_debut_apres_midi else "apres"
            sa = service_agent(s, type_service)
            for v in voyage_ordonnes:
                sa.ajout_voyages(v)
            resultat.append(sa)

        toutes_les_solutions.append(resultat)

    return toutes_les_solutions


# ======================================================
# TON MAIN ORIGINAL — PRINTS CONSERVÉS
# ======================================================

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
    voyage13 = voyage(
        "A1",
        13,
        "GOCAR",
        "CEN05",
        "7:40",
        "8:01"
    )
    voyage14 = voyage(
        "A1",
        14,
        "CEN18",
        "GOCAR",
        "7:10",
        "7:28"
    )

    listes = [voyage1, voyage2, voyage3, voyage4, voyage5, voyage6, voyage7, voyage8,
              voyage9, voyage10, voyage11, voyage12, voyage13, voyage14]

    BM = 5

    solutions = solvertest(
        listes,
        battement_minimum=BM,
        verifier_arrets=True,
        battement_maximum=50,
        max_solutions=10,
        max_services_matin=3,
        max_services_apres_midi=None,
        heure_debut_apres_midi=660,
        heure_fin_matin=1080,
        duree_max_service=540
    )

    for idx, services in enumerate(solutions, 1):
        print("\n" + "#" * 70)
        print(f"SOLUTION {idx}")
        print("#" * 70)
        for s in services:
            print(s)

    # ==================================================
    # AJOUT GUI — APRÈS LES PRINTS (SANS INTERFÉRENCE)
    # ==================================================

    import tkinter as tk
    from tkinter import ttk
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    class TimelineApp(tk.Tk):
        def __init__(self, solutions):
            super().__init__()
            self.title("Visualisation des solutions")
            self.geometry("1600x700")

            self.solutions = solutions

            self.fig, self.ax = plt.subplots(figsize=(18, 6))
            self.canvas = FigureCanvasTkAgg(self.fig, self)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)

            btn_frame = ttk.Frame(self)
            btn_frame.pack(pady=10)

            for i in range(min(10, len(solutions))):
                ttk.Button(
                    btn_frame,
                    text=f"Solution {i+1}",
                    command=lambda idx=i: self.draw_solution(idx)
                ).pack(side="left", padx=5)

            self.draw_solution(0)

        def draw_solution(self, idx):
            self.ax.clear()
            y = 0
            for s in self.solutions[idx]:
                for v in s.get_voyages():
                    self.ax.broken_barh([(v.hdebut, v.hfin - v.hdebut)], (y, 8))
                    self.ax.text(v.hdebut + (v.hfin - v.hdebut)/2, y+4,
                                 f"{v.num_ligne}-{v.num_voyage}",
                                 ha="center", va="center", fontsize=8)
                y += 12

            self.ax.set_xlim(240, 1440)
            self.ax.set_xticks(range(240, 1441, 60))
            self.ax.set_xticklabels([f"{h//60:02d}h" for h in range(240, 1441, 60)])
            self.ax.set_title("Timeline des services")
            self.ax.grid(True, axis="x")
            self.canvas.draw()

    TimelineApp(solutions).mainloop()
