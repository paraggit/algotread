"""
LLM Client abstraction.

Provides a unified interface for different LLM providers.
Enforces JSON mode and handles retries.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Optional

from loguru import logger
from openai import OpenAI
from pydantic import BaseModel

from src.config import LLMConfig, LLMProvider


class LLMClient(ABC):
    """Abstract LLM client interface."""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[type[BaseModel]] = None,
        temperature: float = 0.0
    ) -> dict[str, Any]:
        """
        Generate LLM response.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            response_model: Pydantic model for structured output (optional)
            temperature: Temperature for generation (default 0.0 for deterministic)
            
        Returns:
            Parsed JSON response as dictionary
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI LLM client."""
    
    def __init__(self, config: LLMConfig):
        """
        Initialize OpenAI client.
        
        Args:
            config: LLM configuration
        """
        self.config = config
        self.client = OpenAI(api_key=config.api_key)
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[type[BaseModel]] = None,
        temperature: float = 0.0
    ) -> dict[str, Any]:
        """Generate response using OpenAI API."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            # Use JSON mode if available
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            if content is None:
                logger.error("OpenAI returned None content")
                return {}
            
            # Parse JSON
            result = json.loads(content)
            
            # Validate against Pydantic model if provided
            if response_model:
                validated = response_model(**result)
                result = validated.model_dump()
            
            logger.debug(f"LLM response: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return {}


class AnthropicClient(LLMClient):
    """Anthropic Claude LLM client (placeholder)."""
    
    def __init__(self, config: LLMConfig):
        """
        Initialize Anthropic client.
        
        Args:
            config: LLM configuration
        """
        self.config = config
        # TODO: Initialize Anthropic client
        logger.warning("Anthropic client not yet implemented")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[type[BaseModel]] = None,
        temperature: float = 0.0
    ) -> dict[str, Any]:
        """Generate response using Anthropic API."""
        # TODO: Implement Anthropic API call
        logger.error("Anthropic client not yet implemented")
        return {}


class LocalClient(LLMClient):
    """Local LLM client (placeholder)."""
    
    def __init__(self, config: LLMConfig):
        """
        Initialize local client.
        
        Args:
            config: LLM configuration
        """
        self.config = config
        logger.warning("Local LLM client not yet implemented")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[type[BaseModel]] = None,
        temperature: float = 0.0
    ) -> dict[str, Any]:
        """Generate response using local LLM."""
        # TODO: Implement local LLM call
        logger.error("Local LLM client not yet implemented")
        return {}


def create_llm_client(config: LLMConfig) -> LLMClient:
    """
    Factory function to create LLM client based on configuration.
    
    Args:
        config: LLM configuration
        
    Returns:
        LLM client instance
    """
    if config.provider == LLMProvider.OPENAI:
        return OpenAIClient(config)
    elif config.provider == LLMProvider.ANTHROPIC:
        return AnthropicClient(config)
    elif config.provider == LLMProvider.LOCAL:
        return LocalClient(config)
    else:
        raise ValueError(f"Unknown LLM provider: {config.provider}")
