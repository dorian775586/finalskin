import requests

def get_dmarket_price(item_name: str):
    """
    Получает информацию о предмете с DMarket.
    :param item_name: Название предмета (например, 'AWP | Atheris (Field-Tested)')
    :return: Словарь с данными о цене или None в случае ошибки.
    """
    url = "https://api.dmarket.com/exchange/v1/market/items"

    params = {
        "title": item_name,
        "limit": 1,
        "orderDir": "asc",
        "orderBy": "price"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Проверяем наличие предметов
        if "objects" in data and data["objects"]:
            item = data["objects"][0]

            # Цена в центах, приходит строкой
            price_usd = float(item["price"]["USD"]) / 100  

            return {
                "source": "DMarket",
                "item_name": item_name,
                "lowest_price": f"${price_usd:.2f}",
                "link": item.get("extra", {}).get("link", f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={item_name}")
            }
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к DMarket API: {e}")
        return None


if __name__ == "__main__":
    test_item = "AWP | Atheris (Field-Tested)"
    price_info = get_dmarket_price(test_item)

    if price_info:
        print(f"Информация о предмете: {price_info['item_name']}")
        print(f"Самая низкая цена на DMarket: {price_info['lowest_price']}")
        print(f"Ссылка: {price_info['link']}")
    else:
        print(f"Не удалось получить информацию о {test_item} с DMarket.")
