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
DISTANCE_TERRE_SOLEIL = 149.6e6  # km

# ==================== FONCTION FORMATAGE ====================
def format_nombre(n, decimales=0):
    """Formate un nombre avec espaces entre milliers"""
    if decimales == 0:
        return f"{n:,.0f}".replace(',', ' ')
    else:
        return f"{n:,.{decimales}f}".replace(',', ' ')

# ==================== INITIALISATION ====================
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    
    # Situation 2025 - TERRITOIRE Pays Basque (350 000 habitants)
    # Sources : EMD Pays Basque, PCAET, ENTD 2019
    # Valeurs en millions de km/an pour tout le territoire
    st.session_state.km_2025_territoire = {
        'voiture': 3275,  # Mkm/an
        'bus': 55,        # Mkm/an
        'train': 210,     # Mkm/an
        'velo': 140,      # Mkm/an
        'avion': 900,     # Mkm/an (forte composante touristique)
        'marche': 70      # Mkm/an
    }
    
    # Nombre de déplacements par an par habitant (moyenne)
    st.session_state.nb_depl_hab = {
        'voiture': 401.5,    # ~1.1/jour × 365
        'bus': 219.0,        # ~0.6/jour × 365
        'train': 54.75,      # ~0.15/jour × 365
        'velo': 255.5,       # ~0.7/jour × 365
        'avion': 5.11,       # ~0.014/jour × 365
        'marche': 511.0      # ~1.4/jour × 365
    }
    
    # Caractéristiques parc automobile 2025 Pays Basque
    st.session_state.parc_2025 = {
        'part_ve': 3,  # % véhicules électriques
        'part_thermique': 97,
        'emission_thermique': 218,  # gCO2/km ACV (Base Carbone)
        'taux_occupation': 1.3,
        'temps_stationnement': 95
    }
    
    # Caractéristiques parc vélo 2025
    st.session_state.parc_velo_2025 = {
        'part_elec': 15,  # % vélos électriques
        'part_classique': 85,
        'emission_elec': 22,  # gCO2/km ACV (fabrication + électricité)
        'emission_classique': 5  # gCO2/km ACV
    }
    
    # Caractéristiques parc bus 2025
    st.session_state.parc_bus_2025 = {
        'part_elec': 5,  # % bus électriques
        'part_thermique': 95,
        'emission_thermique': 127,  # gCO2/km ACV (Base Carbone)
        'emission_electrique': 25   # gCO2/km ACV
    }
    
    # Facteurs d'émission ACV (autres modes)
    # Sources ADEME Base Carbone 2024 + impactCO2
    st.session_state.emissions = {
        'voiture_electrique': 103,  # gCO2/km ACV
        'bus_thermique': 127,
        'bus_electrique': 25,
        'train': 5.1,
        'velo_elec': 22,
        'velo_classique': 5,
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
        'part_velo_elec': 15,
        'part_velo_classique': 85,
        'part_bus_elec': 5,
        'part_bus_thermique': 95,
        'reduction_poids': 0
    }

# ==================== FONCTIONS ====================

