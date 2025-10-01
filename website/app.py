from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
    <head>
        <title>NFT Маркетплейс</title>
        <style>
            body { 
                font-family: Arial; 
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white; 
                text-align: center; 
                padding: 50px;
                margin: 0;
            }
            .container {
                background: rgba(255,255,255,0.1);
                padding: 40px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                max-width: 800px;
                margin: 0 auto;
            }
            h1 { color: #ffd700; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 NFT Маркетплейс</h1>
            <p><strong>Добро пожаловать на торговую площадку Discord бота!</strong></p>
            <p>🤖 Бот "Пехота Зенита" работает и готов к работе!</p>
            <p>📊 Статистика скоро будет доступна</p>
            <p>🛒 NFT маркетплейс в разработке</p>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
