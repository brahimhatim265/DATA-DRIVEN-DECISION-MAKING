# Phase 6 : Plan A/B Test — Intervention proactive par coupon

## 1. Contexte et objectif

Notre modèle de prédiction des retards attribue à chaque nouvelle commande une probabilité `delay_risk_proba`. La décision opérationnelle évaluée par ce test : **envoyer un coupon d'excuse proactif de 20 BRL aux commandes classées à risque, dès la passation de la commande**, pour réduire la perte de clients (churn proxy : note ≤ 2 après retard).

L'objectif est de **mesurer rigoureusement l'effet causal de cette intervention** sur le churn proxy, et non de se contenter d'une estimation théorique.

## 2. Hypothèses

- **H0 (nulle)** : l'envoi proactif d'un coupon aux commandes à risque ne change PAS le taux de churn proxy.  
  *taux_churn(traitement) = taux_churn(contrôle).*
- **H1 (alternative)** : l'envoi proactif réduit le taux de churn proxy.  
  *taux_churn(traitement) < taux_churn(contrôle).*

**Cible business** : réduction relative du churn proxy de **15 % à 25 %** parmi les commandes ciblées.

## 3. Population et randomisation

- **Population éligible** : toutes les nouvelles commandes dont `delay_risk_proba ≥ 0,67`. Ce seuil correspond au point de rentabilité individuel de l'intervention : pour une commande de risque 0,67, le gain attendu (`0,67 × 0,20 × 150 ≈ 20,1 BRL`) dépasse tout juste le coût du coupon (20 BRL). En-dessous, l'intervention détruit de la valeur.
- **Allocation aléatoire 50/50** au niveau de la commande, via un hash déterministe de l'`order_id` (reproductible, sans biais d'allocation).
- **Groupes** :
  - **Contrôle** : aucune action (statu quo).
  - **Traitement** : coupon d'excuse de 20 BRL envoyé immédiatement + message d'ajustement de la promesse de livraison.

```mermaid
flowchart LR
    A[Nouvelle commande] --> B{delay_risk_proba >= 0,67 ?}
    B -- Non --> Z[Hors test]
    B -- Oui --> C{Randomisation 50/50}
    C --> Ctrl[Groupe Contrôle<br/>Aucune action]
    C --> Trt[Groupe Traitement<br/>Coupon 20 BRL<br/>+ message proactif]
    Ctrl --> M[Mesure du churn proxy<br/>note <= 2 + retard<br/>fenêtre 30 jours]
    Trt --> M
    M --> D[z-test à deux proportions]
```

## 4. Métriques

- **Métrique principale** : taux de churn proxy = part des commandes avec retard ET note ≤ 2.  
  *Fenêtre de mesure : 30 jours après la date de livraison estimée.*
- **Métriques secondaires** :
  - Note moyenne de l'avis client (échelle 1–5).
  - Taux de ré-achat à 90 jours.
  - Delivery gap moyen (date réelle − date estimée), pour vérifier que les retards eux-mêmes ne sont pas affectés par l'intervention.
- **Garde-fous (guardrails)** :
  - Coût total des coupons ≤ revenu LTV récupéré (rentabilité globale du test).
  - Pas d'augmentation > 10 % des plaintes service client.

## 5. Taille d'échantillon (calcul de puissance)

**Hypothèses du calcul** :
- Taux de churn proxy baseline (groupe contrôle) parmi les commandes high-risk : **30 %** (estimation à recalibrer une fois les métriques du modèle gagnant disponibles).
- Effet minimum détectable (MDE) : **20 % relatif** (centre de la cible 15–25 %) — on cherche à détecter une baisse de 30 % → 24 %.
- α = 0,05 (bilatéral), puissance = 80 %.
- Test : z-test à deux proportions.

**Résultat** :

$$n_{\text{par groupe}} = \frac{(z_{\alpha/2} + z_{\beta})^2 \cdot (p_1(1-p_1) + p_2(1-p_2))}{(p_1 - p_2)^2} \approx 855$$

Soit **environ 1 700 commandes au total**. On retient une cible opérationnelle de **1 000 par groupe (~2 000 au total)** pour absorber les pertes (commandes annulées, données manquantes).

## 6. Durée du test

Avec un volume Olist d'environ 100 000 commandes/an (~275/jour) et une proportion estimée de 10 à 15 % de commandes high-risk au seuil 0,67, on a environ **30 à 40 commandes éligibles par jour**. Pour atteindre 2 000 randomisations :

- **Durée estimée : 7 à 8 semaines.**
- Cette estimation sera recalibrée dès que nous aurons le vrai taux de high-risk sur les données réelles.

## 7. Règle de décision

À la fin de la période :
- **Rejet de H0 si** : p-value < 0,05 **ET** baisse observée du churn proxy ≥ 15 % en relatif (cible business basse) **ET** économies nettes > 0 (selon LTV 150 / coupon 20).
- **Si H0 rejetée** → déploiement du programme à toutes les commandes high-risk.
- **Si H0 non rejetée** → itération sur les leviers : montant du coupon, contenu du message, ou seuil de risque.

## 8. Risques et biais

- **Spillover** : faible (commandes indépendantes, pas d'effet réseau entre clients).
- **Saisonnalité** : neutralisée par la randomisation 50/50 dans la même fenêtre temporelle (les deux groupes subissent les mêmes jours fériés).
- **Effet Hawthorne** : improbable car l'intervention est silencieuse côté client (réception d'un coupon, pas d'avis d'expérimentation).
- **P-hacking** : pré-enregistrement obligatoire du plan d'analyse avant le démarrage (métrique principale, seuil de significativité, durée). Pas d'analyses intermédiaires non planifiées.

## 9. Prochaines étapes

1. Finaliser les métriques (Precision / Recall / F1) du modèle gagnant et le taux réel de commandes high-risk.
2. Recalibrer la baseline de churn proxy et la taille d'échantillon.
3. Implémenter le code de randomisation dans `src/randomizer.py` (hash déterministe d'`order_id`).
4. Coordonner avec l'équipe Marketing pour le canal d'envoi du coupon.
5. Pré-enregistrer le plan d'analyse, puis lancer le test.