from selenium import webdriver
import time
import datetime
import enum
import json
import logging
import random
import re
import string
import pandas as pd
from websocket import create_connection
import requests
import json
from bs4 import BeautifulSoup
from .token_manager import TokenManager

logger = logging.getLogger(__name__)


class Interval(enum.Enum):
    in_1_second = "1S"
    in_5_second = "5S"
    in_10_second = "10S"
    in_15_second = "15S"
    in_30_second = "30S"
    in_45_second = "45S"
    in_1_minute = "1"
    in_3_minute = "3"
    in_5_minute = "5"
    in_15_minute = "15"
    in_30_minute = "30"
    in_45_minute = "45"
    in_1_hour = "1H"
    in_2_hour = "2H"
    in_3_hour = "3H"
    in_4_hour = "4H"
    in_daily = "1D"
    in_weekly = "1W"
    in_monthly = "1M"


class TvDatafeed:
    __sign_in_url = 'https://www.tradingview.com/accounts/signin/'
    __search_url = 'https://symbol-search.tradingview.com/symbol_search/?text={}&hl=1&exchange={}&lang=en&type=&domain=production'
    __ws_headers = json.dumps({"Origin": "https://data.tradingview.com"})
    __signin_headers = {'Referer': 'https://www.tradingview.com'}
    __ws_timeout = 5

    def __init__(
        self,
        username: str = None,
        password: str = None,
        token_file: str = "tvdatafeed_token.json",
    ) -> None:
        """Create TvDatafeed object

        Args:
            username (str, optional): tradingview username. Defaults to None.
            password (str, optional): tradingview password. Defaults to None.
            token_file (str, optional): path to token file. Defaults to "tvdatafeed_token.json".
        """

        self.ws_debug = False
        self.username = username
        self.password = password
        self.token_manager = TokenManager(token_file)

        self.token = self.__auth_with_token_management(username, password)

        if self.token is None:
            self.token = "unauthorized_user_token"
            logger.warning(
                "you are using nologin method, data you access may be limited"
            )

        self.ws = None
        self.session = self.__generate_session()
        self.chart_session = self.__generate_chart_session()

    def __auth_with_token_management(self, username, password):
        """Аутентификация с управлением токенами"""
        
        # Если нет учетных данных, возвращаем None
        if username is None or password is None:
            logger.info("Учетные данные не предоставлены, используется режим без авторизации")
            return None
        
        # Пытаемся загрузить сохраненный токен
        saved_token = self.token_manager.load_token(username)
        if saved_token:
            logger.info("Найден сохраненный токен, проверяем его валидность...")
            
            # Проверяем валидность токена
            if self.__is_token_valid(saved_token):
                logger.info("Сохраненный токен валиден, используем его")
                return saved_token
            else:
                logger.warning("Сохраненный токен недействителен, удаляем его и получаем новый")
                self.token_manager.delete_token()
        
        # Получаем новый токен
        logger.info("Получаем новый токен...")
        new_token = self.__auth(username, password)
        
        # Сохраняем новый токен, если он получен успешно
        if new_token and new_token != "unauthorized_user_token":
            logger.info("Новый токен получен успешно, сохраняем его")
            self.token_manager.save_token(new_token, username)
        
        return new_token

    def __is_token_valid(self, token):
        """Проверка валидности токена путем тестового запроса"""
        try:
            # Создаем тестовое соединение для проверки токена
            test_ws = create_connection(
                "wss://data.tradingview.com/socket.io/websocket", 
                headers=self.__ws_headers, 
                timeout=self.__ws_timeout
            )
            
            # Отправляем токен для проверки
            test_message = self.__prepend_header(
                self.__construct_message("set_auth_token", [token])
            )
            test_ws.send(test_message)
            
            # Ждем ответ
            start_time = time.time()
            while time.time() - start_time < 3:  # Ждем максимум 3 секунды
                try:
                    result = test_ws.recv()
                    # Если получили ответ без ошибки, токен валиден
                    if result:
                        test_ws.close()
                        return True
                except Exception:
                    break
            
            test_ws.close()
            return False
            
        except Exception as e:
            logger.debug(f"Ошибка при проверке токена: {e}")
            return False

    def __auth(self, username, password):
        """Оригинальный метод аутентификации"""
        if (username is None or password is None):
            token = None

        else:
            data = {"username": username,
                    "password": password,
                    "remember": "on"}
            try:
                response = requests.post(
                    url=self.__sign_in_url, data=data, headers=self.__signin_headers)
                token = response.json()['user']['auth_token']
            except Exception as e:
                logger.error('Captha required, please singin manually')
                token = None
                
                try:
                    driver = webdriver.Chrome()
                    driver.get(self.__sign_in_url)
                    
                    time.sleep(2)  
                    print("Пожалуйста, решите капчу и войдите в систему.")
    
                    try:
                        while True:
                            current_url = driver.current_url
                            if current_url in ["https://www.tradingview.com", "https://ru.tradingview.com/"]:
                                print("Успешный вход в систему!")
                                break
                            time.sleep(1)  # Проверяем каждые 1 секунду
                    except Exception as e:
                        logger.error("Ошибка при проверке URL: %s", str(e))
                        driver.quit()
                        return None
                        
                    # Получение HTML-кода страницы
                    print("CHECKPOINT 1")
                    html = driver.page_source
                    driver.quit() # Закрытие браузера
                    print("CHECKPOINT 2")
                    # Парсинг HTML для извлечения auth_token
                    soup = BeautifulSoup(html, 'html.parser')
                    print("CHECKPOINT 2.5")
    
                    # Пример поиска токена в скриптах
                    script_tags = soup.find_all('script')
                    print("CHECKPOINT 3")
                    for script in script_tags:
                        if 'auth_token' in script.text:
                            # Пример извлечения токена
                            try:
                                # Предположим, что токен представлен как 'auth_token":"YOUR_TOKEN"
                                start = script.text.find('auth_token":"') + len('auth_token":"')
                                end = script.text.find('"', start)
                                token = script.text[start:end]
                                logger.info("Найден auth_token: %s", token)
                                return token
                            except Exception as e:
                                logger.error("Ошибка при извлечении токена: %s", str(e))
                                return None
            
                    logger.error("auth_token не найден на странице.")
                    return None
    
                except Exception as e:
                    print("ERROR:", str(e))
                    logger.error('error while signin')
                    token = None
    
            return token

    def __create_connection(self):
        logging.debug("creating websocket connection")
        self.ws = create_connection(
            "wss://data.tradingview.com/socket.io/websocket", headers=self.__ws_headers, timeout=self.__ws_timeout
        )

    @staticmethod
    def __filter_raw_message(text):
        try:
            found = re.search('"m":"(.+?)",', text).group(1)
            found2 = re.search('"p":(.+?"}"])}', text).group(1)

            return found, found2
        except AttributeError:
            logger.error("error in filter_raw_message")

    @staticmethod
    def __generate_session():
        stringLength = 12
        letters = string.ascii_lowercase
        random_string = "".join(random.choice(letters)
                                for i in range(stringLength))
        return "qs_" + random_string

    @staticmethod
    def __generate_chart_session():
        stringLength = 12
        letters = string.ascii_lowercase
        random_string = "".join(random.choice(letters)
                                for i in range(stringLength))
        return "cs_" + random_string

    @staticmethod
    def __prepend_header(st):
        return "~m~" + str(len(st)) + "~m~" + st

    @staticmethod
    def __construct_message(func, param_list):
        return json.dumps({"m": func, "p": param_list}, separators=(",", ":"))

    def __create_message(self, func, paramList):
        return self.__prepend_header(self.__construct_message(func, paramList))

    def __send_message(self, func, args):
        m = self.__create_message(func, args)
        if self.ws_debug:
            print(m)
        self.ws.send(m)

    @staticmethod
    def __create_df(raw_data, symbol):
        try:
            out = re.search(r'"s":\[(.+?)\}\]', raw_data).group(1)
            x = out.split(',{"')
            data = list()
            volume_data = True

            for xi in x:
                xi = re.split(r"\[|:|,|\]", xi)
                ts = datetime.datetime.fromtimestamp(float(xi[4]))

                row = [ts]

                for i in range(5, 10):

                    # skip converting volume data if does not exists
                    if not volume_data and i == 9:
                        row.append(0.0)
                        continue
                    try:
                        row.append(float(xi[i]))

                    except ValueError:
                        volume_data = False
                        row.append(0.0)
                        logger.debug('no volume data')

                data.append(row)

            data = pd.DataFrame(
                data, columns=["datetime", "open",
                               "high", "low", "close", "volume"]
            ).set_index("datetime")
            data.insert(0, "symbol", value=symbol)
            return data
        except AttributeError:
            logger.error("no data, please check the exchange and symbol")

    @staticmethod
    def __format_symbol(symbol, exchange, contract: int = None):

        if ":" in symbol:
            pass
        elif contract is None:
            symbol = f"{exchange}:{symbol}"

        elif isinstance(contract, int):
            symbol = f"{exchange}:{symbol}{contract}!"

        else:
            raise ValueError("not a valid contract")

        return symbol

    def get_hist(
        self,
        symbol: str,
        exchange: str = "NSE",
        interval: Interval = Interval.in_daily,
        n_bars: int = 10,
        fut_contract: int = None,
        extended_session: bool = False,
    ) -> pd.DataFrame:
        """get historical data

        Args:
            symbol (str): symbol name
            exchange (str, optional): exchange, not required if symbol is in format EXCHANGE:SYMBOL. Defaults to None.
            interval (str, optional): chart interval. Defaults to 'D'.
            n_bars (int, optional): no of bars to download, max 5000. Defaults to 10.
            fut_contract (int, optional): None for cash, 1 for continuous current contract in front, 2 for continuous next contract in front . Defaults to None.
            extended_session (bool, optional): regular session if False, extended session if True, Defaults to False.

        Returns:
            pd.Dataframe: dataframe with sohlcv as columns
        """
        symbol = self.__format_symbol(
            symbol=symbol, exchange=exchange, contract=fut_contract
        )

        interval = interval.value

        self.__create_connection()

        self.__send_message("set_auth_token", [self.token])
        self.__send_message("chart_create_session", [self.chart_session, ""])
        self.__send_message("quote_create_session", [self.session])
        self.__send_message(
            "quote_set_fields",
            [
                self.session,
                "ch",
                "chp",
                "current_session",
                "description",
                "local_description",
                "language",
                "exchange",
                "fractional",
                "is_tradable",
                "lp",
                "lp_time",
                "minmov",
                "minmove2",
                "original_name",
                "pricescale",
                "pro_name",
                "short_name",
                "type",
                "update_mode",
                "volume",
                "currency_code",
                "rchp",
                "rtc",
            ],
        )

        self.__send_message(
            "quote_add_symbols", [self.session, symbol,
                                  {"flags": ["force_permission"]}]
        )
        self.__send_message("quote_fast_symbols", [self.session, symbol])

        self.__send_message(
            "resolve_symbol",
            [
                self.chart_session,
                "symbol_1",
                '={"symbol":"'
                + symbol
                + '","adjustment":"splits","session":'
                + ('"regular"' if not extended_session else '"extended"')
                + "}",
            ],
        )
        self.__send_message(
            "create_series",
            [self.chart_session, "s1", "s1", "symbol_1", interval, n_bars],
        )
        self.__send_message("switch_timezone", [
                            self.chart_session, "exchange"])

        raw_data = ""

        logger.debug(f"getting data for {symbol}...")
        while True:
            try:
                result = self.ws.recv()
                raw_data = raw_data + result + "\n"
            except Exception as e:
                logger.error(e)
                break

            if "series_completed" in result:
                break

        return self.__create_df(raw_data, symbol)

    def search_symbol(self, text: str, exchange: str = ''):
        url = self.__search_url.format(text, exchange)

        symbols_list = []
        try:
            resp = requests.get(url)

            symbols_list = json.loads(resp.text.replace(
                '</em>', '').replace('<em>', ''))
        except Exception as e:
            logger.error(e)

        return symbols_list

    def get_token_info(self):
        """Получить информацию о текущем токене"""
        return self.token_manager.get_token_info()

    def refresh_token(self):
        """Принудительно обновить токен"""
        if self.username and self.password:
            logger.info("Принудительное обновление токена...")
            self.token_manager.delete_token()
            new_token = self.__auth(self.username, self.password)
            
            if new_token and new_token != "unauthorized_user_token":
                self.token_manager.save_token(new_token, self.username)
                self.token = new_token
                logger.info("Токен успешно обновлен")
                return True
            else:
                logger.error("Не удалось получить новый токен")
                return False
        else:
            logger.error("Нет учетных данных для обновления токена")
            return False

    def delete_saved_token(self):
        """Удалить сохраненный токен"""
        return self.token_manager.delete_token()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    tv = TvDatafeed()
    print(tv.get_hist("CRUDEOIL", "MCX", fut_contract=1))
    print(tv.get_hist("NIFTY", "NSE", fut_contract=1))
    print(
        tv.get_hist(
            "EICHERMOT",
            "NSE",
            interval=Interval.in_1_hour,
            n_bars=500,
            extended_session=False,
        )
    )
