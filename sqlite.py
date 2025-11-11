import csv
import sqlite3
import tkinter.messagebox as msgbox
from tkinter import filedialog

from gestion_contrainte import time_to_minutes

def add_line(donnees_ligne):
    conn = sqlite3.connect("dbdiaggrantt.db")
    cur = conn.cursor()

    for version in donnees_ligne:
        cur.execute("""
                    SELECT 1 FROM Version_ligne
                    WHERE num_ligne = ? AND Variante = ?
                """, (version["num_ligne"], version["Variante"]))

        existe = cur.fetchone()

        if existe:
            msgbox.showwarning(
                "Doublon détecté",
                f"La ligne {version['num_ligne']} avec la version {version['Variante']} existe déjà."
            )
        else:
            cur.execute("""
                    INSERT INTO Version_ligne (
                        num_ligne, Variante
                    ) VALUES (?, ?)
                """, (
                    version["num_ligne"],
                    version["Variante"]
                ))
            msgbox.showinfo(
                "Ligne et variante",
                f"La ligne {version['num_ligne']} avec la version {version['Variante']} a été ajoutée."
            )

    conn.commit()
    conn.close()


def add_trajet(donnees_trajet):
    conn = sqlite3.connect("dbdiaggrantt.db")
    cur = conn.cursor()

    for trajet in donnees_trajet:
        # Vérifier que la ligne existe
        cur.execute("""
            SELECT num_ligne FROM Version_ligne
            WHERE num_ligne = ? AND Variante = ?
        """, (trajet["Num_ligne"], trajet["variant"]))

        result = cur.fetchone()

        if not result:
            msgbox.showerror(
                "Ligne inconnue",
                f"❌ La ligne {trajet['Num_ligne']} avec variante {trajet['variant']} n'existe pas."
            )
            continue  # Passe au trajet suivant

        num_ligne = result[0]

        # Vérifier si le trajet existe déjà
        cur.execute("""
            SELECT 1 FROM trajet
            WHERE Num_ligne = ? AND Num_trajet = ? AND variant = ?
        """, (
            num_ligne,
            trajet["Num_trajet"],
            trajet["variant"]
        ))

        existe = cur.fetchone()

        if existe:
            msgbox.showwarning(
                "Doublon détecté",
                f"Le trajet ligne {trajet['Num_ligne']} numéro {trajet['Num_trajet']} (variant {trajet['variant']}) existe déjà."
            )
        else:
            # Insertion du trajet
            cur.execute("""
                INSERT INTO trajet (
                    Num_ligne, Num_trajet, variant,
                    DP_arret, DR_arret, Heure_Start, Heure_End
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                num_ligne,
                trajet["Num_trajet"],
                trajet["variant"],
                trajet["DP_arret"],
                trajet["DR_arret"],
                trajet["Heure_Start"],
                trajet["Heure_End"]
            ))
            msgbox.showinfo("Ajout réussi", f"✔️ Trajet {trajet['Num_trajet']} ajouté.")

    conn.commit()
    conn.close()

def add_lieux(donnees_lieux):
    conn = sqlite3.connect("dbdiaggrantt.db")
    cur = conn.cursor()

    for lieux in donnees_lieux:
        cur.execute("""
                    SELECT 1 FROM lieux
                    WHERE id_lieux = ? 
            """,(
            lieux["id_lieux"],
            ))

        existe = cur.fetchone()

        if existe:
            msgbox.showwarning(
                "Doublon détecté",
                f"Le lieux {lieux['id_lieux']} existe déjà"
            )
        else:
            cur.execute("""
                        INSERT INTO lieux (
                            id_lieux, commune, description, zone
                        ) VALUES (?,?,?,?)
                    """,(
                    lieux["id_lieux"],
                    lieux["commune"],
                    lieux["description"],
                    lieux["zone"]
                ))
            msgbox.showinfo(
                "bien éffectué",
                f"le lieux {lieux['id_lieux']} est créé."
            )
    conn.commit()
    conn.close()

def verif_lieux(test_lieux):
    conn = sqlite3.connect("dbdiaggrantt.db")
    cur = conn.cursor()

    cur.execute("""
                SELECT 1 FROM lieux
                WHERE id_lieux = ?
        """,(
        test_lieux,
        ))
    existe = cur.fetchone()
    if not existe:
        msgbox.showwarning("lieu introuvebale","Ce lieux n'existe pas")
    conn.close()

def get_trips_from_database(num_ligne=None):
    """
    Récupère les trajets depuis la base de données.

    Args:
        num_ligne: Numéro de ligne à filtrer (optionnel)

    Returns:
        list: Liste des trajets formatés pour le solver
    """
    try:
        conn = sqlite3.connect('votre_database.db')
        cursor = conn.cursor()

        query = """
            SELECT 
                t.Heure_Start,
                t.Heure_End,
                l1.nom_lieu as lieu_depart,
                l2.nom_lieu as lieu_arrivee,
                t.id_trajet,
                t.Num_ligne,
                t.Num_trajet,
                t.variant
            FROM trajet t
            INNER JOIN lieux l1 ON t.DP_arret = l1.id_lieux
            INNER JOIN lieux l2 ON t.DR_arret = l2.id_lieux
            WHERE 1=1
        """

        params = []

        if num_ligne is not None:
            query += " AND t.Num_ligne = ?"
            params.append(num_ligne)

        query += " ORDER BY t.Heure_Start"

        cursor.execute(query, params)

        trips = []
        for row in cursor.fetchall():
            trips.append({
                "start": time_to_minutes(row[0]),  # Heure_Start
                "end": time_to_minutes(row[1]),  # Heure_End
                "from": row[2],  # lieu_depart (nom)
                "to": row[3],  # lieu_arrivee (nom)
                "id_trajet": row[4],  # id_trajet
                "num_ligne": row[5],  # Num_ligne
                "num_trajet": row[6],  # Num_trajet
                "variant": row[7]  # variant
            })

        conn.close()

        if not trips:
            raise ValueError("Aucun trajet trouvé dans la base de données")

        return trips

    except sqlite3.Error as e:
        raise Exception(f"Erreur base de données: {str(e)}")


def get_lignes_from_db():
    """Récupère toutes les lignes disponibles depuis la base de données"""
    try:
        conn = sqlite3.connect("dbdiaggrantt.db")
        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT num_ligne, Variante 
            FROM Version_ligne 
            ORDER BY num_ligne, Variante
        """)

        lignes = cur.fetchall()
        conn.close()

        # Formatage pour l'affichage : "Ligne X - Variante Y"
        return [f"Ligne {ligne[0]} - Variante {ligne[1]}" for ligne in lignes]

    except sqlite3.Error as e:
        msgbox.showerror("Erreur DB", f"Impossible de récupérer les lignes: {str(e)}")
        return ["Aucune ligne disponible"]

