from logging import setLogRecordFactory

import customtkinter as ctk
from tkinter import ttk, messagebox as msgbox, Canvas, filedialog

from objet import voyage, service_agent, proposition
from tabelauCSV import window_tableau_csv


class TimeLineWisuelle(ctk.CTkFrame):
    def __init__(self, parent, service=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.service = service
        self.canvas = None
        self.largeur_minimale = 700
        self.creer_timeline()

    def creer_timeline(self):
        self.canvas = Canvas(
            self,
            bg="#2b2b2b",
            height=80,
            width=self.largeur_minimale,
            highlightthickness=1,
            highlightbackground="#555555"
        )
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)

        def redessiner_apres_configure(event):
            if hasattr(self, '_timer_redraw'):
                self.after_cancel(self._timer_redraw)
            self._timer_redraw = self.after(100, self.rafraichir)

        self.canvas.bind('<Configure>', redessiner_apres_configure)
        self.after(200, self._dessiner_initial)

    def _dessiner_initial(self):
        if self.service:
            self.dessiner_service()
        else:
            self.dessiner_vide()

    def dessiner_vide(self):
        self.canvas.delete("all")

        self.canvas.update_idletasks()
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

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
        self.canvas.delete("all")
        self.canvas.update_idletasks()
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width < self.largeur_minimale:
            width = self.largeur_minimale
        if height < 50:
            height = 100

        for h in range(4, 25, 2):
            x = self._heure_vers_x(h * 60, width)
            self.canvas.create_line(x, 20, x, height - 10, fill="#444444", dash=(2, 2))
            self.canvas.create_text(x, 10, text=f"{h:02d}h", fill="white", font=("Arial", 8))

        if not self.service or not self.service.voyages:
            self.dessiner_vide()
            return

        voyage_tries = sorted(self.service.voyages, key=lambda x: x.hdebut)
        lignes_y = []

        for v in voyage_tries:
            ligne_trouvee = False
            for ligne in lignes_y:
                chevauche = False
                for v_existant in ligne:
                    if not (v.hfin <= v_existant.hdebut or v.hdebut >= v_existant.hfin):
                        chevauche = True
                        break
                if not chevauche:
                    ligne.append(v)
                    ligne_trouvee = True
                    break
            if not ligne_trouvee:
                lignes_y.append([v])

        h_rect = 40
        espace_entre = 5
        y_start = 25

        for idx_ligne, ligne in enumerate(lignes_y):
            y_rect = y_start + idx_ligne * (h_rect + espace_entre)

            for v in ligne:
                x1 = self._heure_vers_x(v.hdebut, width)
                x2 = self._heure_vers_x(v.hfin, width)

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

    def rafraichir(self):
        if self.service:
            self.dessiner_service()
        else:
            self.dessiner_vide()

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


