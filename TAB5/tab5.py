from logging import setLogRecordFactory

import customtkinter as ctk
from tkinter import ttk, messagebox as msgbox, Canvas, filedialog

import self
from ortools import service

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
            bg= "#2b2b2b",
            height=150,
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

        for h in range(4,25,2):
            x = self._heure_vers_x(h * 60, width)
            self.canvas.create_line(x,20,height - 10, fill="#444444", dash=(2,2))
            self.canvas.create_text(x, 10, text= f"{h:02d}h", fill="white", font=("Arial", 8))

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

        for h in range(4,25,2):
            x = self._heure_vers_x(h * 60, width)
            self.canvas.create_line(x,20,x,height - 10, fill="#444444", dash=(2,2))
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
        y_start = 5

        for idx_ligne, ligne in enumerate(lignes_y):
            y_rect = y_start + idx_ligne * (h_rect + espace_entre)

            for v in ligne:
                x1 = self._heure_vers_x(v.hdebut, width)
                x2 = self._heure_vers_x(v.hfin, width)

                h_d = f"{v.hdebut // 60:02d}h{v.hdebut % 60:02d}"
                h_f = f"{v.hfin // 60:02d}h{v.hfin % 60:02d}"

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
        debut = 4*60
        fin = 24*60
        ratio = (minutes-debut)/(fin-debut)
        return 50 + ratio * (width-100)

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
        scrollbar.pack(side="right", fill="y")
        self.tree_voyages.pack(side="left", fill="both", expand=True)

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

    def ouvrir_fenetre_csv(self):
        window_tableau_csv(callback=self.recevoir_voyages_csv)

    def recevoir_voyages_csv(self, voyages, martrice):
        self.voyages_disponibles=voyages
        self.afficher_voyages_dans_tree(martrice)
        msgbox.showinfo(
            "Voyages chargés",
            f"{len(voyages)} voyage(s) chargé(s) dans la liste"
        )

    def afficher_voyages_dans_tree(self, matrice=None):
        for item in self.tree_voyages.get_children():
            self.tree_voyages.delete(item)

        self.voyages_selectionnes.clear()

        for idx, v in enumerate(self.voyages_disponibles):
            h_debut = f"{v.hdebut // 60:02d}:{v.hdebut % 60:02d}"
            h_fin = f"{v.hfin // 60:02d}:{v.hfin % 60:02d}"
            de_a = f"{v.arret_debut[:10]}→{v.arret_fin[:10]}"

            item_id = self.tree_voyages.insert(
                '',
                'end',
                iid=f"v_{idx}",
                values=('☐', v.num_voyage, v.num_ligne, h_debut, h_fin, de_a)
            )
        self.mettre_a_jour_label_selection()

    def toggle_voyage_selection(self, event):
        item = self.tree_voyages.identify('item', event.x, event.y)
        column = self.tree_voyages.identify_column(event.x)

        if not item or column != '#1':
            return

        # Récupérer l'index du voyage
        idx = int(item.split('_')[1])

        # Toggle la sélection
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
        self.label_selection.configure(
            text=f"{nb_selectionnes} voyage(s) sélectionné(s)"
        )

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