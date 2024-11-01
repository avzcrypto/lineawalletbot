import os
import requests
from web3 import Web3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    raise ValueError("No TOKEN found in environment variables")

# Web3 and contract setup
rpc_url = "https://rpc.linea.build"
lxp_contract_address = "0xd83af4fbD77f3AB65C3B1Dc4B38D7e67AEcf599A"
web3 = Web3(Web3.HTTPProvider(rpc_url))

# Conversation states
CHOOSE_ACTION, ENTER_WALLET = range(2)


# Functions to get data
def get_lxp_balance(wallet):
    contract = web3.eth.contract(address=Web3.to_checksum_address(lxp_contract_address), abi=[
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function",
        }
    ])
    balance = contract.functions.balanceOf(Web3.to_checksum_address(wallet)).call()
    return web3.from_wei(balance, 'ether')


def get_lxp_l_points(wallet):
    lxp_l_api_url = f"https://kx58j6x5me.execute-api.us-east-1.amazonaws.com/linea/getUserPointsSearch?user={wallet.lower()}"
    response = requests.get(lxp_l_api_url)
    if response.status_code == 200:
        data = response.json()
        return data[0].get('xp', 'No XP data') if isinstance(data, list) and len(data) > 0 else 'Unexpected data format'
    else:
        return f"Error: {response.status_code}"


def check_poh_status(wallet):
    poh_api_url = f"https://linea-xp-poh-api.linea.build/poh/{wallet}"
    response = requests.get(poh_api_url)
    if response.status_code == 200:
        return response.json().get("poh", False)
    else:
        return f"Error: {response.status_code}"


# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reset conversation state when /start is called
    context.user_data.clear()

    # Create buttons with emojis
    keyboard = [
        ["⭐ Check LXP", "📈 Check LXP-L"],
        ["✅ Check PoH", "🔍 Check All"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Welcome to the Linea Wallet Bot!\nCreated by @avzcrypto\n\nPlease choose an action using the buttons below:",
        reply_markup=reply_markup
    )

    return CHOOSE_ACTION


# Action choice handler
async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = update.message.text
    context.user_data["action"] = action  # Store the chosen action

    # Prompt for wallet address with a down arrow emoji
    await update.message.reply_text("⬇️ Please enter your wallet address:")

    return ENTER_WALLET


# Wallet address handler
async def enter_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = update.message.text.strip()
    action = context.user_data.get("action")

    if Web3.is_address(wallet_address):
        if action == "⭐ Check LXP":
            lxp_balance = get_lxp_balance(wallet_address)
            response = f"⭐ LXP Balance: {lxp_balance} LXP"

        elif action == "📈 Check LXP-L":
            lxp_l_points = get_lxp_l_points(wallet_address)
            response = f"📈 LXP-L Points: {lxp_l_points}"

        elif action == "✅ Check PoH":
            poh_status = check_poh_status(wallet_address)
            response = f"✅ POH Verified: {poh_status}"

        elif action == "🔍 Check All":
            lxp_balance = get_lxp_balance(wallet_address)
            lxp_l_points = get_lxp_l_points(wallet_address)
            poh_status = check_poh_status(wallet_address)
            response = (
                f"⭐ LXP Balance: {lxp_balance} LXP\n"
                f"📈 LXP-L Points: {lxp_l_points}\n"
                f"✅ POH Verified: {poh_status}"
            )
    else:
        response = "❌ Invalid wallet address. Please enter a valid address."

    # Send the response and ask for another action with keyboard buttons
    keyboard = [["⭐ Check LXP", "📈 Check LXP-L"], ["✅ Check PoH", "🔍 Check All"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(response)
    await update.message.reply_text("⬇️ Please choose another action:", reply_markup=reply_markup)

    return CHOOSE_ACTION


# Cancel command to stop the conversation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Goodbye!")
    return ConversationHandler.END


# Main function to run the bot
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_action)],
            ENTER_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_wallet)],
        },
        fallbacks=[CommandHandler("start", start), CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