def calculer_bilan_territoire(km_territoire, emissions_parc, parc_config, parc_velo_config, parc_bus_config, reduction_poids=0):
    """
    Calcule CO2 total du territoire en tenant compte :
    - du mix voiture thermique/électrique
    - du mix vélo électrique/classique
    - du mix bus thermique/électrique
    - du taux de remplissage
    - de la réduction de poids (tous véhicules)
    
    km_territoire : dict avec km en millions/an
    """
    co2_total_territoire = 0  # tonnes CO2/an
    detail_par_mode = {}
    
    for mode in km_territoire:
        if mode == 'voiture':
            # Effet allègement : -10% poids = -7% consommation (tous véhicules)
            facteur_allegement = 1 - (reduction_poids * 0.7 / 100)
            emission_thermique_ajustee = emissions_parc['emission_thermique'] * facteur_allegement
            emission_electrique_ajustee = emissions_parc['voiture_electrique'] * facteur_allegement
            
            # Mix thermique/électrique
            emission_voiture = (
                parc_config['part_thermique'] / 100 * emission_thermique_ajustee +
                parc_config['part_ve'] / 100 * emission_electrique_ajustee
            )
            
            # Diviser par taux de remplissage
            emission_par_personne = emission_voiture / parc_config['taux_occupation']
            
            # km en millions → CO2 en tonnes
            co2_mode = km_territoire[mode] * 1e6 * emission_par_personne / 1000 / 1000  # tonnes CO2
        
        elif mode == 'bus':
            # Mix bus thermique/électrique (pas d'allègement sur bus)
            emission_bus = (
                parc_bus_config['part_thermique'] / 100 * emissions_parc['bus_thermique'] +
                parc_bus_config['part_elec'] / 100 * emissions_parc['bus_electrique']
            )
            co2_mode = km_territoire[mode] * 1e6 * emission_bus / 1000 / 1000  # tonnes CO2
        
        elif mode == 'velo':
            # Mix vélo électrique/classique
            emission_velo = (
                parc_velo_config['part_elec'] / 100 * emissions_parc['velo_elec'] +
                parc_velo_config['part_classique'] / 100 * emissions_parc['velo_classique']
            )
            co2_mode = km_territoire[mode] * 1e6 * emission_velo / 1000 / 1000  # tonnes CO2
        
        elif mode in ['train', 'avion', 'marche']:
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
    
    parc_velo_2050 = {
        'part_elec': st.session_state.scenario['part_velo_elec'],
        'part_classique': st.session_state.scenario['part_velo_classique']
    }
    
    parc_bus_2050 = {
        'part_elec': st.session_state.scenario['part_bus_elec'],
        'part_thermique': st.session_state.scenario['part_bus_thermique']
    }
    
    emissions_2050 = st.session_state.emissions.copy()
    emissions_2050['emission_thermique'] = st.session_state.parc_2025['emission_thermique']
    
    # 5. Calcul bilans
    bilan_2025 = calculer_bilan_territoire(
        st.session_state.km_2025_territoire,
        {**st.session_state.emissions, 'emission_thermique': st.session_state.parc_2025['emission_thermique']},
        st.session_state.parc_2025,
        st.session_state.parc_velo_2025,
        st.session_state.parc_bus_2025,
        reduction_poids=0
    )
    
    bilan_2050 = calculer_bilan_territoire(
        km_2050_territoire,
        emissions_2050,
        parc_2050,
        parc_velo_2050,
        parc_bus_2050,
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

st.header("🔍 Étape 1 : Diagnostic 2025 - Territoire Pays Basque")
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
    st.markdown("**Dépl./an/hab**")

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
        "nb_v", 0.0, 2000.0, st.session_state.nb_depl_hab['voiture'], 10.0,
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
        "nb_b", 0.0, 1000.0, st.session_state.nb_depl_hab['bus'], 10.0,
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
        "nb_t", 0.0, 500.0, st.session_state.nb_depl_hab['train'], 5.0,
        format="%.1f", label_visibility="collapsed", key="input_nb_t"
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
        "nb_ve", 0.0, 1000.0, st.session_state.nb_depl_hab['velo'], 10.0,
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
        "nb_a", 0.0, 100.0, st.session_state.nb_depl_hab['avion'], 1.0,
        format="%.1f", label_visibility="collapsed", key="input_nb_a"
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
        "nb_m", 0.0, 2000.0, st.session_state.nb_depl_hab['marche'], 10.0,
        format="%.1f", label_visibility="collapsed", key="input_nb_m"
    )

st.divider()

# Caractéristiques parc bus 2025
st.subheader("🚌 Caractéristiques parc bus 2025")

col1, col2, col3 = st.columns(3)

with col1:
    st.session_state.parc_bus_2025['part_elec'] = st.number_input(
        "Part bus électriques (%)",
        min_value=0, max_value=100, value=st.session_state.parc_bus_2025['part_elec'],
        step=1, help="Parc circulant bus électriques"
    )
    st.session_state.parc_bus_2025['part_thermique'] = 100 - st.session_state.parc_bus_2025['part_elec']
    st.caption(f"Part bus thermiques : {st.session_state.parc_bus_2025['part_thermique']}%")

with col2:
    st.session_state.emissions['bus_thermique'] = st.number_input(
        "Émission bus thermique (gCO₂/km ACV)",
        min_value=0, max_value=300, value=st.session_state.emissions['bus_thermique'],
        step=5, help="Base Carbone ADEME"
    )

with col3:
    st.session_state.emissions['bus_electrique'] = st.number_input(
        "Émission bus électrique (gCO₂/km ACV)",
        min_value=0, max_value=100, value=st.session_state.emissions['bus_electrique'],
        step=5, help="Fabrication + électricité"
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

# Caractéristiques parc vélo 2025
st.subheader("🚴 Caractéristiques parc vélo 2025")

col1, col2, col3 = st.columns(3)

with col1:
    st.session_state.parc_velo_2025['part_elec'] = st.number_input(
        "Part vélos électriques (%)",
        min_value=0, max_value=100, value=st.session_state.parc_velo_2025['part_elec'],
        step=1, help="Parc circulant vélos électriques"
    )
    st.session_state.parc_velo_2025['part_classique'] = 100 - st.session_state.parc_velo_2025['part_elec']
    st.caption(f"Part vélos classiques : {st.session_state.parc_velo_2025['part_classique']}%")

with col2:
    st.session_state.emissions['velo_elec'] = st.number_input(
        "Émission vélo électrique (gCO₂/km ACV)",
        min_value=0, max_value=50, value=st.session_state.emissions['velo_elec'],
        step=1, help="Fabrication + électricité"
    )

with col3:
    st.session_state.emissions['velo_classique'] = st.number_input(
        "Émission vélo classique (gCO₂/km ACV)",
        min_value=0, max_value=20, value=st.session_state.emissions['velo_classique'],
        step=1, help="Fabrication uniquement"
    )

st.divider()

# Facteurs émission autres modes
with st.expander("⚙️ Facteurs d'émission autres modes (gCO₂/km ACV)"):
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.emissions['train'] = st.number_input("Train", 0.0, 50.0, st.session_state.emissions['train'], 0.5)
        st.session_state.emissions['avion'] = st.number_input("Avion", 0, 500, st.session_state.emissions['avion'], 10, help="impactCO2.fr : 225g")
    with col2:
        st.session_state.emissions['marche'] = st.number_input("Marche", 0, 10, st.session_state.emissions['marche'], 1)
        st.caption("**Sources** : [Base Carbone](https://base-empreinte.ademe.fr/), [impactCO2](https://impactco2.fr/outils/transport)")

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
    st.session_state.parc_velo_2025,
    st.session_state.parc_bus_2025,
    reduction_poids=0
)
parts_2025 = calculer_parts_modales(st.session_state.km_2025_territoire)

