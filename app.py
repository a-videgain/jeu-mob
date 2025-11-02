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
    
    # Situation 2025 - Habitant moyen Pays Basque
    st.session_state.km_2025 = {
        'voiture': 150,
        'bus': 25,
        'train': 8,
        'velo': 20,
        'avion': 30,
        'marche': 10
    }
    
    # Nombre de déplacements par semaine
    st.session_state.nb_depl = {
        'voiture': 8,
        'bus': 4,
        'train': 1,
        'velo': 5,
        'avion': 0.1,  # ~5 vols/an
        'marche': 10
    }
    
    # Facteurs d'émission (sources ADEME impactCO2 2024)
    st.session_state.emissions = {
        'voiture_thermique': 193,  # gCO2/km (moyenne diesel/essence)
        'voiture_electrique': 20,
        'bus': 103,
        'train': 2.4,
        'velo': 0,
        'avion': 230,  # Vol moyen courrier
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

def calculer_bilan(km_dict, emissions_dict, part_ve=0):
    """Calcule CO2 total en tenant compte du mix voiture thermique/électrique"""
    co2_total = 0
    detail_par_mode = {}
    
    for mode in km_dict:
        if mode == 'voiture':
            # Mix thermique/électrique
            emission_voiture = (
                (100 - part_ve) / 100 * emissions_dict['voiture_thermique'] +
                part_ve / 100 * emissions_dict['voiture_electrique']
            )
            co2_mode = km_dict[mode] * emission_voiture / 1000  # kg CO2
        elif mode in ['bus', 'train', 'avion', 'velo', 'marche']:
            co2_mode = km_dict[mode] * emissions_dict[mode] / 1000  # kg CO2
        else:
            co2_mode = 0
        
        co2_total += co2_mode
        detail_par_mode[mode] = co2_mode
    
    return {
        'co2_hebdo': co2_total,
        'co2_annuel': co2_total * 52,
        'km_total': sum(km_dict.values()),
        'detail_par_mode': detail_par_mode
    }

def calculer_parts_modales(km_dict):
    """Calcule les parts modales en %"""
    km_total = sum(km_dict.values())
    if km_total == 0:
        return {mode: 0 for mode in km_dict}
    return {mode: (km / km_total) * 100 for mode, km in km_dict.items()}

def calculer_2050():
    """Calcule scénario 2050"""
    # 1. Réduction globale des km
    km_total_2025 = sum(st.session_state.km_2025.values())
    km_total_2050 = km_total_2025 * (1 + st.session_state.scenario['reduction_km'] / 100)
    
    # 2. Parts modales 2025 (%)
    parts_2025 = calculer_parts_modales(st.session_state.km_2025)
    
    # 3. Report modal (modification des parts)
    report_total = (st.session_state.scenario['report_velo'] + 
                    st.session_state.scenario['report_bus'] + 
                    st.session_state.scenario['report_train'])
    
    parts_2050 = parts_2025.copy()
    parts_2050['voiture'] = max(0, parts_2025['voiture'] - report_total)
    parts_2050['bus'] = parts_2025['bus'] + st.session_state.scenario['report_bus']
    parts_2050['train'] = parts_2025['train'] + st.session_state.scenario['report_train']
    parts_2050['velo'] = parts_2025['velo'] + st.session_state.scenario['report_velo']
    # Avion et marche restent inchangés (pas de report modal sur ces modes)
    
    # 4. Km absolus 2050
    km_2050 = {mode: km_total_2050 * part / 100 for mode, part in parts_2050.items()}
    
    # 5. Calcul bilans
    bilan_2025 = calculer_bilan(st.session_state.km_2025, st.session_state.emissions, part_ve=3)
    bilan_2050 = calculer_bilan(km_2050, st.session_state.emissions, part_ve=st.session_state.scenario['part_ve'])
    
    # 6. Calcul réduction (CORRECTION : si 2050 < 2025 alors réduction négative = bon)
    if bilan_2025['co2_hebdo'] > 0:
        reduction_pct = ((bilan_2025['co2_hebdo'] - bilan_2050['co2_hebdo']) / bilan_2025['co2_hebdo']) * 100
    else:
        reduction_pct = 0
    
    return {
        'km_2050': km_2050,
        'parts_2050': parts_2050,
        'bilan_2050': bilan_2050,
        'bilan_2025': bilan_2025,
        'reduction_pct': reduction_pct,
        'objectif_atteint': reduction_pct >= 80
    }

# ==================== INTERFACE ====================

st.title("🚗 Mobilité Pays Basque 2050")
st.markdown("**Outil pédagogique simplifié** • Année de référence : 2025 → Objectif : 2050")

# ==================== ÉTAPE 1 : DIAGNOSTIC 2025 ====================

st.header("📍 Étape 1 : Diagnostic 2025")
st.info("**Habitant moyen du Pays Basque** (environ 300 000 habitants)")

# Saisie des données
col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    st.subheader("🛣️ Distances hebdomadaires (km)")
    
    st.session_state.km_2025['voiture'] = st.number_input(
        "🚗 Voiture",
        min_value=0, max_value=500, value=st.session_state.km_2025['voiture'],
        step=10, key="km_voiture"
    )
    
    st.session_state.km_2025['bus'] = st.number_input(
        "🚌 Bus / TC urbains",
        min_value=0, max_value=200, value=st.session_state.km_2025['bus'],
        step=5, key="km_bus"
    )
    
    st.session_state.km_2025['train'] = st.number_input(
        "🚆 Train",
        min_value=0, max_value=100, value=st.session_state.km_2025['train'],
        step=5, key="km_train"
    )
    
    st.session_state.km_2025['velo'] = st.number_input(
        "🚴 Vélo",
        min_value=0, max_value=100, value=st.session_state.km_2025['velo'],
        step=5, key="km_velo"
    )
    
    st.session_state.km_2025['avion'] = st.number_input(
        "✈️ Avion",
        min_value=0, max_value=500, value=st.session_state.km_2025['avion'],
        step=10, key="km_avion",
        help="Km parcourus en avion par semaine (moyenne annuelle)"
    )
    
    st.session_state.km_2025['marche'] = st.number_input(
        "🚶 Marche",
        min_value=0, max_value=50, value=st.session_state.km_2025['marche'],
        step=5, key="km_marche"
    )

with col2:
    st.subheader("🔢 Nombre déplacements/semaine")
    
    st.session_state.nb_depl['voiture'] = st.number_input(
        "🚗 Voiture",
        min_value=0, max_value=50, value=st.session_state.nb_depl['voiture'],
        step=1, key="nb_voiture"
    )
    
    st.session_state.nb_depl['bus'] = st.number_input(
        "🚌 Bus",
        min_value=0, max_value=30, value=st.session_state.nb_depl['bus'],
        step=1, key="nb_bus"
    )
    
    st.session_state.nb_depl['train'] = st.number_input(
        "🚆 Train",
        min_value=0, max_value=20, value=st.session_state.nb_depl['train'],
        step=1, key="nb_train"
    )
    
    st.session_state.nb_depl['velo'] = st.number_input(
        "🚴 Vélo",
        min_value=0, max_value=30, value=st.session_state.nb_depl['velo'],
        step=1, key="nb_velo"
    )
    
    st.session_state.nb_depl['avion'] = st.number_input(
        "✈️ Avion",
        min_value=0.0, max_value=5.0, value=st.session_state.nb_depl['avion'],
        step=0.1, key="nb_avion",
        help="Moyenne par semaine (ex: 5 vols/an = 0.1/semaine)"
    )
    
    st.session_state.nb_depl['marche'] = st.number_input(
        "🚶 Marche",
        min_value=0, max_value=50, value=st.session_state.nb_depl['marche'],
        step=1, key="nb_marche"
    )

with col3:
    st.subheader("⚠️ Facteurs émission (gCO₂/km)")
    st.caption("Sources : [impactco2.fr](https://impactco2.fr/outils/transport)")
    
    st.session_state.emissions['voiture_thermique'] = st.number_input(
        "🚗 Voiture thermique",
        min_value=0, max_value=500, value=st.session_state.emissions['voiture_thermique'],
        step=10, key="em_voiture_therm",
        help="ADEME 2024 : 193 gCO2/km (moyenne diesel/essence)"
    )
    
    st.session_state.emissions['voiture_electrique'] = st.number_input(
        "🔌 Voiture électrique",
        min_value=0, max_value=100, value=st.session_state.emissions['voiture_electrique'],
        step=5, key="em_voiture_elec",
        help="ADEME 2024 : 20 gCO2/km"
    )
    
    st.session_state.emissions['bus'] = st.number_input(
        "🚌 Bus",
        min_value=0, max_value=300, value=st.session_state.emissions['bus'],
        step=10, key="em_bus",
        help="ADEME 2024 : 103 gCO2/km"
    )
    
    st.session_state.emissions['train'] = st.number_input(
        "🚆 Train",
        min_value=0.0, max_value=50.0, value=st.session_state.emissions['train'],
        step=0.5, key="em_train",
        help="ADEME 2024 : 2.4 gCO2/km"
    )
    
    st.session_state.emissions['avion'] = st.number_input(
        "✈️ Avion",
        min_value=0, max_value=500, value=st.session_state.emissions['avion'],
        step=10, key="em_avion",
        help="ADEME 2024 : 230 gCO2/km (courrier moyen)"
    )
    
    st.info("💡 Vélo et marche : 0 gCO₂/km")

# Calcul bilan 2025
bilan_2025 = calculer_bilan(st.session_state.km_2025, st.session_state.emissions, part_ve=3)
parts_2025 = calculer_parts_modales(st.session_state.km_2025)

st.divider()

# Affichage métriques principales
st.subheader("📊 Bilan 2025")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📏 Km total/semaine", f"{bilan_2025['km_total']:.0f} km")
with col2:
    st.metric("🌍 CO₂/semaine", f"{bilan_2025['co2_hebdo']:.1f} kg")
with col3:
    st.metric("📅 CO₂/an", f"{bilan_2025['co2_annuel']:.0f} kg")
with col4:
    nb_depl_total = sum(st.session_state.nb_depl.values())
    st.metric("🔢 Déplacements/semaine", f"{nb_depl_total:.0f}")

# Graphiques diagnostic
col1, col2 = st.columns(2)

with col1:
    st.subheader("🥧 Parts modales 2025")
    
    df_parts = pd.DataFrame({
        'Mode': list(parts_2025.keys()),
        'Part (%)': list(parts_2025.values())
    })
    df_parts['Mode'] = df_parts['Mode'].map({
        'voiture': '🚗 Voiture',
        'bus': '🚌 Bus',
        'train': '🚆 Train',
        'velo': '🚴 Vélo',
        'avion': '✈️ Avion',
        'marche': '🚶 Marche'
    })
    
    fig_parts = px.pie(
        df_parts,
        values='Part (%)',
        names='Mode',
        hole=0.4,
        title="Répartition des km parcourus"
    )
    fig_parts.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_parts, use_container_width=True)

