"""
Complétion automatique des services par algorithme glouton.

Ce module ne dépend ni de Tkinter ni de CustomTkinter et ne modifie aucun
service : il calcule les affectations et les retourne. C'est à l'appelant
(l'interface) de les appliquer. Cela rend l'algorithme facile à tester et
à réutiliser ailleurs dans le projet.

La fonction qui décide si deux voyages consécutifs sont compatibles est
importée seulement quand elle est utilisée (ou fournie par l'appelant),
pour que ce module reste importable même si le solveur est indisponible.
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from outils_horaires import contraintes_service, minutes_vers_texte, se_chevauchent

logger = logging.getLogger(__name__)


def _charger_fonction_compatibilite() -> Callable:
    """Importe `voyages_compatibles` depuis entrainementsolveria à la demande."""
    try:
        from entrainementsolveria import voyages_compatibles
    except ImportError as erreur:
        raise ImportError(
            "Impossible d'importer 'voyages_compatibles' depuis entrainementsolveria.py : "
            "vérifiez que cette fonction existe et que son nom est exact."
        ) from erreur
    return voyages_compatibles


@dataclass
class ResultatCompletion:
    """Résultat d'une complétion automatique.

    Attributes:
        affectations: Liste de (service, voyage) dans l'ordre d'affectation.
        restants: Voyages qui n'ont pu être placés dans aucun service.
    """
    affectations: List[Tuple[object, object]] = field(default_factory=list)
    restants: List[object] = field(default_factory=list)

    @property
    def nb_ajoutes(self) -> int:
        return len(self.affectations)


def respecte_contraintes(v, debut_max: Optional[int], fin_max: Optional[int]) -> bool:
    """Vérifie qu'un voyage tient dans la plage horaire d'un service.

    Une borne à None signifie « pas de contrainte » ; la valeur 0 (minuit)
    est bien traitée comme une contrainte.
    """
    if debut_max is not None and v.hdebut < debut_max:
        return False
    if fin_max is not None and v.hfin > fin_max:
        return False
    return True


def est_compatible(v, voyages_service, battement_min, battement_max, verifier_arrets,
                   fonction_compatibilite: Optional[Callable] = None) -> bool:
    """Vérifie qu'un voyage est compatible avec tous ceux déjà dans le service.

    Args:
        v: Voyage candidat.
        voyages_service: Voyages déjà présents dans le service.
        battement_min / battement_max: Battements autorisés entre deux voyages.
        verifier_arrets: Active la vérification de cohérence des arrêts.
        fonction_compatibilite: Fonction de compatibilité de deux voyages
            consécutifs. Si None, `entrainementsolveria.voyages_compatibles`
            est importée à la demande. Injectable pour les tests.

    Raises:
        ImportError: si la fonction par défaut est introuvable.
    """
    for existant in voyages_service:
        if se_chevauchent(v, existant):
            return False

        if fonction_compatibilite is None:
            fonction_compatibilite = _charger_fonction_compatibilite()

        # Pas de chevauchement : l'un précède forcément l'autre
        if v.hfin <= existant.hdebut:
            premier, second = v, existant
        else:
            premier, second = existant, v

        if not fonction_compatibilite(
            premier, second, voyages_service,
            battement_min, battement_max, verifier_arrets,
        ):
            return False
    return True


def completer_services(services, voyages_non_assignes, battement_min,
                       battement_max, verifier_arrets,
                       fonction_compatibilite: Optional[Callable] = None) -> ResultatCompletion:
    """Affecte glouton les voyages non assignés aux services existants.

    Les voyages sont pris dans l'ordre chronologique ; pour chaque service,
    on ajoute tous les voyages qui respectent ses contraintes horaires et
    sont compatibles avec ceux déjà présents.

    Les services passés en argument ne sont PAS modifiés.

    Returns:
        Un ResultatCompletion (affectations + voyages restants).

    Raises:
        ImportError: si la fonction de compatibilité par défaut est introuvable.
    """
    restants = sorted(voyages_non_assignes, key=lambda v: v.hdebut)
    resultat = ResultatCompletion()

    for service in services:
        debut_max, fin_max = contraintes_service(service)
        voyages_service = list(service.voyages)
        logger.info("Service %s (%s)...", service.num_service, service.type_service)

        for v in list(restants):
            if not respecte_contraintes(v, debut_max, fin_max):
                continue
            if not est_compatible(v, voyages_service, battement_min, battement_max,
                                  verifier_arrets, fonction_compatibilite):
                continue

            resultat.affectations.append((service, v))
            voyages_service.append(v)
            restants.remove(v)
            logger.info(
                "  V%s retenu (%s-%s)",
                v.num_voyage, minutes_vers_texte(v.hdebut), minutes_vers_texte(v.hfin),
            )

    resultat.restants = restants
    logger.info("Total : %d affecté(s), %d restant(s)", resultat.nb_ajoutes, len(restants))
    return resultat