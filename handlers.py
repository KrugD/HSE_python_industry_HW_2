from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from api_food import FoodInfo
from api_weather import WeatherAPI
from states import Form
import aiohttp

food_info = FoodInfo()
weather_temp = WeatherAPI()
router = Router()

# Хранение данных пользователей
users = {}

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("Бу! Испугались? Не бойтесь! Я ваш добрый бот.\nВведите /help для списка команд.")

# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/set_profile - Посмотреть свой профиль\n"
        "/log_water - Поcмотреть, сколько воды выпить для выполнения нормы\n"
        "/log_food - Поcмотреть, сколько каллорий употребить для выполнения нормы\n"
        "/log_workout - Поcмотреть расход воды на тренировке\n"
        "/check_progress - Показывает, сколько воды и калорий потреблено, сожжено и сколько осталось до выполнения цели\n"
        "/joke - Получить случайную шутку"
    )

# Функция расчета дневных норм
def calculate_goals(user_id):
    user = users[user_id]
    weight = user['weight']
    height = user['height']
    age = user['age']
    activity = user['activity']
    city = user['city']

    # Рассчитываем норму воды
    temperature = weather_temp.get_current_temperature(city)
    if temperature <= 25:
        volume = 500
    elif temperature > 25 and temperature <= 35:
        volume = 750
    else:
        volume = 1000

    water_goal = weight * 30 + (volume * (activity // 30))
    user['water_goal'] = water_goal

    # Рассчитываем норму калорий
    calorie_goal = (10 * weight) + (6.25 * height) - (5 * age) + 200
    user['calorie_goal'] = calorie_goal


# Команда для настройки профиля
@router.message(Command("set_profile"))
async def set_profile(message: Message, state: FSMContext):
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(Form.weight)


@router.message(Form.weight)
async def process_weight(message: Message, state: FSMContext):
    weight = int(message.text)
    user_id = message.from_user.id
    users.setdefault(user_id, {}).update({'weight': weight})

    await message.answer("Введите ваш рост (в см):")
    await state.set_state(Form.height)


@router.message(Form.height)
async def process_height(message: Message, state: FSMContext):
    height = int(message.text)
    user_id = message.from_user.id
    users[user_id]['height'] = height

    await message.answer("Введите ваш возраст:")
    await state.set_state(Form.age)


@router.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    age = int(message.text)
    user_id = message.from_user.id
    users[user_id]['age'] = age

    await message.answer("Сколько минут активности у вас в день?")
    await state.set_state(Form.activity)


@router.message(Form.activity)
async def process_activity(message: Message, state: FSMContext):
    activity = int(message.text)
    user_id = message.from_user.id
    users[user_id]['activity'] = activity

    await message.answer("В каком городе вы находитесь?")
    await state.set_state(Form.city)


@router.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    city = message.text
    user_id = message.from_user.id
    users[user_id]['city'] = city

    # Рассчитываем цели
    calculate_goals(user_id)

    await message.answer("Профиль успешно настроен!")
    await state.clear()


# Логирование воды
@router.message(Command("log_water"))
async def log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью /set_profile.")
        return

    water_logged = int(message.get_args())
    users[user_id]['logged_water'] = users[user_id].get('logged_water', 0) + water_logged
    remaining_water = users[user_id]['water_goal'] - users[user_id]['logged_water']

    await message.answer(f"Записано: {water_logged} мл. Осталось: {remaining_water} мл.")


# Логирование еды
@router.message(Command("log_food"))
async def log_food(message: Message):
    food_name = message.get_args()
    if not food_name:
        await message.answer("Укажите название продукта после команды /log_food.")
        return
    calories_per_100g = food_info.get_food_info(food_name)
    await message.answer(f"{food_name.capitalize()} — {calories_per_100g} ккал на 100 г. Сколько грамм вы съели?")


# Логирование тренировок
@router.message(Command("log_workout"))
async def log_workout(message: Message):
    args = message.get_args().split()
    if len(args) != 2:
        await message.answer("Формат команды: /log_workout <тип тренировки> <время (мин)>")
        return

    workout_type, workout_time = args[0], int(args[1])
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью /set_profile.")
        return

    burned_calories = workout_time * 10
    users[user_id]['burned_calories'] = users[user_id].get('burned_calories', 0) + burned_calories
    additional_water = 200 * (workout_time // 30)

    await message.answer(
        f"{workout_type.capitalize()} {workout_time} минут — {burned_calories} ккал. Дополнительно: выпейте {additional_water} мл воды.")


# Проверка прогресса
@router.message(Command("check_progress"))
async def check_progress(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью /set_profile.")
        return

    user = users[user_id]
    water_logged = user.get('logged_water', 0)
    calorie_logged = user.get('logged_calories', 0)
    burned_calories = user.get('burned_calories', 0)

    remaining_water = user['water_goal'] - water_logged
    remaining_calories = user['calorie_goal'] - calorie_logged + burned_calories

    await message.answer(
        f"Прогресс:\nВода:\n"f"Выпито: {water_logged} мл из {user['water_goal']} мл. Осталось: {remaining_water} мл.\n"f"Калории:\n"
        f"Потреблено: {calorie_logged} ккал из {user['calorie_goal']} ккал. "
        f"Сожжено: {burned_calories} ккал. Баланс: {remaining_calories} ккал."
)


# Получение шутки из API
@router.message(Command("joke"))
async def get_joke(message: Message):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.chucknorris.io/jokes/random") as response:
            joke = await response.json()
            await message.reply(joke["value"])

# Функция для подключения обработчиков
def setup_handlers(dp):
    dp.include_router(router)