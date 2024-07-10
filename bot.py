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
from io import BytesIO

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
            db.set_user_attribute(tg_id = user_id, key = what_to_delete, value = -1)



# /start special entry function
# THE WHOLE CODE IS BUILD WITH THE ASSUMPTION THAT THE USER WILL START FROM HERE
async def start_handle(update: Update, context: CallbackContext) -> None:
    async def register_user_if_not_exist(user, user_id: int, chat_id: int):
        db.add_new_user_if_not_exist(
            tg_id = user_id,
            chat_id = chat_id,
            username=user.username or "Unknown")
    
    if update is None or update.message is None:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    await register_user_if_not_exist(user = update.effective_user , user_id = user_id, chat_id=chat_id)
    
    await db_msg_delete("msg_id_with_kb", user_id, chat_id, context)
    
    msg = await context.bot.send_animation(
                                chat_id=chat_id,
                                animation=PATH_TO_MENU_MEDIA,
                                reply_markup= kb.start_menu(),
                                disable_notification=True,
                            )
    db.set_user_attribute(tg_id=user_id, key = "msg_id_with_kb", value = msg.id) # sets last message with kb




async def button_callback_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer() # prevents errors
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message_id = update.effective_message.id
    
    callback = json.loads(query.data)
    from_ = callback.get("from")
    to_ = callback.get("to")

    
    if from_ == -1:
        return
    
    elif from_ in ["menu", "vers"] and to_ == "stock":
        await query.edit_message_reply_markup(reply_markup=kb.stock_models(db.get_models_in_stock()))

    elif from_ == "stock" and to_ == "menu":
        await query.edit_message_reply_markup(reply_markup=kb.start_menu())

    elif model := callback.get("model"):
        await query.edit_message_reply_markup(reply_markup=kb.stock_versions(model, db.get_versions_in_stock(model)))
    
    elif good_full_name := callback.get("good"):
        if not await try_msg_delete(chat_id=chat_id, message_id = message_id, context=context):
            await query.edit_message_reply_markup(reply_markup=None)
        
        good_data = db.get_good_data(good_full_name, user_id)
        
        msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=BytesIO(bytearray(good_data["photo"])),
            caption=f"<b>{good_data["full_name"]}</b> \n\n"+good_data["description"]+f"\n\nЦена: *{int(round(good_data["price_rub"], -2)):,}* RUB",
            reply_markup = kb.good_card(good_data["model"]),
            disable_notification=True,
            parse_mode = "HTML"
        )
        db.set_user_attribute(tg_id=user_id, key = "msg_id_with_kb", value = msg.id) # sets last message with kb
    
    elif from_ == "good" and to_ == "vers":
        model = callback["modl"]
        if not await try_msg_delete(chat_id=chat_id, message_id = message_id, context=context):
            await query.edit_message_reply_markup(reply_markup=None)
        
        msg = await context.bot.send_animation(
                chat_id=chat_id,
                animation=PATH_TO_MENU_MEDIA,
                reply_markup = kb.stock_versions(model, db.get_versions_in_stock(model)),
                disable_notification=True
            )

        db.set_user_attribute(tg_id=user_id, key = "msg_id_with_kb", value = msg.id) # sets last message with kb

    else:
        if not config.production: print(f"Unknown button: from_ {from_}, to {to_}")







async def post_init(application: Application):
    await application.bot.set_my_commands([]) # hide default blue menu button to the left of the keyboard with commands list

async def error_handle(update: Update, context: CallbackContext) -> None:
    error = str(traceback.format_exc())
    if not config.production: print(error)
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




PATH_TO_MENU_MEDIA = path.join("assets", "logo_animation.gif")

db = database.Database()

if __name__ == "__main__":
    run_bot()