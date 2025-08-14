import os
import logging
import asyncio
from typing import Optional, Dict
import openai
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from rapidfuzz import process
import re

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Hindi numbers dictionary (0-100) - Source: Transparent.com
HINDI_NUMBERS = {
    # 0-10
    "shuniye": 0, "zero": 0, "शून्य": 0,
    "ek": 1, "एक": 1,
    "do": 2, "दो": 2,
    "teen": 3, "तीन": 3,
    "char": 4, "चार": 4,
    "panch": 5, "पांच": 5,
    "cheh": 6, "छह": 6,
    "saat": 7, "सात": 7,
    "aath": 8, "आठ": 8,
    "nao": 9, "नौ": 9,
    "das": 10, "दस": 10,
    
    # 11-20
    "gyaarah": 11, "ग्यारह": 11,
    "baarah": 12, "बारह": 12,
    "tehrah": 13, "तेरह": 13,
    "chaudah": 14, "चौदह": 14,
    "pandrah": 15, "पंद्रह": 15,
    "saulah": 16, "सोलह": 16,
    "satrah": 17, "सत्रह": 17,
    "atharah": 18, "अठारह": 18,
    "unnis": 19, "उन्नीस": 19,
    "bees": 20, "बीस": 20,
    
    # 21-30
    "ikis": 21, "इकीस": 21,
    "bais": 22, "बाईस": 22,
    "teis": 23, "तेइस": 23,
    "chaubis": 24, "चौबीस": 24,
    "pachis": 25, "पच्चीस": 25,
    "chabis": 26, "छब्बीस": 26,
    "satais": 27, "सताइस": 27,
    "athais": 28, "अट्ठाइस": 28,
    "unatis": 29, "उनतीस": 29,
    "tis": 30, "तीस": 30,
    
    # 31-40
    "ikatis": 31, "इकतीस": 31,
    "batis": 32, "बतीस": 32,
    "tentis": 33, "तैंतीस": 33,
    "chautis": 34, "चौंतीस": 34,
    "pentis": 35, "पैंतीस": 35,
    "chatis": 36, "छतीस": 36,
    "setis": 37, "सैंतीस": 37,
    "adhtis": 38, "अड़तीस": 38,
    "untaalis": 39, "उनतालीस": 39,
    "chalis": 40, "चालीस": 40,
    
    # 41-50
    "iktalis": 41, "इकतालीस": 41,
    "byalis": 42, "बयालीस": 42,
    "tetalis": 43, "तैतालीस": 43,
    "chavalis": 44, "चवालीस": 44,
    "pentalis": 45, "पैंतालीस": 45,
    "chyalis": 46, "छयालिस": 46,
    "setalis": 47, "सैंतालीस": 47,
    "adtalis": 48, "अड़तालीस": 48,
    "unachas": 49, "उनचास": 49,
    "pachas": 50, "पचास": 50,
    
    # 51-60
    "ikyavan": 51, "इक्यावन": 51,
    "baavan": 52, "बावन": 52,
    "tirepan": 53, "तिरपन": 53,
    "chauvan": 54, "चौवन": 54,
    "pachpan": 55, "पचपन": 55,
    "chappan": 56, "छप्पन": 56,
    "satavan": 57, "सतावन": 57,
    "athaavan": 58, "अठावन": 58,
    "unsadh": 59, "उनसठ": 59,
    "saadh": 60, "साठ": 60,
    
    # 61-70
    "iksadh": 61, "इकसठ": 61,
    "baasad": 62, "बासठ": 62,
    "tirsadh": 63, "तिरसठ": 63,
    "chausadh": 64, "चौंसठ": 64,
    "pensadh": 65, "पैंसठ": 65,
    "chiyasadh": 66, "छियासठ": 66,
    "sadhsadh": 67, "सड़सठ": 67,
    "asdhsadh": 68, "अड़सठ": 68,
    "unahtar": 69, "उनहतर": 69,
    "sattar": 70, "सत्तर": 70,
    
    # 71-80
    "ikahtar": 71, "इकहतर": 71,
    "bahatar": 72, "बहतर": 72,
    "tihatar": 73, "तिहतर": 73,
    "chauhatar": 74, "चौहतर": 74,
    "pachhatar": 75, "पचहतर": 75,
    "chiyahatar": 76, "छिहतर": 76,
    "satahatar": 77, "सतहतर": 77,
    "adhahatar": 78, "अठहतर": 78,
    "unnasi": 79, "उन्नासी": 79,
    "assi": 80, "अस्सी": 80,
    
    # 81-90
    "ikyasi": 81, "इक्यासी": 81,
    "byaasi": 82, "बयासी": 82,
    "tirasi": 83, "तिरासी": 83,
    "chaurasi": 84, "चौरासी": 84,
    "pachasi": 85, "पचासी": 85,
    "chiyaasi": 86, "छियासी": 86,
    "sataasi": 87, "सतासी": 87,
    "athasi": 88, "अट्ठासी": 88,
    "nauasi": 89, "नवासी": 89,
    "nabbe": 90, "नब्बे": 90,
    
    # 91-100
    "ikyaanave": 91, "इक्यानवे": 91,
    "baanave": 92, "बानवे": 92,
    "tiranave": 93, "तिरानवे": 93,
    "chauraanave": 94, "चौरानवे": 94,
    "pachaanave": 95, "पचानवे": 95,
    "chiyaanave": 96, "छियानवे": 96,
    "sataanave": 97, "सतानवे": 97,
    "adhaanave": 98, "अट्ठानवे": 98,
    "ninyaanave": 99, "निन्यानवे": 99,
    "ek sau": 100, "एक सौ": 100, "sau": 100,
    
    # Common alternative spellings and variations
    "baavan": 52,  # Alternative for 52
    "bavan": 52,   # Common misspelling
    "banvan": 52,  # Typo example from your request
    "unnatar": 79, # Alternative for 79
}

