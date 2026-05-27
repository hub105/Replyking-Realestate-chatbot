import os
import json
from flask import Flask, request, jsonify, render_template_string, session
from groq import Groq
from datetime import datetime

# ======================== CONFIGURATION ========================
# 🔑 PASTE YOUR GROQ API KEY HERE (get it from console.groq.com)
GROQ_API_KEY = "gsk_YOUR_API_KEY_HERE"   # <-- REPLACE WITH YOUR REAL KEY

# If you prefer environment variable (safer), use:
# GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "gsk_...")

# Model selection (fast & smart)
MODEL_NAME = "llama3-70b-8192"   # or "mixtral-8x7b-32768", "llama3-8b-8192"

# ======================== FLASK SETUP ========================
app = Flask(__name__)
app.secret_key = "replace-this-with-a-secret-key-for-sessions"   # change in production

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# ---------------------- SYSTEM PROMPT (AI persona) ----------------------
SYSTEM_PROMPT = """You are PropBot, the official real estate assistant for ReplyKing Properties.
ReplyKing serves Lagos, Abuja, Port Harcourt. You help clients buy, rent, sell properties,
and provide price estimates. Be friendly, professional, and always ask qualifying questions
(budget, location, property type). If a user says 'Buy' ask about budget & preferred area.
If 'Rent' ask about monthly rent range. If 'Sell' ask property details. If 'Prices' give
general market ranges. Keep answers concise but helpful. Never invent fake listings.
When appropriate, suggest scheduling a viewing. Always end with an offer to help further."""

# ---------------------- HTML/CSS/JS (embedded) ----------------------
CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
  <title>PropBot – ReplyKing Properties</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: 'Segoe UI', 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
      background: #e5ddd5;
      height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
    }
    .chat-container {
      width: 100%;
      max-width: 500px;
      height: 90vh;
      background: #f0f2f5;
      border-radius: 28px;
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(0,0,0,0.2);
      display: flex;
      flex-direction: column;
      position: relative;
    }
    /* header */
    .chat-header {
      background: #075E54;
      padding: 16px 20px;
      color: white;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .avatar {
      background: #25D366;
      width: 42px;
      height: 42px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.5rem;
      font-weight: bold;
    }
    .header-info h2 {
      font-size: 1.2rem;
      font-weight: 600;
    }
    .header-info p {
      font-size: 0.75rem;
      opacity: 0.9;
    }
    /* messages area */
    .messages {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background-image: radial-gradient(#c9cfd6 0.8px, transparent 0.8px);
      background-size: 20px 20px;
    }
    .bot-message, .user-message {
      max-width: 80%;
      padding: 10px 14px;
      border-radius: 18px;
      font-size: 0.95rem;
      line-height: 1.4;
      word-wrap: break-word;
    }
    .bot-message {
      background: white;
      align-self: flex-start;
      border-top-left-radius: 4px;
      box-shadow: 0 1px 1px rgba(0,0,0,0.05);
    }
    .user-message {
      background: #dcf8c5;
      align-self: flex-end;
      border-top-right-radius: 4px;
    }
    .quick-reply-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 8px 0 4px;
    }
    .quick-btn {
      background: #ffffffdd;
      backdrop-filter: blur(4px);
      border: 1px solid #25D366;
      padding: 6px 16px;
      border-radius: 30px;
      font-size: 0.8rem;
      font-weight: 600;
      color: #075E54;
      cursor: pointer;
      transition: 0.1s;
    }
    .quick-btn:hover {
      background: #25D366;
      color: white;
    }
    /* input area */
    .input-area {
      background: #f0f2f5;
      padding: 12px 16px;
      display: flex;
      gap: 10px;
      border-top: 1px solid #e0e0e0;
    }
    .input-area input {
      flex: 1;
      padding: 12px 16px;
      border: none;
      border-radius: 30px;
      outline: none;
      font-size: 0.95rem;
      background: white;
    }
    .input-area button {
      background: #25D366;
      border: none;
      color: white;
      width: 44px;
      height: 44px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 1.2rem;
      transition: 0.1s;
    }
    .input-area button:hover {
      background: #128C7E;
    }
    .typing {
      font-size: 0.8rem;
      color: #6b6b6b;
      margin-left: 12px;
      font-style: italic;
    }
    footer {
      font-size: 0.7rem;
      text-align: center;
      background: #f0f2f5;
      padding: 6px;
      color: #777;
    }
    @media (max-width: 550px) {
      .chat-container {
        height: 100vh;
        border-radius: 0;
        max-width: 100%;
      }
    }
  </style>
</head>
<body>
<div class="chat-container">
  <div class="chat-header">
    <div class="avatar">🏠</div>
    <div class="header-info">
      <h2>ReplyKing Properties</h2>
      <p>online • Instant response 24/7</p>
    </div>
  </div>
  <div class="messages" id="messages">
    <!-- dynamic messages -->
    <div class="bot-message">
      <strong>🏙️ Find Your Dream Property</strong><br>
      Lagos • Abuja • Port Harcourt<br>
      <span style="font-size:0.8rem;">✔️ Buy | Rent | Sell | Prices</span>
    </div>
    <div class="bot-message">
      <strong>Welcome to ReplyKing Properties! 🎉</strong><br>
      I am <strong>PropBot</strong>, your personal real estate assistant powered by ReplyKing.<br>
      I can help you buy, sell or rent properties across Nigeria.<br>
      <strong>How may I assist you today?</strong>
      <div class="quick-reply-row" id="quickRow">
        <span class="quick-btn" data-msg="Buy">🏠 Buy</span>
        <span class="quick-btn" data-msg="Rent">📋 Rent</span>
        <span class="quick-btn" data-msg="Sell">💰 Sell</span>
        <span class="quick-btn" data-msg="Prices">💵 Prices</span>
      </div>
    </div>
  </div>
  <div class="input-area">
    <input type="text" id="userInput" placeholder="Type your message..." autofocus>
    <button id="sendBtn">➤</button>
  </div>
  <footer>PropBot by ReplyKing • AI-powered real estate assistant</footer>
</div>

<script>
  const messagesDiv = document.getElementById('messages');
  const userInput = document.getElementById('userInput');
  const sendBtn = document.getElementById('sendBtn');

  function addMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.className = sender === 'user' ? 'user-message' : 'bot-message';
    msgDiv.innerHTML = text.replace(/\\n/g, '<br>');
    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'bot-message typing';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerText = 'PropBot is typing...';
    messagesDiv.appendChild(typingDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function removeTyping() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
  }

  async function sendMessage(message) {
    if (!message.trim()) return;
    // disable input during request
    sendBtn.disabled = true;
    userInput.disabled = true;
    addMessage(message, 'user');
    userInput.value = '';
    showTyping();

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
      });
      const data = await response.json();
      removeTyping();
      if (data.reply) {
        addMessage(data.reply, 'bot');
        // if bot message includes quick suggestion? not needed, but we can re-add quick row?
        // re-attach quick buttons if last message is from bot and we want to show options? skip, they always exist in first message.
      } else {
        addMessage("⚠️ Sorry, I'm having trouble. Please try again.", 'bot');
      }
    } catch (err) {
      removeTyping();
      addMessage("❌ Network error. Check your connection.", 'bot');
    } finally {
      sendBtn.disabled = false;
      userInput.disabled = false;
      userInput.focus();
    }
  }

  sendBtn.addEventListener('click', () => {
    sendMessage(userInput.value);
  });
  userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage(userInput.value);
  });

  // Quick reply buttons (dynamic + static)
  function attachQuickEvents() {
    document.querySelectorAll('.quick-btn').forEach(btn => {
      btn.removeEventListener('click', quickHandler);
      btn.addEventListener('click', quickHandler);
    });
  }
  function quickHandler(e) {
    const msg = e.currentTarget.getAttribute('data-msg');
    if (msg) sendMessage(msg);
  }
  attachQuickEvents();

  // observe for new quick buttons (if any added later)
  const observer = new MutationObserver(() => attachQuickEvents());
  observer.observe(messagesDiv, { childList: true, subtree: true });
