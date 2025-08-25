"""
BUDDY Python SDK - Integration Examples

This file demonstrates various ways to integrate BUDDY into Python applications
"""

import asyncio
import time
from buddy_sdk import BuddyClient, BuddyConversation, create_buddy_client


# ===== Basic Usage Examples =====

def basic_chat_example():
    """Basic synchronous chat example"""
    print("🤖 BUDDY Basic Chat Example")
    print("=" * 40)
    
    # Initialize BUDDY client
    buddy = BuddyClient(
        base_url="http://localhost:8081",
        user_id="python_user",
        on_message=lambda response: print(f"BUDDY: {response.response}")
    )
    
    try:
        # Send messages
        response = buddy.chat("Hello BUDDY!")
        print(f"Response confidence: {response.confidence}")
        print(f"Skill used: {response.skill_used}")
        
        # Follow-up conversation
        buddy.chat("What's the weather like?")
        buddy.chat("Can you help me with math? What's 15 * 24?")
        
    except Exception as e:
        print(f"Error: {e}")


async def async_chat_example():
    """Asynchronous chat example"""
    print("\n🚀 BUDDY Async Chat Example")
    print("=" * 40)
    
    buddy = BuddyClient(base_url="http://localhost:8081")
    
    try:
        # Async chat
        response = await buddy.async_chat("Tell me about AI")
        print(f"BUDDY: {response.response}")
        
        # Concurrent skill execution
        tasks = [
            buddy.async_execute_skill("time"),
            buddy.async_execute_skill("calculate", {"expression": "100 + 25"}),
            buddy.async_chat("How's the weather?")
        ]
        
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            print(f"Task {i+1}: {result}")
            
    except Exception as e:
        print(f"Error: {e}")


# ===== Advanced Integration Examples =====

class ChatBot:
    """Simple chatbot using BUDDY"""
    
    def __init__(self):
        self.buddy = BuddyClient(
            base_url="http://localhost:8081",
            on_error=self.handle_error
        )
        self.conversation = BuddyConversation(self.buddy)
    
    def handle_error(self, error):
        print(f"Chatbot error: {error}")
    
    def run(self):
        """Run interactive chatbot"""
        print("🤖 BUDDY Chatbot (type 'quit' to exit)")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("BUDDY: Goodbye! Have a great day!")
                    break
                
                if not user_input:
                    continue
                
                # Send message to BUDDY
                response = self.conversation.chat(user_input)
                print(f"BUDDY: {response.response}")
                
                # Show conversation stats
                if len(self.conversation.history) % 10 == 0:
                    print(f"\n📊 Conversation stats: {len(self.conversation.history)} messages")
                
            except KeyboardInterrupt:
                print("\nBUDDY: Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")


# ===== Flask Web Integration =====

flask_integration = '''
from flask import Flask, request, jsonify, render_template
from buddy_sdk import BuddyClient, BuddyConversation

app = Flask(__name__)

# Initialize BUDDY
buddy = BuddyClient(base_url="http://localhost:8081")
conversations = {}  # Store user conversations

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message')
    user_id = data.get('user_id', 'web_user')
    
    # Get or create conversation for user
    if user_id not in conversations:
        conversations[user_id] = BuddyConversation(buddy)
    
    conversation = conversations[user_id]
    
    try:
        response = conversation.chat(message)
        return jsonify({
            'success': True,
            'response': response.response,
            'confidence': response.confidence,
            'skill_used': response.skill_used
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/skills')
def get_skills():
    try:
        skills = buddy.get_skills()
        return jsonify({'success': True, 'skills': skills})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history/<user_id>')
def get_history(user_id):
    if user_id in conversations:
        history = conversations[user_id].get_history()
        return jsonify({
            'success': True,
            'history': [
                {
                    'content': msg.content,
                    'sender': msg.sender,
                    'timestamp': msg.timestamp
                } for msg in history
            ]
        })
    else:
        return jsonify({'success': True, 'history': []})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
'''


# ===== FastAPI Integration =====

fastapi_integration = '''
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from buddy_sdk import BuddyClient, BuddyConversation

app = FastAPI(title="BUDDY Integration API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize BUDDY
buddy = BuddyClient(base_url="http://localhost:8081")
conversations = {}

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "api_user"
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    confidence: float
    skill_used: str
    execution_time: float

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send message to BUDDY"""
    try:
        # Get or create conversation
        conv_key = f"{request.user_id}_{request.session_id or 'default'}"
        if conv_key not in conversations:
            conversations[conv_key] = BuddyConversation(buddy)
        
        conversation = conversations[conv_key]
        response = await conversation.async_chat(request.message)
        
        return ChatResponse(
            response=response.response,
            confidence=response.confidence,
            skill_used=response.skill_used,
            execution_time=response.execution_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/skills")
async def get_skills():
    """Get available BUDDY skills"""
    try:
        skills = await buddy.async_get_skills()
        return {"skills": skills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Check if BUDDY is healthy"""
    try:
        health = buddy.get_health()
        return health
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''


# ===== Discord Bot Integration =====

discord_integration = '''
import discord
from discord.ext import commands
from buddy_sdk import BuddyClient, BuddyConversation

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!buddy ', intents=intents)

# Initialize BUDDY
buddy = BuddyClient(base_url="http://localhost:8081")
conversations = {}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'BUDDY integration active on {len(bot.guilds)} servers')

