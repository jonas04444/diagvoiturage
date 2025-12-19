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

    def dernier_voyage(self):
        if not self.voyages:
            return None
        return max(self.voyages, key=lambda v: v.hfin)

    def peut_ajouter_voyage(self, nouveau_voyage, battement_minimum, verifier_arrets=False):
        if not self.voyages:
            return True
        for v in self.voyages:
            if self._voyages_se_chevauche(v, nouveau_voyage):
                return False

        dernier = self.dernier_voyage()

        if nouveau_voyage.hdebut < dernier.hfin:
            return False

        battement = nouveau_voyage.hdebut - dernier.hfin
        if battement < battement_minimum:
            return False

        if verifier_arrets:
            if dernier.arret_fin_id() != nouveau_voyage.arret_debut_id():
                return False

        return True

    def _voyages_se_chevauche(self, v1, v2):
        return (v1.hdebut < v2.hfin and v2.hdebut < v1.hfin)

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

def solvertest(listes, battement_minimum, verifier_arrets=False, verbose=True):
    voyages_tries = sorted(listes, key=lambda v: v.hdebut)

    services = []
    num_service_actuel = 1

    for v in voyages_tries:
        service_trouve = None

        for service in services:
            peut_ajouter, raison = service.peut_ajouter_voyage(v, battement_minimum, verifier_arrets)
            if peut_ajouter:
                service_trouve = service
                break

        if service_trouve:
            service_trouve.ajout_voyages(v)
        else:
            nouveau_service = service_agent(num_service=num_service_actuel)
            nouveau_service.ajout_voyages(v)
            services.append(nouveau_service)
            num_service_actuel += 1

    for service in services:
        print(service)
        print()
    return services

BM = 5
MS=5
solvertest(BM,MS)
