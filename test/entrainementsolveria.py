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


def valider_service(voyages, battement_minimum, verifier_arrets=True):

    if len(voyages) == 0:
        return True, []
    if len(voyages) == 1:
        return True, list(voyages)

    voyages_list = list(voyages)
    for i in range(len(voyages_list)):
        for j in range(i+1, len(voyages_list)):
            vi = voyages_list[i]
            vj = voyages_list[j]
            if vi.hdebut < vj.hfin and vj.hdebut < vi.hfin:
                return False, []

    def contruire_chaine(chaine_actuelle, restants):
        if not restants:
            return True, chaine_actuelle

        dernier =  chaine_actuelle[-1] if chaine_actuelle else None

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
                    valide , resultat = contruire_chaine(chaine_actuelle + [v], nouveau_restants)
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

def solvertest(listes, battement_minimum, verifier_arrets=True, max_solutions = 10):

    if not listes:
        return []

    model = cp_model.CpModel()
    n = len(listes)

    max_services = n
    service = [model.NewIntVar(0, max_services -1, f"service{i}") for i in range(n)]

    max_service_utilise = model.NewIntVar(0, max_services -1,"max_service_utilise")

    for i in range (n):
        model.Add(max_service_utilise >= service[i])

    for i in range(n):
        for j in range (i+1, n):
            vi = listes[i]
            vj = listes[j]

            #contrainte de chevauchement
            chevauchement =(
                vi.hdebut < vj.hfin and
                vj.hdebut < vi.hfin
            )

            if chevauchement:
                model.Add(service[i] != service[j])
                continue

            #contrainte qui vérifier si un voyage ne commence pas avant la fin du précédent
            if vj.hfin <= vi.hdebut:
                temps_entre = vi.hdebut - vj.hfin
                if temps_entre < battement_minimum:
                    model.Add(service[i] != service[j])
                    continue

                #vérification du temps de battement entre deux voyages
                if verifier_arrets and  temps_entre >= battement_minimum:
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

            #suite contrainte battement
            if vi.hfin <= vj.hdebut:
                temps_entre = vj.hdebut - vi.hfin
                if temps_entre < battement_minimum:
                    model.Add(service[i] != service[j])
                    continue

                #si temps suffisant vérifier les arrets
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

                    #si condition fausse ils ne peuvent pas etre sur le meme service
                    if (vi.arret_fin_id() != vj.arret_debut_id() and not peut_connecter):
                        model.Add(service[i] != service[j])

    model.Minimize(max_service_utilise)

    class SolutionCollector(cp_model.CpSolverSolutionCallback):
        def __init__(self, variables , limit):
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

    print(f"status: {solver.StatusName(status)}")
    print(f"solution: {solution_collector.solution_count()}")

    toutes_solutions = []

    for sol_idx, solution in enumerate(solution_collector.solutions, 1):
        services_dict = {}

        for i in range(n):
            num_service = solution[i]
            if num_service not in services_dict:
                services_dict[num_service] = []
            services_dict[num_service].append(listes[i])

        #afficher les services
        for num_service in sorted(services_dict.keys()):
            voyages_du_service = services_dict[num_service]
            print(f"service: {num_service}: {len(voyages_du_service)}voyages")
            for v in sorted(voyages_du_service, key=lambda x: x.hdebut):
                print(
                    f"voyage {v.num_voyage}: {v.arret_debut_id()} -> {v.arret_fin} ({v.hdebut //60:02d}:{v.hdebut % 60:02d}-{v.hfin // 60:02d}:{v.hfin % 60:02d})"
                )

        services_crees = []
        for num_service in sorted(services_dict.keys()):
            voyages_du_service = services_dict[num_service]

            est_valide, ordre_voyages = valider_service(
                voyages_du_service, battement_minimum, verifier_arrets
            )

            if not est_valide:
                print(f"service {num_service} pas valide")
                continue

            print(f"service {num_service}valide avec {len(ordre_voyages)} voyages")

            nouveau_service = service_agent(num_service=num_service)
            for v in ordre_voyages:
                nouveau_service.ajout_voyages(v)

            services_crees.append(nouveau_service)

        if services_crees:
            toutes_solutions.append(services_crees)

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
    listes = [voyage1, voyage2, voyage3, voyage4, voyage5, voyage6, voyage7, voyage8]
    BM = 5
    solutions = solvertest(listes, BM)

    for idx, services in enumerate(solutions, 1):
        print("\n" + "#" * 70)
        print(f"SOLUTION {idx}")
        print("#" * 70)

        for s in services:
            print(s)


