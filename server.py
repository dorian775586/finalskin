import os
import psycopg2
import requests
import urllib.parse
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Получение URL базы данных из переменных окружения
DATABASE_URL = os.environ.get('DATABASE_URL')

STEAM_APP_ID = 730  # ID игры Counter-Strike
STEAM_CURRENCY = 1  # USD

def get_dmarket_price(item_name):
    """
    Получает цену предмета с DMarket API.
    """
    try:
        url = "https://api.dmarket.com/exchange/v1/market/items"
        params = {
            "title": item_name,
            "side": "sell",
            "currency": "USD",
            "orderBy": "price",
            "orderDir": "asc",
            "limit": 1,
            "gameId": "a8db"
        }
        
        headers = {
            "X-App-Id": "0xEB3D26980C99b1ca13b29394740b150651c39AAe"
        }

        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        price_data = resp.json()

        if price_data.get('status') == 'ok' and price_data.get('objects'):
            lowest_price = float(price_data['objects'][0]['price']['USD']) / 100.0
            return f"${lowest_price:.2f}"
        else:
            print(f"DMarket API: Нет данных о предмете '{item_name}'")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе DMarket API: {e}")
        return None

@app.route('/')
def index():
    """Главная страница приложения."""
    return render_template('index.html')

@app.route('/search')
def search():
    """API-эндпоинт для поиска скинов по части названия."""
    query = request.args.get('q', '').strip().lower()
    results = []
    if not DATABASE_URL:
        print('Ошибка: DATABASE_URL не найдена.')
        return jsonify({'error': 'DATABASE_URL не найдена'}), 500
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT market_hash_name FROM skins WHERE LOWER(market_hash_name) LIKE %s LIMIT 10",
                    (f"%{query}%",)
                )
                results = [row[0] for row in cursor.fetchall()]
    except psycopg2.Error as e:
        print(f'Ошибка базы данных: {e}')
        return jsonify({'error': 'Ошибка при работе с базой данных'}), 500
    return jsonify({'results': results})

@app.route('/combined_item')
def combined_item():
    """
    API-эндпоинт для получения информации о предмете
    со Steam и DMarket и выбора лучшей цены.
    """
    item_name = request.args.get('name')
    if not item_name:
        return jsonify({'error': 'Параметр name обязателен'}), 400

    steam_price = None
    dmarket_price = None
    steam_link = None
    
    # 1. Запрос к Steam API
    try:
        price_url = "https://steamcommunity.com/market/priceoverview/"
        params = {
            "appid": STEAM_APP_ID,
            "currency": STEAM_CURRENCY,
            "market_hash_name": item_name
        }
        resp = requests.get(price_url, params=params, timeout=10)
        resp.raise_for_status()
        price_data = resp.json()
        if price_data.get('success'):
            steam_price = price_data.get("lowest_price")
            if steam_price:
                steam_price_float = float(steam_price.replace('$', '').replace(' USD', '').replace(',', ''))
            encoded_item_name = urllib.parse.quote(item_name)
            steam_link = f"https://steamcommunity.com/market/listings/{STEAM_APP_ID}/{encoded_item_name}"
    except requests.RequestException as e:
        print(f"Ошибка при запросе Steam API: {e}")

    # 2. Запрос к DMarket API
    dmarket_price = get_dmarket_price(item_name)
    if dmarket_price:
        dmarket_price_float = float(dmarket_price.replace('$', ''))
        dmarket_link = f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={urllib.parse.quote(item_name)}"

    # 3. Сравнение цен и выбор лучшей
    if steam_price and dmarket_price:
        steam_price_float = float(steam_price.replace('$', '').replace(' USD', '').replace(',', ''))
        dmarket_price_float = float(dmarket_price.replace('$', ''))

        if dmarket_price_float < steam_price_float:
            result = {
                "item_name": item_name,
                "lowest_price": dmarket_price,
                "source": "DMarket",
                "link": dmarket_link
            }
        else:
            result = {
                "item_name": item_name,
                "lowest_price": steam_price,
                "source": "Steam",
                "link": steam_link
            }
    elif steam_price:
        result = {
            "item_name": item_name,
            "lowest_price": steam_price,
            "source": "Steam",
            "link": steam_link
        }
    elif dmarket_price:
        result = {
            "item_name": item_name,
            "lowest_price": dmarket_price,
            "source": "DMarket",
            "link": dmarket_link
        }
    else:
        result = {
            "item_name": item_name,
            "lowest_price": "Нет данных",
            "source": "N/A",
            "link": ""
        }
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
