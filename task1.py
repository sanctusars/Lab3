import json
import os
from flask import Flask, jsonify, request, abort, make_response
from flask_httpauth import HTTPBasicAuth

app = Flask(__name__)
auth = HTTPBasicAuth()

DATA_FILE = 'catalog.json'
USERS_FILE = 'users.txt'

# Допоміжні функції для роботи з файлами

def load_catalog():
    # Підвантаження каталогу товарів з файлу
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_catalog(data):
    # Збереження каталогу товарів у файл
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_users():
    # Підвантаження даних користувачів з файлу
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    username, password = line.split(':', 1)
                    users[username] = password
    return users

# Автентификація

@auth.verify_password
def verify_password(username, password):
    users = load_users()
    if username in users and users[username] == password:
        return username
    return None

@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)

# Опрацювання API (endpoints)

# /items GET: Отримати інфо про всі товари
@app.route('/items', methods=['GET'])
@auth.login_required
def get_items():
    catalog = load_catalog()
    return jsonify(catalog)

# /items POST: Додати новий товар
@app.route('/items', methods=['POST'])
@auth.login_required
def create_item():
    if not request.json:
        abort(400, description="Request body must be JSON")
    
    required_fields = ['id', 'name', 'price', 'weight']
    if not all(field in request.json for field in required_fields):
        abort(400, description=f"Missing required fields. Must contain: {required_fields}")

    catalog = load_catalog()
    
    # Унікальність ID
    new_id = request.json['id']
    if any(item['id'] == new_id for item in catalog):
        abort(400, description=f"Item with id {new_id} already exists")

    item = {
        'id': new_id,
        'name': request.json['name'],
        'price': request.json['price'],
        'weight': request.json['weight']
    }
    
    catalog.append(item)
    save_catalog(catalog)
    
    return jsonify(item), 201

# /items/<id> GET: Отримати інфо про конкретний товар
@app.route('/items/<int:item_id>', methods=['GET'])
@auth.login_required
def get_item(item_id):
    catalog = load_catalog()
    item = next((item for item in catalog if item['id'] == item_id), None)
    if item is None:
        abort(404, description="Item not found")
    return jsonify(item)

# /items/<id> PUT: Оновлення товару
@app.route('/items/<int:item_id>', methods=['PUT'])
@auth.login_required
def update_item(item_id):
    if not request.json:
        abort(400, description="Request body must be JSON")

    catalog = load_catalog()
    item = next((item for item in catalog if item['id'] == item_id), None)
    if item is None:
        abort(404, description="Item not found")

    # Обновляем поля, если они присутствуют в запросе
    item['name'] = request.json.get('name', item['name'])
    item['price'] = request.json.get('price', item['price'])
    item['weight'] = request.json.get('weight', item['weight'])

    save_catalog(catalog)
    return jsonify(item)

# /items/<id> DELETE: Видалення товару
@app.route('/items/<int:item_id>', methods=['DELETE'])
@auth.login_required
def delete_item(item_id):
    catalog = load_catalog()
    item = next((item for item in catalog if item['id'] == item_id), None)
    if item is None:
        abort(404, description="Item not found")
    
    catalog.remove(item)
    save_catalog(catalog)
    return jsonify({'result': True, 'message': f'Item {item_id} deleted'})

# Опрацювання помилки 404
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found', 'message': error.description}), 404)

# Опрацювання помилки 400
@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request', 'message': error.description}), 400)

if __name__ == '__main__':
    # Створення файлу каталога, якщо його немає
    if not os.path.exists(DATA_FILE):
        save_catalog([])
    
    app.run(port=8000)