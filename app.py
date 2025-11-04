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
    
    # Nombre de déplacements par SEMAINE
    st.session_state.nb_depl = {
        'voiture': 8,
        'bus': 4,
        'train': 1,
        'velo': 5,
        'avion': 0.1,  # ~5 vols/an
        'marche': 10
    }
    
    # Caractéristiques voiture 2025
    st.session_state.taux_occupation_2025 = 1.3  # pers/véhicule
    st.session_state.temps_stationnement_2025 = 95  # %
    
    # Facteurs d'émission ACV (Analyse Cycle de Vie = fabrication + usage)
    # Sources ADEME Base Carbone 2024
    st.session_state.emissions = {
        'voiture_thermique': 218,  # ACV complet (construction + usage)
        'voiture_electrique': 103, # ACV complet (batterie + élec France)
        'bus': 127,                # ACV complet
        'train': 5.1,              # ACV complet (infrastructure + élec)
        'velo': 5,                 # ACV complet (fabrication)
        'avion': 258,              # ACV vol moyen courrier
        'marche': 0
    }
    
    # Scénario 2050
    st.session_state.scenario = {
        'reduction_km': 0,
        'report_velo': 0,
        'report_bus': 0,
        'report_train': 0,
        'report_train_avion': 0,
        'taux_remplissage': 1.3,   # Valeur 2025 par défaut
        'part_ve': 3,
        'part_thermique': 97,
        'reduction_poids': 0
    }

# ==================== FONCTIONS ====================

def calculer_bilan(km_dict, emissions_dict, part_ve=0, taux_remplissage=1.3, reduction_poids=0):
    """
    Calcule CO2 total en tenant compte :
    - du mix voiture thermique/électrique
    - du taux de remplissage (divise émissions/km par le nb de personnes)
    - de la réduction de poids (diminue consommation thermique)
    """
    co2_total = 0
    detail_par_mode = {}
    
    for mode in km_dict:
        if mode == 'voiture':
            # Effet allègement sur thermique : -10% poids = -7% consommation
            facteur_allègement = 1 - (reduction_poids * 0.7 / 100)
            emission_thermique_ajustee = emissions_dict['voiture_thermique'] * facteur_allègement
            
            # Mix thermique/électrique
            emission_voiture = (
                (100 - part_ve) / 100 * emission_thermique_ajustee +
                part_ve / 100 * emissions_dict['voiture_electrique']
            )
            
            # Diviser par taux de remplissage (covoiturage)
            emission_voiture_par_personne = emission_voiture / taux_remplissage
            
            co2_mode = km_dict[mode] * emission_voiture_par_personne / 1000  # kg CO2
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
    
    # 2. Calcul des km par mode en 2025
    km_voiture_2025 = st.session_state.km_2025['voiture']
    km_avion_2025 = st.session_state.km_2025['avion']
    
    # 3. Report modal en VALEUR ABSOLUE (km transférés)
    # Report depuis voiture = % des km voiture 2025
    km_transferes_velo = km_voiture_2025 * st.session_state.scenario['report_velo'] / 100
    km_transferes_bus = km_voiture_2025 * st.session_state.scenario['report_bus'] / 100
    km_transferes_train_voiture = km_voiture_2025 * st.session_state.scenario['report_train'] / 100
    
    # Report depuis avion = % des km avion 2025
    km_transferes_train_avion = km_avion_2025 * st.session_state.scenario['report_train_avion'] / 100
    
    # 4. Application de la sobriété (réduction globale) PUIS report modal
    # Les km transférés sont calculés sur la base 2025, puis on applique la sobriété globale
    facteur_sobriete = (1 + st.session_state.scenario['reduction_km'] / 100)
    
    km_2050 = {}
    km_2050['voiture'] = (km_voiture_2025 - km_transferes_velo - km_transferes_bus - km_transferes_train_voiture) * facteur_sobriete
    km_2050['bus'] = (st.session_state.km_2025['bus'] + km_transferes_bus) * facteur_sobriete
    km_2050['train'] = (st.session_state.km_2025['train'] + km_transferes_train_voiture + km_transferes_train_avion) * facteur_sobriete
    km_2050['velo'] = (st.session_state.km_2025['velo'] + km_transferes_velo) * facteur_sobriete
    km_2050['avion'] = (km_avion_2025 - km_transferes_train_avion) * facteur_sobriete
    km_2050['marche'] = st.session_state.km_2025['marche'] * facteur_sobriete
    
    # 5. Calcul des parts modales 2050
    parts_2050 = calculer_parts_modales(km_2050)
    
    # 6. Calcul bilans
    bilan_2025 = calculer_bilan(
        st.session_state.km_2025, 
        st.session_state.emissions, 
        part_ve=3,
        taux_remplissage=st.session_state.taux_occupation_2025,
        reduction_poids=0
    )
    
    bilan_2050 = calculer_bilan(
        km_2050, 
        st.session_state.emissions, 
        part_ve=st.session_state.scenario['part_ve'],
        taux_remplissage=st.session_state.scenario['taux_remplissage'],
        reduction_poids=st.session_state.scenario['reduction_poids']
    )
    
    # 7. Calcul réduction
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

