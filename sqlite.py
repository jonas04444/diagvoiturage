import sqlite3
import tkinter.messagebox as msgbox

def add_line(donnees_ligne):
    conn = sqlite3.connect("dbdiaggrantt.db")
    cur =  conn.cursor()

    for version in donnees_ligne:
        cur.execute("""
                    SELECT 1 FROM Version_linge
                    WHERE num_ligne = ? AND Version_ligne = ?
                """, (version["num_ligne"], version["Version_ligne"]))

        existe = cur.fetchone()

        if existe:
            msgbox.showwarning(
                "Doublon détecté",
                f"La ligne {version['num_ligne']} avec la version {version['Version_ligne']} existe déjà."
            )
        else:
            cur.execute("""
                    INSERT INTO Version_linge (
                        num_ligne, Version_ligne
                    ) VALUES (?, ?)
                """, (
                    version["num_ligne"],
                    version["Version_ligne"]
                ))

    conn.commit()
    conn.close()

def add_trajet(donnees_trajet):
    conn = sqlite3.connect("dbdiaggrantt.db")
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    for trajet in donnees_trajet:
        cur.execute("""
            SELECT id_version FROM Version_ligne
            WHERE num_ligne = ? AND Variante = ?
        """, (trajet["Num_ligne"], trajet["variante"]))
        result = cur.fetchone()

        if not result:
            msgbox.showerror("Ligne inconnue", f"❌ La ligne {trajet['Num_ligne']} avec variante {trajet['variante']} n'existe pas.")
        else:
            id_version_ligne = result[0]

        cur.execute("""
            SELECT 1 FROM trajet
            WHERE Num_ligne = ? AND Num_trajet = ? AND variante = ?
        """, (
            id_version_ligne,
            trajet["Num_trajet"],
            trajet["variante"]
        ))

        existe = cur.fetchone()

        if existe:
            msgbox.showwarning(
                "Doublon détecté",
                f"Le trajet ligne {trajet['Num_ligne']} numéro {trajet['Num_trajet']} (variant {trajet['variant']}) existe déjà."
            )
        else:
            cur.execute("""
                INSERT INTO trajet (
                    Num_ligne, Num_trajet,
                    DP_arret, DR_arret, Duree
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                id_version_ligne,
                trajet["Num_trajet"],
                trajet["DP_arret"],
                trajet["DR_arret"],
                trajet["Duree"]
            ))
            msgbox.showinfo("Ajout réussi", f"✔️ Trajet ajouté.")

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
            msgbox.showinfo("bien éffectué")
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

donnees_trajet = [
    {
        "Num_ligne": 63,
        "Num_trajet": 1,
        "variante": 1,
        "DP_arret": "CTLEE",
        "DR_arret": "CTLAA",
        "Duree": 50
    }
]
donnees_lieux = [
    {
        "id_lieux" : "CHMON",
        "commune" : "Charleroi",
        "description" : "route de mons",
        "zone" : 1
    }
]
#add_trajet(donnees_trajet)
#add_lieux(donnees_lieux)
#test = "CHMON"
#verif_lieux(test)