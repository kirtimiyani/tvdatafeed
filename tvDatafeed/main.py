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
    __search_url = 'https://symbol-search.tradingview.com/symbol_search/v3/?text={}&hl=1&exchange={}&lang=en&search_type=undefined&domain=production&sort_by_country=IN'
    __ws_headers = json.dumps({"Origin": "https://data.tradingview.com"})
    __signin_headers = {'Referer': 'https://www.tradingview.com'}
    __ws_timeout = 5
    
    # Constants for token verification

    __token_validation_timeout = 10
    __token_validation_wait_time = 5
    __max_retry_attempts = 2
    
    # Constants for network operations
    __network_retry_attempts = 3
    __network_retry_delay = 2

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
        """Authentication with token management"""

        # Attempt to load the saved token

        if username is None or password is None:
            logger.info("Credentials not provided, using unauthorized mode")
            return None
        
        # Attempt to load the saved token
        saved_token = self.token_manager.load_token(username)
        if saved_token:
            logger.info("A saved token has been found, we're checking its validity...")
            
            # Check the token's validity
            if self.__is_token_valid(saved_token):
                logger.info("The saved token is valid, let's use it")
                return saved_token
            else:
                logger.warning("The saved token is invalid, delete it and get a new one")
                self.token_manager.delete_token()
        
        # Receive a new token
        logger.info("Getting a new token...")
        new_token = self.__auth(username, password)
        
        # Save the new token if it was received successfully
        if new_token and new_token != "unauthorized_user_token":
            logger.info("The new token has been received successfully, let's save it.")
            self.token_manager.save_token(new_token, username)
        
        return new_token

    def __is_token_valid(self, token):
        """Checking the validity of the token via a test request"""
        try:
            logger.debug("We are starting to check the token validity...")
            
            # Create a test connection to verify the token
            test_ws = create_connection(
                "wss://data.tradingview.com/socket.io/websocket", 
                headers=self.__ws_headers, 
                timeout=self.__token_validation_timeout
            )
            
            logger.debug("A WebSocket connection for token verification has been created.")
            
            # Send the token for verification
            test_message = self.__prepend_header(
                self.__construct_message("set_auth_token", [token])
            )
            test_ws.send(test_message)
            logger.debug("The token has been sent for verification.")
            
            # Wait for a response
            start_time = time.time()
            received_response = False
            auth_error = False
            
            while time.time() - start_time < self.__token_validation_wait_time:
                try:
                    result = test_ws.recv()
                    received_response = True
                    logger.debug(f"Response received while verifying token: {result[:200]}...")
                    
                    # Check for authentication errors
                    if "critical_error" in result or "auth_error" in result or "unauthorized" in result.lower():
                        auth_error = True
                        logger.debug("An authentication error was detected in the response.")
                        break
                    
                    # If you received a normal response, the token is valid.
                    if result and not auth_error:
                        test_ws.close()
                        logger.debug("Token valid")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Exception while receiving response: {e}")
                    break
            
            test_ws.close()
            
            # If we didn't receive a response or there was an authentication error
            if not received_response:
                logger.debug("No response received from the server when verifying the token")
                # If we didn't receive a response, but there was no obvious error, we consider the token valid.
                # This could be due to network issues, not token issues.
                return True
            elif auth_error:
                logger.debug("The token is invalid due to an authentication error.")
                return False
            else:
                logger.debug("The token is considered valid")
                return True
            
        except Exception as e:
            logger.debug(f"Error validating token: {e}")
            # If a connection error occurs, consider the token valid.
            # It's better to try using the token than to delete it immediately.
            return True

    def __auth(self, username, password):
        """Original authentication method"""
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
                print(token)
            except Exception as e:
                logger.error('Captha required, please singin manually')
                token = None
                
                try:
                    driver = webdriver.Chrome()
                    driver.get(self.__sign_in_url)
                    
                    time.sleep(2)  
                    print("Please solve the captcha and sign in.")
    
                    try:
                        while True:
                            current_url = driver.current_url
                            if current_url in ["https://www.tradingview.com", "https://ru.tradingview.com/", "https://in.tradingview.com/"]:
                                print("Successful login!")
                                break
                            time.sleep(1)  # Check every 1 second

                    except Exception as e:
                        logger.error("Error validating URL: %s", str(e))
                        driver.quit()
                        return None
                        
                    # Getting page HTML
                    html = driver.page_source
                    driver.quit() # Closing browser
                    # Parsing HTML to extract auth_token
                    soup = BeautifulSoup(html, 'html.parser')
    
                    # Пример поиска токена в скриптах
                    script_tags = soup.find_all('script')
                    for script in script_tags:
                        if 'auth_token' in script.text:
                            # Token retrieval example

                            try:
                                # Assume the token is represented as 'auth_token":"YOUR_TOKEN"
                                start = script.text.find('auth_token":"') + len('auth_token":"')
                                end = script.text.find('"', start)
                                token = script.text[start:end]
                                logger.info("Found auth_token: %s", token)
                                print("Found auth_token success")
                                return token
                            except Exception as e:
                                logger.error("Error retrieving token: %s", str(e))
                                return None
            
                    logger.error("auth_token not found on the page.")
                    return None
    
                except Exception as e:
                    print("ERROR:", str(e))
                    logger.error('error while signin')
                    token = None
            print("token retrived successfully")
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
        _retry_count: int = 0,
    ) -> pd.DataFrame:
        """get historical data

        Args:
            symbol (str): symbol name
            exchange (str, optional): exchange, not required if symbol is in format EXCHANGE:SYMBOL. Defaults to None.
            interval (str, optional): chart interval. Defaults to 'D'.
            n_bars (int, optional): no of bars to download, max 5000. Defaults to 10.
            fut_contract (int, optional): None for cash, 1 for continuous current contract in front, 2 for continuous next contract in front . Defaults to None.
            extended_session (bool, optional): regular session if False, extended session if True, Defaults to False.
            _retry_count (int, optional): internal parameter for retry logic. Defaults to 0.

        Returns:
            pd.Dataframe: dataframe with sohlcv as columns
        """
        logger.debug(f"get_hist called: symbol={symbol}, exchange={exchange}, interval={interval}, n_bars={n_bars}, retry_count={_retry_count}")
        
        # Сохраняем оригинальный interval для рекурсивных вызовов
        original_interval = interval
        
        symbol = self.__format_symbol(
            symbol=symbol, exchange=exchange, contract=fut_contract
        )

        # Преобразуем interval в строку для API
        if hasattr(interval, 'value'):
            interval_str = interval.value
        else:
            # If interval is already a string (for example, during a recursive call)
            interval_str = interval
            logger.debug(f"Interval is already a string: {interval_str}")

        try:
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
                "quote_add_symbols", [self.session, symbol]
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
                [self.chart_session, "s1", "s1", "symbol_1", interval_str, n_bars],
            )
            self.__send_message("switch_timezone", [
                                self.chart_session, "exchange"])

            raw_data = ""
            auth_error_detected = False

            logger.debug(f"getting data for {symbol}...")
            while True:
                try:
                    result = self.ws.recv()
                    raw_data = raw_data + result + "\n"
                    
                    # Checking for authentication and parameter errors
                    if "critical_error" in result:
                        # Checking that this is an authentication error, not a parameter error
                        if "invalid_parameters" in result:
                            logger.warning(f"A parameter error (not authentication) was detected: {result[:500]}...")
                            # This is a parameter error, not an authentication error - continue
                        else:
                            auth_error_detected = True
                            logger.warning(f"A critical error was detected in the server response: {result[:500]}...")
                            break
                    elif "auth_error" in result or "unauthorized" in result.lower():
                        auth_error_detected = True
                        logger.warning(f"An authentication error was detected in the server response: {result[:500]}...")
                        break
                        
                except Exception as e:
                    logger.error(e)
                    break

                if "series_completed" in result:
                    break

            # If an authentication error was detected and credentials are available for a retry

            if auth_error_detected and self.username and self.password and _retry_count < self.__max_retry_attempts:
                logger.info("Attempt to refresh the token due to an authentication error...")
                if self.refresh_token():
                    logger.info("The token has been refreshed, retrying the request...")
                    return self.get_hist(symbol, exchange, original_interval, n_bars, fut_contract, extended_session, _retry_count + 1)
                else:
                    logger.error("Failed to refresh the token")

            result_df = self.__create_df(raw_data, symbol)
            
            # Additional check: if data was not received and the token can be refreshed

            if result_df is None and self.username and self.password and _retry_count < self.__max_retry_attempts:
                logger.warning("Data was not received; the token may have expired. Attempting to refresh...")
                if self.refresh_token():
                    logger.info("Token updated, repeating the request...")
                    return self.get_hist(symbol, exchange, original_interval, n_bars, fut_contract, extended_session, _retry_count + 1)
            
            return result_df
            
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Error receiving data: {e}")
            
            # Checking for network errors (SSL timeout, connection errors, etc.)
            network_errors = [
                "handshake operation timed out",
                "connection timed out", 
                "connection refused",
                "connection reset",
                "ssl",
                "timeout",
                "network"
            ]
            
            is_network_error = any(err in error_msg for err in network_errors)
            
            if is_network_error and _retry_count < self.__network_retry_attempts:
                logger.warning(f"A network error was detected, attempting {_retry_count + 1} of {self.__network_retry_attempts}")
                logger.info(f"Waiting {self.__network_retry_delay} seconds before retrying...")
                time.sleep(self.__network_retry_delay)
                return self.get_hist(symbol, exchange, original_interval, n_bars, fut_contract, extended_session, _retry_count + 1)
            
            # If this is an authentication error and it is possible to refresh the token

            elif ("auth" in error_msg or "unauthorized" in error_msg) and self.username and self.password and _retry_count < self.__max_retry_attempts:
                logger.info("Authentication error detected, attempting to refresh the token...")
                if self.refresh_token():
                    logger.info("Token updated, repeating the request...")
                    return self.get_hist(symbol, exchange, original_interval, n_bars, fut_contract, extended_session, _retry_count + 1)
            
            # If all attempts have been exhausted or it is not a network/authentication error
            if is_network_error and _retry_count >= self.__network_retry_attempts:
                logger.error(f"All attempts ({self.__network_retry_attempts}) to resolve a network error have been exhausted")
            
            raise e

    def search_symbol(self, text: str, exchange: str = ''):
        url = self.__search_url.format(text, exchange)

        symbols_list = []
        try:
            headers = {
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "en-US,en;q=0.9",
                "DNT": "1",
                "Origin": "https://in.tradingview.com",
                "Referer": "https://in.tradingview.com/",
                "Sec-CH-UA": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
                "Sec-CH-UA-Mobile": "?0",
                "Sec-CH-UA-Platform": '"Windows"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
            }
              
            resp = requests.get(url, headers=headers)
            
            symbols_list = json.loads(resp.text.replace('</em>', '').replace('<em>', ''))
        except Exception as e:
            logger.error(e)

        return symbols_list

    def get_token_info(self):
        """Get information about the current token
"""
        return self.token_manager.get_token_info()

    def refresh_token(self):
        """Force refresh token"""
        if self.username and self.password:
            logger.info("Forced token refresh...")
            self.token_manager.delete_token()
            new_token = self.__auth(self.username, self.password)
            
            if new_token and new_token != "unauthorized_user_token":
                self.token_manager.save_token(new_token, self.username)
                self.token = new_token
                logger.info("Token successfully refreshed")
                return True
            else:
                logger.error("Failed to obtain a new token")
                return False
        else:
            logger.error("No credentials to refresh the token")
            return False

    def delete_saved_token(self):
        """Delete saved token"""

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
