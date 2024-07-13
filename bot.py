import asyncio
import json
from os import path
import traceback

from telegram import (
    Update
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    AIORateLimiter,
    filters
)


from base64 import b64decode
from io import BytesIO

import database
import keyboards as kb
import config
from tg import send_telegram_message




async def try_msg_delete(chat_id, context, message_id=None, db_attrib = None, user_id = None):
    try:
        if db_attrib and user_id and message_id is None:
            message_id = db.get_user_data(db_attrib, user_id)
            if message_id == -1:
                return False
            await context.bot.delete_message(chat_id=chat_id, message_id = message_id)
        
        elif message_id is not None:
            await context.bot.delete_message(chat_id=chat_id, message_id = message_id)
        else:
            print(f"ERROR\n:WRONG try_msg_delete params:\n{chat_id=}, {context=}, {message_id=}, {db_attrib =}, {user_id =}")
        
        return True
    except:
        return False



# /start special entry function
# THE WHOLE CODE IS BUILD WITH THE ASSUMPTION THAT THE USER WILL START FROM HERE
async def start_handle(update: Update, context: CallbackContext) -> None:
    async def register_user_if_not_exist(user, user_id: int, chat_id: int):
        db.add_new_user_if_not_exist(
            user_id = user_id,
            chat_id = chat_id,
            username=user.username or "Unknown")
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    await register_user_if_not_exist(user = update.effective_user , user_id = user_id, chat_id=chat_id)
    
    await try_msg_delete(db_attrib="msg_id_with_kb", user_id=user_id, chat_id=chat_id, context=context)
    
    msg = await context.bot.send_animation(
                                chat_id=chat_id,
                                animation=MENU_ANIMATION,
                                reply_markup= kb.start_menu(),
                                disable_notification=True,
                                parse_mode = "HTML")
    db.set_user_attribute(user_id=user_id, key="msg_id_with_kb", value=msg.id) # sets last message with kb


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
        await query.edit_message_reply_markup(reply_markup=kb.stock_models(db.get_stock_models()))

    elif from_ == "stock" and to_ == "menu":
        await query.edit_message_reply_markup(reply_markup=kb.start_menu())

    elif model := callback.get("model"):
        await query.edit_message_reply_markup(reply_markup=kb.stock_versions(model, db.get_stock_versions(model)))
    
    elif (model := callback.get("gd_mdl")) and (version := callback.get("gd_vsn")):
        if not await try_msg_delete(chat_id=chat_id, message_id=message_id, context=context):
            await query.edit_message_reply_markup(reply_markup=None)
        
        good_data = db.get_good_data(model=model, version=version)
        if good_data == False:
            await start_handle(update, context)
            return
        
        message_text = f"<b>{good_data["model"]+ " "+ good_data["version"]}\n\n" + \
                        f"Цена: {int(round( good_data["price_usd"]*good_data["exch_rate"]*(1+good_data["margin_order"]/100), -2 )):,} RUB</b>\n\n" + \
                        good_data["description"]
        
        msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=BytesIO(b64decode(good_data["photo"])),
            caption=message_text,
            reply_markup = kb.good_card(good_data["model"]),
            disable_notification=True,
            parse_mode = "HTML")
        db.set_user_attribute(user_id=user_id, key="msg_id_with_kb", value=msg.id) # sets last message with kb
    
    elif from_ == "good" and to_ == "vers":
        model = callback["modl"]
        if not await try_msg_delete(chat_id=chat_id, message_id=message_id, context=context):
            await query.edit_message_reply_markup(reply_markup=None)
        
        msg = await context.bot.send_animation(
                chat_id=chat_id,
                animation=MENU_ANIMATION,
                reply_markup = kb.stock_versions(model, db.get_stock_versions(model)),
                disable_notification=True,
                parse_mode = "HTML")
        db.set_user_attribute(user_id=user_id, key="msg_id_with_kb", value=msg.id) # sets last message with kb
    else:
        if not config.production: print(f"Unknown button: from_ {from_}, to {to_}")




async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([]) # hide default blue menu button to the left of the keyboard with commands list

async def message_handle(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    message_id = update.effective_message.id

    # Сheck if message is edited (to avoid AttributeError: 'NoneType' object has no attribute 'from_user')
    if update.edited_message or update.message is None:
        return
    
    await try_msg_delete(chat_id, message_id, context)

async def error_handle(update: Update, context: CallbackContext) -> None:
    error = "ERROR\nbot.py:\n" + str(traceback.format_exc())
    print(error)
    try:
        if config.production: send_telegram_message(error)
        db.insert_error(error)
    except: pass
    await start_handle(update, context)






# PATH_TO_MENU_ANIMATION = path.join("assets", "logo_animation.gif")

MENU_ANIMATION = "CgACAgIAAxkDAAICkmaSvdRHrrGITg15ikjErQPaXzlNAAJ5WAACAdSZSLtS2JsfVHdhNQQ"
db = database.Database()

if __name__ == "__main__":
    application = (
        ApplicationBuilder()
        .token(config.telegram_bot_token)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(max_retries=5))
        .http_version("1.1")
        .get_updates_http_version("1.1")
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start_handle))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    application.add_handler(MessageHandler(filters.ALL, message_handle))
    application.add_error_handler(error_handle)


    application.run_polling()