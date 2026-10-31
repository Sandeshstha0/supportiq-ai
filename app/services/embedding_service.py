
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=api_key)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768


def generate_embedding(text: str) -> list[float]:
    """Convert text into a 768-dimensional embedding."""

    text = text.strip()

    if not text:
        raise ValueError("Text cannot be empty.")

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config={
            "output_dimensionality": EMBEDDING_DIMENSION,
        },
    )

    if not response.embeddings:
        raise RuntimeError("Gemini returned no embedding.")

    values = response.embeddings[0].values

    if values is None or len(values) != EMBEDDING_DIMENSION:
        raise RuntimeError(
            "The generated embedding has an unexpected dimension."
        )

    return list(values)
