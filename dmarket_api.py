import requests

def get_dmarket_price(item_name):
    url = "https://api.dmarket.com/exchange/v1/market/items"

    params = {
        "title": item_name,   # фильтр по названию предмета
        "limit": 5,
        "orderBy": "price",
        "orderDir": "asc",
        "currency": "USD"
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("objects", [])
        if not items:
            print("Ничего не найдено на DMarket")
            return None

        first = items[0]
        return {
            "source": "DMarket",
            "item_name": item_name,
            "lowest_price": f"${float(first['price']['USD'])/100:.2f}",
            "link": f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={item_name}"
        }

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к DMarket API: {e}")
        return None


if __name__ == "__main__":
    test_item = "AWP | Duality (Field-Tested)"
    print(get_dmarket_price(test_item))
git add .
git commit -m "Объединение логики DMarket и Steam в server.py"