"""
Rate Limiter: Provides rate limiting functionality for API endpoints
to prevent abuse and ensure fair resource allocation
"""

import time
from typing import Dict, Tuple, Any
import threading

class RateLimiter:
    """
    Rate limiter that uses a token bucket algorithm to limit requests
    Supports burst allowance and per-client rate limits
    """
    
    def __init__(self, requests_per_minute: int = 60, burst_limit: int = 10):
        """
        Initialize a rate limiter
        
        Args:
            requests_per_minute: Number of requests allowed per minute
            burst_limit: Maximum number of requests allowed in a burst
        """
        self.rate = requests_per_minute / 60.0  # Tokens per second
        self.burst_limit = burst_limit
        self.clients: Dict[str, Tuple[float, float]] = {}  # client_id -> (tokens, last_update)
        self.lock = threading.Lock()
    
    def allow_request(self, client_id: str) -> bool:
        """
        Check if a request from a client is allowed
        
        Args:
            client_id: Client identifier (e.g., IP address)
            
        Returns:
            True if the request is allowed, False otherwise
        """
        with self.lock:
            current_time = time.time()
            
            if client_id not in self.clients:
                # New client, initialize with full tokens
                self.clients[client_id] = (self.burst_limit, current_time)
                return True
            
            # Get current token count and last update time
            tokens, last_update = self.clients[client_id]
            
            # Calculate tokens to add based on time passed
            time_passed = current_time - last_update
            tokens_to_add = time_passed * self.rate
            
            # Update token count, but don't exceed burst limit
            new_tokens = min(self.burst_limit, tokens + tokens_to_add)
            
            if new_tokens < 1:
                # Not enough tokens
                self.clients[client_id] = (new_tokens, current_time)
                return False
            
            # Consume a token and allow the request
            self.clients[client_id] = (new_tokens - 1, current_time)
            return True
    
    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        """
        Get the rate limit status for a client
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dictionary with rate limit status
        """
        with self.lock:
            current_time = time.time()
            
            if client_id not in self.clients:
                return {
                    "remaining": self.burst_limit,
                    "limit": self.burst_limit,
                    "reset": current_time
                }
            
            tokens, last_update = self.clients[client_id]
            time_passed = current_time - last_update
            tokens_to_add = time_passed * self.rate
            new_tokens = min(self.burst_limit, tokens + tokens_to_add)
            
            # Calculate reset time (when client will have 1 token)
            reset_time = current_time
            if new_tokens < 1:
                reset_time = current_time + (1 - new_tokens) / self.rate
            
            return {
                "remaining": max(0, int(new_tokens)),
                "limit": self.burst_limit,
                "reset": reset_time
            }
    
    def clear_stale_clients(self, max_age_seconds: int = 3600):
        """
        Clear clients that haven't made requests in a while
        
        Args:
            max_age_seconds: Maximum age of client records to keep
        """
        with self.lock:
            current_time = time.time()
            stale_clients = [
                client_id for client_id, (_, last_update) in self.clients.items()
                if current_time - last_update > max_age_seconds
            ]
            
            for client_id in stale_clients:
                del self.clients[client_id]
