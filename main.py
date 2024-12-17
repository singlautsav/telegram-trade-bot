import logging
import asyncio
import platform
import yaml
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes
from datetime import datetime
import hashlib
import requests
from urllib.parse import urlparse, parse_qs
import pyotp
from api_helper import NorenApiPy

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

basedir = '/home/ubuntu'

with open(f'{basedir}/cred.yml') as f:
    creds = yaml.load(f, Loader=yaml.FullLoader)

TELEGRAM_TOKEN = creds['telegramToken']
chatID = creds['chatID']
ALLOWED_CHAT_IDS = [int(creds['chatID'])]

userid = creds['user']
password = creds['pwd']
totp_key = creds['totp_key']
API_KEY = creds['apikey']
API_SECRET = creds['apisecret']
USER_TOKEN = creds['user_token']
# Initialize Flattrade API
api = None


def reauth():
    global api
    headerJson ={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36","Referer":"https://auth.flattrade.in/"}
    sesUrl = 'https://authapi.flattrade.in/auth/session'
    passwordEncrpted =  hashlib.sha256(password.encode()).hexdigest()
    ses = requests.Session()
    res_pin = ses.post(sesUrl,headers=headerJson)
    sid = res_pin.text
    url2 = 'https://authapi.flattrade.in/ftauth'
    payload = {"UserName":userid,"Password":passwordEncrpted,"PAN_DOB":pyotp.TOTP(totp_key).now(),"App":"","ClientID":"","Key":"","APIKey":API_KEY,"Sid":sid}
    res2 = ses.post(url2, json=payload)
    reqcodeRes = res2.json()
    parsed = urlparse(reqcodeRes['RedirectURL'])
    reqCode = parse_qs(parsed.query)['code'][0]
    api_secret =API_KEY+ reqCode + API_SECRET
    api_secret =  hashlib.sha256(api_secret.encode()).hexdigest()
    payload = {"api_key":API_KEY, "request_code":reqCode, "api_secret":api_secret}
    url3 = 'https://authapi.flattrade.in/trade/apitoken'
    res3 = ses.post(url3, json=payload)
    USER_TOKEN = res3.json()['token']
    ret = api.set_session(userid= userid, password = password, usertoken= USER_TOKEN)
    creds['user_token'] = USER_TOKEN
    # updateMongo('creds', cred)
    return api, USER_TOKEN

async def initialize_flattrade():
    """Initialize Flattrade API session"""
    global api
    api = NorenApiPy()
    if USER_TOKEN == '':
        try:
            api, USER_TOKEN = reauth()
            # print(USER_TOKEN)
        except Exception as e:
            logger.error(e)
            message = f'''🔴 🔴 |  FT Login Error | Failed Login'''
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={chatID}&text={message}"
            requests.get(url).json()
    else:
        ret = api.set_session(userid= userid, password = password, usertoken= USER_TOKEN)
    # print(ret)
    return api

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        await update.message.reply_text("Unauthorized access.")
        return
    
    keyboard = [
        [InlineKeyboardButton("Active Positions 📊", callback_data='positions')],
        [InlineKeyboardButton("New Trade 📈", callback_data='new_trade')],
        [InlineKeyboardButton("Live P&L 💰", callback_data='pnl')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to Trading Terminal! Choose an action:",
        reply_markup=reply_markup
    )

async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the start callback - show main menu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Active Positions 📊", callback_data='positions')],
        [InlineKeyboardButton("New Trade 📈", callback_data='new_trade')],
        [InlineKeyboardButton("Live P&L 💰", callback_data='pnl')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Welcome to Trading Terminal! Choose an action:",
        reply_markup=reply_markup
    )

async def positions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Get positions from Flattrade
    try:
        positions = await get_positions()
        if not positions:
            await query.edit_message_text("No active positions.")
            return
        
        message = "🔵 Active Positions:\n\n"
        for pos in positions:
            # Position header with symbol and type
            message += f"📊 {pos['symbol']} ({pos['product']} - {pos['exchange']})\n"
            
            # Position size and direction
            direction = "LONG 📈" if pos['quantity'] > 0 else "SHORT 📉"
            message += f"Direction: {direction}\n"
            message += f"Quantity: {abs(pos['quantity'])}\n\n"
            
            # Price information
            message += f"Entry Price: ₹{pos['avg_price']:.2f}\n"
            message += f"Current Price: ₹{pos['ltp']:.2f}\n"
            message += f"Market Value: ₹{pos['market_value']:,.2f}\n"
            message += f"Invested Value: ₹{pos['invested_value']:,.2f}\n\n"
            
            # P&L information
            pnl_emoji = "🟢" if pos['total_pnl'] >= 0 else "🔴"
            message += f"P&L Details {pnl_emoji}:\n"
            message += f"Realized: ₹{pos['realized_pnl']:,.2f}\n"
            message += f"Unrealized: ₹{pos['unrealized_pnl']:,.2f}\n"
            message += f"Total P&L: ₹{pos['total_pnl']:,.2f} ({pos['pnl_percentage']}%)\n\n"
            
            # Trade details
            message += f"Trade Details:\n"
            message += f"Buy Qty: {pos['buy_qty']} @ ₹{pos['buy_value']:.2f}\n"
            message += f"Sell Qty: {pos['sell_qty']} @ ₹{pos['sell_value']:.2f}\n"
            message += f"Last Update: {pos['last_update']}\n"
            message += "─" * 30 + "\n\n"
            
        keyboard = [
            [InlineKeyboardButton("Refresh 🔄", callback_data='positions')],
            [InlineKeyboardButton("Back to Menu 🔙", callback_data='start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    except Exception as e:
        await query.edit_message_text(f"Error fetching positions: {str(e)}")

async def pnl_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        pnl = await get_pnl()
        message = f"Current P&L Summary:\n\n"
        message += f"Day P&L: {pnl['day_pnl']}\n"
        message += f"Net P&L: {pnl['net_pnl']}\n"
        message += f"Total Positions: {pnl['positions_count']}\n"
        message += f"Active Positions: {pnl['active_positions']}\n"
        message += f"Last Updated: {datetime.now().strftime('%H:%M:%S')}"
        
        keyboard = [[InlineKeyboardButton("Back to Menu 🔙", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    except Exception as e:
        await query.edit_message_text(f"Error fetching P&L: {str(e)}")

async def new_trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("Buy", callback_data='buy'),
            InlineKeyboardButton("Sell", callback_data='sell')
        ],
        [InlineKeyboardButton("Back to Menu 🔙", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Select trade type:",
        reply_markup=reply_markup
    )

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Ask for symbol and quantity
    keyboard = [[InlineKeyboardButton("Back to Menu 🔙", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "To place a BUY order, send a message in this format:\n"
        "Symbol Quantity [Price] [TriggerPrice]\n\n"
        "Examples:\n"
        "RELIANCE-EQ 10 --> (Market order)\n"
        "TATASTEEL-EQ 5 850.50 --> (Limit order)\n"
        "INFY-EQ 15 1200 1190 --> (Stop Loss order)",
        reply_markup=reply_markup
    )

async def sell_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Ask for symbol and quantity
    keyboard = [[InlineKeyboardButton("Back to Menu 🔙", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "To place a SELL order, send a message in this format:\n"
        "Symbol Quantity [Price] [TriggerPrice]\n\n"
        "Examples:\n"
        "RELIANCE-EQ 10 --> (Market order)\n"
        "TATASTEEL-EQ 5 850.50 --> (Limit order)\n"
        "INFY-EQ 15 1200 1190 --> (Stop Loss order)",
        reply_markup=reply_markup
    )

async def handle_order_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order messages with symbol and quantity"""
    try:
        # Parse the message
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text(
                "Invalid format. Please use:\n"
                "Symbol Quantity [Price] [TriggerPrice]"
            )
            return
            
        symbol = parts[0].upper()
        qty = int(parts[1])
        
        # Determine order type based on number of parameters
        if len(parts) == 2:  # Market order
            price_type = 'MKT'
            price = 0
            trigger_price = 0
        elif len(parts) == 3:  # Limit order
            price_type = 'LMT'
            price = float(parts[2])
            trigger_price = 0
        elif len(parts) == 4:  # Stop Loss order
            price_type = 'SL'
            price = float(parts[2])
            trigger_price = float(parts[3])
        else:
            await update.message.reply_text("Too many parameters provided")
            return
            
        # Place the order
        order_result = await place_order(
            symbol=symbol,
            qty=qty,
            side='B',  # Will be updated in context
            price_type=price_type,
            price=price,
            trigger_price=trigger_price
        )
        
        await update.message.reply_text(f"Order placed successfully!\n{order_result['message']}")
        
    except ValueError as e:
        await update.message.reply_text(f"Invalid number format: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"Error placing order: {str(e)}")

# Flattrade API functions
async def get_positions():
    """Fetch current active positions from Flattrade API"""
    try:
        # Initialize API if not already done
        if not api:
            await initialize_flattrade()
            
        # Get positions using NorenApi
        positions = api.get_positions()
        print("Raw positions:", positions)
        
        if not positions:
            return []
            
        formatted_positions = []
        for pos in positions:
            # Only include positions with non-zero quantity
            netqty = int(pos.get('netqty', 0))
            if netqty != 0:  # This means position is active
                # Calculate current market value and P&L percentage
                avg_price = float(pos.get('avgprc', 0))
                ltp = float(pos.get('lp', 0))  # Last traded price
                market_value = netqty * ltp
                invested_value = abs(netqty * avg_price)
                pnl_percentage = ((market_value - invested_value) / invested_value * 100) if invested_value != 0 else 0
                
                formatted_pos = {
                    'symbol': pos.get('tsym', ''),  # Trading symbol
                    'quantity': netqty,  # Net quantity
                    'avg_price': avg_price,  # Average price
                    'ltp': ltp,  # Last traded price
                    'buy_qty': int(pos.get('buyqty', 0)),  # Total buy quantity
                    'sell_qty': int(pos.get('sellqty', 0)),  # Total sell quantity
                    'buy_value': float(pos.get('buyavgprc', 0)),  # Buy average price
                    'sell_value': float(pos.get('sellavgprc', 0)),  # Sell average price
                    'realized_pnl': float(pos.get('rpnl', 0)),  # Realized P&L
                    'unrealized_pnl': float(pos.get('urmtom', 0)),  # Unrealized P&L
                    'total_pnl': float(pos.get('rpnl', 0)) + float(pos.get('urmtom', 0)),  # Total P&L
                    'pnl_percentage': round(pnl_percentage, 2),  # P&L percentage
                    'product': pos.get('prd', ''),  # Product type (CNC/MIS/NRML)
                    'exchange': pos.get('exch', ''),  # Exchange
                    'market_value': round(market_value, 2),  # Current market value
                    'invested_value': round(invested_value, 2),  # Total invested value
                    'last_update': pos.get('upd', ''),  # Last update time
                }
                formatted_positions.append(formatted_pos)
            
        return formatted_positions
        
    except Exception as e:
        logger.error(f"Error fetching positions: {str(e)}")
        raise Exception(f"Failed to fetch positions: {str(e)}")

async def get_pnl():
    """Fetch current P&L from all positions"""
    try:
        # Get all positions, including closed ones
        positions = api.get_positions()
        
        if not positions:
            return {
                'day_pnl': 0.0,
                'net_pnl': 0.0,
                'positions_count': 0,
                'active_positions': 0
            }
        
        day_pnl = 0
        net_pnl = 0
        active_count = 0
        
        for pos in positions:
            # Calculate P&L for all positions
            day_pnl += float(pos.get('rpnl', 0))  # Realized P&L
            net_pnl += float(pos.get('rpnl', 0)) + float(pos.get('urmtom', 0))  # Total P&L (Realized + Unrealized)
            
            # Count active positions (non-zero quantity)
            if int(pos.get('netqty', 0)) != 0:
                active_count += 1
            
        return {
            'day_pnl': round(day_pnl, 2),
            'net_pnl': round(net_pnl, 2),
            'positions_count': len(positions),  # Total positions
            'active_positions': active_count  # Currently active positions
        }
        
    except Exception as e:
        logger.error(f"Error calculating P&L: {str(e)}")
        raise Exception(f"Failed to calculate P&L: {str(e)}")

async def place_order(symbol, qty, side, product_type='I', price_type='MKT', price=0, trigger_price=0):
    """Place an order using Flattrade API
    
    Args:
        symbol (str): Trading symbol
        qty (int): Quantity to trade
        side (str): 'B' for buy, 'S' for sell
        product_type (str): 'I' for intraday, 'C' for delivery, 'M' for margin
        price_type (str): 'MKT' for market, 'LMT' for limit, 'SL' for stop loss
        price (float): Price for limit orders
        trigger_price (float): Trigger price for stop loss orders
    """
    try:
        if not api:
            await initialize_flattrade()
            
        # Place the order
        ret = api.place_order(
            buy_or_sell=side,  # 'B' or 'S'
            product_type=product_type,  # 'I' for intraday
            exchange='NSE',  # NSE or BSE
            tradingsymbol=symbol,
            quantity=qty,
            discloseqty=0,
            price_type=price_type,  # 'MKT', 'LMT', 'SL'
            price=price,
            trigger_price=trigger_price,
            retention='DAY',
            remarks=f'Order placed via TG Bot'
        )
        
        if ret.get('stat') == 'Ok':
            order_no = ret.get('norenordno')
            return {
                'status': 'success',
                'order_id': order_no,
                'message': f'Order placed successfully. Order ID: {order_no}'
            }
        else:
            raise Exception(ret.get('emsg', 'Unknown error'))
            
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        raise Exception(f"Failed to place order: {str(e)}")

def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    message = f'''🔴 🔴 | Bot Error | {str(context.error)}'''
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={chatID}&text={message}"
    requests.get(url).json()

def main():
    """Start the bot."""
    # Initialize bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(positions_callback, pattern='^positions$'))
    application.add_handler(CallbackQueryHandler(pnl_callback, pattern='^pnl$'))
    application.add_handler(CallbackQueryHandler(new_trade_callback, pattern='^new_trade$'))
    application.add_handler(CallbackQueryHandler(start_callback, pattern='^start$'))
    application.add_handler(CallbackQueryHandler(buy_callback, pattern='^buy$'))
    application.add_handler(CallbackQueryHandler(sell_callback, pattern='^sell$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_order_message))
    application.add_error_handler(error_handler)
    
    # Initialize Flattrade
    print(USER_TOKEN)
    global api
    api = NorenApiPy()
    
    try:
        if USER_TOKEN == '':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(initialize_flattrade())
            loop.close()
        else:
            ret = api.set_session(userid=userid, password=password, usertoken=USER_TOKEN)
            if not ret:
                raise Exception("Failed to set session with existing token")
        print("Flattrade initialized successfully")
    except Exception as e:
        logger.error(f"Flattrade initialization error: {e}")
        message = f'''🔴 🔴 |  FT Login Error | {str(e)}'''
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={chatID}&text={message}"
        requests.get(url).json()
    
    # Start the bot
    print("Starting Telegram bot...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        message = f'''🔴 🔴 | Bot Error | {str(e)}'''
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={chatID}&text={message}"
        requests.get(url).json()
