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
        Analysez ce profil d'entreprise selon les exigences CSRD et fournissez une analyse détaillée de chaque enjeu mentionné :

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

        Pour chaque enjeu mentionné, fournissez une analyse structurée exactement comme suit :

        {{
            "environnement": {{
                "nom_de_l_enjeu": {{
                    "description": "Description détaillée de l'enjeu",
                    "impacts": {{
                        "positifs": [
                            "Liste des impacts positifs liés au modèle d'affaires"
                        ],
                        "negatifs": [
                            "Liste des impacts négatifs liés au modèle d'affaires"
                        ]
                    }},
                    "risques": {{
                        "liste": [
                            "Liste détaillée des risques identifiés"
                        ],
                        "niveau": "Élevé/Moyen/Faible",
                        "horizon": "Court/Moyen/Long terme",
                        "mesures_attenuation": [
                            "Liste des mesures d'atténuation proposées"
                        ]
                    }},
                    "opportunites": {{
                        "liste": [
                            "Liste détaillée des opportunités identifiées"
                        ],
                        "potentiel": "Élevé/Moyen/Faible",
                        "horizon": "Court/Moyen/Long terme",
                        "actions_saisie": [
                            "Actions proposées pour saisir les opportunités"
                        ]
                    }},
                    "iros": [
                        {{
                            "indicateur": "Nom de l'IRO",
                            "description": "Description de l'indicateur",
                            "methodologie": "Méthodologie de collecte et calcul",
                            "frequence": "Fréquence de mesure",
                            "objectifs": {{
                                "court_terme": "Objectif à 1 an",
                                "moyen_terme": "Objectif à 3 ans",
                                "long_terme": "Objectif à 5 ans"
                            }}
                        }}
                    ]
                }}
            }},
            "social": {{
                // même structure pour chaque enjeu social
            }},
            "gouvernance": {{
                // même structure pour chaque enjeu de gouvernance
            }}
        }}"""

def display_results(results: Dict):
    """Affiche les résultats de l'analyse avec la nouvelle structure"""
    st.header("📊 Analyse CSRD détaillée")
    
    if not results:
        st.warning("Aucun résultat à afficher")
        return
    
    rows = []  # Pour l'export Excel
    
    # Définition des icônes pour chaque pilier
    pillars = {
        "environnement": "🌍 Environnement",
        "social": "👥 Social",
        "gouvernance": "⚖️ Gouvernance"
    }
    
    for pilier_id, pilier_name in pillars.items():
        if pilier_id in results:
            with st.expander(pilier_name, expanded=True):
                for enjeu, details in results[pilier_id].items():
                    with st.expander(f"Enjeu : {enjeu}", expanded=True):
                        # Description
                        st.markdown("### 📝 Description")
                        st.write(details["description"])
                        
                        # Impacts
                        st.markdown("### 💫 Impacts")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("#### ✅ Impacts positifs")
                            for impact in details["impacts"]["positifs"]:
                                st.write(f"- {impact}")
                        with col2:
                            st.markdown("#### ❌ Impacts négatifs")
                            for impact in details["impacts"]["negatifs"]:
                                st.write(f"- {impact}")
                        
                        # Risques
                        st.markdown("### ⚠️ Risques")
                        st.write(f"**Niveau de risque :** {details['risques']['niveau']}")
                        st.write(f"**Horizon :** {details['risques']['horizon']}")
                        for risque in details["risques"]["liste"]:
                            st.write(f"- {risque}")
                        st.markdown("#### 🛡️ Mesures d'atténuation")
                        for mesure in details["risques"]["mesures_attenuation"]:
                            st.write(f"- {mesure}")
                        
                        # Opportunités
                        st.markdown("### 🎯 Opportunités")
                        st.write(f"**Potentiel :** {details['opportunites']['potentiel']}")
                        st.write(f"**Horizon :** {details['opportunites']['horizon']}")
                        for opportunite in details["opportunites"]["liste"]:
                            st.write(f"- {opportunite}")
                        st.markdown("#### 🚀 Actions proposées")
                        for action in details["opportunites"]["actions_saisie"]:
                            st.write(f"- {action}")
                        
                        # IROs
                        st.markdown("### 📊 Indicateurs de Résultat (IRO)")
                        for iro in details["iros"]:
                            with st.expander(f"📌 {iro['indicateur']}"):
                                st.write(f"**Description :** {iro['description']}")
                                st.write(f"**Méthodologie :** {iro['methodologie']}")
                                st.write(f"**Fréquence :** {iro['frequence']}")
                                st.markdown("**Objectifs :**")
                                st.write(f"- Court terme : {iro['objectifs']['court_terme']}")
                                st.write(f"- Moyen terme : {iro['objectifs']['moyen_terme']}")
                                st.write(f"- Long terme : {iro['objectifs']['long_terme']}")
                            
                            # Ajout pour l'export Excel
                            rows.append({
                                "Pilier": pilier_name,
                                "Enjeu": enjeu,
                                "IRO": iro['indicateur'],
                                "Description IRO": iro['description'],
                                "Méthodologie": iro['methodologie'],
                                "Fréquence": iro['frequence'],
                                "Objectif CT": iro['objectifs']['court_terme'],
                                "Objectif MT": iro['objectifs']['moyen_terme'],
                                "Objectif LT": iro['objectifs']['long_terme'],
                                "Niveau Risque": details['risques']['niveau'],
                                "Horizon Risque": details['risques']['horizon'],
                                "Potentiel Opportunité": details['opportunites']['potentiel'],
                                "Horizon Opportunité": details['opportunites']['horizon']
                            })
    
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
