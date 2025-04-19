from flask import Flask
import os
import secrets

def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')),
        static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    )
    
    # Configure session
    app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
    
    from app.backend.routes import chat_bp
    app.register_blueprint(chat_bp)
    
    # Load sample university data on startup
    try:
        from app.backend.utils import load_sample_data
        load_sample_data()
    except Exception as e:
        print(f"Warning: Could not load sample data: {e}")
    
    return app