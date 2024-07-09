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
        """CREATE TABLE IF NOT EXISTS users(
                tg_id BIGINT PRIMARY KEY NOT NULL,
                chat_id BIGINT NOT NULL,
                username varchar(100) NOT NULL,

                first_seen timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
                interactions_counter BIGINT DEFAULT 0 NOT NULL,
                
                msg_id_with_kb BIGINT DEFAULT -1 NOT NULL
                );""")


    cursor.execute(
        """CREATE TABLE IF NOT EXISTS goods (
                full_name TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                description TEXT NOT NULL,
                quantity_in_stock INTEGER DEFAULT 0 NOT NULL,
                price_RUB INTEGER DEFAULT 0 NOT NULL
                );""")

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS goods_photos (
                model TEXT PRIMARY KEY,
                photo BYTEA NOT NULL
                );""")
    

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS exchange_rates(
                pair varchar(100) PRIMARY KEY NOT NULL,
                rate real DEFAULT 100 NOT NULL
                );""")


    cursor.execute(
        """CREATE TABLE IF NOT EXISTS errors(
                date timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
                error TEXT NOT NULL
                );""")



    cursor.close()
    conn.close()