# Calculs par habitant
co2_par_hab = (bilan_2025['co2_total_territoire'] * 1000) / POPULATION_PB  # kg/hab/an
km_par_hab = (bilan_2025['km_total_territoire'] * 1e6) / POPULATION_PB / 52  # km/hab/semaine
depl_par_hab_jour = sum(st.session_state.nb_depl_hab.values())

# Calcul équivalent Terre-Soleil
nb_terre_soleil = (bilan_2025['km_total_territoire'] * 1e6) / DISTANCE_TERRE_SOLEIL

st.divider()

# Affichage bilan
st.success("✅ Bilan 2025 validé")
st.header("📊 Bilan 2025")

# Métriques territoire
st.subheader("🌍 Échelle territoire (350 000 habitants)")
col1, col2 = st.columns(2)
with col1:
    st.metric("Km totaux/an", f"{format_nombre(bilan_2025['km_total_territoire'])} Mkm")
    st.caption(f"Soit {nb_terre_soleil:.1f} fois la distance Terre-Soleil")
with col2:
    st.metric("CO₂ total/an", f"{format_nombre(bilan_2025['co2_total_territoire'])} tonnes", 
              help=f"{bilan_2025['co2_total_territoire']/1000:.1f} kt CO2")

st.divider()

# Métriques par habitant
st.subheader("👤 Échelle habitant (moyennes)")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("CO₂/habitant/an", f"{format_nombre(co2_par_hab)} kg")
with col2:
    st.metric("Km/habitant/semaine", f"{format_nombre(km_par_hab)} km")
with col3:
    st.metric("Déplacements/habitant/an", f"{format_nombre(depl_par_hab_jour)}")

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

st.info("""
**💡 Hypothèses du scénario 2050 :**

Par souci de simplification pédagogique, nous considérons que :
- Les **émissions par km par véhicule restent constantes** (sauf voitures via allègement)
- Seuls l'**électrification** et l'**allègement des véhicules** permettent de réduire les émissions par km
- Le **report modal** transfère des km vers des modes moins émetteurs
- La **sobriété** réduit le nombre total de km parcourus
- Le **taux de remplissage** optimise l'usage des véhicules existants

⚠️ Note : L'électrification du vélo augmente légèrement ses émissions, mais peut favoriser le report modal depuis la voiture (distances plus longues, relief).
""")

# Leviers avec saisie directe + boutons
with st.expander("🔧 **LEVIER 1 : Électrification** - Décarboner les parcs", expanded=False):
    st.markdown("**Objectif :** Remplacer véhicules thermiques par électriques")
    
    st.markdown("##### 🚗 Parc automobile")
    part_ve_temp = st.slider(
        "Part véhicules électriques (%)",
        min_value=0, max_value=100, value=st.session_state.scenario['part_ve'],
        step=5, key="lever_part_ve"
    )
    st.info(f"Part thermique : **{100 - part_ve_temp}%**")
    
    st.divider()
    
    st.markdown("##### 🚌 Parc bus")
    part_bus_elec_temp = st.slider(
        "Part bus électriques (%)",
        min_value=0, max_value=100, value=st.session_state.scenario['part_bus_elec'],
        step=5, key="lever_part_bus_elec"
    )
    st.info(f"Part bus thermiques : **{100 - part_bus_elec_temp}%**")
    
    st.divider()
    
    st.markdown("##### 🚴 Parc vélo")
    st.caption("⚠️ L'électrification du vélo augmente légèrement ses émissions, mais favorise le report modal depuis la voiture")
    part_velo_elec_temp = st.slider(
        "Part vélos électriques (%)",
        min_value=0, max_value=100, value=st.session_state.scenario['part_velo_elec'],
        step=5, key="lever_part_velo_elec"
    )
    st.info(f"Part vélos classiques : **{100 - part_velo_elec_temp}%**")