class Interface(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.voyages_disponibles = []
        self.voyages_selectionnes = {}
        self.services = []
        self.service_actif = None
        self.compteur_service = 1
        self.widgets_service = {}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        self.creer_interface()

    def creer_interface(self):
        # ═══════════════════════════════════════════════════════════════
        # PANNEAU GAUCHE - Voyages disponibles
        # ═══════════════════════════════════════════════════════════════
        panel_gauche = ctk.CTkFrame(self, width=500)
        panel_gauche.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        panel_gauche.grid_propagate(False)

        label_titre_gauche = ctk.CTkLabel(
            panel_gauche, text="Voyages Disponibles",
            font=("Arial", 18, "bold")
        )
        label_titre_gauche.pack(pady=10)

        btn_charger = ctk.CTkButton(
            panel_gauche, text="Charger voyages CSV",
            command=self.ouvrir_fenetre_csv, height=50
        )
        btn_charger.pack(pady=10, padx=10, fill="x")

        frame_liste_voyages = ctk.CTkFrame(panel_gauche)
        frame_liste_voyages.pack(fill="both", expand=True, padx=10, pady=10)

        colonnes = ('✓', 'Voy.', 'Ligne', 'Début', 'Fin', 'De→À')
        self.tree_voyages = ttk.Treeview(
            frame_liste_voyages, columns=colonnes,
            show="headings", height=25, selectmode="extended"
        )

        largeurs = {'✓': 35, 'Voy.': 60, 'Ligne': 70, 'Début': 70, 'Fin': 70, 'De→À': 120}
        for col, largeur in largeurs.items():
            self.tree_voyages.column(col, width=largeur, anchor="center")
            self.tree_voyages.heading(col, text=col)

        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.tree_voyages.tag_configure('disabled', foreground="#666666", background="#3a3a3a")

        scrollbar = ttk.Scrollbar(
            frame_liste_voyages, orient="vertical",
            command=self.tree_voyages.yview
        )
        self.tree_voyages.configure(yscrollcommand=scrollbar.set)
        self.tree_voyages.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree_voyages.bind('<Button-1>', self.toggle_voyage_selection)

        self.label_selection = ctk.CTkLabel(
            panel_gauche, text=" 0 voyages sélectionés",
            font=("Arial", 11, "bold")
        )
        self.label_selection.pack(pady=5)

        # ═══════════════════════════════════════════════════════════════
        # PANNEAU CENTRAL - Zone de création
        # ═══════════════════════════════════════════════════════════════
        panel_central = ctk.CTkFrame(self)
        panel_central.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        label_titre_central = ctk.CTkLabel(
            panel_central, text="Zone de création",
            font=("Arial", 18, "bold")
        )
        label_titre_central.pack(pady=10)

        toolbar = ctk.CTkFrame(panel_central, height=70, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=10)

        btn_nouveau_service = ctk.CTkButton(
            toolbar, text="Nouveau service",
            command=self.creer_nouveau_service, height=50,
            fg_color="#4CAF50", hover_color="#388E3C",
            font=("Arial", 12)
        )
        btn_nouveau_service.pack(side="left", padx=10)

        self.combo_type_service = ctk.CTkComboBox(
            toolbar, values=["matin", "après-midi", "coupé"],
            width=180, height=50,
            font=("Arial", 12)
        )
        self.combo_type_service.set("matin")
        self.combo_type_service.pack(side="left", padx=5, pady=5)

        btn_ajouter_voyage = ctk.CTkButton(
            toolbar, text="Ajouter au service",
            command=self.ajouter_voyages_au_service, height=50,
            fg_color="#2196F3", hover_color="#1976D2",
            font=("Arial", 12)
        )
        btn_ajouter_voyage.pack(side="left", padx=5)

        btn_completer = ctk.CTkButton(
            toolbar, text="Optimiser avec OR-Tools",
            command=self.completer_avec_ortools, height=50,
            fg_color="#9C27B0", hover_color="#7B1FA2",
            font=("Arial", 12, "bold")
        )
        btn_completer.pack(side="left", padx=5)

        self.label_selection_actif = ctk.CTkLabel(
            toolbar, text="Aucun service sélectionné",
            font=("Arial", 12, "italic")
        )
        self.label_selection_actif.pack(side="left", padx=20)

        self.scrollable_zone_travail = ctk.CTkScrollableFrame(
            panel_central, label_text="Service créés",
            label_font=("Arial", 14)
        )
        self.scrollable_zone_travail.pack(fill="both", expand=True, padx=10, pady=10)

        # ═══════════════════════════════════════════════════════════════
        # PANNEAU DROIT - Détails du service
        # ═══════════════════════════════════════════════════════════════
        panel_droit = ctk.CTkFrame(self, width=440)
        panel_droit.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        panel_droit.grid_propagate(False)

        label_titre_droit = ctk.CTkLabel(
            panel_droit, text="Détail du service",
            font=("Arial", 18, "bold")
        )
        label_titre_droit.pack(pady=10)

        self.frame_details = ctk.CTkScrollableFrame(panel_droit)
        self.frame_details.pack(fill="both", expand=True, padx=10, pady=10)

        # Info service
        self.label_details = ctk.CTkLabel(
            self.frame_details,
            text="Sélectionnez un service\npour voir les détails",
            font=("Arial", 11), justify="left"
        )
        self.label_details.pack(pady=10)

        # ═══════════════════════════════════════════════════════════════
        # SECTION HEURES LIMITES
        # ═══════════════════════════════════════════════════════════════
        frame_limites = ctk.CTkFrame(self.frame_details)
        frame_limites.pack(fill="x", pady=10, padx=5)

        ctk.CTkLabel(
            frame_limites,
            text="⏰ Heures limites du service",
            font=("Arial", 12, "bold")
        ).pack(pady=5)

        # === DÉBUT ===
        ctk.CTkLabel(frame_limites, text="Début:", anchor="w").pack(anchor="w", padx=10, pady=(5, 0))
        frame_debut = ctk.CTkFrame(frame_limites, fg_color="transparent")
        frame_debut.pack(fill="x", padx=10, pady=(0, 5))

        self.entry_heure_debut = ctk.CTkEntry(frame_debut, width=70, placeholder_text="HH")
        self.entry_heure_debut.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(frame_debut, text="h", width=20).pack(side="left")
        self.entry_min_debut = ctk.CTkEntry(frame_debut, width=70, placeholder_text="MM")
        self.entry_min_debut.pack(side="left", padx=(5, 0))

        # === FIN ===
        ctk.CTkLabel(frame_limites, text="Fin:", anchor="w").pack(anchor="w", padx=10, pady=(5, 0))
        frame_fin = ctk.CTkFrame(frame_limites, fg_color="transparent")
        frame_fin.pack(fill="x", padx=10, pady=(0, 5))

        self.entry_heure_fin = ctk.CTkEntry(frame_fin, width=70, placeholder_text="HH")
        self.entry_heure_fin.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(frame_fin, text="h", width=20).pack(side="left")
        self.entry_min_fin = ctk.CTkEntry(frame_fin, width=70, placeholder_text="MM")
        self.entry_min_fin.pack(side="left", padx=(5, 0))

        # ═══════════════════════════════════════════════════════════════
        # SECTION COUPURE
        # ═══════════════════════════════════════════════════════════════
        self.frame_coupure = ctk.CTkFrame(self.frame_details)
        # Ne pas pack ici - sera affiché dynamiquement

        ctk.CTkLabel(
            self.frame_coupure,
            text="✂️ Heures de coupure",
            font=("Arial", 12, "bold")
        ).pack(pady=5)

        # === DÉBUT COUPURE ===
        ctk.CTkLabel(self.frame_coupure, text="Début coupure:", anchor="w").pack(anchor="w", padx=10, pady=(5, 0))
        frame_debut_coup = ctk.CTkFrame(self.frame_coupure, fg_color="transparent")
        frame_debut_coup.pack(fill="x", padx=10, pady=(0, 5))

        self.entry_heure_debut_coupure = ctk.CTkEntry(frame_debut_coup, width=70, placeholder_text="HH")
        self.entry_heure_debut_coupure.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(frame_debut_coup, text="h", width=20).pack(side="left")
        self.entry_min_debut_coupure = ctk.CTkEntry(frame_debut_coup, width=70, placeholder_text="MM")
        self.entry_min_debut_coupure.pack(side="left", padx=(5, 0))

        # === FIN COUPURE ===
        ctk.CTkLabel(self.frame_coupure, text="Fin coupure:", anchor="w").pack(anchor="w", padx=10, pady=(5, 0))
        frame_fin_coup = ctk.CTkFrame(self.frame_coupure, fg_color="transparent")
        frame_fin_coup.pack(fill="x", padx=10, pady=(0, 5))

        self.entry_heure_fin_coupure = ctk.CTkEntry(frame_fin_coup, width=70, placeholder_text="HH")
        self.entry_heure_fin_coupure.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(frame_fin_coup, text="h", width=20).pack(side="left")
        self.entry_min_fin_coupure = ctk.CTkEntry(frame_fin_coup, width=70, placeholder_text="MM")
        self.entry_min_fin_coupure.pack(side="left", padx=(5, 0))

        # Label durée coupure
        self.label_duree_coupure = ctk.CTkLabel(
            self.frame_coupure,
            text="Durée coupure: --",
            font=("Arial", 10, "italic"),
            text_color="#888888"
        )
        self.label_duree_coupure.pack(pady=5)

        # ═══════════════════════════════════════════════════════════════
        # BOUTON APPLIQUER
        # ═══════════════════════════════════════════════════════════════
        self.frame_bouton_limites = ctk.CTkFrame(self.frame_details, fg_color="transparent")
        self.frame_bouton_limites.pack(fill="x", pady=10)

        self.btn_appliquer_limites = ctk.CTkButton(
            self.frame_bouton_limites,
            text="✅ Appliquer les limites",
            command=self.appliquer_limites_service,
            height=40,
            fg_color="#FF9800",
            hover_color="#F57C00",
            font=("Arial", 12, "bold")
        )
        self.btn_appliquer_limites.pack(pady=5)

        self.label_limites_actuelles = ctk.CTkLabel(
            self.frame_bouton_limites,
            text="Limites: Non définies",
            font=("Arial", 10, "italic"),
            text_color="#888888"
        )
        self.label_limites_actuelles.pack(pady=5)

        # ═══════════════════════════════════════════════════════════════
        # LISTE DES VOYAGES
        # ═══════════════════════════════════════════════════════════════
        self.frame_section_voyages = ctk.CTkFrame(self.frame_details, fg_color="transparent")
        self.frame_section_voyages.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(
            self.frame_section_voyages,
            text="📋 Voyages du service",
            font=("Arial", 12, "bold")
        ).pack(pady=5)

        self.frame_voyages_liste = ctk.CTkFrame(self.frame_section_voyages, fg_color="transparent")
        self.frame_voyages_liste.pack(fill="both", expand=True, pady=5)

        # ═══════════════════════════════════════════════════════════════
        # BOUTONS D'ACTION
        # ═══════════════════════════════════════════════════════════════
        frame_actions = ctk.CTkFrame(panel_droit, fg_color="transparent")
        frame_actions.pack(fill="x", padx=10, pady=10)

        btn_exporter = ctk.CTkButton(
            frame_actions, text="Exporter",
            command=self.exporter_planning, height=50,
            font=("Arial", 12)
        )
        btn_exporter.pack(fill="x", pady=10)

        btn_valider = ctk.CTkButton(
            frame_actions, text="✅ Valider Planning",
            command=self.valider_planning, height=50,
            fg_color="#4CAF50", hover_color="#388E3C",
            font=("Arial", 12)
        )
        btn_valider.pack(fill="x", pady=5)

    # ═══════════════════════════════════════════════════════════════════════
    # MÉTHODES CSV
    # ═══════════════════════════════════════════════════════════════════════
    def ouvrir_fenetre_csv(self):
        window_tableau_csv(callback=self.recevoir_voyages_csv)

    def recevoir_voyages_csv(self, voyages, matrice):
        self.voyages_disponibles = voyages
        self.afficher_voyages_dans_tree()
        msgbox.showinfo(
            "Voyages chargés",
            f"{len(voyages)} voyage(s) chargé(s) dans la liste"
        )

    def afficher_voyages_dans_tree(self):
        for item in self.tree_voyages.get_children():
            self.tree_voyages.delete(item)

        self.voyages_selectionnes.clear()

        for idx, v in enumerate(self.voyages_disponibles):
            h_debut = f"{v.hdebut // 60:02d}:{v.hdebut % 60:02d}"
            h_fin = f"{v.hfin // 60:02d}:{v.hfin % 60:02d}"
            de_a = f"{v.arret_debut[:10]}→{v.arret_fin[:10]}"

            self.tree_voyages.insert(
                '', 'end', iid=f"v_{idx}",
                values=('☐', v.num_voyage, v.num_ligne, h_debut, h_fin, de_a)
            )
        self.mettre_a_jour_label_selection()

    def toggle_voyage_selection(self, event):
        item = self.tree_voyages.identify('item', event.x, event.y)
        column = self.tree_voyages.identify_column(event.x)

        if not item or column != '#1':
            return

        idx = int(item.split('_')[1])
        values = list(self.tree_voyages.item(item, 'values'))

        if values[0] == '☐':
            values[0] = '☑'
            self.voyages_selectionnes[item] = self.voyages_disponibles[idx]
            self.tree_voyages.item(item, values=values, tags=('selected',))
        else:
            values[0] = '☐'
            if item in self.voyages_selectionnes:
                del self.voyages_selectionnes[item]
            self.tree_voyages.item(item, values=values, tags=())

        self.mettre_a_jour_label_selection()

    def mettre_a_jour_label_selection(self):
        nb_selectionnes = len(self.voyages_selectionnes)
        self.label_selection.configure(text=f"{nb_selectionnes} voyage(s) sélectionné(s)")


    def creer_nouveau_service(self):
        type_service = self.combo_type_service.get()
        nouveau_service = service_agent(
            num_service=self.compteur_service,
            type_service=type_service
        )

        self.services.append(nouveau_service)
        self.creer_widget_service(nouveau_service)
        self.compteur_service += 1

        msgbox.showinfo(
            "Service créé",
            f"Service {nouveau_service.num_service} ({type_service}) créé"
        )

    def creer_widget_service(self, service):
        frame_service = ctk.CTkFrame(
            self.scrollable_zone_travail,
            border_color="#4CAF50",
            border_width=2,
            corner_radius=10
        )
        frame_service.pack(fill="x", padx=5, pady=5)

        frame_header = ctk.CTkFrame(frame_service, fg_color="transparent")
        frame_header.pack(fill="x", padx=10, pady=5)

        label_titre = ctk.CTkLabel(
            frame_header,
            text=f"Service {service.num_service} ({service.type_service})",
            font=("Arial", 14, "bold")
        )
        label_titre.pack(side="left")

        btn_supprimer = ctk.CTkButton(
            frame_header, text="✕", width=30, height=30,
            fg_color="#f44336", hover_color="#d32f2f",
            command=lambda s=service: self.supprimer_service(s)
        )
        btn_supprimer.pack(side="right", padx=5)

        btn_selectionner = ctk.CTkButton(
            frame_header, text="Sélectionner", width=100, height=30,
            fg_color="#2196F3", hover_color="#1976D2",
            command=lambda s=service: self.selectionner_service(s)
        )
        btn_selectionner.pack(side="right", padx=5)

        timeline = TimeLineWisuelle(frame_service, service=service, height=60)
        timeline.pack(fill="x", padx=10, pady=5)

        label_info = ctk.CTkLabel(
            frame_service,
            text=f"0 voyage(s) - Durée: 0h00",
            font=("Arial", 10)
        )
        label_info.pack(pady=5)

        self.widgets_service[service] = {
            'frame': frame_service,
            'timeline': timeline,
            'label_info': label_info
        }

    def supprimer_service(self, service):
        if service in self.widgets_service:
            self.widgets_service[service]['frame'].destroy()
            del self.widgets_service[service]

        if service in self.services:
            self.services.remove(service)

        if self.service_actif == service:
            self.service_actif = None
            self.label_selection_actif.configure(text="Aucun service sélectionné")
            self.label_details.configure(text="Sélectionnez un service\npour voir les détails")
            self.frame_coupure.pack_forget()

    def selectionner_service(self, service):
        self.service_actif = service
        self.label_selection_actif.configure(
            text=f"Service {service.num_service} ({service.type_service})"
        )
        self.afficher_detail_service(service)

        for srv, widgets in self.widgets_service.items():
            if srv == service:
                widgets['frame'].configure(border_color="#2196F3", border_width=3)
            else:
                widgets['frame'].configure(border_color="#4CAF50", border_width=2)

    def afficher_detail_service(self, service):
        """Affiche les détails du service sélectionné"""
        nb_voyages = len(service.voyages)
        duree = service.duree_services()
        heures = duree // 60
        minutes = duree % 60

        if nb_voyages > 0:
            debut = min(v.hdebut for v in service.voyages)
            fin = max(v.hfin for v in service.voyages)
            h_debut = f"{debut // 60:02d}h{debut % 60:02d}"
            h_fin = f"{fin // 60:02d}h{fin % 60:02d}"
            detail_text = f"Service {service.num_service}\n"
            detail_text += f"Type: {service.type_service}\n"
            detail_text += f"Voyages: {nb_voyages}\n"
            detail_text += f"Plage: {h_debut} - {h_fin}\n"
            detail_text += f"Durée: {heures}h{minutes:02d}"
        else:
            detail_text = f"Service {service.num_service}\n"
            detail_text += f"Type: {service.type_service}\n"
            detail_text += "Aucun voyage assigné"

        self.label_details.configure(text=detail_text)

        # ═══════════════════════════════════════════════════════════════
        # Afficher/masquer la section coupure
        # ═══════════════════════════════════════════════════════════════
        self.frame_coupure.pack_forget()

        if service.type_service == "coupé":
            self.frame_coupure.pack(fill="x", pady=10, padx=5, before=self.frame_bouton_limites)

        # ═══════════════════════════════════════════════════════════════
        # Remplir les champs limites
        # ═══════════════════════════════════════════════════════════════
        self.entry_heure_debut.delete(0, 'end')
        self.entry_min_debut.delete(0, 'end')
        self.entry_heure_fin.delete(0, 'end')
        self.entry_min_fin.delete(0, 'end')

        limites_text = "Limites: Non définies"

        if service.heure_debut is not None and service.heure_fin is not None:
            h_lim_d = service.heure_debut // 60
            m_lim_d = service.heure_debut % 60
            h_lim_f = service.heure_fin // 60
            m_lim_f = service.heure_fin % 60

            self.entry_heure_debut.insert(0, f"{h_lim_d:02d}")
            self.entry_min_debut.insert(0, f"{m_lim_d:02d}")
            self.entry_heure_fin.insert(0, f"{h_lim_f:02d}")
            self.entry_min_fin.insert(0, f"{m_lim_f:02d}")

            limites_text = f"Limites: {h_lim_d:02d}h{m_lim_d:02d} - {h_lim_f:02d}h{m_lim_f:02d}"

        # ═══════════════════════════════════════════════════════════════
        # Remplir les champs coupure
        # ═══════════════════════════════════════════════════════════════
        self.entry_heure_debut_coupure.delete(0, 'end')
        self.entry_min_debut_coupure.delete(0, 'end')
        self.entry_heure_fin_coupure.delete(0, 'end')
        self.entry_min_fin_coupure.delete(0, 'end')
        self.label_duree_coupure.configure(text="Durée coupure: --")

        if service.type_service == "coupé":
            if service.heure_debut_coupure is not None and service.heure_fin_coupure is not None:
                h_coup_d = service.heure_debut_coupure // 60
                m_coup_d = service.heure_debut_coupure % 60
                h_coup_f = service.heure_fin_coupure // 60
                m_coup_f = service.heure_fin_coupure % 60

                self.entry_heure_debut_coupure.insert(0, f"{h_coup_d:02d}")
                self.entry_min_debut_coupure.insert(0, f"{m_coup_d:02d}")
                self.entry_heure_fin_coupure.insert(0, f"{h_coup_f:02d}")
                self.entry_min_fin_coupure.insert(0, f"{m_coup_f:02d}")

                duree_coup = service.duree_coupure()
                h_duree = duree_coup // 60
                m_duree = duree_coup % 60
                self.label_duree_coupure.configure(text=f"Durée coupure: {h_duree}h{m_duree:02d}")

                limites_text += f"\nCoupure: {h_coup_d:02d}h{m_coup_d:02d} - {h_coup_f:02d}h{m_coup_f:02d}"

        self.label_limites_actuelles.configure(
            text=limites_text,
            text_color="#4CAF50" if service.heure_debut is not None else "#888888"
        )

        # ═══════════════════════════════════════════════════════════════
        # Afficher la liste des voyages
        # ═══════════════════════════════════════════════════════════════
        for widget in self.frame_voyages_liste.winfo_children():
            widget.destroy()

        for v in sorted(service.voyages, key=lambda x: x.hdebut):
            h_d = f"{v.hdebut // 60:02d}h{v.hdebut % 60:02d}"
            h_f = f"{v.hfin // 60:02d}h{v.hfin % 60:02d}"

            frame_voyage = ctk.CTkFrame(self.frame_voyages_liste)
            frame_voyage.pack(fill="x", pady=2)

            ctk.CTkLabel(
                frame_voyage,
                text=f"V{v.num_voyage} | {v.num_ligne} | {h_d}-{h_f}",
                font=("Arial", 10)
            ).pack(side="left", padx=5)

    def mettre_a_jour_widget_service(self, service):
        if service in self.widgets_service:
            widgets = self.widgets_service[service]
            widgets['timeline'].service = service
            widgets['timeline'].rafraichir()

            nb_voyages = len(service.voyages)
            duree = service.duree_services()
            heures = duree // 60
            minutes = duree % 60
            widgets['label_info'].configure(
                text=f"{nb_voyages} voyage(s) - Durée: {heures}h{minutes:02d}"
            )

    # ═══════════════════════════════════════════════════════════════════════
    # MÉTHODES LIMITES
    # ═══════════════════════════════════════════════════════════════════════
    def appliquer_limites_service(self):
        """Applique les heures limites et coupure au service actif"""
        if not self.service_actif:
            msgbox.showwarning("Attention", "Aucun service sélectionné")
            return

        try:
            # Récupérer les limites principales
            h_debut = self.entry_heure_debut.get().strip()
            m_debut = self.entry_min_debut.get().strip()
            h_fin = self.entry_heure_fin.get().strip()
            m_fin = self.entry_min_fin.get().strip()

            if not all([h_debut, m_debut, h_fin, m_fin]):
                msgbox.showwarning("Attention", "Veuillez remplir les heures de début et fin")
                return

            heure_debut = int(h_debut)
            min_debut = int(m_debut)
            heure_fin = int(h_fin)
            min_fin = int(m_fin)

            if not (0 <= heure_debut <= 23 and 0 <= min_debut <= 59):
                msgbox.showerror("Erreur", "Heure de début invalide")
                return
            if not (0 <= heure_fin <= 23 and 0 <= min_fin <= 59):
                msgbox.showerror("Erreur", "Heure de fin invalide")
                return

            limite_debut = heure_debut * 60 + min_debut
            limite_fin = heure_fin * 60 + min_fin

            if limite_fin <= limite_debut:
                msgbox.showerror("Erreur", "L'heure de fin doit être après l'heure de début")
                return

            # Récupérer les heures de coupure (si service coupé)
            coupure_debut = None
            coupure_fin = None

            if self.service_actif.type_service == "coupé":
                h_coup_deb = self.entry_heure_debut_coupure.get().strip()
                m_coup_deb = self.entry_min_debut_coupure.get().strip()
                h_coup_fin = self.entry_heure_fin_coupure.get().strip()
                m_coup_fin = self.entry_min_fin_coupure.get().strip()

                if all([h_coup_deb, m_coup_deb, h_coup_fin, m_coup_fin]):
                    heure_coup_deb = int(h_coup_deb)
                    min_coup_deb = int(m_coup_deb)
                    heure_coup_fin = int(h_coup_fin)
                    min_coup_fin = int(m_coup_fin)

                    if not (0 <= heure_coup_deb <= 23 and 0 <= min_coup_deb <= 59):
                        msgbox.showerror("Erreur", "Heure de début de coupure invalide")
                        return
                    if not (0 <= heure_coup_fin <= 23 and 0 <= min_coup_fin <= 59):
                        msgbox.showerror("Erreur", "Heure de fin de coupure invalide")
                        return

                    coupure_debut = heure_coup_deb * 60 + min_coup_deb
                    coupure_fin = heure_coup_fin * 60 + min_coup_fin

                    if coupure_fin <= coupure_debut:
                        msgbox.showerror("Erreur", "L'heure de fin de coupure doit être après le début")
                        return

                    if coupure_debut < limite_debut or coupure_fin > limite_fin:
                        msgbox.showerror("Erreur", "La coupure doit être dans les limites du service")
                        return
                else:
                    msgbox.showwarning("Attention", "Veuillez remplir les heures de coupure pour un service coupé")
                    return

            # Vérifier les voyages existants
            voyages_hors_limites = []
            for v in self.service_actif.voyages:
                h_d = f"{v.hdebut // 60:02d}h{v.hdebut % 60:02d}"
                h_f = f"{v.hfin // 60:02d}h{v.hfin % 60:02d}"

                if v.hdebut < limite_debut or v.hfin > limite_fin:
                    voyages_hors_limites.append(f"V{v.num_voyage} ({h_d}-{h_f}) - hors limites")
                elif coupure_debut is not None and coupure_fin is not None:
                    if not (v.hfin <= coupure_debut or v.hdebut >= coupure_fin):
                        voyages_hors_limites.append(f"V{v.num_voyage} ({h_d}-{h_f}) - dans la coupure")

            if voyages_hors_limites:
                message = "⚠️ Ces voyages seront supprimés:\n\n"
                message += "\n".join(voyages_hors_limites)
                message += "\n\nContinuer?"
                if msgbox.askyesno("Voyages hors limites", message):
                    # Garder seulement les voyages valides
                    self.service_actif.voyages = [v for v in self.service_actif.voyages
                                                  if self.service_actif.voyage_dans_limites(v)[0]]
                else:
                    return


            self.service_actif.set_limites(limite_debut, limite_fin)

            if coupure_debut is not None and coupure_fin is not None:
                self.service_actif.set_coupure(coupure_debut, coupure_fin)

            self.afficher_detail_service(self.service_actif)
            self.mettre_a_jour_widget_service(self.service_actif)

            msgbox.showinfo("Succès", "Limites appliquées au service")

        except ValueError:
            msgbox.showerror("Erreur", "Veuillez entrer des nombres valides")

    # ═══════════════════════════════════════════════════════════════════════
    # MÉTHODES AJOUT VOYAGES
    # ═══════════════════════════════════════════════════════════════════════
    def verifier_chevauchement(self, nouveau_voyage, service):
        """Vérifie si un voyage chevauche un voyage existant"""
        for v_existant in service.voyages:
            if not (nouveau_voyage.hfin <= v_existant.hdebut or nouveau_voyage.hdebut >= v_existant.hfin):
                return v_existant
        return None

    def ajouter_voyages_au_service(self):
        """Ajoute les voyages sélectionnés au service actif"""
        if not self.service_actif:
            msgbox.showwarning("Attention", "Veuillez d'abord sélectionner un service")
            return

        if not self.voyages_selectionnes:
            msgbox.showwarning("Attention", "Aucun voyage sélectionné")
            return

        nb_ajoutes = 0
        voyages_refuses_chevauchement = []
        voyages_refuses_limites = []

        for item, voyage_a_ajouter in list(self.voyages_selectionnes.items()):
            if voyage_a_ajouter in self.service_actif.voyages:
                continue

            h_debut_v = f"{voyage_a_ajouter.hdebut // 60:02d}h{voyage_a_ajouter.hdebut % 60:02d}"
            h_fin_v = f"{voyage_a_ajouter.hfin // 60:02d}h{voyage_a_ajouter.hfin % 60:02d}"

            # Vérifier les limites horaires
            dans_limites, raison = self.service_actif.voyage_dans_limites(voyage_a_ajouter)
            if not dans_limites:
                voyages_refuses_limites.append(
                    f"• V{voyage_a_ajouter.num_voyage} ({h_debut_v}-{h_fin_v}) {raison}"
                )
                values = list(self.tree_voyages.item(item, 'values'))
                values[0] = '☐'
                self.tree_voyages.item(item, values=values, tags=())
                continue

            # Vérifier le chevauchement
            conflit = self.verifier_chevauchement(voyage_a_ajouter, self.service_actif)
            if conflit:
                h_debut_conf = f"{conflit.hdebut // 60:02d}h{conflit.hdebut % 60:02d}"
                h_fin_conf = f"{conflit.hfin // 60:02d}h{conflit.hfin % 60:02d}"
                voyages_refuses_chevauchement.append(
                    f"• V{voyage_a_ajouter.num_voyage} ({h_debut_v}-{h_fin_v}) chevauche V{conflit.num_voyage} ({h_debut_conf}-{h_fin_conf})"
                )
                values = list(self.tree_voyages.item(item, 'values'))
                values[0] = '☐'
                self.tree_voyages.item(item, values=values, tags=())
            else:
                self.service_actif.ajout_voyages(voyage_a_ajouter)
                nb_ajoutes += 1
                values = list(self.tree_voyages.item(item, 'values'))
                values[0] = '✓'
                self.tree_voyages.item(item, values=values, tags=('disabled',))

        self.voyages_selectionnes.clear()
        self.mettre_a_jour_label_selection()
        self.mettre_a_jour_widget_service(self.service_actif)
        self.afficher_detail_service(self.service_actif)

        # Afficher le résultat
        if voyages_refuses_limites or voyages_refuses_chevauchement:
            message = f"✅ {nb_ajoutes} voyage(s) ajouté(s)\n\n"
            if voyages_refuses_limites:
                message += f"⏰ {len(voyages_refuses_limites)} refusé(s) (hors limites):\n"
                message += "\n".join(voyages_refuses_limites)
                message += "\n\n"
            if voyages_refuses_chevauchement:
                message += f"⚠️ {len(voyages_refuses_chevauchement)} refusé(s) (chevauchement):\n"
                message += "\n".join(voyages_refuses_chevauchement)
            msgbox.showwarning("Ajout partiel", message)
        elif nb_ajoutes > 0:
            msgbox.showinfo("Succès", f"{nb_ajoutes} voyage(s) ajouté(s) au service")
        else:
            msgbox.showinfo("Info", "Aucun voyage ajouté")

    # ═══════════════════════════════════════════════════════════════════════
    # MÉTHODES PLACEHOLDER
    # ═══════════════════════════════════════════════════════════════════════
    def completer_avec_ortools(self):
        msgbox.showinfo("Info", "Fonction: Optimiser avec OR-Tools")

    def exporter_planning(self):
        msgbox.showinfo("Info", "Fonction: Exporter planning")

    def valider_planning(self):
        msgbox.showinfo("Info", "Fonction: Valider planning")


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Test Interface - Tab 5")
    app.geometry("1920x1080")

    interface = Interface(app)
    interface.pack(fill="both", expand=True)

    app.mainloop()