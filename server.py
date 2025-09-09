from flask import Flask, request, jsonify, render_template
import sqlite3
import requests
import json
import logging

app = Flask(__name__, template_folder='templates')
logging.basicConfig(level=logging.INFO)

# DMarket API settings
DM_API_ID = '3e113a3b-253c-40ea-9b16-5c5f89be9d4a'
DM_API_URL = "https://api.dmarket.com/exchange/v1/market/items"

def get_db_connection():
    conn = sqlite3.connect('skins.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/suggest')
def suggest_skins():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify(suggestions=[])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT name FROM skins WHERE name LIKE ? ORDER BY name LIMIT 10",
        ('%' + query + '%',)
    )
    
    suggestions = [row['name'] for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(suggestions=suggestions)

@app.route('/search')
def search_steam():
    item_name = request.args.get('item_name', '')
    if not item_name:
        return jsonify(error="Название предмета не указано"), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT steam_price_id, url_path, lowest_price FROM skins WHERE name = ?",
        (item_name,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return jsonify(error="Скин не найден в базе данных"), 404
    
    steam_url = f"https://steamcommunity.com/market/listings/730/{result['url_path']}"
    
    return jsonify({
        "item_name": item_name,
        "lowest_price": result['lowest_price'],
        "source": "Steam",
        "url": steam_url
    })

@app.route('/dmarket-search')
def dmarket_search():
    item_name = request.args.get('item_name', '')
    if not item_name:
        return jsonify(error="Название предмета не указано"), 400

    headers = {
        'X-App-Id': DM_API_ID,
        'Content-Type': 'application/json'
    }

    payload = {
        "title": item_name,
        "limit": 1
    }

    try:
        response = requests.post(
            f"{DM_API_URL}/search",
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get('objects'):
            return jsonify(error="Скин не найден на DMarket"), 404
        
        item = data['objects'][0]
        
        # DMarket prices are in USD cents
        lowest_price_usd = item.get('min_price', '0')
        lowest_price = f"${float(lowest_price_usd) / 100:.2f}"
        
        return jsonify({
            "item_name": item_name,
            "lowest_price": lowest_price,
            "source": "DMarket",
            "url": f"https://dmarket.com/ru/ingame-items/item-list/csgo-skins?title={item_name}"
        })

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from DMarket API: {e}")
        return jsonify(error=f"Ошибка при подключении к DMarket: {e}"), 500
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON from DMarket response.")
        return jsonify(error="Неверный ответ от DMarket"), 500
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return jsonify(error="Произошла непредвиденная ошибка"), 500

if __name__ == '__main__':
    app.run(debug=True)