with st.expander("🔧 **LEVIER 2 : Sobriété** - Réduire les km parcourus", expanded=False):
    st.markdown("**Objectif :** Diminuer le besoin de déplacement")
    
    reduction_km_temp = st.slider(
        "Variation des km totaux par rapport à 2025 (%)",
        min_value=-50, max_value=10, value=st.session_state.scenario['reduction_km'],
        step=5, key="lever_reduction"
    )
    
    km_total_2025 = sum(st.session_state.km_2025_territoire.values())
    km_total_2050_prevision = km_total_2025 * (1 + reduction_km_temp / 100)
    
    if reduction_km_temp < 0:
        st.success(f"✅ Réduction : {format_nombre(km_total_2025)} Mkm → {format_nombre(km_total_2050_prevision)} Mkm ({abs(reduction_km_temp)}%)")
    elif reduction_km_temp > 0:
        st.warning(f"⚠️ Augmentation : {format_nombre(km_total_2025)} Mkm → {format_nombre(km_total_2050_prevision)} Mkm (+{reduction_km_temp}%)")
    else:
        st.info(f"➡️ Stabilité : {format_nombre(km_total_2025)} Mkm")

with st.expander("🔧 **LEVIER 3 : Report modal** - Transférer vers modes décarbonés", expanded=False):
    st.markdown("**Objectif :** Transférer des km vers des modes moins émetteurs")
    st.caption("Valeurs = % des km du mode d'origine transférés (appliqué APRÈS sobriété)")
    
    st.markdown("##### 🚗 Report depuis la voiture")
    
    # Report vélo
    st.markdown("🚴 **Voiture → Vélo (%)**")
    report_velo_temp = st.slider(
        "Report vélo",
        min_value=0, max_value=50, value=st.session_state.scenario['report_velo'],
        step=1, label_visibility="collapsed", key="slider_report_velo"
    )
    
    # Report bus
    st.markdown("🚌 **Voiture → Bus/TC (%)**")
    report_bus_temp = st.slider(
        "Report bus",
        min_value=0, max_value=50, value=st.session_state.scenario['report_bus'],
        step=1, label_visibility="collapsed", key="slider_report_bus"
    )
    
    # Report train (depuis voiture)
    st.markdown("🚆 **Voiture → Train (%)**")
    report_train_temp = st.slider(
        "Report train",
        min_value=0, max_value=50, value=st.session_state.scenario['report_train'],
        step=1, label_visibility="collapsed", key="slider_report_train"
    )
    
    report_total_voiture = report_velo_temp + report_bus_temp + report_train_temp
    st.info(f"**Report total depuis voiture : {report_total_voiture}%**")
    
    st.divider()
    st.markdown("##### ✈️ Report depuis l'avion")
    
    # Report train (depuis avion)
    st.markdown("🚆 **Avion → Train (%)**")
    report_train_avion_temp = st.slider(
        "Report avion",
        min_value=0, max_value=100, value=st.session_state.scenario['report_train_avion'],
        step=1, label_visibility="collapsed", key="slider_report_avion"
    )
    
    st.info(f"**{report_train_avion_temp}%** des km avion transférés vers le train")

with st.expander("🔧 **LEVIER 4 : Taux de remplissage** - Augmenter l'occupation des véhicules", expanded=False):
    st.markdown("**Objectif :** Plus de personnes par véhicule")
    
    taux_remplissage_temp = st.slider(
        "Taux d'occupation (pers/véhicule)",
        min_value=1.0, max_value=3.0, value=st.session_state.scenario['taux_remplissage'],
        step=0.1, format="%.1f", key="slider_taux_remp"
    )
    
    gain_remplissage = ((taux_remplissage_temp - st.session_state.parc_2025['taux_occupation']) / 
                        st.session_state.parc_2025['taux_occupation']) * 100
    
    if gain_remplissage > 0:
        st.success(f"✅ +{gain_remplissage:.1f}% vs 2025")
    elif gain_remplissage < 0:
        st.warning(f"⚠️ {gain_remplissage:.1f}% vs 2025")
    else:
        st.info("➡️ Identique à 2025")

with st.expander("🔧 **LEVIER 5 : Allègement** - Réduire le poids des véhicules", expanded=False):
    st.markdown("**Objectif :** Véhicules plus légers, moins consommateurs")
    st.caption("Impact : -10% poids = -7% consommation (thermique ET électrique)")
    
    reduction_poids_temp = st.slider(
        "Réduction poids (%)",
        min_value=0, max_value=30, value=st.session_state.scenario['reduction_poids'],
        step=5, key="slider_red_poids"
    )
    
    if reduction_poids_temp > 0:
        reduction_conso = reduction_poids_temp * 0.7
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
            'part_velo_elec': st.session_state.parc_velo_2025['part_elec'],
            'part_velo_classique': st.session_state.parc_velo_2025['part_classique'],
            'part_bus_elec': st.session_state.parc_bus_2025['part_elec'],
            'part_bus_thermique': st.session_state.parc_bus_2025['part_thermique'],
            'reduction_poids': 0
        }
        st.session_state.scenario_2050_valide = False
        st.rerun()

