from .temps import time_to_minutes, minutes_to_time


class voyage:

    def __init__(self, num_ligne, num_voyage, arret_debut, arret_fin,
                 heure_debut, heure_fin, js_srv="", assigned=False):
        self.num_ligne = num_ligne
        self.num_voyage = num_voyage
        self.arret_debut = arret_debut
        self.arret_fin = arret_fin
        self.hdebut = time_to_minutes(heure_debut)
        self.hfin = time_to_minutes(heure_fin)
        self.js_srv = js_srv
        self.distance = None
        self.assigned = assigned

    def arret_debut_id(self):
        return self.arret_debut[:3]

    def arret_fin_id(self):
        return self.arret_fin[:3]

    # Gardés pour compatibilité avec voyage.time_to_minutes(...) ailleurs dans le projet
    time_to_minutes = staticmethod(time_to_minutes)
    minutes_to_time = staticmethod(minutes_to_time)
