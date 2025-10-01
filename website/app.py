from flask import Flask, render_template, jsonify
import aiosqlite
import asyncio
import os

app = Flask(__name__)

# Путь к базе данных бота
DB_PATH = "../data/bot.db"

async def get_user_data(user_id):
    """Получить данные пользователя из базы бота"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT balance, level FROM users WHERE user_id = ?', (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {"balance": result[0], "level": result[1]}
                return None
    except Exception as e:
        print(f"Ошибка базы: {e}")
        return None

async def get_marketplace_nfts():
    """Получить NFT с маркетплейса"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT ni.id, nc.name, ni.token_id, ni.metadata, ni.price
                FROM nft_items ni
                JOIN nft_collections nc ON ni.collection_id = nc.id
                WHERE ni.for_sale = TRUE LIMIT 20
            ''') as cursor:
                nfts = await cursor.fetchall()
                result = []
                for nft in nfts:
                    nft_id, col_name, token_id, metadata, price = nft
                    result.append({
                        "id": nft_id,
                        "name": f"{col_name} #{token_id}",
                        "price": price,
                        "collection": col_name
                    })
                return result
    except Exception as e:
        print(f"Ошибка NFT: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/user/<int:user_id>')
def user_data(user_id):
    data = asyncio.run(get_user_data(user_id))
    return jsonify(data or {"error": "User not found"})

@app.route('/api/marketplace')
def marketplace():
    nfts = asyncio.run(get_marketplace_nfts())
    return jsonify(nfts)

@app.route('/api/stats')
def stats():
    return jsonify({
        "total_users": 150,
        "total_nfts": 45,
        "total_volume": 12500
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
