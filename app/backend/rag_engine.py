# backend/rag_engine.py
import os
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
import PyPDF2
import glob
import hashlib

class RAGEngine:
    def __init__(self, data_dir='data/', embedding_path='embeddings_db/embeddings.npz'):
        """
        Initialize the RAG Engine with paths to data directory and embeddings
        """
        self.data_dir = data_dir
        self.pdf_dir = os.path.join(data_dir, 'pdfs')
        self.data_path = os.path.join(data_dir, 'university_data.json')
        self.embedding_path = embedding_path
        self.documents = []
        self.embeddings = None
        self.vectorizer = TfidfVectorizer()
        
        # Ensure directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.pdf_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.embedding_path), exist_ok=True)
        
        # Load data and create embeddings if they don't exist
        self._load_data()
        self._load_or_create_embeddings()
        
        # Configure API
        self.api_key = "AIzaSyDdw6HUrtinwKhXBLMO0_AW_jyuoXtY7pU"
        if self.api_key:
            genai.configure(api_key=self.api_key)
    
    def _load_data(self):
        """Load university documents from JSON file and PDF directory"""
        try:
            # Load JSON data if it exists
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.documents = data['documents']
                    print(f"Loaded {len(self.documents)} documents from JSON")
            else:
                print(f"Data file not found at {self.data_path}, starting with empty documents")
                self.documents = []
            
            # Check for PDFs that aren't in documents yet
            self._process_pdfs()
            
        except Exception as e:
            print(f"Error loading data: {e}")
            self.documents = []
    
    def _process_pdfs(self):
        """Process all PDFs in the pdf directory and add them to documents if not already there"""
        # Get list of all PDFs in directory
        pdf_files = glob.glob(os.path.join(self.pdf_dir, "*.pdf"))
        
        # Track which PDFs are processed
        processed_files = {doc['source']: doc for doc in self.documents if doc['source'].startswith('pdf:')}
        
        # Process new PDFs
        for pdf_path in pdf_files:
            pdf_name = os.path.basename(pdf_path)
            pdf_id = f"pdf:{pdf_name}"
            
            # Skip if already processed
            if pdf_id in processed_files:
                continue
                
            try:
                # Extract text from PDF
                pdf_text = self._extract_text_from_pdf(pdf_path)
                
                # Create a document for each page or chunk to keep context reasonable
                chunks = self._chunk_text(pdf_text, chunk_size=1000, overlap=200)
                
                for i, chunk in enumerate(chunks):
                    doc_id = len(self.documents)
                    document = {
                        'id': doc_id,
                        'title': f"{pdf_name} - Chunk {i+1}",
                        'content': chunk,
                        'source': f"{pdf_id}:chunk{i+1}"
                    }
                    self.documents.append(document)
                
                print(f"Processed PDF: {pdf_name} into {len(chunks)} chunks")
            
            except Exception as e:
                print(f"Error processing PDF {pdf_name}: {e}")
        
        # Save updated documents
        if pdf_files:
            self._save_documents()
    
    def _extract_text_from_pdf(self, pdf_path):
        """Extract text content from a PDF file"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + " "
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    def _chunk_text(self, text, chunk_size=1000, overlap=200):
        """Split text into overlapping chunks for better context preservation"""
        words = text.split()
        chunks = []
        
        if len(words) <= chunk_size:
            return [text]
            
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i+chunk_size])
            chunks.append(chunk)
            i += (chunk_size - overlap)
            
        return chunks
            
    def _load_or_create_embeddings(self):
        """Load existing embeddings or create new ones"""
        try:
            if os.path.exists(self.embedding_path) and len(self.documents) > 0:
                # Load existing embeddings
                loaded = np.load(self.embedding_path)
                stored_embeddings = loaded['embeddings']
                
                # Check if number of embeddings matches number of documents
                if len(stored_embeddings) == len(self.documents):
                    self.embeddings = stored_embeddings
                    # Make sure vectorizer is fitted even when loading embeddings
                    texts = [doc['content'] for doc in self.documents]
                    self.vectorizer.fit(texts)
                    print(f"Loaded embeddings with shape {self.embeddings.shape}")
                else:
                    print("Number of embeddings doesn't match number of documents. Recreating...")
                    self._create_embeddings()
            else:
                # Create new embeddings
                self._create_embeddings()
        except Exception as e:
            print(f"Error with embeddings: {e}")
            self._create_embeddings()
    
    def _create_embeddings(self):
        """Create embeddings for all documents using TF-IDF"""
        if not self.documents:
            print("No documents to create embeddings for")
            self.embeddings = np.array([])
            return
        
        # Extract text content from documents
        texts = [doc['content'] for doc in self.documents]
        
        # Create TF-IDF embeddings
        self.vectorizer = TfidfVectorizer()
        self.vectorizer.fit(texts)
        self.embeddings = self.vectorizer.transform(texts).toarray()
        
        # Save embeddings
        np.savez(self.embedding_path, embeddings=self.embeddings)
        print(f"Created and saved {len(self.embeddings)} embeddings")
    
    def add_document(self, title, content, source='university_data'):
        """Add a new document to the collection"""
        doc_id = len(self.documents)
        document = {
            'id': doc_id,
            'title': title,
            'content': content,
            'source': source
        }
        
        self.documents.append(document)
        
        # Update embeddings with the new document
        self._create_embeddings()
        
        # Save updated documents
        self._save_documents()
        
        return doc_id
    
    def upload_pdf(self, pdf_file, filename=None):
        """Upload and process a new PDF file"""
        if not filename:
            # Generate unique filename if not provided
            file_hash = hashlib.md5(pdf_file.read()).hexdigest()[:8]
            pdf_file.seek(0)  # Reset file pointer after reading
            filename = f"{file_hash}_{pdf_file.filename}"
        
        # Save PDF to pdf directory
        pdf_path = os.path.join(self.pdf_dir, filename)
        pdf_file.save(pdf_path)
        
        # Process the new PDF
        self._process_pdfs()
        
        # Update embeddings
        self._create_embeddings()
        
        return filename
    
    def _save_documents(self):
        """Save documents to JSON file"""
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump({'documents': self.documents}, f, indent=2)
    
    def search(self, query, top_k=5):
        """Search for most relevant documents to the query"""
        if not self.documents or self.embeddings.size == 0:
            return []

        # Ensure vectorizer is fitted
        if not hasattr(self.vectorizer, 'vocabulary_') or self.vectorizer.vocabulary_ is None:
            texts = [doc['content'] for doc in self.documents]
            self.vectorizer.fit(texts)

        # Create query embedding
        query_embedding = self.vectorizer.transform([query]).toarray()
        
        # Calculate similarity
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        # Get top k results
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            # Only include documents with some relevance
            if similarities[idx] > 0.1:  # Threshold can be adjusted
                results.append({
                    'document': self.documents[idx],
                    'similarity': float(similarities[idx])
                })
        
        return results
    
    def generate_response(self, query, conversation_history=None, system_prompt="You are BotMIT, a helpful University Assistant."):
        """Generate a response using RAG with conversation context"""
        # Default to empty list if history not provided
        if conversation_history is None:
            conversation_history = []
        
        # Step 1: Construct context from conversation history
        conversation_context = ""
        if conversation_history:
            conversation_context = "Previous conversation:\n"
            for i, exchange in enumerate(conversation_history[-3:]):  # Use last 3 exchanges for context
                if exchange.get('sender') == 'user':
                    conversation_context += f"User: {exchange.get('text')}\n"
                else:
                    conversation_context += f"BotMIT: {exchange.get('text')}\n"
            conversation_context += "-" * 40 + "\n"
        
        # Step 2: Retrieve relevant documents for the current query
        relevant_docs = self.search(query)
        
        # Step 3: If no docs are found, also try searching with the last question context
        if not relevant_docs and len(conversation_history) >= 2:
            # Get the last user question
            last_user_messages = [msg for msg in conversation_history if msg.get('sender') == 'user']
            if last_user_messages:
                last_question = last_user_messages[-1].get('text', '')
                # Create combined query
                combined_query = f"{last_question} {query}"
                relevant_docs = self.search(combined_query)
        
        # Step 4: Format document context from retrieved documents
        doc_context = ""
        for i, doc in enumerate(relevant_docs):
            doc_context += f"\nDocument {i+1}: {doc['document']['title']}\n"
            doc_context += f"{doc['document']['content']}\n"
            doc_context += "-" * 40 + "\n"
        
        # Step 5: Create prompt with conversation history and document context
        if doc_context:
            full_prompt = f"{system_prompt}\n\n{conversation_context}\nRelevant University Information:\n{doc_context}\n\nCurrent User Question: {query}\n\nPlease answer based on the relevant university information provided above. Format your response nicely with markdown styling for headers, emphasis, and lists. If the information doesn't contain an answer to the question, please respond that you don't have that specific information but try to provide a helpful response based on the conversation context. You can add emojis to make the response more engaging, Also try to answer breif below 100 words."
        else:
            full_prompt = f"{system_prompt}\n\n{conversation_context}\nCurrent User Question: {query}\n\nI don't have specific university data to answer this question. Please respond based on the conversation context if relevant, or inform the user that you don't have the information they're looking for. You can add emojis to make the response more engaging, Also try to answer breif below 100 words."
        
        try:
            # Step 6: Generate response using Gemini
            model_name = "gemini-1.5-flash"
            
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(full_prompt)
            return response.text
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return f"I'm having trouble connecting to my knowledge base. Please try again later. Technical details: {str(e)}"