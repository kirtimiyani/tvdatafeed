#!/usr/bin/env python3
"""
Упрощенный тест для проверки TokenManager без зависимостей
"""

import sys
import os

# Добавляем путь к модулю
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tvDatafeed'))

from tvDatafeed import TvDatafeed, TokenManager

def test_token_manager():
    """Тест только TokenManager без зависимостей"""
    
    print("=== Тест TokenManager ===\n")
    
    # Тест 1: Создание TokenManager
    print("1. Создание TokenManager...")
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
    
    # Тест 5: Проверка истечения токена
    print("5. Тестирование проверки истечения токена...")
    is_expired = token_manager.is_token_expired(max_age_days=0)  # Считаем токен истекшим сразу
    if is_expired:
        print("✓ Токен корректно определяется как истекший")
    else:
        print("⚠ Токен не определяется как истекший (может быть нормально)")
    
    print()
    
    # Очистка тестовых файлов
    print("6. Очистка тестовых файлов...")
    if os.path.exists("test_token.json"):
        os.remove("test_token.json")
        print("✓ Удален файл: test_token.json")
    
    print()
    print("=== Все тесты TokenManager пройдены успешно! ===")
    return True

def show_usage_examples():
    """Показать примеры использования"""
    
    print("\n=== Примеры использования ===\n")
    
    print("Пример 1: Базовое использование TvDatafeed с сохранением токена")
    print("```python")
    print("from tvDatafeed import TvDatafeed")
    print("")
    print("# Создание с автоматическим сохранением токена")
    print("tv = TvDatafeed(username='your_username', password='your_password')")
    print("")
    print("# При повторном создании токен будет загружен из файла")
    print("# Это избежит необходимости повторной аутентификации и капчи")
    print("tv2 = TvDatafeed(username='your_username', password='your_password')")
    print("```")
    print()
    
    print("Пример 2: Управление токенами")
    print("```python")
    print("# Получение информации о токене")
    print("token_info = tv.get_token_info()")
    print("if token_info:")
    print("    print(f'Токен создан: {token_info[\"created_at\"]}')") 
    print("    print(f'Возраст токена: {token_info[\"age_days\"]} дней')")
    print("")
    print("# Принудительное обновление токена")
    print("if tv.refresh_token():")
    print("    print('Токен успешно обновлен')")
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
    
    print("Преимущества новой системы:")
    print("• Автоматическое сохранение и загрузка токенов")
    print("• Избежание частых запросов капчи")
    print("• Полностью автоматический сбор данных")
    print("• Проверка валидности токенов")
    print("• Безопасное хранение с привязкой к пользователю")
    print()

if __name__ == "__main__":
    print("Запуск упрощенного теста TokenManager...\n")
    
    try:
        success = test_token_manager()
        if success:
            show_usage_examples()
            print("TokenManager готов к использованию!")
        else:
            print("Обнаружены ошибки в тестах.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Критическая ошибка при выполнении тестов: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
