import logging
from tkinter import Canvas
from typing import Optional, List

import customtkinter as ctk

logger = logging.getLogger(__name__)

class TimelineVisuelle(ctk.CTkFrame):
    """
    affiche les voyages d'un service sur une ligne horaire.

    Attributes:
        service: Le service dont on affiche les voyages
        canvas: Le canvas Tkinter utilisé pour dessiner
    """

    HEURE_DEBUT_MIN = 4 * 60
    HEURE_FIN_MIN = 24 * 60

    LARGEUR_MINIMALE = 700
    HAUTEUR_CANVAS = 150
    HAUTEUR_MINIMALE = 100

    HAUTEUR_RECTANGLE = 40
    ESPACE_ENTRE_LIGNES = 5
    MARGE_HAUTE = 25

    MARGE_HORIZONTALE = 50
    DELAI_REDESSIN_MS = 100
    DELAI_INITIAL_MS = 200

    COULEURS_PAR_LIGNE ={
        "A1": "#FF6B6B", "C00A1": "#FF6B6B",
        "25": "#4ECDC4", "C0025": "#4ECDC4",
        "35": "#45B7D1", "C0035": "#45B7D1",
        "43": "#FFA07A", "C0043": "#FFA07A",
        "83": "#98D8C8", "C0083": "#98D8C8",
        "86": "#F7DC6F", "C0086": "#F7DC6F",
    }
    COULEURS_PAR_DEFAUT = "#CCCCCC"

    def __init__(self, parent, service=None, **kwargs):
        """
        init widget

        Args:
            parent: Widget parent CustomTkinter
            service: Service à afficher
            **kwargs: Arguments transmis à CTkFrame
        """
        super().__init__(parent, **kwargs)
        self.service = service
        self.canvas: Optional[Canvas] = None
        self._timer_redraw: Optional[str] = None

        self._creer_canvas()
        self.after(self.DELAI_INITIAL_MS, self._dessiner_initial)

    def _creer_canvas(self) -> None:
        """
            Crée le canvas et branche les événements de redimensionnement
        """
        self.canvas = Canvas(
            self,
            width=self.HAUTEUR_CANVAS,
            height=self.LARGEUR_MINIMALE,
            highlightthickness=1,
            highlightcolor="#555555",
        )
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event) -> None:
        """
            Planifie un redessin après redimensionnement
        """
        if self._timer_redraw is not None:
            self.after_cancel(self._timer_redraw)
        self._timer_redraw = self.after(self.DELAI_REDESSIN_MS, self.rafraichir)

    def _dessiner_initial(self) -> None:
        """
            Déclenche le premier dessin une fois le widgent prêt
        """
        self.rafraichir()

    def rafraichir(self) -> None:
        """
            Redessine la timeline en fonction de l'état actuel du service
        """
        if self.service and self.service.voyages:
            self._dessiner_service()
        else:
            self._dessiner_vide()

    def set_service(self, service) -> None:
        """
            Remplace le service affiché et redessine la timeline
        Args:
            service: Nouveau service à afficherr, ou None pour vider timeline
        """
        self.service = service
        self.rafraichir()

    def _dimensions_canvas(self) -> tuple[int, int]:
        """
            Retourne la dimension du canvas, avec un minimum garanti
        """
        self.canvas.update_idletasks()
        width = max(self.canvas.winfo_width(), self.LARGEUR_MINIMALE)
        height = max(self.canvas.winfo_height(), self.HAUTEUR_MINIMALE)
        return width, height

    def _dessiner_grille_horaire(self, width: int, height: int) -> None:
        """
            Dessine les lignes verticales et libéllés d'heure (4h à 24h)
        """
        for heure in range(4, 25, 2):
            x = self._heure_vers_x(heure * 60, width)
            self.canvas.create_line(
                x, 20, x, height - 10, fill="#444444", dash=(2, 2)
            )
            self.canvas.create_text(
                x, 10, text=f"{heure:02d}h", fill="white", font=("Arial", 8)
            )

    def _dessiner_vide(self) -> None:
        """
            Dessine une timeline sans voyage, avec un message explicatif
        """
        self.canvas.delete("all")
        width, height = self._dimensions_canvas()

        self._dessiner_grille_horaire(width, height)
        self.canvas.create_text(
            width // 2, height //2,
            text="Service vide - ajouter des voyages",
            fill="#888888", font=("Arial", 10, "italic")
        )

    def _dessiner_service(self) -> None:
        """
            Dessine tous les voyages du service, répartis pour éviter les chevauchements
        """
        self.canvas.delete("all")
        width, height = self._dimensions_canvas()

        logger.debug("Dessin timeline - Canvas: %dx%d px", width, height)
        self._dessiner_grille_horaire(width, height)

        if not self.service or not self.service.voyages:
            self._dessiner_vide()
            return

        logger.debug("Service avec %d voyage(s)", len(self.service.voyages))

        lignes = self._repartir_voyages_sans_chevauchement(self.service.voyages)
        logger.debug("Répartition sur %d ligne(s) verticale(s)", len(lignes))

        for idx_ligne, voyages_ligne in enumerate(lignes):
            y_rect = self.MARGE_HAUTE + idx_ligne * (
                    self.HAUTEUR_RECTANGLE + self.ESPACE_ENTRE_LIGNES
            )
            for voyage in voyages_ligne:
                self._dessiner_voyage(voyage, y_rect, width)

    @staticmethod
    def _se_chevauchent(a, b) -> bool:
        """Indique si deux voyages se chevauchent dans le temps."""
        return not (a.hfin <= b.hdebut or a.hdebut >= b.hfin)

    def _repartir_voyages_sans_chevauchement(self, voyages) -> List[list]:
        """Répartit les voyages sur des lignes verticales sans chevauchement.

        Algorithme glouton : chaque voyage est placé sur la première ligne
        existante où il ne chevauche aucun voyage déjà présent, sinon une
        nouvelle ligne est créée.

        Args:
            voyages: Itérable de voyages, chacun avec des attributs `hdebut`/`hfin`.

        Returns:
            Une liste de lignes, chaque ligne étant une liste de voyages.
        """
        voyages_tries = sorted(voyages, key=lambda v: v.hdebut)
        lignes: List[list] = []

        for voyage in voyages_tries:
            ligne_disponible = next(
                (
                    ligne for ligne in lignes
                    if not any(self._se_chevauchent(voyage, v) for v in ligne)
                ),
                None,
            )
            if ligne_disponible is not None:
                ligne_disponible.append(voyage)
            else:
                lignes.append([voyage])

        return lignes

    def _dessiner_voyage(self, voyage, y_rect: float, width: int) -> None:
        """Dessine le rectangle représentant un voyage unique."""
        x1 = self._heure_vers_x(voyage.hdebut, width)
        x2 = self._heure_vers_x(voyage.hfin, width)

        logger.debug(
            "V%s: %s-%s (%d-%d min) -> x1=%.1f, x2=%.1f y=%.1f",
            voyage.num_voyage,
            self._minutes_vers_texte(voyage.hdebut),
            self._minutes_vers_texte(voyage.hfin),
            voyage.hdebut, voyage.hfin, x1, x2, y_rect,
        )

        couleur = self._get_color(voyage.num_ligne)
        self.canvas.create_rectangle(
            x1, y_rect, x2, y_rect + self.HAUTEUR_RECTANGLE,
            fill=couleur, outline="white", width=2,
        )

        mid_x = (x1 + x2) / 2
        mid_y = y_rect + self.HAUTEUR_RECTANGLE / 2

        self.canvas.create_text(
            mid_x, mid_y - 8,
            text=f"V{voyage.num_voyage}",
            fill="black", font=("Arial", 9, "bold"),
        )
        self.canvas.create_text(
            mid_x, mid_y + 8,
            text=f"{voyage.arret_debut[:3]}→{voyage.arret_fin[:3]}",
            fill="black", font=("Arial", 7),
        )

    # --- Utilitaires ------------------------------------------------------

    def _heure_vers_x(self, minutes: int, width: int) -> float:
        """Convertit une heure (en minutes depuis minuit) en coordonnée X."""
        ratio = (minutes - self.HEURE_DEBUT_MIN) / (
                self.HEURE_FIN_MIN - self.HEURE_DEBUT_MIN
        )
        return self.MARGE_HORIZONTALE + ratio * (width - 2 * self.MARGE_HORIZONTALE)

    @staticmethod
    def _minutes_vers_texte(minutes: int) -> str:
        """Formate des minutes depuis minuit en texte 'HHhMM'."""
        return f"{minutes // 60:02d}h{minutes % 60:02d}"

    def _get_color(self, ligne: str) -> str:
        """Retourne la couleur associée à une ligne, ou la couleur par défaut."""
        return self.COULEURS_PAR_LIGNE.get(ligne, self.COULEUR_PAR_DEFAUT)