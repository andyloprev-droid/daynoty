"""
Dashboard Web - Interfaz para revisar y publicar noticias en Facebook
"""
from flask import Flask, jsonify, render_template_string, request, redirect, session
from functools import wraps
import firebase_admin
from firebase_admin import credentials, firestore
import config
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'noticias-seguras-2026'

# Credenciales
DASHBOARD_USERNAME = "admin"
DASHBOARD_PASSWORD = "admin123"

# Initialize Firebase
try:
    os.environ['FIRESTORE_DATABASE_ID'] = 'andy1'
    cred = credentials.Certificate(config.GOOGLE_APPLICATION_CREDENTIALS)
    firebase_admin.initialize_app(cred, {
        'projectId': config.GOOGLE_CLOUD_PROJECT,
    })
except ValueError:
    pass

db = firestore.client()
collection = config.FIRESTORE_DATABASE


def login_required(f):
    """Decorador para proteger rutas"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


# HTML Template para LOGIN
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Dashboard de Noticias</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        h1 {
            text-align: center;
            color: #667eea;
            margin-bottom: 30px;
            font-size: 1.8em;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: bold;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #eee;
            border-radius: 6px;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: scale(1.02);
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            display: none;
        }
        .error.show {
            display: block;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>📰 Dashboard</h1>
        <div class="error" id="error"></div>
        <form method="POST">
            <div class="form-group">
                <label for="username">Usuario:</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>
            <div class="form-group">
                <label for="password">Contraseña:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Entrar</button>
        </form>
    </div>
</body>
</html>
"""

