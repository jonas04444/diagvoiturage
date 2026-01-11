import customtkinter as ctk
from tkinter import ttk, messagebox as msgbox, Canvas, filedialog
from objet import voyage, service_agent, proposition
from tabelauCSV import window_tableau_csv


class Interface(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        # Liste pour stocker les services créés
        self.services = []
        self.compteur_service = 1
        self.service_actif = None

        # Dictionnaire pour associer les widgets de service aux objets service_agent
        self.widgets_services = {}

        self.creer_interface()

    def creer_interface(self):

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
            command=window_tableau_csv, height=50
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
        scrollbar.pack(side="right", fill="y")

        self.tree_voyages.bind('<Button-1>', self.toggle_voyage_selection)

        self.label_selection = ctk.CTkLabel(
            panel_gauche, text=" 0 voyages sélectionés",
            font=("Arial", 11, "bold")
        )

        self.label_selection.pack(pady=5)

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
            fg_color="#4CAF50", hover_color="388E3C",
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
            fg_color="#2196F3", hover_color="1976D2",
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

        self.label_details = ctk.CTkLabel(
            self.frame_details,
            text="Sélectionnez un service\npour voir les détails",
            font=("Arial", 11), justify="left"
        )
        self.label_details.pack(pady=20)

        self.frame_voyages_liste = ctk.CTkFrame(self.frame_details, fg_color="transparent")
        self.frame_voyages_liste.pack(fill="both", expand=True, pady=10)

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

    def charger_voyages_csv(self):
        msgbox.showinfo("Info", "Fonction: Charger voyages CSV")

    def toggle_voyage_selection(self, event):
        pass

    def creer_nouveau_service(self):
        """Crée un nouveau service_agent avec le type sélectionné"""
        type_service = self.combo_type_service.get()

        # Créer l'objet service_agent directement
        nouveau_service = service_agent(
            num_service=self.compteur_service,
            type_service=type_service
        )

        # Ajouter à la liste des services
        self.services.append(nouveau_service)

        # Créer le widget visuel pour ce service
        self.creer_widget_service(nouveau_service)

        # Sélectionner automatiquement le nouveau service
        self.selectionner_service(nouveau_service)

        # Incrémenter le compteur
        self.compteur_service += 1

        # Message de confirmation
        msgbox.showinfo(
            "Service créé",
            f"Service {nouveau_service.num_service} ({type_service}) créé !\n\nConfigurez les horaires dans le panneau de détails."
        )

    def creer_widget_service(self, service):
        """Crée le widget visuel pour un service"""
        frame_service = ctk.CTkFrame(
            self.scrollable_zone_travail,
            fg_color="#2b2b2b",
            border_width=2,
            border_color="#4CAF50"
        )
        frame_service.pack(fill="x", padx=5, pady=5)

        # En-tête du service
        header = ctk.CTkFrame(frame_service, fg_color="#1f1f1f")
        header.pack(fill="x", padx=2, pady=2)

        label_service = ctk.CTkLabel(
            header,
            text=f"Service {service.num_service} - {service.type_service.upper()}",
            font=("Arial", 14, "bold")
        )
        label_service.pack(side="left", padx=10, pady=5)

        label_voyages = ctk.CTkLabel(
            header,
            text=f"{len(service.voyages)} voyages",
            font=("Arial", 11)
        )
        label_voyages.pack(side="left", padx=10)

        # Bouton pour sélectionner ce service
        btn_select = ctk.CTkButton(
            header,
            text="Sélectionner",
            width=100,
            command=lambda: self.selectionner_service(service)
        )
        btn_select.pack(side="right", padx=5)

        # Bouton supprimer
        btn_delete = ctk.CTkButton(
            header,
            text="✖",
            width=30,
            fg_color="#f44336",
            hover_color="#d32f2f",
            command=lambda: self.supprimer_service(service, frame_service)
        )
        btn_delete.pack(side="right", padx=5)

        # Stocker l'association
        self.widgets_services[service] = {
            'frame': frame_service,
            'label_voyages': label_voyages,
            'header': header
        }

    def selectionner_service(self, service):
        """Sélectionne un service comme actif"""
        self.service_actif = service
        self.label_selection_actif.configure(
            text=f"Service {service.num_service} ({service.type_service}) sélectionné"
        )
        self.afficher_details_service(service)

        # Mettre en surbrillance visuellement
        for srv, widgets in self.widgets_services.items():
            if srv == service:
                widgets['frame'].configure(border_color="#2196F3", border_width=3)
            else:
                widgets['frame'].configure(border_color="#4CAF50", border_width=2)

    def afficher_details_service(self, service):
        """Affiche les détails d'un service dans le panneau de droite"""
        # Nettoyer l'affichage précédent
        for widget in self.frame_details.winfo_children():
            widget.destroy()

        # Titre
        titre = ctk.CTkLabel(
            self.frame_details,
            text=f"Service {service.num_service} - {service.type_service.upper()}",
            font=("Arial", 14, "bold")
        )
        titre.pack(pady=10)

        # Informations horaires - MODIFIABLES
        frame_horaires = ctk.CTkFrame(self.frame_details)
        frame_horaires.pack(fill="x", padx=10, pady=10)

        # Heure de début
        frame_debut = ctk.CTkFrame(frame_horaires, fg_color="transparent")
        frame_debut.pack(fill="x", padx=10, pady=8)

        label_debut = ctk.CTkLabel(
            frame_debut,
            text="🕐 Début service:",
            font=("Arial", 12, "bold"),
            anchor="w"
        )
        label_debut.pack(anchor="w", pady=(0, 5))

        entry_debut = ctk.CTkEntry(
            frame_debut,
            placeholder_text="HH:MM (ex: 08:30)",
            height=50,
            font=("Arial", 20, "bold"),
            fg_color="#FFFFFF",
            text_color="#000000",
            border_width=2,
            border_color="#4CAF50",
            justify="center"
        )
        entry_debut.insert(0, service.heure_debut if service.heure_debut else "")
        entry_debut.pack(fill="x")

        # Heure de fin
        frame_fin = ctk.CTkFrame(frame_horaires, fg_color="transparent")
        frame_fin.pack(fill="x", padx=10, pady=8)

        label_fin = ctk.CTkLabel(
            frame_fin,
            text="🕐 Fin service:",
            font=("Arial", 12, "bold"),
            anchor="w"
        )
        label_fin.pack(anchor="w", pady=(0, 5))

        entry_fin = ctk.CTkEntry(
            frame_fin,
            placeholder_text="HH:MM (ex: 16:30)",
            height=50,
            font=("Arial", 20, "bold"),
            fg_color="#FFFFFF",
            text_color="#000000",
            border_width=2,
            border_color="#4CAF50",
            justify="center"
        )
        entry_fin.insert(0, service.heure_fin if service.heure_fin else "")
        entry_fin.pack(side="left", padx=5)

        # Si service coupé, afficher les horaires de coupure
        entry_debut_coupure = None
        entry_fin_coupure = None

        if service.type_service == "coupé":
            label_sep = ctk.CTkLabel(
                frame_horaires,
                text="─── Période de coupure ───",
                font=("Arial", 11, "italic")
            )
            label_sep.pack(pady=15)

            # Début de coupure
            frame_debut_coupure = ctk.CTkFrame(frame_horaires, fg_color="transparent")
            frame_debut_coupure.pack(fill="x", padx=10, pady=8)

            label_debut_coupure = ctk.CTkLabel(
                frame_debut_coupure,
                text="⏸️  Début coupure:",
                font=("Arial", 12, "bold"),
                anchor="w"
            )
            label_debut_coupure.pack(anchor="w", pady=(0, 5))

            entry_debut_coupure = ctk.CTkEntry(
                frame_debut_coupure,
                placeholder_text="HH:MM (ex: 12:00)",
                height=50,
                font=("Arial", 20, "bold"),
                fg_color="#FFFFFF",
                text_color="#000000",
                border_width=2,
                border_color="#4CAF50",
                justify="center"
            )
            entry_debut_coupure.insert(0, service.heure_debut_coupure if service.heure_debut_coupure else "")
            entry_debut_coupure.pack(fill="x")

            # Fin de coupure
            frame_fin_coupure = ctk.CTkFrame(frame_horaires, fg_color="transparent")
            frame_fin_coupure.pack(fill="x", padx=10, pady=8)

            label_fin_coupure = ctk.CTkLabel(
                frame_fin_coupure,
                text="▶️  Fin coupure:",
                font=("Arial", 12, "bold"),
                anchor="w"
            )
            label_fin_coupure.pack(anchor="w", pady=(0, 5))

            entry_fin_coupure = ctk.CTkEntry(
                frame_fin_coupure,
                placeholder_text="HH:MM (ex: 14:00)",
                height=50,
                font=("Arial", 20, "bold"),
                fg_color="#FFFFFF",
                text_color="#000000",
                border_width=2,
                border_color="#4CAF50",
                justify="center"
            )
            entry_fin_coupure.insert(0, service.heure_fin_coupure if service.heure_fin_coupure else "")
            entry_fin_coupure.pack(side="left", padx=5)

        # Bouton pour sauvegarder les modifications
        btn_sauvegarder = ctk.CTkButton(
            frame_horaires,
            text="💾 Sauvegarder les horaires",
            command=lambda: self.sauvegarder_horaires_service(
                service,
                entry_debut,
                entry_fin,
                entry_debut_coupure,
                entry_fin_coupure
            ),
            fg_color="#2196F3",
            hover_color="#1976D2",
            height=35
        )
        btn_sauvegarder.pack(pady=15, fill="x", padx=5)

        # Separator
        ctk.CTkLabel(self.frame_details, text="─" * 40).pack(pady=10)

        # Afficher les voyages
        if service.voyages:
            info_text = str(service)
        else:
            info_text = "Aucun voyage assigné"

        label_info = ctk.CTkLabel(
            self.frame_details,
            text=info_text,
            font=("Arial", 11),
            justify="left"
        )
        label_info.pack(pady=10, padx=10, anchor="w")

    def supprimer_service(self, service, frame):
        """Supprime un service"""
        reponse = msgbox.askyesno(
            "Confirmation",
            f"Voulez-vous vraiment supprimer le Service {service.num_service}?"
        )

        if reponse:
            # Retirer de la liste
            self.services.remove(service)

            # Détruire le widget
            frame.destroy()

            # Retirer du dictionnaire
            del self.widgets_services[service]

            # Si c'était le service actif, réinitialiser
            if self.service_actif == service:
                self.service_actif = None
                self.label_selection_actif.configure(text="Aucun service sélectionné")

    def sauvegarder_horaires_service(self, service, entry_debut, entry_fin, entry_debut_coupure, entry_fin_coupure):
        """Sauvegarde les modifications des horaires d'un service"""
        heure_debut = entry_debut.get().strip()
        heure_fin = entry_fin.get().strip()

        # Validation des heures obligatoires
        if not self.valider_format_heure(heure_debut):
            msgbox.showerror("Erreur", "Format d'heure de début invalide (HH:MM)")
            return

        if not self.valider_format_heure(heure_fin):
            msgbox.showerror("Erreur", "Format d'heure de fin invalide (HH:MM)")
            return

        # Sauvegarder les heures principales
        service.heure_debut = heure_debut
        service.heure_fin = heure_fin

        # Si service coupé, valider et sauvegarder les heures de coupure
        if service.type_service == "coupé" and entry_debut_coupure and entry_fin_coupure:
            heure_debut_coupure = entry_debut_coupure.get().strip()
            heure_fin_coupure = entry_fin_coupure.get().strip()

            if heure_debut_coupure and not self.valider_format_heure(heure_debut_coupure):
                msgbox.showerror("Erreur", "Format d'heure de début de coupure invalide (HH:MM)")
                return

            if heure_fin_coupure and not self.valider_format_heure(heure_fin_coupure):
                msgbox.showerror("Erreur", "Format d'heure de fin de coupure invalide (HH:MM)")
                return

            service.heure_debut_coupure = heure_debut_coupure if heure_debut_coupure else None
            service.heure_fin_coupure = heure_fin_coupure if heure_fin_coupure else None

        # Confirmation
        msgbox.showinfo("Succès", "Horaires sauvegardés avec succès!")

        # Rafraîchir l'affichage
        self.afficher_details_service(service)

    def valider_format_heure(self, heure_str):
        """Valide le format HH:MM"""
        if not heure_str:
            return False

        try:
            parts = heure_str.split(':')
            if len(parts) != 2:
                return False

            h, m = int(parts[0]), int(parts[1])
            return 0 <= h <= 23 and 0 <= m <= 59
        except:
            return False

    def ajouter_voyages_au_service(self):
        """Ajoute les voyages sélectionnés au service actif"""
        if self.service_actif is None:
            msgbox.showwarning(
                "Attention",
                "Veuillez d'abord sélectionner un service!"
            )
            return


        msgbox.showinfo("Info", f"Ajout de voyages au Service {self.service_actif.num_service}")

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