with col2:
    st.subheader("🌍 Émissions par mode 2025")
    
    df_emissions = pd.DataFrame({
        'Mode': list(bilan_2025['detail_par_mode'].keys()),
        'CO₂ (kg/semaine)': list(bilan_2025['detail_par_mode'].values())
    })
    df_emissions['Mode'] = df_emissions['Mode'].map({
        'voiture': '🚗 Voiture',
        'bus': '🚌 Bus',
        'train': '🚆 Train',
        'velo': '🚴 Vélo',
        'avion': '✈️ Avion',
        'marche': '🚶 Marche'
    })
    # Trier par émissions décroissantes
    df_emissions = df_emissions.sort_values('CO₂ (kg/semaine)', ascending=False)
    
    fig_emissions = px.bar(
        df_emissions,
        x='Mode',
        y='CO₂ (kg/semaine)',
        text='CO₂ (kg/semaine)',
        color='CO₂ (kg/semaine)',
        color_continuous_scale='Reds',
        title="Contribution aux émissions"
    )
    fig_emissions.update_traces(texttemplate='%{text:.2f} kg', textposition='outside')
    fig_emissions.update_layout(showlegend=False)
    st.plotly_chart(fig_emissions, use_container_width=True)

# ==================== ÉTAPE 2 : SCÉNARIO 2050 ====================

