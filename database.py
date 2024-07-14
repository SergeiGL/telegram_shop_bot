import psycopg2
import redis
from psycopg2.extras import DictCursor
from config import (
    redis_conf_keys,
    pg_conf_keys,
    is_in_production
)
import json
import multiprocessing
    
import numpy as np
from io import BytesIO
import matplotlib.pyplot as plt



def validate_text(text):
    return text.replace("'", " ").replace('"', " ")


class Database:
    def __init__(self):
        self.redis_conn = redis.StrictRedis(
                host=redis_conf_keys["host"], 
                port=redis_conf_keys["port"], 
                db=redis_conf_keys["db"],
                decode_responses=True)  # Ensures that Redis will return a string (instead of bytes)
        
        self.redis_updater_process = multiprocessing.Process(
            target=self.redis_updater,
            args=(redis_conf_keys, pg_conf_keys, is_in_production)
            )
        self.redis_updater_process.start()
        
        self.cache_pricetable_img_key = "orderbook_img"
        
        self.pg_conn = psycopg2.connect(
                host = pg_conf_keys["host"],
                dbname = pg_conf_keys["dbname"],
                user = pg_conf_keys["user"],
                password = pg_conf_keys["password"],
                port = pg_conf_keys["port"])
        self.pg_conn.autocommit = True

        prepared_statements = [
            "PREPARE add_new_user AS INSERT INTO users ( \
                        user_id, \
                        chat_id, \
                        username \
                        ) VALUES ($1, $2, $3) \
                        ON CONFLICT (user_id) DO NOTHING;",
            
            "PREPARE set_msg_with_kb AS UPDATE users \
                        SET msg_id_with_kb = $1 \
                        WHERE user_id = $2;",
            
            "PREPARE get_msg_id_with_kb AS \
                        SELECT msg_id_with_kb FROM users WHERE user_id = $1;",
            
            "PREPARE get_stock_models AS \
                        SELECT DISTINCT model FROM goods WHERE quantity_in_stock > 0 ORDER BY model",
            
            "PREPARE get_stock_versions AS \
                        SELECT version FROM goods \
                        WHERE quantity_in_stock > 0 AND model = $1 ORDER BY version",
                        
            "PREPARE get_good_data AS \
                        SELECT g.specification_name, g.model, g.version, g.description, g.photo, sp.price_USD, sp.margin_order, \
                        (SELECT exch_rate FROM exchange_rates WHERE pair = 'BUY USDT') AS exch_rate \
                    FROM goods g \
                    JOIN supplier_prices sp ON g.specification_name = sp.specification_name \
                    WHERE g.model = $1 AND g.version = $2 AND g.quantity_in_stock > 0",
            
            "PREPARE insert_error AS \
                INSERT INTO errors(error) VALUES ($1);"
        ]
        
        for prepared_statement in prepared_statements:
            with self.pg_conn.cursor() as cursor:
                cursor.execute(prepared_statement)
    
    def __del__(self):
        self.pg_conn.close()
        self.redis_conn.close()
        
        self.redis_updater_process.terminate()
        self.redis_updater_process.join()  # Wait for the process to actually terminate
        
        print("Connections closed")
    
    
    def add_new_user(self, user_id: int, chat_id: int, username: str):
        with self.pg_conn.cursor() as cursor:
            cursor.execute("""EXECUTE add_new_user (%s, %s, %s);""", (user_id, chat_id, validate_text(username)))
    
    
    def set_msg_with_kb(self, user_id: int, value: int) -> None:
        with self.pg_conn.cursor() as cursor:
            cursor.execute("""EXECUTE set_msg_with_kb (%s, %s);""", (value, user_id))
            affected_rows = cursor.rowcount
        
        if affected_rows == 0:
            raise ValueError(f"DB: error in setting value\nset_user_attribute(self, {user_id=}, {value=}")
    
    
    def get_msg_id_with_kb(self, user_id) -> int:
        with self.pg_conn.cursor() as cursor:
            cursor.execute("""EXECUTE get_msg_id_with_kb (%s);""", (user_id, ))
            data = cursor.fetchone()
        return data[0]
    
    def get_stock_models(self):
        cache_key = "models"
        
        cached_result = self.redis_conn.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        else:
            if not is_in_production: print("DB request")
            with self.pg_conn.cursor() as cursor:
                cursor.execute("""EXECUTE get_stock_models;""")
                res = cursor.fetchall()
                models = [model for (model,) in res]
                self.redis_conn.set(cache_key, json.dumps(models))
                return models
    
    def get_stock_versions(self, model):
        cache_key = f"version{model}"
        
        cached_result = self.redis_conn.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        else:
            if not is_in_production: print("DB request")
            with self.pg_conn.cursor() as cursor:
                cursor.execute("""EXECUTE get_stock_versions (%s);""", (model, ))
                res = cursor.fetchall()
                versions = [vers for (vers,) in res]
                self.redis_conn.set(cache_key, json.dumps(versions))
                return versions
    
    def get_good_data(self, model : str, version: str):
        cache_key = f"good{model}{version}"
        
        cached_result = self.redis_conn.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        else:
            if not is_in_production: print("DB request")
            with self.pg_conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""EXECUTE get_good_data (%s, %s);""", (model, version))
                good_data = cursor.fetchone()
                
                if good_data is None:
                    return False
                
                good_data_dict = dict(good_data)
                
                self.redis_conn.set(cache_key, json.dumps(good_data_dict))
                return good_data_dict
    
    def set_pricetable_img_file_id(self, img_file_id) -> None:
        if not is_in_production: print("redis set")
        self.redis_conn.set(self.cache_pricetable_img_key, json.dumps(img_file_id))
    
    def get_pricetable_img(self):
        cached_result = self.redis_conn.get(self.cache_pricetable_img_key)
        if cached_result:
            return json.loads(cached_result)
        else:
            if not is_in_production: print("DB request")
            def create_image(spec_names, consumer_prices):
                fig, ax = plt.subplots()
                ax.axis('off')
                table = ax.table(cellText=list(zip(spec_names, consumer_prices)),
                                colLabels=['specification_name', 'consumer_order_price'],
                                cellLoc='center', loc='center')
                table.auto_set_font_size(False)
                table.set_fontsize(8)
                table.scale(1, 1.5)
                
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
                plt.close(fig)
                return buffer.getvalue()

            with self.pg_conn.cursor() as cur:
                cur.execute("""
                    SELECT sp.specification_name, sp.price_usd, sp.margin_order, er.exch_rate
                    FROM supplier_prices sp
                    CROSS JOIN (SELECT exch_rate FROM exchange_rates WHERE pair = 'BUY USDT') er
                """)
                data = cur.fetchall()
            
            spec_names, prices, margins, rates = zip(*data)
            consumer_prices = np.round(np.array(prices) * np.array(rates) * (1 + np.array(margins) / 100), -2).astype(int)
            return create_image(list(spec_names), list(consumer_prices))
    
    def insert_error(self, error_text: str):
        with self.pg_conn.cursor() as cursor:
            cursor.execute("""EXECUTE insert_error (%s);""", (validate_text(error_text), ))
    
    
    
    
    def redis_updater(self, redis_config, pg_config, is_in_production): 
        import psycopg2
        import redis
        from time import sleep
        import traceback
        from datetime import datetime
        import select

        def clear_redis_db(redis_client):
            redis_client.flushdb()
            print(f"All Redis keys cleared - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        while True:
            try:
                with redis.StrictRedis(
                    host=redis_config["host"],
                    port=redis_config["port"],
                    db=redis_config["db"],
                    decode_responses=True
                ) as redis_client:
                    pg_conn = psycopg2.connect(
                        dbname=pg_config["dbname"],
                        user=pg_config["user"],
                        password=pg_config["password"],
                        host=pg_config["host"],
                        port=pg_config["port"]
                    )
                    pg_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

                    with pg_conn.cursor() as cur:
                        cur.execute("LISTEN table_change;")
                    
                    clear_redis_db(redis_client)
                    print("Start listening for table changes...")

                    while True:
                        if select.select([pg_conn], [], [], None) == ([], [], []):
                            print("ERROR\nselect.select([conn], [], [], None) == ([], [], [])")
                        else:
                            pg_conn.poll()
                            while pg_conn.notifies:
                                notify = pg_conn.notifies.pop(0)
                                if not is_in_production: print(f"Table changed: {notify.payload} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                clear_redis_db(redis_client)
            except Exception:
                error = "ERROR\nRedis_updater:\n" + traceback.format_exc()
                print(error)
                sleep(600)



if __name__ == "__main__":
    Database()