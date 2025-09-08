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
        # Убедитесь, что переменная окружения DATABASE_URL установлена
        print('Ошибка: DATABASE_URL не найдена.')
        return jsonify({'error': 'DATABASE_URL не найдена'}), 500
    try:
        # Подключение к базе данных и выполнение поиска
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

@app.route('/item')
def item():
    """
    API-эндпоинт для получения информации о предмете по его market_hash_name.
    """
    item_name = request.args.get('name')
    if not item_name:
        return jsonify({'error': 'Параметр name обязателен'}), 400

    try:
        # Запрос к Steam API для получения цен через priceoverview
        price_url = "https://steamcommunity.com/market/priceoverview/"
        params = {
            "appid": STEAM_APP_ID,
            "currency": STEAM_CURRENCY,
            "market_hash_name": item_name
        }
        resp = requests.get(price_url, params=params, timeout=10)
        resp.raise_for_status()
        price_data = resp.json()

        # Формирование ссылки на предмет
        link = f"https://steamcommunity.com/market/listings/{STEAM_APP_ID}/{urllib.parse.quote_plus(item_name)}"

        # Проверка наличия данных в ответе Steam API
        if not price_data or price_data.get('success') is False:
            # Если данные не получены, возвращаем пустое значение
            result = {
                "item_name": item_name,
                "lowest_price": "Нет данных API",
                "median_price": "Нет данных API",
                "volume": "Нет данных API",
                "link": link
            }
        else:
            # Если данные получены, формируем ответ
            result = {
                "item_name": item_name,
                "lowest_price": price_data.get("lowest_price", "N/A"),
                "median_price": price_data.get("median_price", "N/A"),
                "volume": price_data.get("volume", "N/A"),
                "link": link
            }
        
        return jsonify(result)

    except requests.RequestException as e:
        # Обработка ошибок при запросе
        print(f"Ошибка при запросе Steam API: {e}")
        return jsonify({'error': 'Не удалось получить данные с Steam'}), 500

if __name__ == '__main__':
    # Запуск приложения для локальной отладки
    app.run(debug=True)
