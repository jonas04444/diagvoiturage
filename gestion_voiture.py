"""
TAB 5 - VERSION AMÉLIORÉE
- Voyages assignés non réutilisables
- Suppression de voyages d'un service
- Fenêtre plus grande (25%)
"""

import customtkinter as ctk
from tkinter import ttk, messagebox as msgbox, filedialog
from tabelauCSV import window_tableau_csv
from objet import voyage, service_agent
import csv
from timeline import TimelineVisuelle



class ServiceCard(ctk.CTkFrame):
    """Widget représentant un service"""

    def __init__(self, parent, service, on_delete=None, on_select=None, on_edit_constraints=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.service = service
        self.on_delete = on_delete
        self.on_select = on_select
        self.on_edit_constraints = on_edit_constraints  # ✅ NOUVEAU

        self.configure(fg_color="#2b2b2b", corner_radius=10)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        nom = f"Service {service.num_service} - {service.type_service.upper()}"
        label_nom = ctk.CTkLabel(header_frame, text=nom, font=("Arial", 14, "bold"))
        label_nom.pack(side="left")

        # ✅ NOUVEAU : Bouton éditer contraintes
        btn_constraints = ctk.CTkButton(
            header_frame, text="⏰", width=30, height=30,
            command=self._on_edit_constraints_click,
            fg_color="#FF9800", hover_color="#F57C00"
        )
        btn_constraints.pack(side="right", padx=5)

        btn_delete = ctk.CTkButton(
            header_frame, text="🗑️", width=30, height=30,
            command=self._on_delete_click,
            fg_color="#FF4444", hover_color="#CC0000"
        )
        btn_delete.pack(side="right", padx=5)

        btn_select = ctk.CTkButton(
            header_frame, text="✏️", width=30, height=30,
            command=self._on_select_click,
            fg_color="#4CAF50", hover_color="#388E3C"
        )
        btn_select.pack(side="right")

        nb_voyages = len(service.voyages)
        duree = service.duree_services()

        if nb_voyages > 0:
            debut = min(v.hdebut for v in service.voyages)
            fin = max(v.hfin for v in service.voyages)
            info_text = (f"📊 {nb_voyages} voyage(s) | ⏱️ {duree} min | "
                        f"🕐 {voyage.minutes_to_time(debut)} - {voyage.minutes_to_time(fin)}")
        else:
            info_text = "📊 Aucun voyage"

        # ✅ NOUVEAU : Afficher les contraintes horaires
        if hasattr(service, 'heure_debut_max') and hasattr(service, 'heure_fin_max'):
            if service.heure_debut_max and service.heure_fin_max:
                info_text += f"\n⏰ Contraintes : {voyage.minutes_to_time(service.heure_debut_max)} - {voyage.minutes_to_time(service.heure_fin_max)}"

        label_info = ctk.CTkLabel(main_frame, text=info_text, font=("Arial", 10))
        label_info.pack(anchor="w")

        self.timeline = TimelineVisuelle(main_frame, service, height=120)
        self.timeline.pack(fill="x", pady=(5, 0))

    def _on_delete_click(self):
        if self.on_delete:
            self.on_delete(self.service)

    def _on_select_click(self):
        if self.on_select:
            self.on_select(self.service)

    def _on_edit_constraints_click(self):
        """✅ NOUVEAU : Callback pour éditer les contraintes"""
        if self.on_edit_constraints:
            self.on_edit_constraints(self.service)

    def rafraichir(self):
        self.timeline.rafraichir()


class Tab5CreationManuelle(ctk.CTkFrame):
    """Frame pour le Tab 5 - Création manuelle de services"""

    def __init__(self, parent):
        super().__init__(parent)

        self.voyages_disponibles = []
        self.voyages_disponibles_tries = []  # ✅ NOUVEAU : Liste triée pour correspondre aux index du tableau
        self.services = []
        self.service_selectionne = None
        self.compteur_services = 0

        # ✅ NOUVEAU : Tracking des voyages assignés
        self.voyages_assignes = {}  # {id(voyage): service}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        self.creer_interface()

    def creer_interface(self):
        """Crée l'interface complète"""

        # ========== PANNEAU GAUCHE ==========
        panel_gauche = ctk.CTkFrame(self, width=500)  # ✅ 400 → 500
        panel_gauche.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        panel_gauche.grid_propagate(False)

        label_titre_gauche = ctk.CTkLabel(
            panel_gauche, text="📋 Voyages Disponibles",
            font=("Arial", 18, "bold")  # ✅ 16 → 18
        )
        label_titre_gauche.pack(pady=10)

        btn_charger = ctk.CTkButton(
            panel_gauche, text="📂 Charger voyages CSV",
            command=self.charger_voyages_csv, height=50  # ✅ 40 → 50
        )
        btn_charger.pack(pady=10, padx=10, fill="x")

        frame_liste_voyages = ctk.CTkFrame(panel_gauche)
        frame_liste_voyages.pack(fill="both", expand=True, padx=10, pady=10)

        colonnes = ('✓', 'Voy.', 'Ligne', 'Début', 'Fin', 'De→À')
        self.tree_voyages = ttk.Treeview(
            frame_liste_voyages, columns=colonnes,
            show='headings', height=25, selectmode='extended'  # ✅ 20 → 25
        )

        largeurs = {'✓': 35, 'Voy.': 60, 'Ligne': 70, 'Début': 70, 'Fin': 70, 'De→À': 120}
        for col, largeur in largeurs.items():
            self.tree_voyages.column(col, width=largeur, anchor='center')
            self.tree_voyages.heading(col, text=col)

        # ✅ NOUVEAU : Style pour les lignes désactivées
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.tree_voyages.tag_configure('disabled', foreground='#666666', background='#3a3a3a')

        scrollbar = ttk.Scrollbar(
            frame_liste_voyages, orient="vertical",
            command=self.tree_voyages.yview
        )
        self.tree_voyages.configure(yscrollcommand=scrollbar.set)

        self.tree_voyages.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree_voyages.bind('<Button-1>', self.toggle_voyage_selection)

        self.label_selection = ctk.CTkLabel(
            panel_gauche, text="0 voyage(s) sélectionné(s)",
            font=("Arial", 11)  # ✅ 10 → 11
        )
        self.label_selection.pack(pady=5)

        # ========== PANNEAU CENTRAL ==========
        panel_central = ctk.CTkFrame(self)
        panel_central.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        label_titre_central = ctk.CTkLabel(
            panel_central, text="🎯 Zone de Création",
            font=("Arial", 18, "bold")  # ✅ 16 → 18
        )
        label_titre_central.pack(pady=10)

        toolbar = ctk.CTkFrame(panel_central, height=70, fg_color="transparent")  # ✅ 60 → 70
        toolbar.pack(fill="x", padx=10, pady=10)

        btn_nouveau_service = ctk.CTkButton(
            toolbar, text="➕ Nouveau Service",
            command=self.creer_nouveau_service, height=50,  # ✅ 40 → 50
            fg_color="#4CAF50", hover_color="#388E3C",
            font=("Arial", 12)  # ✅ Ajout
        )
        btn_nouveau_service.pack(side="left", padx=5)

        self.combo_type_service = ctk.CTkComboBox(
            toolbar, values=["matin", "apres_midi"],
            width=180, height=50,  # ✅ 150x40 → 180x50
            font=("Arial", 12)
        )
        self.combo_type_service.set("matin")
        self.combo_type_service.pack(side="left", padx=5)

        btn_ajouter_voyages = ctk.CTkButton(
            toolbar, text="➡️ Ajouter au service",
            command=self.ajouter_voyages_au_service, height=50,
            fg_color="#2196F3", hover_color="#1976D2",
            font=("Arial", 12)
        )
        btn_ajouter_voyages.pack(side="left", padx=5)

        # ✅ NOUVEAU : Bouton compléter avec le solveur
        btn_completer = ctk.CTkButton(
            toolbar, text="🤖 Compléter avec solveur",
            command=self.completer_avec_solveur, height=50,
            fg_color="#9C27B0", hover_color="#7B1FA2",
            font=("Arial", 12, "bold")
        )
        btn_completer.pack(side="left", padx=5)

        self.label_service_actif = ctk.CTkLabel(
            toolbar, text="Aucun service sélectionné",
            font=("Arial", 12, "italic")
        )
        self.label_service_actif.pack(side="left", padx=20)

        self.scrollable_zone_travail = ctk.CTkScrollableFrame(
            panel_central, label_text="Services créés",
            label_font=("Arial", 14)
        )
        self.scrollable_zone_travail.pack(fill="both", expand=True, padx=10, pady=10)

        # ========== PANNEAU DROIT ==========
        panel_droit = ctk.CTkFrame(self, width=440)  # ✅ 350 → 440
        panel_droit.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        panel_droit.grid_propagate(False)

        label_titre_droit = ctk.CTkLabel(
            panel_droit, text="📝 Détails du Service",
            font=("Arial", 18, "bold")  # ✅ 16 → 18
        )
        label_titre_droit.pack(pady=10)

        self.frame_details = ctk.CTkScrollableFrame(panel_droit)
        self.frame_details.pack(fill="both", expand=True, padx=10, pady=10)

        self.label_details = ctk.CTkLabel(
            self.frame_details,
            text="Sélectionnez un service\npour voir les détails",
            font=("Arial", 11), justify="left"  # ✅ 10 → 11
        )
        self.label_details.pack(pady=20)

        # ✅ NOUVEAU : Zone pour la liste des voyages avec boutons supprimer
        self.frame_voyages_liste = ctk.CTkFrame(self.frame_details, fg_color="transparent")
        self.frame_voyages_liste.pack(fill="both", expand=True, pady=10)

        frame_actions = ctk.CTkFrame(panel_droit, fg_color="transparent")
        frame_actions.pack(fill="x", padx=10, pady=10)

        btn_exporter = ctk.CTkButton(
            frame_actions, text="💾 Exporter Planning",
            command=self.exporter_planning, height=50,  # ✅ 40 → 50
            font=("Arial", 12)
        )
        btn_exporter.pack(fill="x", pady=5)

        btn_valider = ctk.CTkButton(
            frame_actions, text="✅ Valider Planning",
            command=self.valider_planning, height=50,  # ✅ 40 → 50
            fg_color="#4CAF50", hover_color="#388E3C",
            font=("Arial", 12)
        )
        btn_valider.pack(fill="x", pady=5)

    def charger_voyages_csv(self):
        def callback_chargement(objets_voyages, matrice_donnees):
            self.voyages_disponibles = objets_voyages
            self.voyages_assignes.clear()  # ✅ Réinitialiser les assignations
            self.remplir_liste_voyages()
            msgbox.showinfo("Succès", f"{len(objets_voyages)} voyage(s) chargé(s)")

        window_tableau_csv(callback=callback_chargement)

    def remplir_liste_voyages(self):
        """Remplit le tableau avec les voyages disponibles"""
        for item in self.tree_voyages.get_children():
            self.tree_voyages.delete(item)

        for idx, v in enumerate(sorted(self.voyages_disponibles, key=lambda x: x.hdebut)):
            h_debut = voyage.minutes_to_time(v.hdebut)
            h_fin = voyage.minutes_to_time(v.hfin)
            trajet = f"{v.arret_debut[:3]}→{v.arret_fin[:3]}"

            # ✅ NOUVEAU : Vérifier si le voyage est déjà assigné
            voyage_id = id(v)
            if voyage_id in self.voyages_assignes:
                checkbox = '🔒'  # Cadenas pour voyage assigné
                tags = ('disabled',)
            else:
                checkbox = '☐'
                tags = ()

            # ✅ CORRECTION : Stocker l'index du voyage dans les tags pour le retrouver
            self.tree_voyages.insert(
                '', 'end',
                values=(checkbox, v.num_voyage, v.num_ligne, h_debut, h_fin, trajet),
                tags=tags + (f'idx_{idx}',)  # ← Ajouter l'index dans les tags
            )

        # ✅ NOUVEAU : Stocker la liste triée pour correspondre aux index
        self.voyages_disponibles_tries = sorted(self.voyages_disponibles, key=lambda x: x.hdebut)

    def toggle_voyage_selection(self, event):
        """Gère le clic sur la case à cocher des voyages"""
        item = self.tree_voyages.identify('item', event.x, event.y)
        column = self.tree_voyages.identify_column(event.x)

        if column == '#1' and item:
            values = list(self.tree_voyages.item(item, 'values'))

            # ✅ NOUVEAU : Empêcher la sélection des voyages assignés
            if values[0] == '🔒':
                msgbox.showwarning(
                    "Voyage déjà assigné",
                    "Ce voyage est déjà dans un service.\n"
                    "Supprimez-le d'abord du service pour le réassigner."
                )
                return

            # Toggle normal
            values[0] = '☑' if values[0] == '☐' else '☐'
            self.tree_voyages.item(item, values=values)

            nb_selectionnes = sum(
                1 for item in self.tree_voyages.get_children()
                if self.tree_voyages.item(item, 'values')[0] == '☑'
            )
            self.label_selection.configure(text=f"{nb_selectionnes} voyage(s) sélectionné(s)")

    def creer_nouveau_service(self):
        """✅ HYBRIDE : Crée un service avec contraintes horaires"""
        # Dialogue pour les contraintes
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nouveau Service")
        dialog.geometry("450x500")  # ✅ Plus grand
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="⚙️ Configuration du service", font=("Arial", 16, "bold")).pack(pady=15)

        frame_config = ctk.CTkFrame(dialog)
        frame_config.pack(padx=20, pady=10)  # ✅ CORRECTION : enlever fill et expand

        # Type de service
        ctk.CTkLabel(frame_config, text="Type de service :", font=("Arial", 12)).pack(pady=5)
        combo_type = ctk.CTkComboBox(frame_config, values=["matin", "apres_midi"], width=250, height=35)
        combo_type.set(self.combo_type_service.get())
        combo_type.pack(pady=5)

        # Heure de début max
        ctk.CTkLabel(frame_config, text="⏰ Heure de début max (HH:MM) :", font=("Arial", 12)).pack(pady=5)
        entry_debut = ctk.CTkEntry(frame_config, width=250, height=35, placeholder_text="Ex: 04:00")
        entry_debut.pack(pady=5)

        # Heure de fin max
        ctk.CTkLabel(frame_config, text="⏰ Heure de fin max (HH:MM) :", font=("Arial", 12)).pack(pady=5)
        entry_fin = ctk.CTkEntry(frame_config, width=250, height=35, placeholder_text="Ex: 14:00")
        entry_fin.pack(pady=5)

        ctk.CTkLabel(
            frame_config,
            text="💡 Laissez vide pour aucune contrainte",
            font=("Arial", 10, "italic"),
            text_color="gray"
        ).pack(pady=10)

        def valider():
            self.compteur_services += 1
            type_service = combo_type.get()

            nouveau_service = service_agent(
                num_service=self.compteur_services,
                type_service=type_service
            )

            # ✅ NOUVEAU : Ajouter les contraintes horaires
            try:
                if entry_debut.get():
                    parts = entry_debut.get().replace('h', ':').split(':')
                    h, m = int(parts[0]), int(parts[1])
                    nouveau_service.heure_debut_max = h * 60 + m
                else:
                    nouveau_service.heure_debut_max = None

                if entry_fin.get():
                    parts = entry_fin.get().replace('h', ':').split(':')
                    h, m = int(parts[0]), int(parts[1])
                    nouveau_service.heure_fin_max = h * 60 + m
                else:
                    nouveau_service.heure_fin_max = None
            except:
                msgbox.showerror("Erreur", "Format d'heure invalide\nUtilisez HH:MM (ex: 14:30)")
                return

            self.services.append(nouveau_service)

            card = ServiceCard(
                self.scrollable_zone_travail, nouveau_service,
                on_delete=self.supprimer_service,
                on_select=self.selectionner_service,
                on_edit_constraints=self.editer_contraintes
            )
            card.pack(fill="x", pady=5)

            self.selectionner_service(nouveau_service)
            dialog.destroy()
            msgbox.showinfo("Succès", f"Service {nouveau_service.num_service} créé")

        # ✅ CORRECTION : Bouton dans le dialog principal, pas dans frame_config
        btn_valider = ctk.CTkButton(
            dialog, text="✅ Créer le service",
            command=valider, height=50,
            width=300,
            fg_color="#4CAF50", hover_color="#388E3C",
            font=("Arial", 14, "bold")
        )
        btn_valider.pack(pady=30)

    def ajouter_voyages_au_service(self):
        """Ajoute les voyages sélectionnés au service actif"""
        if not self.service_selectionne:
            msgbox.showwarning("Attention", "Veuillez sélectionner un service d'abord")
            return

        voyages_a_ajouter = []
        items_a_desactiver = []
        voyages_deja_dans_service = []

        for item in self.tree_voyages.get_children():
            values = self.tree_voyages.item(item, 'values')
            if values[0] == '☑':
                # ✅ CORRECTION : Récupérer l'index depuis les tags
                tags = self.tree_voyages.item(item, 'tags')
                idx = None
                for tag in tags:
                    if tag.startswith('idx_'):
                        idx = int(tag.split('_')[1])
                        break

                if idx is None:
                    print(f"⚠️ Impossible de trouver l'index pour le voyage {values[1]}")
                    continue

                # ✅ CORRECTION : Utiliser l'index pour récupérer le bon voyage
                v = self.voyages_disponibles_tries[idx]

                print(f"🔍 Sélectionné : idx={idx}, V{v.num_voyage} {v.num_ligne} {voyage.minutes_to_time(v.hdebut)}-{voyage.minutes_to_time(v.hfin)} {v.arret_debut}→{v.arret_fin}")

                # Vérifier si déjà dans le service
                if v in self.service_selectionne.voyages:
                    voyages_deja_dans_service.append(v)
                else:
                    voyages_a_ajouter.append(v)
                    items_a_desactiver.append(item)

        # ✅ NOUVEAU : Avertir si des voyages sont déjà dans le service
        if voyages_deja_dans_service:
            noms = ", ".join([f"V{v.num_voyage}" for v in voyages_deja_dans_service])
            msgbox.showwarning(
                "Doublons détectés",
                f"Les voyages suivants sont déjà dans ce service :\n{noms}\n\nIls ne seront pas ajoutés à nouveau."
            )

        if not voyages_a_ajouter:
            if voyages_deja_dans_service:
                msgbox.showinfo("Info", "Aucun nouveau voyage à ajouter")
            else:
                msgbox.showwarning("Attention", "Aucun voyage sélectionné")
            return

        # Ajouter les voyages au service
        for v in voyages_a_ajouter:
            self.service_selectionne.ajout_voyages(v)
            # ✅ Marquer comme assigné
            self.voyages_assignes[id(v)] = self.service_selectionne

        # ✅ NOUVEAU : Désactiver les lignes dans le tableau
        for item in items_a_desactiver:
            values = list(self.tree_voyages.item(item, 'values'))
            values[0] = '🔒'
            self.tree_voyages.item(item, values=values, tags=('disabled',))

        # Réinitialiser le compteur
        self.label_selection.configure(text="0 voyage(s) sélectionné(s)")

        # Rafraîchir l'affichage
        self.rafraichir_services()
        self.afficher_details_service(self.service_selectionne)

        msgbox.showinfo(
            "Succès",
            f"{len(voyages_a_ajouter)} voyage(s) ajouté(s)"
        )

    def selectionner_service(self, service):
        self.service_selectionne = service
        self.label_service_actif.configure(
            text=f"Service actif : Service {service.num_service} ({service.type_service})"
        )
        self.afficher_details_service(service)

    def supprimer_service(self, service):
        """Supprime un service et libère ses voyages"""
        if msgbox.askyesno("Confirmation", f"Supprimer le service {service.num_service} ?"):
            # ✅ NOUVEAU : Libérer les voyages du service
            for v in service.voyages:
                voyage_id = id(v)
                if voyage_id in self.voyages_assignes:
                    del self.voyages_assignes[voyage_id]

            self.services.remove(service)

            if self.service_selectionne == service:
                self.service_selectionne = None
                self.label_service_actif.configure(text="Aucun service sélectionné")

            # Rafraîchir la liste des voyages
            self.remplir_liste_voyages()
            self.rafraichir_services()
            msgbox.showinfo("Succès", "Service supprimé")

    def supprimer_voyage_du_service(self, voyage_obj):
        """✅ NOUVEAU : Supprime un voyage du service sélectionné"""
        if not self.service_selectionne:
            return

        if msgbox.askyesno(
            "Confirmation",
            f"Retirer le voyage {voyage_obj.num_voyage} du service {self.service_selectionne.num_service} ?"
        ):
            # Retirer le voyage du service
            self.service_selectionne.voyages.remove(voyage_obj)

            # Libérer le voyage
            voyage_id = id(voyage_obj)
            if voyage_id in self.voyages_assignes:
                del self.voyages_assignes[voyage_id]

            # Rafraîchir tout
            self.remplir_liste_voyages()
            self.rafraichir_services()
            self.afficher_details_service(self.service_selectionne)

            msgbox.showinfo("Succès", f"Voyage {voyage_obj.num_voyage} retiré")

    def rafraichir_services(self):
        for widget in self.scrollable_zone_travail.winfo_children():
            widget.destroy()

        for service in self.services:
            card = ServiceCard(
                self.scrollable_zone_travail, service,
                on_delete=self.supprimer_service,
                on_select=self.selectionner_service,
                on_edit_constraints=self.editer_contraintes  # ✅ NOUVEAU
            )
            card.pack(fill="x", pady=5)

    def afficher_details_service(self, service):
        """Affiche les détails d'un service avec boutons de suppression"""
        # Nettoyer la zone de détails
        for widget in self.frame_voyages_liste.winfo_children():
            widget.destroy()

        details = f"🏷️ SERVICE {service.num_service}\n"
        details += f"📋 Type : {service.type_service.upper()}\n"
        details += f"📊 Voyages : {len(service.voyages)}\n"

        if service.voyages:
            duree = service.duree_services()
            debut = min(v.hdebut for v in service.voyages)
            fin = max(v.hfin for v in service.voyages)

            details += f"⏱️ Durée : {duree} minutes\n"
            details += f"🕐 Période : {voyage.minutes_to_time(debut)} - {voyage.minutes_to_time(fin)}\n"

        self.label_details.configure(text=details)

        # ✅ NOUVEAU : Section contraintes horaires modifiables
        frame_contraintes = ctk.CTkFrame(self.frame_voyages_liste, fg_color="#1a1a1a", corner_radius=10)
        frame_contraintes.pack(fill="x", pady=10, padx=5)

        ctk.CTkLabel(
            frame_contraintes,
            text="⏰ CONTRAINTES HORAIRES",
            font=("Arial", 12, "bold")
        ).pack(pady=10)

        # Heure de début
        frame_debut = ctk.CTkFrame(frame_contraintes, fg_color="transparent")
        frame_debut.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(frame_debut, text="Début max:", font=("Arial", 10), width=80).pack(side="left", padx=5)
        entry_debut = ctk.CTkEntry(frame_debut, width=100, height=30, placeholder_text="HH:MM")
        if hasattr(service, 'heure_debut_max') and service.heure_debut_max:
            h = service.heure_debut_max // 60
            m = service.heure_debut_max % 60
            entry_debut.insert(0, f"{h:02d}:{m:02d}")
        entry_debut.pack(side="left", padx=5)

        # Heure de fin
        frame_fin = ctk.CTkFrame(frame_contraintes, fg_color="transparent")
        frame_fin.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(frame_fin, text="Fin max:", font=("Arial", 10), width=80).pack(side="left", padx=5)
        entry_fin = ctk.CTkEntry(frame_fin, width=100, height=30, placeholder_text="HH:MM")
        if hasattr(service, 'heure_fin_max') and service.heure_fin_max:
            h = service.heure_fin_max // 60
            m = service.heure_fin_max % 60
            entry_fin.insert(0, f"{h:02d}:{m:02d}")
        entry_fin.pack(side="left", padx=5)

        # Bouton sauvegarder
        def sauvegarder_contraintes():
            try:
                if entry_debut.get():
                    parts = entry_debut.get().replace('h', ':').split(':')
                    service.heure_debut_max = int(parts[0]) * 60 + int(parts[1])
                else:
                    service.heure_debut_max = None

                if entry_fin.get():
                    parts = entry_fin.get().replace('h', ':').split(':')
                    service.heure_fin_max = int(parts[0]) * 60 + int(parts[1])
                else:
                    service.heure_fin_max = None

                self.rafraichir_services()
                msgbox.showinfo("✅", "Contraintes mises à jour")
            except:
                msgbox.showerror("Erreur", "Format invalide (utilisez HH:MM)")

        btn_sauvegarder = ctk.CTkButton(
            frame_contraintes,
            text="💾 Sauvegarder",
            command=sauvegarder_contraintes,
            width=150,
            height=35,
            fg_color="#4CAF50",
            hover_color="#388E3C"
        )
        btn_sauvegarder.pack(pady=10)

        # Séparateur
        ctk.CTkLabel(
            self.frame_voyages_liste,
            text="─" * 40 + "\n📝 LISTE DES VOYAGES",
            font=("Arial", 11, "bold")
        ).pack(pady=10)

        # Liste des voyages
        if service.voyages:
            for v in sorted(service.voyages, key=lambda x: x.hdebut):
                frame_voyage = ctk.CTkFrame(self.frame_voyages_liste, fg_color="#2b2b2b", corner_radius=5)
                frame_voyage.pack(fill="x", pady=3, padx=5)

                h_d = voyage.minutes_to_time(v.hdebut)
                h_f = voyage.minutes_to_time(v.hfin)

                # Info du voyage
                info_text = f"V{v.num_voyage} | {v.num_ligne} | {h_d}-{h_f}\n{v.arret_debut} → {v.arret_fin}"
                label_voyage = ctk.CTkLabel(
                    frame_voyage,
                    text=info_text,
                    font=("Arial", 10),
                    justify="left"
                )
                label_voyage.pack(side="left", padx=10, pady=5)

                # Bouton supprimer
                btn_supprimer = ctk.CTkButton(
                    frame_voyage,
                    text="❌",
                    width=30,
                    height=30,
                    command=lambda voyage_obj=v: self.supprimer_voyage_du_service(voyage_obj),
                    fg_color="#FF4444",
                    hover_color="#CC0000"
                )
                btn_supprimer.pack(side="right", padx=5, pady=5)
        else:
            ctk.CTkLabel(
                self.frame_voyages_liste,
                text="⚠️ Service vide",
                font=("Arial", 10, "italic"),
                text_color="gray"
            ).pack(pady=20)

    def editer_contraintes(self, service):
        """✅ HYBRIDE : Éditer les contraintes horaires d'un service"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Contraintes - Service {service.num_service}")
        dialog.geometry("450x350")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=f"⏰ Service {service.num_service}",
            font=("Arial", 16, "bold")
        ).pack(pady=15)

        frame_config = ctk.CTkFrame(dialog)
        frame_config.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(frame_config, text="Heure de début max (HH:MM) :", font=("Arial", 12)).pack(pady=5)
        entry_debut = ctk.CTkEntry(frame_config, width=250, height=35)
        if hasattr(service, 'heure_debut_max') and service.heure_debut_max:
            h = service.heure_debut_max // 60
            m = service.heure_debut_max % 60
            entry_debut.insert(0, f"{h:02d}:{m:02d}")
        entry_debut.pack(pady=5)

        ctk.CTkLabel(frame_config, text="Heure de fin max (HH:MM) :", font=("Arial", 12)).pack(pady=5)
        entry_fin = ctk.CTkEntry(frame_config, width=250, height=35)
        if hasattr(service, 'heure_fin_max') and service.heure_fin_max:
            h = service.heure_fin_max // 60
            m = service.heure_fin_max % 60
            entry_fin.insert(0, f"{h:02d}:{m:02d}")
        entry_fin.pack(pady=5)

        ctk.CTkLabel(
            frame_config,
            text="💡 Laissez vide pour aucune contrainte",
            font=("Arial", 10, "italic"),
            text_color="gray"
        ).pack(pady=10)

        def valider():
            try:
                if entry_debut.get():
                    parts = entry_debut.get().replace('h', ':').split(':')
                    service.heure_debut_max = int(parts[0]) * 60 + int(parts[1])
                else:
                    service.heure_debut_max = None

                if entry_fin.get():
                    parts = entry_fin.get().replace('h', ':').split(':')
                    service.heure_fin_max = int(parts[0]) * 60 + int(parts[1])
                else:
                    service.heure_fin_max = None

                self.rafraichir_services()
                dialog.destroy()
                msgbox.showinfo("Succès", "Contraintes mises à jour")
            except:
                msgbox.showerror("Erreur", "Format invalide (utilisez HH:MM)")

        ctk.CTkButton(
            dialog, text="✅ Valider",
            command=valider, height=40,
            fg_color="#4CAF50", hover_color="#388E3C"
        ).pack(pady=20)

    def completer_avec_solveur(self):
        """✅ HYBRIDE : Complète les services existants avec les voyages non assignés"""

        if not self.services:
            msgbox.showwarning("Attention", "Créez d'abord au moins un service")
            return

        # Récupérer les voyages non assignés
        voyages_non_assignes = [
            v for v in self.voyages_disponibles
            if id(v) not in self.voyages_assignes
        ]

        if not voyages_non_assignes:
            msgbox.showinfo("Info", "Tous les voyages sont déjà assignés !")
            return

        # Dialogue de configuration
        dialog = ctk.CTkToplevel(self)
        dialog.title("Complétion automatique")
        dialog.geometry("500x450")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="🤖 Complétion automatique",
            font=("Arial", 18, "bold")
        ).pack(pady=15)

        info_text = f"📊 Services existants : {len(self.services)}\n"
        info_text += f"📋 Voyages non assignés : {len(voyages_non_assignes)}\n\n"
        info_text += "Le solveur va essayer d'ajouter les voyages\n"
        info_text += "dans vos services en respectant :\n"
        info_text += "  ✓ Les contraintes horaires\n"
        info_text += "  ✓ Le battement minimum\n"
        info_text += "  ✓ La compatibilité des arrêts"

        ctk.CTkLabel(dialog, text=info_text, font=("Arial", 12), justify="left").pack(pady=10)

        frame_config = ctk.CTkFrame(dialog)
        frame_config.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(frame_config, text="⏱️ Battement minimum (min) :").pack(pady=5)
        entry_battement = ctk.CTkEntry(frame_config, width=200)
        entry_battement.insert(0, "5")
        entry_battement.pack(pady=5)

        ctk.CTkLabel(frame_config, text="🚏 Vérifier les arrêts :").pack(pady=5)
        check_arrets = ctk.CTkCheckBox(frame_config, text="Activer (recommandé)")
        check_arrets.select()
        check_arrets.pack(pady=5)

        def lancer():
            try:
                battement = int(entry_battement.get())
                verifier = check_arrets.get() == 1
                dialog.destroy()
                self._executer_completion(voyages_non_assignes, battement, verifier)
            except:
                msgbox.showerror("Erreur", "Valeur invalide")

        ctk.CTkButton(
            dialog, text="🚀 Lancer la complétion",
            command=lancer, height=50,
            fg_color="#4CAF50", hover_color="#388E3C",
            font=("Arial", 14, "bold")
        ).pack(pady=20)

    def _executer_completion(self, voyages_non_assignes, battement_min, verifier_arrets):
        """Exécute la complétion avec le solveur"""

        print("\n" + "="*70)
        print("🤖 COMPLÉTION AUTOMATIQUE")
        print("="*70)

        try:
            from test.entrainementsolveria import voyages_compatibles
        except ImportError:
            msgbox.showerror("Erreur", "Module entrainementsolveria non trouvé")
            return

        nb_voyages_ajoutes = 0
        voyages_restants = list(voyages_non_assignes)

        # Pour chaque service
        for service in self.services:
            print(f"\n📋 Service {service.num_service} ({service.type_service})...")

            h_debut = getattr(service, 'heure_debut_max', None)
            h_fin = getattr(service, 'heure_fin_max', None)

            if h_debut and h_fin:
                print(f"   ⏰ Contraintes : {voyage.minutes_to_time(h_debut)} - {voyage.minutes_to_time(h_fin)}")

            voyages_service = list(service.voyages)

            for v in sorted(voyages_restants, key=lambda x: x.hdebut):
                # Vérifier contraintes horaires
                if h_debut and h_fin:
                    if v.hdebut < h_debut or v.hfin > h_fin:
                        continue

                # Vérifier compatibilité
                compatible = True

                for v_exist in voyages_service:
                    if not (v.hfin <= v_exist.hdebut or v.hdebut >= v_exist.hfin):
                        compatible = False
                        break

                    if v.hfin <= v_exist.hdebut:
                        if not voyages_compatibles(v, v_exist, voyages_service, battement_min, 50, verifier_arrets):
                            compatible = False
                            break
                    elif v_exist.hfin <= v.hdebut:
                        if not voyages_compatibles(v_exist, v, voyages_service, battement_min, 50, verifier_arrets):
                            compatible = False
                            break

                if compatible:
                    service.ajout_voyages(v)
                    self.voyages_assignes[id(v)] = service
                    voyages_service.append(v)
                    voyages_restants.remove(v)
                    nb_voyages_ajoutes += 1

                    print(f"   ✅ V{v.num_voyage} ajouté ({voyage.minutes_to_time(v.hdebut)}-{voyage.minutes_to_time(v.hfin)})")

        # Rafraîchir
        self.remplir_liste_voyages()
        self.rafraichir_services()
        if self.service_selectionne:
            self.afficher_details_service(self.service_selectionne)

        print(f"\n✅ Total : {nb_voyages_ajoutes} voyage(s) ajouté(s)")
        print(f"⚠️ Restants : {len(voyages_restants)} voyage(s)")
        print("="*70 + "\n")

        if voyages_restants:
            msg = f"✅ {nb_voyages_ajoutes} voyage(s) ajouté(s)\n\n"
            msg += f"⚠️ {len(voyages_restants)} voyage(s) n'ont pas pu être assignés\n"
            msg += "(hors contraintes ou incompatibles)"
        else:
            msg = f"✅ Complétion réussie !\n\n{nb_voyages_ajoutes} voyage(s) ajouté(s)"

        msgbox.showinfo("Résultat", msg)

    def valider_planning(self):
        if not self.services:
            msgbox.showwarning("Attention", "Aucun service créé")
            return

        services_vides = [s for s in self.services if not s.voyages]
        if services_vides:
            msg = f"{len(services_vides)} service(s) vide(s). Continuer ?"
            if not msgbox.askyesno("Attention", msg):
                return

        nb_services = len(self.services)
        nb_voyages_total = sum(len(s.voyages) for s in self.services)

        msg = f"✅ Planning validé !\n\n"
        msg += f"Services créés : {nb_services}\n"
        msg += f"Voyages assignés : {nb_voyages_total}\n"

        msgbox.showinfo("Validation", msg)

    def exporter_planning(self):
        if not self.services:
            msgbox.showwarning("Attention", "Aucun service à exporter")
            return

        fichier = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if fichier:
            try:
                with open(fichier, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Service', 'Type', 'Voyage', 'Ligne', 'Debut', 'Fin', 'De', 'A'])

                    for service in self.services:
                        for v in sorted(service.voyages, key=lambda x: x.hdebut):
                            writer.writerow([
                                service.num_service,
                                service.type_service,
                                v.num_voyage,
                                v.num_ligne,
                                voyage.minutes_to_time(v.hdebut),
                                voyage.minutes_to_time(v.hfin),
                                v.arret_debut,
                                v.arret_fin
                            ])

                msgbox.showinfo("Succès", f"Planning exporté vers :\n{fichier}")
            except Exception as e:
                msgbox.showerror("Erreur", f"Erreur lors de l'export : {e}")


# ================== TEST STANDALONE ==================
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Test Tab 5 - Version Améliorée")
    app.geometry("2000x1125")  # ✅ 1600x900 → 2000x1125 (+25%)

    tab5 = Tab5CreationManuelle(app)
    tab5.pack(fill="both", expand=True)

    app.mainloop()