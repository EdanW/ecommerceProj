import json
import google.generativeai as genai
from typing import Dict, Any

# --- CONFIGURATION ---
# Get Key: https://aistudio.google.com/app/apikey
API_KEY = "YOUR_GOOGLE_API_KEY_HERE"
if API_KEY:
    genai.configure(api_key=API_KEY)


class AIEngine:
    def __init__(self):
        # Use a lightweight model for speed
        self.model = genai.GenerativeModel('gemini-pro')

    def analyze_craving(self, craving_text: str, current_glucose: int, week: int) -> Dict[str, Any]:
        """
        Logic:
        1. Context: User is pregnant (Week {week}), Gestational Diabetes.
        2. Input: Current Glucose + Craving.
        3. Output: JSON classification.
        """

        # Guard clause: If no API key, return simulation (prevents crashing during demo)
        if not API_KEY or "YOUR_GOOGLE" in API_KEY:
            return self._mock_response(craving_text, current_glucose)

        prompt = f"""
        You are 'Eat42', an empathetic AI nutritionist for a woman with Gestational Diabetes.

        USER CONTEXT:
        - Pregnancy Week: {week}
        - Current Glucose: {current_glucose} mg/dL (Target range: 70-140)
        - User Craving: "{craving_text}"

        YOUR TASK:
        Analyze the craving based on her CURRENT glucose level.

        RULES:
        1. SAFETY RATING:
           - If glucose > 140: Rate "Low Safety". Be firm but kind.
           - If glucose 100-140: Rate "Medium Safety". Suggest portion control.
           - If glucose < 100: Rate "High Safety". Encouraging.

        2. ALTERNATIVE:
           - If unsafe, suggest a low-carb alternative.
           - If safe, suggest a pairing (e.g. "Add walnuts for protein").

        3. FORMAT:
           Return ONLY raw JSON. No markdown.
           {{
             "safety": "High Safety" | "Medium Safety" | "Low Safety",
             "message": "Empathetic message (max 20 words).",
             "alternative": "Specific food action."
           }}
        """

        try:
            response = self.model.generate_content(prompt)
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"AI Error: {e}")
            return self._mock_response(craving_text, current_glucose)

    def _mock_response(self, craving, glucose):
        # Fallback logic if AI fails
        if glucose > 130:
            return {
                "safety": "Low Safety",
                "message": f"Your sugar is {glucose}, so let's be careful with {craving}.",
                "alternative": "Try cucumber slices with hummus instead!"
            }
        else:
            return {
                "safety": "High Safety",
                "message": "Your levels are great! Enjoy a small portion.",
                "alternative": "Pair it with some protein to keep steady."
            }


engine = AIEngine()