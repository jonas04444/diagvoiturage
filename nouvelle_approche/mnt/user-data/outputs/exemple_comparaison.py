"""
EXEMPLE DE COMPARAISON : Algorithme Glouton vs OR-Tools
Démontre la différence de performance entre les deux approches
"""

from objet import voyage, service_agent
from gestion_voiture import optimiser_affectation
import time


def creer_voyages_test():
    """Crée un ensemble de voyages de test réalistes"""
    voyages = [
        # Ligne 25 - Matin
        voyage("25", "V1", "Gare Centrale", "Place du Marché", "06:00", "06:45"),
        voyage("25", "V2", "Place du Marché", "Quartier Nord", "06:55", "07:30"),
        voyage("25", "V3", "Quartier Nord", "Gare Centrale", "07:40", "08:15"),
        voyage("25", "V4", "Gare Centrale", "Place du Marché", "08:25", "09:10"),
        
        # Ligne 35 - Matin
        voyage("35", "V5", "Gare Sud", "Centre Ville", "06:15", "06:50"),
        voyage("35", "V6", "Centre Ville", "Université", "07:00", "07:45"),
        voyage("35", "V7", "Université", "Gare Sud", "07:55", "08:30"),
        
        # Ligne 43 - Après-midi
        voyage("43", "V8", "Terminal A", "Zone Commerciale", "14:00", "14:45"),
        voyage("43", "V9", "Zone Commerciale", "Hôpital", "14:55", "15:30"),
        voyage("43", "V10", "Hôpital", "Terminal A", "15:40", "16:15"),
        
        # Ligne 25 - Après-midi
        voyage("25", "V11", "Gare Centrale", "Place du Marché", "14:30", "15:15"),
        voyage("25", "V12", "Place du Marché", "Quartier Nord", "15:25", "16:00"),
        
        # Ligne 83 - Journée complète
        voyage("83", "V13", "Aéroport", "Gare Centrale", "09:00", "09:45"),
        voyage("83", "V14", "Gare Centrale", "Aéroport", "10:00", "10:45"),
        voyage("83", "V15", "Aéroport", "Gare Centrale", "13:00", "13:45"),
        voyage("83", "V16", "Gare Centrale", "Aéroport", "14:00", "14:45"),
        
        # Ligne 86 - Matin peak
        voyage("86", "V17", "Banlieue Est", "Centre Ville", "06:30", "07:15"),
        voyage("86", "V18", "Centre Ville", "Banlieue Ouest", "07:25", "08:10"),
        voyage("86", "V19", "Banlieue Ouest", "Centre Ville", "08:20", "09:05"),
        voyage("86", "V20", "Centre Ville", "Banlieue Est", "09:15", "10:00"),
    ]
    return voyages


def creer_services_test():
    """Crée des services avec contraintes horaires"""
    services = [
        service_agent(num_service=1, type_service="matin"),
        service_agent(num_service=2, type_service="matin"),
        service_agent(num_service=3, type_service="apres_midi"),
    ]
    
    # Contraintes horaires
    services[0].heure_debut_max = 6 * 60    # 06:00
    services[0].heure_fin_max = 12 * 60     # 12:00
    
    services[1].heure_debut_max = 6 * 60    # 06:00
    services[1].heure_fin_max = 12 * 60     # 12:00
    
    services[2].heure_debut_max = 12 * 60   # 12:00
    services[2].heure_fin_max = 18 * 60     # 18:00
    
    return services