class HindiNumberBot:
    def __init__(self, telegram_token: str, openai_api_key: Optional[str] = None):
        self.telegram_token = telegram_token
        self.openai_api_key = openai_api_key
        if openai_api_key:
            openai.api_key = openai_api_key
        
    def find_closest_match(self, word: str, threshold: int = 80) -> Optional[int]:
        """Find closest matching Hindi number using fuzzy matching"""
        word = word.strip().lower()
        
        # Direct match first
        if word in HINDI_NUMBERS:
            return HINDI_NUMBERS[word]
        
        # Fuzzy match
        match = process.extractOne(word, HINDI_NUMBERS.keys())
        if match and match[1] >= threshold:
            return HINDI_NUMBERS[match[0]]
        
        return None
    
    async def gpt_fallback(self, word: str) -> Optional[int]:
        """Use GPT API as fallback for unmatched words"""
        if not self.openai_api_key:
            return None
            
        try:
            prompt = f"""Convert this Hindi number word to English numeral. Only respond with the number, nothing else.
            
            Hindi word: "{word}"
            
            If you're not sure or it's not a valid Hindi number word, respond with "UNKNOWN"."""
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip()
            
            # Try to extract number from response
            number_match = re.search(r'\b\d+\b', result)
            if number_match:
                number = int(number_match.group())
                # Validate number is reasonable (0-1000)
                if 0 <= number <= 1000:
                    return number
            
        except Exception as e:
            logger.error(f"GPT API error: {e}")
            
        return None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """🙏 Welcome to Hindi Number Translator Bot!

Send me any Hindi number word and I'll convert it to English numerals.

Examples:
• bavan → 52
• unnatar → 79
• तीन → 3

I can handle:
✅ Numbers 0-100
✅ Multiple spellings (bavan, bāvan, बावन)
✅ Typos and variations

Just send me a Hindi number word to try it out!"""
        
        await update.message.reply_text(welcome_message)
    
    async def translate_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main translation function"""
        if not update.message or not update.message.text:
            return
            
        word = update.message.text.strip()
        
        if not word:
            await update.message.reply_text("Please send a Hindi number word!")
            return
        
        # Try fuzzy matching first
        number = self.find_closest_match(word)
        
        if number is not None:
            await update.message.reply_text(f"✅ {word} → {number}")
            return
        
        # Try GPT fallback
        if self.openai_api_key:
            await update.message.reply_text("🤔 Checking with AI...")
            gpt_number = await self.gpt_fallback(word)
            
            if gpt_number is not None:
                # Double-check GPT result against our dictionary
                confidence_msg = ""
                closest = self.find_closest_match(str(gpt_number), threshold=60)
                if closest != gpt_number:
                    confidence_msg = " (AI guess - please verify)"
                
                await update.message.reply_text(f"🤖 {word} → {gpt_number}{confidence_msg}")
                return
        
        # No match found
        await update.message.reply_text(
            f"❌ Sorry, I couldn't recognize '{word}' as a Hindi number.\n\n"
            "Try:\n• Different spelling (bavan, bāvan)\n• Numbers 0-100\n• /start for examples"
        )
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
    
    def run(self):
        """Start the bot"""
        # Build application
        app = Application.builder().token(self.telegram_token).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.translate_number))
        app.add_error_handler(self.error_handler)
        
        # Start bot
        logger.info("Starting Hindi Number Bot...")
        
        # Use webhooks in production, polling for development
        if os.getenv("RENDER"):  # Render.com environment
            port = int(os.environ.get("PORT", 8000))
            app.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=self.telegram_token,
                webhook_url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{self.telegram_token}"
            )
        else:
            app.run_polling()

def main():
    """Main function"""
    # Get tokens from environment variables
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is required!")
        return
    
    if not openai_key:
        logger.warning("OPENAI_API_KEY not found. GPT fallback will be disabled.")
    
    # Create and run bot
    bot = HindiNumberBot(telegram_token, openai_key)
    bot.run()

if __name__ == "__main__":
    main()