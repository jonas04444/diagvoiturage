from ortools.sat.python import cp_model


class hlp:
    """
    Haut Le Pied - trajet à vide entre deux arrêts.

    Utilisé quand un chauffeur doit se repositionner entre deux voyages
    dont les arrêts ne s'enchaînent pas.
    """

    def __init__(self, arret_depart, arret_arrivee, duree, heure_debut=None):
        """
        Args:
            arret_depart: Arrêt de départ du HLP
            arret_arrivee: Arrêt d'arrivée du HLP
            duree: Durée en minutes
            heure_debut: Heure de début en minutes (optionnel)
        """
        self.arret_depart = arret_depart
        self.arret_arrivee = arret_arrivee
        self.duree = duree
        self.heure_debut = heure_debut

    @property
    def heure_fin(self):
        if self.heure_debut is not None:
            return self.heure_debut + self.duree
        return None

    def __str__(self):
        if self.heure_debut is not None:
            h_debut = voyage.minutes_to_time(self.heure_debut)
            h_fin = voyage.minutes_to_time(self.heure_fin)
            return f"  ⚠ HLP: {self.arret_depart} → {self.arret_arrivee} ({h_debut} - {h_fin}, {self.duree} min)"
        return f"  ⚠ HLP: {self.arret_depart} → {self.arret_arrivee} ({self.duree} min)"

    def __repr__(self):
        return self.__str__()


class service_agent:

    def __init__(self, num_service=None, type_service="matin"):
        self.voyages = []
        self.hlps = []  # Liste des HLP du service
        self.num_service = num_service
        self.type_service = type_service
        self.heure_debut = None
        self.heure_fin = None
        self.heure_debut_coupure = None
        self.heure_fin_coupure = None

    def ajouter_voyage(self, voyage):
        valide, erreur = self.voyage_dans_limites(voyage)
        if not valide:
            raise ValueError(f"Voyage invalide: {erreur}")
        self.voyages.append(voyage)

    def ajouter_hlp(self, hlp_obj):
        """Ajoute un HLP au service."""
        self.hlps.append(hlp_obj)

    def get_voyages(self):
        return self.voyages

    def get_hlps(self):
        return self.hlps

    def set_limites(self, heure_debut, heure_fin):
        self.heure_debut = heure_debut
        self.heure_fin = heure_fin

    def set_coupure(self, heure_debut_coupure, heure_fin_coupure):
        self.heure_debut_coupure = heure_debut_coupure
        self.heure_fin_coupure = heure_fin_coupure

    def voyage_dans_limites(self, voyage):
        if self.heure_debut is not None and self.heure_fin is not None:
            if voyage.hdebut < self.heure_debut:
                return False, "commence avant la limite de début"

            if voyage.hfin > self.heure_fin:
                return False, "termine après la limite de fin"

        if self.type_service == "coupé":
            if self.heure_debut_coupure is not None and self.heure_fin_coupure is not None:
                if not (voyage.hfin <= self.heure_debut_coupure or voyage.hdebut >= self.heure_fin_coupure):
                    h_deb_coup = f"{self.heure_debut_coupure // 60:02d}h{self.heure_debut_coupure % 60:02d}"
                    h_fin_coup = f"{self.heure_fin_coupure // 60:02d}h{self.heure_fin_coupure % 60:02d}"
                    return False, f"chevauche la coupure ({h_deb_coup}-{h_fin_coup})"

        return True, None

    def duree_services(self):
        if not self.voyages:
            return 0
        debut = min(v.hdebut for v in self.voyages)
        fin = max(v.hfin for v in self.voyages)
        return fin - debut

    def duree_coupure(self):
        if self.heure_debut_coupure is not None and self.heure_fin_coupure is not None:
            return self.heure_fin_coupure - self.heure_debut_coupure
        return 0

    def duree_travail_effective(self):
        duree_totale = self.duree_services()
        return duree_totale - self.duree_coupure()

    def duree_hlp_totale(self):
        """Retourne la durée totale des HLP en minutes."""
        return sum(h.duree for h in self.hlps)

    def get_elements_chronologiques(self):
        """
        Retourne tous les éléments (voyages et HLP) triés chronologiquement.

        Returns:
            Liste de tuples (type, element) où type est 'voyage' ou 'hlp'
        """
        elements = []

        for v in self.voyages:
            elements.append(('voyage', v, v.hdebut))

        for h in self.hlps:
            if h.heure_debut is not None:
                elements.append(('hlp', h, h.heure_debut))

        # Trier par heure de début
        elements.sort(key=lambda x: x[2])

        return [(e[0], e[1]) for e in elements]

    def __str__(self):
        if not self.voyages:
            return f"Service {self.num_service}: vide"

        elements = self.get_elements_chronologiques()

        debut_service = min(v.hdebut for v in self.voyages)
        fin_service = max(v.hfin for v in self.voyages)

        result = f"Service {self.num_service} ({self.type_service.upper()}): {len(self.voyages)} voyages"
        if self.hlps:
            result += f", {len(self.hlps)} HLP"
        result += "\n"
        result += f"  Début: {voyage.minutes_to_time(debut_service)}, Fin: {voyage.minutes_to_time(fin_service)}\n"

        for type_elem, elem in elements:
            if type_elem == 'voyage':
                result += f"  • Voyage {elem.num_voyage}: {elem.arret_debut} → {elem.arret_fin} "
                result += f"({voyage.minutes_to_time(elem.hdebut)} - {voyage.minutes_to_time(elem.hfin)})\n"
            else:  # hlp
                result += f"{elem}\n"

        if self.hlps:
            result += f"  → Temps HLP total: {self.duree_hlp_totale()} min\n"

        return result.rstrip()


class voyage:

    def __init__(self, num_ligne, num_voyage, arret_debut, arret_fin, heure_debut, heure_fin, js_srv=""):
        self.num_ligne = num_ligne
        self.num_voyage = num_voyage
        self.arret_debut = arret_debut
        self.arret_fin = arret_fin
        self.hdebut = self.time_to_minutes(heure_debut)
        self.hfin = self.time_to_minutes(heure_fin)
        self.js_srv = js_srv
        self.distance = None

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


class proposition:
    def __init__(self):
        self.service = []

    def ajout_service(self, service):
        self.service.append(service)

    def total_voyages(self):
        return sum(len(s.get_voyages()) for s in self.service)

    def total_hlps(self):
        return sum(len(s.get_hlps()) for s in self.service)

    def duree_hlp_totale(self):
        return sum(s.duree_hlp_totale() for s in self.service)