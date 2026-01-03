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
    """
    Processes uploaded study materials (PDFs, Word docs, text files).
    Extracts text, creates searchable chunks, and enables smart question generation.
    """

    def __init__(self):
        # Initialize text embedding model (converts text to numbers for searching)
        logger.info("Loading embedding model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        # Initialize vector database (stores searchable text)
        self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        logger.info("Material processor initialized")

    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate unique fingerprint for a file.
        Used to detect if the same file is uploaded twice.

        Args:
            file_path: Path to the file

        Returns:
            Hash string (unique identifier)
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def extract_text_from_pdf(self, file_path: Path) -> tuple[str, int, List[Dict]]:
        """
        Extract text from a PDF file.

        Args:
            file_path: Path to PDF

        Returns:
            Tuple of (full_text, page_count, page_chunks)
        """
        try:
            text_chunks = []

            # Use pdfplumber for better text extraction
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        text_chunks.append({
                            'text': text,
                            'page': page_num
                        })
                        logger.debug(f"Extracted page {page_num}/{page_count}")

            # Combine all text
            full_text = "\n\n".join([chunk['text'] for chunk in text_chunks])

            logger.info(f"Extracted {len(full_text)} characters from {page_count} pages")
            return full_text, page_count, text_chunks

        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            # Don't expose internal error details to users
            return "", 0, []

    def extract_text_from_docx(self, file_path: Path) -> tuple[str, int, List[Dict]]:
        """
        Extract text from a Word document.

        Args:
            file_path: Path to DOCX file

        Returns:
            Tuple of (full_text, paragraph_count, chunks)
        """
        try:
            doc = Document(file_path)

            # Extract all paragraphs
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

            full_text = "\n\n".join(paragraphs)

            chunks = [{'text': full_text, 'page': 1}]

            logger.info(f"Extracted {len(full_text)} characters from Word document")
            return full_text, len(paragraphs), chunks

        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            # Don't expose internal error details to users
            return "", 0, []

    def extract_text_from_txt(self, file_path: Path) -> tuple[str, int, List[Dict]]:
        """
        Extract text from a plain text file.

        Args:
            file_path: Path to TXT file

        Returns:
            Tuple of (full_text, line_count, chunks)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            chunks = [{'text': text, 'page': 1}]

            logger.info(f"Extracted {len(text)} characters from text file")
            return text, 1, chunks

        except Exception as e:
            logger.error(f"TXT extraction error: {e}")
            # Don't expose internal error details to users
            return "", 0, []

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for better context preservation.

        Why overlapping? So concepts that span chunk boundaries aren't lost.

        Args:
            text: Full text to chunk
            chunk_size: Words per chunk
            overlap: Words to overlap between chunks

        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks

    def process_material(
        self,
        file_path: Path,
        material_id: int,
        subject: str
    ) -> Dict:
        """
        Main processing function: extract text, chunk it, create embeddings.

        This enables RAG (Retrieval Augmented Generation):
        - Extract text from document
        - Split into chunks
        - Convert to embeddings (numbers that represent meaning)
        - Store in vector database for fast semantic search

        Args:
            file_path: Path to uploaded file
            material_id: Database ID for this material
            subject: Which subject it belongs to

        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Processing material {material_id}: {file_path}")

            # Check file size (max 100MB)
            file_size = file_path.stat().st_size
            if file_size > 100 * 1024 * 1024:
                return {"error": "File too large. Maximum size is 100MB."}

            # Validate file exists and is readable
            if not file_path.exists() or not file_path.is_file():
                return {"error": "File not found or not accessible."}

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

            if not full_text or len(full_text.strip()) < 10:
                return {"error": "No meaningful text could be extracted from file"}

            # Limit text size to prevent memory issues
            if len(full_text) > 10 * 1024 * 1024:  # 10MB of text
                logger.warning(f"Text too large ({len(full_text)} chars), truncating")
                full_text = full_text[:10 * 1024 * 1024]

            # Chunk the text into searchable pieces
            chunks = self.chunk_text(full_text)

            if not chunks:
                return {"error": "Failed to create text chunks"}

            # Generate embeddings (convert text to numbers for searching)
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            embeddings = self.embedder.encode(chunks, show_progress_bar=False)

            # Store in ChromaDB (vector database)
            collection_name = f"material_{material_id}"
            collection = self.chroma_client.get_or_create_collection(collection_name)

            # Add chunks to database
            collection.add(
                documents=chunks,
                embeddings=embeddings.tolist(),
                metadatas=[
                    {
                        "chunk_id": i,
                        "material_id": material_id,
                        "subject": subject
                    }
                    for i in range(len(chunks))
                ],
                ids=[f"chunk_{i}" for i in range(len(chunks))]
            )

            logger.info(f"✓ Material {material_id} processed successfully")

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
        """
        Search for relevant chunks in a material using semantic search.

        This is the "magic" of RAG:
        - Convert query to embedding
        - Find chunks with similar embeddings
        - Return most relevant text

        Args:
            material_id: Which material to search
            query: What to search for
            top_k: How many results to return

        Returns:
            List of relevant text chunks with metadata
        """
        try:
            collection_name = f"material_{material_id}"
            collection = self.chroma_client.get_collection(collection_name)

            # Convert query to embedding
            query_embedding = self.embedder.encode([query])

            # Search vector database
            results = collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k
            )

            # Format results
            relevant_chunks = [
                {
                    "text": doc,
                    "metadata": meta
                }
                for doc, meta in zip(results['documents'][0], results['metadatas'][0])
            ]

            logger.info(f"Found {len(relevant_chunks)} relevant chunks for query: {query[:50]}...")
            return relevant_chunks

        except Exception as e:
            logger.error(f"Material search error: {e}")
            return []

    def delete_material(self, material_id: int):
        """
        Delete a material and its vector database collection.

        Args:
            material_id: Which material to delete
        """
        try:
            collection_name = f"material_{material_id}"
            self.chroma_client.delete_collection(collection_name)
            logger.info(f"✓ Deleted material {material_id}")
        except Exception as e:
            logger.error(f"Error deleting material: {e}")

# Create singleton instance
material_processor = MaterialProcessor()
