import customtkinter as ctk
from tkinter import ttk, messagebox


class InterfaceDemo(ctk.CTkFrame):
    """Classe pour tester l'interface"""

    def __init__(self, parent):
        super().__init__(parent)

        # Configuration de la grille
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        # Créer l'interface
        self.creer_interface()

    def creer_interface(self):
        """Crée l'interface complète"""

        # ========== PANNEAU GAUCHE ==========
        panel_gauche = ctk.CTkFrame(self, width=500)
        panel_gauche.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        panel_gauche.grid_propagate(False)

        label_titre_gauche = ctk.CTkLabel(
            panel_gauche, text="📋 Voyages Disponibles",
            font=("Arial", 18, "bold")
        )
        label_titre_gauche.pack(pady=10)

        btn_charger = ctk.CTkButton(
            panel_gauche, text="📂 Charger voyages CSV",
            command=self.charger_voyages_csv, height=50
        )
        btn_charger.pack(pady=10, padx=10, fill="x")

        frame_liste_voyages = ctk.CTkFrame(panel_gauche)
        frame_liste_voyages.pack(fill="both", expand=True, padx=10, pady=10)

        colonnes = ('✓', 'Voy.', 'Ligne', 'Début', 'Fin', 'De→À')
        self.tree_voyages = ttk.Treeview(
            frame_liste_voyages, columns=colonnes,
            show='headings', height=25, selectmode='extended'
        )

        largeurs = {'✓': 35, 'Voy.': 60, 'Ligne': 70, 'Début': 70, 'Fin': 70, 'De→À': 120}
        for col, largeur in largeurs.items():
            self.tree_voyages.column(col, width=largeur, anchor='center')
            self.tree_voyages.heading(col, text=col)

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
            font=("Arial", 11)
        )
        self.label_selection.pack(pady=5)

        # ========== PANNEAU CENTRAL ==========
        panel_central = ctk.CTkFrame(self)
        panel_central.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        label_titre_central = ctk.CTkLabel(
            panel_central, text="🎯 Zone de Création",
            font=("Arial", 18, "bold")
        )
        label_titre_central.pack(pady=10)

        toolbar = ctk.CTkFrame(panel_central, height=70, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=10)

        btn_nouveau_service = ctk.CTkButton(
            toolbar, text="➕ Nouveau Service",
            command=self.creer_nouveau_service, height=50,
            fg_color="#4CAF50", hover_color="#388E3C",
            font=("Arial", 12)
        )
        btn_nouveau_service.pack(side="left", padx=5)

        self.combo_type_service = ctk.CTkComboBox(
            toolbar, values=["matin", "apres_midi"],
            width=180, height=50,
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

        btn_completer = ctk.CTkButton(
            toolbar, text="🤖 Optimiser (OR-Tools)",
            command=self.completer_avec_ortools, height=50,
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
        panel_droit = ctk.CTkFrame(self, width=440)
        panel_droit.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        panel_droit.grid_propagate(False)

        label_titre_droit = ctk.CTkLabel(
            panel_droit, text="📝 Détails du Service",
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
            frame_actions, text="💾 Exporter Planning",
            command=self.exporter_planning, height=50,
            font=("Arial", 12)
        )
        btn_exporter.pack(fill="x", pady=5)

        btn_valider = ctk.CTkButton(
            frame_actions, text="✅ Valider Planning",
            command=self.valider_planning, height=50,
            fg_color="#4CAF50", hover_color="#388E3C",
            font=("Arial", 12)
        )
        btn_valider.pack(fill="x", pady=5)

    # Méthodes stub pour les boutons (pour éviter les erreurs)
    def charger_voyages_csv(self):
        messagebox.showinfo("Info", "Fonction: Charger voyages CSV")

    def toggle_voyage_selection(self, event):
        pass

    def creer_nouveau_service(self):
        messagebox.showinfo("Info", "Fonction: Créer nouveau service")

    def ajouter_voyages_au_service(self):
        messagebox.showinfo("Info", "Fonction: Ajouter voyages au service")

    def completer_avec_ortools(self):
        messagebox.showinfo("Info", "Fonction: Optimiser avec OR-Tools")

    def exporter_planning(self):
        messagebox.showinfo("Info", "Fonction: Exporter planning")

    def valider_planning(self):
        messagebox.showinfo("Info", "Fonction: Valider planning")



# Lancement de l'application
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Test Interface - Tab 5")
    app.geometry("1920x1080")

    # Créer l'interface
    interface = InterfaceDemo(app)
    interface.pack(fill="both", expand=True)

    app.mainloop()