import requests
from config import api_key

class WeatherAPI:

    api_key = api_key

    def get_current_temperature(self, city):
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric"
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            return data['main']['temp']
        else:
            print(f"Error: {data['message']}")
            return None