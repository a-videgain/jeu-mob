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
    
    # Nombre de déplacements par JOUR
    st.session_state.nb_depl = {
        'voiture': 1.1,  # ~8/7
        'bus': 0.6,      # ~4/7
        'train': 0.15,   # ~1/7
        'velo': 0.7,     # ~5/7
        'avion': 0.014,  # ~5 vols par an / 365 jours
        'marche': 1.4    # ~10/7
    }
    
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
        'report_train_avion': 0,  # NOUVEAU : report avion vers train
        'part_ve': 3,
        'part_thermique': 97,
        'taux_remplissage': 1.3,   # NOUVEAU : taux occupation voiture
        'reduction_poids': 0        # NOUVEAU : allègement véhicules
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
            # Effet allègement sur thermique : -10% poids = -7% consommation (ratio classique)
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
    
    # 2. Parts modales 2025 (%)
    parts_2025 = calculer_parts_modales(st.session_state.km_2025)
    
    # 3. Report modal voiture
    report_total_voiture = (st.session_state.scenario['report_velo'] + 
                            st.session_state.scenario['report_bus'] + 
                            st.session_state.scenario['report_train'])
    
    # 4. Report modal avion → train
    report_avion_train = st.session_state.scenario['report_train_avion']
    
    # 5. Nouvelles parts modales 2050
    parts_2050 = parts_2025.copy()
    parts_2050['voiture'] = max(0, parts_2025['voiture'] - report_total_voiture)
    parts_2050['bus'] = parts_2025['bus'] + st.session_state.scenario['report_bus']
    parts_2050['train'] = parts_2025['train'] + st.session_state.scenario['report_train'] + report_avion_train
    parts_2050['velo'] = parts_2025['velo'] + st.session_state.scenario['report_velo']
    parts_2050['avion'] = max(0, parts_2025['avion'] - report_avion_train)
    # Marche reste inchangée
    
    # 6. Km absolus 2050
    km_2050 = {mode: km_total_2050 * part / 100 for mode, part in parts_2050.items()}
    
    # 7. Calcul bilans
    bilan_2025 = calculer_bilan(
        st.session_state.km_2025, 
        st.session_state.emissions, 
        part_ve=3,
        taux_remplissage=1.3,
        reduction_poids=0
    )
    
    bilan_2050 = calculer_bilan(
        km_2050, 
        st.session_state.emissions, 
        part_ve=st.session_state.scenario['part_ve'],
        taux_remplissage=st.session_state.scenario['taux_remplissage'],
        reduction_poids=st.session_state.scenario['reduction_poids']
    )
    
    # 8. Calcul réduction
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
    st.subheader("🔢 Nombre déplacements/jour")
    
    st.session_state.nb_depl['voiture'] = st.number_input(
        "🚗 Voiture",
        min_value=0.0, max_value=10.0, value=st.session_state.nb_depl['voiture'],
        step=0.1, key="nb_voiture", format="%.1f"
    )
    
    st.session_state.nb_depl['bus'] = st.number_input(
        "🚌 Bus",
        min_value=0.0, max_value=5.0, value=st.session_state.nb_depl['bus'],
        step=0.1, key="nb_bus", format="%.1f"
    )
    
    st.session_state.nb_depl['train'] = st.number_input(
        "🚆 Train",
        min_value=0.0, max_value=3.0, value=st.session_state.nb_depl['train'],
        step=0.05, key="nb_train", format="%.2f"
    )
    
    st.session_state.nb_depl['velo'] = st.number_input(
        "🚴 Vélo",
        min_value=0.0, max_value=5.0, value=st.session_state.nb_depl['velo'],
        step=0.1, key="nb_velo", format="%.1f"
    )
    
    st.session_state.nb_depl['avion'] = st.number_input(
        "✈️ Avion",
        min_value=0.0, max_value=0.5, value=st.session_state.nb_depl['avion'],
        step=0.001, key="nb_avion", format="%.3f",
        help="Moyenne par jour (ex: 5 vols/an = 0.014/jour)"
    )
    
    st.session_state.nb_depl['marche'] = st.number_input(
        "🚶 Marche",
        min_value=0.0, max_value=10.0, value=st.session_state.nb_depl['marche'],
        step=0.1, key="nb_marche", format="%.1f"
    )

