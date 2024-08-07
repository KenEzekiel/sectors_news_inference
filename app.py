from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
import os
import json
import dotenv
from supabase import create_client, Client
from functools import wraps

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

