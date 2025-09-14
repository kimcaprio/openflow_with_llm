"""
Anthropic Claude LLM Provider

This module provides integration with Anthropic's Claude models.
"""

import os
import logging
from typing import Dict, List, Any, Optional
import anthropic
from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider implementation."""
    
    def __init__(
        self,
        model: str = "claude-3-sonnet-20240229",
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Anthropic provider.
        
        Args:
            model: Anthropic model name (e.g., "claude-3-sonnet-20240229")
            api_key: Anthropic API key (if None, will use ANTHROPIC_API_KEY env var)
            **kwargs: Additional Anthropic client arguments
        """
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter.")
        
        super().__init__(model, api_key, **kwargs)
        
        # Initialize Anthropic client
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate a response using Anthropic's API.
        
        Args:
            messages: List of messages in the conversation
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional Anthropic API parameters
            
        Returns:
            Generated response text
        """
        try:
            # Convert messages format for Anthropic
            system_message = None
            conversation_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    conversation_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": conversation_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            
            if system_message:
                api_params["system"] = system_message
            
            response = await self.client.messages.create(**api_params)
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def is_available(self) -> bool:
        """
        Check if Anthropic API is available.
        
        Returns:
            True if available, False otherwise
        """
        try:
            # Try a simple API call to test availability
            await self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"Anthropic API not available: {e}")
            return False
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported Anthropic models."""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0"
        ]
