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

# ==================== CONSTANTES ====================
POPULATION_PB = 350000  # habitants Pays Basque (EMD)

# ==================== INITIALISATION ====================
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    
    # Situation 2025 - TERRITOIRE Pays Basque (350 000 habitants)
    # Sources : EMD Pays Basque, PCAET, ENTD 2019
    # Valeurs en millions de km/an pour tout le territoire
    st.session_state.km_2025_territoire = {
        'voiture': 1750,  # Mkm/an (estimation basée ENTD ~5000 km/hab/an dont 80% voiture)
        'bus': 175,       # Mkm/an
        'train': 70,      # Mkm/an
        'velo': 140,      # Mkm/an
        'avion': 210,     # Mkm/an (forte composante touristique)
        'marche': 70      # Mkm/an
    }
    
    # Nombre de déplacements par jour par habitant (moyenne)
    st.session_state.nb_depl_hab = {
        'voiture': 1.1,
        'bus': 0.6,
        'train': 0.15,
        'velo': 0.7,
        'avion': 0.014,
        'marche': 1.4
    }
    
    # Caractéristiques parc automobile 2025 Pays Basque
    st.session_state.parc_2025 = {
        'part_ve': 3,  # % véhicules électriques
        'part_thermique': 97,
        'emission_thermique': 218,  # gCO2/km ACV (Base Carbone)
        'taux_occupation': 1.3,
        'temps_stationnement': 95
    }
    
    # Facteurs d'émission ACV (autres modes)
    # Sources ADEME Base Carbone 2024 + impactCO2
    st.session_state.emissions = {
        'voiture_electrique': 103,  # gCO2/km ACV
        'bus': 127,
        'train': 5.1,
        'velo': 5,
        'avion': 225,  # impactCO2.fr
        'marche': 0
    }
    
    # Scénario 2050
    st.session_state.scenario = {
        'reduction_km': 0,
        'report_velo': 0,
        'report_bus': 0,
        'report_train': 0,
        'report_train_avion': 0,
        'taux_remplissage': 1.3,
        'part_ve': 3,
        'part_thermique': 97,
        'reduction_poids': 0
    }

# ==================== FONCTIONS ====================

def calculer_bilan_territoire(km_territoire, emissions_parc, parc_config, reduction_poids=0):
    """
    Calcule CO2 total du territoire en tenant compte :
    - du mix voiture thermique/électrique
    - du taux de remplissage
    - de la réduction de poids (tous véhicules)
    
    km_territoire : dict avec km en millions/an
    """
    co2_total_territoire = 0  # tonnes CO2/an
    detail_par_mode = {}
    
    for mode in km_territoire:
        if mode == 'voiture':
            # Effet allègement : -10% poids = -7% consommation (tous véhicules)
            facteur_allègement = 1 - (reduction_poids * 0.7 / 100)
            emission_thermique_ajustee = emissions_parc['emission_thermique'] * facteur_allègement
            emission_electrique_ajustee = emissions_parc['voiture_electrique'] * facteur_allègement
            
            # Mix thermique/électrique
            emission_voiture = (
                parc_config['part_thermique'] / 100 * emission_thermique_ajustee +
                parc_config['part_ve'] / 100 * emission_electrique_ajustee
            )
            
            # Diviser par taux de remplissage
            emission_par_personne = emission_voiture / parc_config['taux_occupation']
            
            # km en millions → CO2 en tonnes
            co2_mode = km_territoire[mode] * 1e6 * emission_par_personne / 1000 / 1000  # tonnes CO2
        elif mode in ['bus', 'train', 'avion', 'velo', 'marche']:
            co2_mode = km_territoire[mode] * 1e6 * emissions_parc[mode] / 1000 / 1000  # tonnes CO2
        else:
            co2_mode = 0
        
        co2_total_territoire += co2_mode
        detail_par_mode[mode] = co2_mode
    
    return {
        'co2_total_territoire': co2_total_territoire,  # tonnes CO2/an
        'km_total_territoire': sum(km_territoire.values()),  # Mkm/an
        'detail_par_mode': detail_par_mode  # tonnes CO2/an par mode
    }

def calculer_parts_modales(km_dict):
    """Calcule les parts modales en %"""
    km_total = sum(km_dict.values())
    if km_total == 0:
        return {mode: 0 for mode in km_dict}
    return {mode: (km / km_total) * 100 for mode, km in km_dict.items()}

