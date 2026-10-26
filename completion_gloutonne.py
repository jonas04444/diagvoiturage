import logging
from dataclasses import dataclass, field
from typing import Callable, List, Tuple, Optional

import objet
from entrainementsolveria import voyages_compatibles
from outils_horaires import contraintes_service, minutes_vers_texte, se_chevauchent

logger = logging.getLogger(__name__)

@dataclass
class ResultatCompletion:
    affectations: List[tuple[objet, objet]] = field(default_factory=list)
    restants: List[objet] = field(default_factory=list)

    @property
    def nb_ajoutes(self) -> int:
        return len(self.affectations)

def respecte_contrainte(v, debut_max: Optional[int], fin_max: Optional[int]) -> bool:
    if debut_max is not None and v.hdebut < debut_max:
        return False
    if fin_max is not None and v.hfint > fin_max:
        return False
    return True

def est_compatible(v, voyage_service, battement_min, battement_max, verifier_arrets,
                   fonction_compatibilite: Callable = voyages_compatibles) -> bool:
    """
    Args:
         v : Voyage candidat
         voyage_service : Voyage déjà présents dans le service
         battement_min / battement_max: battement autorisés entre deux voyages
         verifier_arrets : active la vérification de chohérence des arrêts
         fonction_compatibilite : Fonction de compatibilité des deux voyages
    """
    for existant in voyage_service:
        if se_chevauchent(v, existant):
            return False

        if v.hfin <= existant.hdebut:
            premier, second = v, existant
        else:
            premier, second = existant, v

        if not fonction_compatibilite(
            premier, second, voyage_service, battement_min, battement_max, verifier_arrets
        ):
            return False
    return True

def completer_services(services, voyages_non_assignes, battement_min, battement_max, verifier_arrets,
                       fonction_compatibilite: Callable = voyages_compatibles) -> ResultatCompletion:
    restants = sorted(voyages_non_assignes, key=lambda v: v.hdebut)
    resultat = ResultatCompletion()

    for service in services:
        debut_max , fin_max = contraintes_service(service)
        voyages_service = list(service.voyages)
        logger.info("Service %s (%s)...", service.num_service, service.type_service)

        for v in list(restants):
            if not respecte_contrainte(v, debut_max, fin_max):
                continue
            if not est_compatible(v, voyages_service, battement_min, battement_max, verifier_arrets,
                                  fonction_compatibilite):
                continue

            resultat.affectations.append((service, v))
            voyages_service.append(v)
            restants.remove(v)
            logger.info(
                "   V%s retenu (%s-%s)",
                v.num_voyage, minutes_vers_texte(v.hdebut), minutes_vers_texte(v.hfin)
            )

    resultat.restants = restants
    logger.info("Total : %d affecté(s), %d restant(s)", resultat.nb_ajoutes, len(restants))
    return resultat