# Saisie des données - ALIGNEMENT VISUEL
st.subheader("🛣️ Distances et déplacements")

# Créer un tableau aligné
col_mode, col_km, col_nb, col_emission = st.columns([2, 2, 2, 2])

with col_mode:
    st.markdown("**Mode**")
    st.markdown("🚗 Voiture")
    st.markdown("🚌 Bus / TC")
    st.markdown("🚆 Train")
    st.markdown("🚴 Vélo")
    st.markdown("✈️ Avion")
    st.markdown("🚶 Marche")

with col_km:
    st.markdown("**Km/semaine**")
    st.session_state.km_2025['voiture'] = st.number_input("km_v", 0, 500, st.session_state.km_2025['voiture'], 10, label_visibility="collapsed")
    st.session_state.km_2025['bus'] = st.number_input("km_b", 0, 200, st.session_state.km_2025['bus'], 5, label_visibility="collapsed")
    st.session_state.km_2025['train'] = st.number_input("km_t", 0, 100, st.session_state.km_2025['train'], 5, label_visibility="collapsed")
    st.session_state.km_2025['velo'] = st.number_input("km_ve", 0, 100, st.session_state.km_2025['velo'], 5, label_visibility="collapsed")
    st.session_state.km_2025['avion'] = st.number_input("km_a", 0, 500, st.session_state.km_2025['avion'], 10, label_visibility="collapsed")
    st.session_state.km_2025['marche'] = st.number_input("km_m", 0, 50, st.session_state.km_2025['marche'], 5, label_visibility="collapsed")

with col_nb:
    st.markdown("**Dépl./semaine**")
    st.session_state.nb_depl['voiture'] = st.number_input("nb_v", 0, 50, st.session_state.nb_depl['voiture'], 1, label_visibility="collapsed")
    st.session_state.nb_depl['bus'] = st.number_input("nb_b", 0, 30, st.session_state.nb_depl['bus'], 1, label_visibility="collapsed")
    st.session_state.nb_depl['train'] = st.number_input("nb_t", 0, 20, st.session_state.nb_depl['train'], 1, label_visibility="collapsed")
    st.session_state.nb_depl['velo'] = st.number_input("nb_ve", 0, 30, st.session_state.nb_depl['velo'], 1, label_visibility="collapsed")
    st.session_state.nb_depl['avion'] = st.number_input("nb_a", 0.0, 5.0, st.session_state.nb_depl['avion'], 0.1, format="%.1f", label_visibility="collapsed")
    st.session_state.nb_depl['marche'] = st.number_input("nb_m", 0, 50, st.session_state.nb_depl['marche'], 1, label_visibility="collapsed")

