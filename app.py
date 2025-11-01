import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuration
st.set_page_config(
    page_title="Mobilité Pays Basque 2050",
    page_icon="🚗",
    layout="wide"
)

# ==================== INITIALISATION ====================
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    
    # Situation 2023 - Habitant moyen Pays Basque
    st.session_state.km_2023 = {
        'voiture': 150,
        'bus': 25,
        'train': 8,
        'velo': 20,
        'marche': 10
    }
    
    # Facteurs d'émission (étudiants complèteront)
    st.session_state.emissions = {
        'voiture': 193,  # À compléter par étudiants
        'bus': 103,
        'train': 2.4,
        'velo': 0,
        'marche': 0
    }
    
    # Scénario 2050
    st.session_state.scenario = {
        'reduction_km': 0,
        'report_velo': 0,
        'report_bus': 0,
        'report_train': 0,
        'part_ve': 3,
        'part_thermique': 97
    }

# ==================== FONCTIONS ====================

def calculer_bilan(km_dict, emissions_dict):
    """Calcule CO2 total"""
    co2_hebdo = sum(km_dict[mode] * emissions_dict[mode] for mode in km_dict) / 1000
    return {
        'co2_hebdo': co2_hebdo,
        'co2_annuel': co2_hebdo * 52,
        'km_total': sum(km_dict.values())
    }

def calculer_2050():
    """Calcule scénario 2050"""
    # 1. Réduction globale
    km_total_2023 = sum(st.session_state.km_2023.values())
    km_total_2050 = km_total_2023 * (1 + st.session_state.scenario['reduction_km'] / 100)
    
    # 2. Parts modales 2023 (%)
    part_voiture_2023 = (st.session_state.km_2023['voiture'] / km_total_2023) * 100
    part_bus_2023 = (st.session_state.km_2023['bus'] / km_total_2023) * 100
    part_train_2023 = (st.session_state.km_2023['train'] / km_total_2023) * 100
    part_velo_2023 = (st.session_state.km_2023['velo'] / km_total_2023) * 100
    part_marche_2023 = (st.session_state.km_2023['marche'] / km_total_2023) * 100
    
    # 3. Report modal
    report_total = (st.session_state.scenario['report_velo'] + 
                    st.session_state.scenario['report_bus'] + 
                    st.session_state.scenario['report_train'])
    
    part_voiture_2050 = max(0, part_voiture_2023 - report_total)
    part_bus_2050 = part_bus_2023 + st.session_state.scenario['report_bus']
    part_train_2050 = part_train_2023 + st.session_state.scenario['report_train']
    part_velo_2050 = part_velo_2023 + st.session_state.scenario['report_velo']
    part_marche_2050 = part_marche_2023
    
    # 4. Km absolus 2050
    km_2050 = {
        'voiture': km_total_2050 * part_voiture_2050 / 100,
        'bus': km_total_2050 * part_bus_2050 / 100,
        'train': km_total_2050 * part_train_2050 / 100,
        'velo': km_total_2050 * part_velo_2050 / 100,
        'marche': km_total_2050 * part_marche_2050 / 100
    }
    
    # 5. Émissions voiture 2050 (mix énergétique)
    # Émission VE = 103 gCO2/km (ADEME)
    emission_voiture_2050 = (
        (st.session_state.scenario['part_thermique'] / 100) * st.session_state.emissions['voiture'] +
        (st.session_state.scenario['part_ve'] / 100) * 103
    )
    
    # 6. Émissions totales 2050
    emissions_2050 = st.session_state.emissions.copy()
    emissions_2050['voiture'] = emission_voiture_2050
    
    bilan_2050 = calculer_bilan(km_2050, emissions_2050)
    
    # 7. Calcul réduction
    bilan_2023 = calculer_bilan(st.session_state.km_2023, st.session_state.emissions)
    reduction_pct = ((bilan_2023['co2_hebdo'] - bilan_2050['co2_hebdo']) / bilan_2023['co2_hebdo']) * 100
    
    return {
        'km_2050': km_2050,
        'bilan_2050': bilan_2050,
        'bilan_2023': bilan_2023,
        'reduction_pct': reduction_pct,
        'objectif_atteint': reduction_pct >= 80
    }

# ==================== INTERFACE ====================

st.title("🚗 Mobilité Pays Basque 2050")
st.markdown("**Outil pédagogique simplifié** • Construisez votre scénario de transition")

# ==================== ÉTAPE 1 : DIAGNOSTIC 2023 ====================

