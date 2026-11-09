from typing import Optional

import customtkinter as ctk

from outils_horaires import minutes_vers_texte

STYLE_VERT = {"fg_color": "#4CAF50", "hover_color": "#388E3C"}
STYLE_ROUGE = {"fg_color": "#FF4444", "hover_color": "#CC0000"}
STYLE_ORANGE = {"fg_color": "#FF9800", "hover_color": "#F57C00"}
STYLE_BLEU = {"fg_color": "#2196F3", "hover_color": "#1976D2"}
STYLE_VIOLET = {"fg_color": "#9C27B0", "hover_color": "#7B1FA2"}

def creer_champ_heure(parent, libelle: str, valeur: Optional[int] = None,
                      placheholder: str = "HH:MM") -> ctk.CTkEntry:
    ctk.CTkLabel(parent, text=libelle, font=("Arial",12)).pack(pady=5)
    entry = ctk.CTkEntry(parent, width=250, height=35,
                         placeholder_text=placheholder)
    if valeur is not None:
        entry.insert(0, minutes_vers_texte(valeur))
    entry.pack(pady=5)
    return entry

def creer_ligne_heure(parent, libelle: str, valeur: Optional[int]) -> ctk.CTkEntry:
    cadre = ctk.CTkFrame(parent, fg_color="transparent")
    cadre.pack(fill="x", padx=10, pady=5)
    ctk.CTkLabel(cadre, text=libelle, font=("Arial", 10), width=80).pack(side="left", padx=5)
    entry = ctk.CTkEntry(cadre, width=100, height=30, placeholder_text="HH:MM")
    if valeur is not None:
        entry.insert(0, minutes_vers_texte(valeur))
    entry.pack(side="left", padx=5)
    return entry

def creer_note_aide(parent) -> None:
    ctk.CTkLabel(
        parent, text="💡 Laissez vide pour aucune contrainte",
        font=("Arial", 10, "italic"), text_color="gray",
    ).pack(pady=10)

def creer_bouton_toolbar(parent, texte: str, commande, style: dict,
                         gras: bool = False) -> ctk.CTkButton:
    police = ("Arial", 12, "bold") if gras else ("Arial", 12)
    bouton = ctk.CTkButton(parent, text=texte, command=commande, height=50, font=police, **style)
    bouton.pack(side="left", padx=5)
    return bouton