def calculer_2050():
    """
    Calcule scénario 2050
    ORDRE CORRECT : 1. Sobriété, 2. Report modal
    """
    # 1. APPLICATION DE LA SOBRIÉTÉ D'ABORD (sur km territoriaux 2025)
    facteur_sobriete = (1 + st.session_state.scenario['reduction_km'] / 100)
    
    km_2025_apres_sobriete = {
        mode: km * facteur_sobriete 
        for mode, km in st.session_state.km_2025_territoire.items()
    }
    
    # 2. REPORT MODAL (sur les km après sobriété)
    km_voiture_apres_sobriete = km_2025_apres_sobriete['voiture']
    km_avion_apres_sobriete = km_2025_apres_sobriete['avion']
    
    # Transferts en valeur absolue (Mkm)
    km_transferes_velo = km_voiture_apres_sobriete * st.session_state.scenario['report_velo'] / 100
    km_transferes_bus = km_voiture_apres_sobriete * st.session_state.scenario['report_bus'] / 100
    km_transferes_train_voiture = km_voiture_apres_sobriete * st.session_state.scenario['report_train'] / 100
    km_transferes_train_avion = km_avion_apres_sobriete * st.session_state.scenario['report_train_avion'] / 100
    
    # 3. KM FINAUX 2050 (après sobriété ET report modal)
    km_2050_territoire = {}
    km_2050_territoire['voiture'] = km_voiture_apres_sobriete - km_transferes_velo - km_transferes_bus - km_transferes_train_voiture
    km_2050_territoire['bus'] = km_2025_apres_sobriete['bus'] + km_transferes_bus
    km_2050_territoire['train'] = km_2025_apres_sobriete['train'] + km_transferes_train_voiture + km_transferes_train_avion
    km_2050_territoire['velo'] = km_2025_apres_sobriete['velo'] + km_transferes_velo
    km_2050_territoire['avion'] = km_avion_apres_sobriete - km_transferes_train_avion
    km_2050_territoire['marche'] = km_2025_apres_sobriete['marche']
    
    # 4. Configuration parc 2050
    parc_2050 = {
        'part_thermique': st.session_state.scenario['part_thermique'],
        'part_ve': st.session_state.scenario['part_ve'],
        'taux_occupation': st.session_state.scenario['taux_remplissage']
    }
    
    emissions_2050 = st.session_state.emissions.copy()
    emissions_2050['emission_thermique'] = st.session_state.parc_2025['emission_thermique']
    
    # 5. Calcul bilans
    bilan_2025 = calculer_bilan_territoire(
        st.session_state.km_2025_territoire,
        {**st.session_state.emissions, 'emission_thermique': st.session_state.parc_2025['emission_thermique']},
        st.session_state.parc_2025,
        reduction_poids=0
    )
    
    bilan_2050 = calculer_bilan_territoire(
        km_2050_territoire,
        emissions_2050,
        parc_2050,
        reduction_poids=st.session_state.scenario['reduction_poids']
    )
    
    # 6. Calcul réduction
    if bilan_2025['co2_total_territoire'] > 0:
        reduction_pct = ((bilan_2025['co2_total_territoire'] - bilan_2050['co2_total_territoire']) / 
                        bilan_2025['co2_total_territoire']) * 100
    else:
        reduction_pct = 0
    
    # 7. Parts modales
    parts_2050 = calculer_parts_modales(km_2050_territoire)
    
    return {
        'km_2050_territoire': km_2050_territoire,
        'parts_2050': parts_2050,
        'bilan_2050': bilan_2050,
        'bilan_2025': bilan_2025,
        'reduction_pct': reduction_pct,
        'objectif_atteint': reduction_pct >= 80
    }

# ==================== INTERFACE ====================

st.title("🚗 Mobilité Pays Basque 2050")
st.markdown("**Outil pédagogique** • Territoire : Communauté Pays Basque (350 000 habitants)")

# ==================== ÉTAPE 1 : DIAGNOSTIC 2025 ====================

st.header("📍 Étape 1 : Diagnostic 2025 - Territoire Pays Basque")
st.info("**Sources** : EMD Pays Basque, PCAET, ENTD 2019")

# Saisie des données territoire
st.subheader("🛣️ Mobilités du territoire (millions de km/an)")

# En-têtes
header_cols = st.columns([2, 2, 2])
with header_cols[0]:
    st.markdown("**Mode**")
with header_cols[1]:
    st.markdown("**Mkm/an (territoire)**")
with header_cols[2]:
    st.markdown("**Dépl./jour/hab**")

# Voiture
cols = st.columns([2, 2, 2])
with cols[0]:
    st.markdown("🚗 Voiture")
with cols[1]:
    st.session_state.km_2025_territoire['voiture'] = st.number_input(
        "Mkm voiture", 0, 5000, st.session_state.km_2025_territoire['voiture'], 50,
        label_visibility="collapsed", key="input_km_v", help="Millions de km/an"
    )
with cols[2]:
    st.session_state.nb_depl_hab['voiture'] = st.number_input(
        "nb_v", 0.0, 5.0, st.session_state.nb_depl_hab['voiture'], 0.1,
        format="%.1f", label_visibility="collapsed", key="input_nb_v"
    )

# Bus
cols = st.columns([2, 2, 2])
with cols[0]:
    st.markdown("🚌 Bus / TC")
with cols[1]:
    st.session_state.km_2025_territoire['bus'] = st.number_input(
        "Mkm bus", 0, 1000, st.session_state.km_2025_territoire['bus'], 25,
        label_visibility="collapsed", key="input_km_b"
    )
with cols[2]:
    st.session_state.nb_depl_hab['bus'] = st.number_input(
        "nb_b", 0.0, 3.0, st.session_state.nb_depl_hab['bus'], 0.1,
        format="%.1f", label_visibility="collapsed", key="input_nb_b"
    )

# Train
cols = st.columns([2, 2, 2])
with cols[0]:
    st.markdown("🚆 Train")
