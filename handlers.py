import os
import matplotlib.pyplot as plt
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from api_food import FoodInfo
from api_weather import WeatherAPI
from aiogram.types import FSInputFile
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
        "/set_profile - Посмотреть/создать свой профиль\n"
        "/delete_profile - Удалить профиль\n"
        "/choose_profile - Выбрать профиль\n"
        "/log_water - Поcмотреть, сколько воды выпить для выполнения нормы\n"
        "/log_food - Поcмотреть, сколько калорий употребить для выполнения нормы\n"
        "/log_workout - Поcмотреть расход воды на тренировке\n"
        "/check_progress - Показывает, сколько воды и калорий потреблено, сожжено и сколько осталось до выполнения цели\n"
        "/water_progress - Графическое отображение прогресса по воде\n"
        "/calorie_progress - Графическое отображение прогресса по калориям\n"
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
    await message.answer("Введите ваше имя:")
    await state.set_state(Form.name)


@router.message(Form.name)
async def process_name(message: Message, state: FSMContext):
    name = message.text
    user_id = message.from_user.id
    users.setdefault(user_id, {}).update({'name': name})

    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(Form.weight)


@router.message(Form.weight)
async def process_weight(message: Message, state: FSMContext):
    weight = int(message.text)
    user_id = message.from_user.id
    users[user_id]['weight'] = weight

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


# Удаление профиля
@router.message(Command("delete_profile"))
async def delete_profile(message: Message):
    user_id = message.from_user.id
    if user_id in users:
        del users[user_id]
        await message.answer("Ваш профиль был успешно удален.")
    else:
        await message.answer("У вас нет профиля для удаления.")


# Выбор профиля
@router.message(Command("choose_profile"))
async def choose_profile(message: Message):
    user_id = message.from_user.id
    available_profiles = [user['name'] for user in users.values() if user.get('name')]
    
    if not available_profiles:
        await message.answer("Нет доступных профилей. Сначала создайте профиль с помощью /set_profile.")
        return
    
    await message.answer("Доступные профили:\n" + "\n".join(available_profiles) + "\nВыберите профиль, введя его имя:")


@router.message(lambda message: message.text in [user['name'] for user in users.values() if user.get('name')])
async def process_profile_selection(message: Message):
    user_id = message.from_user.id
    profile_name = message.text

    # Находим пользователя по имени профиля
    for uid, user in users.items():
        if user.get('name') == profile_name:
            # Устанавливаем активный профиль для дальнейшей работы
            users[user_id] = user  # Здесь можно изменить логику, если нужно сохранять разные профили
            await message.answer(f"Вы выбрали профиль: {profile_name}. Теперь вы можете продолжать.")
            return
    
    await message.answer("Профиль не найден.")


# Логирование воды
@router.message(Command("log_water"))
async def log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью /set_profile.")
        return

    # Извлекаем аргументы из текста сообщения
    args = message.text.split()
    if len(args) < 2:  # проверяем, передано ли значение
        await message.answer("Пожалуйста, укажите количество воды (в мл) после команды /log_water.")
        return

    try:
        water_logged = int(args[1])  # берем второй элемент как количество воды
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")
        return

    users[user_id]['logged_water'] = users[user_id].get('logged_water', 0) + water_logged
    remaining_water = users[user_id]['water_goal'] - users[user_id]['logged_water']

    await message.answer(f"Записано: {water_logged} мл. Осталось: {remaining_water} мл.")


# Логирование еды
@router.message(Command("log_food"))
async def log_food(message: Message, state: FSMContext):
    args = message.text.split()
    if len(args) < 2:  # проверяем, указано ли название продукта
        await message.answer("Укажите название продукта после команды /log_food.")
        return

    food_name = " ".join(args[1:])  # объединяем все аргументы, кроме первого, в одно название
    calories_per_100g = food_info.get_food_info(food_name)

    if calories_per_100g is None:  # проверка на случай, если еда не найдена
        await message.answer("Продукт не найден. Попробуйте другой.")
        return

    # Сохраняем информацию о последнем введенном продукте
    await state.update_data(food_name=food_name, calories_per_100g=calories_per_100g)

    await message.answer(f"{food_name.capitalize()} — {calories_per_100g} ккал на 100 г. Сколько грамм вы съели?")
    
    # Переключаемся в состояние ожидания граммов
    await state.set_state(Form.grams)

