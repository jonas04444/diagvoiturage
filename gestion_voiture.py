"""
TAB 5 - VERSION AMÉLIORÉE
- Voyages assignés non réutilisables
- Suppression de voyages d'un service
- Fenêtre plus grande (25%)
"""

import customtkinter as ctk
from tkinter import ttk, messagebox as msgbox, Canvas, filedialog
from tabelauCSV import window_tableau_csv
from objet import voyage, service_agent
import csv


class TimelineVisuelle(ctk.CTkFrame):
    """Widget de timeline pour visualiser un service"""

    def __init__(self, parent, service=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.service = service
        self.canvas = None
        self.largeur_minimale = 700  # ✅ AJOUT : Largeur minimale garantie
        self.creer_timeline()

    def creer_timeline(self):
        """Crée le canvas de la timeline"""
        self.canvas = Canvas(
            self,
            bg="#2b2b2b",
            height=150,  # ✅ AUGMENTÉ : 100 → 150 pour permettre plusieurs lignes
            width=self.largeur_minimale,  # ✅ AJOUT : Largeur initiale
            highlightthickness=1,
            highlightbackground="#555555"
        )
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)

        # ✅ CORRECTION : Redessiner après resize ET après un petit délai
        def redessiner_apres_configure(event):
            # Annuler le timer précédent s'il existe
            if hasattr(self, '_timer_redraw'):
                self.after_cancel(self._timer_redraw)
            # Redessiner après 100ms (pour éviter trop de redraws)
            self._timer_redraw = self.after(100, self.rafraichir)

        self.canvas.bind('<Configure>', redessiner_apres_configure)

        # Dessiner après que tout soit créé
        self.after(200, self._dessiner_initial)

    def _dessiner_initial(self):
        """Dessine la timeline après l'initialisation"""
        if self.service:
            self.dessiner_service()
        else:
            self.dessiner_vide()

    def dessiner_vide(self):
        """Dessine une timeline vide"""
        self.canvas.delete("all")

        self.canvas.update_idletasks()
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        # ✅ Protection : utiliser la largeur minimale si nécessaire
        if width < self.largeur_minimale:
            width = self.largeur_minimale
        if height < 50:
            height = 100

        for h in range(4, 25, 2):
            x = self._heure_vers_x(h * 60, width)
            self.canvas.create_line(x, 20, x, height - 10, fill="#444444", dash=(2, 2))
            self.canvas.create_text(x, 10, text=f"{h:02d}h", fill="white", font=("Arial", 8))

        self.canvas.create_text(
            width // 2, height // 2,
            text="Service vide - Ajoutez des voyages",
            fill="#888888", font=("Arial", 10, "italic")
        )

    def dessiner_service(self):
        """Dessine les voyages du service sur la timeline"""
        self.canvas.delete("all")

        # ✅ CORRECTION : Attendre que le canvas ait sa vraie taille
        self.canvas.update_idletasks()
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        # ✅ Protection : utiliser la largeur minimale si nécessaire
        if width < self.largeur_minimale:
            width = self.largeur_minimale
        if height < 50:
            height = 100

        # Debug
        print(f"\n🎨 Dessin timeline - Canvas: {width}x{height} px")

        for h in range(4, 25, 2):
            x = self._heure_vers_x(h * 60, width)
            self.canvas.create_line(x, 20, x, height - 10, fill="#444444", dash=(2, 2))
            self.canvas.create_text(x, 10, text=f"{h:02d}h", fill="white", font=("Arial", 8))

        if not self.service or not self.service.voyages:
            self.dessiner_vide()
            return

        print(f"📊 Service avec {len(self.service.voyages)} voyage(s)")

        # ✅ NOUVEAU : Organiser les voyages en lignes pour éviter les chevauchements
        voyages_tries = sorted(self.service.voyages, key=lambda x: x.hdebut)
        lignes_y = []  # Liste de listes de voyages par ligne Y

        for v in voyages_tries:
            # Trouver une ligne Y disponible (pas de chevauchement)
            ligne_trouvee = False
            for ligne in lignes_y:
                # Vérifier si ce voyage peut aller sur cette ligne
                chevauche = False
                for v_existant in ligne:
                    if not (v.hfin <= v_existant.hdebut or v.hdebut >= v_existant.hfin):
                        # Il y a chevauchement
                        chevauche = True
                        break

                if not chevauche:
                    ligne.append(v)
                    ligne_trouvee = True
                    break

            if not ligne_trouvee:
                # Créer une nouvelle ligne
                lignes_y.append([v])

        print(f"📐 Répartition sur {len(lignes_y)} ligne(s) verticale(s)")

        # Dessiner les voyages
        h_rect = 40  # Hauteur d'un rectangle
        espace_entre = 5  # Espace entre les lignes
        y_start = 25

        for idx_ligne, ligne in enumerate(lignes_y):
            y_rect = y_start + idx_ligne * (h_rect + espace_entre)

            for v in ligne:
                x1 = self._heure_vers_x(v.hdebut, width)
                x2 = self._heure_vers_x(v.hfin, width)

                # ✅ DEBUG : Afficher les coordonnées
                h_d = f"{v.hdebut//60:02d}h{v.hdebut%60:02d}"
                h_f = f"{v.hfin//60:02d}h{v.hfin%60:02d}"
                print(f"  L{idx_ligne+1} V{v.num_voyage}: {h_d}-{h_f} ({v.hdebut}-{v.hfin}min) → x1={x1:.1f}, x2={x2:.1f} y={y_rect}")

                color = self._get_color(v.num_ligne)
                self.canvas.create_rectangle(
                    x1, y_rect, x2, y_rect + h_rect,
                    fill=color, outline="white", width=2
                )

                mid_x = (x1 + x2) / 2
                mid_y = y_rect + h_rect / 2

                self.canvas.create_text(
                    mid_x, mid_y - 8,
                    text=f"V{v.num_voyage}",
                    fill="black", font=("Arial", 9, "bold")
                )

                self.canvas.create_text(
                    mid_x, mid_y + 8,
                    text=f"{v.arret_debut[:3]}→{v.arret_fin[:3]}",
                    fill="black", font=("Arial", 7)
                )

    def _heure_vers_x(self, minutes, width):
        debut = 4 * 60
        fin = 24 * 60
        ratio = (minutes - debut) / (fin - debut)
        return 50 + ratio * (width - 100)

    def _get_color(self, ligne):
        colors = {
            "A1": "#FF6B6B", "C00A1": "#FF6B6B",
            "25": "#4ECDC4", "C0025": "#4ECDC4",
            "35": "#45B7D1", "C0035": "#45B7D1",
            "43": "#FFA07A", "C0043": "#FFA07A",
            "83": "#98D8C8", "C0083": "#98D8C8",
            "86": "#F7DC6F", "C0086": "#F7DC6F",
        }
        return colors.get(ligne, "#CCCCCC")

    def rafraichir(self):
        if self.service:
            self.dessiner_service()
        else:
            self.dessiner_vide()