with cols[1]:
    st.session_state.km_2025_territoire['train'] = st.number_input(
        "Mkm train", 0, 500, st.session_state.km_2025_territoire['train'], 10,
        label_visibility="collapsed", key="input_km_t"
    )
with cols[2]:
    st.session_state.nb_depl_hab['train'] = st.number_input(
        "nb_t", 0.0, 1.0, st.session_state.nb_depl_hab['train'], 0.05,
        format="%.2f", label_visibility="collapsed", key="input_nb_t"
    )

# Vélo
cols = st.columns([2, 2, 2])
with cols[0]:
    st.markdown("🚴 Vélo")
with cols[1]:
    st.session_state.km_2025_territoire['velo'] = st.number_input(
        "Mkm velo", 0, 500, st.session_state.km_2025_territoire['velo'], 10,
        label_visibility="collapsed", key="input_km_ve"
    )
with cols[2]:
    st.session_state.nb_depl_hab['velo'] = st.number_input(
        "nb_ve", 0.0, 3.0, st.session_state.nb_depl_hab['velo'], 0.1,
        format="%.1f", label_visibility="collapsed", key="input_nb_ve"
    )

# Avion
cols = st.columns([2, 2, 2])
with cols[0]:
    st.markdown("✈️ Avion")
with cols[1]:
    st.session_state.km_2025_territoire['avion'] = st.number_input(
        "Mkm avion", 0, 1000, st.session_state.km_2025_territoire['avion'], 10,
        label_visibility="collapsed", key="input_km_a"
    )
with cols[2]:
    st.session_state.nb_depl_hab['avion'] = st.number_input(
        "nb_a", 0.0, 0.5, st.session_state.nb_depl_hab['avion'], 0.01,
        format="%.3f", label_visibility="collapsed", key="input_nb_a"
    )

# Marche
cols = st.columns([2, 2, 2])
with cols[0]:
    st.markdown("🚶 Marche")
with cols[1]:
    st.session_state.km_2025_territoire['marche'] = st.number_input(
        "Mkm marche", 0, 500, st.session_state.km_2025_territoire['marche'], 10,
        label_visibility="collapsed", key="input_km_m"
    )
with cols[2]:
    st.session_state.nb_depl_hab['marche'] = st.number_input(
        "nb_m", 0.0, 5.0, st.session_state.nb_depl_hab['marche'], 0.1,
        format="%.1f", label_visibility="collapsed", key="input_nb_m"
    )

st.divider()

# Caractéristiques parc automobile 2025
st.subheader("🚗 Caractéristiques parc automobile 2025")

col1, col2, col3 = st.columns(3)

with col1:
    st.session_state.parc_2025['part_ve'] = st.number_input(
        "Part véhicules électriques (%)",
        min_value=0, max_value=100, value=st.session_state.parc_2025['part_ve'],
        step=1, help="Parc circulant Pays Basque 2025"
    )
    st.session_state.parc_2025['part_thermique'] = 100 - st.session_state.parc_2025['part_ve']
    st.caption(f"Part thermique : {st.session_state.parc_2025['part_thermique']}%")

with col2:
    st.session_state.parc_2025['emission_thermique'] = st.number_input(
        "Émission voiture thermique (gCO₂/km ACV)",
        min_value=0, max_value=500, value=st.session_state.parc_2025['emission_thermique'],
        step=10, help="Base Carbone ADEME : 218 gCO2e/km"
    )
    
    st.session_state.emissions['voiture_electrique'] = st.number_input(
        "Émission voiture électrique (gCO₂/km ACV)",
        min_value=0, max_value=200, value=st.session_state.emissions['voiture_electrique'],
        step=5, help="Base Carbone ADEME : 103 gCO2e/km"
    )

with col3:
    st.session_state.parc_2025['taux_occupation'] = st.number_input(
        "Taux d'occupation moyen (pers/véh)",
        min_value=1.0, max_value=4.0, value=st.session_state.parc_2025['taux_occupation'],
        step=0.1, format="%.1f"
    )
    
    st.session_state.parc_2025['temps_stationnement'] = st.number_input(
        "Temps stationné (%)",
        min_value=80, max_value=99, value=st.session_state.parc_2025['temps_stationnement'],
        step=1
    )

st.divider()

# Facteurs émission autres modes
with st.expander("⚙️ Facteurs d'émission autres modes (gCO₂/km ACV)"):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.session_state.emissions['bus'] = st.number_input("Bus", 0, 300, st.session_state.emissions['bus'], 10)
        st.session_state.emissions['train'] = st.number_input("Train", 0.0, 50.0, st.session_state.emissions['train'], 0.5)
    with col2:
        st.session_state.emissions['velo'] = st.number_input("Vélo", 0, 20, st.session_state.emissions['velo'], 1)
        st.session_state.emissions['avion'] = st.number_input("Avion", 0, 500, st.session_state.emissions['avion'], 10, help="impactCO2.fr : 225g")
    with col3:
        st.session_state.emissions['marche'] = st.number_input("Marche", 0, 10, st.session_state.emissions['marche'], 1)
        st.caption("**Sources** : [Base Carbone](https://base-empreinte.ademe.fr/), [impactCO2](https://impactco2.fr)")

st.divider()