with col_emission:
    st.markdown("**Émission ACV (gCO₂/km)**")
    st.session_state.emissions['voiture_thermique'] = st.number_input("em_v", 0, 500, st.session_state.emissions['voiture_thermique'], 10, label_visibility="collapsed", help="Voiture thermique")
    st.session_state.emissions['bus'] = st.number_input("em_b", 0, 300, st.session_state.emissions['bus'], 10, label_visibility="collapsed")
    st.session_state.emissions['train'] = st.number_input("em_t", 0.0, 50.0, st.session_state.emissions['train'], 0.5, label_visibility="collapsed")
    st.session_state.emissions['velo'] = st.number_input("em_ve", 0, 20, st.session_state.emissions['velo'], 1, label_visibility="collapsed")
    st.session_state.emissions['avion'] = st.number_input("em_a", 0, 500, st.session_state.emissions['avion'], 10, label_visibility="collapsed")
    st.text("0")

st.divider()

# Caractéristiques voiture et VE
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🚗 Caractéristiques voiture 2025")
    st.session_state.taux_occupation_2025 = st.number_input(
        "Taux d'occupation moyen (pers/véhicule)",
        min_value=1.0, max_value=4.0, value=st.session_state.taux_occupation_2025,
        step=0.1, format="%.1f"
    )
    st.session_state.temps_stationnement_2025 = st.number_input(
        "Temps stationné (%)",
        min_value=80, max_value=99, value=st.session_state.temps_stationnement_2025,
        step=1
    )

with col2:
    st.markdown("**💡 Sources**")
    st.caption("[Base Carbone ADEME](https://base-empreinte.ademe.fr/)")
    st.caption("ACV = Analyse Cycle de Vie")
    st.caption("(fabrication + usage)")

with col3:
    # Bouton validation
    if st.button("✅ Valider le bilan 2025", type="primary", use_container_width=True):
        st.session_state.bilan_2025_valide = True
        st.rerun()

# Calculs seulement si validé
if 'bilan_2025_valide' not in st.session_state:
    st.session_state.bilan_2025_valide = False

if not st.session_state.bilan_2025_valide:
    st.warning("⚠️ Complétez les données ci-dessus puis cliquez sur **Valider le bilan 2025**")
    st.stop()

# Calcul bilan 2025
bilan_2025 = calculer_bilan(
    st.session_state.km_2025, 
    st.session_state.emissions, 
    part_ve=3,
    taux_remplissage=st.session_state.taux_occupation_2025,
    reduction_poids=0
)
parts_2025 = calculer_parts_modales(st.session_state.km_2025)

st.divider()

# Affichage métriques principales
st.success("✅ Bilan 2025 validé")
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
    nb_depl_par_jour = nb_depl_total / 7
    st.metric("🔢 Déplacements/jour", f"{nb_depl_par_jour:.1f}", help=f"{nb_depl_total:.1f} déplacements/semaine")

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

st.warning("**🎯 Objectif SNBC : Réduire d'environ 80% les émissions du secteur transport d'ici 2050** (par rapport à 1990-2015)")

# Leviers avec boutons +/-
with st.expander("🔧 **LEVIER 1 : Sobriété** - Réduire les km parcourus", expanded=True):
    st.markdown("**Objectif :** Diminuer le besoin de déplacement")
    
    st.session_state.scenario['reduction_km'] = st.slider(
        "Variation des km totaux par rapport à 2025 (%)",
        min_value=-50, max_value=10, value=st.session_state.scenario['reduction_km'],
        step=5, key="lever_reduction"
    )
    
    km_total_2025 = sum(st.session_state.km_2025.values())
    km_total_2050_prevision = km_total_2025 * (1 + st.session_state.scenario['reduction_km'] / 100)
    
    if st.session_state.scenario['reduction_km'] < 0:
        st.success(f"✅ Réduction : {km_total_2025:.0f} km/sem → {km_total_2050_prevision:.0f} km/sem ({abs(st.session_state.scenario['reduction_km'])}%)")
    elif st.session_state.scenario['reduction_km'] > 0:
        st.warning(f"⚠️ Augmentation : {km_total_2025:.0f} km/sem → {km_total_2050_prevision:.0f} km/sem (+{st.session_state.scenario['reduction_km']}%)")
    else:
        st.info(f"➡️ Stabilité : {km_total_2025:.0f} km/sem")