with col_btn3:
    if st.button("✅ Valider le scénario 2050", type="primary", use_container_width=True, key="valider_2050"):
        # Enregistrer les valeurs temporaires dans le scénario
        st.session_state.scenario['part_ve'] = part_ve_temp
        st.session_state.scenario['part_thermique'] = 100 - part_ve_temp
        st.session_state.scenario['part_bus_elec'] = part_bus_elec_temp
        st.session_state.scenario['part_bus_thermique'] = 100 - part_bus_elec_temp
        st.session_state.scenario['part_velo_elec'] = part_velo_elec_temp
        st.session_state.scenario['part_velo_classique'] = 100 - part_velo_elec_temp
        st.session_state.scenario['reduction_km'] = reduction_km_temp
        st.session_state.scenario['report_velo'] = report_velo_temp
        st.session_state.scenario['report_bus'] = report_bus_temp
        st.session_state.scenario['report_train'] = report_train_temp
        st.session_state.scenario['report_train_avion'] = report_train_avion_temp
        st.session_state.scenario['taux_remplissage'] = taux_remplissage_temp
        st.session_state.scenario['reduction_poids'] = reduction_poids_temp
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
km_par_hab_an_2050 = (resultats['bilan_2050']['km_total_territoire'] * 1e6) / POPULATION_PB
km_par_hab_an_2025 = (resultats['bilan_2025']['km_total_territoire'] * 1e6) / POPULATION_PB

# Calcul équivalent Terre-Soleil 2050
nb_terre_soleil_2050 = (resultats['bilan_2050']['km_total_territoire'] * 1e6) / DISTANCE_TERRE_SOLEIL

# Métriques principales
col1, col2, col3 = st.columns(3)

with col1:
    delta_co2_territoire = resultats['bilan_2050']['co2_total_territoire'] - resultats['bilan_2025']['co2_total_territoire']
    st.metric(
        "🌍 CO₂ territoire 2050",
        f"{format_nombre(resultats['bilan_2050']['co2_total_territoire'])} tonnes/an",
        delta=f"{format_nombre(delta_co2_territoire)} t/an",
        delta_color="inverse"
    )
    st.caption(f"Par habitant : {format_nombre(co2_par_hab_2050)} kg/an")

with col2:
    st.metric(
        "📉 Réduction vs 2025",
        f"{resultats['reduction_pct']:.1f}%",
        delta=None
    )

with col3:
    if resultats['objectif_atteint']:
        st.success("🏆 **Félicitations !**\n\nVous avez atteint l'objectif SNBC !\n\nMaintenant, à vous de jouer pour expliquer quelles actions mener pour chaque levier.")
    else:
        st.error(f"❌ **Objectif non atteint**\n\nBesoin : -80%\nActuel : -{resultats['reduction_pct']:.1f}%")

st.divider()

# Métriques km comparaison
st.subheader("🛣️ Kilomètres parcourus - Comparaison")
col1, col2 = st.columns(2)
with col1:
    st.metric(
        "Km totaux 2025",
        f"{format_nombre(resultats['bilan_2025']['km_total_territoire'])} Mkm/an"
    )
    st.caption(f"Soit {nb_terre_soleil:.1f} fois la distance Terre-Soleil")
    st.caption(f"Par habitant : {format_nombre(km_par_hab_an_2025)} km/an")
with col2:
    delta_km = resultats['bilan_2050']['km_total_territoire'] - resultats['bilan_2025']['km_total_territoire']
    st.metric(
        "Km totaux 2050",
        f"{format_nombre(resultats['bilan_2050']['km_total_territoire'])} Mkm/an",
        delta=f"{format_nombre(delta_km)} Mkm/an",
        delta_color="inverse"
    )
    st.caption(f"Soit {nb_terre_soleil_2050:.1f} fois la distance Terre-Soleil")
    st.caption(f"Par habitant : {format_nombre(km_par_hab_an_2050)} km/an")

st.divider()

# Jauge de progression vers objectif 80%
st.subheader("🎯 Progression vers l'objectif SNBC")