with col3:
    st.subheader("⚠️ Facteurs émission ACV (gCO₂/km)")
    st.caption("ACV = Analyse Cycle de Vie (fabrication + usage)")
    st.caption("Sources : [Base Carbone ADEME](https://base-empreinte.ademe.fr/)")
    
    st.session_state.emissions['voiture_thermique'] = st.number_input(
        "🚗 Voiture thermique",
        min_value=0, max_value=500, value=st.session_state.emissions['voiture_thermique'],
        step=10, key="em_voiture_therm",
        help="ADEME Base Carbone : 218 gCO2e/km (ACV)"
    )
    
    st.session_state.emissions['voiture_electrique'] = st.number_input(
        "🔌 Voiture électrique",
        min_value=0, max_value=200, value=st.session_state.emissions['voiture_electrique'],
        step=5, key="em_voiture_elec",
        help="ADEME Base Carbone : 103 gCO2e/km (ACV avec batterie)"
    )
    
    st.session_state.emissions['bus'] = st.number_input(
        "🚌 Bus",
        min_value=0, max_value=300, value=st.session_state.emissions['bus'],
        step=10, key="em_bus",
        help="ADEME Base Carbone : 127 gCO2e/km (ACV)"
    )
    
    st.session_state.emissions['train'] = st.number_input(
        "🚆 Train",
        min_value=0.0, max_value=50.0, value=st.session_state.emissions['train'],
        step=0.5, key="em_train",
        help="ADEME Base Carbone : 5.1 gCO2e/km (ACV)"
    )
    
    st.session_state.emissions['avion'] = st.number_input(
        "✈️ Avion",
        min_value=0, max_value=500, value=st.session_state.emissions['avion'],
        step=10, key="em_avion",
        help="ADEME Base Carbone : 258 gCO2e/km (ACV courrier moyen)"
    )
    
    st.session_state.emissions['velo'] = st.number_input(
        "🚴 Vélo",
        min_value=0, max_value=20, value=st.session_state.emissions['velo'],
        step=1, key="em_velo",
        help="ADEME Base Carbone : 5 gCO2e/km (fabrication)"
    )
    
    st.info("💡 Marche : 0 gCO₂/km")

# Calcul bilan 2025
bilan_2025 = calculer_bilan(
    st.session_state.km_2025, 
    st.session_state.emissions, 
    part_ve=3,
    taux_remplissage=1.3,
    reduction_poids=0
)
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
    st.metric("🔢 Déplacements/jour", f"{nb_depl_total:.1f}")

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

st.warning("**🎯 Objectif SNBC : Réduire de 80% les émissions CO₂ entre 2025 et 2050**")

# Leviers en accordéons
with st.expander("🔧 **LEVIER 1 : Sobriété** - Réduire les km parcourus", expanded=True):
    st.markdown("**Objectif :** Diminuer le besoin de déplacement")
    
    st.session_state.scenario['reduction_km'] = st.slider(
        "Variation des km totaux par rapport à 2025 (%)",
        min_value=-50, max_value=10, value=st.session_state.scenario['reduction_km'],
        step=5, key="lever_reduction",
        help="Valeurs négatives = réduction des km"
    )
    
    km_total_2025 = sum(st.session_state.km_2025.values())
    km_total_2050_prevision = km_total_2025 * (1 + st.session_state.scenario['reduction_km'] / 100)
    
    if st.session_state.scenario['reduction_km'] < 0:
        st.success(f"✅ Réduction de {abs(st.session_state.scenario['reduction_km'])}% : {km_total_2025:.0f} km/sem → {km_total_2050_prevision:.0f} km/sem")
    elif st.session_state.scenario['reduction_km'] > 0:
        st.warning(f"⚠️ Augmentation de {st.session_state.scenario['reduction_km']}% : {km_total_2025:.0f} km/sem → {km_total_2050_prevision:.0f} km/sem")
    else:
        st.info(f"➡️ Stabilité : {km_total_2025:.0f} km/sem")

