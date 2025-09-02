# obsidian_generator.py - Générateur de notes Obsidian automatique
import os
import json
import re
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import unicodedata

def clean_tag(text: str) -> str:
    """Nettoie un texte pour en faire un tag valide sans accents"""
    if not text:
        return ""
    
    # Supprimer les accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Convertir en minuscules
    text = text.lower()
    
    # Remplacer les espaces et caractères spéciaux par des tirets
    text = re.sub(r'[^a-zA-Z0-9]', '-', text)
    
    # Supprimer les tirets multiples et en début/fin
    text = re.sub(r'-+', '-', text).strip('-')
    
    return text

class ObsidianGenerator:
    def __init__(self, obsidian_vault_path: str):
        """
        Générateur de notes Obsidian pour le système YouTube
        
        Args:
            obsidian_vault_path: Chemin vers le coffre Obsidian
        """
        self.vault_path = Path(obsidian_vault_path)
        self.youtube_folder = self.vault_path / "YouTube Knowledge"
        self.videos_folder = self.youtube_folder / "Videos"
        self.mocs_folder = self.youtube_folder / "MOCs"
        
        # Créer la structure si elle n'existe pas
        self._create_folder_structure()
        
        # Categories mapping
        self.categories = {
            'ai_technique_learning': {
                'folder': 'IA Technique Learning',
                'moc': 'IA Technique MOC',
                'type': 'learning'
            },
            'ai_business_learning': {
                'folder': 'IA Business Learning', 
                'moc': 'IA Business MOC',
                'type': 'learning'
            },
            'tech_general_learning': {
                'folder': 'Tech General Learning',
                'moc': 'Tech General MOC',
                'type': 'learning'
            },
            'culture_g_learning': {
                'folder': 'Culture G Learning',
                'moc': 'Culture G MOC',
                'type': 'learning'
            },
            'tech_general_knowledge': {
                'folder': 'Tech General Knowledge',
                'moc': 'Tech General MOC',
                'type': 'knowledge'
            },
            'culture_g_knowledge': {
                'folder': 'Culture G Knowledge',
                'moc': 'Culture G MOC',
                'type': 'knowledge'
            }
        }
    
    def _create_folder_structure(self):
        """Vérifie que la structure Obsidian existe (sans la créer)"""
        if not self.youtube_folder.exists():
            print(f"⚠️ Attention: Dossier 'YouTube Knowledge' non trouvé dans {self.vault_path}")
            print("   Assure-toi que la structure Obsidian existe déjà")
        else:
            print(f"✅ Structure Obsidian trouvée dans: {self.vault_path}")
    
    def clean_filename(self, title: str) -> str:
        """Nettoie un titre pour en faire un nom de fichier valide"""
        # Remplacer caractères problématiques
        cleaned = re.sub(r'[<>:"/\\|?*]', '', title)
        # Limiter la longueur
        if len(cleaned) > 100:
            cleaned = cleaned[:100]
        return cleaned.strip()
    
    def generate_note_from_result(self, result: Dict) -> str:
        """Génère le contenu d'une note depuis un résultat de processing"""
        category = result['category']
        category_info = self.categories.get(category, {})
        processing_type = result.get('processing_type', 'knowledge')
        
        if processing_type == 'learning':
            return self._generate_learning_note(result, category_info)
        else:
            return self._generate_knowledge_note(result, category_info)
    
    def _generate_learning_note(self, result: Dict, category_info: Dict) -> str:
        """Génère une note de type Learning avec formatage amélioré"""
        # Extraire la catégorie depuis result
        category = result.get("category", "")

        content = f"""# {result['title']}

**URL**: {result['url']}  
**Type**: Learning 🎓  
**Domaine**: [[{category_info.get('moc', 'Unknown MOC')}]]  
**Chaîne**: {result.get('channel', 'Unknown')}  
**Date d'ajout**: {result['processed_at'][:10]}  
**Dernière révision**: {result['processed_at'][:10]}  

---

## Résumé Détaillé

    {result.get('summary', 'Aucun résumé disponible')}
    """

        # Concepts clés
        concepts = result.get("concepts", [])
        if concepts:
            content += "\n## Concepts Clés\n\n"
            for concept in concepts:
                if isinstance(concept, dict):
                    name = concept.get("name", "")
                    definition = concept.get("definition", "")
                    content += f"- **{name}** - {definition}\n"
                else:
                    content += f"- **{concept}**\n"

        # Applications pratiques
        applications = result.get("applications", "")
        if applications:
            content += f"\n## Applications Pratiques\n\n{applications}\n"

        content += "\n## Notes Connectées\n\n<!-- Auto-générées -->\n\n---"

        # Tags - avec nettoyage des accents
        clean_category = clean_tag(category)
        content += f"\n*Tags: #video #learning #{clean_category}"

        # Mots-clés comme tags
        keywords = result.get("keywords", [])
        for keyword in keywords:
            if isinstance(keyword, str):
                clean_keyword = clean_tag(keyword)
                if clean_keyword:
                    content += f" #{clean_keyword}"

        content += "*"

        return content


    def _generate_knowledge_note(self, result: Dict, category_info: Dict) -> str:
        """Génère une note de type Knowledge avec formatage amélioré"""
        # Extraire la catégorie depuis result
        category = result.get("category", "")

        content = f"""# {result['title']}

**URL**: {result['url']}  
**Type**: Knowledge 📰  
**Domaine**: [[{category_info.get('moc', 'Unknown MOC')}]]  
**Chaîne**: {result.get('channel', 'Unknown')}  
**Date d'ajout**: {result['processed_at'][:10]}  

---

## Résumé

    {result.get('summary', 'Aucun résumé disponible')}
    """

        # Points clés
        key_points = result.get("key_points", [])
        if key_points:
            content += "\n## Points Clés\n\n"
            for point in key_points:
                content += f"- {point}\n"

        # À retenir
        key_takeaway = result.get("key_takeaway", "")
        if key_takeaway:
            content += f"\n## À Retenir\n\n{key_takeaway}\n"

        content += "\n## Notes Connectées\n\n<!-- Auto-générées -->\n\n---"

        # Tags - avec nettoyage des accents
        clean_category = clean_tag(category)
        content += f"\n*Tags: #video #knowledge #{clean_category}"

        # Mots-clés comme tags
        keywords = result.get("keywords", [])
        for keyword in keywords:
            if isinstance(keyword, str):
                clean_keyword = clean_tag(keyword)
                if clean_keyword:
                    content += f" #{clean_keyword}"

        content += "*"

        return content

    
    def save_note(self, result: Dict) -> str:
        """
        Sauvegarde une note dans Obsidian
        
        Args:
            result: Dictionnaire contenant les informations de la note
        Returns:
            str: Chemin de la note créée
        """
        try:
            # Debug: afficher le contenu de result
            print(f"🔍 Debug result: {list(result.keys())}")
            
            # Extraire la catégorie du résultat
            category = result.get('category')
            print(f"🔍 Debug category extracted: {category}")
            
            if not category or category not in self.categories:
                raise ValueError(f"Catégorie invalide: {category}. Disponibles: {list(self.categories.keys())}")

            # Récupérer les infos de la catégorie
            category_info = self.categories[category]
            folder_name = category_info['folder']
            note_type = category_info['type']

            # Créer le dossier de catégorie s'il n'existe pas
            category_folder = self.videos_folder / folder_name
            category_folder.mkdir(parents=True, exist_ok=True)

            # Générer le contenu de la note selon le type
            if note_type == 'learning':
                note_content = self._generate_learning_note(result, category_info)
            else:
                note_content = self._generate_knowledge_note(result, category_info)

            # Créer le nom du fichier
            title = self.clean_filename(result.get('title', 'Note sans titre'))
            note_path = category_folder / f"{title}.md"

            # Sauvegarder la note
            note_path.write_text(note_content, encoding='utf-8')

            # CORRECTION: Ne plus appeler _update_moc car elle n'existe pas vraiment
            # Les MOCs se mettent à jour automatiquement via Dataview
            print(f"ℹ️ Note sauvegardée, MOC se met à jour automatiquement via Dataview")

            print(f"✅ Note sauvegardée: {note_path}")
            return str(note_path)

        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde de la note: {str(e)}")
            import traceback
            print(f"❌ Traceback complet: {traceback.format_exc()}")
            raise
    
    def get_stats(self) -> Dict:
        """Retourne des statistiques sur les notes générées"""
        stats = {
            'total_notes': 0,
            'by_category': {},
            'recent_notes': []
        }
        
        # Compter les notes par catégorie
        for category, category_info in self.categories.items():
            folder_path = self.videos_folder / category_info['folder']
            if folder_path.exists():
                notes = list(folder_path.glob('*.md'))
                count = len(notes)
                stats['by_category'][category] = count
                stats['total_notes'] += count
                
                # Ajouter les notes récentes
                for note_file in sorted(notes, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
                    stats['recent_notes'].append({
                        'name': note_file.stem,
                        'category': category,
                        'modified': datetime.fromtimestamp(note_file.stat().st_mtime).isoformat()
                    })
        
        return stats

# Fonction utilitaire
def auto_generate_obsidian_notes(vault_path: str, processed_file_path: str = "youtube_data/processed_videos.json"):
    """Fonction utilitaire pour générer automatiquement les notes"""
    generator = ObsidianGenerator(vault_path)
    
    if Path(processed_file_path).exists():
        count = generator.bulk_generate_from_processed_data(processed_file_path)
        print(f"📝 {count} notes générées dans {vault_path}")
    else:
        print(f"❌ Fichier non trouvé: {processed_file_path}")

if __name__ == "__main__":
    # Test du générateur
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Chemin vers ton coffre Obsidian (à configurer)
    OBSIDIAN_VAULT_PATH = os.getenv('OBSIDIAN_VAULT_PATH', './test_vault')
    
    print(f"🧪 Test du générateur Obsidian")
    print(f"📁 Vault path: {OBSIDIAN_VAULT_PATH}")
    
    generator = ObsidianGenerator(OBSIDIAN_VAULT_PATH)
    stats = generator.get_stats()
    
    print(f"📊 Stats: {stats}")