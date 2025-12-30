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

    def __init__(self, num_ligne, num_voyage, arret_debut, arret_fin, heure_debut, heure_fin,js_srv=""):
        self.num_ligne = num_ligne
        self.num_voyage = num_voyage
        self.arret_debut = arret_debut
        self.arret_fin = arret_fin
        self.hdebut = self.time_to_minutes(heure_debut)
        self.hfin = self.time_to_minutes(heure_fin)
        self.js_srv = js_srv

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