st.header("📍 Étape 1 : Diagnostic 2023")
st.info("**Habitant moyen du Pays Basque** (300 000 habitants)")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🚶 Distances hebdomadaires (km)")
    
    st.session_state.km_2023['voiture'] = st.number_input(
        "🚗 Voiture",
        min_value=0, max_value=500, value=st.session_state.km_2023['voiture'],
        step=10, key="km_voiture"
    )
    
    st.session_state.km_2023['bus'] = st.number_input(
        "🚌 Bus / TC urbains",
        min_value=0, max_value=200, value=st.session_state.km_2023['bus'],
        step=5, key="km_bus"
    )
    
    st.session_state.km_2023['train'] = st.number_input(
        "🚆 Train",
        min_value=0, max_value=100, value=st.session_state.km_2023['train'],
        step=5, key="km_train"
    )
    
    st.session_state.km_2023['velo'] = st.number_input(
        "🚴 Vélo",
        min_value=0, max_value=100, value=st.session_state.km_2023['velo'],
        step=5, key="km_velo"
    )
    
    st.session_state.km_2023['marche'] = st.number_input(
        "🚶 Marche",
        min_value=0, max_value=50, value=st.session_state.km_2023['marche'],
        step=5, key="km_marche"
    )

with col2:
    st.subheader("⚠️ Facteurs d'émission (gCO₂/km)")
    st.caption("Complétez avec les données ADEME : [impactco2.fr](https://impactco2.fr/outils/transport)")
    
    st.session_state.emissions['voiture'] = st.number_input(
        "🚗 Voiture thermique (diesel/essence)",
        min_value=0, max_value=500, value=st.session_state.emissions['voiture'],
        step=10, key="em_voiture",
        help="Moyenne France : 193 gCO2/km"
    )
    
    st.session_state.emissions['bus'] = st.number_input(
        "🚌 Bus",
        min_value=0, max_value=300, value=st.session_state.emissions['bus'],
        step=10, key="em_bus",
        help="ADEME : 103 gCO2/km"
    )
    
    st.session_state.emissions['train'] = st.number_input(
        "🚆 Train",
        min_value=0.0, max_value=50.0, value=st.session_state.emissions['train'],
        step=0.5, key="em_train",
        help="ADEME : 2.4 gCO2/km"
    )
    
    st.info("Vélo et marche : 0 gCO₂/km")

# Calcul bilan 2023
bilan_2023 = calculer_bilan(st.session_state.km_2023, st.session_state.emissions)

st.divider()

# Affichage bilan 2023
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Km total/semaine", f"{bilan_2023['km_total']:.0f} km")
with col2:
    st.metric("🌍 CO₂/semaine", f"{bilan_2023['co2_hebdo']:.1f} kg")
with col3:
    st.metric("📅 CO₂/an", f"{bilan_2023['co2_annuel']:.0f} kg", help="Base de référence 2023")

# ==================== ÉTAPE 2 : SCÉNARIO 2050 ====================

st.divider()
st.header("🎯 Étape 2 : Construire le scénario 2050")

st.warning("**Objectif SNBC : -80% d'émissions CO₂ d'ici 2050**")

# Leviers
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔧 Levier 1 : Sobriété")
    st.session_state.scenario['reduction_km'] = st.slider(
        "Réduction des km totaux (%)",
        min_value=-40, max_value=10, value=st.session_state.scenario['reduction_km'],
        step=5, key="lever_reduction",
        help="Négatif = moins de km parcourus"
    )
    
    st.divider()
    
    st.subheader("🔧 Levier 2 : Report modal")
    st.caption("% de la part modale voiture transférée vers :")
    
    st.session_state.scenario['report_velo'] = st.slider(
        "→ Vélo",
        min_value=0, max_value=30, value=st.session_state.scenario['report_velo'],
        step=5, key="lever_velo"
    )
    
    st.session_state.scenario['report_bus'] = st.slider(
        "→ Bus/TC",
        min_value=0, max_value=25, value=st.session_state.scenario['report_bus'],
        step=5, key="lever_bus"
    )
    
    st.session_state.scenario['report_train'] = st.slider(
        "→ Train",
        min_value=0, max_value=20, value=st.session_state.scenario['report_train'],
        step=5, key="lever_train"
    )
    
    report_total = (st.session_state.scenario['report_velo'] + 
                    st.session_state.scenario['report_bus'] + 
                    st.session_state.scenario['report_train'])
    st.info(f"**Report total : {report_total}%**")

with col2:
    st.subheader("🔧 Levier 3 : Électrification")
    st.caption("Composition du parc automobile en 2050")
    
    st.session_state.scenario['part_ve'] = st.slider(
        "Véhicules électriques (%)",
        min_value=0, max_value=100, value=st.session_state.scenario['part_ve'],
        step=5, key="lever_ve",
        help="VE : 20 gCO2/km (ADEME)"
    )
    
    st.session_state.scenario['part_thermique'] = 100 - st.session_state.scenario['part_ve']
    
    st.info(f"**Thermique restant : {st.session_state.scenario['part_thermique']}%**")
    
    st.divider()
    
    # Bouton reset
    if st.button("🔄 Réinitialiser le scénario", use_container_width=True):
        st.session_state.scenario = {
            'reduction_km': 0,
            'report_velo': 0,
            'report_bus': 0,
            'report_train': 0,
            'part_ve': 3,
            'part_thermique': 97
        }
        st.rerun()

# ==================== RÉSULTATS ====================

st.divider()
st.header("📊 Résultats du scénario 2050")

# Calcul
resultats = calculer_2050()