st.divider()
st.header("🎯 Étape 2 : Construire le scénario 2050")

st.warning("**🎯 Objectif SNBC : Réduire de 80% les émissions CO₂ entre 2025 et 2050**")

# Organisation en accordéons pour meilleure lisibilité
with st.expander("🔧 **LEVIER 1 : Sobriété** - Réduire les km parcourus", expanded=True):
    st.markdown("""
    **Objectif :** Diminuer le besoin de déplacement  
    **Moyens :** Télétravail, relocalisations, urbanisme des courtes distances, limitation vitesse...
    """)
    
    st.session_state.scenario['reduction_km'] = st.slider(
        "Variation des km totaux par rapport à 2025 (%)",
        min_value=-50, max_value=10, value=st.session_state.scenario['reduction_km'],
        step=5, key="lever_reduction",
        help="Valeurs négatives = réduction des km (ex: -30% = on parcourt 30% de km en moins)"
    )
    
    km_total_2025 = sum(st.session_state.km_2025.values())
    km_total_2050_prevision = km_total_2025 * (1 + st.session_state.scenario['reduction_km'] / 100)
    
    if st.session_state.scenario['reduction_km'] < 0:
        st.success(f"✅ Réduction de {abs(st.session_state.scenario['reduction_km'])}% : {km_total_2025:.0f} km/sem → {km_total_2050_prevision:.0f} km/sem")
    elif st.session_state.scenario['reduction_km'] > 0:
        st.warning(f"⚠️ Augmentation de {st.session_state.scenario['reduction_km']}% : {km_total_2025:.0f} km/sem → {km_total_2050_prevision:.0f} km/sem")
    else:
        st.info(f"➡️ Stabilité : {km_total_2025:.0f} km/sem")

