import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Configuration
st.set_page_config(
    page_title="Transitions Mobilité Pays Basque 2050",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personnalisé pour améliorer l'UI
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    .stAlert {
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== DONNÉES ADEME ====================
# Source : https://impactco2.fr/outils/transport (2024)
EMISSIONS_CO2 = {
    'voiture_thermique_diesel': 193,  # gCO2/km
    'voiture_thermique_essence': 218,
    'voiture_electrique': 20,
    'voiture_hybride': 110,
    'bus': 103,
    'train': 2.4,
    'velo_elec': 2.5,
    'velo': 0,
    'marche': 0
}

ENERGIE_CONSOMMEE = {
    'voiture_thermique_diesel': 0.65,  # kWh/km (équivalent énergétique)
    'voiture_thermique_essence': 0.75,
    'voiture_electrique': 0.17,
    'voiture_hybride': 0.45,
    'bus': 0.40,
    'train': 0.05,
    'velo_elec': 0.01,
    'velo': 0,
    'marche': 0
}

PARTICULES_FINES = {
    'voiture_thermique_diesel': 0.08,  # g particules fines/km
    'voiture_thermique_essence': 0.02,
    'voiture_electrique': 0.005,  # Freinage + usure pneus
    'voiture_hybride': 0.025,
    'bus': 0.12,
    'autres': 0
}

# ==================== INITIALISATION SESSION ====================
if 'step' not in st.session_state:
    st.session_state.step = 1

if 'perso' not in st.session_state:
    st.session_state.perso = {
        'km_voiture': 200,
        'km_tc': 20,
        'km_train': 10,
        'km_velo': 15,
        'km_marche': 5,
        'type_voiture': 'diesel',
        'taux_remplissage': 1.2,
        'temps_stationnement': 95
    }

if 'moyen' not in st.session_state:
    st.session_state.moyen = {
        'km_voiture': 150,
        'km_tc': 25,
        'km_train': 8,
        'km_velo': 20,
        'km_marche': 10,
        'type_voiture': 'diesel',
        'taux_remplissage': 1.3,
        'temps_stationnement': 95
    }

if 'scenario' not in st.session_state:
    st.session_state.scenario = {
        'reduction_km': 0,
        'report_velo': 0,
        'report_tc': 0,
        'report_train': 0,
        'part_ve': 3,
        'part_hybride': 12,
        'part_essence': 20,
        'part_diesel': 65,
        'taux_remplissage': 1.4
    }

# ==================== FONCTIONS DE CALCUL ====================

def calc_bilan(data):
    """Calcule bilan CO2, énergie, particules hebdomadaire et annuel"""
    type_co2 = 'voiture_thermique_' + data['type_voiture']
    
    # CO2 hebdomadaire (kg)
    co2_hebdo = (
        data['km_voiture'] * EMISSIONS_CO2[type_co2] +
        data['km_tc'] * EMISSIONS_CO2['bus'] +
        data['km_train'] * EMISSIONS_CO2['train'] +
        data['km_velo'] * EMISSIONS_CO2['velo']
    ) / 1000  # Conversion g → kg
    
    # Énergie hebdomadaire (kWh)
    energie_hebdo = (
        data['km_voiture'] * ENERGIE_CONSOMMEE[type_co2] +
        data['km_tc'] * ENERGIE_CONSOMMEE['bus'] +
        data['km_train'] * ENERGIE_CONSOMMEE['train'] +
        data['km_velo'] * ENERGIE_CONSOMMEE['velo']
    )
    
    # Particules hebdomadaires (g)
    particules_hebdo = (
        data['km_voiture'] * PARTICULES_FINES[type_co2] +
        data['km_tc'] * PARTICULES_FINES['bus']
    )
    
    return {
        'km_total': sum([data['km_voiture'], data['km_tc'], data['km_train'], 
                        data['km_velo'], data['km_marche']]),
        'co2_hebdo': co2_hebdo,
        'co2_annuel': co2_hebdo * 52,
        'energie_hebdo': energie_hebdo,
        'energie_annuel': energie_hebdo * 52,
        'particules_hebdo': particules_hebdo,
        'particules_annuel': particules_hebdo * 52
    }


def calc_scenario_2050():
    """
    Calcule résultats scénario 2050 - VERSION CORRIGÉE
    Ordre : 1. Réduction globale km, 2. Report modal, 3. Mix énergétique
    """
    s = st.session_state.scenario
    m = st.session_state.moyen
    
    # === ÉTAPE 1 : Vérification cohérence parc automobile ===
    total_parc = s['part_diesel'] + s['part_essence'] + s['part_hybride'] + s['part_ve']
    if total_parc != 100:
        return {
            'erreur': True,
            'message': f"⚠️ Total du parc automobile = {total_parc}% (doit être exactement 100%)",
            'total_parc': total_parc
        }
    
    # === ÉTAPE 2 : Calcul km total 2023 et 2050 (après réduction globale) ===
    km_total_2023 = sum([m['km_voiture'], m['km_tc'], m['km_train'], 
                         m['km_velo'], m['km_marche']])
    km_total_2050 = km_total_2023 * (1 + s['reduction_km'] / 100)
    
    # === ÉTAPE 3 : Parts modales 2023 (en %) ===
    part_voiture_2023 = (m['km_voiture'] / km_total_2023) * 100 if km_total_2023 > 0 else 0
    part_tc_2023 = (m['km_tc'] / km_total_2023) * 100 if km_total_2023 > 0 else 0
    part_train_2023 = (m['km_train'] / km_total_2023) * 100 if km_total_2023 > 0 else 0
    part_velo_2023 = (m['km_velo'] / km_total_2023) * 100 if km_total_2023 > 0 else 0
    part_marche_2023 = (m['km_marche'] / km_total_2023) * 100 if km_total_2023 > 0 else 0
    
    # === ÉTAPE 4 : Report modal (modification des parts en %) ===
    report_total = s['report_velo'] + s['report_tc'] + s['report_train']
    
    part_voiture_2050 = max(0, part_voiture_2023 - report_total)
    part_tc_2050 = part_tc_2023 + s['report_tc']
    part_train_2050 = part_train_2023 + s['report_train']
    part_velo_2050 = part_velo_2023 + s['report_velo']
    part_marche_2050 = part_marche_2023
    
    # === ÉTAPE 5 : Calcul km absolus 2050 ===
    km_voiture_2050 = (km_total_2050 * part_voiture_2050) / 100
    km_tc_2050 = (km_total_2050 * part_tc_2050) / 100
    km_train_2050 = (km_total_2050 * part_train_2050) / 100
    km_velo_2050 = (km_total_2050 * part_velo_2050) / 100
    km_marche_2050 = (km_total_2050 * part_marche_2050) / 100
    
    # === ÉTAPE 6 : Intensité CO2 moyenne du parc voiture 2050 ===
    co2_voiture_2050 = (
        (s['part_diesel'] / 100) * EMISSIONS_CO2['voiture_thermique_diesel'] +
        (s['part_essence'] / 100) * EMISSIONS_CO2['voiture_thermique_essence'] +
        (s['part_hybride'] / 100) * EMISSIONS_CO2['voiture_hybride'] +
        (s['part_ve'] / 100) * EMISSIONS_CO2['voiture_electrique']
    )
    
    # === ÉTAPE 7 : Intensité énergie moyenne du parc voiture 2050 ===
    energie_voiture_2050 = (
        (s['part_diesel'] / 100) * ENERGIE_CONSOMMEE['voiture_thermique_diesel'] +
        (s['part_essence'] / 100) * ENERGIE_CONSOMMEE['voiture_thermique_essence'] +
        (s['part_hybride'] / 100) * ENERGIE_CONSOMMEE['voiture_hybride'] +
        (s['part_ve'] / 100) * ENERGIE_CONSOMMEE['voiture_electrique']
    )
    
    # === ÉTAPE 8 : Intensité particules moyenne du parc voiture 2050 ===
    particules_voiture_2050 = (
        (s['part_diesel'] / 100) * PARTICULES_FINES['voiture_thermique_diesel'] +
        (s['part_essence'] / 100) * PARTICULES_FINES['voiture_thermique_essence'] +
        (s['part_hybride'] / 100) * PARTICULES_FINES['voiture_hybride'] +
        (s['part_ve'] / 100) * PARTICULES_FINES['voiture_electrique']
    )
    
    # === ÉTAPE 9 : Totaux hebdomadaires 2050 ===
    co2_hebdo_2050 = (
        km_voiture_2050 * co2_voiture_2050 +
        km_tc_2050 * EMISSIONS_CO2['bus'] +
        km_train_2050 * EMISSIONS_CO2['train']
    ) / 1000  # kg CO2
    
    energie_hebdo_2050 = (
        km_voiture_2050 * energie_voiture_2050 +
        km_tc_2050 * ENERGIE_CONSOMMEE['bus'] +
        km_train_2050 * ENERGIE_CONSOMMEE['train']
    )
    
    particules_hebdo_2050 = (
        km_voiture_2050 * particules_voiture_2050 +
        km_tc_2050 * PARTICULES_FINES['bus']
    )
    
    # === ÉTAPE 10 : Calcul baseline 2023 pour comparaison ===
    bilan_moyen_2023 = calc_bilan(m)
    
    # === ÉTAPE 11 : Réductions en % ===
    reduction_co2 = ((bilan_moyen_2023['co2_hebdo'] - co2_hebdo_2050) / bilan_moyen_2023['co2_hebdo']) * 100 if bilan_moyen_2023['co2_hebdo'] > 0 else 0
    reduction_energie = ((bilan_moyen_2023['energie_hebdo'] - energie_hebdo_2050) / bilan_moyen_2023['energie_hebdo']) * 100 if bilan_moyen_2023['energie_hebdo'] > 0 else 0
    reduction_particules = ((bilan_moyen_2023['particules_hebdo'] - particules_hebdo_2050) / bilan_moyen_2023['particules_hebdo']) * 100 if bilan_moyen_2023['particules_hebdo'] > 0 else 0
    
    # === ÉTAPE 12 : Analyses qualitatives ===
    objectif_co2_atteint = reduction_co2 >= 80
    
    # Tension énergétique basée sur part VE
    if s['part_ve'] >= 80:
        tension_energetique = 'Très forte'
    elif s['part_ve'] >= 60:
        tension_energetique = 'Forte'
    elif s['part_ve'] >= 40:
        tension_energetique = 'Modérée'
    else:
        tension_energetique = 'Faible'
    
    # Acceptabilité sociale basée sur ampleur changements
    changement_total = abs(s['reduction_km']) + report_total
    if changement_total >= 60:
        acceptabilite = 'Très faible'
    elif changement_total >= 40:
        acceptabilite = 'Faible'
    elif changement_total >= 20:
        acceptabilite = 'Moyenne'
    else:
        acceptabilite = 'Bonne'
    
    # Faisabilité industrielle
    if s['part_ve'] >= 80:
        faisabilite = 'Très difficile'
    elif s['part_ve'] >= 60:
        faisabilite = 'Difficile'
    elif s['part_ve'] >= 40:
        faisabilite = 'Modérée'
    else:
        faisabilite = 'Réaliste'
    
    return {
        'erreur': False,
        'km_total_2050': km_total_2050,
        'km_voiture_2050': km_voiture_2050,
        'km_tc_2050': km_tc_2050,
        'km_train_2050': km_train_2050,
        'km_velo_2050': km_velo_2050,
        'co2_hebdo': co2_hebdo_2050,
        'co2_annuel': co2_hebdo_2050 * 52,
        'energie_hebdo': energie_hebdo_2050,
        'energie_annuel': energie_hebdo_2050 * 52,
        'particules_hebdo': particules_hebdo_2050,
        'particules_annuel': particules_hebdo_2050 * 52,
        'reduction_co2': reduction_co2,
        'reduction_energie': reduction_energie,
        'reduction_particules': reduction_particules,
        'objectif_co2_atteint': objectif_co2_atteint,
        'tension_energetique': tension_energetique,
        'acceptabilite': acceptabilite,
        'faisabilite': faisabilite,
        'total_parc': total_parc
    }


# ==================== INTERFACE PRINCIPALE ====================

# Header
st.title("🚗 Transitions Mobilité Pays Basque 2050")
st.markdown("**Simulateur pédagogique** • Construisez votre scénario bas-carbone • Données ADEME 2024")

# Barre de progression
col_prog1, col_prog2, col_prog3 = st.columns(3)

with col_prog1:
    if st.button(
        f"{'✅' if st.session_state.step > 1 else '1️⃣'} Mon bilan",
        key="nav1",
        use_container_width=True,
        type="primary" if st.session_state.step == 1 else "secondary"
    ):
        st.session_state.step = 1
        st.rerun()

with col_prog2:
    if st.button(
        f"{'✅' if st.session_state.step > 2 else '2️⃣'} Habitant moyen",
        key="nav2",
        use_container_width=True,
        type="primary" if st.session_state.step == 2 else "secondary"
    ):
        st.session_state.step = 2
        st.rerun()

with col_prog3:
    if st.button(
        f"{'✅' if st.session_state.step > 3 else '3️⃣'} Scénario 2050",
        key="nav3",
        use_container_width=True,
        type="primary" if st.session_state.step == 3 else "secondary"
    ):
        st.session_state.step = 3
        st.rerun()

st.divider()

# ==================== ÉTAPE 1 : BILAN PERSONNEL ====================
if st.session_state.step == 1:
    st.header("👤 Mon bilan mobilité hebdomadaire")
    st.info("📝 Saisissez vos pratiques de mobilité actuelles pour prendre conscience de vos impacts")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📍 Distances parcourues (km/semaine)")
        
        st.session_state.perso['km_voiture'] = st.slider(
            "🚗 Voiture",
            min_value=0, max_value=500, value=st.session_state.perso['km_voiture'],
            step=5, key="p_voiture"
        )
        
        st.session_state.perso['km_tc'] = st.slider(
            "🚌 Transports en commun (bus, tram)",
            min_value=0, max_value=100, value=st.session_state.perso['km_tc'],
            step=5, key="p_tc"
        )
        
        st.session_state.perso['km_train'] = st.slider(
            "🚆 Train",
            min_value=0, max_value=100, value=st.session_state.perso['km_train'],
            step=5, key="p_train"
        )
        
        st.session_state.perso['km_velo'] = st.slider(
            "🚴 Vélo (mécanique ou électrique)",
            min_value=0, max_value=100, value=st.session_state.perso['km_velo'],
            step=5, key="p_velo"
        )
        
        st.session_state.perso['km_marche'] = st.slider(
            "🚶 Marche",
            min_value=0, max_value=50, value=st.session_state.perso['km_marche'],
            step=1, key="p_marche"
        )
    
    with col2:
        st.subheader("🚙 Caractéristiques voiture")
        
        st.session_state.perso['type_voiture'] = st.selectbox(
            "Type de carburant",
            options=['diesel', 'essence'],
            index=0 if st.session_state.perso['type_voiture'] == 'diesel' else 1,
            key="p_type"
        )
        
        st.session_state.perso['taux_remplissage'] = st.slider(
            "Taux de remplissage moyen (personnes/véhicule)",
            min_value=1.0, max_value=4.0, value=st.session_state.perso['taux_remplissage'],
            step=0.1, key="p_remplissage",
            help="1.0 = toujours seul, 2.0 = toujours à 2, etc."
        )
        
        st.session_state.perso['temps_stationnement'] = st.slider(
            "Temps où la voiture est stationnée (%)",
            min_value=80, max_value=99, value=st.session_state.perso['temps_stationnement'],
            step=1, key="p_stat",
            help="En moyenne, une voiture est stationnée 95% du temps"
        )
        
        # Bouton reset
        if st.button("🔄 Réinitialiser mes données", key="reset_perso"):
            st.session_state.perso = {
                'km_voiture': 200, 'km_tc': 20, 'km_train': 10,
                'km_velo': 15, 'km_marche': 5, 'type_voiture': 'diesel',
                'taux_remplissage': 1.2, 'temps_stationnement': 95
            }
            st.rerun()
    
    # Calcul et affichage résultats
    bilan_p = calc_bilan(st.session_state.perso)
    
    st.divider()
    st.subheader("📊 Vos impacts annuels")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="🌍 Émissions CO₂",
            value=f"{bilan_p['co2_annuel']:.0f} kg/an",
            delta=f"{bilan_p['co2_hebdo']:.1f} kg/semaine",
            help="Équivalent CO2 de vos déplacements (scope 1+2)"
        )
    
    with col2:
        st.metric(
            label="⚡ Énergie consommée",
            value=f"{bilan_p['energie_annuel']:.0f} kWh/an",
            delta=f"{bilan_p['energie_hebdo']:.1f} kWh/semaine",
            help="Énergie totale (équivalent électrique)"
        )
    
    with col3:
        st.metric(
            label="💨 Particules fines",
            value=f"{bilan_p['particules_annuel']:.1f} g/an",
            delta=f"{bilan_p['particules_hebdo']:.2f} g/semaine",
            help="Particules PM2.5 et PM10 (impact qualité de l'air)"
        )
    
    # Contexte pédagogique
    st.info(f"""
    **💡 Pour contextualiser :**
    - Vous parcourez **{bilan_p['km_total']} km/semaine** ({bilan_p['km_total'] * 52:.0f} km/an)
    - Objectif national 2050 : **-80% d'émissions CO₂** par rapport à 1990
    - Moyenne française : ~2200 kg CO₂/an pour la mobilité (source SDES)
    """)
    
    # Navigation
    st.divider()
    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav2:
        if st.button("➡️ Étape suivante : Habitant moyen", type="primary", use_container_width=True):
            st.session_state.step = 2
            st.rerun()


# ==================== ÉTAPE 2 : HABITANT MOYEN ====================
elif st.session_state.step == 2:
    st.header("👥 Habitant moyen du Pays Basque")
    
    st.info("""
    **📍 Contexte territorial :**
    - Population : ~300 000 habitants (Communauté Pays Basque)
    - Zone mixte : urbain dense (BAB) + périurbain + rural/montagne
    - Réseaux TC : Chronoplus (Bayonne-Anglet-Biarritz), Hegobus (interurbain)
    - Forte dépendance à la voiture (relief, dispersion habitat)
    
    ⚠️ *Valeurs indicatives : ajustez selon vos connaissances du territoire*
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📍 Distances hebdomadaires moyennes")
        
        st.session_state.moyen['km_voiture'] = st.slider(
            "🚗 Voiture",
            min_value=0, max_value=300, value=st.session_state.moyen['km_voiture'],
            step=5, key="m_voiture"
        )
        
        st.session_state.moyen['km_tc'] = st.slider(
            "🚌 TC urbains",
            min_value=0, max_value=100, value=st.session_state.moyen['km_tc'],
            step=5, key="m_tc"
        )
        
        st.session_state.moyen['km_train'] = st.slider(
            "🚆 Train",
            min_value=0, max_value=50, value=st.session_state.moyen['km_train'],
            step=2, key="m_train"
        )
        
        st.session_state.moyen['km_velo'] = st.slider(
            "🚴 Vélo",
            min_value=0, max_value=100, value=st.session_state.moyen['km_velo'],
            step=5, key="m_velo"
        )
        
        st.session_state.moyen['km_marche'] = st.slider(
            "🚶 Marche",
            min_value=0, max_value=50, value=st.session_state.moyen['km_marche'],
            step=2, key="m_marche"
        )
    
    with col2:
        st.subheader("🚙 Caractéristiques moyennes")
        
        st.session_state.moyen['type_voiture'] = st.selectbox(
            "Type de carburant dominant",
            options=['diesel', 'essence'],
            index=0 if st.session_state.moyen['type_voiture'] == 'diesel' else 1,
            key="m_type"
        )
        
        st.session_state.moyen['taux_remplissage'] = st.slider(
            "Taux de remplissage moyen",
            min_value=1.0, max_value=2.0, value=st.session_state.moyen['taux_remplissage'],
            step=0.1, key="m_remplissage"
        )
        
        st.session_state.moyen['temps_stationnement'] = st.slider(
            "Temps stationné (%)",
            min_value=90, max_value=98, value=st.session_state.moyen['temps_stationnement'],
            step=1, key="m_stat"
        )
        
        if st.button("🔄 Réinitialiser", key="reset_moyen"):
            st.session_state.moyen = {
                'km_voiture': 150, 'km_tc': 25, 'km_train': 8,
                'km_velo': 20, 'km_marche': 10, 'type_voiture': 'diesel',
                'taux_remplissage': 1.3, 'temps_stationnement': 95
            }
            st.rerun()
    
    # Calculs
    bilan_p = calc_bilan(st.session_state.perso)
    bilan_m = calc_bilan(st.session_state.moyen)
    
    st.divider()
    st.subheader("📊 Comparaison : Vous vs Habitant moyen")
    
    # Tableau comparatif
    df_comp = pd.DataFrame({
        'Indicateur': ['CO₂ (kg/an)', 'Énergie (kWh/an)', 'Particules (g/an)'],
        'Vous': [
            f"{bilan_p['co2_annuel']:.0f}",
            f"{bilan_p['energie_annuel']:.0f}",
            f"{bilan_p['particules_annuel']:.1f}"
        ],
        'Habitant moyen': [
            f"{bilan_m['co2_annuel']:.0f}",
            f"{bilan_m['energie_annuel']:.0f}",
            f"{bilan_m['particules_annuel']:.1f}"
        ],
        'Écart (%)': [
            f"{((bilan_p['co2_annuel'] - bilan_m['co2_annuel']) / bilan_m['co2_annuel'] * 100):+.0f}%",
            f"{((bilan_p['energie_annuel'] - bilan_m['energie_annuel']) / bilan_m['energie_annuel'] * 100):+.0f}%",
            f"{((bilan_p['particules_annuel'] - bilan_m['particules_annuel']) / bilan_m['particules_annuel'] * 100):+.0f}%"
        ]
    })
    
    st.dataframe(df_comp, use_container_width=True, hide_index=True)
    
    # Graphique comparatif
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Vous',
        x=['CO₂ (kg)', 'Énergie (kWh)', 'Particules (g)'],
        y=[bilan_p['co2_annuel'], bilan_p['energie_annuel'], bilan_p['particules_annuel']],
        marker_color='#3b82f6'
    ))
    fig.add_trace(go.Bar(
        name='Habitant moyen',
        x=['CO₂ (kg)', 'Énergie (kWh)', 'Particules (g)'],
        y=[bilan_m['co2_annuel'], bilan_m['energie_annuel'], bilan_m['particules_annuel']],
        marker_color='#10b981'
    ))
    fig.update_layout(
        title="Comparaison des impacts annuels",
        barmode='group',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Navigation
    st.divider()
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("⬅️ Retour : Mon bilan", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col_nav2:
        if st.button("➡️ Construire mon scénario 2050", type="primary", use_container_width=True):
            st.session_state.step = 3
            st.rerun()


# ==================== ÉTAPE 3 : SCÉNARIO 2050 ====================
else:
    st.header("🎯 Mon scénario Pays Basque 2050")
    
    st.warning("""
    **🎯 Objectif SNBC (Stratégie Nationale Bas-Carbone) :**
    Réduction de **-80% des émissions de CO₂** d'ici 2050 par rapport à 2023
    
    À partir du profil de l'habitant moyen, construisez un scénario réaliste en actionnant les 4 leviers.
    """)
    
    # Interface leviers
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚶 Levier 1 : Sobriété")
        st.session_state.scenario['reduction_km'] = st.slider(
            "Réduction des km totaux (%)",
            min_value=-40, max_value=10, value=st.session_state.scenario['reduction_km'],
            step=5, key="s_reduction",
            help="Télétravail, relocalisations, urbanisme des courtes distances, limitation vitesse..."
        )
        st.caption(f"Impact : {st.session_state.scenario['reduction_km']:+.0f}% de km parcourus")
        
        st.divider()
        
        st.subheader("🚴 Levier 2 : Report modal")
        st.caption("Transfert de la voiture vers d'autres modes")
        
        st.session_state.scenario['report_velo'] = st.slider(
            "Voiture → Vélo/Marche (%)",
            min_value=0, max_value=35, value=st.session_state.scenario['report_velo'],
            step=5, key="s_velo",
            help="Pistes cyclables sécurisées, vélo à assistance électrique, aménagements piétons"
        )
        
        st.session_state.scenario['report_tc'] = st.slider(
            "Voiture → TC urbains (%)",
            min_value=0, max_value=30, value=st.session_state.scenario['report_tc'],
            step=5, key="s_tc",
            help="Extension Chronoplus, nouvelles lignes de tram, fréquence augmentée"
        )
        
        st.session_state.scenario['report_train'] = st.slider(
            "Voiture → Train (%)",
            min_value=0, max_value=20, value=st.session_state.scenario['report_train'],
            step=5, key="s_train",
            help="Réouverture lignes ferroviaires, cadencement, tarification attractive"
        )
        
        report_total = st.session_state.scenario['report_velo'] + st.session_state.scenario['report_tc'] + st.session_state.scenario['report_train']
        st.info(f"📊 Report total : **{report_total}%** de la part modale voiture transférée")
    
    with col2:
        st.subheader("⚡ Levier 3 : Décarbonation du parc")
        st.caption("Composition du parc automobile en 2050")
        
        st.session_state.scenario['part_ve'] = st.slider(
            "Véhicules 100% électriques (%)",
            min_value=0, max_value=100, value=st.session_state.scenario['part_ve'],
            step=5, key="s_ve",
            help="Voitures électriques à batterie (BEV)"
        )
        
        st.session_state.scenario['part_hybride'] = st.slider(
            "Véhicules hybrides rechargeables (%)",
            min_value=0, max_value=50, value=st.session_state.scenario['part_hybride'],
            step=5, key="s_hybride",
            help="Hybrides rechargeables (PHEV)"
        )
        
        st.session_state.scenario['part_essence'] = st.slider(
            "Véhicules essence (%)",
            min_value=0, max_value=60, value=st.session_state.scenario['part_essence'],
            step=5, key="s_essence"
        )
        
        st.session_state.scenario['part_diesel'] = st.slider(
            "Véhicules diesel (%)",
            min_value=0, max_value=80, value=st.session_state.scenario['part_diesel'],
            step=5, key="s_diesel"
        )
        
        total_parc = (st.session_state.scenario['part_ve'] + 
                      st.session_state.scenario['part_hybride'] + 
                      st.session_state.scenario['part_essence'] + 
                      st.session_state.scenario['part_diesel'])
        
        if total_parc == 100:
            st.success(f"✅ Total parc : {total_parc}%")
        else:
            st.error(f"⚠️ Total parc : {total_parc}% (doit être exactement 100%)")
        
        st.divider()
        
        st.subheader("👥 Levier 4 : Optimisation")
        st.session_state.scenario['taux_remplissage'] = st.slider(
            "Taux de remplissage moyen (pers/véhicule)",
            min_value=1.3, max_value=2.2, value=st.session_state.scenario['taux_remplissage'],
            step=0.1, key="s_remplissage",
            help="Covoiturage, autopartage, transport à la demande"
        )
        
        if st.button("🔄 Réinitialiser le scénario", key="reset_scenario"):
            st.session_state.scenario = {
                'reduction_km': 0, 'report_velo': 0, 'report_tc': 0, 'report_train': 0,
                'part_ve': 3, 'part_hybride': 12, 'part_essence': 20, 'part_diesel': 65,
                'taux_remplissage': 1.4
            }
            st.rerun()
    
    # Calcul des résultats
    resultats = calc_scenario_2050()
    
    # Vérification erreurs
    if resultats['erreur']:
        st.error(resultats['message'])
        st.stop()
    
    # Affichage résultats
    st.divider()
    st.header("📊 Résultats de votre scénario 2050")
    
    # Métriques principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        delta_co2 = f"{resultats['reduction_co2']:.0f}% vs 2023"
        st.metric(
            label="🌍 Émissions CO₂",
            value=f"{resultats['co2_annuel']:.0f} kg/an",
            delta=delta_co2,
            delta_color="inverse"
        )
        if resultats['objectif_co2_atteint']:
            st.success("✅ **Objectif atteint !**")
        else:
            st.error(f"❌ Objectif non atteint (besoin : -80%, actuel : {resultats['reduction_co2']:.0f}%)")
    
    with col2:
        delta_energie = f"{resultats['reduction_energie']:.0f}% vs 2023"
        st.metric(
            label="⚡ Énergie consommée",
            value=f"{resultats['energie_annuel']:.0f} kWh/an",
            delta=delta_energie,
            delta_color="inverse"
        )
        
        # Indicateur tension énergétique avec couleur
        tension_color = {
            'Faible': '🟢',
            'Modérée': '🟡',
            'Forte': '🟠',
            'Très forte': '🔴'
        }
        st.info(f"Tension énergétique : {tension_color.get(resultats['tension_energetique'], '⚪')} **{resultats['tension_energetique']}**")
    
    with col3:
        delta_particules = f"{resultats['reduction_particules']:.0f}% vs 2023"
        st.metric(
            label="💨 Particules fines",
            value=f"{resultats['particules_annuel']:.1f} g/an",
            delta=delta_particules,
            delta_color="inverse"
        )
        st.info(f"Qualité de l'air : **Amélioration de {resultats['reduction_particules']:.0f}%**")
    
    # Indicateurs secondaires
    st.divider()
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        accept_color = {
            'Bonne': '🟢',
            'Moyenne': '🟡',
            'Faible': '🟠',
            'Très faible': '🔴'
        }
        st.info(f"**👥 Acceptabilité sociale**\n\n{accept_color.get(resultats['acceptabilite'], '⚪')} {resultats['acceptabilite']}")
    
    with col_b:
        fais_color = {
            'Réaliste': '🟢',
            'Modérée': '🟡',
            'Difficile': '🟠',
            'Très difficile': '🔴'
        }
        st.info(f"**🏭 Faisabilité industrielle**\n\n{fais_color.get(resultats['faisabilite'], '⚪')} {resultats['faisabilite']}")
    
    with col_c:
        st.info(f"**🚗 Part véhicules électriques**\n\n{st.session_state.scenario['part_ve']}% du parc")
    
    # Graphiques
    st.divider()
    st.subheader("📈 Évolution des indicateurs (2023 → 2050)")
    
    bilan_m = calc_bilan(st.session_state.moyen)
    
    # Graphique barres comparatif
    df_evolution = pd.DataFrame({
        'Indicateur': ['CO₂ (kg/an)', 'Énergie (kWh/an)', 'Particules (g/an)'],
        '2023 (Habitant moyen)': [
            bilan_m['co2_annuel'],
            bilan_m['energie_annuel'],
            bilan_m['particules_annuel']
        ],
        '2050 (Votre scénario)': [
            resultats['co2_annuel'],
            resultats['energie_annuel'],
            resultats['particules_annuel']
        ]
    })
    
    fig_evolution = px.bar(
        df_evolution,
        x='Indicateur',
        y=['2023 (Habitant moyen)', '2050 (Votre scénario)'],
        barmode='group',
        title="Comparaison 2023 vs 2050",
        color_discrete_sequence=['#94a3b8', '#3b82f6']
    )
    fig_evolution.update_layout(height=400, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_evolution, use_container_width=True)
    
    # Graphique radar multi-critères
    st.subheader("🎯 Évaluation multi-critères de votre scénario")
    
    # Calcul des scores normalisés (0-100)
    score_climat = min(100, (resultats['reduction_co2'] / 80) * 100) if resultats['reduction_co2'] > 0 else 0
    score_energie = min(100, resultats['reduction_energie']) if resultats['reduction_energie'] > 0 else 0
    score_air = min(100, resultats['reduction_particules']) if resultats['reduction_particules'] > 0 else 0
    
    # Scores acceptabilité et faisabilité
    accept_scores = {'Bonne': 85, 'Moyenne': 60, 'Faible': 35, 'Très faible': 15}
    fais_scores = {'Réaliste': 85, 'Modérée': 65, 'Difficile': 40, 'Très difficile': 20}
    
    score_accept = accept_scores.get(resultats['acceptabilite'], 50)
    score_fais = fais_scores.get(resultats['faisabilite'], 50)
    
    # Créer le radar
    categories = ['Climat', 'Énergie', 'Qualité air', 'Acceptabilité', 'Faisabilité']
    values = [score_climat, score_energie, score_air, score_accept, score_fais]
    
    fig_radar = go.Figure()
    
    fig_radar.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Votre scénario',
        line_color='#3b82f6',
        fillcolor='rgba(59, 130, 246, 0.3)'
    ))
    
    # Ajouter ligne objectif (80/100 sur tous les critères serait idéal)
    fig_radar.add_trace(go.Scatterpolar(
        r=[80, 80, 80, 80, 80],
        theta=categories,
        fill='toself',
        name='Objectif équilibré',
        line_color='#10b981',
        line_dash='dash',
        fillcolor='rgba(16, 185, 129, 0.1)'
    ))
    
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        showlegend=True,
        height=500
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)
    
    # Questions d'analyse pour débat étudiant
    st.divider()
    st.header("🧐 Questions d'analyse pour le débat")
    
    st.markdown("""
    Utilisez ces questions pour analyser votre scénario et identifier ses forces/faiblesses.
    **Préparez-vous à défendre vos choix en cours !**
    """)
    
    with st.expander("💡 Question 1 : Objectif climatique", expanded=not resultats['objectif_co2_atteint']):
        if resultats['objectif_co2_atteint']:
            st.success("✅ Votre scénario atteint l'objectif -80% !")
            st.write("""
            **Questions à approfondir :**
            - Quels leviers ont été les plus efficaces ?
            - Votre scénario est-il réaliste au vu des autres critères ?
            - Aurait-on pu atteindre l'objectif avec moins de contraintes ?
            """)
        else:
            st.error(f"❌ Objectif non atteint : {resultats['reduction_co2']:.0f}% de réduction (besoin : -80%)")
            st.write("""
            **Pistes d'amélioration :**
            - Quels leviers pourriez-vous actionner davantage ?
            - Quels compromis êtes-vous prêt à accepter ?
            - Un scénario 100% technologique (électrification) suffit-il ?
            """)
    
    with st.expander(f"⚡ Question 2 : Tension énergétique - {resultats['tension_energetique']}"):
        st.write(f"""
        Votre scénario prévoit **{st.session_state.scenario['part_ve']}% de véhicules électriques**.
        
        **Points à analyser :**
        - **Production électrique** : Le Pays Basque produit peu d'électricité (pas de centrale nucléaire, 
          quelques barrages hydroélectriques). D'où viendra l'électricité supplémentaire ?
        - **Réseaux de distribution** : Les réseaux actuels peuvent-ils supporter une charge massive 
          de recharge simultanée (17h-20h) ?
        - **Bornes de recharge** : Combien faut-il installer ? Où (domicile, travail, voirie) ?
        - **Stockage** : Faut-il des batteries stationnaires pour lisser la demande ?
        - **Intermittence** : Si on développe les EnR (solaire, éolien), comment gérer l'intermittence ?
        
        💡 **Tension {resultats['tension_energetique'].lower()}** : 
        {
            'Faible': "L'électrification reste modérée, la tension sur le réseau est gérable.",
            'Modérée': "Une électrification significative nécessite des investissements réseau.",
            'Forte': "L'électrification importante pose des défis majeurs de production et distribution.",
            'Très forte': "L'électrification massive nécessite une refonte complète du système énergétique."
        }.get(resultats['tension_energetique'], '')
        """)
    
    with st.expander(f"🏭 Question 3 : Défi industriel - {resultats['faisabilite']}"):
        st.write(f"""
        **Faisabilité industrielle : {resultats['faisabilite']}**
        
        Votre scénario vise :
        - **{st.session_state.scenario['part_ve']}%** de véhicules électriques
        - **{st.session_state.scenario['part_hybride']}%** de véhicules hybrides
        
        **Questions critiques :**
        - **Capacité de production** : Les constructeurs peuvent-ils produire autant de VE d'ici 2050 ?
          Le parc se renouvelle en ~15 ans. Sommes-nous dans les temps ?
        - **Ressources minérales** : Lithium, cobalt, nickel, terres rares...
          Les réserves mondiales sont-elles suffisantes ? Quels impacts géopolitiques/environnementaux ?
        - **Recyclage batteries** : Quelle filière de recyclage mettre en place ?
        - **Main d'œuvre** : Formation des garagistes, électriciens, etc.
        - **Coût** : Un VE coûte 30-40% plus cher qu'un thermique. Qui paie ? Aides publiques viables ?
        
        💡 Au Pays Basque, faut-il favoriser l'autopartage/covoiturage plutôt que le VE individuel ?
        """)
    
    with st.expander(f"👥 Question 4 : Acceptabilité sociale - {resultats['acceptabilite']}"):
        changement_total = abs(st.session_state.scenario['reduction_km']) + report_total
        st.write(f"""
        **Acceptabilité : {resultats['acceptabilite']}**
        
        Votre scénario demande :
        - **{abs(st.session_state.scenario['reduction_km'])}%** de réduction/augmentation des km parcourus
        - **{report_total}%** de report modal de la voiture vers d'autres modes
        - **Total changement : {changement_total}%**
        
        **Questions de mise en œuvre :**
        - **Contrainte ou incitation** ? Interdictions (ZFE, limitation vitesse) ou aides (prime vélo, TC gratuits) ?
        - **Équité territoriale** : Comment gérer la diversité du territoire (urbain BAB vs montagne basque) ?
        - **Équité sociale** : Les ménages modestes peuvent-ils se passer de voiture ? Acheter un VE ?
        - **Temps de trajet** : Un report vers vélo/TC augmente souvent le temps de trajet. Acceptable ?
        - **Confort** : Renoncer à la voiture individuelle = perte d'autonomie/confort. Comment compenser ?
        - **Temporalité** : 2050 c'est dans 25 ans. Une génération. Les mentalités peuvent-elles évoluer ?
        
        💡 Au Pays Basque : forte identité culturelle, habitat dispersé, relief montagneux.
        Ces spécificités facilitent ou compliquent la transition ?
        """)
    
    with st.expander("🎯 Question 5 : Arbitrages et compromis"):
        st.write(f"""
        **Analyse de vos choix stratégiques :**
        
        Vous avez privilégié :
        - {"🔵 **La sobriété**" if abs(st.session_state.scenario['reduction_km']) > 20 else "⚪ Peu de sobriété"} 
          ({st.session_state.scenario['reduction_km']:+}% de km)
        - {"🟢 **Le report modal**" if report_total > 25 else "⚪ Peu de report modal"} 
          ({report_total}% de transfert)
        - {"🟣 **La technologie**" if st.session_state.scenario['part_ve'] > 60 else "⚪ Peu d'électrification"} 
          ({st.session_state.scenario['part_ve']}% VE)
        
        **Questions de réflexion :**
        1. **Scénario extrême technologique** (100% VE, peu de sobriété/report) :
           - Avantages ? Limites ? Réaliste ?
        
        2. **Scénario extrême sobriété** (-40% km, report massif, peu de VE) :
           - Avantages ? Limites ? Acceptable socialement ?
        
        3. **Scénario équilibré** : Existe-t-il ? Quel dosage optimal ?
        
        4. **Rôle des pouvoirs publics** :
           - Que peut faire la Communauté Pays Basque ?
           - L'État ? L'Europe ?
        
        5. **Et vous personnellement** : Seriez-vous prêt à vivre selon ce scénario ?
        
        💡 Il n'y a pas de "bonne" réponse unique. Chaque scénario fait des choix de société différents.
        """)
    
    with st.expander("🌍 Question 6 : Co-bénéfices et effets rebond"):
        st.write(f"""
        **Au-delà du CO₂, quels autres impacts ?**
        
        **Co-bénéfices positifs :**
        - **Santé publique** : -{resultats['reduction_particules']:.0f}% de particules fines
          → Moins d'asthme, maladies respiratoires, cardiovasculaires
        - **Bruit** : VE et vélos = réduction pollution sonore (surtout en ville)
        - **Activité physique** : +{st.session_state.scenario['report_velo']}% vers vélo/marche
          → Lutte contre sédentarité, obésité
        - **Espace public** : Moins de voitures stationnées ({st.session_state.moyen['temps_stationnement']}% du temps)
          → Récupération espace urbain pour végétalisation, terrasses...
        - **Économies** : Moins de km = moins de carburant/électricité = pouvoir d'achat
        
        **Risques d'effets rebond :**
        - **Effet rebond économique** : Économies faites sur le transport réinvesties dans d'autres
          activités émettrices (voyages en avion, consommation...)
        - **Effet rebond VE** : "C'est électrique donc écolo" → Conduite plus intensive, véhicules plus lourds (SUV électriques)
        - **Report domicile-travail** : Télétravail → Installation plus loin en périurbain → + de km le week-end
        
        💡 Comment maximiser les co-bénéfices et limiter les effets rebond ?
        """)
    
    # Points clés pédagogiques
    st.divider()
    st.header("💡 Points clés à retenir")
    
    st.info("""
    **Synthèse des enseignements :**
    
    1️⃣ **Pas de solution miracle** : L'objectif -80% nécessite d'actionner **TOUS** les leviers simultanément.
       Un seul levier (ex: 100% électrification) ne suffit pas et crée des tensions ailleurs.
    
    2️⃣ **La sobriété est incontournable** : Réduire la demande de mobilité est le levier le plus efficace
       mais aussi le plus difficile socialement et politiquement.
    
    3️⃣ **L'électrification a des limites** : Production, réseaux, ressources, coût, recyclage...
       Une électrification massive pose des défis systémiques majeurs.
    
    4️⃣ **Le report modal nécessite des infrastructures lourdes** : Pistes cyclables, réseaux TC denses,
       intermodalité... Investissements massifs et temps long.
    
    5️⃣ **Le temps presse** : 2050 = dans 25 ans. Le parc automobile se renouvelle en 10-15 ans.
       Les décisions d'aujourd'hui déterminent le parc de 2040.
    
    6️⃣ **Penser territoire** : Un scénario pour Bayonne ≠ un scénario pour Mauléon.
       Il faut des solutions différenciées selon les contextes (urbain/rural, relief, densité...).
    
    7️⃣ **Acceptabilité sociale = clé de voûte** : Une transition imposée sans accompagnement
       génère des résistances (Gilets jaunes 2018...). Il faut co-construire avec les citoyens.
    
    8️⃣ **Approche systémique** : Mobilité liée à urbanisme, habitat, emploi, loisirs...
       On ne peut pas traiter la mobilité isolément.
    
    📚 **Pour aller plus loin :**
    - [Scénarios ADEME Transitions 2050](https://transitions2050.ademe.fr/)
    - [Stratégie Nationale Bas-Carbone (SNBC)](https://www.ecologie.gouv.fr/strategie-nationale-bas-carbone-snbc)
    - [The Shift Project - Plan de transformation de l'économie française](https://theshiftproject.org/plan-de-transformation-de-leconomie-francaise/)
    """)
    
    # Export/partage des résultats (simplifié)
    st.divider()
    st.subheader("💾 Sauvegarder votre scénario")
    
    # Créer un résumé du scénario
    resume_scenario = f"""
SCÉNARIO MOBILITÉ PAYS BASQUE 2050
===================================

LEVIERS ACTIONNÉS:
- Sobriété: {st.session_state.scenario['reduction_km']:+}% de km
- Report modal vers vélo: {st.session_state.scenario['report_velo']}%
- Report modal vers TC: {st.session_state.scenario['report_tc']}%
- Report modal vers train: {st.session_state.scenario['report_train']}%
- Part VE: {st.session_state.scenario['part_ve']}%
- Part hybride: {st.session_state.scenario['part_hybride']}%
- Taux remplissage: {st.session_state.scenario['taux_remplissage']:.1f} pers/véh

RÉSULTATS:
- CO₂: {resultats['co2_annuel']:.0f} kg/an ({resultats['reduction_co2']:.0f}% vs 2023)
- Énergie: {resultats['energie_annuel']:.0f} kWh/an ({resultats['reduction_energie']:.0f}% vs 2023)
- Particules: {resultats['particules_annuel']:.1f} g/an ({resultats['reduction_particules']:.0f}% vs 2023)

ÉVALUATION:
- Objectif climatique: {"✅ ATTEINT" if resultats['objectif_co2_atteint'] else "❌ NON ATTEINT"}
- Tension énergétique: {resultats['tension_energetique']}
- Acceptabilité sociale: {resultats['acceptabilite']}
- Faisabilité industrielle: {resultats['faisabilite']}

SCORES MULTI-CRITÈRES (sur 100):
- Climat: {score_climat:.0f}/100
- Énergie: {score_energie:.0f}/100
- Qualité air: {score_air:.0f}/100
- Acceptabilité: {score_accept:.0f}/100
- Faisabilité: {score_fais:.0f}/100
"""
    
    st.download_button(
        label="📥 Télécharger le résumé (TXT)",
        data=resume_scenario,
        file_name="scenario_mobilite_2050.txt",
        mime="text/plain"
    )
    
    # Navigation
    st.divider()
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("⬅️ Retour : Habitant moyen", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with col_nav2:
        if st.button("🔄 Recommencer l'analyse complète", use_container_width=True):
            st.session_state.step = 1
            st.rerun()


# ==================== FOOTER ====================
st.divider()
st.markdown("""
<div style='text-align: center; color: #6b7280; font-size: 0.875rem;'>
    <p><strong>Sources de données :</strong></p>
    <p>
        <a href='https://impactco2.fr/outils/transport' target='_blank'>impactCO2.fr (ADEME)</a> • 
        <a href='https://www.ecologie.gouv.fr/strategie-nationale-bas-carbone-snbc' target='_blank'>SNBC 2050</a> • 
        <a href='https://transitions2050.ademe.fr/' target='_blank'>ADEME Transitions 2050</a>
    </p>
    <p style='margin-top: 1rem;'>
        <strong>Application pédagogique</strong> • Pays Basque Français • 2024-2050<br>
        ⚠️ Valeurs territoriales indicatives • À affiner selon données locales disponibles
    </p>
</div>
""", unsafe_allow_html=True)