fig_jauge = go.Figure(go.Indicator(
    mode = "gauge+number+delta",
    value = resultats['reduction_pct'],
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text': "Réduction des émissions (%)", 'font': {'size': 24}},
    delta = {'reference': 80, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
    gauge = {
        'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
        'bar': {'color': "lightgreen" if resultats['reduction_pct'] >= 80 else "orange"},
        'bgcolor': "white",
        'borderwidth': 2,
        'bordercolor': "gray",
        'steps': [
            {'range': [0, 50], 'color': '#fee2e2'},
            {'range': [50, 80], 'color': '#fed7aa'},
            {'range': [80, 100], 'color': '#d1fae5'}],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': 80}}))

fig_jauge.update_layout(height=300, font={'size': 16})
st.plotly_chart(fig_jauge, use_container_width=True)

st.divider()

# Graphique en cascade - Contribution de chaque levier
st.subheader("📊 Contribution de chaque levier à la réduction")

# Calcul des contributions individuelles
co2_2025_base = resultats['bilan_2025']['co2_total_territoire']

# Scénario de référence (aucun levier)
scenario_ref = {
    'reduction_km': 0,
    'report_velo': 0,
    'report_bus': 0,
    'report_train': 0,
    'report_train_avion': 0,
    'taux_remplissage': st.session_state.parc_2025['taux_occupation'],
    'part_ve': st.session_state.parc_2025['part_ve'],
    'part_thermique': st.session_state.parc_2025['part_thermique'],
    'part_velo_elec': st.session_state.parc_velo_2025['part_elec'],
    'part_velo_classique': st.session_state.parc_velo_2025['part_classique'],
    'reduction_poids': 0
}

# Fonction pour calculer un scénario partiel
def calculer_scenario_partiel(modifications):
    scenario_temp = scenario_ref.copy()
    scenario_temp.update(modifications)
    
    # Sauvegarder le scénario actuel
    scenario_actuel = st.session_state.scenario.copy()
    
    # Appliquer le scénario temporaire
    st.session_state.scenario = scenario_temp
    
    # Calculer
    resultats_temp = calculer_2050()
    
    # Restaurer le scénario actuel
    st.session_state.scenario = scenario_actuel
    
    return resultats_temp['bilan_2050']['co2_total_territoire']

# Calcul des contributions (ordre d'application)
co2_apres_elec_voiture = calculer_scenario_partiel({
    'part_ve': st.session_state.scenario['part_ve'],
    'part_thermique': st.session_state.scenario['part_thermique']
})
contrib_elec_voiture = co2_2025_base - co2_apres_elec_voiture

co2_apres_elec_bus = calculer_scenario_partiel({
    'part_ve': st.session_state.scenario['part_ve'],
    'part_thermique': st.session_state.scenario['part_thermique'],
    'part_bus_elec': st.session_state.scenario['part_bus_elec'],
    'part_bus_thermique': st.session_state.scenario['part_bus_thermique']
})
contrib_elec_bus = co2_apres_elec_voiture - co2_apres_elec_bus

co2_apres_elec_velo = calculer_scenario_partiel({
    'part_ve': st.session_state.scenario['part_ve'],
    'part_thermique': st.session_state.scenario['part_thermique'],
    'part_bus_elec': st.session_state.scenario['part_bus_elec'],
    'part_bus_thermique': st.session_state.scenario['part_bus_thermique'],
    'part_velo_elec': st.session_state.scenario['part_velo_elec'],
    'part_velo_classique': st.session_state.scenario['part_velo_classique']
})
contrib_elec_velo = co2_apres_elec_bus - co2_apres_elec_velo

co2_apres_sobriete = calculer_scenario_partiel({
    'part_ve': st.session_state.scenario['part_ve'],
    'part_thermique': st.session_state.scenario['part_thermique'],
    'part_bus_elec': st.session_state.scenario['part_bus_elec'],
    'part_bus_thermique': st.session_state.scenario['part_bus_thermique'],
    'part_velo_elec': st.session_state.scenario['part_velo_elec'],
    'part_velo_classique': st.session_state.scenario['part_velo_classique'],
    'reduction_km': st.session_state.scenario['reduction_km']
})
contrib_sobriete = co2_apres_elec_velo - co2_apres_sobriete

co2_apres_report = calculer_scenario_partiel({
    'part_ve': st.session_state.scenario['part_ve'],
    'part_thermique': st.session_state.scenario['part_thermique'],
    'part_bus_elec': st.session_state.scenario['part_bus_elec'],
    'part_bus_thermique': st.session_state.scenario['part_bus_thermique'],
    'part_velo_elec': st.session_state.scenario['part_velo_elec'],
    'part_velo_classique': st.session_state.scenario['part_velo_classique'],
    'reduction_km': st.session_state.scenario['reduction_km'],
    'report_velo': st.session_state.scenario['report_velo'],
    'report_bus': st.session_state.scenario['report_bus'],
    'report_train': st.session_state.scenario['report_train'],
    'report_train_avion': st.session_state.scenario['report_train_avion']
})
contrib_report = co2_apres_sobriete - co2_apres_report

co2_apres_remplissage = calculer_scenario_partiel({
    'part_ve': st.session_state.scenario['part_ve'],
    'part_thermique': st.session_state.scenario['part_thermique'],
    'part_bus_elec': st.session_state.scenario['part_bus_elec'],
    'part_bus_thermique': st.session_state.scenario['part_bus_thermique'],
    'part_velo_elec': st.session_state.scenario['part_velo_elec'],
    'part_velo_classique': st.session_state.scenario['part_velo_classique'],
    'reduction_km': st.session_state.scenario['reduction_km'],
    'report_velo': st.session_state.scenario['report_velo'],
    'report_bus': st.session_state.scenario['report_bus'],
    'report_train': st.session_state.scenario['report_train'],
    'report_train_avion': st.session_state.scenario['report_train_avion'],
    'taux_remplissage': st.session_state.scenario['taux_remplissage']
})
contrib_remplissage = co2_apres_report - co2_apres_remplissage

co2_apres_allegement = calculer_scenario_partiel({
    'part_ve': st.session_state.scenario['part_ve'],
    'part_thermique': st.session_state.scenario['part_thermique'],
    'part_bus_elec': st.session_state.scenario['part_bus_elec'],
    'part_bus_thermique': st.session_state.scenario['part_bus_thermique'],
    'part_velo_elec': st.session_state.scenario['part_velo_elec'],
    'part_velo_classique': st.session_state.scenario['part_velo_classique'],
    'reduction_km': st.session_state.scenario['reduction_km'],
    'report_velo': st.session_state.scenario['report_velo'],
    'report_bus': st.session_state.scenario['report_bus'],
    'report_train': st.session_state.scenario['report_train'],
    'report_train_avion': st.session_state.scenario['report_train_avion'],
    'taux_remplissage': st.session_state.scenario['taux_remplissage'],
    'reduction_poids': st.session_state.scenario['reduction_poids']
})
contrib_allegement = co2_apres_remplissage - co2_apres_allegement

# Créer le graphique en cascade
fig_cascade = go.Figure(go.Waterfall(
    name = "Réduction CO₂",
    orientation = "v",
    measure = ["absolute", "relative", "relative", "relative", "relative", "relative", "relative", "relative", "total"],
    x = ["2025", "Élec. voitures", "Élec. bus", "Élec. vélos", "Sobriété", "Report modal", "Remplissage", "Allègement", "2050"],
    textposition = "outside",
    text = [f"{co2_2025_base:.0f}", 
            f"-{contrib_elec_voiture:.0f}" if contrib_elec_voiture > 0 else f"+{abs(contrib_elec_voiture):.0f}",
            f"-{contrib_elec_bus:.0f}" if contrib_elec_bus > 0 else f"+{abs(contrib_elec_bus):.0f}",
            f"-{contrib_elec_velo:.0f}" if contrib_elec_velo > 0 else f"+{abs(contrib_elec_velo):.0f}",
            f"-{contrib_sobriete:.0f}" if contrib_sobriete > 0 else f"+{abs(contrib_sobriete):.0f}",
            f"-{contrib_report:.0f}" if contrib_report > 0 else f"+{abs(contrib_report):.0f}",
            f"-{contrib_remplissage:.0f}" if contrib_remplissage > 0 else f"+{abs(contrib_remplissage):.0f}",
            f"-{contrib_allegement:.0f}" if contrib_allegement > 0 else f"+{abs(contrib_allegement):.0f}",
            f"{co2_apres_allegement:.0f}"],
    y = [co2_2025_base, 
         -contrib_elec_voiture,
         -contrib_elec_bus,
         -contrib_elec_velo,
         -contrib_sobriete,
         -contrib_report,
         -contrib_remplissage,
         -contrib_allegement,
         co2_apres_allegement],
    connector = {"line":{"color":"rgb(63, 63, 63)"}},
    decreasing = {"marker":{"color":"#10b981"}},
    increasing = {"marker":{"color":"#ef4444"}},
    totals = {"marker":{"color":"#3b82f6"}}
))

fig_cascade.update_layout(
    title = "Contribution de chaque levier (tonnes CO₂/an)",
    showlegend = False,
    height = 500,
    yaxis_title = "Émissions CO₂ (tonnes/an)"
)

st.plotly_chart(fig_cascade, use_container_width=True)

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
        'Mkm/an 2025': f"{format_nombre(km_2025_territoire)}",
        'Mkm/an 2050': f"{format_nombre(km_2050_territoire)}",
        'Part 2025 (%)': f"{parts_2025[mode]:.1f}%",
        'Part 2050 (%)': f"{resultats['parts_2050'][mode]:.1f}%",
        'CO₂ 2025 (kg/hab/an)': f"{format_nombre(emissions_hab_an[mode])}",
        'CO₂ 2050 (kg/hab/an)': f"{format_nombre(emissions_2050_hab[mode])}"
    })

df_comparaison = pd.DataFrame(data_comparaison)
st.dataframe(df_comparaison, use_container_width=True, hide_index=True)

# Détails calculs
with st.expander("🔍 Vérification des calculs"):
    st.markdown(f"""
    **Ordre appliqué : 1. Sobriété → 2. Report modal**
    
    **1. Sobriété ({st.session_state.scenario['reduction_km']:+}%) :**
    - Km territoriaux 2025 : {format_nombre(sum(st.session_state.km_2025_territoire.values()))} Mkm
    - Facteur sobriété : {1 + st.session_state.scenario['reduction_km']/100:.3f}
    - Km après sobriété : {format_nombre(sum(st.session_state.km_2025_territoire.values()) * (1 + st.session_state.scenario['reduction_km']/100))} Mkm
    
    **2. Report modal (appliqué sur km après sobriété) :**
    - Voiture après sobriété : {format_nombre(st.session_state.km_2025_territoire['voiture'] * (1 + st.session_state.scenario['reduction_km']/100))} Mkm
    - Transfert vélo : {st.session_state.scenario['report_velo']}% = {format_nombre(st.session_state.km_2025_territoire['voiture'] * (1 + st.session_state.scenario['reduction_km']/100) * st.session_state.scenario['report_velo']/100, 1)} Mkm
    - Transfert bus : {st.session_state.scenario['report_bus']}% = {format_nombre(st.session_state.km_2025_territoire['voiture'] * (1 + st.session_state.scenario['reduction_km']/100) * st.session_state.scenario['report_bus']/100, 1)} Mkm
    - Transfert train : {st.session_state.scenario['report_train']}% = {format_nombre(st.session_state.km_2025_territoire['voiture'] * (1 + st.session_state.scenario['reduction_km']/100) * st.session_state.scenario['report_train']/100, 1)} Mkm
    
    **3. Km finaux 2050 :**
    - Voiture : {format_nombre(resultats['km_2050_territoire']['voiture'])} Mkm
    - Total : {format_nombre(resultats['bilan_2050']['km_total_territoire'])} Mkm
    
    **4. Émissions voiture 2050 :**
    - Mix : {st.session_state.scenario['part_thermique']}% thermique + {st.session_state.scenario['part_ve']}% électrique
    - Allègement : -{st.session_state.scenario['reduction_poids']}%
    - Taux occupation : {st.session_state.scenario['taux_remplissage']:.1f} pers/véh
    
    **5. Émissions vélo 2050 :**
    - Mix : {st.session_state.scenario['part_velo_classique']}% classique + {st.session_state.scenario['part_velo_elec']}% électrique
    
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
    - Électrification voitures : {st.session_state.scenario['part_ve']}%
    - Électrification bus : {st.session_state.scenario['part_bus_elec']}%
    - Électrification vélos : {st.session_state.scenario['part_velo_elec']}%
    - Sobriété : {st.session_state.scenario['reduction_km']:+}%
    - Report modal voiture : {st.session_state.scenario['report_velo'] + st.session_state.scenario['report_bus'] + st.session_state.scenario['report_train']}%
    - Report modal avion : {st.session_state.scenario['report_train_avion']}%
    - Taux remplissage : {st.session_state.scenario['taux_remplissage']:.1f} pers/véh
    - Allègement : -{st.session_state.scenario['reduction_poids']}%
    
    💡 Testez en n'activant qu'un seul levier à la fois pour mesurer son impact.
    """)

# ==================== SYNTHÈSE ====================

st.divider()
st.header("📚 Points clés à retenir")

st.info("""
**🎯 Enseignements :**

1. **Approche systémique** : Combiner TOUS les leviers
2. **Ordre des actions** : Électrification + Sobriété → Report modal → Optimisation
3. **Échelle territoire** : 350 000 habitants = leviers collectifs nécessaires
4. **Acceptabilité sociale** : Changements comportementaux = enjeu majeur
5. **Temporalité** : 2050 = 25 ans. Agir MAINTENANT.
""")

# ==================== EXPORT ====================

st.divider()
st.subheader("💾 Exporter le scénario")

resume = f"""
╔═══════════════════════════════════════════════════
SCÉNARIO MOBILITÉ PAYS BASQUE 2050
╚═══════════════════════════════════════════════════
Territoire : Communauté Pays Basque (350 000 habitants)

BILAN 2025 :
- Km totaux : {format_nombre(bilan_2025['km_total_territoire'])} Mkm/an
- CO₂ total : {format_nombre(bilan_2025['co2_total_territoire'])} tonnes/an
- CO₂/hab : {format_nombre(co2_par_hab)} kg/an

SCÉNARIO 2050 :
- Électrification voitures : {st.session_state.scenario['part_ve']}%
- Électrification bus : {st.session_state.scenario['part_bus_elec']}%
- Électrification vélos : {st.session_state.scenario['part_velo_elec']}%
- Sobriété : {st.session_state.scenario['reduction_km']:+}%
- Report modal : {st.session_state.scenario['report_velo'] + st.session_state.scenario['report_bus'] + st.session_state.scenario['report_train']}% (voiture)
- Taux remplissage : {st.session_state.scenario['taux_remplissage']:.1f}
- Allègement : -{st.session_state.scenario['reduction_poids']}%

RÉSULTATS 2050 :
- CO₂ total : {format_nombre(resultats['bilan_2050']['co2_total_territoire'])} tonnes/an
- CO₂/hab : {format_nombre(co2_par_hab_2050)} kg/an
- Km totaux : {format_nombre(resultats['bilan_2050']['km_total_territoire'])} Mkm/an
- Réduction : {resultats['reduction_pct']:.1f}%
- Objectif : {"✅ ATTEINT" if resultats['objectif_atteint'] else "❌ NON ATTEINT"}

╔═══════════════════════════════════════════════════
Sources : EMD Pays Basque, PCAET, ENTD 2019
         Base Carbone ADEME, impactCO2.fr
╚═══════════════════════════════════════════════════
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
