# youtube_liked_system.py - Système complet YouTube Liked Videos + Gemini
import os
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

# APIs
import google.generativeai as genai
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class YouTubeLikedSystem:
    def __init__(self):
        """Système complet pour traiter les vidéos likées YouTube"""
        
        # Configuration
        self.client_id = os.getenv('YOUTUBE_CLIENT_ID')
        self.client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('YOUTUBE_REDIRECT_URI', 'http://localhost:5000/oauth/callback')
        self.gemini_api_key = os.getenv('GOOGLE_AI_API_KEY')
        
        # Vérification des clés
        if not all([self.client_id, self.client_secret, self.gemini_api_key]):
            raise ValueError("Clés API manquantes dans .env")
        
        # Configuration Gemini
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        # Configuration OAuth - Scopes minimaux pour éviter les conflits
        self.scopes = [
            'https://www.googleapis.com/auth/youtube.readonly'
        ]
        
        # Stockage sécurisé
        self.data_dir = Path("youtube_data")
        self.data_dir.mkdir(exist_ok=True)
        self.token_file = self.data_dir / "oauth_token.pickle"
        self.processed_file = self.data_dir / "processed_videos.json"
        self.staging_file = self.data_dir / "staging_videos.json"
        
        # Variables
        self.youtube_service = None
        self.credentials = None
        
        # Catégories disponibles
        self.categories = {
            'ai_technique_learning': {
                'name': '🤖 IA Technique Learning',
                'type': 'learning',
                'folder': 'IA Technique Learning'
            },
            'ai_business_learning': {
                'name': '💼 IA Business Learning', 
                'type': 'learning',
                'folder': 'IA Business Learning'
            },
            'tech_general_learning': {
                'name': '💻 Tech General Learning',
                'type': 'learning', 
                'folder': 'Tech General Learning'
            },
            'culture_g_learning': {
                'name': '📚 Culture G Learning',
                'type': 'learning',
                'folder': 'Culture G Learning'
            },
            'tech_general_knowledge': {
                'name': '🔧 Tech General Knowledge',
                'type': 'knowledge',
                'folder': 'Tech General Knowledge'  
            },
            'culture_g_knowledge': {
                'name': '🌍 Culture G Knowledge',
                'type': 'knowledge',
                'folder': 'Culture G Knowledge'
            }
        }
    
    def get_auth_url(self) -> str:
        """Génère l'URL d'authentification OAuth"""
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
        
        # Accepter tous les scopes que Google veut donner
        all_scopes = [
            'https://www.googleapis.com/auth/youtube.readonly',
            'https://www.googleapis.com/auth/youtube',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.appdata', 
            'https://www.googleapis.com/auth/drive.photos.readonly',
            'https://www.googleapis.com/auth/calendar'
        ]
        
        flow = Flow.from_client_config(
            client_config,
            scopes=all_scopes  # Demander tous les scopes possibles
        )
        flow.redirect_uri = self.redirect_uri
        
        auth_url, state = flow.authorization_url(
            prompt='consent',
            access_type='offline',
            include_granted_scopes='true'
        )
        
        # Sauvegarder seulement les données nécessaires pour reconstruire le flow
        flow_data = {
            'client_config': client_config,
            'scopes': all_scopes,
            'redirect_uri': self.redirect_uri,
            'state': state
        }
        
        with open(self.data_dir / "temp_flow_data.json", 'w') as f:
            json.dump(flow_data, f)
        
        return auth_url
    
    def handle_oauth_callback(self, authorization_code: str) -> bool:
        """Traite le callback OAuth et sauvegarde les credentials"""
        try:
            # Récupérer les données du flow
            with open(self.data_dir / "temp_flow_data.json", 'r') as f:
                flow_data = json.load(f)
            
            # Reconstruire le flow
            flow = Flow.from_client_config(
                flow_data['client_config'],
                scopes=flow_data['scopes']
            )
            flow.redirect_uri = flow_data['redirect_uri']
            
            # Échanger le code contre un token - accepter tous les scopes
            flow.fetch_token(code=authorization_code)
            
            # Vérifier que nous avons au moins YouTube readonly
            granted_scopes = flow.credentials.scopes or []
            if 'https://www.googleapis.com/auth/youtube.readonly' not in granted_scopes:
                print(f"❌ Scope YouTube manquant dans: {granted_scopes}")
                return False
            
            print(f"✅ Scopes accordés: {len(granted_scopes)} scopes incluant YouTube")
            
            # Sauvegarder les credentials
            creds_data = {
                'token': flow.credentials.token,
                'refresh_token': flow.credentials.refresh_token,
                'token_uri': flow.credentials.token_uri,
                'client_id': flow.credentials.client_id,
                'client_secret': flow.credentials.client_secret,
                'scopes': flow.credentials.scopes,
                'expiry': flow.credentials.expiry.isoformat() if flow.credentials.expiry else None
            }
            
            with open(self.token_file.with_suffix('.json'), 'w') as f:
                json.dump(creds_data, f)
            
            # Nettoyer le fichier temporaire
            if (self.data_dir / "temp_flow_data.json").exists():
                os.remove(self.data_dir / "temp_flow_data.json")
            
            self.credentials = flow.credentials
            self._build_youtube_service()
            
            print("✅ Authentification réussie !")
            return True
            
        except Exception as e:
            print(f"❌ Erreur OAuth: {e}")
            # Nettoyer en cas d'erreur
            try:
                if (self.data_dir / "temp_flow_data.json").exists():
                    os.remove(self.data_dir / "temp_flow_data.json")
            except:
                pass
            return False
    
    def _load_credentials(self) -> bool:
        """Charge les credentials sauvegardés"""
        json_token_file = self.token_file.with_suffix('.json')
        
        # Essayer d'abord le format JSON (nouveau)
        if json_token_file.exists():
            try:
                with open(json_token_file, 'r') as f:
                    creds_data = json.load(f)
                
                from google.oauth2.credentials import Credentials
                
                # Reconstruire les credentials
                expiry = None
                if creds_data.get('expiry'):
                    from datetime import datetime
                    expiry = datetime.fromisoformat(creds_data['expiry'].replace('Z', '+00:00'))
                
                self.credentials = Credentials(
                    token=creds_data.get('token'),
                    refresh_token=creds_data.get('refresh_token'),
                    token_uri=creds_data.get('token_uri'),
                    client_id=creds_data.get('client_id'),
                    client_secret=creds_data.get('client_secret'),
                    scopes=creds_data.get('scopes'),
                    expiry=expiry
                )
                
                # Vérifier si le token a expiré
                if self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    # Sauvegarder le token rafraîchi
                    self._save_credentials_json()
                
                self._build_youtube_service()
                return True
                
            except Exception as e:
                print(f"❌ Erreur chargement credentials JSON: {e}")
        
        # Fallback sur l'ancien format pickle
        if self.token_file.exists():
            try:
                with open(self.token_file, 'rb') as f:
                    self.credentials = pickle.load(f)
                
                # Vérifier si le token a expiré
                if self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    # Migrer vers le format JSON
                    self._save_credentials_json()
                
                self._build_youtube_service()
                return True
                
            except Exception as e:
                print(f"❌ Erreur chargement credentials pickle: {e}")
        
        return False
    
    def _save_credentials_json(self):
        """Sauvegarde les credentials au format JSON"""
        try:
            creds_data = {
                'token': self.credentials.token,
                'refresh_token': self.credentials.refresh_token,
                'token_uri': self.credentials.token_uri,
                'client_id': self.credentials.client_id,
                'client_secret': self.credentials.client_secret,
                'scopes': self.credentials.scopes,
                'expiry': self.credentials.expiry.isoformat() if self.credentials.expiry else None
            }
            
            json_token_file = self.token_file.with_suffix('.json')
            with open(json_token_file, 'w') as f:
                json.dump(creds_data, f)
                
        except Exception as e:
            print(f"❌ Erreur sauvegarde credentials: {e}")
    
    def _build_youtube_service(self):
        """Construit le service YouTube API"""
        self.youtube_service = build('youtube', 'v3', credentials=self.credentials)
    
    def is_authenticated(self) -> bool:
        """Vérifie si l'utilisateur est authentifié"""
        return self._load_credentials() or self.youtube_service is not None
    
    def get_liked_videos(self, max_results: int = 50) -> List[Dict]:
        """Récupère les vidéos likées"""
        if not self.is_authenticated():
            raise Exception("Authentification requise")
        
        try:
            # Récupérer les vidéos likées
            request = self.youtube_service.videos().list(
                part="id,snippet,contentDetails",
                myRating="like",
                maxResults=max_results
            )
            response = request.execute()
            
            videos = []
            for item in response['items']:
                video_data = {
                    'video_id': item['id'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'][:500] + "..." if len(item['snippet']['description']) > 500 else item['snippet']['description'],
                    'channel': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'duration': item['contentDetails']['duration'],
                    'url': f"https://www.youtube.com/watch?v={item['id']}",
                    'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                    'detected_at': datetime.now().isoformat()
                }
                videos.append(video_data)
            
            return videos
            
        except HttpError as e:
            print(f"❌ Erreur YouTube API: {e}")
            return []
    
    def get_new_liked_videos(self) -> List[Dict]:
        """Récupère seulement les nouvelles vidéos likées"""
        all_videos = self.get_liked_videos()
        
        # Charger l'historique des vidéos traitées
        processed_ids = self._load_processed_video_ids()
        
        # Filtrer les nouvelles vidéos
        new_videos = [
            video for video in all_videos 
            if video['video_id'] not in processed_ids
        ]
        
        print(f"📊 {len(new_videos)} nouvelles vidéos likées détectées")
        return new_videos
    
    def _load_processed_video_ids(self) -> set:
        """Charge la liste des IDs de vidéos déjà traitées"""
        if not self.processed_file.exists():
            return set()
        
        try:
            with open(self.processed_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(video['video_id'] for video in data.get('processed_videos', []))
        except:
            return set()
    
    def save_to_staging(self, videos: List[Dict]):
        """Sauvegarde les vidéos dans le staging"""
        staging_data = {
            'videos': videos,
            'created_at': datetime.now().isoformat()
        }
        
        with open(self.staging_file, 'w', encoding='utf-8') as f:
            json.dump(staging_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 {len(videos)} vidéos sauvegardées en staging")
    
    def get_staging_videos(self) -> List[Dict]:
        """Récupère les vidéos en staging"""
        if not self.staging_file.exists():
            return []
        
        try:
            with open(self.staging_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('videos', [])
        except:
            return []
    
    def process_video_with_gemini(self, video_data: Dict, category: str) -> Dict:
        """Traite une vidéo avec Gemini selon sa catégorie"""
        category_info = self.categories.get(category)
        if not category_info:
            raise ValueError(f"Catégorie inconnue: {category}")
        
        processing_type = category_info['type']
        
        # Construire le prompt selon le type
        if processing_type == 'learning':
            prompt = self._build_learning_prompt(video_data)
        else:  # knowledge
            prompt = self._build_knowledge_prompt(video_data)
        
        try:
            # Appel à Gemini
            response = self.model.generate_content(prompt)
            
            # Parser la réponse
            result = self._parse_gemini_response(response.text, processing_type)
            
            # Ajouter les métadonnées
            result.update({
                'video_id': video_data['video_id'],
                'title': video_data['title'],
                'url': video_data['url'],
                'channel': video_data['channel'],
                'category': category,
                'processing_type': processing_type,
                'processed_at': datetime.now().isoformat()
            })
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur Gemini pour {video_data['title']}: {e}")
            return self._create_fallback_result(video_data, category, processing_type)
    
    def _build_learning_prompt(self, video_data: Dict) -> str:
        """Construit un prompt pour le contenu Learning"""
        return f"""Tu es un assistant spécialisé dans l'extraction de connaissances éducatives.

Analyse cette vidéo YouTube et crée un résumé structuré pour un apprentissage approfondi:

**Titre**: {video_data['title']}
**Chaîne**: {video_data['channel']} 
**Description**: {video_data['description']}

Réponds au format suivant:

## RÉSUMÉ DÉTAILLÉ
[Résumé de 3-4 paragraphes expliquant les concepts principaux]

## CONCEPTS CLÉS
- **Concept 1**: Définition courte
- **Concept 2**: Définition courte  
- **Concept 3**: Définition courte

## APPLICATIONS PRATIQUES
[Comment utiliser ces connaissances concrètement]

## MOTS-CLÉS
[5-7 mots-clés pour les tags et connexions]

Sois précis, éducatif et orienté apprentissage."""
    
    def _build_knowledge_prompt(self, video_data: Dict) -> str:
        """Construit un prompt pour le contenu Knowledge"""
        return f"""Tu es un assistant spécialisé dans l'extraction d'informations utiles.

Analyse cette vidéo YouTube et crée un résumé concis pour une connaissance générale:

**Titre**: {video_data['title']}
**Chaîne**: {video_data['channel']}
**Description**: {video_data['description']}

Réponds au format suivant:

## RÉSUMÉ
[2-3 phrases résumant l'essentiel]

## POINTS CLÉS
- Point important 1
- Point important 2
- Point important 3

## À RETENIR
[L'information la plus utile à retenir]

## MOTS-CLÉS
[3-5 mots-clés pour les tags]

Sois concis, factuel et orienté information utile."""
    
    def _parse_gemini_response(self, response_text: str, processing_type: str) -> Dict:
        """Parse la réponse de Gemini"""
        # Extraction simple par sections
        sections = {}
        current_section = None
        current_content = []
        
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('##'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line.replace('#', '').strip().lower()
                current_content = []
            elif line:
                current_content.append(line)
        
        # Ajouter la dernière section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        # Structurer selon le type
        if processing_type == 'learning':
            return {
                'summary': sections.get('résumé détaillé', ''),
                'concepts': self._extract_concepts(sections.get('concepts clés', '')),
                'applications': sections.get('applications pratiques', ''),
                'keywords': self._extract_keywords(sections.get('mots-clés', ''))
            }
        else:  # knowledge
            return {
                'summary': sections.get('résumé', ''),
                'key_points': self._extract_bullet_points(sections.get('points clés', '')),
                'key_takeaway': sections.get('à retenir', ''),
                'keywords': self._extract_keywords(sections.get('mots-clés', ''))
            }
    
    def _extract_concepts(self, concepts_text: str) -> List[Dict]:
        """Extrait les concepts depuis le texte"""
        concepts = []
        lines = concepts_text.split('\n')
        for line in lines:
            if line.strip().startswith('- **') or line.strip().startswith('**'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    concept_name = parts[0].replace('- **', '').replace('**', '').strip()
                    definition = parts[1].strip()
                    concepts.append({'name': concept_name, 'definition': definition})
        return concepts
    
    def _extract_bullet_points(self, points_text: str) -> List[str]:
        """Extrait les points clés"""
        points = []
        lines = points_text.split('\n')
        for line in lines:
            if line.strip().startswith('- '):
                points.append(line.replace('- ', '').strip())
        return points
    
    def _extract_keywords(self, keywords_text: str) -> List[str]:
        """Extrait les mots-clés"""
        # Nettoie et sépare les mots-clés
        keywords = keywords_text.replace('[', '').replace(']', '')
        keywords = [k.strip() for k in keywords.split(',') if k.strip()]
        return keywords[:7]  # Limiter à 7 max
    
    def _create_fallback_result(self, video_data: Dict, category: str, processing_type: str) -> Dict:
        """Crée un résultat de fallback en cas d'erreur Gemini"""
        base_result = {
            'video_id': video_data['video_id'],
            'title': video_data['title'], 
            'url': video_data['url'],
            'channel': video_data['channel'],
            'category': category,
            'processing_type': processing_type,
            'processed_at': datetime.now().isoformat(),
            'keywords': []
        }
        
        if processing_type == 'learning':
            base_result.update({
                'summary': f"Vidéo sur: {video_data['title']}",
                'concepts': [],
                'applications': 'À analyser manuellement'
            })
        else:
            base_result.update({
                'summary': f"Information sur: {video_data['title']}",
                'key_points': [],
                'key_takeaway': 'À analyser manuellement'
            })
        
        return base_result
    
    def mark_as_processed(self, video_id: str, category: str, result: Dict):
        """Marque une vidéo comme traitée"""
        # Charger l'historique existant
        processed_data = {'processed_videos': []}
        if self.processed_file.exists():
            try:
                with open(self.processed_file, 'r', encoding='utf-8') as f:
                    processed_data = json.load(f)
            except:
                pass
        
        # Ajouter la nouvelle vidéo traitée
        processed_entry = {
            'video_id': video_id,
            'category': category,
            'result': result,
            'processed_at': datetime.now().isoformat()
        }
        processed_data['processed_videos'].append(processed_entry)
        
        # Sauvegarder
        with open(self.processed_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
    
    def clear_staging(self):
        """Vide le staging"""
        if self.staging_file.exists():
            os.remove(self.staging_file)
        print("🧹 Staging vidé")
    
    def get_categories(self) -> Dict:
        """Retourne les catégories disponibles"""
        return self.categories
    
    def get_stats(self) -> Dict:
        """Retourne des statistiques du système"""
        processed_count = len(self._load_processed_video_ids())
        staging_count = len(self.get_staging_videos())
        
        return {
            'processed_videos': processed_count,
            'staging_videos': staging_count,
            'authenticated': self.is_authenticated(),
            'categories': list(self.categories.keys())
        }
    def unlike_video(self, video_id: str) -> bool:
        """
        Supprime le like d'une vidéo YouTube
        
        Args:
            video_id: L'ID de la vidéo à unliker
        Returns:
            bool: True si succès, False sinon
        """
        if not self.is_authenticated():
            print("❌ Authentification requise pour unliker")
            return False
        
        try:
            # Utiliser l'API YouTube pour supprimer le rating
            request = self.youtube_service.videos().rate(
                id=video_id,
                rating="none"  # Supprimer le like
            )
            request.execute()
            
            print(f"✅ Vidéo {video_id} unlikée avec succès")
            return True
            
        except HttpError as e:
            print(f"❌ Erreur lors du unlike de {video_id}: {e}")
            return False
        except Exception as e:
            print(f"❌ Erreur inattendue lors du unlike: {e}")
            return False