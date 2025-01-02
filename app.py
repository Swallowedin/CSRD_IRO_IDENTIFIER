import streamlit as st
from typing import Dict, List
import json
from openai import OpenAI
import pandas as pd
from datetime import datetime
import io
import time

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
                    model="gpt-4o-mini",  # Utilisation du modèle le plus récent
                    messages=[
                        {"role": "system", "content": """Vous êtes un expert en reporting CSRD spécialisé dans l'identification des IRO. 
                        Votre rôle est d'analyser en profondeur TOUS les enjeux mentionnés et de fournir une analyse CSRD complète.
                        Les IRO (Indicateurs de Résultat Obligatoires) sont des indicateurs CSRD spécifiques, distincts des KPIs classiques.
                        
                        RÈGLES IMPORTANTES:
                        1. Vous DEVEZ traiter TOUS les enjeux mentionnés, sans exception
                        2. Respectez STRICTEMENT le format JSON demandé
                        3. Chaque IRO doit être un objet JSON valide avec TOUS les champs requis
                        4. Ne limitez pas le nombre d'enjeux traités"""},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,  # Augmentation légère de la créativité
                    max_tokens=4000,  # Augmentation de la limite de tokens
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                
                # Validation basique du format
                if not isinstance(result, dict):
                    raise ValueError("Le format de réponse n'est pas un dictionnaire JSON valide")
                
                for pilier, enjeux in result.items():
                    if not isinstance(enjeux, dict):
                        raise ValueError(f"Les enjeux du pilier {pilier} ne sont pas au bon format")
                        
                    for enjeu, details in enjeux.items():
                        if not isinstance(details.get('iros', []), list):
                            raise ValueError(f"Les IROs de l'enjeu {enjeu} ne sont pas au bon format")
                
                return result
                
            except Exception as e:
                st.error(f"Erreur lors de la génération des IRO: {str(e)}")
                return {}

    def _create_prompt(self, context: dict) -> str:
        return f"""
        En tant qu'expert CSRD, analysez TOUS les enjeux mentionnés dans les textes fournis.
        Pour CHAQUE enjeu mentionné, vous devez fournir une analyse détaillée et complète.

        PROFIL DE L'ENTREPRISE:
        {context['company_description']}

        SECTEUR D'ACTIVITÉ:
        {context['industry_sector']}

        MODÈLE D'AFFAIRES:
        {context['business_model']}

        CARACTÉRISTIQUES SPÉCIFIQUES:
        {context['specific_features']}

        ENJEUX À ANALYSER EN DÉTAIL:
        [IMPORTANT: Analyser TOUS les enjeux mentionnés ci-dessous]
        
        Environnement: {context['priority_issues']['environmental']}
        Social: {context['priority_issues']['social']}
        Gouvernance: {context['priority_issues']['governance']}

        Format JSON STRICT à respecter:
        {{
            "environnement": {{
                "nom_enjeu_1": {{
                    "description": "Description détaillée",
                    "impacts": {{
                        "positifs": ["impact1", "impact2"],
                        "negatifs": ["impact1", "impact2"]
                    }},
                    "risques": {{
                        "liste": ["risque1", "risque2"],
                        "niveau": "Élevé/Moyen/Faible",
                        "horizon": "Court/Moyen/Long terme",
                        "mesures_attenuation": ["mesure1", "mesure2"]
                    }},
                    "opportunites": {{
                        "liste": ["opportunité1", "opportunité2"],
                        "potentiel": "Élevé/Moyen/Faible",
                        "horizon": "Court/Moyen/Long terme",
                        "actions_saisie": ["action1", "action2"]
                    }},
                    "iros": [
                        {{
                            "indicateur": "Nom IRO",
                            "description": "Description IRO",
                            "methodologie": "Méthodologie",
                            "frequence": "Fréquence",
                            "objectifs": {{
                                "court_terme": "Objectif 1 an",
                                "moyen_terme": "Objectif 3 ans",
                                "long_terme": "Objectif 5 ans"
                            }}
                        }}
                    ]
                }}
            }},
            "social": {{ ... }},
            "gouvernance": {{ ... }}
        }}

        ATTENTION:
        - Vous DEVEZ traiter ABSOLUMENT TOUS les enjeux mentionnés
        - Chaque IRO doit être un objet JSON COMPLET avec TOUS les champs
        - Adaptez chaque analyse au contexte spécifique de l'entreprise
        - Soyez exhaustif dans l'analyse de chaque enjeu
        """

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

    # Option pour afficher les détails
    show_details = st.checkbox("Afficher les détails complets", value=True)
    
    # Définition des piliers
    pillars = {
        "environnement": "🌍 Environnement",
        "social": "👥 Social",
        "gouvernance": "⚖️ Gouvernance"
    }
    
    # Création des tabs avec compteurs
    tab_names = [f"{name} ({len(results.get(pid, {}))} enjeux)" 
                 for pid, name in pillars.items()]
    tabs = st.tabs(tab_names)
    
    rows = []  # Pour l'export Excel
    
    for (pilier_id, pilier_name), tab in zip(pillars.items(), tabs):
        if pilier_id in results:
            with tab:
                for enjeu, details in results[pilier_id].items():
                    st.subheader(f"🎯 Enjeu : {enjeu}")
                    
                    if show_details:
                        # Description
                        if "description" in details:
                            st.markdown("### 📝 Description")
                            st.write(details["description"])
                        
                        # Impacts
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
                        
                        # Risques
                        if "risques" in details:
                            with st.expander("⚠️ Risques et mesures d'atténuation", expanded=True):
                                if "niveau" in details["risques"]:
                                    st.write(f"**Niveau de risque :** {details['risques']['niveau']}")
                                if "horizon" in details["risques"]:
                                    st.write(f"**Horizon :** {details['risques']['horizon']}")
                                if "liste" in details["risques"]:
                                    st.markdown("**Risques identifiés :**")
                                    for risque in details["risques"]["liste"]:
                                        st.write(f"- {risque}")
                                if "mesures_attenuation" in details["risques"]:
                                    st.markdown("**🛡️ Mesures d'atténuation :**")
                                    for mesure in details["risques"]["mesures_attenuation"]:
                                        st.write(f"- {mesure}")
                        
                        # Opportunités
                        if "opportunites" in details:
                            with st.expander("🎯 Opportunités et actions", expanded=True):
                                if "potentiel" in details["opportunites"]:
                                    st.write(f"**Potentiel :** {details['opportunites']['potentiel']}")
                                if "horizon" in details["opportunites"]:
                                    st.write(f"**Horizon :** {details['opportunites']['horizon']}")
                                if "liste" in details["opportunites"]:
                                    st.markdown("**Opportunités identifiées :**")
                                    for opportunite in details["opportunites"]["liste"]:
                                        st.write(f"- {opportunite}")
                                if "actions_saisie" in details["opportunites"]:
                                    st.markdown("**🚀 Actions proposées :**")
                                    for action in details["opportunites"]["actions_saisie"]:
                                        st.write(f"- {action}")
                    
                    # IROs (toujours affichés)
                    if "iros" in details and isinstance(details["iros"], list):
                        st.markdown("### 📊 Indicateurs de Résultat Obligatoires (IRO)")
                        for idx, iro in enumerate(details["iros"], 1):
                            if not isinstance(iro, dict):
                                st.error(f"Format d'IRO invalide pour l'enjeu {enjeu}")
                                continue
                                
                            with st.expander(f"📌 IRO {idx}: {iro.get('indicateur', 'Non spécifié')}", expanded=True):
                                for field, label in [
                                    ('description', 'Description'),
                                    ('methodologie', 'Méthodologie'),
                                    ('frequence', 'Fréquence')
                                ]:
                                    if field in iro:
                                        st.write(f"**{label} :** {iro[field]}")
                                
                                if "objectifs" in iro and isinstance(iro["objectifs"], dict):
                                    st.markdown("**Objectifs :**")
                                    obj = iro["objectifs"]
                                    for term, label in [
                                        ('court_terme', 'Court terme'),
                                        ('moyen_terme', 'Moyen terme'),
                                        ('long_terme', 'Long terme')
                                    ]:
                                        if term in obj:
                                            st.write(f"- {label} : {obj[term]}")
                            
                            # Ajout pour l'export Excel
                            if isinstance(iro.get('objectifs'), dict):
                                row_data = {
                                    "Pilier": pilier_name,
                                    "Enjeu": enjeu,
                                    "IRO": iro.get('indicateur', ''),
                                    "Description IRO": iro.get('description', ''),
                                    "Méthodologie": iro.get('methodologie', ''),
                                    "Fréquence": iro.get('frequence', ''),
                                    "Objectif CT": iro['objectifs'].get('court_terme', ''),
                                    "Objectif MT": iro['objectifs'].get('moyen_terme', ''),
                                    "Objectif LT": iro['objectifs'].get('long_terme', ''),
                                    "Description Enjeu": details.get('description', ''),
                                    "Impacts Positifs": ", ".join(details.get('impacts', {}).get('positifs', [])),
                                    "Impacts Négatifs": ", ".join(details.get('impacts', {}).get('negatifs', [])),
                                    "Risques": ", ".join(details.get('risques', {}).get('liste', [])),
                                    "Niveau Risque": details.get('risques', {}).get('niveau', ''),
                                    "Horizon Risque": details.get('risques', {}).get('horizon', ''),
                                    "Mesures Atténuation": ", ".join(details.get('risques', {}).get('mesures_attenuation', [])),
                                    "Opportunités": ", ".join(details.get('opportunites', {}).get('liste', [])),
                                    "Potentiel Opportunité": details.get('opportunites', {}).get('potentiel', ''),
                                    "Horizon Opportunité": details.get('opportunites', {}).get('horizon', ''),
                                    "Actions Saisie": ", ".join(details.get('opportunites', {}).get('actions_saisie', []))
                                }
                                
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
