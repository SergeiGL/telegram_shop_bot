import requests
from bs4 import BeautifulSoup
import psycopg2
import config
from time import sleep
from tg import send_telegram_message
from apscheduler.schedulers.background import BlockingScheduler
import traceback

def update_rates_in_sql(rates_dict: dict) -> list[tuple]:
    conn = psycopg2.connect(
            host = config.db_config['host'],
            dbname = config.db_config['dbname'],
            user = config.db_config['user'],
            password = config.db_config['password'],
            port = config.db_config['port'],
            )
    conn.autocommit = True
    
    with conn.cursor() as cursor:
        for pair, rate in rates_dict.items():
            cursor.execute("""
                INSERT INTO exchange_rates (pair, rate)
                VALUES (%s, %s)
                ON CONFLICT (pair) DO UPDATE SET rate = EXCLUDED.rate;""", (pair, rate))
        
        cursor.execute("""SELECT * FROM exchange_rates;""")
        saved_rates = cursor.fetchall()
    
    conn.close()
    return saved_rates


def update_exchange_rate(SOURCE_LIST) -> None:
    try:
        result_rates_dict = {}
        
        for pair, link in SOURCE_LIST.items():
            response = requests.get(link)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
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
        send_telegram_message("<b>ERROR:\nSQL EXCHANGE RATES</b>\n\n" + str(traceback.format_exc()))




def update_exchange_rate_thread():
    # Create an instance of BackgroundScheduler
    scheduler = BlockingScheduler()

    # Add jobs to the scheduler to be executed every minute at specific seconds
    # Each job passes a different argument to the function
    scheduler.add_job(update_exchange_rate, 'cron', hour=23, minute=12, second=5, max_instances=1, coalesce=True, misfire_grace_time=180, \
        args = [
                {
                    "BUY USDT": "https://www.bestchange.ru/tinkoff-to-tether-trc20.html",
                    "SELL USDT": "https://www.bestchange.ru/tether-trc20-to-tinkoff.html"
                }
            ])

    # Start the scheduler
    scheduler.start()


if __name__ == "__main__":
    update_exchange_rate_thread()