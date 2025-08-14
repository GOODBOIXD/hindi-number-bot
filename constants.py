# bot.py
import os
import logging
from typing import Optional
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from rapidfuzz import process

# Import the dictionary from the constants file
from constants import HINDI_NUMBERS

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class HindiNumberBot:
    def __init__(self, telegram_token: str, openai_api_key: Optional[str] = None):
        self.telegram_token = telegram_token
        # Create an async client instance if the key exists
        self.openai_client = AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None
    
    def find_closest_match(self, word: str, threshold: int = 80) -> Optional[int]:
        """Find the closest matching Hindi number using fuzzy matching."""
        word = word.strip().lower()
        
        # Direct match first for speed
        if word in HINDI_NUMBERS:
            return HINDI_NUMBERS[word]
        
        # Fuzzy match if no direct match is found
        match = process.extractOne(word, HINDI_NUMBERS.keys())
        if match and match[1] >= threshold:
            logger.info("Fuzzy match found for '%s': '%s' with score %d", word, match[0], match[1])
            return HINDI_NUMBERS[match[0]]
        
        return None
    
    async def gpt_fallback(self, word: str) -> Optional[int]:
        """Use GPT API as a fallback for unmatched words."""
        if not self.openai_client:
            return None
            
        try:
            messages = [
                {"role": "system", "content": "You are an expert at converting Hindi number words to numerals. Respond only with the number (e.g., '52'). If the input is not a number, respond with 'UNKNOWN'."},
                {"role": "user", "content": f'"{word}"'}
            ]
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cheaper, faster, and very capable
                messages=messages,
                max_tokens=10,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip()
            
            if result.isdigit():
                number = int(result)
                if 0 <= number <= 1000:  # Basic validation for reasonableness
                    return number
                    
        except Exception as e:
            # Use formatting arguments for better logging practice
            logger.error("GPT API error: %s", e)
            
        return None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        welcome_message = """🙏 Welcome to the Hindi Number Bot!

Send me a Hindi number written in English (e.g., bavan) or Devanagari (e.g., बावन), and I'll convert it to a numeral.

**I can handle:**
✅ Numbers 0-100
✅ Multiple spellings
✅ Common typos

Give it a try! Send a number word now."""
        
        await update.message.reply_text(welcome_message)
    
    async def translate_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main translation logic."""
        if not update.message or not update.message.text:
            return
            
        word = update.message.text.strip()
        
        # Try our local dictionary first (direct and fuzzy matching)
        number = self.find_closest_match(word)
        
        if number is not None:
            await update.message.reply_text(f"✅ {word} → {number}")
            return
        
        # If no local match, and we have an API key, try the GPT fallback
        if self.openai_client:
            await update.message.reply_chat_action('typing')
            gpt_number = await self.gpt_fallback(word)
            
            if gpt_number is not None:
                confidence_msg = ""
                # Find all known spellings for the number GPT guessed
                known_spellings = [key for key, value in HINDI_NUMBERS.items() if value == gpt_number]
                
                if known_spellings:
                    # Check if the user's word is similar to any of our known spellings
                    match = process.extractOne(word.lower(), known_spellings)
                    # If the similarity is low, it was likely a pure AI guess
                    if not match or match[1] < 75:
                        confidence_msg = " (AI guess, please verify)"
                else:
                    # If we don't have this number in our dictionary at all
                    confidence_msg = " (AI guess, outside my dictionary)"
                    
                await update.message.reply_text(f"🤖 {word} → {gpt_number}{confidence_msg}")
                return
        
        # If all methods fail, send a "not found" message
        await update.message.reply_text(
            f"❌ Sorry, I couldn't recognize '{word}'.\n\nPlease check the spelling or try another number."
        )
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log errors caused by updates."""
        logger.error("Update %s caused error %s", update, context.error)
    
    def run(self):
        """Build and run the bot."""
        app = Application.builder().token(self.telegram_token).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.translate_number))
        app.add_error_handler(self.error_handler)
        
        logger.info("Starting bot...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Entry point of the script."""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not telegram_token:
        logger.critical("TELEGRAM_BOT_TOKEN environment variable not set. Exiting.")
        return
    
    if not openai_key:
        logger.warning("OPENAI_API_KEY not found. GPT fallback will be disabled.")
    
    bot = HindiNumberBot(telegram_token, openai_key)
    bot.run()

if __name__ == "__main__":
    main()
