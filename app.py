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
                        {"role": "system", "content": """Vous êtes un expert en reporting CSRD spécialisé dans l'identification des IRO.
                        Votre rôle est d'analyser le profil de l'entreprise et de suggérer des IRO pertinents et personnalisés.
                        Soyez précis et justifiez vos choix en fonction des spécificités de l'entreprise."""},
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
        Analysez le profil d'entreprise suivant et identifiez les IRO les plus pertinents:

        PROFIL DE L'ENTREPRISE:
        {context['company_description']}

        SECTEUR D'ACTIVITÉ:
        {context['industry_sector']}

        MODÈLE D'AFFAIRES:
        {context['business_model']}

        CARACTÉRISTIQUES SPÉCIFIQUES:
        {context['specific_features']}

        ENJEUX PRIORITAIRES IDENTIFIÉS:
        {json.dumps(context['priority_issues'], indent=2, ensure_ascii=False)}

        Pour chaque enjeu identifié, fournissez une réponse JSON structurée avec:
        {{
            "pilier_esg": {{
                "enjeu": {{
                    "iros": ["liste d'IRO pertinents et spécifiques"],
                    "importance": "Haute/Moyenne/Basse",
                    "justification": "Explication détaillée de la pertinence par rapport au profil",
                    "méthodologie_collecte": "Comment collecter cet indicateur dans ce contexte spécifique",
                    "fréquence_mesure": "Fréquence recommandée de mesure",
                    "points_attention": "Points spécifiques à surveiller pour cet IRO dans ce contexte"
                }}
            }}
        }}
        """

def initialize_session_state():
    """Initialise les variables de session Streamlit"""
    if 'gpt' not in st.session_state:
        st.session_state.gpt = GPTInterface()
    if 'results' not in st.session_state:
        st.session_state.results = None

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
    st.header("📊 Résultats de l'analyse")
    
    if not results:
        st.warning("Aucun résultat à afficher")
        return
    
    # Création d'un DataFrame pour l'export
    rows = []
    
    for pilier, enjeux in results.items():
        st.subheader(f"Pilier : {pilier}")
        
        for enjeu, details in enjeux.items():
            with st.expander(f"Enjeu : {enjeu}"):
                st.write("**IROs recommandés :**")
                for iro in details["iros"]:
                    st.write(f"- {iro}")
                
                st.write(f"**Importance :** {details['importance']}")
                st.write(f"**Justification :** {details['justification']}")
                st.write(f"**Méthodologie de collecte :** {details['méthodologie_collecte']}")
                st.write(f"**Fréquence de mesure :** {details['fréquence_mesure']}")
                st.write(f"**Points d'attention :** {details['points_attention']}")
            
            # Ajout des données pour l'export
            for iro in details["iros"]:
                rows.append({
                    "Pilier": pilier,
                    "Enjeu": enjeu,
                    "IRO": iro,
                    "Importance": details["importance"],
                    "Justification": details["justification"],
                    "Méthodologie": details["méthodologie_collecte"],
                    "Fréquence": details["fréquence_mesure"],
                    "Points d'attention": details["points_attention"]
                })
    
    # Export Excel
    if rows:
        df = pd.DataFrame(rows)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Analyse IRO')
        
        st.download_button(
            label="📥 Télécharger les résultats (Excel)",
            data=buffer.getvalue(),
            file_name=f"analyse_iro_csrd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
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
