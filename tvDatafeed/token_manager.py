import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TokenManager:
    """Менеджер для управления auth token TradingView между сессиями"""
    
    def __init__(self, token_file: str = "tvdatafeed_token.json"):
        """
        Инициализация менеджера токенов
        
        Args:
            token_file (str): Путь к файлу для сохранения токена
        """
        self.token_file = token_file
        self.token_data: Optional[Dict[str, Any]] = None
        
    def save_token(self, token: str, username: str = None) -> bool:
        """
        Сохранить токен в файл
        
        Args:
            token (str): Auth token для сохранения
            username (str, optional): Имя пользователя для идентификации
            
        Returns:
            bool: True если сохранение прошло успешно, False иначе
        """
        try:
            token_data = {
                "token": token,
                "username": username,
                "created_at": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat()
            }
            
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
                
            self.token_data = token_data
            logger.info(f"Token успешно сохранен в {self.token_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении токена: {e}")
            return False
    
    def load_token(self, username: str = None) -> Optional[str]:
        """
        Загрузить токен из файла
        
        Args:
            username (str, optional): Имя пользователя для проверки соответствия
            
        Returns:
            Optional[str]: Токен если найден и валиден, None иначе
        """
        try:
            logger.warning("Token is loading")
            if not os.path.exists(self.token_file):
                logger.debug(f"Файл токена {self.token_file} не найден")
                return None
                
            with open(self.token_file, 'r', encoding='utf-8') as f:
                self.token_data = json.load(f)
                
            # Проверяем соответствие имени пользователя
            if username and self.token_data.get("username") != username:
                logger.warning(f"Токен принадлежит другому пользователю: {self.token_data.get('username')} != {username}")
                return None
                
            # Проверяем возраст токена (токены TradingView обычно действуют долго, но лучше проверить)
            created_at = datetime.fromisoformat(self.token_data["created_at"])
            age_days = (datetime.now() - created_at).days
            
            if age_days > 30:  # Если токен старше 30 дней, считаем его потенциально устаревшим
                logger.warning(f"Токен создан {age_days} дней назад, может быть устаревшим")
                
            # Обновляем время последнего использования
            self.token_data["last_used"] = datetime.now().isoformat()
            self.save_token(self.token_data["token"], self.token_data.get("username"))
            
            logger.info(f"Token успешно загружен из {self.token_file}")
            logger.warning(f"Token successfully loaded from file")
            return self.token_data["token"]
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке токена: {e}")
            return None
    
    def delete_token(self) -> bool:
        """
        Удалить сохраненный токен
        
        Returns:
            bool: True если удаление прошло успешно, False иначе
        """
        try:
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
                logger.info(f"Файл токена {self.token_file} удален")
                
            self.token_data = None
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при удалении токена: {e}")
            return False
    
    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о сохраненном токене
        
        Returns:
            Optional[Dict[str, Any]]: Информация о токене или None если токен не найден
        """
        if self.token_data:
            return {
                "username": self.token_data.get("username"),
                "created_at": self.token_data.get("created_at"),
                "last_used": self.token_data.get("last_used"),
                "age_days": (datetime.now() - datetime.fromisoformat(self.token_data["created_at"])).days
            }
        return None
    
    def is_token_expired(self, max_age_days: int = 30) -> bool:
        """
        Проверить, истек ли токен
        
        Args:
            max_age_days (int): Максимальный возраст токена в днях
            
        Returns:
            bool: True если токен истек, False иначе
        """
        if not self.token_data:
            return True
            
        try:
            created_at = datetime.fromisoformat(self.token_data["created_at"])
            age_days = (datetime.now() - created_at).days
            return age_days > max_age_days
        except Exception:
            return True
