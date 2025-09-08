import urllib.parse
from flask import Flask, request, jsonify

app = Flask(__name__)

# ID игры для CS2
STEAM_APP_ID = 730

@app.route('/test')
def test_url():
    """
    Эндпоинт для тестирования форматирования URL.
    
    Использование: http://127.0.0.1:5000/test?name=ваш_скин
    """
    # Получаем название предмета из параметров запроса
    item_name = request.args.get('name')
    
    if not item_name:
        return jsonify({"error": "Пожалуйста, предоставьте название предмета в параметре 'name'."}), 400

    # Формируем URL-адрес так же, как в вашем server.py
    encoded_item_name = urllib.parse.quote_plus(item_name)
    link = f"https://steamcommunity.com/market/listings/{STEAM_APP_ID}/{encoded_item_name}"
    
    return jsonify({
        "original_name": item_name,
        "encoded_name": encoded_item_name,
        "generated_link": link,
        "description": "Сравните эту ссылку с той, что не работает."
    })

if __name__ == '__main__':
    # Запускаем тестовое приложение
    app.run(debug=True)