# Bouton validation CENTRÉ
col_space1, col_btn, col_space2 = st.columns([1, 1, 1])
with col_btn:
    if st.button("✅ Valider le bilan 2025", type="primary", use_container_width=True):
        st.session_state.bilan_2025_valide = True
        st.rerun()

# Vérification validation
if 'bilan_2025_valide' not in st.session_state:
    st.session_state.bilan_2025_valide = False

if not st.session_state.bilan_2025_valide:
    st.warning("⚠️ Complétez les données ci-dessus puis cliquez sur **Valider le bilan 2025**")
    st.stop()

# Calcul bilan 2025
bilan_2025 = calculer_bilan_territoire(
    st.session_state.km_2025_territoire,
    {**st.session_state.emissions, 'emission_thermique': st.session_state.parc_2025['emission_thermique']},
    st.session_state.parc_2025,
    reduction_poids=0
)
parts_2025 = calculer_parts_modales(st.session_state.km_2025_territoire)

# Calculs par habitant
co2_par_hab = (bilan_2025['co2_total_territoire'] * 1000) / POPULATION_PB  # kg/hab/an
km_par_hab = (bilan_2025['km_total_territoire'] * 1e6) / POPULATION_PB / 52  # km/hab/semaine
depl_par_hab_jour = sum(st.session_state.nb_depl_hab.values())

st.divider()

# Affichage bilan
st.success("✅ Bilan 2025 validé")
st.header("📊 Bilan 2025")

# Métriques territoire
st.subheader("🌍 Échelle territoire (350 000 habitants)")
col1, col2 = st.columns(2)
with col1:
    st.metric("Km totaux/an", f"{bilan_2025['km_total_territoire']:.0f} Mkm")
with col2:
    st.metric("CO₂ total/an", f"{bilan_2025['co2_total_territoire']:.0f} tonnes", help=f"{bilan_2025['co2_total_territoire']/1000:.1f} kt CO2")

st.divider()

# Métriques par habitant
st.subheader("👤 Échelle habitant (moyennes)")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("CO₂/habitant/an", f"{co2_par_hab:.0f} kg")
with col2:
    st.metric("Km/habitant/semaine", f"{km_par_hab:.0f} km")
with col3:
    st.metric("Déplacements/habitant/jour", f"{depl_par_hab_jour:.1f}")

# Graphiques par habitant
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
    st.subheader("🌍 Émissions par mode (kg/hab/an)")
    
    # Calcul par habitant
    emissions_hab_an = {mode: (co2 * 1000) / POPULATION_PB for mode, co2 in bilan_2025['detail_par_mode'].items()}
    
    df_emissions = pd.DataFrame({
        'Mode': list(emissions_hab_an.keys()),
        'CO₂ (kg/hab/an)': list(emissions_hab_an.values())
    })
    df_emissions['Mode'] = df_emissions['Mode'].map({
        'voiture': '🚗 Voiture',
        'bus': '🚌 Bus',
        'train': '🚆 Train',
        'velo': '🚴 Vélo',
        'avion': '✈️ Avion',
        'marche': '🚶 Marche'
    })
    df_emissions = df_emissions.sort_values('CO₂ (kg/hab/an)', ascending=False)
    
    fig_emissions = px.bar(
        df_emissions,
        x='Mode',
        y='CO₂ (kg/hab/an)',
        text='CO₂ (kg/hab/an)',
        color='CO₂ (kg/hab/an)',
        color_continuous_scale='Reds',
        title="Contribution aux émissions"
    )
    fig_emissions.update_traces(texttemplate='%{text:.0f} kg', textposition='outside')
    fig_emissions.update_layout(showlegend=False)
    st.plotly_chart(fig_emissions, use_container_width=True)

# ==================== ÉTAPE 2 : SCÉNARIO 2050 ====================

st.divider()
st.header("🎯 Étape 2 : Construire le scénario 2050")

st.warning("**🎯 Objectif SNBC : Réduire d'environ 80% les émissions du secteur transport d'ici 2050** (par rapport à 1990-2015)")

# Leviers avec saisie directe + boutons
with st.expander("🔧 **LEVIER 1 : Sobriété** - Réduire les km parcourus", expanded=True):
    st.markdown("**Objectif :** Diminuer le besoin de déplacement")
    
    st.session_state.scenario['reduction_km'] = st.slider(
        "Variation des km totaux par rapport à 2025 (%)",
        min_value=-50, max_value=10, value=st.session_state.scenario['reduction_km'],
        step=5, key="lever_reduction"
    )
    
    km_total_2025 = sum(st.session_state.km_2025_territoire.values())
    km_total_2050_prevision = km_total_2025 * (1 + st.session_state.scenario['reduction_km'] / 100)
    
    if st.session_state.scenario['reduction_km'] < 0:
        st.success(f"✅ Réduction : {km_total_2025:.0f} Mkm → {km_total_2050_prevision:.0f} Mkm ({abs(st.session_state.scenario['reduction_km'])}%)")
    elif st.session_state.scenario['reduction_km'] > 0:
        st.warning(f"⚠️ Augmentation : {km_total_2025:.0f} Mkm → {km_total_2050_prevision:.0f} Mkm (+{st.session_state.scenario['reduction_km']}%)")
    else:
        st.info(f"➡️ Stabilité : {km_total_2025:.0f} Mkm")