def get_lieux_from_db():
    """récupère tout les lieux dispo dans la db"""
    try:
        conn = sqlite3.connect("dbdiaggrantt.db")
        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT id_lieux, description
            FROM lieux
            ORDER BY id_lieux, description
        """)

        lieux = cur.fetchall()
        conn.close()

        return [f"{lieu[0]} - {lieu[1]}" for lieu in lieux]

    except sqlite3.Error as e:
        msgbox.showerror("Erreur DB", f"Impossible de récupérer les lieux")
        return ["Aucun lieu disponible"]

def charger_csv():
    """Ouvre une fenêtre pour sélectionner et charger un fichier CSV"""
    try:
        fichier = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )

        if not fichier:
            return

        with open(fichier, 'r', encoding='utf-8') as f:
            lecteur = csv.DictReader(f, delimiter=';')  # ✅ Point-virgule

            donnees = []
            for ligne in lecteur:
                donnees.append(ligne)

            print(f"✅ {len(donnees)} lignes chargées depuis {fichier}")
            print(f"Colonnes disponibles: {list(donnees[0].keys()) if donnees else 'Aucune'}")  # ✅ Corrigé

            msgbox.showinfo("Succès", f"{len(donnees)} lignes chargées avec succès")

    except Exception as e:
        msgbox.showerror("Erreur", f"Impossible de charger le fichier: {str(e)}")

#add_trajet(donnees_trajet)
#add_lieux(donnees_lieux)
#test = "CHMON"
#verif_lieux(test)