@router.message(Form.grams)
async def process_food_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    food_name = data.get('food_name')
    calories_per_100g = data.get('calories_per_100g')

    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью /set_profile.")
        return

    if not message.text.isdigit():  # проверяем, что введено число
        await message.answer("Пожалуйста, введите корректное число граммов.")
        return

    grams = int(message.text)
    calories_logged = (grams / 100) * calories_per_100g  # Здесь calories_per_100g уже просто число

    users[user_id]['logged_calories'] = users[user_id].get('logged_calories', 0) + calories_logged

    await message.answer(f"Записано: {calories_logged:.2f} ккал от {food_name}.")
    
    # Сбрасываем состояние
    await state.clear()

# Логирование тренировок
@router.message(Command("log_workout"))
async def log_workout(message: Message):
    # Извлекаем аргументы из текста сообщения
    args = message.text.split()
    if len(args) != 3:  # Проверяем, указаны ли тип тренировки и время
        await message.answer("Формат команды: /log_workout <тип тренировки> <время (мин)>")
        return

    workout_type, workout_time_str = args[1], args[2]  # Первый аргумент - тип тренировки, второй - время
    try:
        workout_time = int(workout_time_str)  # Преобразуем время в целое число
    except ValueError:
        await message.answer("Пожалуйста, введите время тренировки в минутах.")
        return

    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью /set_profile.")
        return

    burned_calories = workout_time * 10
    users[user_id]['burned_calories'] = users[user_id].get('burned_calories', 0) + burned_calories
    additional_water = 200 * (workout_time // 30)

    await message.answer(
        f"{workout_type.capitalize()} {workout_time} минут — {burned_calories} ккал. Дополнительно: выпейте {additional_water} мл воды."
    )


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
        f"Прогресс:\nВода:\n"
        f"Выпито: {water_logged} мл из {user['water_goal']} мл. Осталось: {remaining_water} мл.\n"
        f"Калории:\n"
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


# Функция для построения графика воды
def plot_water_progress(user):
    water_logged = user.get('logged_water', 0)
    water_goal = user.get('water_goal', 0)

    # Данные для графика
    categories = ['Выпито', 'Цель']
    values = [water_logged, water_goal]

    fig, ax = plt.subplots()
    ax.bar(categories, values, color=['blue', 'orange'])
    ax.set_ylim(0, max(water_goal, water_logged) + 500)  # Устанавливаем лимиты по оси Y
    ax.set_ylabel('Мл')
    ax.set_title('Прогресс по воде')

    # Сохранение графика в файл
    filename = 'water_progress.png'
    plt.savefig(filename, format='png')
    plt.close(fig)  # Закрываем график

    return filename

# Функция для построения графика калорий
def plot_calorie_progress(user):
    calorie_logged = user.get('logged_calories', 0)
    calorie_goal = user.get('calorie_goal', 0)
    burned_calories = user.get('burned_calories', 0)

    # Данные для графика
    categories = ['Потреблено', 'Сожжено', 'Цель']
    values = [calorie_logged, burned_calories, calorie_goal]

    fig, ax = plt.subplots()
    ax.bar(categories, values, color=['green', 'red', 'orange'])
    ax.set_ylim(0, max(calorie_goal, calorie_logged + burned_calories) + 200)  # Устанавливаем лимиты по оси Y
    ax.set_ylabel('Ккал')
    ax.set_title('Прогресс по калориям')

    # Сохранение графика в файл
    filename = 'calorie_progress.png'
    plt.savefig(filename, format='png')
    plt.close(fig)  # Закрываем график

    return filename

@router.message(Command("water_progress"))
async def water_progress(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью /set_profile.")
        return

    user = users[user_id]
    filename = plot_water_progress(user)

    photo = FSInputFile(filename)
    
    await message.answer_photo(photo=photo)

    # Удаляем файл после отправки
    os.remove(filename)

@router.message(Command("calorie_progress"))
async def calorie_progress(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью /set_profile.")
        return

    user = users[user_id]

    # Проверка на наличие данных для построения графика калорий
    if 'logged_calories' not in user or 'calorie_goal' not in user:
        await message.answer("Недостаточно данных для построения графика калорий.")
        return

    filename = plot_calorie_progress(user)
    photo = FSInputFile(filename)
    
    await message.answer_photo(photo=photo)

    # Удаляем файл после отправки
    os.remove(filename)

# Функция для подключения обработчиков
def setup_handlers(dp):
    dp.include_router(router)