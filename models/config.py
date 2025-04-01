"""
Configuration for LLM models and endpoints
"""

import os
from enum import Enum
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env.local
env_path = Path(__file__).parent.parent / 'env' / '.env.local'
load_dotenv(env_path)

class ModelProvider(Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"

class ModelConfig:
    # Default configurations
    DEFAULT_PROVIDER = ModelProvider.OPENAI
    DEFAULT_MODEL = "gpt-4o"
    DEFAULT_TEMPERATURE = 0.3
    
    # Model mappings
    AVAILABLE_MODELS = {
        ModelProvider.OPENAI: [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4"
        ],
        ModelProvider.GOOGLE: [
            "gemini-pro",
            "gemini-pro-vision",
        ],
        ModelProvider.ANTHROPIC: [
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-2.1",
        ]
    }
    
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Load configuration from .env.local file"""
        # Ensure environment variables are loaded
        if not os.getenv("OPENAI_API_KEY"):
            # Try reloading if keys aren't found
            load_dotenv(env_path, override=True)
            
        config = {
            "provider": os.getenv("LLM_PROVIDER", ModelConfig.DEFAULT_PROVIDER.value),
            "model": os.getenv("LLM_MODEL", ModelConfig.DEFAULT_MODEL),
            "temperature": float(os.getenv("LLM_TEMPERATURE", ModelConfig.DEFAULT_TEMPERATURE)),
            "api_keys": {
                "openai": os.getenv("OPENAI_API_KEY", ""),
                "google": os.getenv("GOOGLE_API_KEY", ""),
                "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
            }
        }
        
        # Validate required API keys
        provider = config["provider"]
        api_key = config["api_keys"].get(provider)
        if not api_key:
            raise ValueError(f"API key for provider {provider} not found in .env.local")
            
        return config

    @staticmethod
    def get_available_models(provider: ModelProvider) -> list:
        """Get available models for a provider"""
        return ModelConfig.AVAILABLE_MODELS.get(provider, []) 