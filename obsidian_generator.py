# obsidian_generator.py - Générateur de notes Obsidian automatique
import os
import json
import re
from pathlib import Path
from typing import Dict, List
from datetime import datetime

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
        """Génère une note de type Learning"""
        content = f"""# {result['title']}

## Métadonnées
- **URL**: {result['url']}
- **Type**: Learning 🎓
- **Domaine**: [[{category_info.get('moc', 'Unknown MOC')}]]
- **Chaîne**: {result.get('channel', 'Unknown')}
- **Date d'ajout**: {result['processed_at'][:10]}
- **Dernière révision**: {result['processed_at'][:10]}

---

## Résumé Détaillé
{result.get('summary', 'Aucun résumé disponible')}
"""
        
        # Concepts clés
        concepts = result.get('concepts', [])
        if concepts:
            content += "\n## Concepts Clés\n"
            for concept in concepts:
                if isinstance(concept, dict):
                    name = concept.get('name', '')
                    definition = concept.get('definition', '')
                    content += f"- **{name}** - {definition}\n"
                else:
                    content += f"- **{concept}**\n"
        
        # Applications pratiques
        applications = result.get('applications', '')
        if applications:
            content += f"\n## Applications Pratiques\n{applications}\n"
        
        content += "\n## Notes Connectées\n<!-- Auto-générées -->\n\n---"
        
        # Tags
        content += f"\n*Tags: #video #learning #{category.replace('_', '-')}"
        
        # Mots-clés comme tags
        keywords = result.get('keywords', [])
        for keyword in keywords:
            if isinstance(keyword, str):
                clean_keyword = re.sub(r'[^a-zA-Z0-9]', '-', keyword.lower()).strip('-')
                if clean_keyword:
                    content += f" #{clean_keyword}"
        
        content += "*"
        
        return content
    
    def _generate_knowledge_note(self, result: Dict, category_info: Dict) -> str:
        """Génère une note de type Knowledge"""
        content = f"""# {result['title']}

## Métadonnées
- **URL**: {result['url']}
- **Type**: Knowledge 📰
- **Domaine**: [[{category_info.get('moc', 'Unknown MOC')}]]
- **Chaîne**: {result.get('channel', 'Unknown')}
- **Date d'ajout**: {result['processed_at'][:10]}

---

## Résumé
{result.get('summary', 'Aucun résumé disponible')}
"""
        
        # Points clés
        key_points = result.get('key_points', [])
        if key_points:
            content += "\n## Points Clés\n"
            for point in key_points:
                content += f"- {point}\n"
        
        # À retenir
        key_takeaway = result.get('key_takeaway', '')
        if key_takeaway:
            content += f"\n## À Retenir\n{key_takeaway}\n"
        
        content += "\n## Notes Connectées\n<!-- Auto-générées -->\n\n---"
        
        # Tags
        content += f"\n*Tags: #video #knowledge #{category.replace('_', '-')}"
        
        # Mots-clés comme tags
        keywords = result.get('keywords', [])
        for keyword in keywords:
            if isinstance(keyword, str):
                clean_keyword = re.sub(r'[^a-zA-Z0-9]', '-', keyword.lower()).strip('-')
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
            # Extraire la catégorie du résultat
            category = result.get('category')
            if not category or category not in self.categories:
                raise ValueError(f"Catégorie invalide: {category}")

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

            # Mettre à jour le MOC correspondant
            self._update_moc(category)

            return str(note_path)

        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde de la note: {str(e)}")
            raise
    
    def _update_moc(self, category: str):
        """Met à jour le MOC correspondant à la catégorie (optionnel)"""
        try:
            category_info = self.categories.get(category, {})
            moc_name = category_info.get('moc', 'Unknown MOC')
            moc_file = self.mocs_folder / f"{moc_name}.md"
            
            # Juste vérifier si le MOC existe, ne pas le créer automatiquement
            if moc_file.exists():
                print(f"✅ MOC trouvé: {moc_name}")
            else:
                print(f"ℹ️ MOC non trouvé: {moc_name} (OK si structure manuelle)")
            
            # Le MOC utilise Dataview donc se met à jour automatiquement
            
        except Exception as e:
            print(f"❌ Erreur vérification MOC: {e}")
    
    def _create_moc(self, category: str, moc_name: str):
        """Fonction désactivée - structure gérée manuellement"""
        print(f"ℹ️ Création MOC ignorée: {moc_name} (structure manuelle)")
    
    def bulk_generate_from_processed_data(self, processed_file_path: str) -> int:
        """Génère toutes les notes depuis un fichier de données processed"""
        try:
            with open(processed_file_path, 'r', encoding='utf-8') as f:
                processed_data = json.load(f)
            
            generated_count = 0
            
            for video_entry in processed_data.get('processed_videos', []):
                if video_entry.get('category') != 'skipped':
                    result = video_entry.get('result', {})
                    if result:
                        file_path = self.save_note(result)
                        if file_path:
                            generated_count += 1
            
            print(f"✅ {generated_count} notes générées dans Obsidian")
            return generated_count
            
        except Exception as e:
            print(f"❌ Erreur génération bulk: {e}")
            return 0
    
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