from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json

ADMIN_IDS = ["5129729732", "1297908055"]  # Replace with your admin IDs
USERS_FILE = 'users.json'
VALID_CODES = {"TANGBANMOI123": 1000}
REFERRAL_COMMISSION = 0.02

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def format_currency(amount):
    return "{:,.0f}".format(amount).replace(",", ".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [KeyboardButton("📝 Đăng ký"), KeyboardButton("💰 Số dư")],
        [KeyboardButton("💵 Nạp tiền"), KeyboardButton("💸 Rút MoMo")],
        [KeyboardButton("➕ Cộng số dư") if str(update.message.from_user.id) in ADMIN_IDS else KeyboardButton(""),
         KeyboardButton("👥 Người dùng") if str(update.message.from_user.id) in ADMIN_IDS else KeyboardButton("")],
        [KeyboardButton("🎁 Nhập mã"), KeyboardButton("🤝 Mời bạn")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('🙌 Chào mừng bạn đã đến với thiên đường giải trí \n\n🎗 Tham gia nhóm: t.me/hoanghai211 để khám phá ngay nhé! ', reply_markup=reply_markup)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    users = load_users()
    if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'username': update.message.from_user.username,
            'referred_by': None,
            'referrals': [],
            'commission': 0
        }
        save_users(users)
        await update.message.reply_text('Đăng ký thành công!')
        
        if context.args and context.args[0].startswith("ref_"):
            referrer_id = context.args[0].split("ref_")[1]
            if referrer_id in users:
                users[user_id]['referred_by'] = referrer_id
                users[referrer_id]['referrals'].append(user_id)
                save_users(users)
                await context.bot.send_message(referrer_id, f"Bạn đã mời thành công người dùng {user_id[:-2]}**")
    else:
        await update.message.reply_text('Bạn đã đăng ký trước đó.')

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    users = load_users()
    if user_id in users:
        balance = users[user_id]['balance']
        await update.message.reply_text(f'Số dư của bạn là: {format_currency(balance)}')
    else:
        await update.message.reply_text('Bạn chưa đăng ký.')

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.from_user.id) not in ADMIN_IDS:
        await update.message.reply_text('Bạn không có quyền sử dụng lệnh này.')
        return
    
    args = context.args
    if len(args) != 2:
        await update.message.reply_text('Cú pháp sai. Dùng: /add_balance <user_id> <amount>')
        return
    
    user_id, amount = args
    users = load_users()
    if user_id in users:
        users[user_id]['balance'] += int(amount)
        save_users(users)
        await update.message.reply_text('Cộng tiền thành công!')
        await update.message.reply_text(f'💹 Biến động số dư: + {format_currency(int(amount))} VND\n🛅 Số dư hiện tại: {format_currency(users[user_id]["balance"])}')
        
        referrer_id = users[user_id].get('referred_by')
        if referrer_id:
            commission = int(amount) * REFERRAL_COMMISSION
            users[referrer_id]['commission'] += commission
            save_users(users)
            await context.bot.send_message(referrer_id, f"Bạn nhận được {format_currency(commission)} VND hoa hồng từ giao dịch nạp tiền của {user_id[:-2]}**.")
    else:
        await update.message.reply_text('Người dùng không tồn tại.')