@bot.command(name='chat')
async def buddy_chat(ctx, *, message):
    """Chat with BUDDY"""
    user_id = str(ctx.author.id)
    
    # Get or create conversation
    if user_id not in conversations:
        conversations[user_id] = BuddyConversation(buddy)
    
    conversation = conversations[user_id]
    
    try:
        # Show typing indicator
        async with ctx.typing():
            response = await conversation.async_chat(message)
        
        # Send response
        await ctx.send(f"🤖 **BUDDY**: {response.response}")
        
        # Add reaction based on confidence
        if response.confidence > 0.8:
            await ctx.message.add_reaction('✅')
        elif response.confidence > 0.5:
            await ctx.message.add_reaction('👍')
        else:
            await ctx.message.add_reaction('🤔')
            
    except Exception as e:
        await ctx.send(f"❌ Sorry, I couldn't process that: {str(e)}")

@bot.command(name='skills')
async def buddy_skills(ctx):
    """List BUDDY's skills"""
    try:
        skills = await buddy.async_get_skills()
        skill_list = "\\n".join([f"• {skill['name']}: {skill['description']}" 
                               for skill in skills[:10]])  # Limit to 10 skills
        
        embed = discord.Embed(
            title="🛠️ BUDDY's Skills",
            description=skill_list,
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Couldn't get skills: {str(e)}")

@bot.command(name='clear')
async def clear_conversation(ctx):
    """Clear conversation history"""
    user_id = str(ctx.author.id)
    if user_id in conversations:
        conversations[user_id].clear_history()
        await ctx.send("🧹 Conversation history cleared!")
    else:
        await ctx.send("📝 No conversation history to clear.")

# Run bot (you need to set your Discord bot token)
# bot.run('YOUR_DISCORD_BOT_TOKEN')
'''


# ===== Telegram Bot Integration =====

telegram_integration = '''
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from buddy_sdk import BuddyClient, BuddyConversation

# Initialize BUDDY
buddy = BuddyClient(base_url="http://localhost:8081")
conversations = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    await update.message.reply_text(
        "🤖 Hello! I'm BUDDY AI Assistant.\\n"
        "Send me any message and I'll help you out!\\n\\n"
        "Commands:\\n"
        "/start - Show this message\\n"
        "/skills - List my skills\\n"
        "/clear - Clear conversation history"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    user_id = str(update.effective_user.id)
    message = update.message.text
    
    # Get or create conversation
    if user_id not in conversations:
        conversations[user_id] = BuddyConversation(buddy)
    
    conversation = conversations[user_id]
    
    try:
        # Send typing action
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Get BUDDY response
        response = await conversation.async_chat(message)
        
        # Send response
        await update.message.reply_text(f"🤖 {response.response}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Sorry, something went wrong: {str(e)}")

async def skills_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show BUDDY skills"""
    try:
        skills = await buddy.async_get_skills()
        skill_text = "🛠️ **BUDDY's Skills:**\\n\\n"
        
        for skill in skills[:10]:  # Limit to 10 skills
            skill_text += f"• **{skill['name']}**: {skill['description']}\\n"
        
        await update.message.reply_text(skill_text, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Couldn't get skills: {str(e)}")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history"""
    user_id = str(update.effective_user.id)
    if user_id in conversations:
        conversations[user_id].clear_history()
        await update.message.reply_text("🧹 Conversation history cleared!")
    else:
        await update.message.reply_text("📝 No conversation history to clear.")

def main():
    """Start the Telegram bot"""
    # Create application (you need to set your Telegram bot token)
    application = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("skills", skills_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
'''


# ===== Data Analysis Integration =====

def data_analysis_example():
    """Example of using BUDDY for data analysis tasks"""
    print("\n📊 BUDDY Data Analysis Example")
    print("=" * 40)
    
    buddy = BuddyClient(base_url="http://localhost:8081")
    
    # Sample data analysis queries
    queries = [
        "Analyze the trend in this data: [1, 3, 5, 7, 9, 11, 13]",
        "What's the correlation between temperature and ice cream sales?",
        "How do I calculate the mean absolute error?",
        "Explain linear regression in simple terms",
        "What's the best chart type for time series data?"
    ]
    
    for query in queries:
        try:
            response = buddy.chat(query)
            print(f"\nQ: {query}")
            print(f"A: {response.response}")
            print(f"Confidence: {response.confidence:.2f}")
        except Exception as e:
            print(f"Error with query '{query}': {e}")


# ===== Streaming Example =====

async def streaming_example():
    """Example of streaming responses from BUDDY"""
    print("\n🌊 BUDDY Streaming Example")
    print("=" * 40)
    
    buddy = BuddyClient(base_url="http://localhost:8081")
    
    def handle_chunk(chunk):
        if chunk.get('type') == 'message':
            print(chunk.get('content', ''), end='', flush=True)
        elif chunk.get('type') == 'complete':
            print("\n✅ Stream complete!")
    
    try:
        print("BUDDY: ", end='', flush=True)
        await buddy.stream_chat(
            "Tell me a short story about a robot learning to paint",
            handle_chunk
        )
    except Exception as e:
        print(f"\nStreaming error: {e}")


# ===== Run Examples =====

if __name__ == "__main__":
    print("🤖 BUDDY Python SDK Examples")
    print("=" * 50)
    
    # Run synchronous examples
    basic_chat_example()
    data_analysis_example()
    
    # Run asynchronous examples
    asyncio.run(async_chat_example())
    asyncio.run(streaming_example())
    
    # Interactive chatbot (uncomment to run)
    # chatbot = ChatBot()
    # chatbot.run()
    
    print("\n📚 Additional integrations available:")
    print("• Flask web app")
    print("• FastAPI service")
    print("• Discord bot")
    print("• Telegram bot")
    print("• Data analysis workflows")
    print("\nCheck the source code for implementation details!")
