#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application de gestion de voyages CSV
=====================================
Charge un fichier CSV, affiche les données dans un tableau avec tri,
permet la sélection de voyages via des checkboxes,
et exporte les sélections vers une base de données SQLite.

Auteur: Expert Python 3.13
Date: 2024
"""

import csv
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Vérification et import de ttkbootstrap
try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.constants import *
    BOOTSTRAP_AVAILABLE = True
except ImportError:
    print("ttkbootstrap non disponible, utilisation de Tkinter standard")
    BOOTSTRAP_AVAILABLE = False


class CSVVoyageManager:
    """Application principale pour la gestion des voyages CSV."""
    
    def __init__(self, root: tk.Tk):
        """
        Initialise l'application.
        
        Args:
            root: Fenêtre principale Tkinter
        """
        self.root = root
        self.root.title("Gestionnaire de Voyages CSV")
        self.root.geometry("1400x800")
        
        # Données
        self.csv_data: List[Dict[str, str]] = []
        self.csv_headers: List[str] = []
        self.sort_reverse: Dict[str, bool] = {}  # État du tri pour chaque colonne
        self.selected_rows: set = set()  # Ensemble des indices de lignes sélectionnées
        self.db_path: Optional[str] = None  # Chemin de la base de données SQLite sélectionnée
        
        # Interface
        self.setup_ui()
        
    def setup_ui(self):
        """Configure l'interface utilisateur."""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame pour les boutons en haut
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Bouton Charger CSV
        btn_load = ttk.Button(
            button_frame,
            text="Charger un fichier CSV",
            command=self.load_csv_dialog
        )
        btn_load.pack(side=tk.LEFT, padx=(0, 10))
        
        # Bouton Sélectionner base SQLite
        self.btn_select_db = ttk.Button(
            button_frame,
            text="Sélectionner une base SQLite",
            command=self.select_db_dialog
        )
        self.btn_select_db.pack(side=tk.LEFT, padx=(0, 10))
        
        # Label pour afficher la base de données sélectionnée
        self.db_label = ttk.Label(
            button_frame,
            text="Aucune base de données sélectionnée",
            foreground="gray"
        )
        self.db_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Bouton Exporter vers SQLite
        self.btn_export = ttk.Button(
            button_frame,
            text="Exporter les voyages sélectionnés vers SQLite",
            command=self.export_selected_to_db,
            state=tk.DISABLED
        )
        self.btn_export.pack(side=tk.LEFT, padx=(0, 10))
        
        # Bouton Sauvegarder dans la table trajet
        self.btn_save_trajet = ttk.Button(
            button_frame,
            text="Sauvegarder dans la table trajet",
            command=self.save_to_trajet_table,
            state=tk.DISABLED
        )
        self.btn_save_trajet.pack(side=tk.LEFT)
        
        # Label pour le nombre de sélections
        self.selection_label = ttk.Label(
            button_frame,
            text="Aucune sélection"
        )
        self.selection_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Frame pour le tableau avec scrollbars
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # TreeView pour afficher les données
        self.tree = ttk.Treeview(
            table_frame,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            show="headings"
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configuration des scrollbars
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        
        # Binding pour gérer les clics sur les cellules (une seule fois)
        self.tree.bind("<Button-1>", self.on_tree_click)
        
    def load_csv_dialog(self):
        """Ouvre une boîte de dialogue pour sélectionner un fichier CSV."""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        
        if file_path:
            self.load_csv(file_path)
    
    def load_csv(self, file_path: str):
        """
        Charge un fichier CSV et affiche les données.
        Détecte automatiquement l'encodage du fichier.
        
        Args:
            file_path: Chemin vers le fichier CSV
        """
        # Liste des encodages à essayer (du plus commun au moins commun)
        encodings = ['utf-8', 'utf-8-sig', 'windows-1252', 'iso-8859-1', 'latin1', 'cp1252']
        
        try:
            # Essai de chaque encodage jusqu'à ce qu'un fonctionne
            last_error = None
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        # Lecture avec le séparateur point-virgule
                        reader = csv.DictReader(f, delimiter=';')
                        self.csv_headers = reader.fieldnames or []
                        self.csv_data = list(reader)
                    
                    # Si on arrive ici, l'encodage fonctionne
                    break
                    
                except UnicodeDecodeError as e:
                    last_error = e
                    continue
                except Exception as e:
                    # Autre erreur (pas d'encodage)
                    raise e
            
            # Vérification si aucun encodage n'a fonctionné
            if last_error and not self.csv_data:
                raise UnicodeDecodeError(
                    last_error.encoding,
                    last_error.object,
                    last_error.start,
                    last_error.end,
                    f"Aucun encodage ne fonctionne. Essayé: {', '.join(encodings)}"
                )
            
            if not self.csv_data:
                messagebox.showwarning("Attention", "Le fichier CSV est vide.")
                return
            
            # Réinitialisation des sélections
            self.selected_rows.clear()
            self.sort_reverse.clear()
            
            # Peuplement du tableau
            self.populate_table()
            
            # Activation des boutons d'export
            self.btn_export.config(state=tk.NORMAL)
            self.btn_save_trajet.config(state=tk.NORMAL)
            
            messagebox.showinfo("Succès", f"{len(self.csv_data)} lignes chargées avec succès.")
            
        except FileNotFoundError:
            messagebox.showerror("Erreur", f"Fichier non trouvé: {file_path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement du CSV:\n{str(e)}")
    
    def populate_table(self):
        """Peuple le TreeView avec les données CSV."""
        # Suppression des colonnes existantes
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
        
        # Configuration des colonnes
        # Ajout de la colonne de sélection en premier
        all_columns = ["Sélection"] + list(self.csv_headers)
        self.tree["columns"] = all_columns
        
        # Configuration de la colonne de sélection
        self.tree.heading("#0", text="", anchor=tk.CENTER)
        self.tree.column("#0", width=0, stretch=False)
        
        # Configuration de chaque colonne
        for col in all_columns:
            if col == "Sélection":
                self.tree.heading(
                    col,
                    text=col,
                    anchor=tk.CENTER,
                    command=lambda c=col: self.sort_column(c)
                )
                self.tree.column(col, width=80, anchor=tk.CENTER, stretch=False)
            else:
                self.tree.heading(
                    col,
                    text=col,
                    anchor=tk.CENTER,
                    command=lambda c=col: self.sort_column(c)
                )
                # Largeur adaptative basée sur le contenu
                self.tree.column(col, width=120, anchor=tk.W, stretch=True)
        
        # Suppression des anciennes lignes
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Insertion des données
        for idx, row in enumerate(self.csv_data):
            # Valeur de la checkbox (✓ si sélectionné, sinon vide)
            checkbox_value = "✓" if idx in self.selected_rows else ""
            
            # Valeurs pour chaque colonne
            values = [checkbox_value] + [row.get(header, "") for header in self.csv_headers]
            
            # Insertion de la ligne avec l'index stocké dans les tags
            item = self.tree.insert("", tk.END, values=values, tags=(str(idx),))
        
        # Mise à jour du label de sélection
        self.update_selection_label()
    
    def on_tree_click(self, event):
        """
        Gère les clics sur le TreeView.
        Si le clic est sur la colonne de sélection, bascule la sélection.
        
        Args:
            event: Événement de clic
        """
        # Identification de l'élément cliqué
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        if not item:
            return
        
        # Vérification si c'est la colonne de sélection (colonne #1)
        if column == "#1":
            # Récupération de l'index de la ligne
            tags = self.tree.item(item, "tags")
            if tags:
                try:
                    row_index = int(tags[0])
                    self.toggle_selection(row_index)
                except (ValueError, IndexError):
                    pass
    
    def toggle_selection(self, row_index: int):
        """
        Bascule la sélection d'une ligne.
        
        Args:
            row_index: Index de la ligne dans csv_data
        """
        if row_index in self.selected_rows:
            self.selected_rows.remove(row_index)
        else:
            self.selected_rows.add(row_index)
        
        # Mise à jour de l'affichage
        self.refresh_checkboxes()
        self.update_selection_label()
    
    def refresh_checkboxes(self):
        """Met à jour l'affichage des checkboxes dans le tableau."""
        for item in self.tree.get_children():
            tags = self.tree.item(item, "tags")
            if tags:
                try:
                    row_index = int(tags[0])
                    checkbox_value = "✓" if row_index in self.selected_rows else ""
                    values = list(self.tree.item(item, "values"))
                    values[0] = checkbox_value
                    self.tree.item(item, values=values)
                except (ValueError, IndexError):
                    pass
    
    def update_selection_label(self):
        """Met à jour le label affichant le nombre de sélections."""
        count = len(self.selected_rows)
        if count == 0:
            self.selection_label.config(text="Aucune sélection")
        else:
            self.selection_label.config(text=f"{count} voyage(s) sélectionné(s)")
    
    def sort_column(self, column: str):
        """
        Trie les données par colonne.
        
        Args:
            column: Nom de la colonne à trier
        """
        if not self.csv_data:
            return
        
        # Si c'est la colonne de sélection, on ne trie pas
        if column == "Sélection":
            return
        
        # Détermination de l'ordre de tri
        reverse = self.sort_reverse.get(column, False)
        self.sort_reverse[column] = not reverse
        
        # Tri des données
        try:
            # Tentative de tri numérique si possible
            self.csv_data.sort(
                key=lambda x: self._try_convert(x.get(column, "")),
                reverse=reverse
            )
        except Exception:
            # Tri alphabétique en cas d'erreur
            self.csv_data.sort(
                key=lambda x: str(x.get(column, "")).lower(),
                reverse=reverse
            )
        
        # Réaffichage du tableau
        self.populate_table()
    
    def _try_convert(self, value: str):
        """
        Essaie de convertir une valeur en nombre pour le tri.
        
        Args:
            value: Valeur à convertir
            
        Returns:
            Nombre si conversion possible, sinon la valeur originale
        """
        if not value or not value.strip():
            return 0
        
        try:
            # Essai de conversion en float
            return float(value.replace(",", "."))
        except ValueError:
            try:
                # Essai de conversion en int
                return int(value)
            except ValueError:
                # Retour de la valeur originale pour tri alphabétique
                return str(value).lower()
    
    def select_db_dialog(self):
        """Ouvre une boîte de dialogue pour sélectionner une base de données SQLite existante."""
        db_path = filedialog.askopenfilename(
            title="Sélectionner une base de données SQLite",
            filetypes=[("Base de données SQLite", "*.db"), ("Tous les fichiers", "*.*")]
        )
        
        if db_path:
            self.db_path = db_path
            # Mise à jour du label avec le nom du fichier
            db_name = Path(db_path).name
            self.db_label.config(text=f"Base: {db_name}", foreground="green")
            messagebox.showinfo("Succès", f"Base de données sélectionnée:\n{db_path}")
    
    def export_selected_to_db(self):
        """
        Exporte les voyages sélectionnés vers une base de données SQLite.
        Utilise la base de données sélectionnée si disponible, sinon demande un nouveau chemin.
        """
        if not self.selected_rows:
            messagebox.showwarning("Attention", "Aucun voyage sélectionné.")
            return
        
        # Utilisation de la base de données sélectionnée ou demande d'un nouveau chemin
        if self.db_path:
            db_path = self.db_path
        else:
            # Demande du chemin de la base de données
            db_path = filedialog.asksaveasfilename(
                title="Enregistrer la base de données SQLite",
                defaultextension=".db",
                filetypes=[("Base de données SQLite", "*.db"), ("Tous les fichiers", "*.*")]
            )
            
            if not db_path:
                return
            
            # Sauvegarde du chemin pour les prochains exports
            self.db_path = db_path
            db_name = Path(db_path).name
            self.db_label.config(text=f"Base: {db_name}", foreground="green")
        
        try:
            # Connexion à la base de données
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Création de la table si elle n'existe pas
            self._create_table_if_not_exists(cursor)
            
            # Insertion des lignes sélectionnées
            rows_inserted = 0
            for row_index in sorted(self.selected_rows):
                if 0 <= row_index < len(self.csv_data):
                    row_data = self.csv_data[row_index]
                    self._insert_row(cursor, row_data)
                    rows_inserted += 1
            
            # Validation des changements
            conn.commit()
            conn.close()
            
            messagebox.showinfo(
                "Succès",
                f"{rows_inserted} voyage(s) exporté(s) avec succès vers:\n{db_path}"
            )
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export:\n{str(e)}")
    
    def _create_table_if_not_exists(self, cursor: sqlite3.Cursor):
        """
        Crée la table dans la base de données si elle n'existe pas.
        
        Args:
            cursor: Curseur SQLite
        """
        # Construction de la requête CREATE TABLE
        columns_def = []
        
        # Colonne ID auto-incrémentée
        columns_def.append("id INTEGER PRIMARY KEY AUTOINCREMENT")
        
        # Colonnes basées sur les en-têtes CSV
        for header in self.csv_headers:
            # Nettoyage du nom de colonne pour SQLite (remplacement des caractères spéciaux)
            clean_header = header.replace(" ", "_").replace("-", "_").replace(".", "_")
            clean_header = "".join(c for c in clean_header if c.isalnum() or c == "_")
            
            # Type TEXT pour toutes les colonnes (flexibilité maximale)
            columns_def.append(f"{clean_header} TEXT")
        
        # Colonne pour la date d'export
        columns_def.append("date_export TEXT")
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS voyages (
            {', '.join(columns_def)}
        )
        """
        
        cursor.execute(create_table_sql)
    
    def _insert_row(self, cursor: sqlite3.Cursor, row_data: Dict[str, str]):
        """
        Insère une ligne dans la base de données.
        
        Args:
            cursor: Curseur SQLite
            row_data: Dictionnaire contenant les données de la ligne
        """
        import datetime
        
        # Nettoyage des noms de colonnes
        clean_headers = [
            header.replace(" ", "_").replace("-", "_").replace(".", "_")
            for header in self.csv_headers
        ]
        clean_headers = [
            "".join(c for c in h if c.isalnum() or c == "_")
            for h in clean_headers
        ]
        
        # Préparation des colonnes et valeurs
        columns = ["id"] + clean_headers + ["date_export"]
        placeholders = ["?"] * (len(columns))
        placeholders[0] = "NULL"  # ID auto-incrémenté
        
        # Valeurs à insérer
        values = [row_data.get(header, "") for header in self.csv_headers]
        values.append(datetime.datetime.now().isoformat())
        
        insert_sql = f"""
        INSERT INTO voyages ({', '.join(columns[1:])})
        VALUES ({', '.join(placeholders[1:])})
        """
        
        cursor.execute(insert_sql, values)
    
    def save_to_trajet_table(self):
        """
        Sauvegarde les voyages sélectionnés dans la table 'trajet' de la base de données.
        """
        if not self.selected_rows:
            messagebox.showwarning("Attention", "Aucun voyage sélectionné.")
            return
        
        if not self.db_path:
            messagebox.showwarning("Attention", "Veuillez d'abord sélectionner une base de données.")
            return
        
        try:
            # Connexion à la base de données
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Création de la table trajet si elle n'existe pas
            self._create_trajet_table_if_not_exists(cursor)
            
            # Mapping des colonnes CSV vers les colonnes de la table trajet
            # Cette fonction essaie de trouver automatiquement les colonnes correspondantes
            column_mapping = self._get_trajet_column_mapping()
            
            # Vérification que les colonnes essentielles sont trouvées
            missing_columns = []
            if not column_mapping.get('Num_ligne'):
                missing_columns.append('Num_ligne (colonne "Ligne" attendue)')
            if not column_mapping.get('DP_arret'):
                missing_columns.append('DP_arret (colonne "De" attendue)')
            if not column_mapping.get('DR_arret'):
                missing_columns.append('DR_arret (colonne "Fin" ou "Direction" attendue)')
            if not column_mapping.get('Heure_Start'):
                missing_columns.append('Heure_Start (colonne "Début" attendue)')
            if not column_mapping.get('Heure_End'):
                missing_columns.append('Heure_End (colonne "Fin" attendue)')
            
            if missing_columns:
                messagebox.showerror(
                    "Erreur",
                    f"Colonnes manquantes dans le CSV:\n" + "\n".join(missing_columns) +
                    f"\n\nColonnes disponibles: {', '.join(self.csv_headers)}"
                )
                conn.close()
                return
            
            # Insertion des lignes sélectionnées
            rows_inserted = 0
            for row_index in sorted(self.selected_rows):
                if 0 <= row_index < len(self.csv_data):
                    row_data = self.csv_data[row_index]
                    self._insert_trajet_row(cursor, row_data, column_mapping)
                    rows_inserted += 1
            
            # Validation des changements
            conn.commit()
            conn.close()
            
            messagebox.showinfo(
                "Succès",
                f"{rows_inserted} trajet(s) sauvegardé(s) avec succès dans la table 'trajet'."
            )
            
        except sqlite3.IntegrityError as e:
            messagebox.showerror(
                "Erreur d'intégrité",
                f"Erreur lors de la sauvegarde (contrainte de clé étrangère probable):\n{str(e)}"
            )
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde:\n{str(e)}")
    
    def _create_trajet_table_if_not_exists(self, cursor: sqlite3.Cursor):
        """
        Crée la table 'trajet' dans la base de données si elle n'existe pas.
        
        Args:
            cursor: Curseur SQLite
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS trajet (
            id_trajet INTEGER PRIMARY KEY AUTOINCREMENT,
            Num_ligne INTEGER,
            Num_trajet INTEGER,
            variant INTEGER,
            DP_arret TEXT,
            DR_arret TEXT,
            Heure_Start TEXT,
            Heure_End TEXT,
            FOREIGN KEY(DP_arret) REFERENCES lieux(id_lieux),
            FOREIGN KEY(DR_arret) REFERENCES lieux(id_lieux),
            FOREIGN KEY(Num_ligne) REFERENCES Version_ligne(num_ligne)
        )
        """
        
        cursor.execute(create_table_sql)
    
    def _get_trajet_column_mapping(self) -> Dict[str, Optional[str]]:
        """
        Détermine le mapping entre les colonnes CSV et les colonnes de la table trajet.
        
        Returns:
            Dictionnaire avec les clés de la table trajet et les noms de colonnes CSV correspondants
        """
        mapping = {}
        
        # Mapping basé sur les noms de colonnes (insensible à la casse)
        csv_headers_lower = {h.lower(): h for h in self.csv_headers}
        
        # Num_ligne -> cherche "ligne"
        if 'ligne' in csv_headers_lower:
            mapping['Num_ligne'] = csv_headers_lower['ligne']
        else:
            mapping['Num_ligne'] = None
        
        # Num_trajet -> cherche "voy", "voy.", "trajet", "num_trajet"
        for key in ['voy.', 'voy', 'trajet', 'num_trajet', 'num trajet']:
            if key in csv_headers_lower:
                mapping['Num_trajet'] = csv_headers_lower[key]
                break
        else:
            mapping['Num_trajet'] = None
        
        # variant -> cherche "variant", "variante"
        for key in ['variant', 'variante']:
            if key in csv_headers_lower:
                mapping['variant'] = csv_headers_lower[key]
                break
        else:
            mapping['variant'] = None
        
        # DP_arret -> cherche "de", "depart", "départ"
        for key in ['de', 'depart', 'départ', 'dp_arret', 'dp arret']:
            if key in csv_headers_lower:
                mapping['DP_arret'] = csv_headers_lower[key]
                break
        else:
            mapping['DP_arret'] = None
        
        # DR_arret -> cherche "direction", "destination", "arrivee", "arrivée", "dr_arret", "dr arret"
        # On évite "fin" car il peut être utilisé pour Heure_End
        for key in ['direction', 'destination', 'arrivee', 'arrivée', 'dr_arret', 'dr arret']:
            if key in csv_headers_lower:
                mapping['DR_arret'] = csv_headers_lower[key]
                break
        else:
            # Si aucune colonne spécifique trouvée, on essaie "fin" en dernier recours
            if 'fin' in csv_headers_lower:
                mapping['DR_arret'] = csv_headers_lower['fin']
            else:
                mapping['DR_arret'] = None
        
        # Heure_Start -> cherche "début", "debut", "heure_start", "heure debut"
        for key in ['début', 'debut', 'heure_start', 'heure debut', 'heure_début', 'start']:
            if key in csv_headers_lower:
                mapping['Heure_Start'] = csv_headers_lower[key]
                break
        else:
            mapping['Heure_Start'] = None
        
        # Heure_End -> cherche "heure_end", "heure fin", "heure_fin", "end", puis "fin" en dernier recours
        for key in ['heure_end', 'heure fin', 'heure_fin', 'end']:
            if key in csv_headers_lower:
                mapping['Heure_End'] = csv_headers_lower[key]
                break
        else:
            # Si aucune colonne spécifique trouvée, on essaie "fin" (mais seulement si DR_arret n'a pas déjà pris "fin")
            if 'fin' in csv_headers_lower and mapping.get('DR_arret') != csv_headers_lower['fin']:
                mapping['Heure_End'] = csv_headers_lower['fin']
            else:
                mapping['Heure_End'] = None
        
        return mapping
    
    def _insert_trajet_row(self, cursor: sqlite3.Cursor, row_data: Dict[str, str], column_mapping: Dict[str, Optional[str]]):
        """
        Insère une ligne dans la table trajet.
        
        Args:
            cursor: Curseur SQLite
            row_data: Dictionnaire contenant les données de la ligne CSV
            column_mapping: Mapping des colonnes de la table trajet vers les colonnes CSV
        """
        # Fonction helper pour convertir en entier ou None
        def to_int(value):
            if not value or not str(value).strip():
                return None
            try:
                return int(float(str(value).replace(',', '.')))
            except (ValueError, TypeError):
                return None
        
        # Récupération des valeurs avec conversion appropriée
        num_ligne = to_int(row_data.get(column_mapping['Num_ligne'], '')) if column_mapping['Num_ligne'] else None
        num_trajet = to_int(row_data.get(column_mapping['Num_trajet'], '')) if column_mapping['Num_trajet'] else None
        variant = to_int(row_data.get(column_mapping['variant'], '')) if column_mapping['variant'] else None
        
        dp_arret = row_data.get(column_mapping['DP_arret'], '').strip() if column_mapping['DP_arret'] else ''
        dr_arret = row_data.get(column_mapping['DR_arret'], '').strip() if column_mapping['DR_arret'] else ''
        heure_start = row_data.get(column_mapping['Heure_Start'], '').strip() if column_mapping['Heure_Start'] else ''
        heure_end = row_data.get(column_mapping['Heure_End'], '').strip() if column_mapping['Heure_End'] else ''
        
        # Insertion dans la table trajet
        insert_sql = """
        INSERT INTO trajet (Num_ligne, Num_trajet, variant, DP_arret, DR_arret, Heure_Start, Heure_End)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(insert_sql, (
            num_ligne,
            num_trajet,
            variant,
            dp_arret if dp_arret else None,
            dr_arret if dr_arret else None,
            heure_start if heure_start else None,
            heure_end if heure_end else None
        ))


def main():
    """Point d'entrée principal de l'application."""
    # Création de la fenêtre principale
    if BOOTSTRAP_AVAILABLE:
        root = ttkb.Window(themename="cosmo")  # Thème moderne
    else:
        root = tk.Tk()
        # Style par défaut amélioré
        style = ttk.Style()
        style.theme_use("clam")
    
    # Création de l'application
    app = CSVVoyageManager(root)
    
    # Lancement de la boucle principale
    root.mainloop()


if __name__ == "__main__":
    main()

