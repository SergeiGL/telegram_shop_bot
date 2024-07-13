from telegram import Bot
import config
import asyncio

async def get_file_id(photo_path):
    bot = Bot(token=config.telegram_bot_token)
    
    with open(photo_path, 'rb') as photo_file:
        msg = await bot.send_photo(chat_id=config.telegram_alerts_chats[0], photo=photo_file)
        file_id = msg.photo[-1].file_id
        print(file_id)
        return file_id, msg



if __name__ == "__main__":
    res = asyncio.run(get_file_id("assets/tech_shop_logo_dark.png"))
    print(res)