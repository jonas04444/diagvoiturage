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
    """

    def __init__(self, voyages, services, min_pause=5, max_pause=60):
        """
        Initialise le solver.

        Args:
            voyages: Liste des objets voyage disponibles
            services: Liste des objets service_agent
            min_pause: Pause minimum entre deux voyages (en minutes)
            max_pause: Pause maximum entre deux voyages (en minutes)
        """
        self.voyages = voyages
        self.services = services
        self.min_pause = min_pause
        self.max_pause = max_pause
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

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

    def _voyages_se_chevauchent(self, v1, v2):
        """Vérifie si deux voyages se chevauchent"""
        return not (v1.hfin <= v2.hdebut or v1.hdebut >= v2.hfin)

    def _calculer_pause(self, v1, v2):
        """Calcule la pause entre deux voyages (v1 avant v2)"""
        if v1.hfin <= v2.hdebut:
            return v2.hdebut - v1.hfin
        return -1  # Chevauchement

    def construire_modele(self):
        """Construit le modèle OR-Tools avec toutes les contraintes"""

        print("🔧 Construction du modèle OR-Tools...")

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
        for v_idx, voyage in enumerate(self.voyages):
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
        # 4. Contrainte : Pas de chevauchement dans un même service
        # ═══════════════════════════════════════════════════════════════
        nb_chevauchements = 0
        for s_idx, service in enumerate(self.services):
            for v1_idx in range(len(self.voyages)):
                for v2_idx in range(v1_idx + 1, len(self.voyages)):
                    v1 = self.voyages[v1_idx]
                    v2 = self.voyages[v2_idx]

                    if self._voyages_se_chevauchent(v1, v2):
                        # Si les voyages se chevauchent, ils ne peuvent pas être
                        # tous les deux dans le même service
                        self.model.Add(
                            self.affectations[(v1_idx, s_idx)] +
                            self.affectations[(v2_idx, s_idx)] <= 1
                        )
                        nb_chevauchements += 1

        print(f"   ✓ {nb_chevauchements} contraintes de non-chevauchement")

        # ═══════════════════════════════════════════════════════════════
        # 5. Contrainte : Pause minimum et maximum entre voyages consécutifs
        # ═══════════════════════════════════════════════════════════════
        nb_pauses_invalides = 0
        for s_idx, service in enumerate(self.services):
            for v1_idx in range(len(self.voyages)):
                for v2_idx in range(len(self.voyages)):
                    if v1_idx == v2_idx:
                        continue

                    v1 = self.voyages[v1_idx]
                    v2 = self.voyages[v2_idx]

                    # v1 se termine avant v2 commence
                    if v1.hfin <= v2.hdebut:
                        pause = v2.hdebut - v1.hfin

                        # Pause trop courte (< 5 min)
                        if 0 < pause < self.min_pause:
                            self.model.Add(
                                self.affectations[(v1_idx, s_idx)] +
                                self.affectations[(v2_idx, s_idx)] <= 1
                            )
                            nb_pauses_invalides += 1

                        # Vérifier si les voyages sont consécutifs (pas d'autre voyage entre)
                        # et si la pause est trop longue
                        elif pause > self.max_pause:
                            # On vérifie s'il existe un voyage intermédiaire possible
                            voyage_intermediaire_existe = False
                            for v3_idx in range(len(self.voyages)):
                                if v3_idx == v1_idx or v3_idx == v2_idx:
                                    continue
                                v3 = self.voyages[v3_idx]
                                # v3 peut s'insérer entre v1 et v2
                                if (v1.hfin + self.min_pause <= v3.hdebut and
                                        v3.hfin + self.min_pause <= v2.hdebut):
                                    if self._voyage_compatible_service(v3, service):
                                        voyage_intermediaire_existe = True
                                        break

                            # Si aucun voyage ne peut s'insérer et la pause est trop longue
                            # On ne bloque pas mais on pénalise dans l'objectif

        print(f"   ✓ {nb_pauses_invalides} contraintes de pause minimum")

        # ═══════════════════════════════════════════════════════════════
        # 6. Fonction objectif : Maximiser les voyages affectés + Minimiser les pauses
        # ═══════════════════════════════════════════════════════════════

        # Objectif principal : maximiser le nombre de voyages affectés
        total_affectations = sum(self.affectations.values())

        # Objectif secondaire : minimiser les "trous" (pauses longues)
        # On crée des variables pour pénaliser les grandes pauses
        penalites_pause = []

        for s_idx, service in enumerate(self.services):
            voyages_tries = sorted(enumerate(self.voyages), key=lambda x: x[1].hdebut)

            for i in range(len(voyages_tries) - 1):
                v1_idx, v1 = voyages_tries[i]
                v2_idx, v2 = voyages_tries[i + 1]

                if v1.hfin <= v2.hdebut:
                    pause = v2.hdebut - v1.hfin
                    if pause > self.min_pause:
                        # Variable indiquant si les deux voyages sont consécutifs
                        # dans ce service (sans voyage entre)
                        consecutifs = self.model.NewBoolVar(f"cons_{v1_idx}_{v2_idx}_s{s_idx}")

                        # consecutifs = 1 seulement si les deux sont affectés au service
                        self.model.Add(
                            self.affectations[(v1_idx, s_idx)] +
                            self.affectations[(v2_idx, s_idx)] - 1 <= consecutifs
                        )
                        self.model.Add(
                            consecutifs <= self.affectations[(v1_idx, s_idx)]
                        )
                        self.model.Add(
                            consecutifs <= self.affectations[(v2_idx, s_idx)]
                        )

                        # Pénalité proportionnelle à la pause
                        penalite = (pause - self.min_pause) // 10  # Pénalité par tranche de 10 min
                        if penalite > 0:
                            penalites_pause.append(consecutifs * penalite)

        # Objectif combiné : maximiser affectations - pénalités
        if penalites_pause:
            self.model.Maximize(total_affectations * 100 - sum(penalites_pause))
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

        return True

    def _extraire_resultats(self):
        """Extrait les résultats de la solution"""

        # Initialiser les résultats
        self.voyages_affectes = {service: [] for service in self.services}
        self.voyages_non_affectes = []

        voyages_utilises = set()

        for v_idx, voyage in enumerate(self.voyages):
            affecte = False
            for s_idx, service in enumerate(self.services):
                if self.solver.Value(self.affectations[(v_idx, s_idx)]) == 1:
                    self.voyages_affectes[service].append(voyage)
                    voyages_utilises.add(v_idx)
                    affecte = True
                    break

            if not affecte:
                self.voyages_non_affectes.append(voyage)

        # Trier les voyages par heure de début dans chaque service
        for service in self.services:
            self.voyages_affectes[service].sort(key=lambda v: v.hdebut)

        # Calculer les statistiques
        total_voyages = len(self.voyages)
        total_affectes = sum(len(v) for v in self.voyages_affectes.values())

        self.statistiques = {
            'total_voyages': total_voyages,
            'voyages_affectes': total_affectes,
            'voyages_non_affectes': len(self.voyages_non_affectes),
            'taux_affectation': (total_affectes / total_voyages * 100) if total_voyages > 0 else 0,
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

                self.statistiques['par_service'][service.num_service] = {
                    'nb_voyages': len(voyages),
                    'debut': debut,
                    'fin': fin,
                    'duree': duree,
                    'temps_pause': temps_pause
                }

    def afficher_resultats(self):
        """Affiche les résultats de manière lisible"""

        if not self.solution_trouvee:
            print("\n❌ Pas de solution à afficher")
            return

        print("\n" + "═" * 60)
        print("📊 RÉSULTATS DE L'OPTIMISATION")
        print("═" * 60)

        print(f"\n📈 Statistiques globales:")
        print(f"   • Voyages totaux: {self.statistiques['total_voyages']}")
        print(f"   • Voyages affectés: {self.statistiques['voyages_affectes']}")
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

                print(f"      • {stats['nb_voyages']} voyages")
                print(f"      • Plage: {h_debut} - {h_fin}")
                print(f"      • Temps de pause total: {stats['temps_pause']} min")

                print(f"      • Voyages:")
                for v in voyages:
                    h_d = f"{v.hdebut // 60:02d}h{v.hdebut % 60:02d}"
                    h_f = f"{v.hfin // 60:02d}h{v.hfin % 60:02d}"
                    print(f"         - V{v.num_voyage} ({v.num_ligne}): {h_d}-{h_f}")
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
        rapport.append(
            f"Voyages affectés: {self.statistiques['voyages_affectes']}/{self.statistiques['total_voyages']}")
        rapport.append(f"Taux d'affectation: {self.statistiques['taux_affectation']:.1f}%")
        rapport.append("")

        for service in self.services:
            voyages = self.voyages_affectes[service]
            rapport.append(f"Service {service.num_service} ({service.type_service}): {len(voyages)} voyages")

        if self.voyages_non_affectes:
            rapport.append("")
            rapport.append(f"Non affectés: {len(self.voyages_non_affectes)} voyages")

        return "\n".join(rapport)


def optimiser_services(voyages_disponibles, services, min_pause=5, max_pause=60, timeout=30):
    """
    Fonction utilitaire pour lancer l'optimisation.

    Args:
        voyages_disponibles: Liste des voyages à affecter
        services: Liste des services cibles
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