with st.expander("🔧 **LEVIER 2 : Report modal** - Transférer vers des modes moins émetteurs", expanded=True):
    st.markdown("**Objectif :** Faire passer les usagers vers des modes décarbonés")
    
    st.markdown("##### 🚗 Report depuis la voiture")
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.scenario['report_velo'] = st.slider(
            "🚴 Voiture → Vélo (%)",
            min_value=0, max_value=35, value=st.session_state.scenario['report_velo'],
            step=5, key="lever_velo"
        )
        
        st.session_state.scenario['report_bus'] = st.slider(
            "🚌 Voiture → Bus/TC (%)",
            min_value=0, max_value=30, value=st.session_state.scenario['report_bus'],
            step=5, key="lever_bus"
        )
    
    with col2:
        st.session_state.scenario['report_train'] = st.slider(
            "🚆 Voiture → Train (%)",
            min_value=0, max_value=25, value=st.session_state.scenario['report_train'],
            step=5, key="lever_train"
        )
        
        report_total_voiture = (st.session_state.scenario['report_velo'] + 
                                st.session_state.scenario['report_bus'] + 
                                st.session_state.scenario['report_train'])
        
        part_voiture_2025 = parts_2025['voiture']
        part_voiture_2050_prevision = max(0, part_voiture_2025 - report_total_voiture)
        
        st.metric("Report total voiture", f"{report_total_voiture}%")
        st.info(f"Part voiture : {part_voiture_2025:.1f}% → {part_voiture_2050_prevision:.1f}%")
    
    st.divider()
    st.markdown("##### ✈️ Report depuis l'avion")
    
    st.session_state.scenario['report_train_avion'] = st.slider(
        "🚆 Avion → Train (%)",
        min_value=0, max_value=50, value=st.session_state.scenario['report_train_avion'],
        step=5, key="lever_train_avion",
        help="% de la part modale avion transférée vers le train"
    )
    
    part_avion_2025 = parts_2025['avion']
    part_avion_2050_prevision = max(0, part_avion_2025 - st.session_state.scenario['report_train_avion'])
    st.info(f"Part avion : {part_avion_2025:.1f}% → {part_avion_2050_prevision:.1f}%")

with st.expander("🔧 **LEVIER 3 : Électrification** - Décarboner le parc automobile", expanded=True):
    st.markdown("**Objectif :** Remplacer les véhicules thermiques par des véhicules électriques")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.scenario['part_ve'] = st.slider(
            "Part de véhicules électriques (%)",
            min_value=0, max_value=100, value=st.session_state.scenario['part_ve'],
            step=5, key="lever_ve"
        )
        
        st.session_state.scenario['part_thermique'] = 100 - st.session_state.scenario['part_ve']
        st.info(f"Part thermique : {st.session_state.scenario['part_thermique']}%")
    
    with col2:
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

with st.expander("🔧 **LEVIER 4 : Optimisation** - Augmenter le taux de remplissage", expanded=True):
    st.markdown("**Objectif :** Augmenter le nombre de personnes par véhicule")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.scenario['taux_remplissage'] = st.slider(
            "Taux de remplissage moyen (pers/véhicule)",
            min_value=1.0, max_value=3.0, value=st.session_state.scenario['taux_remplissage'],
            step=0.1, key="lever_remplissage",
            format="%.1f"
        )
        
        taux_2025 = 1.3
        gain_remplissage = ((st.session_state.scenario['taux_remplissage'] - taux_2025) / taux_2025) * 100
        
        if gain_remplissage > 0:
            st.success(f"✅ +{gain_remplissage:.1f}% de personnes par voiture")
        else:
            st.info("➡️ Pas d'amélioration du taux de remplissage")
    
    with col2:
        # Impact sur émissions par personne
        emission_par_pers_2025 = emission_moy_2025 / taux_2025
        emission_par_pers_2050 = emission_moy_2050 / st.session_state.scenario['taux_remplissage']
        
        st.metric(
            "Émission par personne",
            f"{emission_par_pers_2050:.0f} gCO₂/km",
            delta=f"{emission_par_pers_2050 - emission_par_pers_2025:.0f} gCO₂/km",
            delta_color="inverse",
            help="Prend en compte électrification + taux remplissage"
        )

