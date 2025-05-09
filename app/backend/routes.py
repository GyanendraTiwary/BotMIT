# backend/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, session
import google.generativeai as genai
import os
import uuid
from app.backend.rag_engine import RAGEngine
from werkzeug.utils import secure_filename
import bleach
import markdown
import re
from functools import wraps
import glob
from config import ADMIN_USERNAME, check_password, GOOGLE_API_KEY

chat_bp = Blueprint('chat_bp', __name__)

# Set your Google API key
google_api_key = GOOGLE_API_KEY
genai.configure(api_key=google_api_key)

# Initialize RAG engine
rag_engine = RAGEngine()

# Configure allowed HTML tags and attributes for safe markdown rendering
allowed_tags = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
    'em', 'strong', 'del', 'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'blockquote', 'code', 'pre', 'a', 'img', 'table', 'thead', 'tbody',
    'tr', 'th', 'td', 'sup', 'sub'
]

allowed_attrs = {
    '*': ['class'],
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'th': ['scope', 'colspan', 'rowspan'],
    'td': ['colspan', 'rowspan']
}

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('chat_bp.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def process_markdown(text):
    """Convert markdown to HTML and sanitize the output"""
    # Convert markdown to HTML
    html = markdown.markdown(text, extensions=['extra', 'nl2br'])
    
    # Sanitize HTML to prevent XSS attacks
    sanitized_html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs)
    
    return sanitized_html

@chat_bp.route('/', methods=['GET', 'POST'])
def chat():
    # Check if this is a new tab/window by checking the Referer header
    referer = request.headers.get('Referer', '')
    current_url = request.base_url
    
    # If there's no referer or it doesn't match our domain, it's likely a new tab
    if not referer or current_url not in referer:
        # Generate a new session ID for each new browser tab or window
        session['session_id'] = str(uuid.uuid4())
        session['chat_history'] = []
        # Add welcome message
        session['chat_history'].append({
            'sender': 'bot',
            'text': process_markdown("# Welcome to BotMIT! 👋\nI'm your university assistant. How can I help you today?"),
            'raw_text': "# Welcome to BotMIT! 👋\nI'm your university assistant. How can I help you today?"
        })

    # Generate a new session ID for each new browser tab or window
    if request.method == 'GET' and 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session['chat_history'] = []
    
    # Initialize chat history in session if it doesn't exist
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    if request.method == 'POST':
        # Check if the request is JSON (from fetch) or form (from regular form submit)
        if request.is_json:
            user_input = request.json.get('user_input')
        else:
            user_input = request.form.get('user_input')

        try:
            # Get current chat history from session
            chat_history = session.get('chat_history', [])
            
            # Add user message to history
            chat_history.append({'sender': 'user', 'text': user_input})
            
            # Use RAG Engine with conversation history
            bot_response = rag_engine.generate_response(
                user_input,
                conversation_history=chat_history, 
                system_prompt="You are BotMIT, a helpful University Assistant. Answer university-related questions based on the provided context. Format your responses with markdown for better readability. Use headers (# for main headings, ## for subheadings), bold (**text**) for emphasis, lists (* item) where appropriate, and other markdown formatting to make your responses clear and structured."
            )
            
            # Process markdown in the response (for displaying in the template)
            processed_response = process_markdown(bot_response)
            
            # Add bot response to history (store both raw and processed versions)
            chat_history.append({
                'sender': 'bot', 
                'text': processed_response,  # Store the HTML version
                'raw_text': bot_response     # Store the raw markdown for follow-up context
            })
            
            # Update session chat history
            session['chat_history'] = chat_history
            
            # If it's a JSON request, return JSON response
            if request.is_json:
                return jsonify({'bot_response': processed_response})
                
        except Exception as e:
            error_message = f"Error: {str(e)}"
            print(f"Error details: {e}")
            
            # Update session with error
            chat_history = session.get('chat_history', [])
            chat_history.append({'sender': 'user', 'text': user_input})
            chat_history.append({'sender': 'bot', 'text': error_message})
            session['chat_history'] = chat_history
            
            # If it's a JSON request, return JSON error
            if request.is_json:
                return jsonify({'bot_response': error_message}), 500

        # For form submissions, redirect
        if not request.is_json:
            return redirect(url_for('chat_bp.chat'))

    return render_template('index.html', messages=session.get('chat_history', []))