with st.expander("🔧 **LEVIER 2 : Report modal** - Transférer de la voiture vers d'autres modes", expanded=True):
    st.markdown("""
    **Objectif :** Faire passer les usagers de la voiture vers des modes moins émetteurs  
    **Moyens :** Pistes cyclables, réseaux TC denses, trains fréquents, intermodalité...
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.scenario['report_velo'] = st.slider(
            "🚴 Voiture → Vélo (%)",
            min_value=0, max_value=35, value=st.session_state.scenario['report_velo'],
            step=5, key="lever_velo",
            help="% de la part modale voiture transférée vers le vélo"
        )
        
        st.session_state.scenario['report_bus'] = st.slider(
            "🚌 Voiture → Bus/TC (%)",
            min_value=0, max_value=30, value=st.session_state.scenario['report_bus'],
            step=5, key="lever_bus",
            help="% de la part modale voiture transférée vers les TC"
        )
    
    with col2:
        st.session_state.scenario['report_train'] = st.slider(
            "🚆 Voiture → Train (%)",
            min_value=0, max_value=25, value=st.session_state.scenario['report_train'],
            step=5, key="lever_train",
            help="% de la part modale voiture transférée vers le train"
        )
        
        report_total = (st.session_state.scenario['report_velo'] + 
                        st.session_state.scenario['report_bus'] + 
                        st.session_state.scenario['report_train'])
        
        st.metric("📊 Report modal total", f"{report_total}%", help="Somme des transferts depuis la voiture")
        
        part_voiture_2025 = parts_2025['voiture']
        part_voiture_2050_prevision = max(0, part_voiture_2025 - report_total)
        
        st.info(f"Part modale voiture : {part_voiture_2025:.1f}% → {part_voiture_2050_prevision:.1f}%")

with st.expander("🔧 **LEVIER 3 : Électrification** - Décarboner le parc automobile", expanded=True):
    st.markdown("""
    **Objectif :** Remplacer les véhicules thermiques par des véhicules électriques  
    **Moyens :** Aides à l'achat, bornes de recharge, production électrique bas-carbone...
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.scenario['part_ve'] = st.slider(
            "Part de véhicules électriques (%)",
            min_value=0, max_value=100, value=st.session_state.scenario['part_ve'],
            step=5, key="lever_ve",
            help="Pourcentage du parc automobile en 2050"
        )
        
        st.session_state.scenario['part_thermique'] = 100 - st.session_state.scenario['part_ve']
        
        st.info(f"Part thermique restante : {st.session_state.scenario['part_thermique']}%")
    
    with col2:
        # Calcul émission moyenne voiture 2050
        emission_moy_2050 = (
            st.session_state.scenario['part_thermique'] / 100 * st.session_state.emissions['voiture_thermique'] +
            st.session_state.scenario['part_ve'] / 100 * st.session_state.emissions['voiture_electrique']
        )
        
        emission_moy_2025 = (
            97 / 100 * st.session_state.emissions['voiture_thermique'] +
            3 / 100 * st.session_state.emissions['voiture_electrique']
        )
        
        st.metric(
            "Émission moyenne voiture",
            f"{emission_moy_2050:.0f} gCO₂/km",
            delta=f"{emission_moy_2050 - emission_moy_2025:.0f} gCO₂/km",
            delta_color="inverse"
        )
        
        st.caption(f"2025 : {emission_moy_2025:.0f} gCO₂/km (3% VE)")

st.divider()

# Bouton reset visible
col_reset1, col_reset2, col_reset3 = st.columns([1, 1, 1])
with col_reset2:
    if st.button("🔄 Réinitialiser tous les leviers", use_container_width=True, type="secondary"):
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

# Métriques principales avec couleurs conditionnelles
col1, col2, col3 = st.columns(3)

with col1:
    delta_co2_annuel = resultats['bilan_2050']['co2_annuel'] - resultats['bilan_2025']['co2_annuel']
    st.metric(
        "🌍 Émissions CO₂ 2050",
        f"{resultats['bilan_2050']['co2_annuel']:.0f} kg/an",
        delta=f"{delta_co2_annuel:.0f} kg/an",
        delta_color="inverse",
        help="Comparaison avec 2025"
    )

with col2:
    st.metric(
        "📉 Réduction vs 2025",
        f"{resultats['reduction_pct']:.1f}%",
        delta=None,
        help="Pourcentage de réduction des émissions"
    )

with col3:
    if resultats['objectif_atteint']:
        st.success("✅ **Objectif SNBC atteint !**\n\n(≥ 80% de réduction)")
    else:
        st.error(f"❌ **Objectif non atteint**\n\nBesoin : -80%\nActuel : -{resultats['reduction_pct']:.1f}%")

st.divider()

# Graphiques comparaison détaillée
col1, col2 = st.columns(2)

with col1:
    st.subheader("📉 Évolution des émissions")
    
    df_evol = pd.DataFrame({
        'Année': ['2025', '2050'],
        'CO₂ (kg/an)': [
            resultats['bilan_2025']['co2_annuel'],
            resultats['bilan_2050']['co2_annuel']
        ]
    })
    
    fig_evol = px.bar(
        df_evol,
        x='Année',
        y='CO₂ (kg/an)',
        text='CO₂ (kg/an)',
        color='Année',
        color_discrete_map={'2025': '#94a3b8', '2050': '#3b82f6'}
    )
    fig_evol.update_traces(texttemplate='%{text:.0f} kg', textposition='outside')
    fig_evol.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_evol, use_container_width=True)
    
    # Indicateur de réduction
    if resultats['reduction_pct'] > 0:
        st.success(f"✅ Réduction de {resultats['reduction_pct']:.1f}%")
    elif resultats['reduction_pct'] < 0:
        st.error(f"⚠️ Augmentation de {abs(resultats['reduction_pct']):.1f}%")
    else:
        st.info("➡️ Émissions stables")

with col2:
    st.subheader("🚦 Parts modales 2050")
    
    df_parts_2050 = pd.DataFrame({
        'Mode': list(resultats['parts_2050'].keys()),
        'Part (%)': list(resultats['parts_2050'].values())
    })
    df_parts_2050['Mode'] = df_parts_2050['Mode'].map({
        'voiture': '🚗 Voiture',
        'bus': '🚌 Bus',
        'train': '🚆 Train',
        'velo': '🚴 Vélo',
        'avion': '✈️ Avion',
        'marche': '🚶 Marche'
    })
    
    fig_parts_2050 = px.pie(
        df_parts_2050,
        values='Part (%)',
        names='Mode',
        hole=0.4
    )
    fig_parts_2050.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_parts_2050, use_container_width=True)

# Tableau comparatif détaillé
st.subheader("📋 Tableau comparatif 2025 vs 2050")

