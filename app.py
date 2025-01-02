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
    """Interface avec l'API GPT pour l'analyse CSRD"""
    
    def __init__(self):
        try:
            self.api_key = st.secrets["OPENAI_API_KEY"]
        except KeyError:
            st.error("❌ Clé API OpenAI non trouvée dans les secrets Streamlit.")
            st.info("💡 Ajoutez votre clé API dans les secrets Streamlit avec la clé 'OPENAI_API_KEY'")
            st.stop()
            
        self.client = OpenAI(api_key=self.api_key)

    def clean_json_string(self, json_str: str) -> str:
        """Nettoie une chaîne JSON potentiellement mal formée de manière plus robuste"""
        # Étape 1: Nettoyage des sauts de ligne et espaces problématiques
        lines = json_str.split('\n')
        cleaned_lines = []
        in_string = False
        escape_next = False
        
        for line in lines:
            cleaned_line = ''
            for char in line:
                if char == '\\' and not escape_next:
                    escape_next = True
                    cleaned_line += char
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    
                if in_string or char not in ('\n', '\r', '\t'):
                    cleaned_line += char
                    
                escape_next = False
                
            cleaned_lines.append(cleaned_line)
        
        cleaned = ' '.join(cleaned_lines)
        
        # Étape 2: Équilibrage des guillemets
        quote_positions = []
        backslash_positions = []
        for i, char in enumerate(cleaned):
            if char == '\\':
                backslash_positions.append(i)
            elif char == '"' and i-1 not in backslash_positions:
                quote_positions.append(i)
        
        # Si nombre impair de guillemets, ajout d'un guillemet final
        if len(quote_positions) % 2 != 0:
            last_quote = quote_positions[-1]
            next_brace = cleaned.find('}', last_quote)
            if next_brace != -1:
                cleaned = cleaned[:next_brace] + '"' + cleaned[next_brace:]
            else:
                cleaned += '"'
        
        # Étape 3: Équilibrage des accolades
        stack = []
        for i, char in enumerate(cleaned):
            if char == '{':
                stack.append(char)
            elif char == '}':
                if stack:
                    stack.pop()
                
        # Ajout des accolades manquantes
        cleaned += '}' * len(stack)
        
        # Étape 4: Validation finale de la structure
        try:
            # Tentative de parse pour vérifier la validité
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError as e:
            # Si erreur, tentative de correction supplémentaire
            if "Expecting ',' delimiter" in str(e):
                pos = int(str(e).split('char ')[-1].strip())
                cleaned = cleaned[:pos] + ',' + cleaned[pos:]
                
            # Vérification des objets non fermés
            if cleaned.count('{') > cleaned.count('}'):
                cleaned += '}' * (cleaned.count('{') - cleaned.count('}'))
            
            return cleaned

    def generate_iros(self, context: dict) -> dict:
        """Génère l'analyse IRO (Impact, Risques, Opportunités) via GPT"""
        prompt = self._create_prompt(context)
        
        with st.spinner('Analyse des impacts, risques et opportunités en cours...'):
            progress_bar = st.progress(0)
            try:
                # Simulation de progression
                for i in range(100):
                    time.sleep(0.02)
                    progress_bar.progress(i + 1)

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": """Vous êtes un expert en reporting CSRD spécialisé dans l'analyse exhaustive des impacts, risques et opportunités (IRO).

INSTRUCTIONS CRITIQUES POUR LES IRO:
- Pour CHAQUE enjeu, vous DEVEZ identifier entre 5 et 10 éléments dans CHACUNE des catégories suivantes :
  * Impacts positifs (minimum 5)
  * Impacts négatifs (minimum 5)
  * Risques identifiés (minimum 5)
  * Opportunités (minimum 5)
  * Mesures d'atténuation (minimum 5)
  * Actions de saisie d'opportunités (minimum 5)

- Il est STRICTEMENT INTERDIT de limiter à 2 ou 3 éléments par catégorie
- Plus l'enjeu est important, plus le nombre d'éléments identifiés doit être proche de 10
- Chaque élément doit être unique et pertinent pour l'enjeu analysé
- Les éléments doivent être détaillés et contextualisés

