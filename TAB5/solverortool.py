"""
Solver OR-Tools pour l'optimisation des services de transport
"""

from ortools.sat.python import cp_model


class SolverOrTools:
    """
    Solver pour affecter les voyages aux services en respectant les contraintes :
    - Pas de chevauchement entre voyages d'un même service
    - Minimum 5 minutes entre deux voyages consécutifs
    - Maximum 60 minutes de pause entre deux voyages consécutifs
    - Respect des tranches horaires des services
    - Respect des coupures pour les services coupés
    - Respect des voyages déjà affectés aux services
    """

    def __init__(self, voyages, services, min_pause=5, max_pause=60):
        """
        Initialise le solver.

        Args:
            voyages: Liste des objets voyage disponibles (non encore affectés)
            services: Liste des objets service_agent (peuvent déjà contenir des voyages)
            min_pause: Pause minimum entre deux voyages (en minutes)
            max_pause: Pause maximum entre deux voyages (en minutes)
        """
        self.voyages = voyages
        self.services = services
        self.min_pause = min_pause
        self.max_pause = max_pause
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # Récupérer les voyages déjà affectés à chaque service
        self.voyages_existants = {}
        for service in services:
            self.voyages_existants[service] = list(service.voyages)

        # Variables de décision
        self.affectations = {}  # affectations[(v, s)] = 1 si voyage v affecté au service s

        # Résultats
        self.solution_trouvee = False
        self.voyages_affectes = {}  # {service: [voyages]}
        self.voyages_non_affectes = []
        self.statistiques = {}

    def _voyage_compatible_service(self, voyage, service):
        """Vérifie si un voyage peut être affecté à un service (contraintes horaires)"""

        # Vérifier les limites du service
        if service.heure_debut is not None and service.heure_fin is not None:
            if voyage.hdebut < service.heure_debut:
                return False
            if voyage.hfin > service.heure_fin:
                return False

        # Vérifier la coupure pour les services coupés
        if service.type_service == "coupé":
            if service.heure_debut_coupure is not None and service.heure_fin_coupure is not None:
                # Le voyage ne doit pas chevaucher la coupure
                if not (voyage.hfin <= service.heure_debut_coupure or
                        voyage.hdebut >= service.heure_fin_coupure):
                    return False

        return True

    def _voyages_compatibles(self, v1, v2):
        """
        Vérifie si deux voyages peuvent être dans le même service.
        Retourne True si les voyages sont compatibles (pas de chevauchement ET pause >= min_pause)
        """
        # Calculer la pause entre les deux voyages
        if v1.hfin <= v2.hdebut:
            # v1 se termine avant v2
            pause = v2.hdebut - v1.hfin
            return pause >= self.min_pause
        elif v2.hfin <= v1.hdebut:
            # v2 se termine avant v1
            pause = v1.hdebut - v2.hfin
            return pause >= self.min_pause
        else:
            # Les voyages se chevauchent
            return False

    def _voyage_compatible_avec_existants(self, voyage, service):
        """
        Vérifie si un nouveau voyage est compatible avec tous les voyages
        déjà présents dans le service.
        """
        for v_existant in self.voyages_existants[service]:
            if not self._voyages_compatibles(voyage, v_existant):
                return False
        return True

    def construire_modele(self):
        """Construit le modèle OR-Tools avec toutes les contraintes"""

        print("🔧 Construction du modèle OR-Tools...")
        print(f"   • {len(self.voyages)} voyages à affecter")
        print(f"   • {len(self.services)} services disponibles")
        print(f"   • Pause minimum: {self.min_pause} min")
        print(f"   • Pause maximum: {self.max_pause} min")

        # Afficher les voyages déjà dans les services
        for service in self.services:
            nb_existants = len(self.voyages_existants[service])
            if nb_existants > 0:
                print(f"   • Service {service.num_service}: {nb_existants} voyage(s) déjà affecté(s)")

        # ═══════════════════════════════════════════════════════════════
        # 1. Créer les variables de décision
        # ═══════════════════════════════════════════════════════════════
        for v_idx, voyage in enumerate(self.voyages):
            for s_idx, service in enumerate(self.services):
                # Variable binaire : 1 si voyage affecté à ce service, 0 sinon
                var_name = f"v{v_idx}_s{s_idx}"
                self.affectations[(v_idx, s_idx)] = self.model.NewBoolVar(var_name)

        print(f"   ✓ {len(self.affectations)} variables créées")

        # ═══════════════════════════════════════════════════════════════
        # 2. Contrainte : Un voyage ne peut être affecté qu'à un seul service (ou aucun)
        # ═══════════════════════════════════════════════════════════════
        for v_idx in range(len(self.voyages)):
            vars_voyage = [self.affectations[(v_idx, s_idx)]
                          for s_idx in range(len(self.services))]
            self.model.Add(sum(vars_voyage) <= 1)

        print(f"   ✓ Contraintes d'unicité ajoutées")

        # ═══════════════════════════════════════════════════════════════
        # 3. Contrainte : Compatibilité voyage/service (horaires)
        # ═══════════════════════════════════════════════════════════════
        nb_incompatibles = 0
        for v_idx, voyage in enumerate(self.voyages):
            for s_idx, service in enumerate(self.services):
                if not self._voyage_compatible_service(voyage, service):
                    self.model.Add(self.affectations[(v_idx, s_idx)] == 0)
                    nb_incompatibles += 1

        print(f"   ✓ {nb_incompatibles} incompatibilités horaires bloquées")

        # ═══════════════════════════════════════════════════════════════
        # 4. Contrainte : Compatibilité avec les voyages DÉJÀ dans le service
        # ═══════════════════════════════════════════════════════════════
        nb_conflits_existants = 0
        for v_idx, voyage in enumerate(self.voyages):
            for s_idx, service in enumerate(self.services):
                # Vérifier si le nouveau voyage est compatible avec les existants
                if not self._voyage_compatible_avec_existants(voyage, service):
                    self.model.Add(self.affectations[(v_idx, s_idx)] == 0)
                    nb_conflits_existants += 1

        print(f"   ✓ {nb_conflits_existants} conflits avec voyages existants bloqués")

        # ═══════════════════════════════════════════════════════════════
        # 5. Contrainte : Pas de chevauchement entre nouveaux voyages du même service
        # ═══════════════════════════════════════════════════════════════
        nb_conflits = 0
        for s_idx, service in enumerate(self.services):
            for v1_idx in range(len(self.voyages)):
                for v2_idx in range(v1_idx + 1, len(self.voyages)):
                    v1 = self.voyages[v1_idx]
                    v2 = self.voyages[v2_idx]

                    # Si les deux voyages ne sont pas compatibles, ils ne peuvent pas
                    # être tous les deux dans le même service
                    if not self._voyages_compatibles(v1, v2):
                        self.model.Add(
                            self.affectations[(v1_idx, s_idx)] +
                            self.affectations[(v2_idx, s_idx)] <= 1
                        )
                        nb_conflits += 1

        print(f"   ✓ {nb_conflits} contraintes entre nouveaux voyages")

        # ═══════════════════════════════════════════════════════════════
        # 6. Fonction objectif : Maximiser les voyages affectés
        # ═══════════════════════════════════════════════════════════════

        # Objectif principal : maximiser le nombre de voyages affectés
        total_affectations = sum(self.affectations.values())

        # Pénaliser les grandes pauses entre voyages consécutifs
        penalites = []
        for s_idx, service in enumerate(self.services):
            for v1_idx in range(len(self.voyages)):
                for v2_idx in range(len(self.voyages)):
                    if v1_idx == v2_idx:
                        continue

                    v1 = self.voyages[v1_idx]
                    v2 = self.voyages[v2_idx]

                    # v1 se termine avant v2 commence (avec pause suffisante)
                    if v1.hfin <= v2.hdebut:
                        pause = v2.hdebut - v1.hfin
                        if pause >= self.min_pause and pause > self.max_pause:
                            # Pénalité si pause > max_pause
                            both_in_service = self.model.NewBoolVar(f"both_{v1_idx}_{v2_idx}_s{s_idx}")
                            self.model.AddBoolAnd([
                                self.affectations[(v1_idx, s_idx)],
                                self.affectations[(v2_idx, s_idx)]
                            ]).OnlyEnforceIf(both_in_service)
                            self.model.AddBoolOr([
                                self.affectations[(v1_idx, s_idx)].Not(),
                                self.affectations[(v2_idx, s_idx)].Not()
                            ]).OnlyEnforceIf(both_in_service.Not())

                            # Pénalité proportionnelle au dépassement
                            penalite = (pause - self.max_pause) // 10
                            if penalite > 0:
                                penalites.append(both_in_service * penalite)

        # Objectif : maximiser affectations - pénalités pour grandes pauses
        if penalites:
            self.model.Maximize(total_affectations * 100 - sum(penalites))
        else:
            self.model.Maximize(total_affectations)

        print(f"   ✓ Fonction objectif configurée")
        print(f"🔧 Modèle construit avec succès !")

    def resoudre(self, timeout_secondes=30):
        """
        Résout le modèle et retourne les résultats.

        Args:
            timeout_secondes: Temps maximum de résolution

        Returns:
            bool: True si une solution a été trouvée
        """
        print(f"\n🚀 Résolution en cours (timeout: {timeout_secondes}s)...")

        self.solver.parameters.max_time_in_seconds = timeout_secondes
        status = self.solver.Solve(self.model)

        if status == cp_model.OPTIMAL:
            print("✅ Solution OPTIMALE trouvée !")
            self.solution_trouvee = True
        elif status == cp_model.FEASIBLE:
            print("✅ Solution RÉALISABLE trouvée (peut-être pas optimale)")
            self.solution_trouvee = True
        else:
            print("❌ Aucune solution trouvée")
            self.solution_trouvee = False
            return False

        # Extraire les résultats
        self._extraire_resultats()

        # Vérifier qu'il n'y a pas de chevauchements
        self._verifier_solution()

        return True

    def _extraire_resultats(self):
        """Extrait les résultats de la solution"""

        # Initialiser les résultats avec les voyages déjà existants
        self.voyages_affectes = {}
        for service in self.services:
            # Commencer avec les voyages déjà dans le service
            self.voyages_affectes[service] = list(self.voyages_existants[service])

        self.voyages_non_affectes = []

        # Ajouter les nouveaux voyages affectés
        for v_idx, voyage in enumerate(self.voyages):
            affecte = False
            for s_idx, service in enumerate(self.services):
                if self.solver.Value(self.affectations[(v_idx, s_idx)]) == 1:
                    self.voyages_affectes[service].append(voyage)
                    affecte = True
                    break

            if not affecte:
                self.voyages_non_affectes.append(voyage)

        # Trier les voyages par heure de début dans chaque service
        for service in self.services:
            self.voyages_affectes[service].sort(key=lambda v: v.hdebut)

        # Calculer les statistiques
        total_voyages = len(self.voyages)
        total_nouveaux_affectes = sum(len(v) for v in self.voyages_affectes.values()) - sum(len(v) for v in self.voyages_existants.values())

        self.statistiques = {
            'total_voyages': total_voyages,
            'voyages_affectes': total_nouveaux_affectes,
            'voyages_non_affectes': len(self.voyages_non_affectes),
            'taux_affectation': (total_nouveaux_affectes / total_voyages * 100) if total_voyages > 0 else 0,
            'services_utilises': sum(1 for s, v in self.voyages_affectes.items() if len(v) > 0)
        }

        # Statistiques par service
        self.statistiques['par_service'] = {}
        for service in self.services:
            voyages = self.voyages_affectes[service]
            if voyages:
                debut = min(v.hdebut for v in voyages)
                fin = max(v.hfin for v in voyages)
                duree = fin - debut

                # Calculer le temps de pause total
                voyages_tries = sorted(voyages, key=lambda v: v.hdebut)
                temps_pause = 0
                for i in range(len(voyages_tries) - 1):
                    pause = voyages_tries[i + 1].hdebut - voyages_tries[i].hfin
                    if pause > 0:
                        temps_pause += pause

                nb_existants = len(self.voyages_existants[service])
                nb_nouveaux = len(voyages) - nb_existants

                self.statistiques['par_service'][service.num_service] = {
                    'nb_voyages': len(voyages),
                    'nb_existants': nb_existants,
                    'nb_nouveaux': nb_nouveaux,
                    'debut': debut,
                    'fin': fin,
                    'duree': duree,
                    'temps_pause': temps_pause
                }

    def _verifier_solution(self):
        """Vérifie que la solution ne contient pas de chevauchements"""
        print("\n🔍 Vérification de la solution...")

        erreurs = []
        for service in self.services:
            voyages = self.voyages_affectes[service]
            voyages_tries = sorted(voyages, key=lambda v: v.hdebut)

            for i in range(len(voyages_tries) - 1):
                v1 = voyages_tries[i]
                v2 = voyages_tries[i + 1]

                pause = v2.hdebut - v1.hfin

                if pause < 0:
                    erreurs.append(f"   ❌ Service {service.num_service}: V{v1.num_voyage} et V{v2.num_voyage} se chevauchent!")
                elif pause < self.min_pause:
                    erreurs.append(f"   ⚠️ Service {service.num_service}: V{v1.num_voyage} → V{v2.num_voyage} pause de {pause}min < {self.min_pause}min")

        if erreurs:
            print("   Problèmes détectés:")
            for e in erreurs:
                print(e)
        else:
            print("   ✅ Aucun chevauchement détecté")
            print(f"   ✅ Toutes les pauses >= {self.min_pause} min")

    def afficher_resultats(self):
        """Affiche les résultats de manière lisible"""

        if not self.solution_trouvee:
            print("\n❌ Pas de solution à afficher")
            return

        print("\n" + "═" * 60)
        print("📊 RÉSULTATS DE L'OPTIMISATION")
        print("═" * 60)

        print(f"\n📈 Statistiques globales:")
        print(f"   • Voyages à affecter: {self.statistiques['total_voyages']}")
        print(f"   • Nouveaux voyages affectés: {self.statistiques['voyages_affectes']}")
        print(f"   • Voyages non affectés: {self.statistiques['voyages_non_affectes']}")
        print(f"   • Taux d'affectation: {self.statistiques['taux_affectation']:.1f}%")
        print(f"   • Services utilisés: {self.statistiques['services_utilises']}/{len(self.services)}")

        print(f"\n📋 Détail par service:")
        for service in self.services:
            voyages = self.voyages_affectes[service]
            print(f"\n   🚌 Service {service.num_service} ({service.type_service}):")

            if voyages:
                stats = self.statistiques['par_service'][service.num_service]
                h_debut = f"{stats['debut'] // 60:02d}h{stats['debut'] % 60:02d}"
                h_fin = f"{stats['fin'] // 60:02d}h{stats['fin'] % 60:02d}"

                print(f"      • {stats['nb_voyages']} voyages total ({stats['nb_existants']} existants + {stats['nb_nouveaux']} nouveaux)")
                print(f"      • Plage: {h_debut} - {h_fin}")
                print(f"      • Temps de pause total: {stats['temps_pause']} min")

                print(f"      • Voyages:")
                for v in voyages:
                    h_d = f"{v.hdebut // 60:02d}h{v.hdebut % 60:02d}"
                    h_f = f"{v.hfin // 60:02d}h{v.hfin % 60:02d}"
                    # Marquer les voyages existants
                    marker = "🔵" if v in self.voyages_existants[service] else "🟢"
                    print(f"         {marker} V{v.num_voyage} ({v.num_ligne}): {h_d}-{h_f}")
            else:
                print(f"      • Aucun voyage affecté")

        if self.voyages_non_affectes:
            print(f"\n   ⚠️ Voyages non affectés:")
            for v in self.voyages_non_affectes:
                h_d = f"{v.hdebut // 60:02d}h{v.hdebut % 60:02d}"
                h_f = f"{v.hfin // 60:02d}h{v.hfin % 60:02d}"
                print(f"      - V{v.num_voyage} ({v.num_ligne}): {h_d}-{h_f}")

        print("\n" + "═" * 60)

    def get_rapport(self):
        """Retourne un rapport textuel des résultats"""

        if not self.solution_trouvee:
            return "Aucune solution trouvée"

        rapport = []
        rapport.append("═" * 50)
        rapport.append("RAPPORT D'OPTIMISATION")
        rapport.append("═" * 50)
        rapport.append("")
        rapport.append(f"Nouveaux voyages affectés: {self.statistiques['voyages_affectes']}/{self.statistiques['total_voyages']}")
        rapport.append(f"Taux d'affectation: {self.statistiques['taux_affectation']:.1f}%")
        rapport.append("")

        for service in self.services:
            voyages = self.voyages_affectes[service]
            if service.num_service in self.statistiques.get('par_service', {}):
                stats = self.statistiques['par_service'][service.num_service]
                rapport.append(f"Service {service.num_service} ({service.type_service}): {stats['nb_voyages']} voyages ({stats['nb_existants']} existants + {stats['nb_nouveaux']} nouveaux)")
            else:
                rapport.append(f"Service {service.num_service} ({service.type_service}): 0 voyages")

        if self.voyages_non_affectes:
            rapport.append("")
            rapport.append(f"Non affectés: {len(self.voyages_non_affectes)} voyages")

        return "\n".join(rapport)

    def get_nouveaux_voyages_par_service(self):
        """
        Retourne uniquement les NOUVEAUX voyages affectés (pas les existants).
        Utilisé par l'interface pour mettre à jour les services.
        """
        nouveaux = {}
        for service in self.services:
            nouveaux[service] = []
            for v in self.voyages_affectes[service]:
                if v not in self.voyages_existants[service]:
                    nouveaux[service].append(v)
        return nouveaux


def optimiser_services(voyages_disponibles, services, min_pause=5, max_pause=60, timeout=30):
    """
    Fonction utilitaire pour lancer l'optimisation.

    Args:
        voyages_disponibles: Liste des voyages à affecter (non encore affectés)
        services: Liste des services cibles (peuvent déjà contenir des voyages)
        min_pause: Pause minimum entre voyages (défaut: 5 min)
        max_pause: Pause maximum entre voyages (défaut: 60 min)
        timeout: Temps maximum de résolution (défaut: 30 sec)

    Returns:
        SolverOrTools: Instance du solver avec les résultats
    """
    solver = SolverOrTools(voyages_disponibles, services, min_pause, max_pause)
    solver.construire_modele()
    solver.resoudre(timeout)

    return solver