with st.expander("🔧 **LEVIER 2 : Report modal** - Transférer vers modes décarbonés", expanded=True):
    st.markdown("**Objectif :** Transférer des km vers des modes moins émetteurs")
    st.caption("Valeurs = % des km du mode d'origine transférés")
    
    st.markdown("##### 🚗 Report depuis la voiture")
    
    # Report vélo
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"🚴 Voiture → Vélo : **{st.session_state.scenario['report_velo']}%**")
    with col2:
        if st.button("➖", key="velo_moins"):
            st.session_state.scenario['report_velo'] = max(0, st.session_state.scenario['report_velo'] - 1)
            st.rerun()
    with col3:
        if st.button("➕", key="velo_plus"):
            st.session_state.scenario['report_velo'] = min(50, st.session_state.scenario['report_velo'] + 1)
            st.rerun()
    
    # Report bus
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"🚌 Voiture → Bus/TC : **{st.session_state.scenario['report_bus']}%**")
    with col2:
        if st.button("➖", key="bus_moins"):
            st.session_state.scenario['report_bus'] = max(0, st.session_state.scenario['report_bus'] - 1)
            st.rerun()
    with col3:
        if st.button("➕", key="bus_plus"):
            st.session_state.scenario['report_bus'] = min(50, st.session_state.scenario['report_bus'] + 1)
            st.rerun()
    
    # Report train (depuis voiture)
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"🚆 Voiture → Train : **{st.session_state.scenario['report_train']}%**")
    with col2:
        if st.button("➖", key="train_moins"):
            st.session_state.scenario['report_train'] = max(0, st.session_state.scenario['report_train'] - 1)
            st.rerun()
    with col3:
        if st.button("➕", key="train_plus"):
            st.session_state.scenario['report_train'] = min(50, st.session_state.scenario['report_train'] + 1)
            st.rerun()
    
    report_total_voiture = (st.session_state.scenario['report_velo'] + 
                            st.session_state.scenario['report_bus'] + 
                            st.session_state.scenario['report_train'])
    st.info(f"**Report total depuis voiture : {report_total_voiture}%** des km voiture 2025")
    
    st.divider()
    st.markdown("##### ✈️ Report depuis l'avion")
    
    # Report train (depuis avion)
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"🚆 Avion → Train : **{st.session_state.scenario['report_train_avion']}%**")
    with col2:
        if st.button("➖", key="avion_moins"):
            st.session_state.scenario['report_train_avion'] = max(0, st.session_state.scenario['report_train_avion'] - 1)
            st.rerun()
    with col3:
        if st.button("➕", key="avion_plus"):
            st.session_state.scenario['report_train_avion'] = min(100, st.session_state.scenario['report_train_avion'] + 1)
            st.rerun()
    
    st.info(f"**{st.session_state.scenario['report_train_avion']}%** des km avion 2025 transférés vers le train")

with st.expander("🔧 **LEVIER 3 : Taux de remplissage** - Augmenter l'occupation des véhicules", expanded=True):
    st.markdown("**Objectif :** Plus de personnes par véhicule")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"Taux d'occupation : **{st.session_state.scenario['taux_remplissage']:.1f} pers/véhicule**")
    with col2:
        if st.button("➖", key="remplissage_moins"):
            st.session_state.scenario['taux_remplissage'] = max(1.0, st.session_state.scenario['taux_remplissage'] - 0.1)
            st.rerun()
    with col3:
        if st.button("➕", key="remplissage_plus"):
            st.session_state.scenario['taux_remplissage'] = min(3.0, st.session_state.scenario['taux_remplissage'] + 0.1)
            st.rerun()
    
    gain_remplissage = ((st.session_state.scenario['taux_remplissage'] - st.session_state.taux_occupation_2025) / st.session_state.taux_occupation_2025) * 100
    
    if gain_remplissage > 0:
        st.success(f"✅ +{gain_remplissage:.1f}% de personnes par voiture vs 2025")
    elif gain_remplissage < 0:
        st.warning(f"⚠️ {gain_remplissage:.1f}% vs 2025 (dégradation)")
    else:
        st.info("➡️ Identique à 2025")

