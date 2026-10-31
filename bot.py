import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler, PreCheckoutQueryHandler)
import database

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

QTY, UPI, CONFIRM, SUPPORT_MSG = range(4)
database.init_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    database.add_user(user.id, user.username, user.first_name)
    keyboard = [[InlineKeyboardButton("⭐ Sell Star", callback_data="sell_star")], [InlineKeyboardButton("💬 Support", callback_data="support")]]
    await update.message.reply_text(f"नमस्ते {user.first_name}! STAR ⭐ बॉट में आपका स्वागत है।\n\nकृपया नीचे दिए गए विकल्पों में से चुनें:", reply_markup=InlineKeyboardMarkup(keyboard))

async def sell_star(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("आप कितने Stars भेजना चाहते हैं?\n\n⚠️ नियम: कम से कम 50 Stars होने चाहिए।\n💡 दर: 1 Star = 1 INR (Gift INR ✅)\n\nकृपया सिर्फ संख्या (number) टाइप करें:")
    return QTY

async def receive_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit() or int(text) < 50:
        await update.message.reply_text("❌ गलत संख्या! कृपया 50 या उससे ज़्यादा का कोई नंबर डालें:")
        return QTY
    context.user_data['stars_qty'] = int(text)
    await update.message.reply_text("✅ अब कृपया अपनी UPI ID डालें (जैसे: example@upi):")
    return UPI

async def receive_upi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upi = update.message.text.strip()
    if "@" not in upi or " " in upi:
        await update.message.reply_text("❌ गलत UPI ID! कृपया सही UPI ID डालें (जैसे: name@bank):")
        return UPI
    context.user_data['upi_id'] = upi
    qty = context.user_data['stars_qty']
    keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data="confirm_pay")], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_pay")]]
    await update.message.reply_text(f"कृपया अपनी जानकारी जांचें:\n\n⭐ Stars Quantity: {qty}\n💳 UPI ID: {upi}\n\nसही है तो Confirm दबाएं।", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM

async def confirm_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    qty = context.user_data['stars_qty']
    upi = context.user_data['upi_id']
    user_id = query.from_user.id
    req_id = database.create_request(user_id, qty, upi)
    context.user_data['req_id'] = req_id
    await context.bot.send_invoice(
        chat_id=user_id, title="Gift INR ✅ (Education Purpose)", description=f"{qty} Stars ke liye Gift INR",
        payload=f"req_{req_id}", provider_token="", currency="XTR", prices=[LabeledPrice(label="Stars", amount=qty)], start_parameter="star-payment"
    )
    await query.edit_message_text("इनवॉइस भेज दिया गया है। कृपया पेमेंट पूरा करें।")
    return ConversationHandler.END

async def cancel_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ आपने कैंसिल कर दिया है।")
    return ConversationHandler.END

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    charge_id = payment.telegram_payment_charge_id
    payload = payment.invoice_payload
    user_id = update.effective_user.id
    req_id = int(payload.split("_")[1])
    success = database.mark_request_paid(req_id, charge_id)
    if success:
        await update.message.reply_text("✅ आपका भुगतान सफल हो गया है! एडमिन जल्द ही आपको लिंक भेजेंगे।")
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🚨 नया पेमेंट सफल!\n\nUser ID: {user_id}\nRequest ID: {req_id}\nCharge ID: {charge_id}\n\nकमांड: /admin")
    else:
        await update.message.reply_text("⚠️ यह पेमेंट पहले ही प्रोसेस हो चुका है।")

async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("कृपया अपनी समस्या या सवाल टाइप करें (Admin को भेजा जाएगा):")
    return SUPPORT_MSG

async def receive_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user = update.effective_user
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"💬 नया सपोर्ट मैसेज\nUser: {user.first_name} (@{user.username})\nID: {user.id}\n\nमैसेज: {msg}\n\nजवाब: /reply {user.id} आपका_जवाब")
    await update.message.reply_text("✅ आपका मैसेज एडमिन को भेज दिया गया है।")
    return ConversationHandler.END

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ आप एडमिन नहीं हैं।")
        return
    users, total_reqs, pending, paid = database.get_stats()
    await update.message.reply_text(f"👑 एडमिन पैनल\n\n👥 कुल यूज़र: {users}\n📋 कुल रिक्वेस्ट: {total_reqs}\n⏳ पेंडिंग: {pending}\n✅ सफल पेमेंट: {paid}\n\nनिर्देश:\n1. यूज़र को DM में लिंक भेजें।\n2. उनका स्क्रीनशॉट यहाँ भेजें।\n3. कमांड: /reply ID मैसेज")

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        target_id = int(context.args[0])
        reply_text = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=target_id, text=f"📩 एडमिन का जवाब:\n\n{reply_text}")
        await update.message.reply_text("✅ जवाब भेज दिया गया।")
    except:
        await update.message.reply_text("❌ गलत फॉर्मेट! सही तरीका: /reply ID मैसेज")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    sell_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(sell_star, pattern="^sell_star$")],
        states={QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_qty)], UPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_upi)], CONFIRM: [CallbackQueryHandler(confirm_pay, pattern="^confirm_pay$"), CallbackQueryHandler(cancel_pay, pattern="^cancel_pay$")]},
        fallbacks=[]
    )
    support_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(support_start, pattern="^support$")],
        states={SUPPORT_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support)]},
        fallbacks=[]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("reply", admin_reply))
    app.add_handler(sell_conv)
    app.add_handler(support_conv)
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    print("बॉट चालू हो गया है... रुकने के लिए CTRL+C दबाएं")
    app.run_polling()

if __name__ == "__main__":
    main()
0