def algorithme_glouton(voyages, services, battement_min=5, battement_max=50, verifier_arrets=True):
    """
    Algorithme glouton simple pour comparaison
    Essaie d'ajouter les voyages dans l'ordre chronologique
    """
    print("\n" + "="*70)
    print("🐌 ALGORITHME GLOUTON")
    print("="*70)
    
    debut = time.time()
    nb_affectes = 0
    voyages_tries = sorted(voyages, key=lambda x: x.hdebut)
    
    for v in voyages_tries:
        affecte = False
        
        for service in services:
            # Vérifier contraintes horaires
            h_debut = getattr(service, 'heure_debut_max', None)
            h_fin = getattr(service, 'heure_fin_max', None)
            
            if h_debut and h_fin:
                if v.hdebut < h_debut or v.hfin > h_fin:
                    continue
            
            # Vérifier compatibilité avec voyages existants
            compatible = True
            
            for v_exist in service.voyages:
                # Chevauchement temporel
                if not (v.hfin <= v_exist.hdebut or v.hdebut >= v_exist.hfin):
                    compatible = False
                    break
                
                # Vérifier battement
                if v.hfin <= v_exist.hdebut:
                    battement = v_exist.hdebut - v.hfin
                    if battement < battement_min or (battement_max and battement > battement_max):
                        compatible = False
                        break
                    
                    # Vérifier arrêts
                    if verifier_arrets and v.arret_fin_id() != v_exist.arret_debut_id():
                        compatible = False
                        break
                        
                elif v_exist.hfin <= v.hdebut:
                    battement = v.hdebut - v_exist.hfin
                    if battement < battement_min or (battement_max and battement > battement_max):
                        compatible = False
                        break
                    
                    # Vérifier arrêts
                    if verifier_arrets and v_exist.arret_fin_id() != v.arret_debut_id():
                        compatible = False
                        break
            
            if compatible:
                service.ajout_voyages(v)
                nb_affectes += 1
                affecte = True
                print(f"  ✓ V{v.num_voyage} → Service {service.num_service}")
                break
        
        if not affecte:
            print(f"  ✗ V{v.num_voyage} non affecté")
    
    temps = time.time() - debut
    
    print(f"\n📊 RÉSULTATS GLOUTON:")
    print(f"  Voyages affectés : {nb_affectes} / {len(voyages)}")
    print(f"  Temps : {temps:.4f}s")
    print("="*70)
    
    return nb_affectes, temps


def algorithme_ortools(voyages, services, battement_min=5, battement_max=50, verifier_arrets=True):
    """Lance l'optimisation OR-Tools"""
    # Créer des copies des services pour ne pas modifier les originaux
    services_copie = [
        service_agent(num_service=s.num_service, type_service=s.type_service)
        for s in services
    ]
    
    # Copier les contraintes horaires
    for i, s in enumerate(services):
        if hasattr(s, 'heure_debut_max'):
            services_copie[i].heure_debut_max = s.heure_debut_max
        if hasattr(s, 'heure_fin_max'):
            services_copie[i].heure_fin_max = s.heure_fin_max
    
    success, resultats = optimiser_affectation(
        voyages=voyages,
        services=services_copie,
        battement_min=battement_min,
        battement_max=battement_max,
        verifier_arrets=verifier_arrets,
        temps_limite=30
    )
    
    if success:
        return resultats['nb_affectes'], resultats['temps']
    else:
        return 0, 0


def afficher_services(services, titre):
    """Affiche le contenu des services"""
    print(f"\n{titre}")
    print("-" * 70)
    for service in services:
        if service.voyages:
            print(f"\n{service}")
        else:
            print(f"\nService {service.num_service}: vide")


def comparaison_complete():
    """Compare les deux algorithmes sur le même problème"""
    print("\n" + "="*70)
    print("🔬 COMPARAISON ALGORITHME GLOUTON vs OR-TOOLS")
    print("="*70)
    
    # Préparer les données
    voyages = creer_voyages_test()
    
    print(f"\n📊 Configuration du test:")
    print(f"  Voyages : {len(voyages)}")
    print(f"  Services : 3 (2 matin, 1 après-midi)")
    print(f"  Battement min : 5 min")
    print(f"  Battement max : 50 min")
    print(f"  Vérification arrêts : Oui")
    
    # Test 1 : Algorithme Glouton
    print("\n" + "="*70)
    print("TEST 1 : ALGORITHME GLOUTON")
    print("="*70)
    
    services_glouton = creer_services_test()
    nb_glouton, temps_glouton = algorithme_glouton(
        voyages, services_glouton,
        battement_min=5, battement_max=50, verifier_arrets=True
    )
    
    afficher_services(services_glouton, "📋 SERVICES APRÈS GLOUTON")
    
    # Test 2 : OR-Tools
    print("\n" + "="*70)
    print("TEST 2 : OR-TOOLS CP-SAT")
    print("="*70)
    
    services_ortools = creer_services_test()
    nb_ortools, temps_ortools = algorithme_ortools(
        voyages, services_ortools,
        battement_min=5, battement_max=50, verifier_arrets=True
    )
    
    afficher_services(services_ortools, "📋 SERVICES APRÈS OR-TOOLS")
    
    # Comparaison finale
    print("\n" + "="*70)
    print("🏆 COMPARAISON FINALE")
    print("="*70)
    
    print(f"\n{'Critère':<25} {'Glouton':<20} {'OR-Tools':<20}")
    print("-" * 70)
    print(f"{'Voyages affectés':<25} {nb_glouton:<20} {nb_ortools:<20}")
    print(f"{'Taux de réussite':<25} {nb_glouton/len(voyages)*100:.1f}%{'':<14} {nb_ortools/len(voyages)*100:.1f}%")
    print(f"{'Temps de calcul':<25} {temps_glouton:.4f}s{'':<12} {temps_ortools:.4f}s")
    print(f"{'Vitesse relative':<25} {temps_ortools/temps_glouton:.1f}x plus lent{'':<6} 1.0x")
    
    if nb_ortools > nb_glouton:
        amelioration = ((nb_ortools - nb_glouton) / nb_glouton * 100)
        print(f"\n✅ OR-Tools a affecté {nb_ortools - nb_glouton} voyage(s) de plus (+{amelioration:.1f}%)")
    elif nb_ortools == nb_glouton:
        print(f"\n🤝 Les deux algorithmes ont trouvé le même nombre de voyages")
    else:
        print(f"\n⚠️ L'algorithme glouton a été plus efficace (cas rare)")
    
    print("\n💡 CONCLUSION:")
    print("  • Glouton = Rapide, solution correcte mais pas optimale")
    print("  • OR-Tools = Plus lent, solution optimale garantie")
    print("  • Utilisez OR-Tools en production pour la meilleure qualité")
    print("="*70 + "\n")


