import ollama
from typing import List, Dict, Optional
from config.settings import settings
from loguru import logger
import json
import time
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    """Simple rate limiter to prevent abuse of LLM calls"""
    def __init__(self, max_calls_per_minute: int = 30):
        self.max_calls = max_calls_per_minute
        self.calls = defaultdict(list)

    def is_allowed(self, user_id: str = "default") -> bool:
        """Check if user is within rate limits"""
        now = datetime.now()
        # Clean old calls
        self.calls[user_id] = [
            call_time for call_time in self.calls[user_id]
            if now - call_time < timedelta(minutes=1)
        ]

        # Check if under limit
        if len(self.calls[user_id]) >= self.max_calls:
            return False

        # Record this call
        self.calls[user_id].append(now)
        return True

class LLMService:
    """
    Service for interacting with the local LLM via Ollama.
    This is the "brain" that generates questions, explanations, and feedback.

    Key Features:
    - Question generation with multiple choice options
    - Concept explanations at different difficulty levels
    - Answer evaluation with detailed feedback
    - Hint generation without revealing answers
    - Retry logic for robustness
    """

    def __init__(self):
        self.model = settings.OLLAMA_MODEL
        self.client = ollama.Client(host=settings.OLLAMA_BASE_URL)
        self.max_retries = 3
        self.rate_limiter = RateLimiter(max_calls_per_minute=30)
        logger.info(f"✓ LLM Service initialized with model: {self.model}")

        # Test connection
        try:
            self.client.list()
            logger.info("✓ Successfully connected to Ollama")
        except Exception as e:
            logger.error(f"✗ Failed to connect to Ollama: {e}")
            logger.error("Make sure Ollama is running with: ollama serve")

    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        user_id: str = "default"
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: What to ask the AI
            system_prompt: Instructions for how the AI should behave
            temperature: Creativity level (0=focused, 1=creative)
            max_tokens: Maximum length of response
            user_id: User identifier for rate limiting

        Returns:
            The AI's response as a string
        """
        # Check rate limits
        if not self.rate_limiter.is_allowed(user_id):
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return "Rate limit exceeded. Please wait a moment before trying again."

        # Validate input length to prevent abuse
        if len(prompt) > 5000:
            logger.warning(f"Prompt too long: {len(prompt)} characters")
            return "Prompt too long. Please keep questions under 5000 characters."

        for attempt in range(self.max_retries):
            try:
                messages = []

                # Add system prompt (instructions for the AI)
                if system_prompt:
                    messages.append({
                        "role": "system",
                        "content": system_prompt
                    })

                # Add user's question
                messages.append({
                    "role": "user",
                    "content": prompt
                })

                # Call Ollama
                logger.debug(f"Calling Ollama (attempt {attempt + 1}/{self.max_retries})...")

                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "top_k": 20,
                        "top_p": 0.9,
                        "repeat_penalty": 1.1,
                        "num_ctx": 1024  # Smaller context for faster processing
                    }
                )

                content = response['message']['content']
                logger.debug(f"✓ Response received ({len(content)} chars)")
                return content

            except Exception as e:
                logger.error(f"LLM generation error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1)  # Wait before retry
                    continue
                else:
                    return "I apologize, but I'm having trouble generating a response. Please check that Ollama is running and try again."

    def generate_question(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        context: Optional[str] = None,
        previous_questions: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate a practice question with multiple choice options.

        Args:
            subject: e.g., "Python Programming"
            topic: e.g., "Control Flow"
            difficulty: "beginner", "intermediate", or "advanced"
            context: Optional text from study material to base question on
            previous_questions: A list of recently asked questions to avoid repetition.

        Returns:
            Dictionary with:
            - question: The question text
            - options: Dict of {"A": "text", "B": "text", ...}
            - correct: The correct answer key (e.g., "A")
            - explanation: Why the answer is correct
        """

        # Build context info if studying from material
        context_info = ""
        if context:
            context_info = f"\n\nBase the question on this context from study material:\n{context}\n\nReference specific details from this context in the question."

        # Build history info to prevent repetition
        history_info = ""
        if previous_questions:
            history_str = "\n".join(f"- {q}" for q in previous_questions)
            history_info = f"\n\nTo ensure variety, do NOT repeat questions or ask questions that are too similar to these recently asked ones:\n{history_str}\n"

        # Define difficulty-appropriate instructions
        difficulty_instructions = {
            "beginner": "Focus on fundamental concepts and definitions. Use clear, simple language.",
            "intermediate": "Test understanding and application of concepts. Include scenario-based questions.",
            "advanced": "Test deep understanding, edge cases, and complex scenarios. Require critical thinking."
        }

        prompt = f"""You are a JSON generation bot. Your only output is a single, valid JSON object. Do not output any other text.
Generate a multiple choice question based on these parameters:
- Subject: {subject}
- Topic: {topic}
- Difficulty: {difficulty}
- Do not ask questions similar to these: {previous_questions or "None"}
{history_info}
{context_info}

If the question is about a piece of code (e.g., "What is the output of this function?"), you MUST include the code in the "code_snippet" field.

The JSON object must have the following structure. Every value MUST be a JSON string enclosed in double quotes.
{{
  "question": "A question about {topic}",
  "code_snippet": "Optional: A string containing a block of code if the question is about code. Use triple backticks for formatting. Can be null if not applicable.",
  "options": {{
    "A": "The first possible answer.",
    "B": "The second possible answer.",
    "C": "The third possible answer.",
    "D": "The fourth possible answer."
  }},
  "correct": "A string containing only the letter of the correct option (e.g. 'A', 'B', 'C', or 'D').",
  "explanation": "A string explaining why the correct answer is right. Any newlines in this string must be escaped as \\\\n."
}}
"""

        system_prompt = """Generate educational multiple choice questions in JSON format only. Be concise."""

        def _parse_response(raw: str):
            """Clean and parse LLM response; raises on failure."""
            text = raw.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            if not text.endswith('}'):
                if text.count('{') > text.count('}'):
                    text += '}'
            data = json.loads(text)
            required_keys = ["question", "options", "correct", "explanation"]
            if not all(key in data for key in required_keys):
                raise ValueError("Missing required keys in question data")
            if not isinstance(data.get("options"), dict):
                raise ValueError("Options must be a dictionary")
            opts = data["options"]
            if len(opts) < 3 or len(opts) > 4:
                raise ValueError(f"Must have 3 or 4 options, got {len(opts)}")
            correct_key = data.get("correct")
            if correct_key not in opts:
                raise ValueError(f"correct must be one of the option keys {list(opts.keys())}")
            data["correct"] = correct_key
            return data

        for attempt in range(2):  # Try up to 2 times (initial + 1 retry)
            response = self.generate_response(prompt, system_prompt, temperature=0.7, max_tokens=1200)

            # Skip retry if we got a rate-limit or error message instead of JSON
            if response.startswith("Rate limit") or response.startswith("Prompt too long"):
                return {"_generation_failed": True, "message": response}
            if response.startswith("I apologize") or "trouble generating" in response:
                return {"_generation_failed": True, "message": "The AI service couldn't generate a response. Check that Ollama is running and try again."}

            try:
                question_data = _parse_response(response)
                logger.info(f"✓ Generated question for {subject}/{topic} at {difficulty} level")
                return question_data
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Parse attempt {attempt + 1} failed: {e}\nResponse: {response[:200]}...")
                if attempt == 0:
                    continue  # Retry once
                logger.error(f"Failed to parse question JSON after retry: {e}")
                return {
                    "_generation_failed": True,
                    "message": "We couldn't generate a valid question (the AI returned invalid data). Click **Try again** to generate another question."
                }

    def explain_concept(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        context: Optional[str] = None
    ) -> str:
        """
        Generate a clear explanation of a concept.

        Args:
            subject: The subject area
            topic: The specific topic to explain
            difficulty: Beginner, intermediate, or advanced
            context: Optional material context to reference

        Returns:
            A clear, educational explanation
        """
        context_info = ""
        if context:
            context_info = f"\n\nReference this context: {context}"

        difficulty_styles = {
            "beginner": "Explain in very simple terms, as if to someone completely new to the subject. Use analogies and everyday examples.",
            "intermediate": "Explain with moderate detail, assuming some background knowledge. Include practical applications.",
            "advanced": "Provide a comprehensive explanation with technical depth, edge cases, and nuanced understanding."
        }

        prompt = f"""Explain {topic} in {subject} at a {difficulty} level.

{difficulty_styles.get(difficulty, "")}
{context_info}

Structure your explanation:
1. Brief definition or overview
2. Key concepts broken down
3. Practical example(s)
4. Common misconceptions or pitfalls (if applicable)

Be clear, encouraging, and educational. Use formatting for readability."""

        system_prompt = """You are a patient, expert tutor who explains concepts clearly.
Your explanations are well-structured, use examples, and leave students feeling confident they understand."""

        return self.generate_response(prompt, system_prompt, temperature=0.7, max_tokens=1000)

    def evaluate_answer(
        self,
        question: str,
        user_answer: str,
        correct_answer: str,
        explanation: str = ""
    ) -> Dict[str, any]:
        """
        Evaluate if a user's answer is correct and provide feedback.

        This is more sophisticated than simple string matching - it uses
        the LLM to understand if the answer demonstrates understanding,
        even if worded differently.

        Args:
            question: The question asked
            user_answer: What the user answered
            correct_answer: The correct answer
            explanation: The explanation of why it's correct

        Returns:
            Dictionary with:
            - is_correct: Boolean
            - feedback: Encouraging feedback message
            - score: 0.0 to 1.0 (allows for partial credit)
        """
        prompt = f"""Evaluate this student's answer:

Question: {question}
Student's answer: {user_answer}
Correct answer: {correct_answer}
Explanation: {explanation}

Evaluate if the student answered correctly. Consider:
- Exact matches are obviously correct
- Semantically equivalent answers should be marked correct
- Partially correct answers deserve partial credit
- Completely wrong answers get zero credit

Provide encouraging, constructive feedback regardless of correctness.

Return ONLY valid JSON:
{{
  "is_correct": true or false,
  "feedback": "Brief, encouraging feedback (2-3 sentences)",
  "score": 0.0 to 1.0
}}"""

        system_prompt = """You are an encouraging tutor evaluating student answers.
Be fair, supportive, and constructive. Help students learn from both correct and incorrect answers.
Return only valid JSON."""

        response = self.generate_response(prompt, system_prompt, temperature=0.3, max_tokens=150)

        # Clean and parse JSON
        response = response.strip().replace("```json", "").replace("```", "").strip()

        try:
            evaluation = json.loads(response)
            # Normalize is_correct (LLM may return string "true"/"false")
            is_correct = evaluation.get("is_correct", False)
            if isinstance(is_correct, str):
                is_correct = is_correct.lower() in ("true", "1", "yes")
            evaluation["is_correct"] = bool(is_correct)
            evaluation["score"] = float(evaluation.get("score", 1.0 if is_correct else 0.0))
            evaluation["feedback"] = str(evaluation.get("feedback", "")) or (
                "Great job!" if is_correct else f"Not quite. The correct answer is {correct_answer}. {explanation}"
            )
            logger.info(f"✓ Evaluated answer: {'correct' if evaluation['is_correct'] else 'incorrect'}")
            return evaluation

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse evaluation JSON: {e}")

            # Fallback: simple string comparison
            is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
            return {
                "is_correct": is_correct,
                "feedback": "Great job!" if is_correct else f"Not quite. The correct answer is {correct_answer}. {explanation}",
                "score": 1.0 if is_correct else 0.0
            }

    def provide_hint(
        self,
        question: str,
        options: Dict[str, str],
        correct_answer: str
    ) -> str:
        """
        Provide a helpful hint without giving away the answer directly.

        Args:
            question: The question
            options: Answer options {"A": "text", ...}
            correct_answer: The correct answer key

        Returns:
            A helpful hint string
        """
        prompt = f"""Provide a helpful hint for this question WITHOUT revealing the answer:

Question: {question}
Options: {json.dumps(options, indent=2)}

The correct answer is {correct_answer}: "{options[correct_answer]}"

Give a hint that:
- Guides the student's thinking in the right direction
- Doesn't directly state the answer
- Helps them reason through the problem
- Is encouraging and educational

Keep the hint to 2-3 sentences."""

        system_prompt = """You are a helpful tutor providing hints.
Guide students without giving direct answers. Help them develop problem-solving skills."""

        hint = self.generate_response(prompt, system_prompt, temperature=0.7, max_tokens=200)
        logger.info("✓ Generated hint")
        return hint

    def generate_topic_introduction(
        self,
        subject: str,
        topic: str,
        difficulty: str
    ) -> str:
        """
        Generate a friendly introduction to start a study session.

        Args:
            subject: The subject
            topic: The topic
            difficulty: The difficulty level

        Returns:
            A welcoming introduction message
        """
        prompt = f"""Create a brief, encouraging introduction for a student about to study:

Subject: {subject}
Topic: {topic}
Level: {difficulty}

The introduction should:
- Welcome the student
- Briefly explain what they'll learn
- Be encouraging and motivating
- Be 2-3 sentences

Keep it concise and friendly."""

        system_prompt = "You are an enthusiastic tutor starting a study session. Be warm, encouraging, and brief."

        intro = self.generate_response(prompt, system_prompt, temperature=0.8, max_tokens=200)
        return intro

# Create singleton instance
llm_service = LLMService()