data_comparaison = []
for mode in ['voiture', 'bus', 'train', 'velo', 'avion', 'marche']:
    emoji = {'voiture': '🚗', 'bus': '🚌', 'train': '🚆', 'velo': '🚴', 'avion': '✈️', 'marche': '🚶'}[mode]
    data_comparaison.append({
        'Mode': f"{emoji} {mode.capitalize()}",
        'Km/sem 2025': f"{st.session_state.km_2025[mode]:.0f}",
        'Km/sem 2050': f"{resultats['km_2050'][mode]:.0f}",
        'Part 2025 (%)': f"{parts_2025[mode]:.1f}%",
        'Part 2050 (%)': f"{resultats['parts_2050'][mode]:.1f}%",
        'CO₂ 2025 (kg/sem)': f"{bilan_2025['detail_par_mode'][mode]:.2f}",
        'CO₂ 2050 (kg/sem)': f"{resultats['bilan_2050']['detail_par_mode'][mode]:.2f}"
    })

df_comparaison = pd.DataFrame(data_comparaison)
st.dataframe(df_comparaison, use_container_width=True, hide_index=True)

# ==================== QUESTIONS PÉDAGOGIQUES ====================

st.divider()
st.header("💡 Questions pour le débat")

with st.expander("❓ Question 1 : Votre scénario atteint-il l'objectif ?", expanded=not resultats['objectif_atteint']):
    if resultats['objectif_atteint']:
        st.success(f"✅ **Bravo ! Votre scénario atteint l'objectif de -80%**")
        st.write(f"Vous avez réduit les émissions de **{resultats['reduction_pct']:.1f}%** entre 2025 et 2050.")
        st.markdown("""
        **Questions à approfondir :**
        - Quels leviers ont été les plus efficaces dans votre scénario ?
        - Votre scénario vous semble-t-il réaliste au vu du contexte du Pays Basque ?
        - Quels seraient les principaux défis de mise en œuvre ?
        - Pourrait-on atteindre l'objectif avec moins de contraintes ?
        """)
    else:
        st.error(f"❌ **Objectif non atteint**")
        st.write(f"Réduction actuelle : **{resultats['reduction_pct']:.1f}%** (objectif : -80%)")
        st.write(f"Il manque encore **{80 - resultats['reduction_pct']:.1f} points de pourcentage** pour atteindre l'objectif.")
        st.markdown("""
        **Pistes d'amélioration :**
        - Quels leviers pourriez-vous actionner davantage ?
        - Quel est le levier le plus efficace ? Le moins coûteux socialement ?
        - Un scénario 100% technologique (électrification totale) suffit-il ?
        - Faut-il nécessairement réduire les km parcourus ?
        """)

with st.expander("❓ Question 2 : L'électrification est-elle suffisante ?"):
    st.write(f"""
    **Votre scénario : {st.session_state.scenario['part_ve']}% de véhicules électriques en 2050**
    
    Émission moyenne d'une voiture dans votre scénario 2050 :
    - **{((st.session_state.scenario['part_thermique'] / 100) * st.session_state.emissions['voiture_thermique'] + 
         (st.session_state.scenario['part_ve'] / 100) * st.session_state.emissions['voiture_electrique']):.0f} gCO₂/km**
    - Comparé à 2025 : **{((97 / 100) * st.session_state.emissions['voiture_thermique'] + 
                           (3 / 100) * st.session_state.emissions['voiture_electrique']):.0f} gCO₂/km**
    """)
    
    st.markdown("""
    **Questions à débattre :**
    
    **Avantages de l'électrification :**
    - Réduction drastique des émissions : 193 → 20 gCO₂/km
    - Amélioration de la qualité de l'air (moins de particules)
    - Réduction du bruit en ville
    
    **Limites et défis :**
    - **Production électrique** : Le Pays Basque produit peu d'électricité. D'où viendra le surplus ?
    - **Réseau électrique** : Les réseaux actuels peuvent-ils supporter la charge de recharge ?
    - **Bornes de recharge** : Combien en installer ? Où (domicile, travail, voirie) ?
    - **Ressources** : Lithium, cobalt, nickel... Impacts environnementaux et géopolitiques de l'extraction ?
    - **Coût** : Un VE coûte 30-40% plus cher qu'un thermique. Accessible à tous ?
    - **Recyclage** : Quelle filière pour les batteries en fin de vie ?
    - **Délais** : Le parc se renouvelle en 15 ans. Sommes-nous dans les temps ?
    
    💡 **Question clé :** Peut-on atteindre -80% uniquement par l'électrification, sans toucher aux autres leviers ?
    """)

with st.expander("❓ Question 3 : Le report modal est-il réaliste ?"):
    report_total = (st.session_state.scenario['report_velo'] + 
                    st.session_state.scenario['report_bus'] + 
                    st.session_state.scenario['report_train'])
    
    st.write(f"""
    **Votre scénario : {report_total}% de report modal**
    - Vers vélo : {st.session_state.scenario['report_velo']}%
    - Vers bus/TC : {st.session_state.scenario['report_bus']}%
    - Vers train : {st.session_state.scenario['report_train']}%
    
    Part modale voiture : **{parts_2025['voiture']:.1f}% → {resultats['parts_2050']['voiture']:.1f}%**
    """)
    
    st.markdown("""
    **Infrastructures nécessaires :**
    
    **Pour le vélo :**
    - Réseau de pistes cyclables sécurisées et continues
    - Stationnement vélo sécurisé (domicile, gares, entreprises)
    - Développement du vélo à assistance électrique (relief vallonné)
    - Services de location/réparation
    
    **Pour les TC :**
    - Extension du réseau Chronoplus (nouvelles lignes, fréquence)
    - Développement de lignes de tram/BHNS
    - Amélioration Hegobus (liaisons interurbaines)
    - Tarification attractive, intermodalité
    
    **Pour le train :**
    - Réouverture de lignes fermées (Bayonne-St-Jean-Pied-de-Port ?)
    - Cadencement des trains (fréquence régulière)
    - Développement EuskoTren transfrontalier
    - Connexion avec le réseau TER Nouvelle-Aquitaine
    
    **Contraintes du Pays Basque :**
    - Relief montagneux (Pyrénées) → vélo difficile sans assistance électrique
    - Habitat dispersé en zone rurale → TC peu rentables
    - Zone touristique → forte saisonnalité des flux
    - Frontière espagnole → opportunités de coopération transfrontalière
    
    💡 **Question clé :** Ces infrastructures sont-elles finançables et réalisables d'ici 2050 ?
    """)

