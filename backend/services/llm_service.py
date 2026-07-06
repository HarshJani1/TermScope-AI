"""
LLM Service
Handles all interactions with the Groq LLM API for document analysis and Q&A.
"""

import logging
import hashlib
from groq import Groq
from utils.redis_client import redis_client, is_redis_available
from config import get_config

logger = logging.getLogger(__name__)

config = get_config()
cache_ttl = getattr(config, "CACHE_DEFAULT_TIMEOUT", 86400)

# System prompt for Terms & Conditions analysis
SYSTEM_PROMPT = """You are **TermScope AI**, an expert legal document analyst specializing in Terms and Conditions, Privacy Policies, End User License Agreements (EULAs), and similar legal documents.

## Your Core Responsibilities

### When Analyzing a New Document:
1. **Executive Summary**: Provide a clear, concise overview of the document's purpose and scope.
2. **Key Terms Breakdown**: List and explain the most important terms, organized by category:
   - **Data & Privacy**: How user data is collected, stored, shared, and used
   - **User Rights & Obligations**: What users can and cannot do
   - **Service Provider Rights**: What the company reserves the right to do
   - **Financial Terms**: Fees, billing, refunds, and payment terms
   - **Termination & Cancellation**: How either party can end the agreement
   - **Liability & Warranties**: Limitations of liability and disclaimers
3. **Risk Assessment**: Highlight clauses that are:
   - 🔴 **High Risk**: Potentially harmful, one-sided, or concerning for users
   - 🟡 **Medium Risk**: Vague, ambiguous, or could be interpreted unfavorably
   - 🟢 **Low Risk**: Standard, fair, and transparent
4. **Plain Language Explanations**: Translate legal jargon into simple, everyday language.
5. **Overall Rating**: Rate the document's user-friendliness on a scale of 1-10 with justification.
6. **Actionable Recommendations**: What should users pay special attention to before agreeing?
7. If the document is other than Terms and documentation you must only reply with "Provided documentation is not Terms and Condition please provide correct documenation."

### When Answering Follow-Up Questions:
- Base your answers STRICTLY on the provided document content and previous conversation context.
- Cite specific sections, clauses, or paragraphs when possible.
- If information is NOT available in the document, clearly state: "This information is not covered in the provided document."
- NEVER fabricate, assume, or add information not present in the document.
- Maintain conversation continuity — reference previous analysis when relevant.

## Formatting Guidelines
- Use Markdown formatting for clear, structured responses.
- Use bullet points, numbered lists, and headers for organization.
- Use bold and italics for emphasis on critical points.
- Use emoji indicators (🔴🟡🟢) for risk levels.
- Keep explanations accessible to non-legal professionals.

## Important Note:
- No need to provide follow up questions.

"""


class LLMService:
    """Service for Groq LLM interactions."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 4096, temperature: float = 0.3):
        """
        Initialize the LLM service.

        Args:
            api_key: Groq API key.
            model: Model identifier (e.g., openai/gpt-oss-120b).
            max_tokens: Maximum tokens in LLM response.
            temperature: Sampling temperature.
        """
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set. Please configure it in .env")

        self.client = Groq(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def analyze_document(self, cleaned_text: str) -> str:
        """
        Send cleaned document text to the LLM for initial analysis.

        Args:
            cleaned_text: The cleaned and normalized document text.

        Returns:
            LLM analysis response as a string.

        Raises:
            RuntimeError: If the LLM call fails.
        """
        cache_key = None
        if is_redis_available():
            try:
                text_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
                cache_key = f"cache:analysis:{self.model}:{text_hash}"
                cached_res = redis_client.get(cache_key)
                if cached_res:
                    logger.info("Cache hit for document analysis.")
                    return cached_res
            except Exception as e:
                logger.error(f"Redis cache lookup failed in analyze_document: {e}")

        try:
            logger.info(f"Sending document ({len(cleaned_text)} chars) to LLM for analysis")

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Please analyze the following Terms and Conditions document "
                        "thoroughly and provide your complete assessment:\n\n"
                        f"---\n\n{cleaned_text}\n\n---"
                    ),
                },
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            result = response.choices[0].message.content
            logger.info(f"LLM analysis complete. Response: {len(result)} chars")

            # Store in Redis cache
            if cache_key and is_redis_available():
                try:
                    redis_client.setex(cache_key, cache_ttl, result)
                    logger.info("Saved document analysis to cache.")
                except Exception as e:
                    logger.error(f"Failed to write analysis to Redis cache: {e}")

            return result

        except Exception as e:
            logger.error(f"LLM analysis failed: {str(e)}")
            raise RuntimeError(f"LLM analysis failed: {str(e)}")

    def ask_followup(
        self,
        question: str,
        document_text: str,
        relevant_chunks: list[str],
        conversation_history: list[dict],
    ) -> str:
        """
        Answer a follow-up question using document context and conversation history.

        Args:
            question: The user's follow-up question.
            document_text: The full cleaned document text (truncated if very long).
            relevant_chunks: Relevant text chunks retrieved from FAISS.
            conversation_history: List of prior conversation messages.

        Returns:
            LLM response as a string.

        Raises:
            RuntimeError: If the LLM call fails.
        """
        cache_key = None
        if is_redis_available():
            try:
                # Build unique payload to represent state of the conversation
                history_str = "".join([f"{m['role']}:{m['content']}" for m in conversation_history])
                chunks_str = "".join(relevant_chunks) if relevant_chunks else ""
                state_str = f"{self.model}:{document_text[:8000]}:{question}:{history_str}:{chunks_str}"
                state_hash = hashlib.sha256(state_str.encode("utf-8")).hexdigest()
                cache_key = f"cache:chat:{state_hash}"
                
                cached_res = redis_client.get(cache_key)
                if cached_res:
                    logger.info("Cache hit for follow-up question.")
                    return cached_res
            except Exception as e:
                logger.error(f"Redis cache lookup failed in ask_followup: {e}")

        try:
            logger.info(f"Processing follow-up question: {question[:100]}...")

            # Build context from relevant chunks
            chunks_context = ""
            if relevant_chunks:
                chunks_context = (
                    "\n\n## Most Relevant Document Sections:\n"
                    + "\n\n---\n\n".join(relevant_chunks)
                )

            # Build messages
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Here is the document being discussed:\n\n{document_text[:8000]}",
                },
                {
                    "role": "assistant",
                    "content": "I have the document context. I'm ready to answer your questions about it.",
                },
            ]

            # Add conversation history (limit to last 20 messages to avoid token overflow)
            for msg in conversation_history[-20:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

            # Add the current question with relevant chunks
            user_message = question
            if chunks_context:
                user_message += f"\n\n{chunks_context}"

            messages.append({"role": "user", "content": user_message})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            result = response.choices[0].message.content
            logger.info(f"Follow-up response complete. Response: {len(result)} chars")

            # Store in Redis cache
            if cache_key and is_redis_available():
                try:
                    redis_client.setex(cache_key, cache_ttl, result)
                    logger.info("Saved follow-up response to cache.")
                except Exception as e:
                    logger.error(f"Failed to write follow-up response to Redis cache: {e}")

            return result

        except Exception as e:
            logger.error(f"Follow-up question failed: {str(e)}")
            raise RuntimeError(f"Failed to process follow-up question: {str(e)}")
