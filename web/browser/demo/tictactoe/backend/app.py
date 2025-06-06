from flask import Flask, request, jsonify, send_from_directory
import json
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
GAMES_FILE = 'games.json'

def load_games():
    if not os.path.exists(GAMES_FILE):
        return []
    with open(GAMES_FILE, 'r') as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_games(games):
    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=2)

@app.route('/games', methods=['GET'])
def get_games():
    games = load_games()
    return jsonify(games)

@app.route('/games', methods=['POST'])
def add_game():
    games = load_games()
    data = request.json
    # Assign a new id
    new_id = (max([g['id'] for g in games], default=0) + 1) if games else 1
    data['id'] = new_id
    games.append(data)
    save_games(games)
    return jsonify({'success': True, 'id': new_id}), 201

@app.route('/games/<int:game_id>', methods=['DELETE'])
def delete_game(game_id):
    games = load_games()
    games = [g for g in games if g['id'] != game_id]
    save_games(games)
    return jsonify({'success': True})

@app.route('/games/<int:game_id>', methods=['GET'])
def get_game(game_id):
    games = load_games()
    for g in games:
        if g['id'] == game_id:
            return jsonify(g)
    return jsonify({'error': 'Game not found'}), 404

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    app.run(debug=True) 