with st.expander("❓ Question 4 : La sobriété est-elle incontournable ?"):
    st.write(f"""
    **Votre scénario : {st.session_state.scenario['reduction_km']:+}% de variation des km parcourus**
    
    Km totaux : **{bilan_2025['km_total']:.0f} km/sem → {resultats['bilan_2050']['km_total']:.0f} km/sem**
    """)
    
    if st.session_state.scenario['reduction_km'] < 0:
        st.success(f"✅ Vous avez réduit les km de {abs(st.session_state.scenario['reduction_km'])}%")
    elif st.session_state.scenario['reduction_km'] > 0:
        st.warning(f"⚠️ Vos km ont augmenté de {st.session_state.scenario['reduction_km']}%")
    else:
        st.info("➡️ Les km sont restés stables")
    
    st.markdown("""
    **La sobriété, c'est quoi ?**
    - Réduire le **besoin** de mobilité, pas juste changer de mode
    - Rapprocher lieux de vie, travail, services, loisirs
    - Questionner nos modes de vie
    
    **Leviers de sobriété :**
    - **Télétravail** : 2-3 jours/semaine → -40% de trajets domicile-travail
    - **Relocalisations** : Commerces de proximité, services publics locaux
    - **Urbanisme** : Ville des courtes distances, densification maîtrisée
    - **Limitation vitesse** : 30 km/h en ville, 110 km/h sur autoroute → -10-15% de consommation
    - **Sobriété aérienne** : Limiter les vols, favoriser le train
    
    **Freins et résistances :**
    - Liberté de mouvement perçue comme fondamentale
    - Modèle économique basé sur la croissance et la mobilité
    - Étalement urbain déjà installé (impossible de tout relocaliser rapidement)
    - Inégalités : tout le monde ne peut pas télétravailler ou déménager
    
    **Expérience Gilets Jaunes (2018) :**
    - Taxe carbone perçue comme injuste et punitive
    - Ruraux/périurbains dépendants de la voiture
    - Absence d'alternatives crédibles
    → Importance de l'accompagnement et de la justice sociale
    
    💡 **Question clé :** Peut-on atteindre -80% sans sobriété ? Testez en mettant le levier 1 à 0% et en jouant uniquement sur les leviers 2 et 3.
    """)

with st.expander("❓ Question 5 : Quid de l'avion ?"):
    st.write(f"""
    **Dans votre scénario :**
    - Km avion/semaine (2025) : **{st.session_state.km_2025['avion']} km** ({(parts_2025['avion']):.1f}% des km totaux)
    - Km avion/semaine (2050) : **{resultats['km_2050']['avion']:.0f} km** ({resultats['parts_2050']['avion']:.1f}% des km totaux)
    - Émissions avion/semaine (2025) : **{bilan_2025['detail_par_mode']['avion']:.2f} kg CO₂**
    - Émissions avion/semaine (2050) : **{resultats['bilan_2050']['detail_par_mode']['avion']:.2f} kg CO₂**
    """)
    
    st.markdown("""
    **Constats :**
    - L'avion représente une **part faible des km** mais une **part élevée des émissions**
    - 230 gCO₂/km vs 193 pour voiture, 103 pour bus, 2.4 pour train
    - 1 aller-retour Paris-Bayonne (~1600 km) = **370 kg CO₂**, soit 17% du budget annuel d'un habitant moyen !
    
    **Limites actuelles :**
    - Pas d'alternative crédible pour l'aviation décarbonée à court/moyen terme
    - Biocarburants : ressources limitées, concurrence avec alimentation
    - Hydrogène : technologie immature, coûts élevés
    - Avion électrique : impossible pour long courrier (densité énergétique batteries insuffisante)
    
    **Enjeux au Pays Basque :**
    - Aéroport Biarritz Pays Basque : 1,2 million de passagers/an (2019)
    - Majorité de vols tourisme (été) et affaires
    - Concurrence avec le train pour destinations nationales (Paris, Lyon...)
    
    **Pistes de réflexion :**
    - Limiter les vols courts distance (< 2h30 de train) ?
    - Taxation du kérosène (actuellement exonéré) ?
    - Quotas carbone individuels (ex: 3 vols long courrier/vie) ?
    - Développement du train de nuit
    
    💡 **Dans votre scénario actuel, l'avion n'est pas impacté par vos leviers. Est-ce cohérent avec l'objectif -80% ?**
    """)

