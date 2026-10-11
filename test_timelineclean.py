"""Tests automatiques de TimelineVisuelle (à lancer avec pytest).

Nécessite un écran (ou xvfb sur un serveur) car on crée une vraie fenêtre.
"""

from types import SimpleNamespace

import customtkinter as ctk
import pytest

from timelineclean import TimelineVisuelle


def voyage(debut, fin, num=1, ligne="25"):
    return SimpleNamespace(
        num_voyage=num, num_ligne=ligne,
        hdebut=debut, hfin=fin,
        arret_debut="AAA", arret_fin="BBB",
    )


@pytest.fixture(scope="session")
def root():
    """Une seule fenêtre cachée pour toute la session de tests."""
    fenetre = ctk.CTk()
    fenetre.withdraw()
    yield fenetre
    fenetre.destroy()


@pytest.fixture
def timeline(root):
    """Un TimelineVisuelle neuf pour chaque test."""
    widget = TimelineVisuelle(root)
    widget.pack(fill="both", expand=True)
    root.update()
    yield widget
    widget.destroy()


# --- Chevauchement ------------------------------------------------------

def test_voyages_qui_se_chevauchent():
    assert TimelineVisuelle._se_chevauchent(voyage(360, 420), voyage(390, 450))


def test_voyages_consecutifs_ne_se_chevauchent_pas():
    # Le premier finit à 7h00, le second commence à 7h00 : pas de chevauchement
    assert not TimelineVisuelle._se_chevauchent(voyage(360, 420), voyage(420, 480))


def test_voyages_separes_ne_se_chevauchent_pas():
    assert not TimelineVisuelle._se_chevauchent(voyage(360, 420), voyage(600, 660))


# --- Répartition en lignes ---------------------------------------------

def test_repartition_liste_vide(timeline):
    assert timeline._repartir_voyages_sans_chevauchement([]) == []


def test_repartition_sans_chevauchement_une_seule_ligne(timeline):
    voyages = [voyage(360, 420), voyage(420, 480), voyage(600, 660)]
    lignes = timeline._repartir_voyages_sans_chevauchement(voyages)
    assert len(lignes) == 1
    assert len(lignes[0]) == 3


def test_repartition_avec_chevauchement_deux_lignes(timeline):
    voyages = [voyage(360, 420), voyage(390, 450)]
    lignes = timeline._repartir_voyages_sans_chevauchement(voyages)
    assert len(lignes) == 2


def test_repartition_trie_les_voyages_desordonnes(timeline):
    voyages = [voyage(600, 660, num=2), voyage(360, 420, num=1)]
    lignes = timeline._repartir_voyages_sans_chevauchement(voyages)
    assert [v.num_voyage for v in lignes[0]] == [1, 2]


# --- Conversions et couleurs --------------------------------------------

def test_heure_vers_x_debut_et_fin(timeline):
    width = 1000
    assert timeline._heure_vers_x(4 * 60, width) == timeline.MARGE_HORIZONTALE
    assert timeline._heure_vers_x(24 * 60, width) == width - timeline.MARGE_HORIZONTALE


def test_minutes_vers_texte():
    assert TimelineVisuelle._minutes_vers_texte(485) == "08h05"
    assert TimelineVisuelle._minutes_vers_texte(0) == "00h00"


def test_couleur_connue_et_inconnue(timeline):
    assert timeline._get_color("25") == "#4ECDC4"
    assert timeline._get_color("ligne_inconnue") == timeline.COULEUR_PAR_DEFAUT


# --- Dessin (vérifie juste que ça ne plante pas) -------------------------

def test_rafraichir_sans_service_ne_plante_pas(timeline):
    timeline.rafraichir()


def test_rafraichir_avec_service_dessine_des_elements(timeline):
    timeline.set_service(SimpleNamespace(voyages=[voyage(360, 420), voyage(390, 450)]))
    assert len(timeline.canvas.find_all()) > 0