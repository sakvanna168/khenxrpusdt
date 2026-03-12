# How to Run Your XRPUSDT Signal Bot

Follow these instructions to get your bot running!

### 1. Create a Telegram Bot
1. Open Telegram and search for **@BotFather**.
2. Send the command `/newbot`.
3. Follow the instructions to give your bot a Name and a Username.
4. Once completed, BotFather will give you a **Bot Token** (it looks like `123456789:ABCDefghiJKLM_nopqRSTUvwxYZ`). Copy this token.

### 2. Get your Chat ID
You need to tell the bot where to send messages (either your personal chat or a Telegram Channel).
1. Go to Telegram and search for **@userinfobot** or **@RawDataBot**.
2. Click Start, and it will reply with your personal Info.
3. Look for the `"id": 12345678` under the `chat` section. Copy this ID.
   - *(If sending to a public channel, it might look like `@YourChannelName`)*

### 3. Add to `.env`
1. Open the `.env` (you need to create it by renaming `.env.example` to `.env`) in the `xrp_signal_bot` folder.
2. Replace `YOUR_TELEGRAM_BOT_TOKEN_HERE` with the token from Step 1.
3. Replace `YOUR_TELEGRAM_CHAT_ID_HERE` with the ID from Step 2.

### 4. Run the Bot
Open your terminal in the `xrp_signal_bot` folder and run:
`.\venv\Scripts\activate`
`python bot.py`

Your bot is now running and checking Binance for Trading Signals!
