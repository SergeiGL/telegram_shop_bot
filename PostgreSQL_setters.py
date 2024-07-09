import psycopg2
import config
import os

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

        with conn.cursor() as cursor:
            for good_name in os.listdir('goods'):
                with open(f'goods/{good_name}/description.txt', 'r') as f:
                    description = "\n".join(f.readlines())
                
                with open(f'goods/{good_name}/picture.png', 'rb') as f:
                    binary_picture = f.read()
                
                for memory_size_str in [" 256 GB", " 512 GB"]:
                    cursor.execute("""INSERT INTO goods (full_name, model, description, quantity_in_stock) 
                        VALUES (%s, %s, %s, %s) ON CONFLICT (full_name) DO NOTHING""", 
                        (good_name+memory_size_str, good_name, description, 1)
                        )
                
                cursor.execute("""INSERT INTO goods_photos (model, photo) 
                    VALUES (%s, %s)""", 
                    (good_name, psycopg2.Binary(binary_picture))
                    )
        
        cursor.close()
        conn.close()

