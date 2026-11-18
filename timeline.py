"""Affichage d'une solution du solveur sous forme de timeline sur un Canvas."""

from tkinter import messagebox as msgbox

from objet import voyage

COULEURS_LIGNES = {
    "A1": "#FF6B6B",
    "25": "#4ECDC4",
    "35": "#45B7D1",
    "43": "#FFA07A",
    "83": "#98D8C8",
    "86": "#F7DC6F",
    "85": "#BB8FCE",
    "63": "#85C1E2",
    "41": "#F8B88B",
    "M4": "#AED6F1",
}
COULEUR_DEFAUT = "#CCCCCC"
COULEUR_ORPHELIN = "#FF6B6B"


class TimelineCanvas:
    """Dessine les services (matin, après-midi, orphelins) sur un Canvas Tk."""

    def __init__(self, canvas, trips_data):
        """Initialise la timeline.

        Args:
            canvas: Canvas Tk sur lequel dessiner.
            trips_data: Liste des voyages (dictionnaires avec les clés
                « start », « end », « from », « to » et « line »).
        """
        self.canvas = canvas
        self.trips = trips_data
        self.timeline_start = 4 * 60
        self.timeline_end = 24 * 60
        self.timeline_height = 600
        self.timeline_width = 1200
        self.service_height = 50
        self.padding_top = 50
        self.padding_left = 80
        self.padding_bottom = 50
        self.colors = COULEURS_LIGNES

    def draw_solution(self, solution):
        """Dessine une solution complète.

        Args:
            solution: Dictionnaire avec les clés « matin » et « apres_midi »
                (service_id -> liste de (index, voyage)) et « orphelins »
                (liste d'index de voyages non affectés).
        """
        self.canvas.delete("all")
        self.canvas.update()

        largeur = self.canvas.winfo_width()
        hauteur = self.canvas.winfo_height()
        if largeur <= 1 or hauteur <= 1:
            msgbox.showerror(
                "Erreur", f"Canvas dimensions invalides: {largeur}x{hauteur}"
            )
            return

        self._draw_timeline_background()
        self._draw_time_labels()

        current_y = self.padding_top
        current_y = self._draw_section(current_y, "MATIN", solution["matin"], "AM")
        current_y = self._draw_section(
            current_y, "APRES-MIDI", solution["apres_midi"], "PM"
        )
        self._draw_orphans(current_y, solution["orphelins"])

    def _draw_section(self, y, titre, services, prefixe):
        """Dessine un bloc de services (matin ou après-midi).

        Args:
            y: Position verticale de départ.
            titre: Titre de la section.
            services: Dictionnaire service_id -> liste de (index, voyage).
            prefixe: Préfixe du libellé de chaque service (« AM » ou « PM »).

        Returns:
            La nouvelle position verticale après la section.
        """
        if not services:
            return y

        self.canvas.create_text(
            10, y, text=titre, font=("Arial", 10, "bold"), anchor="w", fill="white"
        )
        y += 20

        for service_id, trips in services.items():
            self._draw_service_line(y, trips, f"{prefixe}-{service_id}")
            y += self.service_height + 5
        return y

    def _draw_orphans(self, y, orphelins):
        """Dessine les voyages non affectés à un service.

        Args:
            y: Position verticale de départ.
            orphelins: Liste d'index de voyages orphelins.
        """
        if not orphelins:
            return

        y += 15
        self.canvas.create_text(
            10, y, text="⚠️ ORPHELINS", font=("Arial", 10, "bold"),
            anchor="w", fill=COULEUR_ORPHELIN,
        )
        y += 20

        for trip_idx in orphelins:
            self._draw_trip_rect(
                y, self.trips[trip_idx], COULEUR_ORPHELIN, f"Orphelin-{trip_idx}"
            )
            y += 25

    def _draw_timeline_background(self):
        """Dessine le fond de la timeline."""
        # TODO: rendre les couleurs paramétrables
        self.canvas.create_rectangle(
            self.padding_left, self.padding_top,
            self.padding_left + self.timeline_width,
            self.padding_top + self.timeline_height,
            fill="#2b2b2b", outline="#555555",
        )

    def _draw_time_labels(self):
        """Affiche les repères horaires (une graduation toutes les 2 heures)."""
        for hour in range(4, 25, 2):
            x = self._time_to_x(hour * 60)
            self.canvas.create_line(
                x, self.padding_top,
                x, self.padding_top + self.timeline_height,
                fill="#444444", dash=(2, 2),
            )
            self.canvas.create_text(
                x, self.padding_top - 20,
                text=f"{hour:02d}h", font=("Arial", 9), fill="white",
            )

    def _draw_trip_rect(self, y, trip, color, label):
        """Dessine le rectangle d'un voyage avec son libellé et ses horaires.

        Args:
            y: Position verticale du rectangle.
            trip: Voyage (dictionnaire avec « start » et « end » en minutes).
            color: Couleur de remplissage.
            label: Texte affiché au-dessus des horaires.
        """
        x1 = self._time_to_x(trip["start"])
        x2 = self._time_to_x(trip["end"])
        y2 = y + self.service_height

        self.canvas.create_rectangle(x1, y, x2, y2, fill=color, outline="white", width=2)

        mid_x = (x1 + x2) / 2
        mid_y = (y + y2) / 2
        start_time = voyage.minutes_to_time(trip["start"])
        end_time = voyage.minutes_to_time(trip["end"])

        self.canvas.create_text(
            mid_x, mid_y - 8, text=label, font=("Arial", 8, "bold"), fill="black"
        )
        self.canvas.create_text(
            mid_x, mid_y + 8, text=f"{start_time}-{end_time}",
            font=("Arial", 7), fill="black",
        )

    def _time_to_x(self, minutes):
        """Convertit une heure (en minutes depuis minuit) en coordonnée X."""
        ratio = (minutes - self.timeline_start) / (self.timeline_end - self.timeline_start)
        return self.padding_left + ratio * self.timeline_width

    def _draw_service_line(self, y, trips, service_label):
        """Dessine une ligne de service avec ses voyages.

        Args:
            y: Position verticale de la ligne.
            trips: Liste de tuples (index, voyage).
            service_label: Libellé du service affiché à gauche.
        """
        self.canvas.create_text(
            10, y + self.service_height // 2,
            text=service_label, font=("Arial", 9, "bold"), anchor="w", fill="white",
        )

        for _, trip in sorted(trips, key=lambda t: t[1]["start"]):
            color = self.colors.get(trip.get("line", "default"), COULEUR_DEFAUT)
            self._draw_trip_rect(y, trip, color, f"{trip['from'][:3]}-{trip['to'][:3]}")