"""LLM-based answer generator — uses Google Gemini 2.5 Flash (free tier)."""

import os
import time
import logging
from typing import List

logger = logging.getLogger(__name__)

DEFAULT_PROMPT_TEMPLATE = (
    "Answer the question based on the provided context.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer:"
)


class Generator:
    """Generates answers using Google Gemini via LangChain with exponential backoff."""

    def __init__(self, model_name: str = "gemini-2.5-flash-lite", temperature: float = 0.3):
        from langchain_google_genai import ChatGoogleGenerativeAI
        self.model_name = model_name
        self.temperature = temperature
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
        )

    def generate(self, query: str, contexts: List[str], prompt_template: str = DEFAULT_PROMPT_TEMPLATE) -> str:
        """Generate an answer given a query and list of context strings.

        Retries with exponential backoff on rate-limit (429) errors.
        Max 5 retries, starting at 2 seconds, doubling each retry.
        """
        context_str = "\n\n".join(f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts))
        prompt = prompt_template.format(context=context_str, question=query)

        delay = 2.0
        for attempt in range(6):
            try:
                response = self.llm.invoke(prompt)
                if hasattr(response, "content"):
                    return response.content.strip()
                return str(response).strip()
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "rate" in err_str:
                    if attempt < 5:
                        logger.warning("Rate limit hit, retrying in %.1fs (attempt %d/5)", delay, attempt + 1)
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.error("Rate limit exceeded after 5 retries.")
                        raise
                else:
                    raise
        return ""
