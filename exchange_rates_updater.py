import requests
from bs4 import BeautifulSoup
import psycopg2
from config import pg_conf_keys, is_in_production
from time import sleep
from tg import send_telegram_message
from apscheduler.schedulers.background import BlockingScheduler
import traceback
from fake_useragent import UserAgent



def update_rates_in_sql(rates_dict: dict) -> list[tuple]:
    conn = psycopg2.connect(
            host = pg_conf_keys['host'],
            dbname = pg_conf_keys['dbname'],
            user = pg_conf_keys['user'],
            password = pg_conf_keys['password'],
            port = pg_conf_keys['port'],
            )
    conn.autocommit = True
    
    with conn.cursor() as cursor:
        for pair, rate in rates_dict.items():
            cursor.execute("""
                INSERT INTO exchange_rates (pair, exch_rate)
                VALUES (%s, %s)
                ON CONFLICT (pair) DO UPDATE SET exch_rate = EXCLUDED.exch_rate;""", (pair, rate))
        
        cursor.execute("""SELECT * FROM exchange_rates;""")
        saved_rates = cursor.fetchall()
    
    conn.close()
    return saved_rates


def update_exchange_rate() -> None:
    SOURCE_LIST = {
                    "BUY USDT": "https://www.bestchange.ru/tinkoff-to-tether-trc20.html",
                    "SELL USDT": "https://www.bestchange.ru/tether-trc20-to-tinkoff.html"
                }
    
    try:
        result_rates_dict = {}

        for pair, link in SOURCE_LIST.items():
            response = requests.get(link, 
                                    headers = {
                                            'authority': 'www.bestchange.com',
                                            'cache-control': 'max-age=0',
                                            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                                            'sec-ch-ua-mobile': '?0',
                                            'sec-fetch-dest': 'document',
                                            'sec-fetch-mode': 'navigate',
                                            'sec-fetch-site': 'none',
                                            'sec-fetch-user': '?1',
                                            'upgrade-insecure-requests': '1',
                                            'user-agent': UserAgent().random
                                        },
                                    cookies = {'session_id': '1234567890abcdef', 'tracking_id': 'abcdef1234567890'})
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            first_row = soup.find('tbody').find('tr')
            
            if "BUY" in pair.upper():
                exchange_rate = first_row.find_all('td', class_='bi')[0].find('div', class_='fs').text.strip().split()[0]
            elif "SELL" in pair.upper():
                exchange_rate = first_row.find_all('td', class_='bi')[1].text.strip().split()[0]
            else:
                raise ValueError(f"No BUY or SELL in pair={pair}")
            
            exchange_rate = float(exchange_rate)
            assert(exchange_rate > 0)
            
            result_rates_dict[pair] = exchange_rate
            
            sleep(10)

        assert (result_rates_dict["BUY USDT"] >= result_rates_dict["SELL USDT"])
        
        saved_rates = update_rates_in_sql(result_rates_dict)
        send_telegram_message("<b>UPDATE:\nSQL EXCHANGE RATES</b>\n\n" + "\n".join(f"{action}: {value}" for action, value in saved_rates))
    
    except Exception:
        if is_in_production: 
            send_telegram_message("<b>ERROR:\nSQL EXCHANGE RATES</b>\n\n" + str(traceback.format_exc()))
        else: print(str(traceback.format_exc()))




def update_exchange_rate_scheduler():
    # Create an instance of BackgroundScheduler
    scheduler = BlockingScheduler()

    # Add jobs to the scheduler to be executed every minute at specific seconds
    # Each job passes a different argument to the function
    scheduler.add_job(update_exchange_rate, 
                        'cron', 
                        hour=23,
                        minute=0,
                        second=5,
                        max_instances=1,
                        coalesce=True,
                        misfire_grace_time=180
                        )

    # Start the scheduler
    scheduler.start()
