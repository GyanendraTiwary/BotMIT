from flask import Flask, session
from flask_session import Session
import os
import secrets
import uuid

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')),
        static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    )
    
    # Configure session
    app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
    app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem storage
    app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(__file__), '..', 'flask_session')
    app.config['SESSION_PERMANENT'] = False  # Non-permanent sessions
    app.config['SESSION_USE_SIGNER'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour (adjust as needed)

    
    # Initialize Flask-Session
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    Session(app)
    
    from app.backend.routes import chat_bp
    app.register_blueprint(chat_bp)
    
    # Load sample university data on startup
    try:
        from app.backend.utils import load_sample_data
        load_sample_data()
    except Exception as e:
        print(f"Warning: Could not load sample data: {e}")
    
    return app