with st.expander("❓ Question 6 : Acceptabilité sociale et justice"):
    st.markdown("""
    **Qui peut/doit faire des efforts ?**
    
    **Inégalités de mobilité au Pays Basque :**
    - **Urbains BAB** : Accès TC, vélo possible, courtes distances
    - **Périurbains** : Dépendants voiture, distances moyennes
    - **Ruraux montagne** : Très dépendants voiture, TC quasi inexistants, relief difficile
    - **Frontaliers** : Trajets quotidiens France-Espagne
    - **Touristes** : Mobilité saisonnière importante
    
    **Inégalités sociales :**
    - Revenus modestes : Pas les moyens d'acheter un VE, dépendent de vieux véhicules thermiques
    - Classes moyennes : Peuvent investir dans VE avec aides, mais coût élevé
    - Classes aisées : Peuvent acheter VE, garder aussi une thermique, prendre l'avion
    
    **Dilemme de l'acceptabilité :**
    - Une transition **imposée** (taxes, interdictions) génère des résistances (cf. Gilets Jaunes)
    - Une transition **incitative** (aides, gratuité TC) coûte cher aux finances publiques
    - Une transition **laissée au marché** est trop lente et inégalitaire
    
    **Mesures d'accompagnement nécessaires :**
    - Aides ciblées sur les ménages modestes
    - Alternatives crédibles AVANT de contraindre (TC, vélo)
    - Progressivité (pas de changement brutal)
    - Concertation territoriale (solutions adaptées à chaque contexte)
    - Communication positive ("co-bénéfices" : santé, qualité de vie, économies)
    
    💡 **Question clé :** Votre scénario est-il socialement acceptable ? Qui sont les "gagnants" et les "perdants" ?
    """)

# ==================== SYNTHÈSE PÉDAGOGIQUE ====================

st.divider()
st.header("📚 Synthèse : Points clés à retenir")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### ✅ Enseignements principaux
    
    **1. Approche systémique nécessaire**
    - Aucun levier seul ne suffit
    - Il faut combiner sobriété + report modal + décarbonation
    - Les 3 leviers sont **complémentaires**, pas substituables
    
    **2. Hiérarchie d'efficacité**
    - **Sobriété** : Levier le plus puissant (ne pas émettre > émettre moins)
    - **Report modal** : Efficace mais nécessite infrastructures lourdes
    - **Électrification** : Importante mais ne résout pas tout
    
    **3. Limites de la technologie**
    - L'électrification a des limites (production, réseaux, ressources)
    - Pas de solution miracle pour l'avion
    - La technologie seule ne peut pas tout résoudre
    
    **4. Importance du contexte territorial**
    - Pays Basque ≠ Paris ≠ Creuse
    - Relief, densité, climat, culture : solutions différenciées
    - Penser "système de mobilité" pas juste "modes"
    """)

with col2:
    st.markdown("""
    ### ⚠️ Défis à relever
    
    **1. Acceptabilité sociale**
    - Changements de comportement difficiles
    - Liberté de mouvement = valeur forte
    - Justice sociale indispensable
    
    **2. Temporalité**
    - 2050 = dans 25 ans seulement
    - Renouvellement parc auto : 15 ans
    - Infrastructures TC/vélo : 10-20 ans
    → **Il faut agir MAINTENANT**
    
    **3. Financement**
    - Infrastructures coûteuses (milliards €)
    - Aides individuelles nécessaires
    - Qui paie ? État, collectivités, usagers ?
    
    **4. Gouvernance**
    - Compétences multiples (État, Région, Agglo, Communes)
    - Nécessité de coordination
    - Implication citoyenne essentielle
    """)

st.info("""
**🎯 Message clé :**  
Atteindre -80% d'ici 2050 est **techniquement possible** mais **socialement et politiquement exigeant**.  
Cela nécessite une **transformation profonde** de nos modes de vie et de notre organisation territoriale.  
La question n'est pas "est-ce possible ?" mais "comment faire pour que ce soit acceptable et juste ?".
""")

# ==================== RESSOURCES ====================

st.divider()
st.header("📖 Pour aller plus loin")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **📊 Données et références**
    - [impactCO2.fr (ADEME)](https://impactco2.fr/outils/transport) - Facteurs d'émission
    - [SNBC 2050](https://www.ecologie.gouv.fr/strategie-nationale-bas-carbone-snbc) - Stratégie nationale
    - [Transitions 2050 (ADEME)](https://transitions2050.ademe.fr/) - Scénarios prospectifs
    """)

with col2:
    st.markdown("""
    **🎓 Études et rapports**
    - [The Shift Project](https://theshiftproject.org/) - Plan de transformation
    - [Négawatt](https://negawatt.org/) - Scénario énergétique
    - [B&L évolution](https://www.bl-evolution.com/) - Mobilité bas-carbone
    """)

with col3:
    st.markdown("""
    **🏛️ Acteurs locaux**
    - [Communauté Pays Basque](https://www.communaute-paysbasque.fr/)
    - [Chronoplus](https://www.chronoplus.eu/) - TC urbains
    - [Hegobus](https://www.hegobus.fr/) - TC interurbains
    """)

# ==================== EXPORT ====================

st.divider()
st.subheader("💾 Exporter votre scénario")

