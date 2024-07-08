import psycopg2
import config

if __name__ == "__main__":

        conn = psycopg2.connect(
                        host = config.db_config['host'],
                        dbname = config.db_config['dbname'],
                        user = config.db_config['user'],
                        password = config.db_config['password'],
                        port = config.db_config['port'],
                        )
        
        conn.autocommit = True
        cursor = conn.cursor()
        
        cursor.execute(
                """INSERT INTO exchange_rates(
                        pair,
                        rate)
                VALUES ('USD_RUB', 100), ('EUR_RUB', 110)
                ON CONFLICT (pair) DO NOTHING
                ;""")

        cursor.close()
        conn.close()

