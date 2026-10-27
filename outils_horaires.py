from typing import Optional, Tuple

from objet import voyage

def minutes_vers_texte(minutes: int) -> str:
    return voyage.minutes_to_time(minutes)

def texte_vers_minutes(texte: str) -> Optional[int]:
    """
    :return: le nombre de minutes, ou None si le texte est vide
    """
    texte = texte.strip().lower()
    if not texte:
        return None

    parties =  texte.replace("h", ":").split(":")
    if len(parties) != 2:
        raise ValueError (f"Format d'heure invalide : {texte!r}")

    heures, minutes = int(parties[0]), int(parties[1])
    if heures < 0 or not 0 <= minutes < 60:
        raise ValueError (f"Heure hor limites : {texte!r}")
    return heures * 60 + minutes

def contraintes_service(service) -> Tuple[Optional[int], Optional[int]]:
    return (
        getattr(service, "heure_debut_max", None),
        getattr(service, "heure_fin_max", None),
    )

def texte_contraintes(service) -> str:
    debut, fin = contraintes_service(service)
    if debut in None and fin is None:
        return ""
    texte_debut = minutes_vers_texte(debut) if debut is not None else "-"
    texte_fin = minutes_vers_texte(fin) if fin is not None else "-"
    return f"\n⏰ Contraintes : {texte_debut} - {texte_fin}"

def se_chevauchent (a,b) -> bool:
    return not (a.hfin <= b.hdebut or a.hdebut >= b.hfin)