async def naptien(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    message = (
        f"Tên: NGUYEN HOANG HAI\n"
        f"Ngân hàng: MB BANK\n"
        f"STK: 9999999999999\n"
        f"Nội dung: {user_id}"
    )
    
    keyboard = [
        [InlineKeyboardButton("Xác nhận đã nạp", callback_data='confirm_nap')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(message, reply_markup=reply_markup)

async def confirm_nap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="💌 Cảm ơn bạn đã nạp, số tiền sẽ được admin cộng sau 5 - 15 phút.")

async def rutmomo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    args = context.args
    
    if len(args) != 2:
        await update.message.reply_text('💸 Vui lòng thực hiện theo hướng dẫn sau:\n/rutmomo [dấu cách] SĐT [dấu cách] Số tiền muốn rút\n\n➡️ VD: /rutmomo 0337529128 500,000\n\n⚠️ Số tiền rút tối thiểu là 30.000')
        return
    
    sdt, amount_str = args
    if not amount_str.replace(",", "").isdigit():
        await update.message.reply_text('❌ Số tiền không hợp lệ.')
        return
    
    amount = int(amount_str.replace(",", ""))
    if amount < 30000:
        await update.message.reply_text('❌ Số tiền rút tối thiểu là 30.000 VND.')
        return
    
    users = load_users()
    if user_id in users:
        if users[user_id]['balance'] >= amount:
            users[user_id]['balance'] -= amount
            save_users(users)
            username = users[user_id].get('username', 'Unknown')
            admin_message = (
                f"🔔 Người dùng {user_id} ({username}) đã yêu cầu rút tiền:\n"
                f"📌 SĐT: {sdt}\n"
                f"📌 Số tiền: {format_currency(amount)} VND"
            )
            for admin_id in ADMIN_IDS:
                await context.bot.send_message(admin_id, admin_message)
            
            await update.message.reply_text('Yêu cầu rút tiền đã được gửi đến admin.')
        else:
            await update.message.reply_text('Số dư không đủ để rút.')
    else:
        await update.message.reply_text('🎉 Xin lỗi ! Nhưng bạn chưa đăng ký.')

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.from_user.id) not in ADMIN_IDS:
        await update.message.reply_text('Bạn không có quyền sử dụng lệnh này.')
        return
    
    users = load_users()
    message = ""
    for user_id, data in users.items():
        message += f"🆔 ID: {user_id}\n📌 Username: {data.get('username', 'Unknown')}\n📌 Số dư: {format_currency(data['balance'])}\n"
    await update.message.reply_text(message if message else "Không có người dùng nào đăng ký.")

async def gifcode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    users = load_users()
    if user_id not in users:
        await update.message.reply_text('Bạn chưa đăng ký.')
        return
    
    args = context.args
    if len(args) != 1:
        await update.message.reply_text('Cú pháp sai. Dùng: /gifcode <code>')
        return
    
    code = args[0]
    if code in VALID_CODES:
        amount = VALID_CODES[code]
        users[user_id]['balance'] += amount
        save_users(users)
        await update.message.reply_text(f'🎉 Nhập mã thành công! Bạn được cộng {format_currency(amount)} VND.')
    else:
        await update.message.reply_text('🎁 Nhận ngẫu nhiên 1k - 50k khi nhập code \n\nCode : /gifcode GITFREE:1KMIENPHI')

async def ref(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    users = load_users()
    if user_id in users:
        referrals = users[user_id].get('referrals', [])
        commission = users[user_id].get('commission', 0)
        if referrals:
            message = f"Bạn đã mời {len(referrals)} người dùng:\n"
            for ref_id in referrals:
                message += f" - {ref_id[:-2]}**\n"
            message += f"Tổng hoa hồng nhận được: {format_currency(commission)} VND"
        else:
            message = "Xin lỗi ! Nhưng mà bạn chưa mời được ai mà."
        await update.message.reply_text(message)
    else:
        await update.message.reply_text('Bạn chưa đăng ký.')

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    invite_link = f"https://t.me/bot_checkinfo_bot?start=ref_{user_id}"
    await update.message.reply_text(f"🌟 Mời bạn bè của bạn tham gia và nhận hoa hồng từ mỗi lần họ nạp tiền!\n\nĐây là liên kết mời : {invite_link}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if text == "📝 Đăng ký":
        await register(update, context)
    elif text == "💰 Số dư":
        await balance(update, context)
    elif text == "💵 Nạp tiền":
        await naptien(update, context)
    elif text == "💸 Rút MoMo":
        await rutmomo(update, context)
    elif text == "➕ Cộng số dư":
        await add_balance(update, context)
    elif text == "👥 Người dùng":
        await users(update, context)
    elif text.startswith("🎁 Nhập mã"):
        args = text.split(" ")
        if len(args) > 2:
            code = args[-1]
            context.args = [code]
            await gifcode(update, context)
    elif text == "🤝 Mời bạn":
        await invite(update, context)

def main() -> None:
    application = ApplicationBuilder().token("6833270832:AAHLVkZ1BTxbqqfFYNQxcxO0pmjN50cc1Ro").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("add_balance", add_balance))
    application.add_handler(CommandHandler("naptien", naptien))
    application.add_handler(CallbackQueryHandler(confirm_nap, pattern='confirm_nap'))
    application.add_handler(CommandHandler("rutmomo", rutmomo))
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("gifcode", gifcode))
    application.add_handler(CommandHandler("ref", ref))
    application.add_handler(CommandHandler("invite", invite))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
