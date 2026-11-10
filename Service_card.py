import customtkinter as ctk

from outils_horaires import minutes_vers_texte, texte_contraintes
from timelineclean import TimelineVisuelle

from Widgets_communs import STYLE_ORANGE, STYLE_ROUGE, STYLE_VERT

class ServiceCard(ctk.CTkFrame):
    def __init__(self, parent, service, on_delete=None, on_select=None,
                 o_edit_contraints=None, **kwargs):
        super().__init__(parent, fg_color='#2b2b2b', corner_radius=10, **kwargs)
        self.service = service
        self.on_delete = on_delete
        self.on_select = on_select
        self.o_edit_contraints = o_edit_contraints

        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.pack(fill="both", expand=True, padx=10, pady=10)

        self._creer_entete(cadre)
        ctk.CTkLabel(cadre, text=self._texte_info(), font=("Arial", 10)).pack(anchor="w")

        self.timeline = TimelineVisuelle(cadre, service, height=120)
        self.timeline.pack(fill="x", pady=(5, 0))

    def _creer_entete(self, parent) -> None:
        """Crée le titre et les trois boutons d'action."""
        entete = ctk.CTkFrame(parent, fg_color="transparent")
        entete.pack(fill="x", pady=(0, 10))

        titre = f"Service {self.service.num_service} - {self.service.type_service.upper()}"
        ctk.CTkLabel(entete, text=titre, font=("Arial", 14, "bold")).pack(side="left")

        boutons = (
            ("⏰", self.on_edit_constraints, STYLE_ORANGE, 5),
            ("🗑️", self.on_delete, STYLE_ROUGE, 5),
            ("✏️", self.on_select, STYLE_VERT, 0),
        )
        for texte, callback, style, padx in boutons:
            ctk.CTkButton(
                entete, text=texte, width=30, height=30,
                command=lambda cb=callback: self._declencher(cb), **style,
            ).pack(side="right", padx=padx)

    def _declencher(self, callback) -> None:
        """Appelle le callback avec le service, s'il est défini."""
        if callback:
            callback(self.service)

    def _texte_info(self) -> str:
        """Construit le résumé (nombre de voyages, durée, période, contraintes)."""
        voyages = self.service.voyages
        if voyages:
            debut = min(v.hdebut for v in voyages)
            fin = max(v.hfin for v in voyages)
            texte = (
                f"📊 {len(voyages)} voyage(s) | ⏱️ {self.service.duree_services()} min | "
                f"🕐 {minutes_vers_texte(debut)} - {minutes_vers_texte(fin)}"
            )
        else:
            texte = "📊 Aucun voyage"
        return texte + texte_contraintes(self.service)

    def rafraichir(self) -> None:
        self.timeline.rafraichir()