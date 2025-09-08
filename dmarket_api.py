import requests

def get_dmarket_price(item_name):
    """
    Получает информацию о предмете с DMarket.
    :param item_name: Название предмета (например, 'AWP | Atheris (Field-Tested)')
    :return: Словарь с данными о цене или None в случае ошибки.
    """
    # Базовый URL для API DMarket
    url = "https://api.dmarket.com/exchange/v1/market/items"

    # Параметры запроса
    params = {
        'title': item_name,
        'limit': 1,
        'orderDir': 'asc',
        'orderBy': 'price'
    }

    try:
        # Отправляем GET-запрос к DMarket API
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Вызовет ошибку для плохих ответов (4xx или 5xx)
        data = response.json()

        # Проверяем, есть ли предметы в ответе
        if 'Items' in data and data['Items']:
            item = data['Items'][0]
            price = item.get('price', {}).get('USD', 0)
            # DMarket возвращает цену в центах, поэтому нужно разделить на 100
            price_usd = float(price) / 100
            
            return {
                'source': 'DMarket',
                'item_name': item_name,
                'lowest_price': f"${price_usd:.2f}",
                'link': f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={item_name}"
            }
        else:
            return None

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к DMarket API: {e}")
        return None

if __name__ == '__main__':
    # Пример использования
    test_item = "AWP | Atheris (Field-Tested)"
    price_info = get_dmarket_price(test_item)

    if price_info:
        print(f"Информация о предмете: {price_info['item_name']}")
        print(f"Самая низкая цена на DMarket: {price_info['lowest_price']}")
        print(f"Ссылка: {price_info['link']}")
    else:
        print(f"Не удалось получить информацию о {test_item} с DMarket.")
