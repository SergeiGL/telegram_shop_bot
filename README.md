# Telegram Shop Bot

## Overview
A sophisticated Telegram bot that functions as an online shop, built with Python. The bot utilizes PostgreSQL for data storage and Redis for caching to optimize response times. It features automatic USD/RUB exchange rate updates for real-time pricing and runs as a system service.

## Features
- PostgreSQL database integration for reliable data storage
- Redis caching system for improved performance
- Automatic USD/RUB exchange rate updates for dynamic pricing
- Systemd service integration for automatic startup
- Smooth, simple interface for intuitive navigation

## Prerequisites
Before installation, ensure you have the following:
- Python 3.x
- PostgreSQL
- Redis
- Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))

## Installation

### 1. Set up the environment
```bash
# Create virtual environment
python3 -m venv bot_venv

# Activate virtual environment
source bot_venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure the System Service
```bash
# Copy service file to systemd
sudo cp tech_shop_bot.service /etc/systemd/system/

# Important: Modify the service file
# Edit /etc/systemd/system/tech_shop_bot.service to update:
# - Working directory path
# - Python executable path
# - Possibly something else

# Reload daemon and enable service
sudo systemctl daemon-reload
sudo systemctl enable tech_shop_bot.service
```

### 3. Configuration Setup
1. Create `config.py` file based on the template below
2. Run `get_file_id.py` to upload static assets (logo, menu animations) to Telegram
3. Update the config file with obtained file IDs

```python
is_in_production = False

if is_in_production:
    telegram_bot_token = "YOUR_PRODUCTION_BOT_TOKEN"
    telegram_alerts_chats = ["ALERT_CHAT_IDS"]
    telegram_alerts_token = "ALERTS_BOT_TOKEN"
    
    good_picture_sample_file_id = "SAMPLE_PICTURE_ID"
    menu_anim_file_id = "MENU_ANIMATION_ID"
    
    order_description_text = "YOUR_ORDER_DESCRIPTION"
    
    is_drop_all_tables = False
    is_set_tables = False
    
    pg_conf_keys = {
        'host': "localhost",
        'dbname': "tech_shop_prod",
        'user': "YOUR_USERNAME",
        'password': "YOUR_PASSWORD",
        'port': "5432",
    }
else:
    # Development configuration
    # ... (similar structure as production)

redis_conf_keys = {
    "host": "localhost",
    "port": "6379",
    "db": "1"
}
```

### 4. Database Setup
1. Run `PostgreSQL_tables_create.py` to initialize the database schema
2. Add products to the database tables


## Running the Bot

### Check Services Status
```bash
sudo systemctl status redis-server.service
sudo systemctl status postgresql
sudo systemctl status tech_shop_bot.service
```

### Start the Bot
```bash
sudo systemctl start tech_shop_bot.service
```


Enjoy using the Bot!
If you find it helpful, don't forget to star the repository! ⭐
