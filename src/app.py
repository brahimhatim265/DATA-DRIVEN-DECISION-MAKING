"""
Dashboard décisionnel Olist  (src/app.py)

Lit deux fichiers depuis data/processed/ (le contrat de données convenu) :
  - predictions.csv : order_id, delay_risk_proba, predicted_late,
                      top_risk_factor_1, top_risk_factor_2,
                      customer_state, product_category
  - master.csv      : order_id, price, freight_value, ... , is_late

Les deux fichiers sont joints sur order_id. Pour l'instant ce sont des
données factices (mock) produites par generate_mock_data.py. Quand Brahim
fournira le VRAI predictions.csv, rien ne change ici -- il suffit de
remplacer le fichier.

Lancer depuis la racine du projet :
    streamlit run src/app.py
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st

# ---- Hypothèses économiques -- MÊMES chiffres que la Phase 1 ----
LTV = 150.0          # R$ valeur à vie d'un client sauvé (Phase 1)
COUPON_COST = 20.0   # R$ coût d'un coupon proactif (Phase 1)
SAVE_RATE = 0.20     # part des clients à risque sauvés par l'intervention (Phase 1)

# ---- Traduction des facteurs de risque (issus de SHAP) en libellés lisibles ----
LIBELLES_FACTEURS = {
    "long_distance": "Longue distance",
    "near_holiday": "Proximité d'un jour férié",
    "low_gdp_region": "Région à faible PIB",
    "heavy_freight": "Frais de port élevés",
    "bulky_category": "Catégorie volumineuse",
}

DATA_DIR = os.path.join("data", "processed")

st.set_page_config(page_title="Olist — Dashboard retards & churn",
                   page_icon="📦", layout="wide")


@st.cache_data
def load_data():
    pred_path = os.path.join(DATA_DIR, "predictions.csv")
    master_path = os.path.join(DATA_DIR, "master.csv")
    if not os.path.exists(pred_path):
        return None
    df = pd.read_csv(pred_path)
    if os.path.exists(master_path):
        master = pd.read_csv(master_path)
        keep = [c for c in ["order_id", "price", "freight_value",
                            "is_near_holiday", "is_late"] if c in master.columns]
        df = df.merge(master[keep], on="order_id", how="left")
    if "price" not in df.columns:
        df["price"] = LTV  # valeur de secours si master absent
    return df


df = load_data()
if df is None:
    st.error("Aucune donnée trouvée. Lancez d'abord "
             "`python generate_mock_data.py` "
             "(ou déposez le vrai predictions.csv de Brahim dans data/processed/).")
    st.stop()

# ---- Barre latérale : profil + contrôles ----
st.sidebar.title("📦 Dashboard décisionnel Olist")
profile = st.sidebar.radio("Vue par profil", ["Direction", "Opérations", "Marketing"])
threshold = st.sidebar.slider("Seuil de risque élevé (probabilité de retard)",
                              0.1, 0.9, 0.7, 0.05)
all_states = sorted(df["customer_state"].unique())
states = st.sidebar.multiselect("Filtrer par état", all_states, default=all_states)
st.sidebar.caption("Source : data/processed/predictions.csv")

view = df[df["customer_state"].isin(states)].copy()
view["high_risk"] = view["delay_risk_proba"] >= threshold

# Calculs décisionnels partagés -- mêmes hypothèses que la Phase 1,
# appliquées par commande en utilisant le score de risque du modèle.
high = view[view["high_risk"]]
coupons = len(high)                                     # un coupon par commande à risque
customers_saved = (high["delay_risk_proba"] * SAVE_RATE).sum()
revenue_saved = customers_saved * LTV
coupon_budget = coupons * COUPON_COST
net_savings = revenue_saved - coupon_budget
revenue_at_risk = high["delay_risk_proba"].sum() * LTV  # clients perdus attendus x LTV


def by_state_risk():
    g = view.groupby("customer_state").agg(
        commandes=("order_id", "count"),
        risque_moyen=("delay_risk_proba", "mean")).reset_index()
    return g.sort_values("risque_moyen", ascending=False)


# ============================ DIRECTION ============================
if profile == "Direction":
    st.title("Vue Direction")
    st.caption("Où perdons-nous des clients à cause des retards, et combien ça coûte ?")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Commandes analysées", f"{len(view):,}")
    c2.metric("Commandes à risque élevé", f"{coupons:,}",
              f"{coupons/len(view):.1%} du total")
    c3.metric("Revenu à risque", f"R$ {revenue_at_risk:,.0f}")
    c4.metric("Économies nettes projetées", f"R$ {net_savings:,.0f}",
              help="Un coupon est envoyé à chaque commande au-dessus du seuil. "
                   "Augmenter le seuil pour ne cibler que les commandes les plus "
                   "risquées, où chaque coupon rapporte plus qu'il ne coûte.")

    st.subheader("Vue 1 — Risque moyen de retard par état")
    g = by_state_risk()
    fig = px.bar(g, x="customer_state", y="risque_moyen",
                 color="risque_moyen", color_continuous_scale="Reds",
                 labels={"risque_moyen": "Risque moyen", "customer_state": "État"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Vue 2 — Où se concentre le revenu à risque")
    g2 = (high.groupby("customer_state")["delay_risk_proba"].sum() * LTV) \
        .reset_index(name="revenu_a_risque") \
        .sort_values("revenu_a_risque", ascending=False)
    st.plotly_chart(px.bar(g2.head(10), x="customer_state", y="revenu_a_risque",
                           labels={"customer_state": "État",
                                   "revenu_a_risque": "Revenu à risque (R$)"}),
                    use_container_width=True)

# ============================ OPÉRATIONS ============================
elif profile == "Opérations":
    st.title("Vue Opérations")
    st.caption("Quels itinéraires, régions et catégories de produits causent les retards ?")

    st.subheader("Vue 3 — États les plus risqués (où recruter des transporteurs en priorité)")
    g = by_state_risk().head(10)
    st.plotly_chart(
        px.bar(g, x="risque_moyen", y="customer_state", orientation="h",
               color="risque_moyen", color_continuous_scale="Oranges",
               labels={"risque_moyen": "Risque moyen", "customer_state": "État"}),
        use_container_width=True)

    st.subheader("Vue 4 — Risque de retard par catégorie de produit")
    gc = view.groupby("product_category")["delay_risk_proba"].mean() \
        .reset_index().sort_values("delay_risk_proba", ascending=False)
    st.plotly_chart(px.bar(gc, x="product_category", y="delay_risk_proba",
                           labels={"product_category": "Catégorie",
                                   "delay_risk_proba": "Risque moyen"}),
                    use_container_width=True)

    if "is_near_holiday" in view.columns:
        st.subheader("Vue 5 — L'effet des jours fériés")
        gh = view.groupby("is_near_holiday")["delay_risk_proba"].mean().reset_index()
        gh["is_near_holiday"] = gh["is_near_holiday"].map(
            {0: "Période normale", 1: "Près d'un férié"})
        st.plotly_chart(px.bar(gh, x="is_near_holiday", y="delay_risk_proba",
                               labels={"is_near_holiday": "Période",
                                       "delay_risk_proba": "Risque moyen"}),
                        use_container_width=True)

    st.subheader("Facteurs de risque les plus fréquents")
    drivers = pd.concat([view["top_risk_factor_1"], view["top_risk_factor_2"]])
    drivers = drivers.map(lambda x: LIBELLES_FACTEURS.get(x, x))
    counts = drivers.value_counts().reset_index()
    counts.columns = ["facteur", "occurrences"]
    st.plotly_chart(px.bar(counts, x="occurrences", y="facteur", orientation="h",
                           labels={"occurrences": "Occurrences",
                                   "facteur": "Facteur"}),
                    use_container_width=True)

# ============================ MARKETING ============================
else:
    st.title("Marketing — rétention proactive")
    st.caption("Qui contacter, et combien on économise grâce à l'intervention ?")

    c1, c2, c3 = st.columns(3)
    c1.metric("Clients à contacter", f"{coupons:,}")
    c2.metric("Budget coupons", f"R$ {coupons * COUPON_COST:,.0f}")
    c3.metric("Économies nettes", f"R$ {net_savings:,.0f}")

    st.subheader("Vue 6 — Commandes à risque à cibler")
    cols = ["order_id", "customer_state", "product_category",
            "delay_risk_proba", "top_risk_factor_1", "top_risk_factor_2"]
    target = high[cols].sort_values("delay_risk_proba", ascending=False).copy()
    target["top_risk_factor_1"] = target["top_risk_factor_1"].map(
        lambda x: LIBELLES_FACTEURS.get(x, x))
    target["top_risk_factor_2"] = target["top_risk_factor_2"].map(
        lambda x: LIBELLES_FACTEURS.get(x, x))
    target["Action recommandée"] = "Envoyer coupon d'excuse + ajuster la promesse de livraison"

    display = target.rename(columns={
        "order_id": "ID commande",
        "customer_state": "État client",
        "product_category": "Catégorie produit",
        "delay_risk_proba": "Probabilité de retard",
        "top_risk_factor_1": "Facteur de risque 1",
        "top_risk_factor_2": "Facteur de risque 2",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.download_button("Télécharger la liste cible (CSV)",
                       display.to_csv(index=False).encode("utf-8"),
                       "cibles_risque_eleve.csv", "text/csv")