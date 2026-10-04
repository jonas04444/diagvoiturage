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