</script>
</body>
</html>
"""

# ---------------------- ROUTES ----------------------
@app.route('/')
def index():
    """Serve the chat interface"""
    return render_template_string(CHAT_HTML)

@app.route('/chat', methods=['POST'])
def chat():
    """Handle user message, maintain conversation history using session"""
    if not client.api_key or GROQ_API_KEY == "":
        return jsonify({"reply": "⚠️ Groq API key not configured. Please add your key in app.py and restart."}), 500

    user_message = request.json.get('message', '').strip()
    if not user_message:
        return jsonify({"reply": "Please type a message."}), 400

    # Get or create conversation history in session
    if 'history' not in session:
        # Initialize with system prompt + a welcome context (optional)
        session['history'] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    history = session['history']
    # Append user message
    history.append({"role": "user", "content": user_message})

    # Trim history if too long (keep last ~12 exchanges to avoid token limits)
    # system + last 20 messages (10 user/bot pairs)
    if len(history) > 21:
        # keep system + last 20 messages
        history = [history[0]] + history[-20:]
        session['history'] = history

    try:
        # Call Groq API
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=history,
            temperature=0.7,
            max_tokens=500,
            top_p=0.9,
        )
        bot_reply = completion.choices[0].message.content.strip()

        # Append assistant reply to history
        history.append({"role": "assistant", "content": bot_reply})
        session['history'] = history

        return jsonify({"reply": bot_reply})

    except Exception as e:
        print("Groq API error:", str(e))
        return jsonify({"reply": "🤖 Oops! PropBot is having technical hiccups. Please try again later."}), 500

# ---------------------- RUN ----------------------
if __name__ == '__main__':
    # For local testing; on production use gunicorn
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
