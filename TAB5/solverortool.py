"""
Solver OR-Tools pour l'optimisation des services de transport
Compatible avec tab5.py
"""

from ortools.sat.python import cp_model


class SolverOrTools:
    """
    Solver pour affecter les voyages aux services.

    Contraintes :
    - Pas de chevauchement entre voyages
    - Pause minimum 5 min (géo OK) ou 10 min (géo KO)
    - Pause maximum 60 min entre voyages consécutifs
    - Respect des limites horaires (heure_debut_max, heure_fin_max)
    - Conservation des voyages déjà assignés
    - Répartition équitable entre services

    Objectif :
    - Maximiser le nombre de voyages affectés
    - Favoriser la continuité géographique
    - Utiliser toute l'amplitude des services
    """

    def __init__(self, voyages, services, min_pause_geo_ok=5, min_pause_geo_ko=10, max_pause=60):
        """
        Args:
            voyages: Liste des voyages NON assignés à affecter
            services: Liste des services (peuvent contenir des voyages existants)
            min_pause_geo_ok: Pause min si arrêts compatibles (défaut: 5)
            min_pause_geo_ko: Pause min si arrêts incompatibles (défaut: 10)
            max_pause: Pause max entre voyages consécutifs (défaut: 60)
        """
        self.voyages = list(voyages)
        self.services = list(services)
        self.min_pause_geo_ok = min_pause_geo_ok
        self.min_pause_geo_ko = min_pause_geo_ko
        self.max_pause = max_pause

        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # Voyages déjà dans les services (à conserver absolument)
        self.voyages_existants = {}
        for service in services:
            self.voyages_existants[service] = list(service.voyages)

        # Variables de décision
        self.x = {}  # x[v_idx, s_idx] = 1 si voyage v affecté au service s

        # Résultats
        self.solution_trouvee = False
        self.voyages_affectes = {}
        self.voyages_non_affectes = []
        self.statistiques = {}

    def _arrets_compatibles(self, v1, v2):
        """Compare les 3 premiers caractères des arrêts"""
        fin = v1.arret_fin[:3].upper() if v1.arret_fin else ""
        debut = v2.arret_debut[:3].upper() if v2.arret_debut else ""
        return fin == debut

    def _pause_requise(self, v_avant, v_apres):
        """Retourne la pause minimum requise entre deux voyages"""
        if self._arrets_compatibles(v_avant, v_apres):
            return self.min_pause_geo_ok
        return self.min_pause_geo_ko

    def _voyage_dans_limites(self, voyage, service):
        """Vérifie si le voyage respecte les limites horaires du service"""
        h_debut = getattr(service, 'heure_debut_max', None)
        h_fin = getattr(service, 'heure_fin_max', None)

        if h_debut is not None and voyage.hdebut < h_debut:
            return False
        if h_fin is not None and voyage.hfin > h_fin:
            return False
        return True

    def _voyages_compatibles_temporellement(self, v1, v2):
        """
        Vérifie si v1 et v2 peuvent coexister dans le même service.
        Retourne True si pas de conflit.
        """
        # Déterminer l'ordre
        if v1.hdebut <= v2.hdebut:
            v_avant, v_apres = v1, v2
        else:
            v_avant, v_apres = v2, v1

        # Chevauchement ?
        if v_avant.hfin > v_apres.hdebut:
            return False

        # Pause suffisante ?
        pause = v_apres.hdebut - v_avant.hfin
        pause_min = self._pause_requise(v_avant, v_apres)

        return pause >= pause_min

    def construire_modele(self):
        """Construit le modèle OR-Tools"""

        print("\n" + "=" * 60)
        print("🔧 CONSTRUCTION DU MODÈLE OR-TOOLS")
        print("=" * 60)
        print(f"   Voyages à affecter : {len(self.voyages)}")
        print(f"   Services : {len(self.services)}")
        print(f"   Pause min (géo OK) : {self.min_pause_geo_ok} min")
        print(f"   Pause min (géo KO) : {self.min_pause_geo_ko} min")
        print(f"   Pause max : {self.max_pause} min")

        # Afficher les voyages existants
        for s in self.services:
            nb = len(self.voyages_existants[s])
            if nb > 0:
                print(f"   Service {s.num_service} : {nb} voyage(s) existant(s)")

        # ═══════════════════════════════════════════════════════════════
        # 1. VARIABLES : x[v_idx, s_idx] = 1 si voyage affecté au service
        # ═══════════════════════════════════════════════════════════════
        for v_idx in range(len(self.voyages)):
            for s_idx in range(len(self.services)):
                self.x[v_idx, s_idx] = self.model.NewBoolVar(f"x_{v_idx}_{s_idx}")

        print(f"\n   ✓ {len(self.x)} variables créées")

        # ═══════════════════════════════════════════════════════════════
        # 2. CONTRAINTE : Un voyage va dans au plus UN service
        # ═══════════════════════════════════════════════════════════════
        for v_idx in range(len(self.voyages)):
            self.model.Add(
                sum(self.x[v_idx, s_idx] for s_idx in range(len(self.services))) <= 1
            )

        # ═══════════════════════════════════════════════════════════════
        # 3. CONTRAINTE : Respect des limites horaires du service
        # ═══════════════════════════════════════════════════════════════
        nb_hors_limites = 0
        for v_idx, voyage in enumerate(self.voyages):
            for s_idx, service in enumerate(self.services):
                if not self._voyage_dans_limites(voyage, service):
                    self.model.Add(self.x[v_idx, s_idx] == 0)
                    nb_hors_limites += 1

        print(f"   ✓ {nb_hors_limites} affectations hors limites bloquées")

        # ═══════════════════════════════════════════════════════════════
        # 4. CONTRAINTE : Compatibilité avec les voyages EXISTANTS
        # ═══════════════════════════════════════════════════════════════
        nb_conflits_existants = 0
        for v_idx, voyage in enumerate(self.voyages):
            for s_idx, service in enumerate(self.services):
                for v_exist in self.voyages_existants[service]:
                    if not self._voyages_compatibles_temporellement(voyage, v_exist):
                        self.model.Add(self.x[v_idx, s_idx] == 0)
                        nb_conflits_existants += 1
                        break

        print(f"   ✓ {nb_conflits_existants} conflits avec existants bloqués")

        # ═══════════════════════════════════════════════════════════════
        # 5. CONTRAINTE : Compatibilité entre NOUVEAUX voyages
        # ═══════════════════════════════════════════════════════════════
        nb_conflits_nouveaux = 0
        for s_idx in range(len(self.services)):
            for i in range(len(self.voyages)):
                for j in range(i + 1, len(self.voyages)):
                    v1, v2 = self.voyages[i], self.voyages[j]
                    if not self._voyages_compatibles_temporellement(v1, v2):
                        self.model.Add(self.x[i, s_idx] + self.x[j, s_idx] <= 1)
                        nb_conflits_nouveaux += 1

        print(f"   ✓ {nb_conflits_nouveaux} conflits entre nouveaux bloqués")

        # ═══════════════════════════════════════════════════════════════
        # 6. CONTRAINTE : Pause maximum (nécessite des intermédiaires)
        # ═══════════════════════════════════════════════════════════════
        nb_contraintes_pause_max = 0

        for s_idx, service in enumerate(self.services):
            # Tous les voyages potentiels du service
            tous = []
            for v in self.voyages_existants[service]:
                tous.append((None, v))  # None = existant
            for v_idx, v in enumerate(self.voyages):
                tous.append((v_idx, v))

            # Pour chaque paire de voyages
            for i, (idx1, v1) in enumerate(tous):
                for j, (idx2, v2) in enumerate(tous):
                    if i >= j:
                        continue

                    # Ordonner temporellement
                    if v1.hdebut <= v2.hdebut:
                        v_avant, idx_avant = v1, idx1
                        v_apres, idx_apres = v2, idx2
                    else:
                        v_avant, idx_avant = v2, idx2
                        v_apres, idx_apres = v1, idx1

                    # Calculer la pause
                    if v_avant.hfin > v_apres.hdebut:
                        continue  # Chevauchement, déjà géré

                    pause = v_apres.hdebut - v_avant.hfin

                    if pause <= self.max_pause:
                        continue  # Pause OK

                    # Pause > max : chercher des intermédiaires possibles
                    intermediaires = []
                    for k, vk in enumerate(self.voyages):
                        if vk == v_avant or vk == v_apres:
                            continue

                        # vk peut s'insérer entre v_avant et v_apres ?
                        pause1 = vk.hdebut - v_avant.hfin
                        pause2 = v_apres.hdebut - vk.hfin

                        if pause1 < self._pause_requise(v_avant, vk):
                            continue
                        if pause2 < self._pause_requise(vk, v_apres):
                            continue
                        if pause1 > self.max_pause or pause2 > self.max_pause:
                            continue
                        if not self._voyage_dans_limites(vk, service):
                            continue

                        intermediaires.append(k)

                    # Appliquer la contrainte
                    avant_existant = idx_avant is None
                    apres_existant = idx_apres is None

                    if avant_existant and apres_existant:
                        # Deux existants avec trou > max : DOIT avoir intermédiaire
                        if intermediaires:
                            self.model.Add(
                                sum(self.x[k, s_idx] for k in intermediaires) >= 1
                            )
                    elif avant_existant:
                        if intermediaires:
                            self.model.Add(
                                sum(self.x[k, s_idx] for k in intermediaires) >= self.x[idx_apres, s_idx]
                            )
                        else:
                            self.model.Add(self.x[idx_apres, s_idx] == 0)
                    elif apres_existant:
                        if intermediaires:
                            self.model.Add(
                                sum(self.x[k, s_idx] for k in intermediaires) >= self.x[idx_avant, s_idx]
                            )
                        else:
                            self.model.Add(self.x[idx_avant, s_idx] == 0)
                    else:
                        if intermediaires:
                            self.model.Add(
                                self.x[idx_avant, s_idx] + self.x[idx_apres, s_idx] - 1 <=
                                sum(self.x[k, s_idx] for k in intermediaires)
                            )
                        else:
                            self.model.Add(
                                self.x[idx_avant, s_idx] + self.x[idx_apres, s_idx] <= 1
                            )

                    nb_contraintes_pause_max += 1

        print(f"   ✓ {nb_contraintes_pause_max} contraintes pause max")

        # ═══════════════════════════════════════════════════════════════
        # 7. CONTRAINTE : Répartition équitable
        # ═══════════════════════════════════════════════════════════════
        if len(self.services) > 0:
            total = len(self.voyages) + sum(len(v) for v in self.voyages_existants.values())
            moyenne = total / len(self.services)
            min_voy = max(0, int(moyenne) - 2)
            max_voy = int(moyenne) + 3

            print(f"   📊 Répartition cible : {min_voy} à {max_voy} voyages/service")

            for s_idx, service in enumerate(self.services):
                nb_existants = len(self.voyages_existants[service])
                nouveaux = sum(self.x[v_idx, s_idx] for v_idx in range(len(self.voyages)))

                # Max
                self.model.Add(nouveaux <= max_voy - nb_existants)

        # ═══════════════════════════════════════════════════════════════
        # 8. OBJECTIF : Maximiser affectations + bonus géo + bonus amplitude
        # ═══════════════════════════════════════════════════════════════
        objectif = []

        for v_idx, voyage in enumerate(self.voyages):
            for s_idx, service in enumerate(self.services):
                # Base : 1000 points par affectation
                score = 1000

                # Bonus amplitude : proche du début ou de la fin du service
                h_debut = getattr(service, 'heure_debut_max', None)
                h_fin = getattr(service, 'heure_fin_max', None)

                if h_debut is not None:
                    dist = voyage.hdebut - h_debut
                    if dist <= 60:
                        score += (60 - dist)  # +0 à +60

                if h_fin is not None:
                    dist = h_fin - voyage.hfin
                    if dist <= 60:
                        score += (60 - dist)  # +0 à +60

                # Bonus géo : compatible avec un voyage existant
                for v_exist in self.voyages_existants[service]:
                    if v_exist.hfin <= voyage.hdebut:
                        if self._arrets_compatibles(v_exist, voyage):
                            score += 100
                            break
                    elif voyage.hfin <= v_exist.hdebut:
                        if self._arrets_compatibles(voyage, v_exist):
                            score += 100
                            break

                objectif.append(self.x[v_idx, s_idx] * score)

        self.model.Maximize(sum(objectif))

        print(f"   ✓ Objectif : max(affectations + amplitude + géo)")
        print("=" * 60)

    def resoudre(self, timeout=60):
        """Résout le modèle"""
        print(f"\n🚀 Résolution (timeout: {timeout}s)...")

        self.solver.parameters.max_time_in_seconds = timeout
        status = self.solver.Solve(self.model)

        if status == cp_model.OPTIMAL:
            print("✅ Solution OPTIMALE trouvée !")
            self.solution_trouvee = True
        elif status == cp_model.FEASIBLE:
            print("✅ Solution trouvée (peut-être pas optimale)")
            self.solution_trouvee = True
        else:
            print("❌ Aucune solution trouvée")
            self.solution_trouvee = False
            return False

        self._extraire_resultats()
        self._verifier_solution()
        return True

    def _extraire_resultats(self):
        """Extrait les résultats"""

        # Initialiser avec les existants
        self.voyages_affectes = {s: list(self.voyages_existants[s]) for s in self.services}
        self.voyages_non_affectes = []

        # Ajouter les nouveaux
        for v_idx, voyage in enumerate(self.voyages):
            affecte = False
            for s_idx, service in enumerate(self.services):
                if self.solver.Value(self.x[v_idx, s_idx]) == 1:
                    self.voyages_affectes[service].append(voyage)
                    affecte = True
                    break
            if not affecte:
                self.voyages_non_affectes.append(voyage)

        # Trier par heure
        for service in self.services:
            self.voyages_affectes[service].sort(key=lambda v: v.hdebut)

        # Stats
        total = len(self.voyages)
        affectes = total - len(self.voyages_non_affectes)

        self.statistiques = {
            'total_voyages': total,
            'voyages_affectes': affectes,
            'voyages_non_affectes': len(self.voyages_non_affectes),
            'taux_affectation': (affectes / total * 100) if total > 0 else 0,
            'par_service': {}
        }

        for service in self.services:
            voyages = self.voyages_affectes[service]
            if voyages:
                ruptures = 0
                pause_max = 0
                vlist = sorted(voyages, key=lambda v: v.hdebut)

                for i in range(len(vlist) - 1):
                    v1, v2 = vlist[i], vlist[i + 1]
                    pause = v2.hdebut - v1.hfin
                    if pause > pause_max:
                        pause_max = pause
                    if not self._arrets_compatibles(v1, v2):
                        ruptures += 1

                self.statistiques['par_service'][service.num_service] = {
                    'nb_voyages': len(voyages),
                    'nb_existants': len(self.voyages_existants[service]),
                    'nb_nouveaux': len(voyages) - len(self.voyages_existants[service]),
                    'pause_max': pause_max,
                    'ruptures_geo': ruptures
                }

    def _verifier_solution(self):
        """Vérifie la solution"""
        print("\n🔍 Vérification...")

        erreurs = []
        avertissements = []

        for service in self.services:
            voyages = sorted(self.voyages_affectes[service], key=lambda v: v.hdebut)

            for i in range(len(voyages) - 1):
                v1, v2 = voyages[i], voyages[i + 1]
                pause = v2.hdebut - v1.hfin
                pause_min = self._pause_requise(v1, v2)

                if pause < 0:
                    erreurs.append(f"S{service.num_service}: chevauchement V{v1.num_voyage}-V{v2.num_voyage}")
                elif pause < pause_min:
                    erreurs.append(f"S{service.num_service}: pause {pause}min < {pause_min}min")
                elif pause > self.max_pause:
                    erreurs.append(f"S{service.num_service}: pause {pause}min > {self.max_pause}min")

                if not self._arrets_compatibles(v1, v2):
                    avertissements.append(f"S{service.num_service}: {v1.arret_fin[:3]}→{v2.arret_debut[:3]}")

        if erreurs:
            print("   ❌ ERREURS:")
            for e in erreurs[:5]:
                print(f"      {e}")
        else:
            print("   ✅ Contraintes temporelles OK")

        if avertissements:
            print(f"   ⚠️ {len(avertissements)} rupture(s) géographique(s)")
        else:
            print("   ✅ Continuité géographique parfaite")

        # Répartition
        print("\n📊 Répartition:")
        for s in self.services:
            if s.num_service in self.statistiques['par_service']:
                st = self.statistiques['par_service'][s.num_service]
                print(f"   Service {s.num_service}: {st['nb_voyages']} voy ({st['nb_existants']} exist + {st['nb_nouveaux']} nouveaux)")

    def get_nouveaux_voyages_par_service(self):
        """Retourne UNIQUEMENT les nouveaux voyages (pas les existants)"""
        return {
            service: [v for v in self.voyages_affectes[service]
                     if v not in self.voyages_existants[service]]
            for service in self.services
        }

    def get_rapport(self):
        """Retourne un rapport textuel"""
        if not self.solution_trouvee:
            return "Aucune solution trouvée"

        lignes = [
            f"Affectés: {self.statistiques['voyages_affectes']}/{self.statistiques['total_voyages']}",
            f"Taux: {self.statistiques['taux_affectation']:.0f}%",
            ""
        ]
        for s in self.services:
            if s.num_service in self.statistiques['par_service']:
                st = self.statistiques['par_service'][s.num_service]
                lignes.append(f"Service {s.num_service}: {st['nb_voyages']} voyages")

        return "\n".join(lignes)


def optimiser_services(voyages_disponibles, services, min_pause=5, max_pause=60, timeout=60):
    """
    Fonction utilitaire pour lancer l'optimisation.

    Args:
        voyages_disponibles: Voyages à affecter (non encore assignés)
        services: Liste des services
        min_pause: Pause min si géo compatible (défaut: 5)
        max_pause: Pause max entre voyages (défaut: 60)
        timeout: Temps max de résolution (défaut: 60s)

    Returns:
        SolverOrTools: Instance du solver avec les résultats
    """
    solver = SolverOrTools(
        voyages_disponibles,
        services,
        min_pause_geo_ok=min_pause,
        min_pause_geo_ko=10,
        max_pause=max_pause
    )
    solver.construire_modele()
    solver.resoudre(timeout)
    return solver