class ServiceCard(ctk.CTkFrame):
    """Widget représentant un service"""

    def __init__(self, parent, service, on_delete=None, on_select=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.service = service
        self.on_delete = on_delete
        self.on_select = on_select

        self.configure(fg_color="#2b2b2b", corner_radius=10)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        nom = f"Service {service.num_service} - {service.type_service.upper()}"
        label_nom = ctk.CTkLabel(header_frame, text=nom, font=("Arial", 14, "bold"))
        label_nom.pack(side="left")

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

        label_info = ctk.CTkLabel(main_frame, text=info_text, font=("Arial", 10))
        label_info.pack(anchor="w")

        self.timeline = TimelineVisuelle(main_frame, service, height=120)  # ✅ 80 → 120
        self.timeline.pack(fill="x", pady=(5, 0))

    def _on_delete_click(self):
        if self.on_delete:
            self.on_delete(self.service)

    def _on_select_click(self):
        if self.on_select:
            self.on_select(self.service)

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
            toolbar, text="➡️ Ajouter au service actif",
            command=self.ajouter_voyages_au_service, height=50,  # ✅ 40 → 50
            fg_color="#2196F3", hover_color="#1976D2",
            font=("Arial", 12)
        )
        btn_ajouter_voyages.pack(side="left", padx=5)

        self.label_service_actif = ctk.CTkLabel(
            toolbar, text="Aucun service sélectionné",
            font=("Arial", 12, "italic")  # ✅ 11 → 12
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
        self.compteur_services += 1
        type_service = self.combo_type_service.get()

        nouveau_service = service_agent(
            num_service=self.compteur_services,
            type_service=type_service
        )

        self.services.append(nouveau_service)

        card = ServiceCard(
            self.scrollable_zone_travail, nouveau_service,
            on_delete=self.supprimer_service,
            on_select=self.selectionner_service
        )
        card.pack(fill="x", pady=5)

        self.selectionner_service(nouveau_service)
        msgbox.showinfo("Succès", f"Service {nouveau_service.num_service} créé")

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
                on_select=self.selectionner_service
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
            details += f"🕐 Période : {voyage.minutes_to_time(debut)} - {voyage.minutes_to_time(fin)}\n\n"
            details += "📝 LISTE DES VOYAGES :\n" + "─" * 40 + "\n"

            self.label_details.configure(text=details)

            # ✅ NOUVEAU : Créer une ligne pour chaque voyage avec bouton supprimer
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
            details += "\n⚠️ Service vide\n"
            self.label_details.configure(text=details)

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