import os
import asyncio
import httpx
import json
import logging
from typing import Optional
from transformers import pipeline

logger = logging.getLogger(__name__)

def build_prompt(text: str, task: str) -> str:
    if not isinstance(text, str) or not isinstance(task, str):
        raise ValueError("Input text and task must be strings")
    
    if task == "sentiment":
        return f"Analyze the sentiment of the following text and respond with 'positive', 'negative', or 'neutral':\n\n{text}"
    elif task == "emotion":
        return f"Identify the primary emotion expressed in the following text (e.g., joy, sadness, anger, fear, surprise, disgust):\n\n{text}"
    else:
        raise ValueError("Unknown task")

class SentimentAnalyzer:
    def __init__(self, model_type: str = 'local', model_name: Optional[str] = None):
        self.model_type = model_type
        self.device = -1  # CPU by default
        
        if self.model_type == 'local':
            # Sentiment Model
            s_model = model_name or os.getenv("HUGGINGFACE_MODEL", "distilbert-base-uncased-finetuned-sst-2-english")
            self.sentiment_pipe = pipeline("text-classification", model=s_model, device=self.device)
            
            # Emotion Model
            e_model = os.getenv("EMOTION_MODEL", "j-hartmann/emotion-english-distilroberta-base")
            self.emotion_pipe = pipeline("text-classification", model=e_model, device=self.device)
            
        else:
            self.api_key = os.getenv("EXTERNAL_LLM_API_KEY")
            self.api_url = "https://api.groq.com/openai/v1/chat/completions" # Default to Groq
            self.llm_model = os.getenv("EXTERNAL_LLM_MODEL", "llama-3.1-8b-instant")

    async def analyze_sentiment(self, text: str) -> dict:
        if not text:
            return {"sentiment_label": "neutral", "confidence_score": 0.0, "model_name": "none"}
        
        if not isinstance(text, str):
            raise ValueError("Input text must be a string")
        
        if self.model_type == 'local':
            result = self.sentiment_pipe(text[:512])[0]
            # Map labels to lowercase standard
            label = result['label'].lower()
            if label == 'positive' or label == 'negative':
                final_label = label
            else:
                final_label = 'neutral'
                
            return {
                'sentiment_label': final_label,
                'confidence_score': float(result['score']),
                'model_name': self.sentiment_pipe.model.config._name_or_path
            }
        else:
            return await self._analyze_external(text, "sentiment")

    async def analyze_emotion(self, text: str) -> dict:
        if not text: raise ValueError("Empty text")

        if not isinstance(text, str):
            raise ValueError("Input text must be a string")
        
        if len(text) < 10: return {"emotion": "neutral", "confidence_score": 1.0, "model_name": "rule-based"}

        if self.model_type == 'local':
            result = self.emotion_pipe(text[:512])[0]
            return {
                'emotion': result['label'].lower(),
                'confidence_score': float(result['score']),
                'model_name': self.emotion_pipe.model.config._name_or_path
            }
        else:
            return await self._analyze_external(text, "emotion")

    async def _analyze_external(self, text: str, task: str) -> dict:
        """Call external LLM API (Groq/OpenAI) for sentiment or emotion analysis."""
        if not self.api_key:
            raise ValueError("EXTERNAL_LLM_API_KEY not configured")
        
        if not isinstance(text, str):
            raise ValueError("Input text must be a string")
        
        prompt = build_prompt(text[:2000], task)  # Limit text length
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": "You are a precise text analysis assistant. Respond with only the requested classification label in lowercase."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 50
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                # Extract the response text
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
                logger.debug(f"External API response content: {content}")

                # Parse and normalize the response
                if task == "sentiment":
                    # Extract sentiment label
                    if "positive" in content:
                        label = "positive"
                    elif "negative" in content:
                        label = "negative"
                    else:
                        label = "neutral"
                    
                    return {
                        'sentiment_label': label,
                        'confidence_score': 0.85,  # External APIs don't always provide confidence
                        'model_name': self.llm_model
                    }
                
                elif task == "emotion":
                    # Extract emotion label
                    emotions = ["joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral"]
                    detected_emotion = "neutral"
                    
                    for emotion in emotions:
                        if emotion in content:
                            detected_emotion = emotion
                            break
                    
                    return {
                        'emotion': detected_emotion,
                        'confidence_score': 0.85,
                        'model_name': self.llm_model
                    }
                
                else:
                    raise ValueError(f"Unknown task: {task}")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling external API: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error calling external API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in external analysis: {e}")
            raise

    async def batch_analyze(self, texts: list[str]) -> list[dict]:
        if not texts: return []
        
        if not isinstance(texts, list):
            raise ValueError("Input must be a list of texts")
        
        if not all(isinstance(t, str) for t in texts):
            raise ValueError("All items in the input list must be strings")
        
        if self.model_type == 'local':
            # Local pipeline supports lists natively for batching
            results = self.sentiment_pipe(texts, batch_size=len(texts))
            return [{
                'sentiment_label': r['label'].lower(),
                'confidence_score': float(r['score']),
                'model_name': 'batch-local'
            } for r in results]
        else:
            return await asyncio.gather(*[self.analyze_sentiment(t) for t in texts])