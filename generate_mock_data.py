"""
generate_mock_data.py  --  DONNÉES FACTICES / PLACEHOLDER UNIQUEMENT

Crée des fichiers `master.csv` et `predictions.csv` factices respectant le
contrat de colonnes convenu avec Brahim, afin de construire le dashboard
en parallèle.

>>> À SUPPRIMER une fois les vraies données + prédictions de Brahim prêtes. <<<

Lancer depuis la racine du projet :
    python generate_mock_data.py
Les deux fichiers sont écrits dans data/processed/.
"""

import os
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
N = 8000  # enough rows for nice charts; the real dataset will be ~100k

# Brazilian states: (sampling weight, gdp_per_capita_proxy, urbanization, base difficulty)
# Higher difficulty = poorer infrastructure / further from the SP-SE hub.
STATES = {
    "SP": (0.34, 58000, 0.96, 0.10),
    "RJ": (0.13, 46000, 0.97, 0.18),
    "MG": (0.11, 32000, 0.85, 0.22),
    "RS": (0.06, 41000, 0.85, 0.24),
    "PR": (0.06, 43000, 0.85, 0.23),
    "SC": (0.05, 44000, 0.84, 0.22),
    "BA": (0.05, 21000, 0.72, 0.40),
    "DF": (0.04, 88000, 0.97, 0.15),
    "ES": (0.03, 30000, 0.83, 0.26),
    "GO": (0.03, 29000, 0.90, 0.30),
    "PE": (0.03, 20000, 0.80, 0.42),
    "CE": (0.03, 18000, 0.75, 0.45),
    "PA": (0.02, 19000, 0.68, 0.55),
    "AM": (0.01, 24000, 0.79, 0.58),
    "MA": (0.01, 14000, 0.63, 0.60),
}
CATEGORIES = [
    "bed_bath_table", "health_beauty", "sports_leisure", "furniture_decor",
    "computers_accessories", "housewares", "watches_gifts", "toys",
    "garden_tools", "auto",
]
# Some categories are bulkier -> more freight -> slightly more delay risk
HEAVY_CATS = {"furniture_decor", "garden_tools", "auto"}

state_codes = list(STATES.keys())
weights = np.array([STATES[s][0] for s in state_codes])
weights = weights / weights.sum()


def build_master():
    cust = RNG.choice(state_codes, size=N, p=weights)
    sell = RNG.choice(state_codes, size=N, p=weights)
    cat = RNG.choice(CATEGORIES, size=N)

    gdp = np.array([STATES[s][1] for s in cust])
    urb = np.array([STATES[s][2] for s in cust])
    cust_diff = np.array([STATES[s][3] for s in cust])

    # distance: small if same state, larger across regions
    same = cust == sell
    distance = np.where(
        same,
        RNG.uniform(20, 350, N),
        RNG.uniform(300, 3200, N),
    ).round(0)

    price = RNG.gamma(2.0, 60, N).round(2)
    freight = (price * RNG.uniform(0.05, 0.25, N)
               + np.where(np.isin(cat, list(HEAVY_CATS)), RNG.uniform(15, 45, N), 0)).round(2)
    n_items = RNG.choice([1, 1, 1, 2, 2, 3], size=N)

    dow = RNG.integers(0, 7, N)
    month = RNG.integers(1, 13, N)
    days_to_holiday = RNG.integers(0, 30, N)
    near_holiday = (days_to_holiday <= 5).astype(int)

    # latent delay risk -> drives the label and review score
    z = (-3.2
         + 2.2 * cust_diff
         + 0.0006 * distance
         + 0.9 * near_holiday
         + 0.4 * np.isin(cat, list(HEAVY_CATS))
         - 0.000004 * gdp)
    p_late = 1 / (1 + np.exp(-z))
    is_late = (RNG.uniform(0, 1, N) < p_late).astype(int)

    # reviews: late orders skew low (this is what feeds the churn proxy)
    review = np.where(
        is_late == 1,
        RNG.choice([1, 2, 3, 4, 5], N, p=[0.34, 0.26, 0.20, 0.12, 0.08]),
        RNG.choice([1, 2, 3, 4, 5], N, p=[0.04, 0.06, 0.12, 0.30, 0.48]),
    )

    df = pd.DataFrame({
        "order_id": [f"ord_{i:06d}" for i in range(N)],
        "customer_state": cust,
        "seller_state": sell,
        "product_category": cat,
        "price": price,
        "freight_value": freight,
        "n_items": n_items,
        "distance_km": distance,
        "purchase_dow": dow,
        "purchase_month": month,
        "days_to_next_holiday": days_to_holiday,
        "is_near_holiday": near_holiday,
        "state_gdp": gdp,
        "state_urbanization": urb,
        "review_score": review,
        "is_late": is_late,
    })
    df.attrs["p_late"] = p_late
    return df, p_late


def build_predictions(master, p_late):
    # A fake "model": its predicted probability is the true risk plus noise.
    proba = np.clip(p_late + RNG.normal(0, 0.08, len(master)), 0.01, 0.99).round(3)
    predicted_late = (proba >= 0.5).astype(int)

    # Fake SHAP-style top factors, chosen from the real drivers of each row
    cust_diff = np.array([STATES[s][3] for s in master["customer_state"]])
    factors = []
    for i in range(len(master)):
        scores = {
            "long_distance": master["distance_km"].iloc[i] / 3200,
            "near_holiday": 0.9 if master["is_near_holiday"].iloc[i] else 0.0,
            "low_gdp_region": cust_diff[i],
            "heavy_freight": min(master["freight_value"].iloc[i] / 80, 1.0),
            "bulky_category": 0.6 if master["product_category"].iloc[i] in HEAVY_CATS else 0.0,
        }
        top2 = sorted(scores, key=scores.get, reverse=True)[:2]
        factors.append(top2)

    return pd.DataFrame({
        "order_id": master["order_id"],
        "delay_risk_proba": proba,
        "predicted_late": predicted_late,
        "top_risk_factor_1": [f[0] for f in factors],
        "top_risk_factor_2": [f[1] for f in factors],
        "customer_state": master["customer_state"],
        "product_category": master["product_category"],
    })


def main():
    out = os.path.join("data", "processed")
    os.makedirs(out, exist_ok=True)
    master, p_late = build_master()
    preds = build_predictions(master, p_late)
    master.to_csv(os.path.join(out, "master.csv"), index=False)
    preds.to_csv(os.path.join(out, "predictions.csv"), index=False)
    print(f"{len(master)} lignes écrites -> {out}/master.csv et predictions.csv")
    print(f"  Taux de retard simulé : {master['is_late'].mean():.1%}")
    print(f"  Taux de retard prédit : {preds['predicted_late'].mean():.1%}")
    print("  RAPPEL : ce sont des données factices. Les remplacer plus tard "
          "par les vrais fichiers de Brahim.")


if __name__ == "__main__":
    main()