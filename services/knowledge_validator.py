import json
from pathlib import Path

class KnowledgeValidator:
    """Ensures agent only discusses Brigade Eternia"""
    
    FORBIDDEN_KEYWORDS = [
        "other property", "other properties", "different project", "alternative", "comparison",
        "similar properties", "nearby projects", "competitor", "other options",
        "different options", "other developments", "compare with"
    ]
    
    @staticmethod
    def load_knowledge():
        kb_path = Path("knowledge/brigade_eternia.json")
        with open(kb_path) as f:
            return json.load(f)
    
    @staticmethod
    def validate_response(response_text: str) -> bool:
        """Check if response stays on topic"""
        response_lower = response_text.lower()
        
        # Check for forbidden deviations
        for keyword in KnowledgeValidator.FORBIDDEN_KEYWORDS:
            if keyword in response_lower:
                return False
        
        # Must mention Brigade Eternia or related terms
        required_terms = ["brigade eternia", "eternia", "this project", "our project", "brigade group"]
        has_required = any(term in response_lower for term in required_terms)
        
        return has_required
