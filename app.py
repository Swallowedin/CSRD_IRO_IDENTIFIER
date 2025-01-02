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
                # Premier appel pour la structure
                first_response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": """Vous êtes un expert en reporting CSRD. Pour chacun des enjeux mentionnés, 
                        identifiez UNIQUEMENT les grands domaines d'impact, sans les détailler. 
                        Votre rôle est d'établir une première structure qui sera enrichie ensuite."""},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.5
                )

                progress_bar.progress(33)

                # Deuxième appel pour enrichir chaque enjeu
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": """Vous êtes un expert en reporting CSRD spécialisé dans l'analyse exhaustive.
                        RÈGLE ABSOLUE: Pour chaque catégorie (impacts positifs, impacts négatifs, risques, opportunités), 
                        vous DEVEZ fournir entre 5 et 10 éléments.
                        La réponse sera rejetée si elle contient moins de 5 éléments par catégorie.
                        
                        Chaque élément doit être :
                        1. Détaillé et explicite (pas de descriptions vagues)
                        2. Spécifique à l'enjeu traité
                        3. Actionnable et mesurable quand applicable"""},
                        {"role": "assistant", "content": first_response.choices[0].message.content},
                        {"role": "user", "content": """Enrichissez CHAQUE enjeu avec au minimum 5 éléments par catégorie.
                        
                        FORMAT STRICT À RESPECTER:
                        - Au moins 5 impacts positifs par enjeu
                        - Au moins 5 impacts négatifs par enjeu
                        - Au moins 5 risques identifiés par enjeu
                        - Au moins 5 mesures d'atténuation par enjeu
                        - Au moins 5 opportunités par enjeu
                        - Au moins 5 actions proposées par enjeu
                        
                        ATTENTION: Je refuse catégoriquement toute réponse avec moins de 5 éléments par catégorie.
                        
                        Les datapoints CSRD doivent TOUS citer les paragraphes de référence de la CSRD."""}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7,
                    max_tokens=4000
                )

                progress_bar.progress(66)
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

                progress_bar.progress(100)

                # Validation stricte du nombre d'éléments
                for pilier, enjeux in result.items():
                    for enjeu, details in enjeux.items():
                        if len(details.get('impacts', {}).get('positifs', [])) < 5:
                            st.error(f"❌ Réponse rejetée : moins de 5 impacts positifs pour {enjeu}")
                            return self.generate_iros(context)  # Nouvelle tentative
                        if len(details.get('impacts', {}).get('negatifs', [])) < 5:
                            st.error(f"❌ Réponse rejetée : moins de 5 impacts négatifs pour {enjeu}")
                            return self.generate_iros(context)  # Nouvelle tentative
                        if len(details.get('risques', {}).get('liste', [])) < 5:
                            st.error(f"❌ Réponse rejetée : moins de 5 risques pour {enjeu}")
                            return self.generate_iros(context)  # Nouvelle tentative
                        if len(details.get('risques', {}).get('mesures_attenuation', [])) < 5:
                            st.error(f"❌ Réponse rejetée : moins de 5 mesures d'atténuation pour {enjeu}")
                            return self.generate_iros(context)  # Nouvelle tentative
                        if len(details.get('opportunites', {}).get('liste', [])) < 5:
                            st.error(f"❌ Réponse rejetée : moins de 5 opportunités pour {enjeu}")
                            return self.generate_iros(context)  # Nouvelle tentative
                        if len(details.get('opportunites', {}).get('actions_saisie', [])) < 5:
                            st.error(f"❌ Réponse rejetée : moins de 5 actions pour {enjeu}")
                            return self.generate_iros(context)  # Nouvelle tentative

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
                            "Premier impact positif détaillé",
                            "Deuxième impact positif détaillé",
                            "Troisième impact positif détaillé",
                            "Quatrième impact positif détaillé",
                            "Cinquième impact positif détaillé",
                            "Sixième impact positif si pertinent",
                            "Septième impact positif si pertinent",
                            "Huitième impact positif si pertinent",
                            "Neuvième impact positif si pertinent",
                            "Dixième impact positif si pertinent"
                        ],
                        "negatifs": [
                            "Premier impact négatif détaillé",
                            "Deuxième impact négatif détaillé",
                            "Troisième impact négatif détaillé",
                            "Quatrième impact négatif détaillé",
                            "Cinquième impact négatif détaillé",
                            "Sixième impact négatif si pertinent",
                            "Septième impact négatif si pertinent",
                            "Huitième impact négatif si pertinent",
                            "Neuvième impact négatif si pertinent",
                            "Dixième impact négatif si pertinent"
                        ]
                    }},
                    "risques": {{
                        "liste": [
                            "Premier risque identifié et détaillé",
                            "Deuxième risque identifié et détaillé",
                            "Troisième risque identifié et détaillé",
                            "Quatrième risque identifié et détaillé",
                            "Cinquième risque identifié et détaillé",
                            "Sixième risque si pertinent",
                            "Septième risque si pertinent",
                            "Huitième risque si pertinent",
                            "Neuvième risque si pertinent",
                            "Dixième risque si pertinent"
                        ],
                        "niveau": "Élevé/Moyen/Faible",
                        "horizon": "Court/Moyen/Long terme",
                        "mesures_attenuation": [
                            "Première mesure d'atténuation détaillée",
                            "Deuxième mesure d'atténuation détaillée",
                            "Troisième mesure d'atténuation détaillée",
                            "Quatrième mesure d'atténuation détaillée",
                            "Cinquième mesure d'atténuation détaillée",
                            "Sixième mesure si pertinente",
                            "Septième mesure si pertinente",
                            "Huitième mesure si pertinente",
                            "Neuvième mesure si pertinente",
                            "Dixième mesure si pertinente"
                        ]
                    }},
                    "opportunites": {{
                        "liste": [
                            "Première opportunité identifiée et détaillée",
                            "Deuxième opportunité identifiée et détaillée",
                            "Troisième opportunité identifiée et détaillée",
                            "Quatrième opportunité identifiée et détaillée",
                            "Cinquième opportunité identifiée et détaillée",
                            "Sixième opportunité si pertinente",
                            "Septième opportunité si pertinente",
                            "Huitième opportunité si pertinente",
                            "Neuvième opportunité si pertinente",
                            "Dixième opportunité si pertinente"
                        ],
                        "potentiel": "Élevé/Moyen/Faible",
                        "horizon": "Court/Moyen/Long terme",
                        "actions_saisie": [
                            "Première action proposée et détaillée",
                            "Deuxième action proposée et détaillée",
                            "Troisième action proposée et détaillée",
                            "Quatrième action proposée et détaillée",
                            "Cinquième action proposée et détaillée",
                            "Sixième action si pertinente",
                            "Septième action si pertinente",
                            "Huitième action si pertinente",
                            "Neuvième action si pertinente",
                            "Dixième action si pertinente"
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
        - Pour chaque enjeu, fournissez AU MINIMUM 5 éléments pour chaque catégorie
        - Le nombre d'éléments doit être adapté à l'importance de l'enjeu (jusqu'à 10 par catégorie)
        - Chaque élément doit être détaillé et spécifique à l'enjeu
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
