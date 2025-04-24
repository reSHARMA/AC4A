from flask import Flask, request, jsonify
from flask_cors import CORS
from policy_system.policy_system import PolicySystem

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173", "http://localhost:5000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

policy_system = PolicySystem()

@app.route('/get_attribute_trees', methods=['GET'])
def get_attribute_trees():
    try:
        trees = policy_system.export_attributes()
        return jsonify({'attribute_trees': trees})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/get_policies', methods=['GET'])
def get_policies():
    try:
        policies = policy_system.policy_rules
        return jsonify({'policies': policies})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/add_policy', methods=['POST'])
def add_policy():
    try:
        data = request.get_json()
        policy_system.add_policy(data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/delete_policy', methods=['POST'])
def delete_policy():
    try:
        data = request.get_json()
        success = policy_system.remove_policy(data)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/convert_to_text', methods=['POST'])
def convert_to_text():
    try:
        data = request.get_json()
        policy = {
            'granular_data': data['granular_data'],
            'data_access': data['data_access'],
            'position': data['position']
        }
        text = policy_system.text(policy=policy, mode="decl")
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 