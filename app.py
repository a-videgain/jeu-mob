import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Configuration de la page
st.set_page_config(
    page_title="Transitions Mobilité 2050",
    page_icon="🚗",
    layout="wide"
)

# Données de référence
BASELINE = {
    'km_year_per_person': 12500,
    'modal_split': {'voiture': 80, 'tc_urbain': 8, 'train': 4, 'velo_marche': 8},
    'parc_vehicles': {'thermique': 95, 'electrique': 3, 'hydrogene': 2},
    'taux_occupation': 1.4,
    'co2_intensity': {
        'thermique': 220, 'electrique': 20, 'hydrogene': 30,
        'tc': 15, 'train': 10
    }
}

SCENARIOS_ADEME = {
    'S1': {'name': 'Génération frugale', 'reduction_km': -45, 'report_modal': 25, 'electrif': 60},
    'S2': {'name': 'Coopérations territoriales', 'reduction_km': -30, 'report_modal': 18, 'electrif': 75},
    'S3': {'name': 'Technologies vertes', 'reduction_km': -10, 'report_modal': 8, 'electrif': 95},
    'S4': {'name': 'Pari réparateur', 'reduction_km': -5, 'report_modal': 5, 'electrif': 85}
}

def calculate_results(levers):
    """Calcule tous les indicateurs du scénario"""
    total_km = BASELINE['km_year_per_person'] * (1 + levers['reduction_km'] / 100)
    
    # Nouveau split modal
    voiture_initial = BASELINE['modal_split']['voiture']
    report_total = levers['report_voiture_velo'] + levers['report_voiture_tc'] + levers['report_voiture_train']
    voiture_final = max(0, voiture_initial - report_total)
    
    new_split = {
        'voiture': voiture_final,
        'velo_marche': BASELINE['modal_split']['velo_marche'] + levers['report_voiture_velo'],
        'tc_urbain': BASELINE['modal_split']['tc_urbain'] + levers['report_voiture_tc'],
        'train': BASELINE['modal_split']['train'] + levers['report_voiture_train']
    }
    
    # Km par mode
    km_voiture = total_km * new_split['voiture'] / 100
    km_velo = total_km * new_split['velo_marche'] / 100
    km_tc = total_km * new_split['tc_urbain'] / 100
    km_train = total_km * new_split['train'] / 100
    
    # CO2 voiture selon mix énergétique
    thermique_pct = 100 - levers['electrification'] - levers['hydrogene']
    co2_voiture = (
        (thermique_pct / 100) * BASELINE['co2_intensity']['thermique'] +
        (levers['electrification'] / 100) * BASELINE['co2_intensity']['electrique'] +
        (levers['hydrogene'] / 100) * BASELINE['co2_intensity']['hydrogene']
    )
    
    # CO2 total
    co2_total = (
        km_voiture * co2_voiture +
        km_velo * 0 +
        km_tc * BASELINE['co2_intensity']['tc'] +
        km_train * BASELINE['co2_intensity']['train']
    ) / 1000  # kg CO2/an
    
    co2_baseline = (BASELINE['km_year_per_person'] * 0.8 * 220) / 1000
    reduction_co2_pct = ((co2_baseline - co2_total) / co2_baseline) * 100
    
    # Énergie
    population = 67_000_000
    energie_elec = (km_voiture * levers['electrification'] / 100 * 0.15) * population / 1e9
    energie_h2 = (km_voiture * levers['hydrogene'] / 100 * 0.30) * population / 1e9
    tension_energetique = min(100, (energie_elec / 500) * 100 * 10)
    
    # Acceptabilité et faisabilité
    changement_comportemental = abs(levers['reduction_km']) + report_total
    acceptabilite = max(0, 100 - changement_comportemental * 0.8)
    
    ve_needed_pct = levers['electrification']
    faisabilite = 40 if ve_needed_pct > 80 else (70 if ve_needed_pct > 60 else 90)
    
    cobenefices = min(100, reduction_co2_pct * 0.7 + report_total * 0.5)
    
    return {
        'total_km': total_km,
        'new_split': new_split,
        'co2_total': co2_total,
        'co2_baseline': co2_baseline,
        'reduction_co2_pct': reduction_co2_pct,
        'energie_elec': energie_elec,
        'energie_h2': energie_h2,
        'tension_energetique': tension_energetique,
        'acceptabilite': acceptabilite,
        'faisabilite': faisabilite,
        'cobenefices': cobenefices,
        'objectif_2050': -80
    }

# Interface Streamlit
st.title("🚗 Transitions Mobilité 2050")
st.markdown("**Simulateur pédagogique inspiré des scénarios ADEME** • Horizon 2050 • Transport de personnes uniquement")

# Initialisation des leviers
if 'levers' not in st.session_state:
    st.session_state.levers = {
        'reduction_km': 0,
        'report_voiture_velo': 0,
        'report_voiture_tc': 0,
        'report_voiture_train': 0,
        'electrification': 3,
        'hydrogene': 2,
        'taux_occupation': 1.4
    }

# Scénarios ADEME
st.header("⚡ Scénarios ADEME (optionnel)")
cols = st.columns(4)
for i, (key, s) in enumerate(SCENARIOS_ADEME.items()):
    with cols[i]:
        if st.button(f"{key} - {s['name']}", use_container_width=True):
            st.session_state.levers.update({
                'reduction_km': s['reduction_km'],
                'report_voiture_velo': s['report_modal'] * 0.4,
                'report_voiture_tc': s['report_modal'] * 0.3,
                'report_voiture_train': s['report_modal'] * 0.3,
                'electrification': s['electrif'],
                'hydrogene': 100 - s['electrif'] - 5,
                'taux_occupation': 1.4 + (abs(s['reduction_km']) * 0.01)
            })
            st.rerun()

