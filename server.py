# Импортируем необходимые библиотеки
import os
import requests
import psycopg2
import logging

from flask import Flask, jsonify, request

# Создаем экземпляр Flask-приложения
app = Flask(__name__)
# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

# Ключи API
DMARKET_APP_ID = "0xEB3D26980C99b1ca13b29394740b150651c39AAe"

# Функция для подключения к базе данных PostgreSQL
def get_db_connection():
    try:
        # Получаем URL базы данных из переменных окружения Render
        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            logging.error("DATABASE_URL environment variable is not set.")
            raise ValueError("DATABASE_URL is not configured.")

        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Error connecting to the database: {e}")
        raise RuntimeError("Failed to connect to the database") from e
    except Exception as e:
        logging.error(f"An unexpected error occurred during database connection: {e}")
        raise RuntimeError("An unexpected error occurred") from e

# Получение данных из Steam Web API
def get_steam_price(item_name):
    try:
        url = "https://steamcommunity.com/market/priceoverview/"
        params = {
            "appid": 730,
            "currency": 1,
            "market_hash_name": item_name
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and data.get("success"):
            return {
                "source": "Steam",
                "item_name": item_name,
                "lowest_price": data.get("lowest_price"),
                "volume": data.get("volume")
            }
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе к Steam API: {e}")
        return None

# Получение данных с DMarket API
def get_dmarket_price(item_name):
    url = "https://api.dmarket.com/exchange/v1/market/items"
    headers = {
        "X-App-Id": DMARKET_APP_ID
    }
    params = {
        "title": item_name,
        "limit": 1,
        "orderBy": "price",
        "orderDir": "asc",
        "currency": "USD"
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("objects", [])
        if not items:
            logging.info(f"На DMarket ничего не найдено для: {item_name}")
            return None

        first = items[0]
        price_usd = float(first["price"]["USD"]) / 100
        return {
            "source": "DMarket",
            "item_name": item_name,
            "lowest_price": f"${price_usd:.2f}",
            "link": f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={item_name}"
        }

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе к DMarket API: {e}")
        return None
    except Exception as e:
        logging.error(f"Непредвиденная ошибка в get_dmarket_price: {e}")
        return None

# Маршрут для поиска Steam
@app.route('/search')
def search_steam():
    item_name = request.args.get('q')
    if not item_name:
        return jsonify({"error": "Требуется 'q' параметр"}), 400
    
    steam_item = get_steam_price(item_name)
    if not steam_item:
        return jsonify({"message": "Ничего не найдено в Steam"}), 404
        
    return jsonify(steam_item)

# Маршрут для поиска DMarket
@app.route('/dmarket-search')
def search_dmarket():
    item_name = request.args.get('q')
    if not item_name:
        return jsonify({"error": "Требуется 'q' параметр"}), 400

    dmarket_item = get_dmarket_price(item_name)
    if not dmarket_item:
        return jsonify({"message": "Ничего не найдено на DMarket"}), 404

    return jsonify(dmarket_item)

# Этот блок кода будет выполняться только при локальном запуске
if __name__ == '__main__':
    # Получаем порт из переменной окружения Render, по умолчанию 5000
    port = int(os.environ.get("PORT", 5000))
    # Запускаем приложение на всех интерфейсах и на указанном порту
    app.run(host="0.0.0.0", port=port, debug=False)
