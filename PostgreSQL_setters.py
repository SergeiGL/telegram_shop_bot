import psycopg2
import config


conn = psycopg2.connect(
                host = config.db_config['host'],
                dbname = config.db_config['dbname'],
                user = config.db_config['user'],
                password = config.db_config['password'],
                port = config.db_config['port'],
                )

conn.autocommit = True
cursor = conn.cursor()


# ---------------------------------------------------- OPENAI PRICING ------------------------------------------------------
def initialize_OPENAI_MODEL_prices():
        cursor.execute(
                f"""INSERT INTO model_pricing(
                model,
                input_price,
                output_price
                ) VALUES ('oai_3.5_t', 1, 1);""")
        
        cursor.execute(
                f"""INSERT INTO model_pricing(
                model,
                input_price,
                output_price
                ) VALUES ('oai_4_t', 1, 1);""")


def change_OPENAI_MODEL_prices(gpt_35_turbo_input_price=None, gpt_35_turbo_output_price=None, gpt_4_tubro_input_price=None, gpt_4_tubro_output_price=None):
        
        if gpt_35_turbo_input_price:
                cursor.execute("UPDATE model_pricing SET input_price = %s WHERE model = 'oai_3.5_t'", (gpt_35_turbo_input_price,))
        
        if gpt_35_turbo_output_price:
                cursor.execute("UPDATE model_pricing SET output_price = %s WHERE model = 'oai_3.5_t'", (gpt_35_turbo_output_price,))

        if gpt_4_tubro_input_price:
                cursor.execute("UPDATE model_pricing SET input_price = %s WHERE model = 'oai_4_t'", (gpt_4_tubro_input_price,))
        
        if gpt_4_tubro_output_price:
                cursor.execute("UPDATE model_pricing SET output_price = %s WHERE model = 'oai_4_t'", (gpt_4_tubro_output_price,))




# ---------------------------------------------------- EXCHANGE RATE ------------------------------------------------------
def initialize_exchange_rate():
        cursor.execute(
                f"""INSERT INTO exchange_rate(
                pair
                ) VALUES ('USD_RUB');""")



def update_exchange_rate(pair="USD_RUB", rate=100):
        cursor.execute("UPDATE exchange_rate SET rate = %s WHERE pair = %s", (rate, pair))








# ---------------------------------------------------- USAGE ------------------------------------------------------

initialize_OPENAI_MODEL_prices()
initialize_exchange_rate()

change_OPENAI_MODEL_prices(gpt_35_turbo_input_price=0.001/1000, gpt_35_turbo_output_price=0.002/1000, gpt_4_tubro_input_price=0.01/1000, gpt_4_tubro_output_price=0.03/1000)
update_exchange_rate(pair="USD_RUB", rate=100)


cursor.close()
conn.close()

