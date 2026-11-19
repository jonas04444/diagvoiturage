from .temps import minutes_to_time


class service_agent:

    def __init__(self, num_service=None, type_service="matin"):
        self.num_service = num_service
        self.type_service = type_service
        self.voyages = []
        self.hlps = []
        # Limites du service
        self.heure_debut = None
        self.heure_fin = None
        # Coupure (services « coupé »)
        self.heure_debut_coupure = None
        self.heure_fin_coupure = None

    # ------------------------------------------------------------ Contenu
    def ajouter_voyage(self, v):
        valide, erreur = self.voyage_dans_limites(v)
        if not valide:
            raise ValueError(f"Voyage invalide: {erreur}")
        self.voyages.append(v)

    def ajouter_hlp(self, hlp_obj):
        self.hlps.append(hlp_obj)

    def get_voyages(self):
        return self.voyages

    def get_hlps(self):
        return self.hlps

    # ------------------------------------------------------------ Limites
    def set_limites(self, heure_debut, heure_fin):
        self.heure_debut = heure_debut
        self.heure_fin = heure_fin

    def set_coupure(self, heure_debut_coupure, heure_fin_coupure):
        self.heure_debut_coupure = heure_debut_coupure
        self.heure_fin_coupure = heure_fin_coupure

    def _a_des_limites(self):
        return self.heure_debut is not None and self.heure_fin is not None

    def _a_une_coupure(self):
        return self.heure_debut_coupure is not None and self.heure_fin_coupure is not None

    def voyage_dans_limites(self, v):
        """Renvoie (True, None) si le voyage est acceptable, sinon (False, raison)."""
        if self._a_des_limites():
            if v.hdebut < self.heure_debut:
                return False, "commence avant la limite de début"
            if v.hfin > self.heure_fin:
                return False, "termine après la limite de fin"

        if self.type_service == "coupé" and self._a_une_coupure():
            chevauche = not (v.hfin <= self.heure_debut_coupure
                             or v.hdebut >= self.heure_fin_coupure)
            if chevauche:
                debut = minutes_to_time(self.heure_debut_coupure)
                fin = minutes_to_time(self.heure_fin_coupure)
                return False, f"chevauche la coupure ({debut}-{fin})"

        return True, None

    # ------------------------------------------------------------- Durées
    def _bornes_voyages(self):
        """(début du premier voyage, fin du dernier voyage). Suppose self.voyages non vide."""
        return (min(v.hdebut for v in self.voyages),
                max(v.hfin for v in self.voyages))

    def duree_services(self):
        if not self.voyages:
            return 0
        debut, fin = self._bornes_voyages()
        return fin - debut

    def duree_coupure(self):
        if self._a_une_coupure():
            return self.heure_fin_coupure - self.heure_debut_coupure
        return 0

    def duree_travail_effective(self):
        return self.duree_services() - self.duree_coupure()

    def duree_hlp_totale(self):
        """Durée totale des HLP en minutes."""
        return sum(h.duree for h in self.hlps)

    # ------------------------------------------------------------ Affichage
    def get_elements_chronologiques(self):
        """Voyages et HLP (datés) triés par heure de début : [('voyage'|'hlp', objet), ...]"""
        elements = [('voyage', v, v.hdebut) for v in self.voyages]
        elements += [('hlp', h, h.heure_debut) for h in self.hlps if h.heure_debut is not None]
        elements.sort(key=lambda e: e[2])
        return [(type_elem, elem) for type_elem, elem, _ in elements]

    def __str__(self):
        if not self.voyages:
            return f"Service {self.num_service}: vide"

        debut, fin = self._bornes_voyages()
        lignes = ", ".join(sorted({v.num_ligne for v in self.voyages}))

        entete = (f"Service {self.num_service} ({self.type_service.upper()}): "
                  f"{len(self.voyages)} voyages [Lignes: {lignes}]")
        if self.hlps:
            entete += f", {len(self.hlps)} HLP"

        sortie = [
            entete,
            f"  Début: {minutes_to_time(debut)}, Fin: {minutes_to_time(fin)}",
        ]

        for type_elem, elem in self.get_elements_chronologiques():
            if type_elem == 'voyage':
                sortie.append(
                    f"  • Voyage {elem.num_voyage}: {elem.arret_debut} → {elem.arret_fin} "
                    f"({minutes_to_time(elem.hdebut)} - {minutes_to_time(elem.hfin)})"
                )
            else:
                sortie.append(str(elem))

        if self.hlps:
            sortie.append(f"  → Temps HLP total: {self.duree_hlp_totale()} min")

        return "\n".join(sortie)