st.divider()

# Leviers d'action
col1, col2 = st.columns(2)

with col1:
    st.subheader("📉 Levier 1 : Réduction de la demande")
    st.session_state.levers['reduction_km'] = st.slider(
        "Réduction des km parcourus (%)",
        -50, 10, st.session_state.levers['reduction_km'], 5,
        help=f"{BASELINE['km_year_per_person']} km/an actuellement"
    )
    
    st.subheader("🚴 Levier 2 : Report modal")
    st.session_state.levers['report_voiture_velo'] = st.slider(
        "Voiture → Vélo/Marche (%)",
        0, 30, int(st.session_state.levers['report_voiture_velo']), 2
    )
    st.session_state.levers['report_voiture_tc'] = st.slider(
        "Voiture → TC urbains (%)",
        0, 25, int(st.session_state.levers['report_voiture_tc']), 2
    )
    st.session_state.levers['report_voiture_train'] = st.slider(
        "Voiture → Train (%)",
        0, 20, int(st.session_state.levers['report_voiture_train']), 2
    )

with col2:
    st.subheader("⚡ Levier 3 : Électrification")
    st.session_state.levers['electrification'] = st.slider(
        "Part de véhicules électriques (%)",
        0, 100, st.session_state.levers['electrification'], 5
    )
    st.session_state.levers['hydrogene'] = st.slider(
        "Part hydrogène/biocarburants (%)",
        0, 50, st.session_state.levers['hydrogene'], 5
    )
    thermique = max(0, 100 - st.session_state.levers['electrification'] - st.session_state.levers['hydrogene'])
    st.info(f"Thermique restant : {thermique:.0f}%")
    
    st.subheader("🚗 Levier 4 : Taux d'occupation")
    st.session_state.levers['taux_occupation'] = st.slider(
        "Personnes par véhicule",
        1.2, 2.5, st.session_state.levers['taux_occupation'], 0.1
    )

# Calculs
results = calculate_results(st.session_state.levers)

st.divider()

# Indicateurs clés
st.header("📊 Résultats")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Émissions CO₂",
        f"{results['co2_total']:.0f} kg/an",
        f"{results['reduction_co2_pct']:.0f}% vs 2023",
        delta_color="inverse"
    )

with col2:
    st.metric(
        "Énergie électrique",
        f"{results['energie_elec']:.0f} TWh",
        f"Tension : {results['tension_energetique']:.0f}%"
    )

with col3:
    st.metric(
        "Acceptabilité sociale",
        f"{results['acceptabilite']:.0f}%"
    )

with col4:
    objectif_atteint = "✅" if results['reduction_co2_pct'] >= results['objectif_2050'] else "⚠️"
    st.metric(
        "Objectif SNBC 2050",
        objectif_atteint,
        "-80% requis"
    )

st.divider()

# Graphiques
col1, col2 = st.columns(2)

with col1:
    # Parts modales
    df_modal = pd.DataFrame({
        'Mode': ['Voiture', 'Vélo/Marche', 'TC urbain', 'Train'],
        '2023': [BASELINE['modal_split']['voiture'], BASELINE['modal_split']['velo_marche'],
                 BASELINE['modal_split']['tc_urbain'], BASELINE['modal_split']['train']],
        '2050': [results['new_split']['voiture'], results['new_split']['velo_marche'],
                 results['new_split']['tc_urbain'], results['new_split']['train']]
    })
    
    fig1 = px.bar(df_modal, x='Mode', y=['2023', '2050'], barmode='group',
                  title="Parts modales (%)", labels={'value': '%', 'variable': 'Année'})
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    # Radar multi-critères
    categories = ['Climat', 'Acceptabilité', 'Faisabilité', 'Co-bénéfices', 'Énergie']
    values = [
        min(100, (results['reduction_co2_pct'] / 80) * 100),
        results['acceptabilite'],
        results['faisabilite'],
        results['cobenefices'],
        max(0, 100 - results['tension_energetique'])
    ]
    
    fig2 = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Votre scénario'
    ))
    fig2.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        title="Évaluation multi-critères"
    )
    st.plotly_chart(fig2, use_container_width=True)

# Alertes pédagogiques
st.header("⚠️ Analyse du scénario")

if results['reduction_co2_pct'] < results['objectif_2050']:
    st.error(f"Objectif climatique non atteint : {results['reduction_co2_pct']:.0f}% de réduction vs -80% requis")

if results['tension_energetique'] > 50:
    st.warning("⚡ Forte tension énergétique : l'électrification massive nécessite une production électrique conséquente")

if results['acceptabilite'] < 50:
    st.warning("👥 Acceptabilité sociale faible : les changements comportementaux demandés sont très importants")

if results['faisabilite'] < 60:
    st.warning("🏭 Défi industriel : la production de véhicules électriques/hydrogène à cette échelle est un enjeu majeur")

if (results['reduction_co2_pct'] >= results['objectif_2050'] and 
    results['tension_energetique'] < 40 and 
    results['acceptabilite'] > 60):
    st.success("✅ Scénario équilibré ! Vous atteignez les objectifs climatiques avec un bon compromis.")

# Footer
st.divider()
st.info("""
**💡 Points clés à retenir :**
- Aucun levier seul ne suffit : il faut combiner sobriété, report modal et décarbonation
- L'électrification totale pose des défis énergétiques (production, réseaux, ressources)
- Les changements comportementaux sont essentiels mais difficiles à mettre en œuvre
- Les scénarios ADEME montrent différentes voies possibles, avec des compromis différents
""")
```

