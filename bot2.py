import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import json
import random
import asyncio


USERS_FILE = 'users.json'
HISTORY_FILE = 'history.json'
CURRENT_BETS = {}
PHASE_DURATION = 45  # Duration of each phase in seconds

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def load_history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)
            if "recent_results" not in history:
                history["recent_results"] = []
            return history
    except FileNotFoundError:
        return {"recent_results": []}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)

def format_currency(amount):
    return "{:,.0f}".format(amount).replace(",", ".")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Chào mừng bạn đến với trò chơi tài xỉu!')

async def handle_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    users = load_users()
    
    if user_id not in users:
        await update.message.reply_text('Bạn chưa đăng ký.')
        return
    
    text = update.message.text.upper().split()
    if len(text) != 2 or text[0] not in ['X', 'T', 'C', 'L'] or not text[1].isdigit():
        return  # Không báo lỗi cú pháp nếu tin nhắn không phải lệnh cược hợp lệ

    bet_type, bet_amount = text[0], int(text[1])
    if users[user_id]['balance'] < bet_amount:
        await update.message.reply_text('Số dư không đủ.')
        return

    if bet_type not in CURRENT_BETS:
        CURRENT_BETS[bet_type] = {}
    
    CURRENT_BETS[bet_type][user_id] = bet_amount
    await update.message.reply_text(f'✅ Bạn đã cược {format_currency(bet_amount)} vào {bet_type}.')

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.lower()
    if text in ["sd", "sodu"]:
        await check_balance(update, context)
    else:
        await update.message.reply_text('❌ Cú pháp sai. Dùng: T <số tiền cược>, X <số tiền cược>, C <số tiền cược> hoặc L <số tiền cược>')

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    users = load_users()
    
    if user_id not in users:
        await update.message.reply_text('Bạn chưa đăng ký.')
    else:
        balance = users[user_id]['balance']
        await update.message.reply_text(f'Số dư của bạn là: {format_currency(balance)}')

async def lucky(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('hong bé ơi')

async def game_loop(context: ContextTypes.DEFAULT_TYPE):
    phase = 1

    while True:
        CURRENT_BETS.clear()  # Reset bets for the new phase
        keyboard = [[InlineKeyboardButton("Nạp tiền", url="https://t.me/bot_checkinfo_bot")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            context.job.chat_id, 
            f'*#Phiên {phase} bắt đầu! Thời gian đặt cược là 45 giây.* \n\n Cách chơi: [[Cửa cược]]  [[Số tiền]]\n\n- VD: T 50000 hoặc X 30000\n\n- VD: C 50000 hoặc L 30000\n\n- Tiền cược tối thiểu là 1.000', 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Gửi ảnh sau thông báo bắt đầu phiên
        await context.bot.send_photo(context.job.chat_id, photo='https://i.imgur.com/eFqLsvJ.jpeg')

        await asyncio.sleep(5)
        await notify(context, phase, 40)
        
        await asyncio.sleep(20)
        await notify(context, phase, 20)
        
        await asyncio.sleep(15)
        await context.bot.send_message(context.job.chat_id, f'🤖 Tung Xúc Xắc phiên #{phase} 🤖')
        await asyncio.sleep(5)

        # Roll the dice and then wait 5 seconds before showing the result
        await finalize_phase(context, phase)
        await asyncio.sleep(5)

        phase += 1

        # Wait 5 seconds before starting the next phase
        await asyncio.sleep(5)

async def notify(context: ContextTypes.DEFAULT_TYPE, phase, remaining_time):
    tai_total = sum(CURRENT_BETS.get('T', {}).values())
    xiu_total = sum(CURRENT_BETS.get('X', {}).values())
    chan_total = sum(CURRENT_BETS.get('C', {}).values())
    le_total = sum(CURRENT_BETS.get('L', {}).values())
    
    keyboard = [[InlineKeyboardButton("Nạp tiền", url="https://t.me/bot_checkinfo_bot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        context.job.chat_id,
        f"⏰ *Còn {remaining_time} giây cho phiên #{phase}*\n"
        f"🔵 *TÀI*: {format_currency(tai_total)}\n"
        f"🔴 *XỈU*: {format_currency(xiu_total)}\n\n"
        f"⚪️ *CHẴN*: {format_currency(chan_total)}\n"
        f"⚫️ *LẺ*: {format_currency(le_total)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def finalize_phase(context: ContextTypes.DEFAULT_TYPE, phase):
    users = load_users()
    history = load_history()

    dice_results = []
    for _ in range(3):
        message = await context.bot.send_dice(context.job.chat_id)
        dice_results.append(message.dice.value)
    
    dice_sum = sum(dice_results)
    result = 'X' if 3 <= dice_sum <= 10 else 'T'
    chan_le = 'C' if dice_sum % 2 == 0 else 'L'

    total_win = 0
    total_lose = 0

    for bet_type, user_bets in CURRENT_BETS.items():
        for user_id, bet_amount in user_bets.items():
            if result == bet_type or chan_le == bet_type:
                win_amount = int(bet_amount * 1.95)
                users[user_id]['balance'] += win_amount
                total_win += win_amount
            else:
                users[user_id]['balance'] -= bet_amount
                total_lose += bet_amount

    save_users(users)
    
    history["recent_results"].append((result, chan_le))
    if len(history["recent_results"]) > 12:
        history["recent_results"] = history["recent_results"][-12:]
    
    save_history(history)

    recent_results_str_tai_xiu = "".join(['🔴' if res[0] == 'X' else '🔵' for res in history["recent_results"] if len(res) > 1])
    recent_results_str_chan_le = "".join(['⚪️' if res[1] == 'C' else '⚫️' for res in history["recent_results"] if len(res) > 1])
    
    result_message = (
        f"*Kết quả phiên #{phase}*\n"
        f"┏━━━━━━━━━━━━┓\n"
        f"┃ {' '.join(map(str, dice_results))} ({dice_sum}) {'TÀI' if result == 'T' else 'XỈU'} {'CHẴN' if chan_le == 'C' else 'LẺ'} {'🔵' if result == 'T' else '🔴'}{'⚪️' if chan_le == 'C' else '⚫️'}\n"
        f"┃ *Tổng thắng*: {format_currency(total_win)}\n"
        f"┃ *Tổng thua*: {format_currency(total_lose)}\n"
        f"┗━━━━━━━━━━━━┛\n"
        f"*Kết quả 12 cầu gần nhất:*\n\n"
        f"{recent_results_str_tai_xiu}\n\n"
        f"{recent_results_str_chan_le}\n\n"
        f"🔵 Tài  | 🔴 XỈU"
        f"⚪️ Chẵn | ⚫️ Lẻ"
    )
    await context.bot.send_message(context.job.chat_id, result_message, parse_mode=ParseMode.MARKDOWN)

def main() -> None:
    application = ApplicationBuilder().token("7050851037:AAFOT2fxogbG383ubAIMcsA5Jfjuhk8jZVk").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lucky", lucky))
    application.add_handler(MessageHandler(filters.Regex(r'^(sd|sodu)$'), check_balance))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bet))
    application.add_handler(MessageHandler(filters.COMMAND, handle_command))

    application.job_queue.run_repeating(game_loop, interval=PHASE_DURATION + 5, first=1, chat_id="-1002193531047")

    application.run_polling()

if __name__ == '__main__':
    main()
