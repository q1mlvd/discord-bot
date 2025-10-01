from flask import Flask, request, jsonify
import aiosqlite
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['user_id']
        except:
            return jsonify({'error': 'Token is invalid'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/user/<int:user_id>', methods=['GET'])
@token_required
def get_user_data(current_user, user_id):
    # Получение данных пользователя
    async def get_data():
        async with aiosqlite.connect('data/bot.db') as db:
            async with db.execute('SELECT balance, level FROM users WHERE user_id = ?', (user_id,)) as cursor:
                user = await cursor.fetchone()
                if user:
                    return {'balance': user[0], 'level': user[1]}
                return None
    
    user_data = asyncio.run(get_data())
    if user_data:
        return jsonify(user_data)
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/open_case', methods=['POST'])
@token_required
def open_case(current_user):
    data = request.json
    case_id = data.get('case_id')
    
    # Логика открытия кейса
    success, reward = asyncio.run(bot.case_system.open_case(current_user, case_id))
    
    return jsonify({
        'success': success,
        'reward': reward
    })

@app.route('/api/nft/marketplace', methods=['GET'])
def get_marketplace():
    nfts = asyncio.run(bot.nft_system.get_marketplace_nfts())
    return jsonify({'nfts': nfts})

if __name__ == '__main__':
    app.run(debug=True)