with st.expander("🔧 **LEVIER 4 : Électrification** - Décarboner le parc automobile", expanded=True):
    st.markdown("**Objectif :** Remplacer véhicules thermiques par électriques")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"Part véhicules électriques : **{st.session_state.scenario['part_ve']}%**")
    with col2:
        if st.button("➖", key="ve_moins"):
            st.session_state.scenario['part_ve'] = max(0, st.session_state.scenario['part_ve'] - 5)
            st.session_state.scenario['part_thermique'] = 100 - st.session_state.scenario['part_ve']
            st.rerun()
    with col3:
        if st.button("➕", key="ve_plus"):
            st.session_state.scenario['part_ve'] = min(100, st.session_state.scenario['part_ve'] + 5)
            st.session_state.scenario['part_thermique'] = 100 - st.session_state.scenario['part_ve']
            st.rerun()
    
    st.info(f"Part thermique : **{st.session_state.scenario['part_thermique']}%**")

with st.expander("🔧 **LEVIER 5 : Allègement** - Réduire le poids des véhicules", expanded=True):
    st.markdown("**Objectif :** Véhicules plus légers, moins consommateurs")
    st.caption("Impact : -10% poids = -7% consommation (thermique uniquement)")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"Réduction poids : **-{st.session_state.scenario['reduction_poids']}%**")
    with col2:
        if st.button("➖", key="poids_moins"):
            st.session_state.scenario['reduction_poids'] = max(0, st.session_state.scenario['reduction_poids'] - 5)
            st.rerun()
    with col3:
        if st.button("➕", key="poids_plus"):
            st.session_state.scenario['reduction_poids'] = min(30, st.session_state.scenario['reduction_poids'] + 5)
            st.rerun()
    
    if st.session_state.scenario['reduction_poids'] > 0:
        reduction_conso = st.session_state.scenario['reduction_poids'] * 0.7
        st.success(f"✅ Réduction consommation thermique : -{reduction_conso:.1f}%")
    else:
        st.info("➡️ Pas d'allègement des véhicules")

st.divider()

# Bouton reset
col_reset1, col_reset2, col_reset3 = st.columns([1, 1, 1])
with col_reset2:
    if st.button("🔄 Réinitialiser tous les leviers", use_container_width=True, type="secondary", key="reset_btn"):
        # Réinitialisation complète
        st.session_state.scenario['reduction_km'] = 0
        st.session_state.scenario['report_velo'] = 0
        st.session_state.scenario['report_bus'] = 0
        st.session_state.scenario['report_train'] = 0
        st.session_state.scenario['report_train_avion'] = 0
        st.session_state.scenario['taux_remplissage'] = st.session_state.taux_occupation_2025
        st.session_state.scenario['part_ve'] = 3
        st.session_state.scenario['part_thermique'] = 97
        st.session_state.scenario['reduction_poids'] = 0
        st.rerun()

# ==================== RÉSULTATS ====================

st.divider()
st.header("📊 Résultats du scénario 2050")

# Calcul
resultats = calculer_2050()

# Métriques principales
col1, col2, col3 = st.columns(3)

with col1:
    delta_co2_annuel = resultats['bilan_2050']['co2_annuel'] - resultats['bilan_2025']['co2_annuel']
    st.metric(
        "🌍 Émissions CO₂ 2050",
        f"{resultats['bilan_2050']['co2_annuel']:.0f} kg/an",
        delta=f"{delta_co2_annuel:.0f} kg/an",
        delta_color="inverse"
    )

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

