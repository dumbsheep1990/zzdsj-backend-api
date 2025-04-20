"""
Text Processing Utilities: Functions for text processing, token counting,
chunking, and other text-related operations
"""

import re
from typing import List, Dict, Any, Tuple, Optional

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Count the number of tokens in a text string
    
    Args:
        text: Text to count tokens for
        model: Model to use for token counting (determines tokenization strategy)
        
    Returns:
        Number of tokens
    """
    if not text:
        return 0
    
    try:
        # Try to use tiktoken for accurate token counting if available
        import tiktoken
        
        # Select encoding based on model
        if model.startswith("gpt-4"):
            encoding = tiktoken.encoding_for_model("gpt-4")
        elif model.startswith("gpt-3.5"):
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        else:
            # Default to cl100k_base for newer models
            encoding = tiktoken.get_encoding("cl100k_base")
        
        # Count tokens
        return len(encoding.encode(text))
    
    except (ImportError, ModuleNotFoundError):
        # Fallback to approximate counting if tiktoken not available
        # This is a very rough approximation
        words = len(re.findall(r'\S+', text))
        # Roughly 4 chars per token on average for English text
        char_tokens = len(text) // 4
        # Take the max as a conservative estimate
        return max(words, char_tokens)

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks
    
    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters
        
    Returns:
        List of text chunks
    """
    if not text or chunk_size <= 0:
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        # Calculate end position accounting for text length
        end = min(start + chunk_size, text_len)
        
        # If not at the end of text and not at a good break point, find a good break
        if end < text_len and text[end] not in [' ', '\n', '.', ',', '!', '?', ';', ':', '-']:
            # Look for a good break point (whitespace or punctuation)
            good_break = max(
                text.rfind(' ', start, end),
                text.rfind('\n', start, end),
                text.rfind('.', start, end),
                text.rfind(',', start, end),
                text.rfind('!', start, end),
                text.rfind('?', start, end),
                text.rfind(';', start, end),
                text.rfind(':', start, end),
                text.rfind('-', start, end)
            )
            
            # If found a good break, use it
            if good_break != -1 and good_break > start:
                end = good_break + 1  # Include the break character
        
        # Extract chunk
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Calculate next start position with overlap
        start = end - chunk_overlap if end - chunk_overlap > start else end
        
        # Prevent infinite loop if we can't move forward
        if start >= end:
            break
    
    return chunks

def detect_language(text: str) -> str:
    """
    Detect the language of a text string (simple implementation)
    
    Args:
        text: Text to detect language for
        
    Returns:
        ISO 639-1 language code
    """
    try:
        # Try to use langdetect if available
        from langdetect import detect
        return detect(text)
    except (ImportError, ModuleNotFoundError):
        # Very simplistic fallback detection for common languages
        # This is only a placeholder - real detection would use a proper library
        text = text.lower()
        # Chinese characters
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return 'zh'
        # Japanese characters
        elif any('\u3040' <= char <= '\u30ff' for char in text):
            return 'ja'
        # Korean characters
        elif any('\uac00' <= char <= '\ud7a3' for char in text):
            return 'ko'
        # Cyrillic characters (Russian)
        elif any('\u0400' <= char <= '\u04ff' for char in text):
            return 'ru'
        # Arabic characters
        elif any('\u0600' <= char <= '\u06ff' for char in text):
            return 'ar'
        # Default to English
        else:
            return 'en'

def extract_metadata_from_text(text: str) -> Dict[str, Any]:
    """
    Extract potential metadata from text content
    
    Args:
        text: Text to extract metadata from
        
    Returns:
        Dictionary of metadata
    """
    metadata = {}
    
    # Try to detect language
    metadata['language'] = detect_language(text)
    
    # Count tokens
    metadata['token_count'] = count_tokens(text)
    
    # Character and word count
    metadata['char_count'] = len(text)
    metadata['word_count'] = len(re.findall(r'\S+', text))
    
    # Get summary statistics
    lines = text.split('\n')
    metadata['line_count'] = len(lines)
    
    # Extract potential title from first line
    if lines and len(lines[0]) < 100:
        metadata['potential_title'] = lines[0].strip()
    
    return metadata

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract potential keywords from text
    
    Args:
        text: Text to extract keywords from
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of keywords
    """
    try:
        # Try to use a keyword extraction library if available
        import yake
        
        # Simple keyword extraction
        kw_extractor = yake.KeywordExtractor(
            lan=detect_language(text),
            n=1,  # 1-gram
            dedupLim=0.9,
            dedupFunc='seqm',
            windowsSize=1,
            top=max_keywords
        )
        
        # Extract keywords
        keywords = kw_extractor.extract_keywords(text)
        return [kw[0] for kw in keywords]
    
    except (ImportError, ModuleNotFoundError):
        # Fallback to simple frequency-based extraction
        # This is a very simplistic approach
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                    'in', 'on', 'at', 'to', 'for', 'with', 'by', 'of', 'about', 'from'}
        
        # Count word frequencies
        word_counts = {}
        for word in words:
            if word not in stopwords and len(word) > 2:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Return top keywords
        return [word for word, count in sorted_words[:max_keywords]]
