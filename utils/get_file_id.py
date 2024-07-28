from telegram import Bot
import config
import asyncio

async def get_photo_file_id(photo_path):
    bot = Bot(token=config.telegram_bot_token)
    
    with open(photo_path, 'rb') as photo_file:
        msg = await bot.send_photo(chat_id=config.telegram_alerts_chats[0], photo=photo_file)
        file_id = msg.photo[-1].file_id
        return file_id, msg

async def get_anim_file_id(anim_path):
    bot = Bot(token=config.telegram_bot_token)

    msg = await bot.send_animation(chat_id=config.telegram_alerts_chats[0], animation=anim_path)
    file_id = msg.animation.file_id
    return file_id, msg


if __name__ == "__main__":
    file_id, msg = asyncio.run(get_photo_file_id("assets/tech_shop_logo_dark.png"))
    print(f"Photo {file_id=}")
    
    
    file_id, msg = asyncio.run(get_anim_file_id("assets/logo_animation.gif"))
    print(f"Animation {file_id=}")
    