with st.expander("🔧 **LEVIER 2 : Report modal** - Transférer vers modes décarbonés", expanded=True):
    st.markdown("**Objectif :** Transférer des km vers des modes moins émetteurs")
    st.caption("Valeurs = % des km du mode d'origine transférés (appliqué APRÈS sobriété)")
    
    st.markdown("##### 🚗 Report depuis la voiture")
    
    # Report vélo
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown("🚴 **Voiture → Vélo (%)**")
    with col2:
        new_val = st.number_input(
            "report_velo", 0, 50, st.session_state.scenario['report_velo'], 1,
            label_visibility="collapsed", key="input_report_velo"
        )
        if new_val != st.session_state.scenario['report_velo']:
            st.session_state.scenario['report_velo'] = new_val
    with col3:
        col_moins, col_plus = st.columns(2)
        with col_moins:
            if st.button("➖", key="velo_moins"):
                st.session_state.scenario['report_velo'] = max(0, st.session_state.scenario['report_velo'] - 1)
                st.rerun()
        with col_plus:
            if st.button("➕", key="velo_plus"):
                st.session_state.scenario['report_velo'] = min(50, st.session_state.scenario['report_velo'] + 1)
                st.rerun()
    
    # Report bus
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown("🚌 **Voiture → Bus/TC (%)**")
    with col2:
        new_val = st.number_input(
            "report_bus", 0, 50, st.session_state.scenario['report_bus'], 1,
            label_visibility="collapsed", key="input_report_bus"
        )
        if new_val != st.session_state.scenario['report_bus']:
            st.session_state.scenario['report_bus'] = new_val
    with col3:
        col_moins, col_plus = st.columns(2)
        with col_moins:
            if st.button("➖", key="bus_moins"):
                st.session_state.scenario['report_bus'] = max(0, st.session_state.scenario['report_bus'] - 1)
                st.rerun()
        with col_plus:
            if st.button("➕", key="bus_plus"):
                st.session_state.scenario['report_bus'] = min(50, st.session_state.scenario['report_bus'] + 1)
                st.rerun()
    
    # Report train (depuis voiture)
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown("🚆 **Voiture → Train (%)**")
    with col2:
        new_val = st.number_input(
            "report_train", 0, 50, st.session_state.scenario['report_train'], 1,
            label_visibility="collapsed", key="input_report_train"
        )
        if new_val != st.session_state.scenario['report_train']:
            st.session_state.scenario['report_train'] = new_val
    with col3:
        col_moins, col_plus = st.columns(2)
        with col_moins:
            if st.button("➖", key="train_moins"):
                st.session_state.scenario['report_train'] = max(0, st.session_state.scenario['report_train'] - 1)
                st.rerun()
        with col_plus:
            if st.button("➕", key="train_plus"):
                st.session_state.scenario['report_train'] = min(50, st.session_state.scenario['report_train'] + 1)
                st.rerun()
    
    report_total_voiture = (st.session_state.scenario['report_velo'] + 
                            st.session_state.scenario['report_bus'] + 
                            st.session_state.scenario['report_train'])
    st.info(f"**Report total depuis voiture : {report_total_voiture}%**")
    
    st.divider()
    st.markdown("##### ✈️ Report depuis l'avion")
    
    # Report train (depuis avion)
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown("🚆 **Avion → Train (%)**")
    with col2:
        new_val = st.number_input(
            "report_avion", 0, 100, st.session_state.scenario['report_train_avion'], 1,
            label_visibility="collapsed", key="input_report_avion"
        )
        if new_val != st.session_state.scenario['report_train_avion']:
            st.session_state.scenario['report_train_avion'] = new_val
    with col3:
        col_moins, col_plus = st.columns(2)
        with col_moins:
            if st.button("➖", key="avion_moins"):
                st.session_state.scenario['report_train_avion'] = max(0, st.session_state.scenario['report_train_avion'] - 1)
                st.rerun()
        with col_plus:
            if st.button("➕", key="avion_plus"):
                st.session_state.scenario['report_train_avion'] = min(100, st.session_state.scenario['report_train_avion'] + 1)
                st.rerun()
    
    st.info(f"**{st.session_state.scenario['report_train_avion']}%** des km avion transférés vers le train")

with st.expander("🔧 **LEVIER 3 : Taux de remplissage** - Augmenter l'occupation des véhicules", expanded=True):
    st.markdown("**Objectif :** Plus de personnes par véhicule")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown("**Taux d'occupation (pers/véhicule)**")
    with col2:
        new_val = st.number_input(
            "taux_remp", 1.0, 3.0, st.session_state.scenario['taux_remplissage'], 0.1,
            format="%.1f", label_visibility="collapsed", key="input_taux_remp"
        )
        if new_val != st.session_state.scenario['taux_remplissage']:
            st.session_state.scenario['taux_remplissage'] = round(new_val, 1)
    with col3:
        col_moins, col_plus = st.columns(2)
        with col_moins:
            if st.button("➖", key="remplissage_moins"):
                st.session_state.scenario['taux_remplissage'] = max(1.0, round(st.session_state.scenario['taux_remplissage'] - 0.1, 1))
                st.rerun()
        with col_plus:
            if st.button("➕", key="remplissage_plus"):
                st.session_state.scenario['taux_remplissage'] = min(3.0, round(st.session_state.scenario['taux_remplissage'] + 0.1, 1))
                st.rerun()
    
    gain_remplissage = ((st.session_state.scenario['taux_remplissage'] - st.session_state.parc_2025['taux_occupation']) / 
                        st.session_state.parc_2025['taux_occupation']) * 100
    
    if gain_remplissage > 0:
        st.success(f"✅ +{gain_remplissage:.1f}% vs 2025")
    elif gain_remplissage < 0:
        st.warning(f"⚠️ {gain_remplissage:.1f}% vs 2025")
    else:
        st.info("➡️ Identique à 2025")