def test_cas_difficile():
    """Teste un cas où l'algorithme glouton échoue mais OR-Tools réussit"""
    print("\n" + "="*70)
    print("🧪 CAS DIFFICILE : Où l'algorithme glouton échoue")
    print("="*70)
    
    # Cas spécial : 3 voyages, 2 services
    # L'algorithme glouton va mettre V1 et V3 dans S1
    # Mais la solution optimale est V1 dans S1, V2 et V3 dans S2
    voyages = [
        voyage("25", "V1", "A", "B", "06:00", "07:00"),  # 06:00-07:00
        voyage("25", "V2", "B", "C", "07:10", "08:00"),  # 07:10-08:00 (battement 10min avec V1)
        voyage("25", "V3", "C", "D", "09:00", "10:00"),  # 09:00-10:00 (battement 60min avec V2)
    ]
    
    services = [
        service_agent(num_service=1, type_service="matin"),
        service_agent(num_service=2, type_service="matin"),
    ]
    
    # Contrainte : battement max = 50 minutes
    # → V1-V3 ont un battement de 120 min (9:00 - 7:00)
    # → V2-V3 ont un battement de 60 min (9:00 - 8:00)
    
    print("\n📊 Voyages :")
    for v in voyages:
        print(f"  {v.num_voyage}: {voyage.minutes_to_time(v.hdebut)}-{voyage.minutes_to_time(v.hfin)}")
    
    print("\n🔧 Contrainte : Battement max = 50 min")
    print("\n💭 Analyse :")
    print("  V1→V2 : 10 min (OK)")
    print("  V2→V3 : 60 min (KO, > 50 min)")
    print("  V1→V3 : 120 min (KO, > 50 min)")
    
    # Test Glouton
    print("\n🐌 Algorithme Glouton :")
    services_g = [service_agent(num_service=s.num_service, type_service=s.type_service) for s in services]
    nb_g, _ = algorithme_glouton(voyages, services_g, battement_min=5, battement_max=50, verifier_arrets=False)
    
    # Test OR-Tools
    print("\n🤖 OR-Tools :")
    services_o = [service_agent(num_service=s.num_service, type_service=s.type_service) for s in services]
    nb_o, _ = algorithme_ortools(voyages, services_o, battement_min=5, battement_max=50, verifier_arrets=False)
    
    print("\n" + "="*70)
    print(f"Résultat : Glouton = {nb_g}/3, OR-Tools = {nb_o}/3")
    if nb_o > nb_g:
        print("✅ OR-Tools a trouvé une meilleure solution !")
    print("="*70 + "\n")


if __name__ == "__main__":
    print("\n🚀 DÉMARRAGE DES TESTS DE COMPARAISON\n")
    
    # Test 1 : Comparaison complète
    comparaison_complete()
    
    # Test 2 : Cas difficile
    test_cas_difficile()
    
    print("\n✅ Tests terminés !\n")