with st.expander("🔧 **LEVIER 5 : Allègement** - Réduire le poids des véhicules", expanded=True):
    st.markdown("**Objectif :** Véhicules plus légers, moins consommateurs")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.scenario['reduction_poids'] = st.slider(
            "Réduction moyenne du poids des véhicules (%)",
            min_value=0, max_value=30, value=st.session_state.scenario['reduction_poids'],
            step=5, key="lever_poids",
            help="Impact : -10% poids = -7% consommation (thermique uniquement)"
        )
        
        if st.session_state.scenario['reduction_poids'] > 0:
            reduction_conso = st.session_state.scenario['reduction_poids'] * 0.7
            st.success(f"✅ Réduction consommation thermique : -{reduction_conso:.1f}%")
        else:
            st.info("➡️ Pas d'allègement des véhicules")
    
    with col2:
        # Impact sur émission thermique
        facteur_allègement = 1 - (st.session_state.scenario['reduction_poids'] * 0.7 / 100)
        emission_thermique_allegee = st.session_state.emissions['voiture_thermique'] * facteur_allègement
        
        st.metric(
            "Émission voiture thermique",
            f"{emission_thermique_allegee:.0f} gCO₂/km",
            delta=f"{emission_thermique_allegee - st.session_state.emissions['voiture_thermique']:.0f} gCO₂/km",
            delta_color="inverse",
            help="Allègement n'impacte que les véhicules thermiques"
        )

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
            'report_train_avion': 0,
            'part_ve': 3,
            'part_thermique': 97,
            'taux_remplissage': 1.3,
            'reduction_poids': 0
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

# ==================== QUESTIONS PÉDAGOGIQUES ====================

st.divider()
st.header("💡 Questions pour le débat")

with st.expander("❓ Question 1 : Votre scénario atteint-il l'objectif ?", expanded=not resultats['objectif_atteint']):
    if resultats['objectif_atteint']:
        st.success(f"✅ **Bravo ! Votre scénario atteint l'objectif de -80%**")
        st.write(f"Vous avez réduit les émissions de **{resultats['reduction_pct']:.1f}%** entre 2025 et 2050.")
        st.markdown("""
        **À approfondir :**
        - Quels leviers ont été les plus efficaces ?
        - Votre scénario est-il réaliste pour le Pays Basque ?
        - Quels seraient les principaux défis ?
        """)
    else:
        st.error(f"❌ **Objectif non atteint**")
        st.write(f"Réduction actuelle : **{resultats['reduction_pct']:.1f}%** (objectif : -80%)")
        st.write(f"Il manque **{80 - resultats['reduction_pct']:.1f} points** pour atteindre l'objectif.")
        st.markdown("""
        **Pistes :**
        - Quels leviers actionner davantage ?
        - L'électrification seule suffit-elle ?
        - Faut-il réduire les km parcourus ?
        """)

with st.expander("❓ Question 2 : L'électrification est-elle suffisante ?"):
    st.write(f"**Votre scénario : {st.session_state.scenario['part_ve']}% de véhicules électriques**")
    st.markdown("""
    **À débattre :**
    - Production électrique suffisante au Pays Basque ?
    - Infrastructures de recharge nécessaires ?
    - Ressources (lithium, cobalt) : impacts ?
    - Coût : accessible à tous ?
    - Recyclage des batteries ?
    
    💡 Testez : mettez 100% VE, que se passe-t-il ?
    """)

with st.expander("❓ Question 3 : Le report modal est-il réaliste ?"):
    report_total = (st.session_state.scenario['report_velo'] + 
                    st.session_state.scenario['report_bus'] + 
                    st.session_state.scenario['report_train'])
    st.write(f"**Report voiture : {report_total}% | Report avion : {st.session_state.scenario['report_train_avion']}%**")
    st.markdown("""
    **À débattre :**
    - Infrastructures nécessaires ?
    - Contexte Pays Basque (relief, habitat dispersé) ?
    - Acceptabilité sociale ?
    - Réseau TXIK TXAK suffisant ?
    - Train transfrontalier (EuskoTren) ?
    """)