with st.expander("🔧 **LEVIER 4 : Électrification** - Décarboner le parc automobile", expanded=True):
    st.markdown("**Objectif :** Remplacer véhicules thermiques par électriques")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown("**Part véhicules électriques (%)**")
    with col2:
        new_val = st.number_input(
            "part_ve", 0, 100, st.session_state.scenario['part_ve'], 5,
            label_visibility="collapsed", key="input_part_ve"
        )
        if new_val != st.session_state.scenario['part_ve']:
            st.session_state.scenario['part_ve'] = new_val
            st.session_state.scenario['part_thermique'] = 100 - new_val
    with col3:
        col_moins, col_plus = st.columns(2)
        with col_moins:
            if st.button("➖", key="ve_moins"):
                st.session_state.scenario['part_ve'] = max(0, st.session_state.scenario['part_ve'] - 5)
                st.session_state.scenario['part_thermique'] = 100 - st.session_state.scenario['part_ve']
                st.rerun()
        with col_plus:
            if st.button("➕", key="ve_plus"):
                st.session_state.scenario['part_ve'] = min(100, st.session_state.scenario['part_ve'] + 5)
                st.session_state.scenario['part_thermique'] = 100 - st.session_state.scenario['part_ve']
                st.rerun()
    
    st.info(f"Part thermique : **{st.session_state.scenario['part_thermique']}%**")

with st.expander("🔧 **LEVIER 5 : Allègement** - Réduire le poids des véhicules", expanded=True):
    st.markdown("**Objectif :** Véhicules plus légers, moins consommateurs")
    st.caption("Impact : -10% poids = -7% consommation (thermique ET électrique)")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown("**Réduction poids (%)**")
    with col2:
        new_val = st.number_input(
            "red_poids", 0, 30, st.session_state.scenario['reduction_poids'], 5,
            label_visibility="collapsed", key="input_red_poids"
        )
        if new_val != st.session_state.scenario['reduction_poids']:
            st.session_state.scenario['reduction_poids'] = new_val
    with col3:
        col_moins, col_plus = st.columns(2)
        with col_moins:
            if st.button("➖", key="poids_moins"):
                st.session_state.scenario['reduction_poids'] = max(0, st.session_state.scenario['reduction_poids'] - 5)
                st.rerun()
        with col_plus:
            if st.button("➕", key="poids_plus"):
                st.session_state.scenario['reduction_poids'] = min(30, st.session_state.scenario['reduction_poids'] + 5)
                st.rerun()
    
    if st.session_state.scenario['reduction_poids'] > 0:
        reduction_conso = st.session_state.scenario['reduction_poids'] * 0.7
        st.success(f"✅ Réduction consommation : -{reduction_conso:.1f}% (tous véhicules)")
        st.caption("💡 Thermiques ET électriques concernés (batteries, carrosserie...)")
    else:
        st.info("➡️ Pas d'allègement")

st.divider()

# Boutons reset et validation
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])

with col_btn1:
    if st.button("🔄 Réinitialiser les leviers", use_container_width=True, type="secondary", key="reset_btn"):
        st.session_state.scenario = {
            'reduction_km': 0,
            'report_velo': 0,
            'report_bus': 0,
            'report_train': 0,
            'report_train_avion': 0,
            'taux_remplissage': st.session_state.parc_2025['taux_occupation'],
            'part_ve': st.session_state.parc_2025['part_ve'],
            'part_thermique': st.session_state.parc_2025['part_thermique'],
            'reduction_poids': 0
        }
        st.session_state.scenario_2050_valide = False
        st.rerun()

with col_btn3:
    if st.button("✅ Valider le scénario 2050", type="primary", use_container_width=True, key="valider_2050"):
        st.session_state.scenario_2050_valide = True
        st.rerun()

# Vérifier validation
if 'scenario_2050_valide' not in st.session_state:
    st.session_state.scenario_2050_valide = False

if not st.session_state.scenario_2050_valide:
    st.warning("⚠️ Ajustez les leviers ci-dessus puis cliquez sur **Valider le scénario 2050**")
    st.stop()

# ==================== RÉSULTATS ====================

st.divider()
st.success("✅ Scénario 2050 validé")
st.header("📊 Résultats du scénario 2050")

# Calcul
resultats = calculer_2050()

# Calculs par habitant 2050
co2_par_hab_2050 = (resultats['bilan_2050']['co2_total_territoire'] * 1000) / POPULATION_PB
km_par_hab_2050 = (resultats['bilan_2050']['km_total_territoire'] * 1e6) / POPULATION_PB / 52

