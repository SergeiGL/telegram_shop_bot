import psycopg2
import config
from random import randint


if __name__ == "__main__":
    
    conn = psycopg2.connect(
            host = config.db_config['host'],
            dbname = config.db_config['dbname'],
            user = config.db_config['user'],
            password = config.db_config['password'],
            port = config.db_config['port'],
            )

    conn.autocommit = True
    
    with conn.cursor() as cursor:
        for model in ["iPhone 15", "iPhone 14"]:
            for version in ["256GB ⬜", "512GB ⬛", "PRO 256GB ⬜", "PRO 512GB ⬛"]:
                cursor.execute(
                    """INSERT INTO goods(
                        model,
                        version,
                        description,
                        quantity_in_stock,
                        price_rub,
                        photo)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (full_name) DO NOTHING;""", (model, version, f"Nice {model+" "+ version}. You could by it :-)", 1, randint(10_000, 100_000) , \
                    psycopg2.Binary(open('assets/tech_shop_logo_only_dark.png', 'rb').read())))
    
    conn.close()
