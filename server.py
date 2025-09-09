import os
import requests
import psycopg2
import logging
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# DMarket App ID (можно убрать — для поиска не нужен)
DMARKET_APP_ID = "0xEB3D26980C99b1ca13b29394740b150651c39AAe"

# --- База данных (для suggest) ---
def get_db_connection():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL)

# --- Steam API ---
def get_steam_price(item_name: str):
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
                "url": f"https://steamcommunity.com/market/listings/730/{item_name}"
            }
        return None
    except Exception as e:
        logging.error(f"Steam API error: {e}")
        return None

# --- DMarket API ---
def get_dmarket_price(item_name: str):
    url = "https://api.dmarket.com/exchange/v1/market/items"
    params = {
        "title": item_name,
        "limit": 1,
        "orderBy": "price",
        "orderDir": "asc",
        "currency": "USD"
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        objects = data.get("objects", [])
        if not objects:
            return None

        item = objects[0]
        # dmarket всегда отдаёт minPrice в центах
        price_cents = int(item.get("minPrice", "0"))
        price_usd = price_cents / 100

        return {
            "source": "DMarket",
            "item_name": item_name,
            "lowest_price": f"${price_usd:.2f}",
            "url": f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={item_name}"
        }

    except Exception as e:
        logging.error(f"DMarket API error: {e}")
        return None

# --- Routes ---
@app.route("/")
def serve_index():
    return render_template("index.html")

@app.route("/suggest")
def suggest():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify(suggestions=[])
    conn = get_db_connection()
    if not conn:
        return jsonify(suggestions=[])
    cur = conn.cursor()
    cur.execute("SELECT name FROM skins WHERE name ILIKE %s LIMIT 10", (f"%{query}%",))
    rows = cur.fetchall()
    conn.close()
    return jsonify(suggestions=[r[0] for r in rows])

@app.route("/search")
def search_steam():
    item_name = request.args.get("q")
    if not item_name:
        return jsonify(error="Параметр 'q' обязателен"), 400
    result = get_steam_price(item_name)
    if not result:
        return jsonify(message="Ничего не найдено в Steam"), 404
    return jsonify(result)

@app.route("/dmarket-search")
def search_dmarket():
    item_name = request.args.get("q")
    if not item_name:
        return jsonify(error="Параметр 'q' обязателен"), 400
    result = get_dmarket_price(item_name)
    if not result:
        return jsonify(message="Ничего не найдено на DMarket"), 404
    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