# Métriques principales
col1, col2, col3 = st.columns(3)

with col1:
    delta_co2_territoire = resultats['bilan_2050']['co2_total_territoire'] - resultats['bilan_2025']['co2_total_territoire']
    st.metric(
        "🌍 CO₂ territoire 2050",
        f"{resultats['bilan_2050']['co2_total_territoire']:.0f} tonnes/an",
        delta=f"{delta_co2_territoire:.0f} t/an",
        delta_color="inverse"
    )
    st.caption(f"Par habitant : {co2_par_hab_2050:.0f} kg/an")

with col2:
    st.metric(
        "📉 Réduction vs 2025",
        f"{resultats['reduction_pct']:.1f}%",
        delta=None
    )

with col3:
    if resultats['objectif_atteint']:
        st.success("✅ **Objectif SNBC atteint !**\n\n(≥ 80% de réduction)")
    else:
        st.error(f"❌ **Objectif non atteint**\n\nBesoin : -80%\nActuel : -{resultats['reduction_pct']:.1f}%")

st.divider()

# Graphiques comparaison
col1, col2 = st.columns(2)

with col1:
    st.subheader("📉 Évolution émissions (kg/hab/an)")
    
    df_evol = pd.DataFrame({
        'Année': ['2025', '2050'],
        'CO₂ (kg/hab/an)': [co2_par_hab, co2_par_hab_2050]
    })
    
    fig_evol = px.bar(
        df_evol,
        x='Année',
        y='CO₂ (kg/hab/an)',
        text='CO₂ (kg/hab/an)',
        color='Année',
        color_discrete_map={'2025': '#94a3b8', '2050': '#3b82f6'}
    )
    fig_evol.update_traces(texttemplate='%{text:.0f} kg', textposition='outside')
    fig_evol.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_evol, use_container_width=True)
    
    if resultats['reduction_pct'] > 0:
        st.success(f"✅ Réduction de {resultats['reduction_pct']:.1f}%")
    else:
        st.error(f"⚠️ Augmentation de {abs(resultats['reduction_pct']):.1f}%")

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

# Tableau comparatif
st.subheader("📋 Tableau comparatif 2025 vs 2050")

# Calculs par habitant pour tableau
emissions_2050_hab = {mode: (co2 * 1000) / POPULATION_PB for mode, co2 in resultats['bilan_2050']['detail_par_mode'].items()}

data_comparaison = []
for mode in ['voiture', 'bus', 'train', 'velo', 'avion', 'marche']:
    emoji = {'voiture': '🚗', 'bus': '🚌', 'train': '🚆', 'velo': '🚴', 'avion': '✈️', 'marche': '🚶'}[mode]
    
    km_2025_territoire = st.session_state.km_2025_territoire[mode]
    km_2050_territoire = resultats['km_2050_territoire'][mode]
    
    data_comparaison.append({
        'Mode': f"{emoji} {mode.capitalize()}",
        'Mkm/an 2025': f"{km_2025_territoire:.0f}",
        'Mkm/an 2050': f"{km_2050_territoire:.0f}",
        'Part 2025 (%)': f"{parts_2025[mode]:.1f}%",
        'Part 2050 (%)': f"{resultats['parts_2050'][mode]:.1f}%",
        'CO₂ 2025 (kg/hab/an)': f"{emissions_hab_an[mode]:.0f}",
        'CO₂ 2050 (kg/hab/an)': f"{emissions_2050_hab[mode]:.0f}"
    })

df_comparaison = pd.DataFrame(data_comparaison)
st.dataframe(df_comparaison, use_container_width=True, hide_index=True)

# Détails calculs
with st.expander("🔍 Vérification des calculs"):
    st.markdown(f"""
    **Ordre appliqué : 1. Sobriété → 2. Report modal**
    
    **1. Sobriété ({st.session_state.scenario['reduction_km']:+}%) :**
    - Km territoriaux 2025 : {sum(st.session_state.km_2025_territoire.values()):.0f} Mkm
    - Facteur sobriété : {1 + st.session_state.scenario['reduction_km']/100:.3f}
    - Km après sobriété : {sum(st.session_state.km_2025_territoire.values()) * (1 + st.session_state.scenario['reduction_km']/100):.0f} Mkm
    
    **2. Report modal (appliqué sur km après sobriété) :**
    - Voiture après sobriété : {st.session_state.km_2025_territoire['voiture'] * (1 + st.session_state.scenario['reduction_km']/100):.0f} Mkm
    - Transfert vélo : {st.session_state.scenario['report_velo']}% = {st.session_state.km_2025_territoire['voiture'] * (1 + st.session_state.scenario['reduction_km']/100) * st.session_state.scenario['report_velo']/100:.1f} Mkm
    - Transfert bus : {st.session_state.scenario['report_bus']}% = {st.session_state.km_2025_territoire['voiture'] * (1 + st.session_state.scenario['reduction_km']/100) * st.session_state.scenario['report_bus']/100:.1f} Mkm
    - Transfert train : {st.session_state.scenario['report_train']}% = {st.session_state.km_2025_territoire['voiture'] * (1 + st.session_state.scenario['reduction_km']/100) * st.session_state.scenario['report_train']/100:.1f} Mkm
    
    **3. Km finaux 2050 :**
    - Voiture : {resultats['km_2050_territoire']['voiture']:.0f} Mkm
    - Total : {resultats['bilan_2050']['km_total_territoire']:.0f} Mkm
    
    **4. Émissions voiture 2050 :**
    - Mix : {st.session_state.scenario['part_thermique']}% thermique + {st.session_state.scenario['part_ve']}% électrique
    - Allègement : -{st.session_state.scenario['reduction_poids']}%
    - Taux occupation : {st.session_state.scenario['taux_remplissage']:.1f} pers/véh
    
    ✅ Pas de double application de la sobriété
    """)

