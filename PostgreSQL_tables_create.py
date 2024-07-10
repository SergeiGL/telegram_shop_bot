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
                username VARCHAR(100) NOT NULL,

                first_seen timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
                interactions_counter BIGINT DEFAULT 0 NOT NULL,
                
                msg_id_with_kb BIGINT DEFAULT -1 NOT NULL
                );""")


    cursor.execute(
        """CREATE TABLE IF NOT EXISTS goods (
                model VARCHAR(25) NOT NULL,
                version VARCHAR(25) NOT NULL,
                full_name VARCHAR(60) GENERATED ALWAYS AS (model || ' ' || version) STORED PRIMARY KEY,
                description VARCHAR(500) NOT NULL,
                quantity_in_stock INTEGER DEFAULT 0 NOT NULL,
                price_RUB INTEGER DEFAULT 0 NOT NULL,
                photo BYTEA NOT NULL
                );""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_model_quantity_in_stock ON goods (model, quantity_in_stock);""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_quantity_in_stock ON goods (quantity_in_stock);""")
    
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS exchange_rates(
                pair VARCHAR(20) PRIMARY KEY NOT NULL,
                rate real DEFAULT 100 NOT NULL
                );""")


    cursor.execute(
        """CREATE TABLE IF NOT EXISTS errors(
                date timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
                error TEXT NOT NULL
                );""")



    cursor.close()
    conn.close()