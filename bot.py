import asyncio
import json
from os import path
import traceback
import requests

from telegram import (
    Update,
    # InputMedia,
    InputMediaPhoto,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    AIORateLimiter,
    filters,
    PreCheckoutQueryHandler,

)

import database
import keyboards as kb

import config


def timing_wrapper(func):
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"Function {func.__name__} took {(end - start):.6f} seconds to run.")
        return result
    return wrapper








async def try_msg_delete(chat_id, message_id, context):
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id = message_id)
        return True
    except: return False


async def db_msg_delete(what_to_delete, user_id, chat_id, context):
    msg_id_to_delete = db.get_attribute(from_="users", value=user_id, select = what_to_delete)
    
    if msg_id_to_delete != -1:
        if await try_msg_delete(chat_id, msg_id_to_delete, context): 
            db.set_user_attribute(user_tg_id = user_id, key = what_to_delete, value = -1)


async def register_user_if_not_exist(user, user_id: int, chat_id: int):
    db.add_new_user_if_not_exist(
        user_tg_id = user_id,
        chat_id = chat_id,
        username=user.username or "Unknown")


# /start special entry function
# THE WHOLE CODE IS BUILD WITH THE ASSUMPTION THAT THE USER WILL START FROM HERE
async def start_handle(update: Update, context: CallbackContext) -> None:
    if update is None or update.message is None:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    await try_msg_delete(chat_id=chat_id, message_id = update.message.id, context=context)

    await register_user_if_not_exist(user = update.effective_user , user_id = user_id, chat_id=chat_id)
    
    await db_msg_delete("msg_id_with_kb", user_id, chat_id, context)
    
    msg = await context.bot.send_photo(
                                chat_id=chat_id,
                                photo=PATH_TO_MENU_PICTURE,
                                reply_markup= kb.start_menu(),
                                disable_notification=True,
                            )
    db.set_user_attribute(user_tg_id=user_id, key = "msg_id_with_kb", value = msg.id) # sets last message with kb




async def button_callback_handler(update: Update, context: CallbackContext) -> None:
    if update is None:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = update.effective_message.id
    
    query = update.callback_query
    await query.answer() # prevents errors
    callback = json.loads(query.data)
    from_ = callback.get("from")
    to_ = callback.get("to")

    
    if from_ == "menu" and to_ == "stock":
        await query.edit_message_reply_markup(reply_markup=kb.stock(goods_in_stock = db.get_goods_in_stock()))

    elif from_ == "stock" and to_ == "menu":
        await query.edit_message_reply_markup(reply_markup=kb.start_menu())

    elif (full_name := callback.get("good")) != None:
        if not await try_msg_delete(chat_id=chat_id, message_id = message_id, context=context):
            await query.edit_message_reply_markup(reply_markup=None)
        
        good_info, good_photo = db.get_info_and_photos(full_name)
        
        msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=good_photo,
            caption=f"*{good_info["full_name"]}* \n\n"+good_info["description"]+f"\n\nЦена: {int(round(good_info["price_rub"], -2))} RUB",
            reply_markup = kb.back_to_stock(),
            disable_notification=True,
            parse_mode="MARKDOWN"
        )
        db.set_user_attribute(user_tg_id=user_id, key = "msg_id_with_kb", value = msg.id) # sets last message with kb

    elif from_ == "good" and to_ == "stock":
        if not await try_msg_delete(chat_id=chat_id, message_id = message_id, context=context):
            await query.edit_message_reply_markup(reply_markup=None)
        
        msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=PATH_TO_MENU_PICTURE,
            reply_markup = kb.stock(goods_in_stock = db.get_goods_in_stock()),
            disable_notification=True
        )
        db.set_user_attribute(user_tg_id=user_id, key = "msg_id_with_kb", value = msg.id) # sets last message with kb

    else:
        if config.production != True: print(f"Unknown button: from_ {from_}, to {to_}")
        await start_handle(update, context)        




async def post_init(application: Application):
    await application.bot.set_my_commands([]) # hide default blue menu button to the left of the keyboard with commands list



async def error_handle(update: Update, context: CallbackContext) -> None:
    error = str(traceback.format_exc())
    if config.production != True: print(error)
    db.insert_error(error)
    await start_handle(update, context)






def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(max_retries=5))
        .http_version("1.1")
        .get_updates_http_version("1.1")
        .post_init(post_init)
        .build()
    )


    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handle))
    application.add_handler(CommandHandler("start", start_handle))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    application.add_error_handler(error_handle)


    application.run_polling()




PATH_TO_MENU_PICTURE = path.join("assets", "menu.png")
db = database.Database()

if __name__ == "__main__":
    run_bot()