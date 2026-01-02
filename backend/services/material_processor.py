import hashlib
from pathlib import Path
from typing import Optional, List, Dict
import PyPDF2
import pdfplumber
from docx import Document
from sentence_transformers import SentenceTransformer
import chromadb
from config.settings import settings
from loguru import logger

class MaterialProcessor:
    def __init__(self):
        # Initialize embedding model
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash for duplicate detection"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def extract_text_from_pdf(self, file_path: Path) -> tuple[str, int]:
        """Extract text from PDF and return (text, page_count)"""
        try:
            text_chunks = []
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        text_chunks.append({
                            'text': text,
                            'page': page_num
                        })
            
            full_text = "\n\n".join([chunk['text'] for chunk in text_chunks])
            return full_text, page_count, text_chunks
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return "", 0, []
    
    def extract_text_from_docx(self, file_path: Path) -> str:
        """Extract text from Word document"""
        try:
            doc = Document(file_path)
            text = "\n\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text, len(doc.paragraphs), [{'text': text, 'page': 1}]
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            return "", 0, []
    
    def extract_text_from_txt(self, file_path: Path) -> str:
        """Extract text from plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return text, 1, [{'text': text, 'page': 1}]
        except Exception as e:
            logger.error(f"TXT extraction error: {e}")
            return "", 0, []
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks for better context"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        return chunks
    
    def process_material(
        self,
        file_path: Path,
        material_id: int,
        subject: str
    ) -> Dict:
        """Process uploaded material and create embeddings"""
        try:
            # Extract text based on file type
            file_ext = file_path.suffix.lower()
            
            if file_ext == '.pdf':
                full_text, page_count, page_chunks = self.extract_text_from_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                full_text, page_count, page_chunks = self.extract_text_from_docx(file_path)
            elif file_ext == '.txt':
                full_text, page_count, page_chunks = self.extract_text_from_txt(file_path)
            else:
                return {"error": f"Unsupported file type: {file_ext}"}
            
            if not full_text:
                return {"error": "No text could be extracted"}
            
            # Chunk the text
            chunks = self.chunk_text(full_text)
            
            # Generate embeddings
            embeddings = self.embedder.encode(chunks)
            
            # Store in ChromaDB
            collection_name = f"material_{material_id}"
            collection = self.chroma_client.get_or_create_collection(collection_name)
            
            collection.add(
                documents=chunks,
                embeddings=embeddings.tolist(),
                metadatas=[{"chunk_id": i, "material_id": material_id} for i in range(len(chunks))],
                ids=[f"chunk_{i}" for i in range(len(chunks))]
            )
            
            return {
                "success": True,
                "page_count": page_count,
                "total_chunks": len(chunks),
                "text_length": len(full_text)
            }
        
        except Exception as e:
            logger.error(f"Material processing error: {e}")
            return {"error": str(e)}
    
    def search_material(
        self,
        material_id: int,
        query: str,
        top_k: int = 3
    ) -> List[Dict]:
        """Search for relevant chunks in material"""
        try:
            collection_name = f"material_{material_id}"
            collection = self.chroma_client.get_collection(collection_name)
            
            query_embedding = self.embedder.encode([query])
            
            results = collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k
            )
            
            return [
                {
                    "text": doc,
                    "metadata": meta
                }
                for doc, meta in zip(results['documents'][0], results['metadatas'][0])
            ]
        except Exception as e:
            logger.error(f"Material search error: {e}")
            return []

material_processor = MaterialProcessor()