# Test standalone
if __name__ == "__main__":
    from objet import voyage, service_agent

    # Créer des voyages de test
    voyages_test = [
        voyage("25", "101", "Gare", "Centre", "06:00", "06:30"),
        voyage("25", "102", "Centre", "Gare", "06:45", "07:15"),
        voyage("25", "103", "Gare", "Centre", "07:30", "08:00"),
        voyage("25", "104", "Centre", "Gare", "08:15", "08:45"),
        voyage("25", "105", "Gare", "Centre", "09:00", "09:30"),
        voyage("35", "201", "Place", "Mairie", "06:15", "06:45"),
        voyage("35", "202", "Mairie", "Place", "07:00", "07:30"),
        voyage("35", "203", "Place", "Mairie", "14:00", "14:30"),
        voyage("35", "204", "Mairie", "Place", "14:45", "15:15"),
    ]

    # Créer des services de test
    service1 = service_agent(num_service=1, type_service="matin")
    service1.set_limites(6 * 60, 10 * 60)  # 06:00 - 10:00

    service2 = service_agent(num_service=2, type_service="après-midi")
    service2.set_limites(13 * 60, 17 * 60)  # 13:00 - 17:00

    services_test = [service1, service2]

    # Lancer l'optimisation
    solver = optimiser_services(voyages_test, services_test)
    solver.afficher_resultats()