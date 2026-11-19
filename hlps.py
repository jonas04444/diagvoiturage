from .temps import minutes_to_time


class hlp:
    """Haut-le-pied : déplacement à vide entre deux arrêts."""

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
        if self.heure_debut is None:
            return None
        return self.heure_debut + self.duree

    def __str__(self):
        base = f"  ⚠ HLP: {self.arret_depart} → {self.arret_arrivee}"
        if self.heure_debut is None:
            return f"{base} ({self.duree} min)"
        h_debut = minutes_to_time(self.heure_debut)
        h_fin = minutes_to_time(self.heure_fin)
        return f"{base} ({h_debut} - {h_fin}, {self.duree} min)"

    __repr__ = __str__