with st.expander("❓ Question 4 : La sobriété est-elle incontournable ?"):
    st.write(f"**Variation km : {st.session_state.scenario['reduction_km']:+}%**")
    st.markdown("""
    **À débattre :**
    - Peut-on atteindre -80% sans sobriété ?
    - Comment réduire les km : télétravail, relocalisations ?
    - Freins : étalement urbain, liberté de mouvement ?
    - Justice sociale : qui peut télétravailler ?
    
    💡 Testez : mettez réduction_km à 0%, jouez sur les autres leviers
    """)

with st.expander("❓ Question 5 : Avion vs Train ?"):
    st.write(f"**Report avion → train : {st.session_state.scenario['report_train_avion']}%**")
    st.markdown("""
    **Constats :**
    - Avion : {0:.1f}% des km mais forte contribution CO₂
    - 258 gCO₂/km (ACV) vs 5.1 pour le train
    - Aéroport Biarritz : 1,2M passagers/an
    
    **À débattre :**
    - Limiter vols courts (< 2h30 de train) ?
    - Développer train de nuit ?
    - Taxation kérosène (actuellement exonéré) ?
    - Impact sur tourisme/économie locale ?
    """.format(parts_2025['avion']))

with st.expander("❓ Question 6 : Covoiturage et véhicules légers ?"):
    st.write(f"""**Taux remplissage : {st.session_state.scenario['taux_remplissage']:.1f} pers/véh**  
**Allègement : -{st.session_state.scenario['reduction_poids']}% de poids**""")
    st.markdown("""
    **À débattre :**
    
    **Covoiturage :**
    - 1.3 → 2.0 = Division émissions par 1.5 !
    - Comment favoriser : voies réservées, parkings, applis ?
    - Limites : flexibilité, trajets compatibles ?
    
    **Allègement :**
    - Tendance inverse : SUV de plus en plus lourds
    - VE plus lourds (batteries) que thermiques
    - Solutions : petites citadines, véhicules intermédiaires ?
    - Règlementation : bonus/malus au poids ?
    
    💡 Ces leviers sont souvent oubliés mais très efficaces !
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
    - Sobriété : le plus puissant
    - Report modal : infrastructures lourdes
    - Électrification : importante mais insuffisante
    - Covoiturage : impact fort, facile
    - Allègement : souvent oublié
    
    **3. Contexte territorial**
    - Pays Basque ≠ Paris
    - Solutions différenciées
    """)

with col2:
    st.markdown("""
    ### ⚠️ Défis
    
    **1. Acceptabilité sociale**
    - Changements comportementaux
    - Justice sociale nécessaire
    
    **2. Temporalité**
    - 2050 = 25 ans
    - Agir MAINTENANT
    
    **3. Financement**
    - Infrastructures coûteuses
    - Qui paie ?
    
    **4. Gouvernance**
    - Multiples acteurs
    - Coordination essentielle
    """)

st.info("""
**🎯 Message clé :**  
Atteindre -80% est **techniquement possible** mais **socialement exigeant**.  
La question n'est pas "est-ce possible ?" mais "comment faire pour que ce soit acceptable et juste ?".
""")

# ==================== RESSOURCES ====================

st.divider()
st.header("📖 Ressources bibliographiques")