@chat_bp.route('/clear', methods=['POST'])
def clear_chat():
    session['chat_history'] = []  # Clear chat history but keep session ID
    return '', 204  # No Content (better for fetch)

@chat_bp.route('/new-session', methods=['POST'])
def new_session():
    """Create a brand new session - can be triggered by a button"""
    session.clear()  # Clear the entire session
    session['session_id'] = str(uuid.uuid4())
    session['chat_history'] = []
    return '', 204  # No Content

@chat_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    error = None
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            error = "Username and password are required."
        elif username != ADMIN_USERNAME or not check_password(password):
            error = "Invalid username or password."
        else:
            session['admin_logged_in'] = True
            return redirect(url_for('chat_bp.admin_dashboard'))
    
    return render_template('admin_login.html', error=error)

@chat_bp.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('chat_bp.chat'))

@chat_bp.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard page"""
    # Get list of all documents
    documents = rag_engine.documents
    
    # Get list of all PDFs
    pdf_files = []
    for file in glob.glob(os.path.join(rag_engine.pdf_dir, "*.pdf")):
        pdf_files.append({
            'filename': os.path.basename(file),
            'path': file,
            'size': f"{os.path.getsize(file) / 1024:.1f} KB"
        })
    
    return render_template('admin_dashboard.html', 
                           documents=documents, 
                           pdf_files=pdf_files)

@chat_bp.route('/admin/add-document', methods=['GET', 'POST'])
@admin_required
def add_document():
    """Admin interface to add documents to the RAG system"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        source = request.form.get('source', 'university_data')
        
        if title and content:
            doc_id = rag_engine.add_document(title, content, source)
            return render_template('admin_add_document.html', 
                                  message=f"Document added successfully with ID: {doc_id}")
        else:
            return render_template('admin_add_document.html', 
                                  error="Title and content are required")
            
    return render_template('admin_add_document.html')

@chat_bp.route('/admin/upload-pdf', methods=['GET', 'POST'])
@admin_required
def upload_pdf():
    """Admin interface to upload PDF files to the RAG system"""
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'pdf_file' not in request.files:
            return render_template('admin_upload_pdf.html', 
                                   error="No file part")
                                   
        file = request.files['pdf_file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            return render_template('admin_upload_pdf.html', 
                                   error="No selected file")
                                   
        if file and file.filename.endswith('.pdf'):
            try:
                # Process and save the PDF
                filename = secure_filename(file.filename)
                saved_filename = rag_engine.upload_pdf(file, filename)
                
                return render_template('admin_upload_pdf.html', 
                                       message=f"PDF file '{saved_filename}' uploaded and processed successfully")
            except Exception as e:
                return render_template('admin_upload_pdf.html', 
                                       error=f"Error processing PDF: {str(e)}")
        else:
            return render_template('admin_upload_pdf.html', 
                                   error="Invalid file. Please upload a PDF file.")
            
    return render_template('admin_upload_pdf.html')

@chat_bp.route('/admin/delete-document/<int:doc_id>', methods=['POST'])
@admin_required
def delete_document(doc_id):
    """Delete a text document from the knowledge base"""
    try:
        # Delete document using the RAG engine's method
        success = rag_engine.delete_document(doc_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Document deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete document'}), 500
            
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@chat_bp.route('/admin/delete-pdf/<filename>', methods=['POST'])
@admin_required
def delete_pdf(filename):
    """Delete a PDF file from the system"""
    try:
        # Secure the filename
        filename = secure_filename(filename)
        
        # Delete PDF using the RAG engine's method
        success = rag_engine.delete_pdf(filename)
        
        if success:
            return jsonify({'success': True, 'message': 'PDF deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete PDF'}), 500
            
    except FileNotFoundError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500