# ==================== QUESTIONS DÉBAT ====================

st.divider()
st.header("💡 Questions pour le débat")

with st.expander("❓ Objectif atteint ?", expanded=not resultats['objectif_atteint']):
    if resultats['objectif_atteint']:
        st.success(f"✅ Objectif atteint : -{resultats['reduction_pct']:.1f}%")
        st.write("**À analyser :** Quels leviers ont été décisifs ? Le scénario est-il réaliste ?")
    else:
        st.error(f"❌ Objectif non atteint : -{resultats['reduction_pct']:.1f}%")
        st.write(f"**Manque : {80 - resultats['reduction_pct']:.1f} points**. Quels leviers actionner davantage ?")

with st.expander("❓ Rôle de chaque levier"):
    st.markdown(f"""
    **Votre scénario :**
    - Sobriété : {st.session_state.scenario['reduction_km']:+}%
    - Report modal voiture : {st.session_state.scenario['report_velo'] + st.session_state.scenario['report_bus'] + st.session_state.scenario['report_train']}%
    - Report modal avion : {st.session_state.scenario['report_train_avion']}%
    - Taux remplissage : {st.session_state.scenario['taux_remplissage']:.1f} pers/véh
    - Électrification : {st.session_state.scenario['part_ve']}%
    - Allègement : -{st.session_state.scenario['reduction_poids']}%
    
    💡 Testez en n'activant qu'un seul levier à la fois pour mesurer son impact.
    """)

# ==================== SYNTHÈSE ====================

st.divider()
st.header("📚 Points clés à retenir")

st.info("""
**🎯 Enseignements :**

1. **Approche systémique** : Combiner TOUS les leviers
2. **Ordre des actions** : Sobriété → Report modal → Décarbonation
3. **Échelle territoire** : 350 000 habitants = leviers collectifs nécessaires
4. **Acceptabilité sociale** : Changements comportementaux = enjeu majeur
5. **Temporalité** : 2050 = 25 ans. Agir MAINTENANT.
""")

# ==================== EXPORT ====================

st.divider()
st.subheader("💾 Exporter le scénario")

resume = f"""
═══════════════════════════════════════════════════
SCÉNARIO MOBILITÉ PAYS BASQUE 2050
═══════════════════════════════════════════════════
Territoire : Communauté Pays Basque (350 000 habitants)

BILAN 2025 :
- Km totaux : {bilan_2025['km_total_territoire']:.0f} Mkm/an
- CO₂ total : {bilan_2025['co2_total_territoire']:.0f} tonnes/an
- CO₂/hab : {co2_par_hab:.0f} kg/an

SCÉNARIO 2050 :
- Sobriété : {st.session_state.scenario['reduction_km']:+}%
- Report modal : {st.session_state.scenario['report_velo'] + st.session_state.scenario['report_bus'] + st.session_state.scenario['report_train']}% (voiture)
- Électrification : {st.session_state.scenario['part_ve']}%
- Taux remplissage : {st.session_state.scenario['taux_remplissage']:.1f}
- Allègement : -{st.session_state.scenario['reduction_poids']}%

RÉSULTATS 2050 :
- CO₂ total : {resultats['bilan_2050']['co2_total_territoire']:.0f} tonnes/an
- CO₂/hab : {co2_par_hab_2050:.0f} kg/an
- Réduction : {resultats['reduction_pct']:.1f}%
- Objectif : {"✅ ATTEINT" if resultats['objectif_atteint'] else "❌ NON ATTEINT"}

═══════════════════════════════════════════════════
Sources : EMD Pays Basque, PCAET, ENTD 2019
         Base Carbone ADEME, impactCO2.fr
═══════════════════════════════════════════════════
"""

st.download_button(
    label="📥 Télécharger (TXT)",
    data=resume,
    file_name=f"scenario_PB_2050_{resultats['reduction_pct']:.0f}pct.txt",
    mime="text/plain",
    use_container_width=True
)

# ==================== FOOTER ====================

st.divider()
st.markdown("""
<div style='text-align: center; color: #6b7280; font-size: 0.875rem; padding: 1rem;'>
    <p><strong>📚 Sources :</strong> 
        EMD Pays Basque • PCAET • ENTD 2019 • 
        <a href='https://base-empreinte.ademe.fr/' target='_blank'>Base Carbone ADEME</a> • 
        <a href='https://impactco2.fr' target='_blank'>impactCO2.fr</a>
    </p>
    <p style='margin-top: 1rem;'>
        <strong>🎓 Application pédagogique</strong> • Communauté Pays Basque (350 000 hab) • 2025-2050
    </p>
</div>
""", unsafe_allow_html=True)
