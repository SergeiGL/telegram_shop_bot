import asyncio
import json
import traceback
import multiprocessing
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


import database
import keyboards as kb
from tg import send_telegram_message
from config import (
    telegram_bot_token,
    is_in_production,
    order_description_text
)





async def try_msg_delete(del_msg_id, send_msg_id, chat_id, user_id, context, query):
    if del_msg_id != -1:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id = del_msg_id)
        except Exception as e:
            if not is_in_production: print(e)
            try:
                if query is not None: await query.edit_message_reply_markup(reply_markup=None)
            except: pass
    
    if send_msg_id is not None and user_id is not None:
        db.set_msg_with_kb(user_id=user_id, value=send_msg_id) # sets last message with kb



# /start special entry function
# THE WHOLE CODE IS BUILD WITH THE ASSUMPTION THAT THE USER WILL START FROM HERE
async def start_handle(update: Update, context: CallbackContext, create_user = True) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if create_user:
        db.add_new_user(user_id, chat_id=chat_id, username=update.effective_user.username or "Unknown")
    
    
    send_msg = await context.bot.send_animation(
                                chat_id=chat_id,
                                animation=MENU_ANIM_FILE_ID,
                                reply_markup= kb.start_menu(),
                                disable_notification=True,
                                parse_mode = "HTML")
    await try_msg_delete(db.get_msg_id_with_kb(user_id), send_msg.id, chat_id, user_id, context, update.callback_query)


async def button_callback_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer() # prevents errors
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    msg_id = update.effective_message.id
    
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
        good_data = db.get_good_data(model=model, version=version)
        if good_data == False:
            await start_handle(update, context)
            return
        
        message_text = f"<b>{good_data["specification_name"]}\n\n" + \
                        f"{int(round( good_data["price_usd"]*good_data["exch_rate"]*(1+good_data["margin_stock"]/100), -2 )):,} RUB</b>\n" \
                        + good_data["description"]
        
        send_msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=good_data["photo"],
            caption=message_text,
            reply_markup = kb.good_card(good_data["model"]),
            disable_notification=True,
            parse_mode = "HTML")
        await try_msg_delete(msg_id, send_msg.id, chat_id, user_id, context, query)
    
    elif from_ == "good" and to_ == "vers":
        model = callback["modl"]
        
        send_msg = await context.bot.send_animation(
                chat_id=chat_id,
                animation=MENU_ANIM_FILE_ID,
                reply_markup = kb.stock_versions(model, db.get_stock_versions(model)),
                disable_notification=True,
                parse_mode = "HTML")
        await try_msg_delete(msg_id, send_msg.id, chat_id, user_id, context, query)
    
    elif from_ == "menu" and to_ == "order":
        pricetable_img = db.get_pricetable_img()
        send_msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=pricetable_img,
            caption=order_description_text,
            reply_markup = kb.pricetable(),
            disable_notification=True,
            parse_mode = "HTML")
        await try_msg_delete(msg_id, send_msg.id, chat_id, user_id, context, query)
        
        if isinstance(pricetable_img, bytes):
            db.set_pricetable_img_file_id(send_msg.photo[-1].file_id)
    
    elif from_ == "pricetable" and to_ == "start":
        await start_handle(update, context, create_user = False)
    
    else:
        if not is_in_production: print(f"Unknown button: from_ {from_}, to {to_}")




async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([]) # hide default blue menu button to the left of the keyboard with commands list

async def message_handle(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    msg_id = update.effective_message.id

    # Сheck if message is edited (to avoid AttributeError: 'NoneType' object has no attribute 'from_user')
    if update.edited_message or update.message is None:
        return
    
    await try_msg_delete(msg_id, None, chat_id, None, context, query=None)


async def error_handle(update: Update, context: CallbackContext) -> None:
    error = "ERROR\nbot.py:\n" + str(traceback.format_exc())
    print(error)
    try:
        if is_in_production: send_telegram_message(error)
        db.insert_error(error)
    except: pass
    await start_handle(update, context)






# PATH_TO_MENU_ANIMATION = path.join("assets", "logo_animation.gif")

MENU_ANIM_FILE_ID = "CgACAgIAAxkDAAICkmaSvdRHrrGITg15ikjErQPaXzlNAAJ5WAACAdSZSLtS2JsfVHdhNQQ"
db = database.Database()


def run_exchange_rate_process():
    from exchange_rates_updater import update_exchange_rate, update_exchange_rate_scheduler
    
    update_exchange_rate()
    
    from time import sleep
    sleep(120)
    
    # Start the scheduled process
    update_exchange_rate_scheduler()



if __name__ == "__main__":
    # Create a new process
    update_exchange_rate_process = multiprocessing.Process(target=run_exchange_rate_process)
    
    # Start the process
    update_exchange_rate_process.start()
    
    application = (
        ApplicationBuilder()
        .token(telegram_bot_token)
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