# Détails des calculs (pour vérification)
with st.expander("🔍 Détails des calculs (vérification)"):
    st.markdown(f"""
    **Calculs effectués :**
    
    **1. Sobriété :**
    - Km totaux 2025 : {sum(st.session_state.km_2025.values()):.0f} km/sem
    - Variation : {st.session_state.scenario['reduction_km']:+}%
    - Km totaux 2050 : {resultats['bilan_2050']['km_total']:.0f} km/sem
    
    **2. Report modal (calculé sur base 2025) :**
    - Voiture 2025 : {st.session_state.km_2025['voiture']} km
    - Report vers vélo : {st.session_state.scenario['report_velo']}% = {st.session_state.km_2025['voiture'] * st.session_state.scenario['report_velo'] / 100:.1f} km transférés
    - Report vers bus : {st.session_state.scenario['report_bus']}% = {st.session_state.km_2025['voiture'] * st.session_state.scenario['report_bus'] / 100:.1f} km transférés
    - Report vers train : {st.session_state.scenario['report_train']}% = {st.session_state.km_2025['voiture'] * st.session_state.scenario['report_train'] / 100:.1f} km transférés
    - Avion 2025 : {st.session_state.km_2025['avion']} km
    - Report avion→train : {st.session_state.scenario['report_train_avion']}% = {st.session_state.km_2025['avion'] * st.session_state.scenario['report_train_avion'] / 100:.1f} km transférés
    
    **3. Émissions voiture 2050 :**
    - Mix énergétique : {st.session_state.scenario['part_thermique']}% thermique + {st.session_state.scenario['part_ve']}% électrique
    - Allègement : -{st.session_state.scenario['reduction_poids']}% de poids
    - Facteur allègement thermique : {1 - st.session_state.scenario['reduction_poids'] * 0.7 / 100:.3f}
    - Émission thermique ajustée : {st.session_state.emissions['voiture_thermique'] * (1 - st.session_state.scenario['reduction_poids'] * 0.7 / 100):.1f} gCO₂/km
    - Émission moyenne voiture : {(st.session_state.scenario['part_thermique']/100 * st.session_state.emissions['voiture_thermique'] * (1 - st.session_state.scenario['reduction_poids'] * 0.7 / 100) + st.session_state.scenario['part_ve']/100 * st.session_state.emissions['voiture_electrique']):.1f} gCO₂/km
    - Taux occupation : {st.session_state.scenario['taux_remplissage']:.1f} pers/véh
    - Émission par personne : {(st.session_state.scenario['part_thermique']/100 * st.session_state.emissions['voiture_thermique'] * (1 - st.session_state.scenario['reduction_poids'] * 0.7 / 100) + st.session_state.scenario['part_ve']/100 * st.session_state.emissions['voiture_electrique']) / st.session_state.scenario['taux_remplissage']:.1f} gCO₂/km
    
    **4. CO₂ total :**
    - 2025 : {resultats['bilan_2025']['co2_annuel']:.0f} kg/an
    - 2050 : {resultats['bilan_2050']['co2_annuel']:.0f} kg/an
    - Réduction : {resultats['reduction_pct']:.1f}%
    """)

# ==================== QUESTIONS PÉDAGOGIQUES ====================

st.divider()
st.header("💡 Questions pour le débat")

with st.expander("❓ Question 1 : Votre scénario atteint-il l'objectif ?", expanded=not resultats['objectif_atteint']):
    if resultats['objectif_atteint']:
        st.success(f"✅ **Bravo ! Objectif atteint : -{resultats['reduction_pct']:.1f}%**")
        st.markdown("""
        **À approfondir :**
        - Quels leviers ont été les plus efficaces ?
        - Votre scénario est-il réaliste pour le Pays Basque ?
        - Quels défis de mise en œuvre ?
        """)
    else:
        st.error(f"❌ **Objectif non atteint : -{resultats['reduction_pct']:.1f}%**")
        st.write(f"Il manque **{80 - resultats['reduction_pct']:.1f} points** pour -80%.")
        st.markdown("""
        **Pistes :**
        - Quels leviers actionner davantage ?
        - L'électrification seule suffit-elle ?
        - Faut-il réduire les km parcourus ?
        """)

with st.expander("❓ Question 2 : Rôle de chaque levier"):
    st.markdown(f"""
    **Votre scénario :**
    - Sobriété : {st.session_state.scenario['reduction_km']:+}%
    - Report modal voiture : {st.session_state.scenario['report_velo'] + st.session_state.scenario['report_bus'] + st.session_state.scenario['report_train']}%
    - Report modal avion : {st.session_state.scenario['report_train_avion']}%
    - Taux remplissage : {st.session_state.scenario['taux_remplissage']:.1f} pers/véh
    - Électrification : {st.session_state.scenario['part_ve']}%
    - Allègement : -{st.session_state.scenario['reduction_poids']}%
    
    **À débattre :**
    - Quel levier a le plus d'impact ? Testez en activant un seul à la fois
    - Y a-t-il des leviers "sans regret" (faciles + efficaces) ?
    - Lesquels sont les plus difficiles socialement ?
    """)

