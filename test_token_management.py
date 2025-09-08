#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функционала сохранения токенов
"""

import logging
import os
import sys
from tvDatafeed import TvDatafeed, TokenManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_token_management():
    """Тест функционала управления токенами"""
    
    print("=== Тест системы управления токенами TvDatafeed ===\n")
    
    # Тест 1: Создание TokenManager
    print("1. Тестирование TokenManager...")
    token_manager = TokenManager("test_token.json")
    print("✓ TokenManager создан успешно\n")
    
    # Тест 2: Проверка отсутствия токена
    print("2. Проверка отсутствия сохраненного токена...")
    token = token_manager.load_token("test_user")
    if token is None:
        print("✓ Токен отсутствует (ожидаемо)\n")
    else:
        print("⚠ Найден существующий токен, удаляем его...")
        token_manager.delete_token()
        print("✓ Токен удален\n")
    
    # Тест 3: Сохранение и загрузка токена
    print("3. Тестирование сохранения и загрузки токена...")
    test_token = "test_auth_token_12345"
    test_username = "test_user"
    
    # Сохраняем токен
    if token_manager.save_token(test_token, test_username):
        print("✓ Токен сохранен успешно")
    else:
        print("✗ Ошибка при сохранении токена")
        return False
    
    # Загружаем токен
    loaded_token = token_manager.load_token(test_username)
    if loaded_token == test_token:
        print("✓ Токен загружен успешно")
    else:
        print(f"✗ Ошибка при загрузке токена: {loaded_token} != {test_token}")
        return False
    
    # Проверяем информацию о токене
    token_info = token_manager.get_token_info()
    if token_info:
        print(f"✓ Информация о токене: {token_info}")
    else:
        print("✗ Не удалось получить информацию о токене")
        return False
    
    print()
    
    # Тест 4: Проверка защиты от неправильного пользователя
    print("4. Тестирование защиты от неправильного пользователя...")
    wrong_user_token = token_manager.load_token("wrong_user")
    if wrong_user_token is None:
        print("✓ Токен не загружается для неправильного пользователя")
    else:
        print("✗ Токен загрузился для неправильного пользователя")
        return False
    
    print()
    
    # Тест 5: Создание TvDatafeed без учетных данных
    print("5. Тестирование TvDatafeed без учетных данных...")
    try:
        tv_no_auth = TvDatafeed()
        print("✓ TvDatafeed создан без учетных данных")
        
        # Проверяем, что используется режим без авторизации
        if tv_no_auth.token == "unauthorized_user_token":
            print("✓ Используется режим без авторизации")
        else:
            print(f"⚠ Неожиданный токен: {tv_no_auth.token}")
        
    except Exception as e:
        print(f"✗ Ошибка при создании TvDatafeed: {e}")
        return False
    
    print()
    
    # Тест 6: Создание TvDatafeed с пользовательским файлом токена
    print("6. Тестирование TvDatafeed с пользовательским файлом токена...")
    try:
        tv_custom = TvDatafeed(token_file="custom_token.json")
        print("✓ TvDatafeed создан с пользовательским файлом токена")
        
        # Проверяем методы управления токенами
        token_info = tv_custom.get_token_info()
        print(f"✓ Информация о токене: {token_info}")
        
    except Exception as e:
        print(f"✗ Ошибка при создании TvDatafeed: {e}")
        return False
    
    print()
    
    # Очистка тестовых файлов
    print("7. Очистка тестовых файлов...")
    test_files = ["test_token.json", "custom_token.json"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"✓ Удален файл: {file}")
    
    print()
    print("=== Все тесты пройдены успешно! ===")
    return True

def demo_usage():
    """Демонстрация использования новой функциональности"""
    
    print("\n=== Демонстрация использования ===\n")
    
    print("Пример 1: Создание TvDatafeed с сохранением токена")
    print("```python")
    print("from tvDatafeed import TvDatafeed")
    print("")
    print("# Создание с автоматическим сохранением токена")
    print("tv = TvDatafeed(username='your_username', password='your_password')")
    print("")
    print("# При повторном создании токен будет загружен из файла")
    print("tv2 = TvDatafeed(username='your_username', password='your_password')")
    print("```")
    print()
    
    print("Пример 2: Управление токенами")
    print("```python")
    print("# Получение информации о токене")
    print("token_info = tv.get_token_info()")
    print("print(token_info)")
    print("")
    print("# Принудительное обновление токена")
    print("tv.refresh_token()")
    print("")
    print("# Удаление сохраненного токена")
    print("tv.delete_saved_token()")
    print("```")
    print()
    
    print("Пример 3: Использование пользовательского файла токена")
    print("```python")
    print("# Использование пользовательского файла для токена")
    print("tv = TvDatafeed(")
    print("    username='your_username',")
    print("    password='your_password',")
    print("    token_file='my_custom_token.json'")
    print(")")
    print("```")
    print()

if __name__ == "__main__":
    print("Запуск тестов системы управления токенами...\n")
    
    try:
        success = test_token_management()
        if success:
            demo_usage()
            print("Функционал готов к использованию!")
        else:
            print("Обнаружены ошибки в тестах.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Критическая ошибка при выполнении тестов: {e}")
        sys.exit(1)