# HTML Template para el NUEVO dashboard
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Noticias</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 2.5em;
            color: #333;
            margin-bottom: 10px;
        }

        .header p {
            color: #666;
            font-size: 1.1em;
        }

        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 40px;
            justify-content: center;
            flex-wrap: wrap;
        }

        .stat-card {
            background: white;
            padding: 20px 30px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
            min-width: 150px;
        }

        .stat-card h3 {
            color: #667eea;
            font-size: 2em;
            margin-bottom: 5px;
        }

        .stat-card p {
            color: #666;
            font-size: 0.9em;
        }

        .news-container {
            display: flex;
            flex-direction: column;
            gap: 0;
        }

        .news-item {
            background: white;
            display: flex;
            flex-direction: row;
            border-bottom: 2px solid #eee;
            padding: 20px;
            gap: 20px;
            align-items: flex-start;
        }

        .news-item:last-child {
            border-bottom: none;
        }

        .news-image-container {
            flex-shrink: 0;
            width: 300px;
            height: 200px;
            position: relative;
            overflow: hidden;
            border-radius: 8px;
            background: #ddd;
        }

        .news-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .news-title-overlay {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(to top, rgba(0,0,0,0.8), transparent);
            color: white;
            padding: 20px;
            font-size: 1.3em;
            font-weight: bold;
            line-height: 1.3;
            display: flex;
            align-items: flex-end;
            min-height: 60px;
        }

        .news-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .news-title {
            color: #222;
            font-size: 1.3em;
            font-weight: bold;
            line-height: 1.3;
            margin-bottom: 12px;
        }

        .news-summary {
            color: #555;
            font-size: 0.95em;
            line-height: 1.6;
            margin-bottom: 15px;
            white-space: pre-line;  /* preserva saltos de linea del caption */
        }

        .news-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #999;
            font-size: 0.85em;
        }

        .news-date {
            color: #667eea;
            font-weight: bold;
        }

        .publish-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: transform 0.2s;
        }

        .publish-btn:hover {
            transform: scale(1.05);
        }

        .loading {
            text-align: center;
            color: #666;
            padding: 40px;
        }

        .no-articles {
            background: white;
            padding: 40px;
            text-align: center;
            color: #666;
            border-radius: 10px;
        }

        @media (max-width: 768px) {
            .news-item {
                flex-direction: column;
            }

            .news-image-container {
                width: 100%;
            }

            .header h1 {
                font-size: 1.8em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📰 Dashboard de Noticias</h1>
            <p>Últimas noticias extraídas</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3 id="total-news">0</h3>
                <p>Noticias</p>
            </div>
            <div class="stat-card">
                <h3 id="last-update">--:--</h3>
                <p>Última actualización</p>
            </div>
        </div>

        <div id="news-list" class="news-container">
            <div class="loading">Cargando noticias...</div>
        </div>
    </div>

    <script>
        const AUTO_REFRESH_INTERVAL = 30000;
        let articlesCache = [];

        async function loadNews() {
            try {
                const response = await fetch('/api/noticias');
                const articles = await response.json();

                articles.sort((a, b) => {
                    const dateA = new Date(b.processed_date || 0);
                    const dateB = new Date(a.processed_date || 0);
                    return dateA - dateB;
                });

                articlesCache = articles;
                renderNews(articles);
            } catch (error) {
                console.error('Error cargando noticias:', error);
            }
        }

        function renderNews(articles) {
            const newsList = document.getElementById('news-list');
            const totalNews = document.getElementById('total-news');

            if (articles.length === 0) {
                newsList.innerHTML = '<div class="no-articles">No hay noticias aun</div>';
                totalNews.textContent = '0';
                return;
            }

            totalNews.textContent = articles.length;

            newsList.innerHTML = articles.map((article, index) => {
                const date = new Date(article.processed_date || Date.now());
                const formattedDate = formatDate(date);
                const imageUrl = article.cloud_image_url || 'https://via.placeholder.com/300x200?text=Sin+imagen';

                return `
                    <div class="news-item">
                        <div class="news-image-container">
                            <img src="${imageUrl}" alt="" class="news-image">
                        </div>
                        <div class="news-content">
                            <div class="news-title">${escapeHtml(article.title)}</div>
                            <div class="news-summary">${escapeHtml(article.summary)}</div>
                            <div class="news-meta">
                                <span class="news-date">${formattedDate}</span>
                                <button class="publish-btn" data-index="${index}">Copiar</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            // Agregar event listeners a los botones
            document.querySelectorAll('.publish-btn').forEach(btn => {
                btn.addEventListener('click', handleCopyClick);
            });
        }

        function handleCopyClick(e) {
            const btn = e.currentTarget;
            const index = parseInt(btn.getAttribute('data-index'));
            const article = articlesCache[index];

            if (!article) return;

            const text = article.summary;
            copyToClipboard(text, btn);
        }

        function copyToClipboard(text, btn) {
            const originalText = btn.textContent;
            const originalBg = btn.style.background;

            const showSuccess = () => {
                btn.textContent = '✓ Copiado';
                btn.style.background = '#22c55e';
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.style.background = originalBg;
                }, 2000);
            };

            const showError = () => {
                btn.textContent = '✗ Error';
                btn.style.background = '#ef4444';
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.style.background = originalBg;
                }, 2000);
            };

            // Método 1: Clipboard API moderna
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text)
                    .then(showSuccess)
                    .catch(() => fallbackCopy(text, showSuccess, showError));
            } else {
                fallbackCopy(text, showSuccess, showError);
            }
        }

        function fallbackCopy(text, onSuccess, onError) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.top = '0';
            textarea.style.left = '0';
            textarea.style.width = '2em';
            textarea.style.height = '2em';
            textarea.style.padding = '0';
            textarea.style.border = 'none';
            textarea.style.outline = 'none';
            textarea.style.boxShadow = 'none';
            textarea.style.background = 'transparent';
            document.body.appendChild(textarea);
            textarea.focus();
            textarea.select();

            try {
                const successful = document.execCommand('copy');
                if (successful) {
                    onSuccess();
                } else {
                    onError();
                }
            } catch (err) {
                console.error('Error al copiar:', err);
                onError();
            }

            document.body.removeChild(textarea);
        }

        function formatDate(date) {
            const dateStr = date.toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
            const timeStr = date.toLocaleTimeString('es-ES', {
                hour: '2-digit',
                minute: '2-digit'
            });
            return dateStr + ' ' + timeStr;
        }

        function escapeHtml(text) {
            if (!text) return '';
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return String(text).replace(/[&<>"']/g, m => map[m]);
        }

        loadNews();
        setInterval(loadNews, AUTO_REFRESH_INTERVAL);
    </script>
</body>
</html>
"""


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if username == DASHBOARD_USERNAME and password == DASHBOARD_PASSWORD:
            session['logged_in'] = True
            return redirect('/')
        else:
            return render_template_string(LOGIN_TEMPLATE)

    return render_template_string(LOGIN_TEMPLATE)


@app.route('/')
@login_required
def dashboard():
    """Dashboard principal"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/noticias', methods=['GET'])
def api_noticias():
    """API para obtener noticias"""
    try:
        docs = db.collection(collection).stream()
        articles = []

        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            articles.append(data)

        return jsonify(articles)
    except Exception as e:
        logger.error(f"Error obteniendo noticias: {e}")
        return jsonify([]), 500


@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    logger.info("Iniciando Dashboard en http://localhost:5000")
    logger.info("Abre tu navegador y ve a: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
