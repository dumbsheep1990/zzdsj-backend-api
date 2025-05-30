import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.knowledge import Document, DocumentChunk
from app.config import settings

def process_document(document_id: int, db: Session):
    """
    Process a document by chunking it and creating embeddings.
    """
    # Retrieve the document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise ValueError(f"Document with ID {document_id} not found")
    
    # Get document content based on type
    content = None
    if document.content:
        content = document.content
    elif document.file_path and os.path.exists(document.file_path):
        # Extract content from file based on mime type
        content = extract_content_from_file(document.file_path, document.mime_type)
    
    if not content:
        return
    
    # Chunk the document
    chunks = chunk_document(content, document.mime_type)
    
    # Create embeddings and store chunks
    for chunk_content, chunk_metadata in chunks:
        # Create document chunk record
        chunk = DocumentChunk(
            document_id=document.id,
            content=chunk_content,
            metadata=chunk_metadata
        )
        db.add(chunk)
    
    db.commit()
    
    # Create embeddings for all chunks
    create_embeddings_for_document(document_id, db)

def extract_content_from_file(file_path: str, mime_type: str) -> Optional[str]:
    """
    Extract text content from a file based on its MIME type.
    """
    # Simple text file handling
    if mime_type.startswith("text/"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    # PDF handling
    elif mime_type == "application/pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return None
    
    # DOCX handling
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        try:
            import docx
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            print(f"Error extracting text from DOCX: {e}")
            return None
    
    # Add more document type handling as needed
    
    return None

def chunk_document(content: str, mime_type: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[tuple]:
    """
    Split document content into overlapping chunks suitable for embedding.
    Returns list of (chunk_content, chunk_metadata) tuples.
    """
    # Simple text chunking by character count
    chunks = []
    
    # For plain text, split by paragraphs first, then by size
    if mime_type.startswith("text/"):
        paragraphs = content.split("\n\n")
        current_chunk = ""
        current_position = 0
        
        for para in paragraphs:
            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += para + "\n\n"
            else:
                # If current_chunk is not empty, add it to chunks
                if current_chunk:
                    chunks.append((
                        current_chunk.strip(),
                        {"position": current_position, "type": "paragraph"}
                    ))
                    current_position += 1
                
                # Start a new chunk with the current paragraph
                # If paragraph is larger than chunk_size, it needs its own special handling
                if len(para) > chunk_size:
                    # Split the large paragraph
                    for i in range(0, len(para), chunk_size - chunk_overlap):
                        sub_chunk = para[i:i + chunk_size]
                        chunks.append((
                            sub_chunk.strip(),
                            {"position": current_position, "type": "paragraph_segment"}
                        ))
                        current_position += 1
                else:
                    current_chunk = para + "\n\n"
        
        # Add the final chunk if not empty
        if current_chunk:
            chunks.append((
                current_chunk.strip(),
                {"position": current_position, "type": "paragraph"}
            ))
    else:
        # For other document types, use simple overlapping chunks
        for i in range(0, len(content), chunk_size - chunk_overlap):
            chunk_content = content[i:i + chunk_size]
            if chunk_content:
                chunks.append((
                    chunk_content.strip(),
                    {"position": i // (chunk_size - chunk_overlap), "type": "segment"}
                ))
    
    return chunks

def create_embeddings_for_document(document_id: int, db: Session):
    """
    Create embeddings for all chunks of a document and store them.
    """
    from app.frameworks.llamaindex.embeddings import get_embedding_model
    
    # Get document chunks
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    
    # Get embedding model
    embedding_model = get_embedding_model()
    
    # Process chunks in batches to avoid memory issues
    batch_size = 10
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [chunk.content for chunk in batch]
        
        # Generate embeddings
        try:
            embeddings = [embedding_model.get_text_embedding(text) for text in texts]
            
            # Store embeddings
            for j, chunk in enumerate(batch):
                # Store embedding ID or the embedding itself, depending on your vector DB
                # For FAISS, we'd store the ID that references the vector
                chunk.embedding_id = f"doc_{document_id}_chunk_{chunk.id}"
                
                # If using a vector database directly in the code, add vectors to it
                add_to_vector_store(
                    chunk.content,
                    embeddings[j],
                    {"chunk_id": chunk.id, "document_id": document_id}
                )
            
            db.commit()
        except Exception as e:
            print(f"Error generating embeddings: {e}")

def add_to_vector_store(text: str, embedding: List[float], metadata: Dict[str, Any]):
    """
    Add a text and its embedding to the vector store.
    """
    import os
    import faiss
    import numpy as np
    import pickle
    
    os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
    
    # Path for vector store
    index_path = os.path.join(settings.VECTOR_STORE_PATH, "faiss_index.idx")
    metadata_path = os.path.join(settings.VECTOR_STORE_PATH, "metadata.pkl")
    
    # Convert embedding to numpy array
    vector = np.array([embedding], dtype=np.float32)
    
    # Load or create the FAISS index
    if os.path.exists(index_path):
        # Load existing index
        index = faiss.read_index(index_path)
        
        # Load metadata
        with open(metadata_path, 'rb') as f:
            stored_metadata = pickle.load(f)
            stored_texts = pickle.load(f)
    else:
        # Create new index
        dimension = len(embedding)
        index = faiss.IndexFlatL2(dimension)
        stored_metadata = []
        stored_texts = []
    
    # Add the vector to the index
    index.add(vector)
    
    # Store metadata and text
    stored_metadata.append(metadata)
    stored_texts.append(text)
    
    # Save to disk
    faiss.write_index(index, index_path)
    with open(metadata_path, 'wb') as f:
        pickle.dump(stored_metadata, f)
        pickle.dump(stored_texts, f)
