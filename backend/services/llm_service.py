import ollama
from typing import List, Dict, Optional
from config.settings import settings
from loguru import logger

class LLMService:
    def __init__(self):
        self.model = settings.OLLAMA_MODEL
        self.client = ollama.Client(host=settings.OLLAMA_BASE_URL)
    
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """Generate a response from the LLM"""
        try:
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            )
            
            return response['message']['content']
        
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "I apologize, but I'm having trouble generating a response. Please try again."
    
    def generate_question(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        context: Optional[str] = None
    ) -> Dict:
        """Generate a practice question"""
        
        context_info = f"\n\nBased on this context from study material:\n{context}" if context else ""
        
        prompt = f"""Generate a {difficulty} level practice question about {topic} in {subject}.{context_info}

Return ONLY a JSON object with this exact structure (no markdown, no extra text):
{{
  "question": "The question text here",
  "options": {{"A": "option 1", "B": "option 2", "C": "option 3", "D": "option 4"}},
  "correct": "A",
  "explanation": "Why this answer is correct"
}}"""

        system_prompt = "You are an expert tutor creating educational questions. Return only valid JSON, no markdown formatting."
        
        response = self.generate_response(prompt, system_prompt, temperature=0.8)
        
        # Clean up response (remove markdown code blocks if present)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse question JSON: {e}\nResponse: {response}")
            # Return a fallback question
            return {
                "question": f"What is an important concept in {topic}?",
                "options": {"A": "Concept A", "B": "Concept B", "C": "Concept C", "D": "Concept D"},
                "correct": "A",
                "explanation": "This is a fallback question due to a parsing error."
            }
    
    def explain_concept(self, subject: str, topic: str, difficulty: str) -> str:
        """Generate an explanation of a concept"""
        prompt = f"Explain {topic} in {subject} at a {difficulty} level. Use clear language and examples."
        system_prompt = "You are a patient, encouraging tutor who explains concepts clearly."
        
        return self.generate_response(prompt, system_prompt)
    
    def evaluate_answer(
        self,
        question: str,
        user_answer: str,
        correct_answer: str
    ) -> Dict[str, any]:
        """Evaluate if a user's answer is correct"""
        prompt = f"""Question: {question}
User's answer: {user_answer}
Correct answer: {correct_answer}

Is the user's answer correct? Consider partial credit for close answers.
Return ONLY a JSON object:
{{
  "is_correct": true or false,
  "feedback": "Brief encouraging feedback",
  "score": 0.0 to 1.0
}}"""

        system_prompt = "You are an encouraging tutor evaluating student answers. Be fair and supportive."
        response = self.generate_response(prompt, system_prompt, temperature=0.3)
        
        # Clean and parse
        response = response.strip().replace("```json", "").replace("```", "").strip()
        try:
            import json
            return json.loads(response)
        except:
            # Fallback
            return {
                "is_correct": user_answer.lower().strip() == correct_answer.lower().strip(),
                "feedback": "Let me check that answer.",
                "score": 1.0 if user_answer.lower().strip() == correct_answer.lower().strip() else 0.0
            }

# Singleton instance
llm_service = LLMService()