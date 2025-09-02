# app_liked_system.py - Application Flask pour le système YouTube Liked
from flask import Flask, request, jsonify, redirect, render_template_string
from flask_cors import CORS
from youtube_liked_system import YouTubeLikedSystem
from pathlib import Path
import os
from dotenv import load_dotenv
from obsidian_generator import ObsidianGenerator

load_dotenv()
app = Flask(__name__)
CORS(app)

# Initialiser le système
youtube_system = YouTubeLikedSystem()

# Template HTML simple pour la page de staging
STAGING_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>YouTube Liked Videos - Staging</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .video-card { 
            background: white; 
            padding: 20px; 
            margin: 15px 0; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            gap: 20px;
            transition: opacity 0.3s ease;
        }
        .video-info { flex: 1; }
        .video-title { font-size: 18px; font-weight: bold; margin-bottom: 8px; }
        .video-meta { color: #666; font-size: 14px; margin-bottom: 15px; }
        .categories { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px; }
        .category-option { 
            padding: 10px; 
            border: 2px solid #e0e0e0; 
            border-radius: 6px; 
            cursor: pointer; 
            text-align: center; 
            transition: all 0.2s;
        }
        .category-option:hover { border-color: #2196F3; background: #f0f8ff; }
        .category-option.selected { border-color: #2196F3; background: #e3f2fd; }
        .actions { margin-top: 15px; text-align: right; }
        .btn { 
            padding: 10px 20px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
            margin-left: 10px;
            font-size: 14px;
        }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .btn-primary { background: #2196F3; color: white; }
        .btn-secondary { background: #757575; color: white; }
        .btn-danger { background: #f44336; color: white; }
        .stats { background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .thumbnail { width: 120px; height: 90px; border-radius: 4px; object-fit: cover; }
        
        /* Notifications */
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        }
        .notification.success { background: #4CAF50; }
        .notification.info { background: #2196F3; }
        .notification.error { background: #f44336; }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 YouTube Liked Videos - Staging</h1>
        
        <div class="stats">
            <strong>📊 Stats:</strong> 
            {{ stats.staging_videos }} vidéos en staging | 
            {{ stats.processed_videos }} vidéos traitées | 
            Auth: {{ "✅" if stats.authenticated else "❌" }}
        </div>
        
        {% if not videos %}
            <div class="video-card">
                <div class="video-info">
                    <h3>Aucune vidéo en staging</h3>
                    <p>Utilisez <code>/sync</code> pour récupérer les nouvelles vidéos likées</p>
                </div>
            </div>
        {% endif %}
        
        {% for video in videos %}
        <div class="video-card" data-video-id="{{ video.video_id }}">
            <img src="{{ video.thumbnail }}" alt="Thumbnail" class="thumbnail">
            
            <div class="video-info">
                <div class="video-title">{{ video.title }}</div>
                <div class="video-meta">
                    📺 {{ video.channel }} | 
                    ⏱️ {{ video.duration }} | 
                    📅 {{ video.detected_at[:10] }}
                </div>
                
                <div class="categories">
                    {% for cat_id, cat_info in categories.items() %}
                    <div class="category-option" 
                         data-category="{{ cat_id }}"
                         onclick="selectCategory('{{ video.video_id }}', '{{ cat_id }}')">
                        {{ cat_info.name }}
                    </div>
                    {% endfor %}
                    <div class="category-option" 
                         data-category="skip"
                         onclick="selectCategory('{{ video.video_id }}', 'skip')" 
                         style="border-color: #f44336; color: #f44336;">
                        ❌ Skip
                    </div>
                </div>
                
                <div class="actions">
                    <button class="btn btn-secondary" onclick="previewVideo('{{ video.url }}')">👁️ Preview</button>
                    <button class="btn btn-primary" onclick="processVideo('{{ video.video_id }}')">✅ Process</button>
                    <button class="btn btn-danger" onclick="skipVideo('{{ video.video_id }}')">⏭️ Skip</button>
                </div>
            </div>
        </div>
        {% endfor %}
        
        {% if videos %}
        <div style="text-align: center; margin: 30px 0;">
            <button class="btn btn-danger" onclick="clearStaging()">🧹 Clear All Staging</button>
        </div>
        {% endif %}
    </div>

    <script>
        let selectedCategories = {};

        function selectCategory(videoId, category) {
            selectedCategories[videoId] = category;

            const videoCard = document.querySelector(`[data-video-id="${videoId}"]`);
            const options = videoCard.querySelectorAll('.category-option');
            options.forEach(opt => opt.classList.remove('selected'));

            const selectedOption = [...options].find(opt => opt.dataset.category === category);
            if (selectedOption) selectedOption.classList.add('selected');
        }

        function processVideo(videoId) {
            const category = selectedCategories[videoId];
            if (!category) {
                alert("⚠️ Sélectionnez une catégorie d'abord !");
                return;
            }

            // Désactiver le bouton pendant le traitement
            const processBtn = event.target;
            const originalText = processBtn.textContent;
            processBtn.disabled = true;
            processBtn.textContent = "🔄 Traitement...";

            fetch('/process-video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video_id: videoId, category: category })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Supprimer la carte vidéo de l'affichage
                    const videoCard = document.querySelector(`[data-video-id="${videoId}"]`);
                    if (videoCard) {
                        videoCard.style.transition = 'opacity 0.3s ease';
                        videoCard.style.opacity = '0';
                        setTimeout(() => videoCard.remove(), 300);
                    }
                    
                    // Notification de succès
                    showNotification("✅ Vidéo traitée avec succès !", "success");
                    
                    // Vérifier s'il reste des vidéos
                    setTimeout(() => {
                        const remainingCards = document.querySelectorAll('.video-card');
                        if (remainingCards.length <= 1) {
                            location.reload();
                        }
                    }, 500);
                } else {
                    alert("❌ Erreur: " + data.error);
                    // Réactiver le bouton en cas d'erreur
                    processBtn.disabled = false;
                    processBtn.textContent = originalText;
                }
            })
            .catch(err => {
                console.error("Erreur fetch:", err);
                alert("❌ Problème lors de l'appel au serveur.");
                // Réactiver le bouton en cas d'erreur
                processBtn.disabled = false;
                processBtn.textContent = originalText;
            });
        }

        function skipVideo(videoId) {
            if (!confirm("Êtes-vous sûr de vouloir ignorer cette vidéo ?")) return;

            // Désactiver visuellement la carte
            const videoCard = document.querySelector(`[data-video-id="${videoId}"]`);
            if (videoCard) {
                videoCard.style.opacity = '0.5';
                videoCard.style.pointerEvents = 'none';
            }

            fetch('/process-video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video_id: videoId, category: 'skip' })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Supprimer la carte vidéo de l'affichage
                    if (videoCard) {
                        videoCard.style.transition = 'opacity 0.3s ease';
                        videoCard.style.opacity = '0';
                        setTimeout(() => videoCard.remove(), 300);
                    }
                    
                    showNotification("⏭️ Vidéo ignorée", "info");
                    
                    // Vérifier s'il reste des vidéos
                    setTimeout(() => {
                        const remainingCards = document.querySelectorAll('.video-card');
                        if (remainingCards.length <= 1) {
                            location.reload();
                        }
                    }, 500);
                } else {
                    alert("❌ Erreur: " + data.error);
                    // Réactiver la carte en cas d'erreur
                    if (videoCard) {
                        videoCard.style.opacity = '1';
                        videoCard.style.pointerEvents = 'auto';
                    }
                }
            })
            .catch(err => {
                console.error("Erreur skip:", err);
                alert("❌ Problème lors du skip.");
                if (videoCard) {
                    videoCard.style.opacity = '1';
                    videoCard.style.pointerEvents = 'auto';
                }
            });
        }

        function showNotification(message, type) {
            // Créer une notification temporaire
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.textContent = message;
            
            document.body.appendChild(notification);
            
            // Supprimer après 3 secondes
            setTimeout(() => {
                notification.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }

        function previewVideo(url) {
            window.open(url, '_blank');
        }

        function clearStaging() {
            if (!confirm("Êtes-vous sûr de vouloir vider le staging ?")) return;

            fetch('/clear-staging', { method: 'POST' })
                .then(() => location.reload())
                .catch(err => {
                    console.error("Erreur clear-staging:", err);
                    alert("❌ Impossible de vider le staging.");
                });
        }
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    """Page d'accueil"""
    stats = youtube_system.get_stats()
    
    auth_status = '✅ Oui' if stats['authenticated'] else '❌ Non'
    staging_link = '<li><a href="/staging">📋 Gérer le Staging</a></li>' if stats['staging_videos'] > 0 else ''
    auth_link = '<li><a href="/auth/youtube">🔐 S\'authentifier YouTube</a></li>' if not stats['authenticated'] else ''
    
    return f"""
    <h1>🎬 YouTube Liked Videos System</h1>
    
    <h2>📊 Status</h2>
    <ul>
        <li>Authentifié: {auth_status}</li>
        <li>Vidéos en staging: {stats['staging_videos']}</li>
        <li>Vidéos traitées: {stats['processed_videos']}</li>
    </ul>
    
    <h2>🔗 Actions</h2>
    <ul>
        {staging_link}
        <li><a href="/sync">🔄 Sync Nouvelles Vidéos Likées</a></li>
        {auth_link}
        <li><a href="/stats">📊 Statistiques Détaillées</a></li>
    </ul>
    """

@app.route('/auth/youtube')
def auth_youtube():
    """Initie l'authentification YouTube"""
    try:
        auth_url = youtube_system.get_auth_url()
        return redirect(auth_url)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/oauth/callback')
def oauth_callback():
    """Callback OAuth YouTube"""
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "Code d'autorisation manquant"}), 400
    
    success = youtube_system.handle_oauth_callback(code)
    
    if success:
        return """
        <h2>✅ Authentification réussie !</h2>
        <p>Vous pouvez maintenant utiliser le système.</p>
        <a href="/">← Retour à l'accueil</a>
        """
    else:
        return jsonify({"error": "Échec de l'authentification"}), 500

@app.route('/sync')
def sync_liked_videos():
    """Synchronise les nouvelles vidéos likées"""
    try:
        if not youtube_system.is_authenticated():
            return redirect('/auth/youtube')
        
        # Récupérer les nouvelles vidéos
        new_videos = youtube_system.get_new_liked_videos()
        
        if new_videos:
            # Les sauvegarder en staging
            youtube_system.save_to_staging(new_videos)
            return redirect('/staging')
        else:
            return """
            <h2>📭 Aucune nouvelle vidéo</h2>
            <p>Toutes vos vidéos likées ont déjà été traitées.</p>
            <a href="/">← Retour à l'accueil</a>
            """
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/staging')
def staging_interface():
    """Interface de gestion du staging"""
    videos = youtube_system.get_staging_videos()
    categories = youtube_system.get_categories()
    stats = youtube_system.get_stats()
    
    return render_template_string(STAGING_TEMPLATE, 
                                videos=videos, 
                                categories=categories, 
                                stats=stats)

@app.route('/process-video', methods=['POST'])
def process_video():
    """Traite une vidéo selon sa catégorie"""
    try:
        # 1. Récupérer les données de la requête
        data = request.get_json()
        video_id = data.get('video_id')
        category = data.get('category')
        
        print(f"🔍 Debug process_video - video_id: {video_id}, category: {category}")
        
        if not video_id or not category:
            return jsonify({"success": False, "error": "Données manquantes"}), 400
        
        # 2. Gestion du skip
        if category == 'skip':
            youtube_system.mark_as_processed(video_id, 'skipped', {'status': 'skipped'})
            staging_videos = youtube_system.get_staging_videos()
            updated_videos = [v for v in staging_videos if v['video_id'] != video_id]
            youtube_system.save_to_staging(updated_videos)
            return jsonify({"success": True, "message": "Vidéo skippée"})
        
        # 3. Récupérer les données de la vidéo
        staging_videos = youtube_system.get_staging_videos()
        video_data = next((video for video in staging_videos if video['video_id'] == video_id), None)
        
        if not video_data:
            return jsonify({"success": False, "error": "Vidéo non trouvée en staging"}), 404
        
        # 4. Traitement avec Gemini
        result = youtube_system.process_video_with_gemini(video_data, category)
        print(f"🔍 Debug result from Gemini: {list(result.keys()) if result else 'None'}")
        
        if not result:
            return jsonify({"success": False, "error": "Erreur lors du traitement Gemini"}), 500
        
        # 5. IMPORTANT: S'assurer que la catégorie est dans le résultat AVANT save_note
        if 'category' not in result:
            result['category'] = category
            print(f"🔍 Debug: Ajout de category={category} au résultat")
        
        # 6. Génération et sauvegarde de la note Obsidian
        obsidian_generator = ObsidianGenerator(os.getenv('OBSIDIAN_VAULT_PATH'))
        try:
            print(f"🔍 Debug avant save_note: result contient {list(result.keys())}")
            obsidian_note_path = obsidian_generator.save_note(result)
        except Exception as e:
            print(f"❌ Erreur Obsidian détaillée: {str(e)}")
            import traceback
            print(f"❌ Traceback Obsidian: {traceback.format_exc()}")
            return jsonify({"success": False, "error": f"Erreur Obsidian: {str(e)}"}), 500
        
        # 7. Marquer comme traitée et mettre à jour le staging
        youtube_system.mark_as_processed(video_id, category, result)
        
        # 8. NOUVEAU: Supprimer le like YouTube si traitement réussi (optionnel)
        try:
            if category != 'skip':  # Ne pas unliker si c'est un skip
                unlike_success = youtube_system.unlike_video(video_id)
                if unlike_success:
                    print(f"✅ Like supprimé de YouTube pour {video_id}")
                else:
                    print(f"⚠️ Impossible de supprimer le like YouTube pour {video_id}")
        except Exception as unlike_error:
            print(f"⚠️ Erreur unlike (non bloquant): {unlike_error}")
        
        # 9. Retirer du staging
        updated_videos = [v for v in staging_videos if v['video_id'] != video_id]
        youtube_system.save_to_staging(updated_videos)
        
        # 10. Retourner le résultat
        return jsonify({
            "success": True, 
            "message": "Vidéo traitée avec succès",
            "result": result,
            "obsidian_note_path": obsidian_note_path,
            "category": category
        })
        
    except Exception as e:
        print(f"❌ Erreur processing générale: {str(e)}")
        import traceback
        print(f"❌ Traceback complet: {traceback.format_exc()}")
        return jsonify({
            "success": False, 
            "error": str(e),
            "details": {
                "video_id": video_id if 'video_id' in locals() else None,
                "category": category if 'category' in locals() else None
            }
        }), 500

@app.route('/clear-staging', methods=['POST'])
def clear_staging():
    """Vide le staging"""
    youtube_system.clear_staging()
    return jsonify({"success": True})

@app.route('/stats')
def get_stats():
    """Statistiques détaillées"""
    stats = youtube_system.get_stats()
    
    # Récupérer des stats plus détaillées
    if youtube_system.processed_file.exists():
        import json
        with open(youtube_system.processed_file, 'r', encoding='utf-8') as f:
            processed_data = json.load(f)
            
        # Stats par catégorie
        category_stats = {}
        for video in processed_data.get('processed_videos', []):
            cat = video.get('category', 'unknown')
            category_stats[cat] = category_stats.get(cat, 0) + 1
        
        stats['category_breakdown'] = category_stats
    
    return jsonify(stats)

@app.route('/api/staging', methods=['GET'])
def api_get_staging():
    """API endpoint pour récupérer le staging (pour intégrations)"""
    videos = youtube_system.get_staging_videos()
    categories = youtube_system.get_categories()
    
    return jsonify({
        "videos": videos,
        "categories": categories,
        "count": len(videos)
    })

@app.route('/api/sync', methods=['POST'])
def api_sync():
    """API endpoint pour synchroniser"""
    try:
        if not youtube_system.is_authenticated():
            return jsonify({"error": "Authentication required"}), 401
        
        new_videos = youtube_system.get_new_liked_videos()
        
        if new_videos:
            youtube_system.save_to_staging(new_videos)
        
        return jsonify({
            "success": True,
            "new_videos_count": len(new_videos),
            "videos": new_videos
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def generate_obsidian_note(result: dict) -> str:
    """Génère le contenu de la note Obsidian"""
    category_info = youtube_system.categories[result['category']]
    processing_type = result['processing_type']
    
    # Template basé sur le type
    if processing_type == 'learning':
        note_content = f"""# {result['title']}

## Métadonnées
- **URL**: {result['url']}
- **Type**: Learning 🎓
- **Domaine**: [[{category_info['folder']} MOC]]
- **Chaîne**: {result['channel']}
- **Date d'ajout**: {result['processed_at'][:10]}
- **Dernière révision**: {result['processed_at'][:10]}

---

## Résumé Détaillé
{result.get('summary', '')}

## Concepts Clés"""
        
        # Ajouter les concepts
        for concept in result.get('concepts', []):
            note_content += f"\n- **{concept['name']}** - {concept['definition']}"
        
        note_content += f"""

## Applications Pratiques
{result.get('applications', '')}

## Notes Connectées
<!-- Auto-générées -->

---
*Tags: #video #learning #{result['category'].replace('_', '-')}"""
        
        # Ajouter les mots-clés comme tags
        for keyword in result.get('keywords', []):
            clean_keyword = keyword.lower().replace(' ', '-').replace(',', '')
            note_content += f" #{clean_keyword}"
        
        note_content += "*"
    
    else:  # knowledge
        note_content = f"""# {result['title']}

## Métadonnées
- **URL**: {result['url']}
- **Type**: Knowledge 📰
- **Domaine**: [[{category_info['folder']} MOC]]
- **Chaîne**: {result['channel']}
- **Date d'ajout**: {result['processed_at'][:10]}

---

## Résumé
{result.get('summary', '')}

## Points Clés"""
        
        # Ajouter les points clés
        for point in result.get('key_points', []):
            note_content += f"\n- {point}"
        
        note_content += f"""

## À Retenir
{result.get('key_takeaway', '')}

## Notes Connectées
<!-- Auto-générées -->

---
*Tags: #video #knowledge #{result['category'].replace('_', '-')}"""
        
        # Ajouter les mots-clés comme tags
        for keyword in result.get('keywords', []):
            clean_keyword = keyword.lower().replace(' ', '-').replace(',', '')
            note_content += f" #{clean_keyword}"
        
        note_content += "*"
    
    return note_content

@app.route('/export-obsidian/<video_id>')
def export_obsidian(video_id):
    """Exporte une note traitée au format Obsidian"""
    try:
        # Charger les données traitées
        if not youtube_system.processed_file.exists():
            return jsonify({"error": "Aucune vidéo traitée"}), 404
        
        import json
        with open(youtube_system.processed_file, 'r', encoding='utf-8') as f:
            processed_data = json.load(f)
        
        # Trouver la vidéo
        video_result = None
        for video in processed_data.get('processed_videos', []):
            if video['video_id'] == video_id:
                video_result = video['result']
                break
        
        if not video_result:
            return jsonify({"error": "Vidéo non trouvée"}), 404
        
        # Générer le contenu Obsidian
        obsidian_content = generate_obsidian_note(video_result)
        
        return {
            "content": obsidian_content,
            "filename": f"{video_result['title']}.md",
            "category": video_result['category']
        }
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Démarrage du système YouTube Liked Videos...")
    print("📝 Endpoints disponibles:")
    print("   GET  / - Page d'accueil")
    print("   GET  /auth/youtube - Authentification") 
    print("   GET  /sync - Synchroniser les vidéos likées")
    print("   GET  /staging - Interface de gestion")
    print("   POST /process-video - Traiter une vidéo")
    print("   GET  /stats - Statistiques")
    print()
    print("🔑 Configuration requise dans .env:")
    print("   YOUTUBE_CLIENT_ID=...")
    print("   YOUTUBE_CLIENT_SECRET=...")
    print("   GOOGLE_AI_API_KEY=...")
    print()
    
    # Vérifier la config
    missing_keys = []
    if not os.getenv('YOUTUBE_CLIENT_ID'): missing_keys.append('YOUTUBE_CLIENT_ID')
    if not os.getenv('YOUTUBE_CLIENT_SECRET'): missing_keys.append('YOUTUBE_CLIENT_SECRET')
    if not os.getenv('GOOGLE_AI_API_KEY'): missing_keys.append('GOOGLE_AI_API_KEY')
    
    if missing_keys:
        print(f"❌ Clés manquantes: {', '.join(missing_keys)}")
    else:
        print("✅ Configuration OK")
    
    app.run(debug=True, port=5000)