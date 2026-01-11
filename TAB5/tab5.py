import customtkinter as ctk
from tkinter import ttk, messagebox as msgbox, Canvas, filedialog

from ortools import service

from objet import voyage, service_agent, proposition
from tabelauCSV import window_tableau_csv

class Interface(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

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

        panel_central =  ctk.CTkFrame(self)
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
            f"service {nouveau_service.num_service} ({type_service}) créé"
        )

    def creer_widget_service(self, service):
        frame_service = ctk.CTkFrame(
            self.scrollable_zone_travail,
            fg_color="#2b2b2b",
            border_width=2,
            border_color="#4CAF50"
        )
        frame_service.pack(fill="x", padx=5, pady=5)

        header = ctk.CTkFrame(frame_service, fg_color="#1f1f1f")
        header.pack(fill="x", padx=2, pady=2)

        label_service = ctk.CTkLabel(
            header,
            text=f"service {service.num_service} ({service.type_service})",
        )
        label_service.pack(side= "left", padx=10, pady=5)

        label_voyages = ctk.CTkLabel(
            header,
            text=f"{len(service.voyages)} voyages",
            font=("Arial", 11)
        )
        label_voyages.pack(side="left", padx=10)

        btn_select = ctk.CTkButton(
            header,
            text="Sélectionner",
            width=100,
            command=lambda: self.selectionner_service(service)
        )
        btn_select.pack(side="right", padx=5)

        btn_delete = ctk.CTkButton(
            header,
            text="✖",
            width=30,
            fg_color="#f44336",
            hover_color="#d32f2f",
            command=lambda: self.supprimer_service(service, frame_service)
        )
        btn_delete.pack(side="right", padx=5)

        self.widgets_services[service] = {
            'frame': frame_service,
            'label_voyages': label_voyages,
            'header': header
        }

    def selectionner_service(self, service):
        self.service_actif = service
        self.label_selection_actif.configure(
            text=f"service {service.num_service} ({service.type_service})"
        )
        self.afficher_detail_service(service)

        for srv, widgets in self.widgets_service.items():
            if srv == service:
                widgets['frame'].configure(border_color = "#2196F3", border_width = 3)
            else:
                widgets['frame'].configure(border_color = "#4CAF50", border_width = 2)

    def ajouter_voyages_au_service(self):
        msgbox.showinfo("Info", "Fonction: Ajouter voyages au service")

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