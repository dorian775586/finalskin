# Импортируем необходимые библиотеки
import os
import requests
import psycopg2
import logging

from flask import Flask, jsonify, request, render_template

# Создаем экземпляр Flask-приложения
app = Flask(__name__)
# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

# Ключи API
DMARKET_APP_ID = "0xEB3D26980C99b1ca13b29394740b150651c39AAe"


# Функция для подключения к базе данных PostgreSQL
def get_db_connection():
    try:
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
        logging.error(f"Unexpected DB error: {e}")
        raise RuntimeError("Unexpected error") from e


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
            "url": f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={item_name}"
        }

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе к DMarket API: {e}")
        return None
    except Exception as e:
        logging.error(f"Непредвиденная ошибка в get_dmarket_price: {e}")
        return None


# --- маршруты ---

@app.route('/')
def serve_index():
    return render_template('index.html')


@app.route('/search')
def search_steam():
    item_name = request.args.get('item_name')
    if not item_name:
        return jsonify({"error": "Нужен параметр 'item_name'"}), 400

    steam_item = get_steam_price(item_name)
    if not steam_item:
        return jsonify({"message": "Ничего не найдено в Steam"}), 404
    return jsonify(steam_item)


@app.route('/dmarket-search')
def search_dmarket():
    item_name = request.args.get('item_name')
    if not item_name:
        return jsonify({"error": "Нужен параметр 'item_name'"}), 400

    dmarket_item = get_dmarket_price(item_name)
    if not dmarket_item:
        return jsonify({"message": "Ничего не найдено на DMarket"}), 404

    return jsonify(dmarket_item)


@app.route('/suggest')
def suggest_items():
    query = request.args.get('q')
    if not query:
        return jsonify({"suggestions": []})

    try:
        url = "https://steamcommunity.com/market/search/suggest"
        params = {"appid": 730, "q": query}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()

        # Ответ у стима приходит как HTML <li> ... </li>
        text = resp.text
        suggestions = []
        for line in text.splitlines():
            if "<span class=\"market_listing_item_name\"" in line:
                name = line.split(">")[1].split("<")[0]
                suggestions.append(name)

        return jsonify({"suggestions": suggestions})
    except Exception as e:
        logging.error(f"Ошибка при получении подсказок: {e}")
        return jsonify({"suggestions": []})


# --- запуск ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