with st.expander("❓ Question 3 : L'électrification est-elle suffisante ?"):
    st.write(f"**Votre scénario : {st.session_state.scenario['part_ve']}% de VE**")
    st.markdown("""
    **À débattre :**
    - Testez 100% VE sans autres leviers : atteint-on -80% ?
    - Production électrique au Pays Basque ?
    - Infrastructures de recharge ?
    - Ressources (lithium, cobalt) ?
    - Coût : 30-40% plus cher qu'un thermique
    """)

with st.expander("❓ Question 4 : Report modal réaliste ?"):
    st.markdown("""
    **À débattre :**
    - Infrastructures nécessaires (pistes cyclables, TC denses) ?
    - Relief du Pays Basque (Pyrénées) : contrainte ?
    - Habitat dispersé en zone rurale : comment faire ?
    - TXIK TXAK : suffisant ? Extensions nécessaires ?
    - Train transfrontalier (EuskoTren) ?
    """)

with st.expander("❓ Question 5 : Avion vs Train ?"):
    st.write(f"**Report avion→train : {st.session_state.scenario['report_train_avion']}%**")
    st.markdown("""
    **Constats :**
    - Avion : 258 gCO₂/km vs Train : 5.1 gCO₂/km (ACV)
    - Aéroport Biarritz : 1,2M passagers/an
    - Forte saisonnalité touristique
    
    **À débattre :**
    - Limiter vols courts (< 2h30 de train alternatif) ?
    - Train de nuit Paris-Hendaye ?
    - Taxation kérosène (exonéré actuellement) ?
    - Impact économique sur tourisme ?
    """)

with st.expander("❓ Question 6 : Covoiturage et allègement ?"):
    st.write(f"""**Taux remplissage : {st.session_state.scenario['taux_remplissage']:.1f} pers/véh**  
**Allègement : -{st.session_state.scenario['reduction_poids']}%**""")
    st.markdown("""
    **Covoiturage :**
    - 1.3 → 2.0 = division émissions par 1.5 !
    - Comment favoriser : voies réservées, parkings, applis ?
    - Limites : flexibilité, trajets compatibles
    
    **Allègement :**
    - Tendance inverse : SUV toujours plus lourds
    - VE plus lourds (batteries 300-500 kg)
    - Solutions : citadines, véhicules intermédiaires
    - Règlementation : bonus/malus au poids ?
    
    💡 Leviers souvent oubliés mais très efficaces !
    """)

# ==================== SYNTHÈSE ====================

st.divider()
st.header("📚 Synthèse : Points clés")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### ✅ Enseignements
    
    **1. Approche systémique**
    - Combiner TOUS les leviers
    - Pas de solution unique
    
    **2. Hiérarchie d'efficacité**
    - **Sobriété** : le plus puissant
    - **Covoiturage** : impact fort, peu coûteux
    - **Report modal** : infrastructures lourdes
    - **Électrification** : importante mais insuffisante
    - **Allègement** : souvent oublié
    
    **3. Contexte territorial**
    - Pays Basque ≠ Paris
    - Solutions adaptées au relief, densité
    """)

with col2:
    st.markdown("""
    ### ⚠️ Défis
    
    **1. Acceptabilité sociale**
    - Changements comportementaux
    - Justice sociale nécessaire
    
    **2. Temporalité**
    - 2050 = 25 ans seulement
    - Agir MAINTENANT
    
    **3. Financement**
    - Infrastructures coûteuses (milliards €)
    - Qui paie ?
    
    **4. Gouvernance**
    - Multiples acteurs à coordonner
    """)

st.info("""
**🎯 Message clé :**  
Atteindre -80% est **techniquement possible** mais **socialement exigeant**.  
La question : "comment faire pour que ce soit acceptable et juste ?".
""")

# ==================== RESSOURCES ====================

st.divider()
st.header("📖 Ressources bibliographiques")

st.markdown("""
### 📊 Sources de données (faciles à lire)

