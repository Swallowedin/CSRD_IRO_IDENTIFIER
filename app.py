import streamlit as st
from typing import Dict, List
import json
from openai import OpenAI
import pandas as pd
from datetime import datetime
import io

# Configuration de la page
st.set_page_config(
    page_title="Analyseur CSRD - IRO",
    page_icon="📊",
    layout="wide"
)

class GPTInterface:
    """Interface avec l'API GPT"""
    def __init__(self):
        try:
            self.api_key = st.secrets["OPENAI_API_KEY"]
        except KeyError:
            st.error("❌ Clé API OpenAI non trouvée dans les secrets Streamlit.")
            st.info("💡 Ajoutez votre clé API dans les secrets Streamlit avec la clé 'OPENAI_API_KEY'")
            st.stop()
            
        self.client = OpenAI(api_key=self.api_key)

    def generate_iros(self, context: dict) -> dict:
        """Génère des IRO via GPT"""
        prompt = self._create_prompt(context)
        
        with st.spinner('Analyse en cours et génération des IRO...'):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Vous êtes un expert en reporting CSRD spécialisé dans l'identification des IRO. Analysez en profondeur chaque enjeu mentionné pour fournir une analyse CSRD complète."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Erreur lors de la génération des IRO: {str(e)}")
                return {}

    def _create_prompt(self, context: dict) -> str:
        return f"""
        En tant qu'expert CSRD, analysez en détail ce profil d'entreprise et générez une analyse détaillée selon le format demandé.

        PROFIL DE L'ENTREPRISE:
        {context['company_description']}

        SECTEUR D'ACTIVITÉ:
        {context['industry_sector']}

        MODÈLE D'AFFAIRES:
        {context['business_model']}

        CARACTÉRISTIQUES SPÉCIFIQUES:
        {context['specific_features']}

        ENJEUX IDENTIFIÉS:
        Environnement: {context['priority_issues']['environmental']}
        Social: {context['priority_issues']['social']}
        Gouvernance: {context['priority_issues']['governance']}

        Pour chaque ENJEU MENTIONNÉ dans les textes ci-dessus, réalisez une analyse CSRD complète selon cette structure JSON exacte :

        {{
            "nom_du_pilier": {{ // environnement, social, ou gouvernance
                "nom_de_l_enjeu": {{
                    "description": "Description détaillée de l'enjeu",
                    "impacts": {{
                        "positifs": [
                            "Impact positif 1 lié au modèle d'affaires",
                            "Impact positif 2 lié au modèle d'affaires"
                        ],
                        "negatifs": [
                            "Impact négatif 1 lié au modèle d'affaires",
                            "Impact négatif 2 lié au modèle d'affaires"
                        ]
                    }},
                    "risques": {{
                        "liste": [
                            "Description risque 1",
                            "Description risque 2"
                        ],
                        "niveau": "Élevé/Moyen/Faible",
                        "horizon": "Court/Moyen/Long terme",
                        "mesures_attenuation": [
                            "Mesure 1 pour atténuer les risques",
                            "Mesure 2 pour atténuer les risques"
                        ]
                    }},
                    "opportunites": {{
                        "liste": [
                            "Description opportunité 1",
                            "Description opportunité 2"
                        ],
                        "potentiel": "Élevé/Moyen/Faible",
                        "horizon": "Court/Moyen/Long terme",
                        "actions_saisie": [
                            "Action 1 pour saisir l'opportunité",
                            "Action 2 pour saisir l'opportunité"
                        ]
                    }},
                    "iros": [
                        {{
                            "indicateur": "Nom de l'IRO 1",
                            "description": "Description détaillée de l'indicateur",
                            "methodologie": "Comment collecter et calculer",
                            "frequence": "Fréquence de mesure",
                            "objectifs": {{
                                "court_terme": "Objectif à 1 an",
                                "moyen_terme": "Objectif à 3 ans",
                                "long_terme": "Objectif à 5 ans"
                            }}
                        }}
                    ]
                }}
            }}
        }}

        EXEMPLE CONCRET pour un enjeu :
        {{
            "environnement": {{
                "emissions_ges": {{
                    "description": "Gestion et réduction des émissions de gaz à effet de serre dans les opérations",
                    "impacts": {{
                        "positifs": [
                            "Développement de solutions bas-carbone innovantes",
                            "Amélioration de l'efficacité énergétique"
                        ],
                        "negatifs": [
                            "Émissions directes liées aux activités de production",
                            "Émissions indirectes de la chaîne logistique"
                        ]
                    }},
                    "risques": {{
                        "liste": [
                            "Augmentation des coûts liés à la tarification carbone",
                            "Perte de parts de marché face aux alternatives plus vertes"
                        ],
                        "niveau": "Élevé",
                        "horizon": "Moyen terme",
                        "mesures_attenuation": [
                            "Programme de réduction des émissions",
                            "Investissement dans les énergies renouvelables"
                        ]
                    }},
                    "opportunites": {{
                        "liste": [
                            "Développement de produits éco-conçus",
                            "Accès à de nouveaux marchés verts"
                        ],
                        "potentiel": "Élevé",
                        "horizon": "Moyen terme",
                        "actions_saisie": [
                            "Programme R&D produits bas-carbone",
                            "Certification environnementale"
                        ]
                    }},
                    "iros": [
                        {{
                            "indicateur": "Intensité carbone par unité produite",
                            "description": "Mesure des émissions de GES par unité de production",
                            "methodologie": "Calcul selon GHG Protocol",
                            "frequence": "Trimestrielle",
                            "objectifs": {{
                                "court_terme": "-10% en 1 an",
                                "moyen_terme": "-30% en 3 ans",
                                "long_terme": "-50% en 5 ans"
                            }}
                        }}
                    ]
                }}
            }}
        }}

        IMPORTANT :
        1. Analysez CHAQUE enjeu mentionné dans les textes fournis
        2. Suivez EXACTEMENT la structure JSON donnée
        3. Adaptez le contenu au contexte spécifique de l'entreprise
        4. Soyez PRÉCIS et CONCRET dans les descriptions"""

