"""
Solver OR-Tools pour l'optimisation des services de transport
"""

from ortools.sat.python import cp_model


class SolverOrTools:
    """
    Solver pour affecter les voyages aux services en respectant les contraintes :
    - Pas de chevauchement entre voyages d'un même service
    - Minimum 5 minutes entre deux voyages consécutifs
    - Maximum 60 minutes de pause entre deux voyages consécutifs (STRICTE)
    - Respect des tranches horaires des services
    - Respect des coupures pour les services coupés
    - Respect des voyages déjà affectés aux services
    - CONTINUITÉ GÉOGRAPHIQUE : un voyage doit partir de là où le précédent s'est terminé
    """

    def __init__(self, voyages, services, min_pause=5, max_pause=60):
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
        self.affectations = {}

        # Résultats
        self.solution_trouvee = False
        self.voyages_affectes = {}
        self.voyages_non_affectes = []
        self.statistiques = {}

    def _voyage_compatible_service(self, voyage, service):
        """Vérifie si un voyage peut être affecté à un service (contraintes horaires)"""

        if service.heure_debut is not None and service.heure_fin is not None:
            if voyage.hdebut < service.heure_debut:
                return False
            if voyage.hfin > service.heure_fin:
                return False

        if service.type_service == "coupé":
            if service.heure_debut_coupure is not None and service.heure_fin_coupure is not None:
                if not (voyage.hfin <= service.heure_debut_coupure or
                        voyage.hdebut >= service.heure_fin_coupure):
                    return False

        return True

    def _arrets_compatibles(self, v_precedent, v_suivant):
        """
        Vérifie si deux voyages sont compatibles géographiquement.
        Le voyage suivant doit partir de là où le précédent s'est terminé.
        Compare les 3 premiers caractères des arrêts.
        """
        arret_fin = v_precedent.arret_fin[:3].upper()
        arret_debut = v_suivant.arret_debut[:3].upper()
        return arret_fin == arret_debut

    def _voyages_compatibles_temporellement(self, v1, v2):
        """
        Vérifie si deux voyages sont compatibles temporellement.
        Retourne True si pas de chevauchement ET pause >= min_pause
        """
        if v1.hfin <= v2.hdebut:
            pause = v2.hdebut - v1.hfin
            return pause >= self.min_pause
        elif v2.hfin <= v1.hdebut:
            pause = v1.hdebut - v2.hfin
            return pause >= self.min_pause
        else:
            return False

    def _voyages_peuvent_etre_consecutifs(self, v_avant, v_apres):
        """
        Vérifie si v_avant peut être immédiatement suivi par v_apres.
        Doit respecter : temps ET géographie
        """
        # Vérifier l'ordre temporel
        if v_avant.hfin > v_apres.hdebut:
            return False

        # Vérifier la pause minimum
        pause = v_apres.hdebut - v_avant.hfin
        if pause < self.min_pause:
            return False

        # Vérifier la compatibilité géographique
        if not self._arrets_compatibles(v_avant, v_apres):
            return False

        return True

    def _voyage_compatible_avec_existants(self, voyage, service):
        """Vérifie si un nouveau voyage est compatible avec les voyages existants."""
        for v_existant in self.voyages_existants[service]:
            if not self._voyages_compatibles_temporellement(voyage, v_existant):
                return False
        return True

    def _peut_inserer_entre(self, v_inter, v_avant, v_apres, service):
        """
        Vérifie si v_inter peut s'insérer entre v_avant et v_apres.
        Doit respecter temps ET géographie.
        """
        # Vérifier l'ordre
        if v_avant.hfin > v_apres.hdebut:
            v_avant, v_apres = v_apres, v_avant

        # Vérifier que v_inter peut suivre v_avant (temps + géo)
        if v_avant.hfin + self.min_pause > v_inter.hdebut:
            return False
        if not self._arrets_compatibles(v_avant, v_inter):
            return False

        # Vérifier que v_apres peut suivre v_inter (temps + géo)
        if v_inter.hfin + self.min_pause > v_apres.hdebut:
            return False
        if not self._arrets_compatibles(v_inter, v_apres):
            return False

        # Vérifier la compatibilité avec le service
        if not self._voyage_compatible_service(v_inter, service):
            return False

        return True

    def _calculer_score_amplitude(self, voyage, service):
        """Calcule un score bonus pour l'utilisation de l'amplitude."""
        if service.heure_debut is None or service.heure_fin is None:
            return 0

        distance_debut = voyage.hdebut - service.heure_debut
        distance_fin = service.heure_fin - voyage.hfin

        score = 0
        if distance_debut <= 120:
            score += (120 - distance_debut) // 10
        if distance_fin <= 120:
            score += (120 - distance_fin) // 10

        return score

    def construire_modele(self):
        """Construit le modèle OR-Tools avec toutes les contraintes"""

        print("🔧 Construction du modèle OR-Tools...")
        print(f"   • {len(self.voyages)} voyages à affecter")
        print(f"   • {len(self.services)} services disponibles")
        print(f"   • Pause minimum: {self.min_pause} min")
        print(f"   • Pause maximum: {self.max_pause} min")
        print(f"   • Continuité géographique: ACTIVÉE (3 premiers caractères)")

        for service in self.services:
            nb_existants = len(self.voyages_existants[service])
            if nb_existants > 0:
                print(f"   • Service {service.num_service}: {nb_existants} voyage(s) déjà affecté(s)")

        # ═══════════════════════════════════════════════════════════════
        # 1. Créer les variables de décision
        # ═══════════════════════════════════════════════════════════════
        for v_idx, voyage in enumerate(self.voyages):
            for s_idx, service in enumerate(self.services):
                var_name = f"v{v_idx}_s{s_idx}"
                self.affectations[(v_idx, s_idx)] = self.model.NewBoolVar(var_name)

        print(f"   ✓ {len(self.affectations)} variables créées")

        # ═══════════════════════════════════════════════════════════════
        # 2. Un voyage ne peut être affecté qu'à un seul service
        # ═══════════════════════════════════════════════════════════════
        for v_idx in range(len(self.voyages)):
            vars_voyage = [self.affectations[(v_idx, s_idx)]
                          for s_idx in range(len(self.services))]
            self.model.Add(sum(vars_voyage) <= 1)

        print(f"   ✓ Contraintes d'unicité ajoutées")

        # ═══════════════════════════════════════════════════════════════
        # 3. Compatibilité voyage/service (horaires)
        # ═══════════════════════════════════════════════════════════════
        nb_incompatibles = 0
        for v_idx, voyage in enumerate(self.voyages):
            for s_idx, service in enumerate(self.services):
                if not self._voyage_compatible_service(voyage, service):
                    self.model.Add(self.affectations[(v_idx, s_idx)] == 0)
                    nb_incompatibles += 1

        print(f"   ✓ {nb_incompatibles} incompatibilités horaires bloquées")

        # ═══════════════════════════════════════════════════════════════
        # 4. Compatibilité avec les voyages DÉJÀ dans le service
        # ═══════════════════════════════════════════════════════════════
        nb_conflits_existants = 0
        for v_idx, voyage in enumerate(self.voyages):
            for s_idx, service in enumerate(self.services):
                if not self._voyage_compatible_avec_existants(voyage, service):
                    self.model.Add(self.affectations[(v_idx, s_idx)] == 0)
                    nb_conflits_existants += 1

        print(f"   ✓ {nb_conflits_existants} conflits temporels avec existants bloqués")

        # ═══════════════════════════════════════════════════════════════
        # 5. Pas de chevauchement entre nouveaux voyages
        # ═══════════════════════════════════════════════════════════════
        nb_conflits_temps = 0
        for s_idx, service in enumerate(self.services):
            for v1_idx in range(len(self.voyages)):
                for v2_idx in range(v1_idx + 1, len(self.voyages)):
                    v1 = self.voyages[v1_idx]
                    v2 = self.voyages[v2_idx]

                    if not self._voyages_compatibles_temporellement(v1, v2):
                        self.model.Add(
                            self.affectations[(v1_idx, s_idx)] +
                            self.affectations[(v2_idx, s_idx)] <= 1
                        )
                        nb_conflits_temps += 1

        print(f"   ✓ {nb_conflits_temps} contraintes de chevauchement temporel")

        # ═══════════════════════════════════════════════════════════════
        # 6. CONTINUITÉ GÉOGRAPHIQUE + PAUSE MAXIMUM
        # ═══════════════════════════════════════════════════════════════
        nb_contraintes_geo = 0

        for s_idx, service in enumerate(self.services):
            # Tous les voyages (existants + nouveaux)
            tous_voyages = list(self.voyages_existants[service]) + list(self.voyages)

            for i, v1 in enumerate(tous_voyages):
                for j, v2 in enumerate(tous_voyages):
                    if i >= j:
                        continue

                    # Déterminer l'ordre temporel
                    if v1.hfin <= v2.hdebut:
                        v_avant, v_apres = v1, v2
                    elif v2.hfin <= v1.hdebut:
                        v_avant, v_apres = v2, v1
                    else:
                        # Chevauchement, déjà géré
                        continue

                    pause = v_apres.hdebut - v_avant.hfin

                    # Vérifier si les voyages peuvent être consécutifs
                    peuvent_etre_consecutifs = self._voyages_peuvent_etre_consecutifs(v_avant, v_apres)

                    # Si pause > max_pause OU arrêts incompatibles, il faut un intermédiaire
                    besoin_intermediaire = (pause > self.max_pause) or (not self._arrets_compatibles(v_avant, v_apres))

                    if besoin_intermediaire and pause >= self.min_pause:
                        # Chercher les voyages qui peuvent s'insérer
                        voyages_intermediaires = []
                        for k, v_inter in enumerate(self.voyages):
                            if v_inter == v_avant or v_inter == v_apres:
                                continue
                            if self._peut_inserer_entre(v_inter, v_avant, v_apres, service):
                                voyages_intermediaires.append(k)

                        # Déterminer si v_avant et v_apres sont existants ou nouveaux
                        v_avant_existant = v_avant in self.voyages_existants[service]
                        v_apres_existant = v_apres in self.voyages_existants[service]

                        if v_avant_existant and v_apres_existant:
                            # Les deux sont existants : il FAUT un intermédiaire
                            if voyages_intermediaires:
                                intermediaires_vars = [self.affectations[(k, s_idx)]
                                                     for k in voyages_intermediaires]
                                self.model.Add(sum(intermediaires_vars) >= 1)
                            else:
                                # Problème avec les données existantes - pas de solution possible
                                print(f"   ⚠️ Service {service.num_service}: V{v_avant.num_voyage} → V{v_apres.num_voyage} incompatibles sans intermédiaire")

                        elif v_avant_existant or v_apres_existant:
                            # Un seul est existant
                            if v_avant_existant:
                                v_apres_idx = self.voyages.index(v_apres)
                                if voyages_intermediaires:
                                    intermediaires_vars = [self.affectations[(k, s_idx)]
                                                         for k in voyages_intermediaires]
                                    self.model.Add(
                                        sum(intermediaires_vars) >= self.affectations[(v_apres_idx, s_idx)]
                                    )
                                else:
                                    self.model.Add(self.affectations[(v_apres_idx, s_idx)] == 0)
                            else:
                                v_avant_idx = self.voyages.index(v_avant)
                                if voyages_intermediaires:
                                    intermediaires_vars = [self.affectations[(k, s_idx)]
                                                         for k in voyages_intermediaires]
                                    self.model.Add(
                                        sum(intermediaires_vars) >= self.affectations[(v_avant_idx, s_idx)]
                                    )
                                else:
                                    self.model.Add(self.affectations[(v_avant_idx, s_idx)] == 0)

                        else:
                            # Les deux sont nouveaux
                            v_avant_idx = self.voyages.index(v_avant)
                            v_apres_idx = self.voyages.index(v_apres)

                            if voyages_intermediaires:
                                intermediaires_vars = [self.affectations[(k, s_idx)]
                                                     for k in voyages_intermediaires]
                                self.model.Add(
                                    self.affectations[(v_avant_idx, s_idx)] +
                                    self.affectations[(v_apres_idx, s_idx)] - 1 <=
                                    sum(intermediaires_vars)
                                )
                            else:
                                self.model.Add(
                                    self.affectations[(v_avant_idx, s_idx)] +
                                    self.affectations[(v_apres_idx, s_idx)] <= 1
                                )

                        nb_contraintes_geo += 1

        print(f"   ✓ {nb_contraintes_geo} contraintes géographiques/pause max")

        # ═══════════════════════════════════════════════════════════════
        # 7. Fonction objectif : Maximiser voyages + amplitude
        # ═══════════════════════════════════════════════════════════════
        score_affectations = []
        for v_idx, voyage in enumerate(self.voyages):
            for s_idx, service in enumerate(self.services):
                score_base = 100
                score_amplitude = self._calculer_score_amplitude(voyage, service)
                score_total = score_base + score_amplitude
                score_affectations.append(self.affectations[(v_idx, s_idx)] * score_total)

        self.model.Maximize(sum(score_affectations))

        print(f"   ✓ Fonction objectif configurée")
        print(f"🔧 Modèle construit avec succès !")

    def resoudre(self, timeout_secondes=30):
        """Résout le modèle et retourne les résultats."""
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

        self._extraire_resultats()
        self._verifier_solution()

        return True

    def _extraire_resultats(self):
        """Extrait les résultats de la solution"""

        self.voyages_affectes = {}
        for service in self.services:
            self.voyages_affectes[service] = list(self.voyages_existants[service])

        self.voyages_non_affectes = []

        for v_idx, voyage in enumerate(self.voyages):
            affecte = False
            for s_idx, service in enumerate(self.services):
                if self.solver.Value(self.affectations[(v_idx, s_idx)]) == 1:
                    self.voyages_affectes[service].append(voyage)
                    affecte = True
                    break

            if not affecte:
                self.voyages_non_affectes.append(voyage)

        for service in self.services:
            self.voyages_affectes[service].sort(key=lambda v: v.hdebut)

        total_voyages = len(self.voyages)
        total_nouveaux_affectes = sum(len(v) for v in self.voyages_affectes.values()) - sum(len(v) for v in self.voyages_existants.values())

        self.statistiques = {
            'total_voyages': total_voyages,
            'voyages_affectes': total_nouveaux_affectes,
            'voyages_non_affectes': len(self.voyages_non_affectes),
            'taux_affectation': (total_nouveaux_affectes / total_voyages * 100) if total_voyages > 0 else 0,
            'services_utilises': sum(1 for s, v in self.voyages_affectes.items() if len(v) > 0)
        }

        self.statistiques['par_service'] = {}
        for service in self.services:
            voyages = self.voyages_affectes[service]
            if voyages:
                debut = min(v.hdebut for v in voyages)
                fin = max(v.hfin for v in voyages)
                duree = fin - debut

                voyages_tries = sorted(voyages, key=lambda v: v.hdebut)
                temps_pause = 0
                pause_max_trouvee = 0
                ruptures_geo = 0

                for i in range(len(voyages_tries) - 1):
                    v_avant = voyages_tries[i]
                    v_apres = voyages_tries[i + 1]

                    pause = v_apres.hdebut - v_avant.hfin
                    if pause > 0:
                        temps_pause += pause
                        if pause > pause_max_trouvee:
                            pause_max_trouvee = pause

                    # Vérifier la continuité géographique
                    if not self._arrets_compatibles(v_avant, v_apres):
                        ruptures_geo += 1

                nb_existants = len(self.voyages_existants[service])
                nb_nouveaux = len(voyages) - nb_existants

                taux_utilisation = 0
                if service.heure_debut is not None and service.heure_fin is not None:
                    amplitude_service = service.heure_fin - service.heure_debut
                    if amplitude_service > 0:
                        taux_utilisation = (duree / amplitude_service) * 100

                self.statistiques['par_service'][service.num_service] = {
                    'nb_voyages': len(voyages),
                    'nb_existants': nb_existants,
                    'nb_nouveaux': nb_nouveaux,
                    'debut': debut,
                    'fin': fin,
                    'duree': duree,
                    'temps_pause': temps_pause,
                    'pause_max': pause_max_trouvee,
                    'taux_utilisation': taux_utilisation,
                    'ruptures_geo': ruptures_geo
                }

    def _verifier_solution(self):
        """Vérifie que la solution respecte toutes les contraintes"""
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
                    erreurs.append(f"   ⚠️ Service {service.num_service}: V{v1.num_voyage} → V{v2.num_voyage} pause {pause}min < {self.min_pause}min")
                elif pause > self.max_pause:
                    erreurs.append(f"   ⚠️ Service {service.num_service}: V{v1.num_voyage} → V{v2.num_voyage} pause {pause}min > {self.max_pause}min")

                # Vérifier la continuité géographique
                if not self._arrets_compatibles(v1, v2):
                    erreurs.append(f"   ⚠️ Service {service.num_service}: V{v1.num_voyage}({v1.arret_fin[:3]}) → V{v2.num_voyage}({v2.arret_debut[:3]}) rupture géographique!")

        if erreurs:
            print("   Problèmes détectés:")
            for e in erreurs:
                print(e)
        else:
            print("   ✅ Aucun chevauchement détecté")
            print(f"   ✅ Toutes les pauses >= {self.min_pause} min")
            print(f"   ✅ Toutes les pauses <= {self.max_pause} min")
            print("   ✅ Continuité géographique respectée")

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

        print(f"\n📋 Détail par service:")
        for service in self.services:
            voyages = self.voyages_affectes[service]
            print(f"\n   🚌 Service {service.num_service} ({service.type_service}):")

            if voyages and service.num_service in self.statistiques.get('par_service', {}):
                stats = self.statistiques['par_service'][service.num_service]
                h_debut = f"{stats['debut'] // 60:02d}h{stats['debut'] % 60:02d}"
                h_fin = f"{stats['fin'] // 60:02d}h{stats['fin'] % 60:02d}"

                print(f"      • {stats['nb_voyages']} voyages")
                print(f"      • Plage: {h_debut} - {h_fin}")
                print(f"      • Amplitude utilisée: {stats['taux_utilisation']:.0f}%")
                print(f"      • Pause max: {stats['pause_max']} min")
                if stats['ruptures_geo'] > 0:
                    print(f"      • ⚠️ Ruptures géo: {stats['ruptures_geo']}")
            else:
                print(f"      • Aucun voyage")

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
            if service.num_service in self.statistiques.get('par_service', {}):
                stats = self.statistiques['par_service'][service.num_service]
                rapport.append(f"Service {service.num_service}: {stats['nb_voyages']} voyages | Amplitude: {stats['taux_utilisation']:.0f}%")

        if self.voyages_non_affectes:
            rapport.append("")
            rapport.append(f"Non affectés: {len(self.voyages_non_affectes)} voyages")

        return "\n".join(rapport)

    def get_nouveaux_voyages_par_service(self):
        """Retourne uniquement les NOUVEAUX voyages affectés."""
        nouveaux = {}
        for service in self.services:
            nouveaux[service] = []
            for v in self.voyages_affectes[service]:
                if v not in self.voyages_existants[service]:
                    nouveaux[service].append(v)
        return nouveaux


def optimiser_services(voyages_disponibles, services, min_pause=5, max_pause=60, timeout=30):
    """Fonction utilitaire pour lancer l'optimisation."""
    solver = SolverOrTools(voyages_disponibles, services, min_pause, max_pause)
    solver.construire_modele()
    solver.resoudre(timeout)

    return solver