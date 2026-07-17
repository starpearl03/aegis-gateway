import json
import time
import logging
import re
from typing import Callable
import google.generativeai as genai
from flask import current_app

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for Google Gemini AI with lazy loading configuration"""

    def __init__(self):
        """Initialize LLMClient - config will be retrieved from Flask app context"""
        self._ai_config = None
        self._model = None
        self._max_retries = 3
        self._retry_delay = 2  # seconds

    @property
    def ai_config(self):
        """Lazy load AI config from Flask app context"""
        if self._ai_config is None:
            if not current_app:
                raise RuntimeError("LLMClient must be used within Flask application context")
            self._ai_config = current_app.config['INTEGRATIONS']['AI']
        return self._ai_config

    @property
    def model(self):
        """Lazy load Gemini model"""
        if self._model is None:
            logger.info("Initializing Gemini model...")
            gemini_config = self.ai_config.gemini
            genai.configure(api_key=gemini_config.api_key)
            self._model = genai.GenerativeModel(gemini_config.model)
            logger.info(f"Model {gemini_config.model} initialized successfully")
        return self._model

    def _retry_with_delay(self, func: Callable, *args, **kwargs):
        """Retries function with exponential backoff"""
        for attempt in range(self._max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self._max_retries - 1:
                    raise
                wait_time = self._retry_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

    def generate(self, prompt: str) -> dict:
        """Generate content from prompt and extract JSON response"""

        def _execute():
            response = self.model.generate_content(prompt)
            if not response or not response.text:
                raise ValueError("Empty response from model")
            return self._extract_json(response.text.strip())

        return self._retry_with_delay(_execute)

    # @staticmethod
    # def _extract_json(text: str) -> dict:
    #     """Extract JSON from response text using multiple strategies"""
    #     # Strategy 1: Direct parse
    #     try:
    #         return json.loads(text)
    #     except json.JSONDecodeError:
    #         pass
    #
    #     # Strategy 2: Extract from code blocks or braces
    #     patterns = [
    #         r"```(?:json)?\s*([\s\S]*?)\s*```",  # Markdown code blocks
    #         r"\{[\s\S]*\}"  # JSON objects
    #     ]
    #
    #     for pattern in patterns:
    #         for match in re.findall(pattern, text):
    #             try:
    #                 return json.loads(match)
    #             except json.JSONDecodeError:
    #                 continue
    #
    #     raise ValueError("No valid JSON found in the response")

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract JSON from response text using multiple strategies"""
        # Strategy 1: Direct parse
        try:
            result = json.loads(text)
            # Handle array responses - return first element
            return result[0] if isinstance(result, list) and result else result
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from code blocks or braces
        patterns = [
            r"```(?:json)?\s*([\s\S]*?)\s*```",  # Markdown code blocks
            r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",  # Balanced JSON objects
            r"\[[\s\S]*?\]"  # JSON arrays
        ]

        for pattern in patterns:
            for match in re.findall(pattern, text):
                try:
                    result = json.loads(match)
                    return result[0] if isinstance(result, list) and result else result
                except json.JSONDecodeError:
                    continue

        raise ValueError(f"No valid JSON found in response. First 200 chars: {text[:200]}...")