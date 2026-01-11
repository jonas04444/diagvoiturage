import customtkinter as ctk
from tkinter import ttk, messagebox as msgbox, Canvas, filedialog

class TimelineVisuelle(ctk.CTkFrame):

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
