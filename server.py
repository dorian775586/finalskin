import os
import psycopg2
import requests
import urllib.parse
from flask import Flask, request, jsonify, render_template

# Импортируем нашу новую функцию
from dmarket_api import get_dmarket_price

app = Flask(__name__)

# Получение URL базы данных из переменных окружения
DATABASE_URL = os.environ.get('DATABASE_URL')

STEAM_APP_ID = 730  # ID игры Counter-Strike
STEAM_CURRENCY = 1  # USD

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

# Старый эндпоинт для Steam API (оставлен для справки)
@app.route('/item')
def item():
    """
    API-эндпоинт для получения информации о предмете по его market_hash_name.
    """
    item_name = request.args.get('name')
    if not item_name:
        return jsonify({'error': 'Параметр name обязателен'}), 400

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

        encoded_item_name = urllib.parse.quote(item_name)
        link = f"https://steamcommunity.com/market/listings/{STEAM_APP_ID}/{encoded_item_name}"

        if not price_data or price_data.get('success') is False:
            result = {
                "item_name": item_name,
                "lowest_price": "Нет данных API",
                "median_price": "Нет данных API",
                "volume": "Нет данных API",
                "link": link
            }
        else:
            result = {
                "item_name": item_name,
                "lowest_price": price_data.get("lowest_price", "N/A"),
                "median_price": price_data.get("median_price", "N/A"),
                "volume": price_data.get("volume", "N/A"),
                "link": link
            }
        
        return jsonify(result)

    except requests.RequestException as e:
        print(f"Ошибка при запросе Steam API: {e}")
        return jsonify({'error': 'Не удалось получить данные с Steam'}), 500

@app.route('/combined_item')
def combined_item():
    """
    API-эндпоинт для получения самой низкой цены с нескольких площадок.
    """
    item_name = request.args.get('name')
    if not item_name:
        return jsonify({'error': 'Параметр name обязателен'}), 400

    steam_price_data = None
    dmarket_price_data = None
    
    # 1. Запрос цены со Steam API
    try:
        price_url = "https://steamcommunity.com/market/priceoverview/"
        params = {
            "appid": STEAM_APP_ID,
            "currency": STEAM_CURRENCY,
            "market_hash_name": item_name
        }
        resp = requests.get(price_url, params=params, timeout=10)
        resp.raise_for_status()
        steam_data = resp.json()
        
        if steam_data.get('success'):
            lowest_price_str = steam_data.get("lowest_price", "N/A")
            # Конвертируем цену в число для сравнения
            if lowest_price_str != "N/A":
                # Убираем значок валюты и запятые, чтобы получить float
                steam_price = float(lowest_price_str.replace('$', '').replace(',', '.'))
                steam_price_data = {
                    'price': steam_price,
                    'source': 'Steam',
                    'link': f"https://steamcommunity.com/market/listings/{STEAM_APP_ID}/{urllib.parse.quote(item_name)}"
                }
    except requests.RequestException:
        print(f"Не удалось получить данные со Steam для предмета: {item_name}")

    # 2. Запрос цены с DMarket
    dmarket_data = get_dmarket_price(item_name)
    if dmarket_data:
        # Убираем значок валюты и конвертируем в float
        dmarket_price = float(dmarket_data['lowest_price'].replace('$', ''))
        dmarket_price_data = {
            'price': dmarket_price,
            'source': 'DMarket',
            'link': dmarket_data['link']
        }

    # 3. Сравнение и выбор самой низкой цены
    final_result = {
        'item_name': item_name,
        'lowest_price': "Нет данных",
        'source': "N/A",
        'link': "N/A"
    }

    if steam_price_data and dmarket_price_data:
        if steam_price_data['price'] <= dmarket_price_data['price']:
            final_result['lowest_price'] = steam_price_data['lowest_price']
            final_result['source'] = steam_price_data['source']
            final_result['link'] = steam_price_data['link']
        else:
            final_result['lowest_price'] = dmarket_price_data['lowest_price']
            final_result['source'] = dmarket_price_data['source']
            final_result['link'] = dmarket_price_data['link']
    elif steam_price_data:
        final_result['lowest_price'] = steam_price_data['lowest_price']
        final_result['source'] = steam_price_data['source']
        final_result['link'] = steam_price_data['link']
    elif dmarket_price_data:
        final_result['lowest_price'] = dmarket_price_data['lowest_price']
        final_result['source'] = dmarket_price_data['source']
        final_result['link'] = dmarket_price_data['link']

    return jsonify(final_result)


if __name__ == '__main__':
    # Запуск приложения для локальной отладки
    app.run(debug=True)
