"""Tests de outils_horaires.py (aucune interface graphique requise)."""

from types import SimpleNamespace

import pytest

from outils_horaires import (
    contraintes_service,
    minutes_vers_texte,
    se_chevauchent,
    texte_contraintes,
    texte_vers_minutes,
)


def voyage(debut, fin):
    return SimpleNamespace(hdebut=debut, hfin=fin)


# --- texte_vers_minutes ----------------------------------------------------

@pytest.mark.parametrize("texte, attendu", [
    ("14:30", 14 * 60 + 30),
    ("14h30", 14 * 60 + 30),
    ("14H30", 14 * 60 + 30),
    ("  08:05  ", 8 * 60 + 5),
    ("00:00", 0),
    ("4:00", 240),
])
def test_texte_vers_minutes_valide(texte, attendu):
    assert texte_vers_minutes(texte) == attendu


@pytest.mark.parametrize("texte", ["", "   "])
def test_texte_vide_donne_none(texte):
    assert texte_vers_minutes(texte) is None


def test_minuit_n_est_pas_confondu_avec_vide():
    assert texte_vers_minutes("00:00") is not None


@pytest.mark.parametrize("texte", ["abc", "14", "14h", "14:60", "-1:30", "14:30:00", "14:xx"])
def test_texte_vers_minutes_invalide(texte):
    with pytest.raises(ValueError):
        texte_vers_minutes(texte)


# --- minutes_vers_texte ----------------------------------------------------

def test_minutes_vers_texte_contient_heures_et_minutes():
    # Le format exact dépend de objet.voyage.minutes_to_time : on vérifie l'essentiel
    texte = minutes_vers_texte(8 * 60 + 5)
    assert "08" in texte and "05" in texte


# --- contraintes_service ---------------------------------------------------

def test_contraintes_service_absentes():
    assert contraintes_service(SimpleNamespace()) == (None, None)


def test_contraintes_service_presentes():
    service = SimpleNamespace(heure_debut_max=240, heure_fin_max=840)
    assert contraintes_service(service) == (240, 840)


def test_contraintes_service_partielles():
    assert contraintes_service(SimpleNamespace(heure_fin_max=600)) == (None, 600)


# --- texte_contraintes -----------------------------------------------------

def test_texte_contraintes_vide_si_aucune():
    assert texte_contraintes(SimpleNamespace(heure_debut_max=None, heure_fin_max=None)) == ""


def test_texte_contraintes_avec_une_seule_borne():
    texte = texte_contraintes(SimpleNamespace(heure_debut_max=None, heure_fin_max=840))
    assert "Contraintes" in texte
    assert "—" in texte


def test_texte_contraintes_avec_minuit():
    # 0 est une vraie contrainte, pas une absence de contrainte
    texte = texte_contraintes(SimpleNamespace(heure_debut_max=0, heure_fin_max=None))
    assert texte != ""


# --- se_chevauchent --------------------------------------------------------

def test_chevauchement():
    assert se_chevauchent(voyage(360, 420), voyage(390, 450))


def test_voyages_consecutifs_ne_se_chevauchent_pas():
    assert not se_chevauchent(voyage(360, 420), voyage(420, 480))


def test_voyages_separes():
    assert not se_chevauchent(voyage(360, 420), voyage(600, 660))


def test_chevauchement_est_symetrique():
    a, b = voyage(360, 420), voyage(390, 450)
    assert se_chevauchent(a, b) == se_chevauchent(b, a)


def test_voyage_inclus_dans_un_autre():
    assert se_chevauchent(voyage(360, 600), voyage(400, 450))