**Facteurs d'émission :**
- [Base Carbone ADEME](https://base-empreinte.ademe.fr/) - Base officielle
- [Documentation Base Carbone](https://bilans-ges.ademe.fr/documentation/UPLOAD_DOC_FR/index.htm?transport_de_personnes.htm) - Guide méthodologique
- [impactCO2.fr](https://impactco2.fr/outils/transport) - Comparateur simplifié

**Scénarios prospectifs :**
- [ADEME Transitions 2050](https://transitions2050.ademe.fr/) - 4 scénarios nationaux
- [SNBC](https://www.ecologie.gouv.fr/strategie-nationale-bas-carbone-snbc) - Stratégie officielle (voir page 78)
- [The Shift Project - Mobilité](https://theshiftproject.org/article/decarboner-la-mobilite-dans-les-zones-de-moyenne-densite/)

**Spécificités territoriales :**
- [Communauté Pays Basque - Plan Climat](https://www.communaute-paysbasque.fr/) 
- [TXIK TXAK](https://www.txiktxak.eus/) - Réseau de transport
- [Observatoire des mobilités Nouvelle-Aquitaine](https://www.obs-mobilites.com/)
""")

# ==================== EXPORT ====================

st.divider()
st.subheader("💾 Exporter votre scénario")

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

Émissions 2025 : {bilan_2025['co2_annuel']:.0f} kg CO₂e/an

───────────────────────────────────────────────────
🎯 SCÉNARIO 2050 - LEVIERS ACTIONNÉS
───────────────────────────────────────────────────

1. Sobriété : {st.session_state.scenario['reduction_km']:+}% km
2. Report modal :
   • Voiture → Vélo : {st.session_state.scenario['report_velo']}%
   • Voiture → Bus : {st.session_state.scenario['report_bus']}%
   • Voiture → Train : {st.session_state.scenario['report_train']}%
   • Avion → Train : {st.session_state.scenario['report_train_avion']}%
3. Taux remplissage : {st.session_state.scenario['taux_remplissage']:.1f} pers/véh
4. Électrification : {st.session_state.scenario['part_ve']}% VE
5. Allègement : -{st.session_state.scenario['reduction_poids']}% poids

───────────────────────────────────────────────────
📈 RÉSULTATS 2050
───────────────────────────────────────────────────

Émissions 2050 : {resultats['bilan_2050']['co2_annuel']:.0f} kg CO₂e/an
Réduction : {resultats['reduction_pct']:.1f}%
Objectif SNBC (-80%) : {"✅ ATTEINT" if resultats['objectif_atteint'] else "❌ NON ATTEINT"}

═══════════════════════════════════════════════════
Sources : Base Carbone ADEME (ACV), SNBC 2050
Application pédagogique - Pays Basque 2025-2050
═══════════════════════════════════════════════════
"""

st.download_button(
    label="📥 Télécharger le résumé (TXT)",
    data=resume_scenario,
    file_name=f"scenario_mobilite_PB_{resultats['reduction_pct']:.0f}pct.txt",
    mime="text/plain",
    use_container_width=True
)

# ==================== FOOTER ====================

st.divider()
st.markdown("""
<div style='text-align: center; color: #6b7280; font-size: 0.875rem; padding: 1rem;'>
    <p><strong>📚 Sources :</strong> 
        <a href='https://base-empreinte.ademe.fr/' target='_blank'>Base Carbone ADEME</a> (ACV) • 
        <a href='https://www.ecologie.gouv.fr/strategie-nationale-bas-carbone-snbc' target='_blank'>SNBC 2050</a> • 
        <a href='https://transitions2050.ademe.fr/' target='_blank'>ADEME Transitions 2050</a>
    </p>
    <p style='margin-top: 1rem;'>
        <strong>🎓 Application pédagogique</strong> • Communauté Pays Basque • 2025-2050<br>
        Réseau de transport : <strong>TXIK TXAK</strong>
    </p>
</div>
""", unsafe_allow_html=True)