INSTRUCTIONS POUR LES DATAPOINTS:
- Identifiez tous les datapoints CSRD pertinents
- Citez systématiquement les paragraphes de la CSRD correspondants
- Incluez à la fois des KPIs quantitatifs et des exigences narratives"""},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7,
                    max_tokens=4000
                )

                raw_content = response.choices[0].message.content

                try:
                    # Premier essai avec le JSON brut
                    result = json.loads(raw_content)
                except json.JSONDecodeError as e:
                    st.warning(f"Tentative de réparation du JSON... Erreur initiale: {str(e)}")
                    
                    # Tentative de nettoyage et nouveau parse
                    cleaned_content = self.clean_json_string(raw_content)
                    try:
                        result = json.loads(cleaned_content)
                    except json.JSONDecodeError as e2:
                        st.error(f"Impossible de réparer le JSON: {str(e2)}")
                        st.error("Contenu JSON problématique:")
                        st.code(raw_content)
                        return {}

                # Validation du nombre d'éléments par catégorie
                for pilier, enjeux in result.items():
                    for enjeu, details in enjeux.items():
                        for categorie in ['impacts', 'risques', 'opportunites']:
                            if categorie == 'impacts':
                                for type_impact in ['positifs', 'negatifs']:
                                    if len(details.get(categorie, {}).get(type_impact, [])) < 5:
                                        st.warning(f"Attention: Nombre insuffisant d'{type_impact} pour l'enjeu {enjeu}")
                            elif categorie == 'risques':
                                if len(details.get(categorie, {}).get('liste', [])) < 5:
                                    st.warning(f"Attention: Nombre insuffisant de risques pour l'enjeu {enjeu}")
                                if len(details.get(categorie, {}).get('mesures_attenuation', [])) < 5:
                                    st.warning(f"Attention: Nombre insuffisant de mesures d'atténuation pour l'enjeu {enjeu}")
                            elif categorie == 'opportunites':
                                if len(details.get(categorie, {}).get('liste', [])) < 5:
                                    st.warning(f"Attention: Nombre insuffisant d'opportunités pour l'enjeu {enjeu}")
                                if len(details.get(categorie, {}).get('actions_saisie', [])) < 5:
                                    st.warning(f"Attention: Nombre insuffisant d'actions pour l'enjeu {enjeu}")

                return result

            except Exception as e:
                st.error(f"Erreur lors de la génération des IRO: {str(e)}")
                st.error("Détails de l'erreur pour le débogage:")
                st.exception(e)
                return {}
            finally:
                progress_bar.empty()

    def _create_prompt(self, context: dict) -> str:
        """Crée le prompt pour l'analyse CSRD"""
        return f"""
        En tant qu'expert CSRD, analysez TOUS les enjeux mentionnés dans les textes fournis.
        Pour CHAQUE enjeu mentionné, vous devez fournir une analyse complète des impacts, risques et opportunités.

        PROFIL DE L'ENTREPRISE:
        {context['company_description']}

        SECTEUR D'ACTIVITÉ:
        {context['industry_sector']}

        MODÈLE D'AFFAIRES:
        {context['business_model']}

        CARACTÉRISTIQUES SPÉCIFIQUES:
        {context['specific_features']}

        ENJEUX À ANALYSER:
        [IMPORTANT: Analyser TOUS les enjeux mentionnés ci-dessous]
        
        Environnement: {context['priority_issues']['environmental']}
        Social: {context['priority_issues']['social']}
        Gouvernance: {context['priority_issues']['governance']}

        Format JSON STRICT à respecter:
        {{
            "environnement": {{
                "nom_enjeu_1": {{
                    "description": "Description détaillée de l'enjeu",
                    "impacts": {{
                        "positifs": [
                            "impact1",
                            "impact2",
                            "impact3",
                            "impact4",
                            "impact5",
                            "...jusqu'à 10 impacts positifs pertinents"
                        ],
                        "negatifs": [
                            "impact1",
                            "impact2",
                            "impact3",
                            "impact4",
                            "impact5",
                            "...jusqu'à 10 impacts négatifs pertinents"
                        ]
                    }},
                    "risques": {{
                        "liste": [
                            "risque1",
                            "risque2",
                            "risque3",
                            "risque4",
                            "risque5",
                            "...jusqu'à 10 risques pertinents"
                        ],
                        "niveau": "Élevé/Moyen/Faible",
                        "horizon": "Court/Moyen/Long terme",
                        "mesures_attenuation": [
                            "mesure1",
                            "mesure2",
                            "mesure3",
                            "mesure4",
                            "mesure5",
                            "...jusqu'à 10 mesures pertinentes"
                        ]
                    }},
                    "opportunites": {{
                        "liste": [
                            "opportunité1",
                            "opportunité2",
                            "opportunité3",
                            "opportunité4",
                            "opportunité5",
                            "...jusqu'à 10 opportunités pertinentes"
                        ],
                        "potentiel": "Élevé/Moyen/Faible",
                        "horizon": "Court/Moyen/Long terme",
                        "actions_saisie": [
                            "action1",
                            "action2",
                            "action3",
                            "action4",
                            "action5",
                            "...jusqu'à 10 actions pertinentes"
                        ]
                    }},
                    "datapoints_csrd": [
                        {{
                            "indicateur": "Nom du datapoint",
                            "type": "KPI quantitatif ou texte narratif",
                            "reference_csrd": "Paragraphe CSRD correspondant",
                            "description": "Description du datapoint",
                            "methodologie": "Méthodologie de collecte/calcul",
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
            "social": {{ ... }},
            "gouvernance": {{ ... }}
        }}

        ATTENTION:
        - Vous DEVEZ traiter ABSOLUMENT TOUS les enjeux mentionnés
        - Pour chaque enjeu, fournissez AU MINIMUM 5 éléments pour chaque liste (impacts, risques, opportunités)
        - Le nombre d'éléments doit être adapté à l'importance de l'enjeu (jusqu'à 10 par catégorie)
        - Chaque élément doit être unique et pertinent pour l'enjeu
        - Citez les paragraphes CSRD pour chaque datapoint
        - Ne limitez PAS le nombre d'enjeux traités
        - Assurez-vous que la réponse est un JSON valide et complet
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
    show_details = st.checkbox("Afficher/Masquer tous les détails", value=True)
    
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
                    with st.expander(f"🎯 Enjeu : {enjeu}", expanded=show_details):
                        # Description
                        if "description" in details:
                            st.markdown("### 📝 Description")
                            st.write(details["description"])
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Impacts
                            st.markdown("### 💫 Impacts")
                            if "impacts" in details:
                                st.markdown("#### ✅ Impacts positifs")
                                if "positifs" in details["impacts"]:
                                    for impact in details["impacts"]["positifs"]:
                                        st.write(f"- {impact}")
                                
                                st.markdown("#### ❌ Impacts négatifs")
                                if "negatifs" in details["impacts"]:
                                    for impact in details["impacts"]["negatifs"]:
                                        st.write(f"- {impact}")
                            
                            # Risques
                            st.markdown("### ⚠️ Risques")
                            if "risques" in details:
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
                        
                        with col2:
                            # Opportunités
                            st.markdown("### 🎯 Opportunités")
                            if "opportunites" in details:
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
                            
                            # Datapoints CSRD
                            if "datapoints_csrd" in details and isinstance(details["datapoints_csrd"], list):
                                st.markdown("### 📊 Datapoints CSRD conseillés")
                                for idx, datapoint in enumerate(details["datapoints_csrd"], 1):
                                    if not isinstance(datapoint, dict):
                                        st.error(f"Format de datapoint invalide pour l'enjeu {enjeu}")
                                        continue
                                    
                                    st.markdown(f"#### 📌 Datapoint {idx}: {datapoint.get('indicateur', 'Non spécifié')}")
                                    st.write(f"**Type :** {datapoint.get('type', 'Non spécifié')}")
                                    for field, label in [
                                        ('description', 'Description'),
                                        ('methodologie', 'Méthodologie'),
                                        ('frequence', 'Fréquence')
                                    ]:
                                        if field in datapoint:
                                            st.write(f"**{label} :** {datapoint[field]}")
                                    
                                    if "objectifs" in datapoint and isinstance(datapoint["objectifs"], dict):
                                        st.markdown("**Objectifs :**")
                                        obj = datapoint["objectifs"]
                                        for term, label in [
                                            ('court_terme', 'Court terme'),
                                            ('moyen_terme', 'Moyen terme'),
                                            ('long_terme', 'Long terme')
                                        ]:
                                            if term in obj:
                                                st.write(f"- {label} : {obj[term]}")

                                    # Ajout pour l'export Excel
                                    if isinstance(datapoint.get('objectifs'), dict):
                                        row_data = {
                                            "Pilier": pilier_name,
                                            "Enjeu": enjeu,
                                            "Datapoint": datapoint.get('indicateur', ''),
                                            "Type": datapoint.get('type', ''),
                                            "Description Datapoint": datapoint.get('description', ''),
                                            "Méthodologie": datapoint.get('methodologie', ''),
                                            "Fréquence": datapoint.get('frequence', ''),
                                            "Objectif CT": datapoint['objectifs'].get('court_terme', ''),
                                            "Objectif MT": datapoint['objectifs'].get('moyen_terme', ''),
                                            "Objectif LT": datapoint['objectifs'].get('long_terme', ''),
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
