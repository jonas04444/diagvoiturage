import csv
import tkinter as tk
from tkinter import messagebox as msgbox, filedialog
import customtkinter as ctk
from pyexpat.errors import messages


class CSVimportvoyage:
    def __init__(self, root: tk.tk):
        self.root = root
        self.root.title("Gestionnaire de voyage CSV")
        self.root.geometry("1400x800")

        #donées
        self.csv_data = List[]
    def loa_csv(self):
        """ouvre une boite de dialogue pour selectionner le fichier CSv"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV",
            filetypes = [("Fichiers CSV", "*.csv"), ("tous les fichiers", "*.*")]
        )

        if file_path:
            self.loa_csv(file_path)

    def load_csv(self, file_path: str):
        """
        charge fichier CSV
        :param file_path:
        :return:
        """
        """liste des encodages (proposer par cursor)"""
        encodings = ['utf-8', 'utf-8-sig', 'windows-1252', 'iso-8859-1', 'latin1', 'cp1252']

        try:
            last_error = None
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        reader = csv.DictReader(f, delimiter=";")
                        self.csv_headers = reader.fieldnames or []
                        self.csv_data = list(reader)

                    break
                except UnicodeDecodeError as e:
                    last_error = e
                    continue
                except Exception as e:
                    raise e

            #vérif si encodage pas bon
            if last_error and not self.csv_data:
                raise UnicodeDecodeError(
                    last_error.encoding,
                    last_error.object,
                    last_error.start,
                    last_error.end,
                    f"Aucun encodage ne fonctionne. Essayé: {', '.join(encodings)}"
                )

            if not self.csv_data:
                msgbox.showwarning("Attention","Le fichier CSV est vide.")
                return

            """Reset des selection"""
            self.selectec_rows.clear()
            self.sort_reverse.clear()

            self.populate_table()

            """bouton export"""
            self.btn_export.config(state=tk.NORMAL)
            self.btn_save_trajet.config(state=tk.NORMAL)

            msgbox.showinfo("Succès", f"{len(self.csv_data)} lignes chargées avec succès.")

        except FileNotFoundError:
            msgbox.showerror("Erreur", f"Fichier non trouvé: {file_path}")

        except Exception as e:
            msgbox.showerror("Erreur", f"Erreur lors du chargement du CSV:\n{str(e)}")

    def populate_table(self):
        #supp des colonnes existantes
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")