# Telegram Trade Bot

A Telegram bot for managing and monitoring trading activities through FlatTrade API.

## Features

- View current positions
- Check P&L status
- Place new trades
- Real-time trade monitoring
- Secure authentication

## Prerequisites

- Python 3.7+
- Telegram Bot Token
- FlatTrade API credentials

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd telegram_trade_bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Create a `cred.yaml` file with your credentials:
```yaml
telegram:
  telegramToken: "YOUR_TELEGRAM_BOT_TOKEN"
  chatID: "YOUR CHAT ID"

flattrade:
  user: "YOUR_FLATTRADE_USER_ID"
  pwd: "YOUR_FLATTRADE_PASSWORD"
  apikey: "YOUR_FLATTRADE_API_KEY"
  totp_key: "YOUR_TOTP_KEY"
  apisecret: "YOUR API SECRET"
  user_token: "Generated User Token"
```

## Running the Bot

1. Make sure you're in the virtual environment:
```bash
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Ensure your `cred.yaml` file is properly configured with all required credentials:
   - Telegram credentials:
     - `telegramToken`: Your Telegram bot token from BotFather
     - `chatID`: Your Telegram chat ID (this restricts bot access to only your chat)
   - FlatTrade credentials:
     - `user`: Your FlatTrade user ID
     - `pwd`: Your FlatTrade password
     - `apikey`: FlatTrade API key
     - `totp_key`: TOTP key for 2FA authentication
     - `apisecret`: Your FlatTrade API secret
     - `user_token`: Your generated user token

3. Run the main script:
```bash
python main.py
```

The bot will:
- Initialize logging with INFO level
- Authenticate with FlatTrade using your credentials
- Start the Telegram bot and listen for commands

4. In your Telegram chat, start the bot:
   - Send `/start` to initialize the bot
   - Use the inline keyboard menu to:
     - View your current positions
     - Check your P&L
     - Place new trades

## Bot Features

The bot provides the following functionality:
- Real-time position tracking
- P&L monitoring
- Trade execution with various order types:
  - Market orders
  - Limit orders
  - Stop-loss orders
- Support for different product types:
  - Intraday (I)
  - Delivery (C)
  - Margin (M)

## Placing Orders

To place a trade through the Telegram bot:

1. Click the "New Trade" button from the main menu
2. Select trade direction:
   - "Buy" for long positions
   - "Sell" for short positions
3. After selecting Buy or Sell, send your order details in the following format:
   ```
   Symbol Quantity [Price] [TriggerPrice]
   ```

Order Format Examples:
- Market Order: `RELIANCE-EQ 10`
- Limit Order: `TATASTEEL-EQ 5 850.50`
- Stop Loss Order: `INFY-EQ 15 1200 1190`

The bot supports the following order parameters:
- Symbol: Trading symbol (e.g., "RELIANCE-EQ")
- Quantity: Number of shares to trade
- Order Types (automatically determined by parameters):
  - Market Order (MKT): Only symbol and quantity
  - Limit Order (LMT): Symbol, quantity, and price
  - Stop Loss (SL): Symbol, quantity, price, and trigger price
- Product Types:
  - Intraday (I)
  - Delivery (C)
  - Margin (M)

All orders are placed with:
- Exchange: NSE
- Retention: DAY
- Disclosure Quantity: 0

After order placement:
- You'll receive a confirmation message with the order ID
- Any errors during order placement will be displayed in the chat

## Security Features

- TOTP-based two-factor authentication for FlatTrade
- Chat ID verification to restrict bot access
- Secure session management with FlatTrade API
- Encrypted password handling

## Logging

The bot includes comprehensive logging that provides:
- Timestamp for each operation
- Operation type and status
- Error messages and stack traces for debugging

Logs are output to the console in the format:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## Available Commands

- `/start` - Initialize the bot and show main menu
- Use the inline keyboard buttons to:
  - View Positions
  - Check P&L
  - Place New Trades

## Error Handling

The bot includes comprehensive error handling and logging. Check the console output for any issues.

## Support

For any issues or questions, please open an issue in the repository.
