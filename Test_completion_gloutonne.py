"""Tests de completion_gloutonne.py (aucune interface graphique requise).

La fonction de compatibilité réelle (entrainementsolveria.voyages_compatibles)
est remplacée par des fausses fonctions pour tester uniquement l'algorithme.
"""

from types import SimpleNamespace

from completion_gloutonne import (
    ResultatCompletion,
    completer_services,
    est_compatible,
    respecte_contraintes,
)


def voyage(num, debut, fin):
    return SimpleNamespace(num_voyage=num, hdebut=debut, hfin=fin)


def service(num, voyages=None, debut_max=None, fin_max=None):
    return SimpleNamespace(
        num_service=num, type_service="matin",
        voyages=list(voyages or []),
        heure_debut_max=debut_max, heure_fin_max=fin_max,
    )


def toujours_compatible(*args):
    return True


def jamais_compatible(*args):
    return False


# --- respecte_contraintes --------------------------------------------------

def test_sans_contrainte_tout_est_accepte():
    assert respecte_contraintes(voyage(1, 360, 420), None, None)


def test_voyage_avant_le_debut_est_refuse():
    assert not respecte_contraintes(voyage(1, 300, 360), 360, None)


def test_voyage_apres_la_fin_est_refuse():
    assert not respecte_contraintes(voyage(1, 800, 900), None, 840)


def test_voyage_dans_la_plage_est_accepte():
    assert respecte_contraintes(voyage(1, 360, 420), 300, 840)


def test_borne_a_zero_est_une_vraie_contrainte():
    # Une fin max à 0 (minuit) exclut tout voyage qui finit après
    assert not respecte_contraintes(voyage(1, 10, 20), None, 0)


def test_une_seule_borne_suffit():
    assert not respecte_contraintes(voyage(1, 300, 360), 360, None)
    assert not respecte_contraintes(voyage(1, 800, 900), None, 840)


# --- est_compatible --------------------------------------------------------

def test_service_vide_toujours_compatible():
    assert est_compatible(voyage(1, 360, 420), [], 5, 50, True, jamais_compatible)


def test_chevauchement_refuse_sans_appeler_la_fonction_externe():
    appels = []

    def espion(*args):
        appels.append(args)
        return True

    assert not est_compatible(voyage(1, 360, 420), [voyage(2, 390, 450)], 5, 50, True, espion)
    assert appels == []


def test_fonction_externe_decide_si_pas_de_chevauchement():
    existants = [voyage(2, 480, 540)]
    assert est_compatible(voyage(1, 360, 420), existants, 5, 50, True, toujours_compatible)
    assert not est_compatible(voyage(1, 360, 420), existants, 5, 50, True, jamais_compatible)


def test_ordre_des_arguments_voyage_precedent_puis_suivant():
    appels = []

    def espion(premier, second, *reste):
        appels.append((premier.num_voyage, second.num_voyage))
        return True

    # Candidat avant l'existant
    est_compatible(voyage(1, 360, 420), [voyage(2, 480, 540)], 5, 50, True, espion)
    # Candidat après l'existant
    est_compatible(voyage(3, 600, 660), [voyage(2, 480, 540)], 5, 50, True, espion)

    assert appels == [(1, 2), (2, 3)]


def test_parametres_transmis_a_la_fonction_externe():
    recus = []

    def espion(premier, second, voyages_service, bat_min, bat_max, verifier):
        recus.append((bat_min, bat_max, verifier))
        return True

    est_compatible(voyage(1, 360, 420), [voyage(2, 480, 540)], 7, 42, False, espion)
    assert recus == [(7, 42, False)]


# --- completer_services ----------------------------------------------------

def test_aucun_service_tout_reste():
    v1, v2 = voyage(1, 360, 420), voyage(2, 480, 540)
    resultat = completer_services([], [v1, v2], 5, 50, True, toujours_compatible)
    assert resultat.affectations == []
    assert resultat.restants == [v1, v2]


def test_aucun_voyage_rien_a_faire():
    resultat = completer_services([service(1)], [], 5, 50, True, toujours_compatible)
    assert resultat.nb_ajoutes == 0
    assert resultat.restants == []


def test_voyages_successifs_dans_le_meme_service():
    s1 = service(1)
    v1, v2 = voyage(1, 360, 420), voyage(2, 480, 540)
    resultat = completer_services([s1], [v2, v1], 5, 50, True, toujours_compatible)
    assert [(s.num_service, v.num_voyage) for s, v in resultat.affectations] == [(1, 1), (1, 2)]
    assert resultat.restants == []


def test_voyage_qui_chevauche_va_dans_le_service_suivant():
    s1, s2 = service(1), service(2)
    v1, v2, v3 = voyage(1, 360, 420), voyage(2, 390, 450), voyage(3, 480, 540)
    resultat = completer_services([s1, s2], [v1, v2, v3], 5, 50, True, toujours_compatible)

    par_service = {}
    for s, v in resultat.affectations:
        par_service.setdefault(s.num_service, []).append(v.num_voyage)

    assert par_service == {1: [1, 3], 2: [2]}
    assert resultat.restants == []


def test_voyage_hors_contraintes_reste_non_assigne():
    s1 = service(1, debut_max=360, fin_max=480)
    v_ok, v_trop_tard = voyage(1, 360, 420), voyage(2, 600, 660)
    resultat = completer_services([s1], [v_ok, v_trop_tard], 5, 50, True, toujours_compatible)
    assert [v.num_voyage for _, v in resultat.affectations] == [1]
    assert resultat.restants == [v_trop_tard]


def test_incompatibilite_externe_laisse_les_voyages_restants():
    s1 = service(1, voyages=[voyage(9, 300, 330)])
    v1 = voyage(1, 360, 420)
    resultat = completer_services([s1], [v1], 5, 50, True, jamais_compatible)
    assert resultat.affectations == []
    assert resultat.restants == [v1]


def test_les_services_ne_sont_pas_modifies():
    s1 = service(1)
    completer_services([s1], [voyage(1, 360, 420)], 5, 50, True, toujours_compatible)
    assert s1.voyages == []


def test_voyages_existants_du_service_sont_pris_en_compte():
    # V9 occupe déjà 360-420 : V1 (390-450) chevauche, donc refusé
    s1 = service(1, voyages=[voyage(9, 360, 420)])
    v1 = voyage(1, 390, 450)
    resultat = completer_services([s1], [v1], 5, 50, True, toujours_compatible)
    assert resultat.restants == [v1]


def test_resultat_nb_ajoutes():
    assert ResultatCompletion(affectations=[(1, 2), (3, 4)]).nb_ajoutes == 2