def company_profile_section():
    """Section pour la description détaillée de l'entreprise"""
    st.header("📋 Profil de l'entreprise")
    
    company_description = st.text_area(
        "Description générale de l'entreprise",
        height=150,
        help="Décrivez votre entreprise en détail (taille, marchés, implantation géographique, etc.)"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        industry_sector = st.text_area(
            "Secteur d'activité",
            height=100,
            help="Décrivez votre secteur d'activité et ses spécificités"
        )
    
    with col2:
        business_model = st.text_area(
            "Modèle d'affaires",
            height=100,
            help="Expliquez votre modèle d'affaires et sa chaîne de valeur"
        )
    
    specific_features = st.text_area(
        "Caractéristiques spécifiques",
        height=150,
        help="Détaillez les particularités qui distinguent votre entreprise (innovation, technologies, contraintes réglementaires, etc.)"
    )
    
    return {
        "company_description": company_description,
        "industry_sector": industry_sector,
        "business_model": business_model,
        "specific_features": specific_features
    }

def priority_issues_section():
    """Section pour identifier les enjeux prioritaires"""
    st.header("🎯 Enjeux prioritaires")
    
    st.info("Identifiez et décrivez les enjeux ESG prioritaires pour votre entreprise")
    
    environmental_issues = st.text_area(
        "Enjeux environnementaux",
        height=100,
        help="Décrivez les enjeux environnementaux spécifiques à votre activité"
    )
    
    social_issues = st.text_area(
        "Enjeux sociaux",
        height=100,
        help="Décrivez les enjeux sociaux et sociétaux pertinents"
    )
    
    governance_issues = st.text_area(
        "Enjeux de gouvernance",
        height=100,
        help="Décrivez les enjeux de gouvernance importants"
    )
    
    return {
        "environmental": environmental_issues,
        "social": social_issues,
        "governance": governance_issues
    }

def display_results(results: Dict):
    """Affiche les résultats de l'analyse"""
    st.header("📊 Analyse CSRD détaillée")
    
    if not results:
        st.warning("Aucun résultat à afficher")
        return
    
    # Debug: afficher la structure des résultats
    st.write("Structure des résultats reçus:", results)
    
    rows = []  # Pour l'export Excel
    
    # Définition des piliers
    pillars = {
        "environnement": "🌍 Environnement",
        "social": "👥 Social",
        "gouvernance": "⚖️ Gouvernance"
    }
    
    # Création des tabs pour les piliers
    tabs = st.tabs([name for _, name in pillars.items()])
    
    for (pilier_id, pilier_name), tab in zip(pillars.items(), tabs):
        if pilier_id in results:
            with tab:
                for enjeu, details in results[pilier_id].items():
                    st.subheader(f"🎯 Enjeu : {enjeu}")
                    
                    # On vérifie chaque clé avant de l'utiliser
                    if "description" in details:
                        st.markdown("### 📝 Description")
                        st.write(details["description"])
                    
                    if "impacts" in details:
                        st.markdown("### 💫 Impacts")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("#### ✅ Impacts positifs")
                            if "positifs" in details["impacts"]:
                                for impact in details["impacts"]["positifs"]:
                                    st.write(f"- {impact}")
                        with col2:
                            st.markdown("#### ❌ Impacts négatifs")
                            if "negatifs" in details["impacts"]:
                                for impact in details["impacts"]["negatifs"]:
                                    st.write(f"- {impact}")
                    
                    if "risques" in details:
                        st.markdown("### ⚠️ Risques")
                        if "niveau" in details["risques"]:
                            st.write(f"**Niveau de risque :** {details['risques']['niveau']}")
                        if "horizon" in details["risques"]:
                            st.write(f"**Horizon :** {details['risques']['horizon']}")
                        if "liste" in details["risques"]:
                            for risque in details["risques"]["liste"]:
                                st.write(f"- {risque}")
                        if "mesures_attenuation" in details["risques"]:
                            st.markdown("#### 🛡️ Mesures d'atténuation")
                            for mesure in details["risques"]["mesures_attenuation"]:
                                st.write(f"- {mesure}")
                    
                    if "opportunites" in details:
                        st.markdown("### 🎯 Opportunités")
                        if "potentiel" in details["opportunites"]:
                            st.write(f"**Potentiel :** {details['opportunites']['potentiel']}")
                        if "horizon" in details["opportunites"]:
                            st.write(f"**Horizon :** {details['opportunites']['horizon']}")
                        if "liste" in details["opportunites"]:
                            for opportunite in details["opportunites"]["liste"]:
                                st.write(f"- {opportunite}")
                        if "actions_saisie" in details["opportunites"]:
                            st.markdown("#### 🚀 Actions proposées")
                            for action in details["opportunites"]["actions_saisie"]:
                                st.write(f"- {action}")
                    
                    if "iros" in details:
                        st.markdown("### 📊 Indicateurs de Résultat (IRO)")
                        for iro in details["iros"]:
                            if isinstance(iro, dict):  # Vérifie si iro est un dictionnaire
                                st.markdown(f"#### 📌 {iro.get('indicateur', 'IRO')}")
                                if "description" in iro:
                                    st.write(f"**Description :** {iro['description']}")
                                if "methodologie" in iro:
                                    st.write(f"**Méthodologie :** {iro['methodologie']}")
                                if "frequence" in iro:
                                    st.write(f"**Fréquence :** {iro['frequence']}")
                                if "objectifs" in iro:
                                    st.markdown("**Objectifs :**")
                                    obj = iro["objectifs"]
                                    if "court_terme" in obj:
                                        st.write(f"- Court terme : {obj['court_terme']}")
                                    if "moyen_terme" in obj:
                                        st.write(f"- Moyen terme : {obj['moyen_terme']}")
                                    if "long_terme" in obj:
                                        st.write(f"- Long terme : {obj['long_terme']}")
                            else:  # Si iro est une chaîne simple
                                st.markdown(f"#### 📌 {iro}")
                            
                            # Ajout pour l'export Excel
                            row_data = {
                                "Pilier": pilier_name,
                                "Enjeu": enjeu
                            }
                            
                            if isinstance(iro, dict):
                                row_data.update({
                                    "IRO": iro.get('indicateur', ''),
                                    "Description IRO": iro.get('description', ''),
                                    "Méthodologie": iro.get('methodologie', ''),
                                    "Fréquence": iro.get('frequence', ''),
                                    "Objectif CT": iro.get('objectifs', {}).get('court_terme', ''),
                                    "Objectif MT": iro.get('objectifs', {}).get('moyen_terme', ''),
                                    "Objectif LT": iro.get('objectifs', {}).get('long_terme', '')
                                })
                            else:
                                row_data["IRO"] = str(iro)
                            
                            row_data.update({
                                "Niveau Risque": details.get('risques', {}).get('niveau', ''),
                                "Horizon Risque": details.get('risques', {}).get('horizon', ''),
                                "Potentiel Opportunité": details.get('opportunites', {}).get('potentiel', ''),
                                "Horizon Opportunité": details.get('opportunites', {}).get('horizon', '')
                            })
                            
                            rows.append(row_data)
                    
                    st.divider()
    
    # Export Excel
    if rows:
        df = pd.DataFrame(rows)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Analyse CSRD')
        
        st.download_button(
            label="📥 Télécharger l'analyse complète (Excel)",
            data=buffer.getvalue(),
            file_name=f"analyse_csrd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

def initialize_session_state():
    """Initialise les variables de session Streamlit"""
    if 'gpt' not in st.session_state:
        st.session_state.gpt = GPTInterface()
    if 'results' not in st.session_state:
        st.session_state.results = None

def main():
    st.title("🎯 Analyseur CSRD - Identification des IRO")
    
    initialize_session_state()
    
    with st.sidebar:
        st.header("ℹ️ Guide d'utilisation")
        st.write("""
        1. Décrivez votre entreprise en détail
        2. Identifiez vos enjeux prioritaires
        3. Lancez l'analyse pour obtenir des IRO personnalisés
        """)
        
        st.header("💡 Conseils")
        st.write("""
        - Soyez précis dans vos descriptions
        - N'hésitez pas à mentionner les spécificités
        - Pensez à long terme dans l'identification des enjeux
        """)
    
    # Sections principales
    company_profile = company_profile_section()
    priority_issues = priority_issues_section()
    
    # Bouton d'analyse
    if st.button("🔍 Lancer l'analyse"):
        if not all([company_profile["company_description"], 
                   company_profile["industry_sector"],
                   priority_issues["environmental"] or 
                   priority_issues["social"] or 
                   priority_issues["governance"]]):
            st.error("Veuillez remplir au moins la description de l'entreprise, le secteur d'activité et un enjeu prioritaire")
            return
        
        context = {
            **company_profile,
            "priority_issues": priority_issues
        }
        
        st.session_state.results = st.session_state.gpt.generate_iros(context)
        
    # Affichage des résultats
    if st.session_state.results:
        display_results(st.session_state.results)

if __name__ == "__main__":
    main()
