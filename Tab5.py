import csv
import logging
from typing import Dict, List

import customtkinter as ctk
from tkinter import ttk, messagebox as msgbox, filedialog

from completion_gloutonne import completer_services
from objet import service_agent
from outils_horaires import contraintes_service, minutes_vers_texte, texte_vers_minutes
from service_card import ServiceCard
from tabelauCSV import window_tableau_csv
from widgets_communs import (
    STYLE_BLEU, STYLE_ROUGE, STYLE-VERT, STYLE_VI0LET,
    creer_bouton_toolbar, creer_champ_heure, creer_ligne_heure, creer_note_aide,
)

logger = logging.getLogger(__name__)

TYPPES_SERVICE = ["matin", "après_midi"]

SYMBOLE_VIDE = "☐"
SYMBOLE_COCHE = "☑"
SYMBOLE_VERROU = "🔒"

COLONNES_VOYAGES = ("✓", "Voy.", "Ligne", "Début", "Fin", "De→À")
LARGEURS_COLONNES = {"✓": 35, "Voy.": 60, "Ligne": 70, "Début": 70, "Fin": 70, "De→À": 120}

ENTETE_EXPORT = ["Service", "Type", "Voyage", "Ligne", "Debut", "Fin", "De", "A"]
MESSAGE_FORMAT_HEURE = "Format d'heure invalide\nUtilisez HH:MM (ex: 14:30)"

class Tab5CreationManuelle(ctk.CTkFrame):
    """
        onglet 5: création manuelle de service
    """

    LARGEUR_PANNEAU_GAUCHE = 500
    LARGEUR_ROUGE_DROIT = 440

    def __init__(self, parent):
        super().__init__(parent)

        self.voyages_disponibles: list = []
        self._voyages_tries: list = []
        self.services: list = []
        self.service_selectionne = None
        self.compteur_services = 0
        self.voyages_assignes: Dict[int, objet] = {}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure([0], weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        self._creer_interface()

    def _creer_interface(self):
        self._creer_panneau_gauche()
        self._creer_panneau_central()
        self._creer_panneau_droit()

    def _creer_panneau_gauche(self) -> None:
        """
            liste des voyages disponibles avec cases à cocher
        """
        panneau = ctk.CTkFrame(self, width=self.LARGEUR_PANNEAU_GAUCHE)
        panneau.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        panneau.grid_propagate(False)

        ctk.CTkLabel(
            panneau, text="📋 Voyages Disponibles", font=("Arial", 18, "bold")
        ).pack(pady=10)