# Métriques principales
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "🌍 Émissions CO₂ 2050",
        f"{resultats['bilan_2050']['co2_annuel']:.0f} kg/an",
        f"{resultats['reduction_pct']:.0f}% vs 2023",
        delta_color="inverse"
    )

with col2:
    if resultats['objectif_atteint']:
        st.success("✅ **Objectif SNBC atteint !**")
    else:
        st.error(f"❌ **Objectif non atteint**\n\nBesoin : -80%\nActuel : {resultats['reduction_pct']:.0f}%")

with col3:
    st.metric(
        "🚗 Part véhicules électriques",
        f"{st.session_state.scenario['part_ve']}%"
    )

st.divider()

# Graphique comparaison
col1, col2 = st.columns(2)

with col1:
    st.subheader("📉 Évolution des émissions")
    
    df_emissions = pd.DataFrame({
        'Année': ['2023', '2050'],
        'CO₂ (kg/an)': [
            resultats['bilan_2023']['co2_annuel'],
            resultats['bilan_2050']['co2_annuel']
        ]
    })
    
    fig1 = px.bar(
        df_emissions,
        x='Année',
        y='CO₂ (kg/an)',
        text='CO₂ (kg/an)',
        color='Année',
        color_discrete_map={'2023': '#94a3b8', '2050': '#3b82f6'}
    )
    fig1.update_traces(texttemplate='%{text:.0f} kg', textposition='outside')
    fig1.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("🚦 Parts modales 2050")
    
    df_modal = pd.DataFrame({
        'Mode': ['Voiture', 'Bus/TC', 'Train', 'Vélo', 'Marche'],
        'Km/semaine': [
            resultats['km_2050']['voiture'],
            resultats['km_2050']['bus'],
            resultats['km_2050']['train'],
            resultats['km_2050']['velo'],
            resultats['km_2050']['marche']
        ]
    })
    
    fig2 = px.pie(
        df_modal,
        values='Km/semaine',
        names='Mode',
        hole=0.4
    )
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)

# ==================== QUESTIONS PÉDAGOGIQUES ====================

st.divider()
st.header("💡 Questions pour le débat")

with st.expander("❓ Votre scénario atteint-il l'objectif ?", expanded=not resultats['objectif_atteint']):
    if resultats['objectif_atteint']:
        st.success("✅ Bravo ! Votre scénario atteint -80% d'émissions.")
        st.write("**Questions :** Quels leviers ont été les plus efficaces ? Ce scénario est-il réaliste ?")
    else:
        st.error(f"❌ Réduction actuelle : {resultats['reduction_pct']:.0f}% (objectif : -80%)")
        st.write("**Questions :** Quels leviers faut-il actionner davantage ? Quels compromis accepter ?")

with st.expander("❓ L'électrification est-elle suffisante ?"):
    st.write(f"""
    Votre scénario : **{st.session_state.scenario['part_ve']}% de véhicules électriques**
    
    **À discuter :**
    - Peut-on atteindre -80% uniquement avec l'électrification ?
    - Quels défis : production électrique, bornes de recharge, ressources (lithium) ?
    - Émission VE = 20 gCO2/km vs thermique = {st.session_state.emissions['voiture']} gCO2/km
    """)

with st.expander("❓ Le report modal est-il réaliste ?"):
    report_total = (st.session_state.scenario['report_velo'] + 
                    st.session_state.scenario['report_bus'] + 
                    st.session_state.scenario['report_train'])
    st.write(f"""
    Votre scénario : **{report_total}% de report modal**
    
    **À discuter :**
    - Quelles infrastructures nécessaires ? (pistes cyclables, lignes de bus, trains)
    - Acceptabilité sociale : les gens acceptent-ils de changer leurs habitudes ?
    - Contexte Pays Basque : relief montagneux, habitat dispersé. Quel impact ?
    """)

with st.expander("❓ La sobriété est-elle incontournable ?"):
    st.write(f"""
    Votre scénario : **{st.session_state.scenario['reduction_km']:+}% de km parcourus**
    
    **À discuter :**
    - Peut-on atteindre -80% sans réduire les km parcourus ?
    - Comment réduire : télétravail, relocalisations, urbanisme des courtes distances ?
    - Quels freins sociaux, économiques, culturels ?
    """)

# ==================== POINTS CLÉS ====================

st.divider()
st.info("""
**💡 Points clés à retenir :**

1. **Pas de solution miracle** : Un seul levier ne suffit pas. Il faut combiner sobriété, report modal et électrification.

2. **L'électrification a des limites** : Production électrique, réseaux, ressources, coût...

3. **La sobriété est difficile mais efficace** : Réduire la demande = levier le plus puissant mais le moins accepté.

4. **Penser territoire** : Les solutions varient selon le contexte (urbain/rural, relief, densité).

5. **Le temps presse** : 2050 = dans 25 ans. Il faut agir maintenant.
""")

# ==================== FOOTER ====================

st.divider()
st.caption("Sources : [impactCO2.fr (ADEME)](https://impactco2.fr/outils/transport) • SNBC 2050 • Application pédagogique Pays Basque")
