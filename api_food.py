import requests

class FoodInfo:
    def __init__(self):
        self.base_url = "https://world.openfoodfacts.org/cgi/search.pl"

    def get_food_info(self, product_name):
        url = f"{self.base_url}?action=process&search_terms={product_name}&json=true"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            products = data.get('products', [])
            if products:  # Проверяем, есть ли найденные продукты
                first_product = products[0]
                return {
                    'name': first_product.get('product_name', 'Неизвестно'),
                    'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
                }
            return None
        print(f"Ошибка: {response.status_code}")
        return None