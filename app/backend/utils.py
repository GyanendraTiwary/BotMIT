# backend/utils.py
import os
import json

def load_sample_data():
    """Load sample university data on startup if none exists"""
    data_dir = 'data'
    pdf_dir = os.path.join(data_dir, 'pdfs')
    embeddings_dir = 'embeddings_db'
    data_file = os.path.join(data_dir, 'university_data.json')
    
    # Create required directories
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(embeddings_dir, exist_ok=True)
    
    # Create sample data if it doesn't exist
    if not os.path.exists(data_file):
        sample_data = {
            "documents": [
                {
                    "id": 0,
                    "title": "About BotMIT University",
                    "content": "MITWPU University is a prestigious institution founded in 1984. We offer a wide range of academic programs across engineering, science, humanities, and business. Our mission is to provide world-class education and foster innovation.",
                    "source": "sample_data"
                },
                {
                    "id": 1,
                    "title": "Admission Requirements",
                    "content": "To apply to MITWPU, students need to submit academic transcripts, standardized test scores (SAT/ACT), a personal statement, and letters of recommendation. The application deadline is January 15 for fall admission.",
                    "source": "sample_data"
                }
            ]
        }
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2)
            
        print("Created sample university data")
    else:
        print("Sample data already exists")