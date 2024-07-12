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
        """CREATE TABLE IF NOT EXISTS supplier_prices (
                specification_name VARCHAR(125) PRIMARY KEY,
                price_USD INTEGER DEFAULT 0 NOT NULL,
                margin_stock real DEFAULT 20.0 NOT NULL,
                margin_order real DEFAULT 15.0 NOT NULL
                );""")
    
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS goods (
                specification_name VARCHAR(125) PRIMARY KEY,
                model VARCHAR(25) NOT NULL,
                version VARCHAR(25) NOT NULL,
                quantity_in_stock INTEGER DEFAULT 0 NOT NULL,
                photo BYTEA NOT NULL,
                description VARCHAR(500) NOT NULL,
                FOREIGN KEY (specification_name) REFERENCES supplier_prices(specification_name),
                UNIQUE (model, version)
                );""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_model ON goods (model);""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_version ON goods (version);""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_quantity_in_stock ON goods (quantity_in_stock);""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_specification_name ON goods (specification_name);""")
    
    
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS exchange_rates(
                pair VARCHAR(20) PRIMARY KEY NOT NULL,
                exch_rate real DEFAULT 150 NOT NULL
                );""")


    cursor.execute(
        """CREATE TABLE IF NOT EXISTS errors(
                date timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
                error TEXT NOT NULL
                );""")



    cursor.close()
    conn.close()