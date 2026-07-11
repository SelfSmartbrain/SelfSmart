'''experience_encoder.py

Encodes raw experiences (episodes) into vector embeddings for semantic storage.
Uses a HuggingFace transformer model (e.g., sentence‑transformers) to generate embeddings.
''' 

from typing import List, Dict
from transformers import AutoTokenizer, AutoModel
import torch

class ExperienceEncoder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Return a list of embedding vectors for the given texts."""
        with torch.no_grad():
            inputs = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
            outputs = self.model(**inputs)
            # Mean pooling
            embeddings = outputs.last_hidden_state.mean(dim=1)
            return embeddings.cpu().numpy().tolist()

    def encode_episode(self, episode: Dict) -> List[float]:
        """Encode a single episode dictionary (expects a ``'description'`` field)."""
        text = episode.get("description", "")
        return self.encode([text])[0]