# Résumé textuel du scénario
resume_scenario = f"""
═══════════════════════════════════════════════════
SCÉNARIO MOBILITÉ PAYS BASQUE 2050
═══════════════════════════════════════════════════

📅 ANNÉE DE RÉFÉRENCE : 2025

─────────────────────────────────────────────────── 
📊 DIAGNOSTIC 2025
───────────────────────────────────────────────────

Distances hebdomadaires :
  • Voiture : {st.session_state.km_2025['voiture']} km ({parts_2025['voiture']:.1f}%)
  • Bus/TC : {st.session_state.km_2025['bus']} km ({parts_2025['bus']:.1f}%)
  • Train : {st.session_state.km_2025['train']} km ({parts_2025['train']:.1f}%)
  • Vélo : {st.session_state.km_2025['velo']} km ({parts_2025['velo']:.1f}%)
  • Avion : {st.session_state.km_2025['avion']} km ({parts_2025['avion']:.1f}%)
  • Marche : {st.session_state.km_2025['marche']} km ({parts_2025['marche']:.1f}%)

TOTAL : {bilan_2025['km_total']:.0f} km/semaine

Émissions 2025 :
  • Hebdomadaire : {bilan_2025['co2_hebdo']:.2f} kg CO₂
  • Annuelle : {bilan_2025['co2_annuel']:.0f} kg CO₂

───────────────────────────────────────────────────
🎯 SCÉNARIO 2050
───────────────────────────────────────────────────

LEVIERS ACTIONNÉS :

1. Sobriété :
   • Variation km totaux : {st.session_state.scenario['reduction_km']:+}%
   • {bilan_2025['km_total']:.0f} km/sem → {resultats['bilan_2050']['km_total']:.0f} km/sem

2. Report modal :
   • Voiture → Vélo : {st.session_state.scenario['report_velo']}%
   • Voiture → Bus/TC : {st.session_state.scenario['report_bus']}%
   • Voiture → Train : {st.session_state.scenario['report_train']}%
   • TOTAL : {st.session_state.scenario['report_velo'] + st.session_state.scenario['report_bus'] + st.session_state.scenario['report_train']}%

3. Électrification :
   • Véhicules électriques : {st.session_state.scenario['part_ve']}%
   • Véhicules thermiques : {st.session_state.scenario['part_thermique']}%

───────────────────────────────────────────────────
📈 RÉSULTATS 2050
───────────────────────────────────────────────────

Distances 2050 :
  • Voiture : {resultats['km_2050']['voiture']:.0f} km ({resultats['parts_2050']['voiture']:.1f}%)
  • Bus/TC : {resultats['km_2050']['bus']:.0f} km ({resultats['parts_2050']['bus']:.1f}%)
  • Train : {resultats['km_2050']['train']:.0f} km ({resultats['parts_2050']['train']:.1f}%)
  • Vélo : {resultats['km_2050']['velo']:.0f} km ({resultats['parts_2050']['velo']:.1f}%)
  • Avion : {resultats['km_2050']['avion']:.0f} km ({resultats['parts_2050']['avion']:.1f}%)
  • Marche : {resultats['km_2050']['marche']:.0f} km ({resultats['parts_2050']['marche']:.1f}%)

TOTAL : {resultats['bilan_2050']['km_total']:.0f} km/semaine

Émissions 2050 :
  • Hebdomadaire : {resultats['bilan_2050']['co2_hebdo']:.2f} kg CO₂
  • Annuelle : {resultats['bilan_2050']['co2_annuel']:.0f} kg CO₂

───────────────────────────────────────────────────
🎯 BILAN
───────────────────────────────────────────────────

Réduction des émissions : {resultats['reduction_pct']:.1f}%
Objectif SNBC (-80%) : {"✅ ATTEINT" if resultats['objectif_atteint'] else "❌ NON ATTEINT"}

{f"Écart restant : {80 - resultats['reduction_pct']:.1f} points de %" if not resultats['objectif_atteint'] else ""}

═══════════════════════════════════════════════════
Générateur de scénarios - Mobilité Pays Basque 2050
Sources : ADEME impactCO2, SNBC
═══════════════════════════════════════════════════
"""

st.download_button(
    label="📥 Télécharger le résumé (TXT)",
    data=resume_scenario,
    file_name=f"scenario_mobilite_PB_2050_{resultats['reduction_pct']:.0f}pct.txt",
    mime="text/plain",
    use_container_width=True
)

# ==================== FOOTER ====================

st.divider()
st.markdown("""
<div style='text-align: center; color: #6b7280; font-size: 0.875rem; padding: 1rem;'>
    <p><strong>📚 Sources de données :</strong></p>
    <p>
        <a href='https://impactco2.fr/outils/transport' target='_blank'>impactCO2.fr (ADEME 2024)</a> • 
        <a href='https://www.ecologie.gouv.fr/strategie-nationale-bas-carbone-snbc' target='_blank'>SNBC 2050</a> • 
        <a href='https://transitions2050.ademe.fr/' target='_blank'>ADEME Transitions 2050</a>
    </p>
    <p style='margin-top: 1rem;'>
        <strong>🎓 Application pédagogique</strong> • Pays Basque Français • Année de référence : 2025<br>
        ⚠️ Valeurs territoriales indicatives • À affiner selon données locales disponibles
    </p>
</div>
""", unsafe_allow_html=True)