st.markdown("""
### 📊 Sources de données (faciles à lire)

**Facteurs d'émission :**
- [Base Carbone ADEME](https://base-empreinte.ademe.fr/) - Base de données officielle
- [Documentation Base Carbone](https://bilans-ges.ademe.fr/documentation/UPLOAD_DOC_FR/index.htm?transport_de_personnes.htm) - Guide méthodologique
- [impactCO2.fr](https://impactco2.fr/outils/transport) - Comparateur simplifié

**Scénarios prospectifs :**
- [ADEME Transitions 2050](https://transitions2050.ademe.fr/) - 4 scénarios nationaux
- [SNBC](https://www.ecologie.gouv.fr/strategie-nationale-bas-carbone-snbc) - Stratégie officielle
- [The Shift Project - Mobilité](https://theshiftproject.org/article/decarboner-la-mobilite-dans-les-zones-de-moyenne-densite/) - Analyse zones moyennes densités

**Spécificités territoriales :**
- [Communauté Pays Basque - Plan Climat](https://www.communaute-paysbasque.fr/) 
- [TXIK TXAK](https://www.txiktxak.eus/) - Réseau de transport en commun
- [Observatoire des mobilités Nouvelle-Aquitaine](https://www.obs-mobilites.com/)

### 📚 Pour approfondir

**Ouvrages accessibles :**
- "Le futur de la mobilité" - Aurélien Bigo (2024)
- "Ralentir ou périr" - Timothée Parrique (2022)
- "Comment éviter un avenir climatique catastrophique" - Bill Gates (2021)

**Articles de référence :**
- Bigo A. (2020) "Les transports face au défi de la transition énergétique"
- Jancovici JM & Grandjean A. (2006) "Le plein s'il vous plaît !"

**Podcasts :**
- Greenletter Club (épisodes mobilité)
- Le Réveilleur (transport)
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

Émissions 2025 :
  • Hebdomadaire : {bilan_2025['co2_hebdo']:.2f} kg CO₂e
  • Annuelle : {bilan_2025['co2_annuel']:.0f} kg CO₂e

───────────────────────────────────────────────────
🎯 SCÉNARIO 2050 - LEVIERS ACTIONNÉS
───────────────────────────────────────────────────

1. Sobriété :
   • Variation km : {st.session_state.scenario['reduction_km']:+}%

2. Report modal :
   • Voiture → Vélo : {st.session_state.scenario['report_velo']}%
   • Voiture → Bus : {st.session_state.scenario['report_bus']}%
   • Voiture → Train : {st.session_state.scenario['report_train']}%
   • Avion → Train : {st.session_state.scenario['report_train_avion']}%

3. Électrification :
   • Véhicules électriques : {st.session_state.scenario['part_ve']}%
   • Véhicules thermiques : {st.session_state.scenario['part_thermique']}%

4. Optimisation :
   • Taux remplissage : {st.session_state.scenario['taux_remplissage']:.1f} pers/véh

5. Allègement :
   • Réduction poids : -{st.session_state.scenario['reduction_poids']}%

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
  • Hebdomadaire : {resultats['bilan_2050']['co2_hebdo']:.2f} kg CO₂e
  • Annuelle : {resultats['bilan_2050']['co2_annuel']:.0f} kg CO₂e

───────────────────────────────────────────────────
🎯 BILAN
───────────────────────────────────────────────────

Réduction des émissions : {resultats['reduction_pct']:.1f}%
Objectif SNBC (-80%) : {"✅ ATTEINT" if resultats['objectif_atteint'] else "❌ NON ATTEINT"}

{f"Écart restant : {80 - resultats['reduction_pct']:.1f} points" if not resultats['objectif_atteint'] else ""}

═══════════════════════════════════════════════════
Sources : Base Carbone ADEME (ACV), SNBC 2050
Application pédagogique - Pays Basque 2025-2050
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
    <p><strong>📚 Sources :</strong></p>
    <p>
        <a href='https://base-empreinte.ademe.fr/' target='_blank'>Base Carbone ADEME</a> (ACV) • 
        <a href='https://www.ecologie.gouv.fr/strategie-nationale-bas-carbone-snbc' target='_blank'>SNBC 2050</a> • 
        <a href='https://transitions2050.ademe.fr/' target='_blank'>ADEME Transitions 2050</a>
    </p>
    <p style='margin-top: 1rem;'>
        <strong>🎓 Application pédagogique</strong> • Communauté Pays Basque • 2025-2050<br>
        Réseau de transport : <strong>TXIK TXAK</strong> (anciens Chronoplus et Hegobus)
    </p>
</div>
""", unsafe_allow_html=True)
