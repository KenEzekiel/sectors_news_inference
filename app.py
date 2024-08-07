from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
import os
import json
import dotenv
from functools import wraps
from scripts.classifier import get_tickers, get_tags_chat, get_subsector_chat, get_sentiment_chat


dotenv.load_dotenv()

API_KEY = os.getenv("API_KEY")

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'Authorization' not in request.headers:
            return jsonify({"status": "error", "message": "API key required"}), 403
        
        auth_header = request.headers.get('Authorization')
        if auth_header != f"Bearer {API_KEY}":
            return jsonify({"status": "error", "message": "Invalid API key"}), 403

        return f(*args, **kwargs)
    return decorated_function
  

  
app = Flask(__name__)

def inference_data(data):
    body = data.get('body')
    
    tickers = get_tickers(body)
    tags = get_tags_chat(body)
    sub_sector = get_subsector_chat(body)
    sentiment = get_sentiment_chat(body)
    
    return {
        "tickers": tickers,
        "tags": tags,
        "sub_sector": sub_sector,
        "sentiment": sentiment
    }
    

@app.route('/url-article', methods=['POST'])
@require_api_key
def get_data_from_source():
    input_data = request.get_json()
    try:
        return inference_data(input_data), 200
    except Exception as e:
        return {}, 500