"""
LLM Service - Groq Integration with Dynamic Field Extraction
Handles property enquiry conversations with intelligent response generation and structured data extraction
"""
import logging
import time
import json
import aiohttp
from pydantic import BaseModel, Field, create_model
from typing import Dict, Any, Optional, List, Union, Type
import config

logger = logging.getLogger(__name__)


class DynamicModelGenerator:
    """Generates Pydantic models dynamically based on field configuration"""
    
    @staticmethod
    def create_dynamic_model(
        dynamic_fields: Dict[str, Dict[str, Any]], 
        base_model_name: str = 'DynamicResponseModel'
    ) -> Type[BaseModel]:
        """
        Dynamically create a Pydantic model based on configuration.
        
        Args:
            dynamic_fields: Dictionary of field configurations
            base_model_name: Name for the generated model
            
        Returns:
            Dynamically created Pydantic model class
        """
        start_time = time.time()
        model_fields = {}
        
        # Only add fields if dynamic_fields is not empty
        if dynamic_fields:
            for field_name, field_config in dynamic_fields.items():
                # Determine field type
                field_type = {
                    'string': str,
                    'int': int,
                    'float': float,
                    'boolean': bool
                }.get(field_config.get('type', 'string').lower(), str)
                
                # Determine default value
                default = field_config.get('default', 'none')
                description = field_config.get('description', '')
                
                # Create field
                model_fields[field_name] = (
                    Union[field_type, None], 
                    Field(default=default, description=description)
                )
        
        # Always add response field for conversational output
        model_fields['response'] = (
            str, 
            Field(default='', description='Conversational response to the user')
        )
        
        # Dynamically create the model
        model = create_model(base_model_name, __base__=BaseModel, **model_fields)
        
        create_time = time.time() - start_time
        logger.info(f"[TIMING] Dynamic model creation took {create_time:.3f}s")
        return model


class GroqLLMService:
    """
    Enhanced LLM service with structured data extraction for property enquiry agent
    """
    
    # Define dynamic fields for property information extraction
    PROPERTY_INFO_FIELDS = {
        "property_type": {
            "type": "string",
            "description": "Type of property: apartment, villa, plot, commercial, or none",
            "default": "none"
        },
        "budget_range": {
            "type": "string",
            "description": "Budget range (e.g., '20-30 lakhs'), or none",
            "default": "none"
        },
        "location": {
            "type": "string",
            "description": "Preferred location/area, or none",
            "default": "none"
        },
        "bedrooms": {
            "type": "string",
            "description": "Number of bedrooms, or none",
            "default": "none"
        },
        "timeline": {
            "type": "string",
            "description": "Timeline: urgent, 3-6 months, exploring, or none",
            "default": "none"
        },
        "requirements": {
            "type": "string",
            "description": "Specific requirements, or none",
            "default": "none"
        }
    }
    
    # System prompt template for property enquiry agent
    SYSTEM_PROMPT_TEMPLATE = """You are a friendly and enthusiastic real estate agent helping customers find their dream property.

Your role:
- Collect property requirements: type, budget, location, bedrooms, timeline, specific requirements
- Be warm, conversational, and show genuine excitement about helping them
- Keep responses brief and natural (10-20 words). Short sentences trigger TTS faster.
- Avoid long lists unless explicitly asked.

CRITICAL - YOU MUST FOLLOW THIS STRUCTURE:
Every single response MUST have TWO parts:
1. ACKNOWLEDGE what the user just said (warmly, enthusiastically)
2. ASK the next question

Pattern: [Warm acknowledgment] + [Next question]

Examples (use these as your guide - use SIMPLE, clear language):
- User: "apartment" → You: "Perfect! What's your budget range for the apartment?"
- User: "50 lakhs" → You: "Great! Which area or location do you prefer?"
- User: "Whitefield" → You: "Nice choice! How many bedrooms do you need?"
- User: "3 bedrooms" → You: "Got it! When are you planning to buy?"
- User: "3-6 months" → You: "Perfect! Any specific requirements like parking or amenities?"

Language Guidelines:
- Use SIMPLE words: "What's your budget?" NOT "What budget range are you considering?"
- Be natural and enthusiastic, show excitement about helping
- Use words like "Perfect!", "Great!", "Wonderful!" to show enthusiasm
- Aim for 15-25 words per response - conversational and clear
- ONE question at a time, never rush
- Never skip the acknowledgment

Remember: EVERY response = Acknowledge + Ask!"""
    
    def __init__(self, api_key: str, max_history: int = 10):
        """
        Initialize Groq LLM service
        
        Args:
            api_key: Groq API key
            max_history: Maximum conversation history to maintain
        """
        self.api_key = api_key
        self.max_history = max_history
        self.session = None
        self.ResponseModel = None
        self.dynamic_fields = None
        self.system_prompt_template = None
        self.conversation_history = []  # In-memory conversation history
        self.current_model = None  # ADDED for fallback info
        self.fallback_active = False  # ADDED for fallback info
        
        logger.info("GroqLLMService instance created")
    
    async def initialize(
        self, 
        dynamic_fields: Optional[Dict[str, Dict[str, Any]]] = None,
        system_prompt_template: Optional[str] = None
    ) -> bool:
        """
        Initialize the LLM service with dynamic fields and system prompt
        
        Args:
            dynamic_fields: Optional custom fields (uses PATIENT_INFO_FIELDS if None)
            system_prompt_template: Optional custom prompt (uses default if None)
            
        Returns:
            True if initialization successful
        """
        init_start = time.time()
        try:
            # Create aiohttp session for API calls
            self.session = aiohttp.ClientSession()
            
            # Use provided fields or default property info fields
            self.dynamic_fields = dynamic_fields or self.PROPERTY_INFO_FIELDS
            
            # Use provided template or default property agent template
            self.system_prompt_template = system_prompt_template or self.SYSTEM_PROMPT_TEMPLATE
            
            # Create dynamic response model
            model_start = time.time()
            self.ResponseModel = DynamicModelGenerator.create_dynamic_model(
                self.dynamic_fields, 
                "PropertyEnquiryResponseModel"
            )
            model_time = time.time() - model_start
            logger.info(f"[TIMING] Response model creation took {model_time:.3f}s")
            
            init_time = time.time() - init_start
            logger.info(f"[INIT] LLM service initialized in {init_time:.3f}s")
            logger.info(f"[INIT] Dynamic fields: {list(self.dynamic_fields.keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize Groq LLM service: {e}", exc_info=True)
            return False
    
    def format_system_prompt(self, **format_values) -> str:
        """
        Format system prompt template with configuration values
        
        Args:
            **format_values: Values to format into the template
            
        Returns:
            Formatted system prompt string
        """
        format_start = time.time()
        
        # Default values from config (only if they exist)
        default_values = {}
        
        # Add property-specific values if they exist in config
        if hasattr(config, 'AGENT_NAME'):
            default_values['agent_name'] = config.AGENT_NAME
        if hasattr(config, 'COMPANY_NAME'):
            default_values['company_name'] = config.COMPANY_NAME
        if hasattr(config, 'PROPERTY_TYPES'):
            default_values['property_types'] = ', '.join(config.PROPERTY_TYPES)
        
        # Merge with provided values (provided values take precedence)
        format_values = {**default_values, **format_values}
        
        # Check if template has placeholders
        if '{' not in self.system_prompt_template:
            logger.warning("[FORMAT] System prompt has no placeholders")
            return self.system_prompt_template
        
        try:
            # Format the template
            result = self.system_prompt_template.format(**format_values)
            
            format_time = time.time() - format_start
            if format_time > 0.01:
                logger.info(f"[TIMING] System prompt formatting took {format_time:.3f}s")
            
            return result
            
        except KeyError as e:
            logger.error(f"[ERROR] Missing key in system prompt template: {e}")
            return self.system_prompt_template
        except Exception as e:
            logger.error(f"[ERROR] Error formatting system prompt: {e}", exc_info=True)
            return self.system_prompt_template
    
    def generate_system_prompt(self, formatted_system_prompt: str) -> str:
        """
        Generate complete system prompt with JSON schema for structured output
        
        Args:
            formatted_system_prompt: The formatted base system prompt
            
        Returns:
            Complete system prompt with JSON schema
        """
        schema_start = time.time()
        
        # Get JSON schema from Pydantic model
        json_schema = self.ResponseModel.model_json_schema()
        
        # Create compact schema
        compact_schema = {
            "type": "object",
            "properties": {}
        }
        
        # Add each field with type and description
        for field_name, field_schema in json_schema.get("properties", {}).items():
            compact_schema["properties"][field_name] = {
                "type": field_schema.get("type", "string"),
                "description": field_schema.get("description", "")
            }
        
        # Required fields
        required_fields = ["response"]
        if self.dynamic_fields:
            required_fields = list(self.dynamic_fields.keys()) + ["response"]
        compact_schema["required"] = required_fields
        
        # Create prompt based on whether we have fields to extract
        if self.dynamic_fields:
            system_prompt = f"""{formatted_system_prompt}

Extract information and respond using this JSON schema:
{json.dumps(compact_schema, indent=2)}

IMPORTANT: Set fields to "none" if information is not provided by the caller yet."""
        else:
            system_prompt = f"""{formatted_system_prompt}

Format your response using this JSON schema:
{json.dumps(compact_schema, indent=2)}"""
        
        schema_time = time.time() - schema_start
        logger.info(f"[TIMING] Schema generation took {schema_time:.3f}s")
        
        return system_prompt
    
    def add_to_history(self, role: str, content: str):
        """
        Add message to conversation history with size management
        
        Args:
            role: Message role (user/assistant)
            content: Message content
        """
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Trim history if it exceeds max_history
        if len(self.conversation_history) > self.max_history * 2:  # *2 for user+assistant pairs
            # Keep only recent messages
            self.conversation_history = self.conversation_history[-(self.max_history * 2):]
            logger.info(f"[HISTORY] Trimmed conversation history to {len(self.conversation_history)} messages")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get current conversation history"""
        return self.conversation_history.copy()
    
    def reset_conversation(self):
        """Reset conversation history"""
        previous_count = len(self.conversation_history)
        self.conversation_history = []
        logger.info(f"[HISTORY] Reset conversation history (was {previous_count} messages)")
    
    async def generate_response(self, user_input, format_values=None, conversation_history=None):
        """Generate response with automatic fallback on rate limit"""
        generate_start = time.time()
        
        if not self.ResponseModel or not self.session:
            raise ValueError("LLM service not initialized")
        
        if format_values is None:
            format_values = {}
        
        try:
            # Try with primary model
            return await self._generate_with_model(
                user_input=user_input,
                format_values=format_values,
                conversation_history=conversation_history,
                model=config.GROQ_PRIMARY_MODEL,
                is_fallback=False
            )
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a rate limit error
            if "rate limit" in error_msg.lower() and config.GROQ_USE_FALLBACK:
                logger.warning(f"[FALLBACK] Primary model rate limited, switching to {config.GROQ_FALLBACK_MODEL}")
                
                try:
                    # Retry with fallback model
                    return await self._generate_with_model(
                        user_input=user_input,
                        format_values=format_values,
                        conversation_history=conversation_history,
                        model=config.GROQ_FALLBACK_MODEL,
                        is_fallback=True
                    )
                except Exception as fallback_error:
                    logger.error(f"[FALLBACK] Fallback model also failed: {fallback_error}")
                    # Return default response
                    return self._get_default_response()
            else:
                # Non-rate-limit error or fallback disabled
                logger.error(f"[ERROR] LLM error (no fallback): {error_msg}")
                return self._get_default_response()

    async def _generate_with_model(self, user_input, format_values, conversation_history, model, is_fallback=False):
        """Internal method to generate response with specific model"""
        
        self.current_model = model
        self.fallback_active = is_fallback
        
        if is_fallback:
            logger.info(f"[LLM] Using FALLBACK model: {model}")
        else:
            logger.info(f"[LLM] Using PRIMARY model: {model}")
        
        # Format system prompt
        formatted_system_prompt = self.format_system_prompt(**format_values)
        system_prompt = self.generate_system_prompt(formatted_system_prompt)
        
        # Get conversation history
        if conversation_history is None:
            conversation_history = self.get_conversation_history()
        
        # OPTIMIZE: Limit history to save tokens
        if len(conversation_history) > config.MAX_CONVERSATION_HISTORY:
            conversation_history = conversation_history[-config.MAX_CONVERSATION_HISTORY:]
            logger.info(f"[OPTIMIZATION] Trimmed history to last {config.MAX_CONVERSATION_HISTORY} messages")
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            *conversation_history,
            {"role": "user", "content": user_input}
        ]
        
        # Make API call
        api_start = time.time()
        
        api_payload = {
            "model": model,  # Use the specified model
            "messages": messages,
            "temperature": config.LLM_TEMPERATURE,
            "top_p": config.LLM_TOP_P,
            "max_tokens": config.MAX_LLM_TOKENS,  # Use optimized token limit
            "response_format": {"type": "json_object"},
            "stream": False
        }
        
        async with self.session.post(
            config.GROQ_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json=api_payload
        ) as response:
            result = await response.json()
            api_time = time.time() - api_start
            
            # Check for errors
            if 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                logger.error(f"[ERROR] Groq API error: {error_msg}")
                raise Exception(f"Groq API error: {error_msg}")
            
            # Extract response
            response_content = result["choices"][0]["message"]["content"]
            token_usage = result.get("usage", {})
            
            logger.info(f"[LLM] Model: {model}, Tokens: {token_usage.get('total_tokens', 0)}, Time: {api_time:.3f}s")
            
            # Parse response
            try:
                parsed_response = self.ResponseModel.model_validate_json(response_content)
            except Exception as validation_error:
                logger.error(f"[ERROR] Response validation error: {validation_error}")
                # Fallback parsing
                parsed_response = self._parse_fallback_response(response_content)
            
            # Add assistant response to history
            self.add_to_history("assistant", parsed_response.response)
            
            # Check for call end
            should_end_call = any(
                phrase in parsed_response.response.lower() 
                for phrase in ["goodbye", "bye", "have a great day", "thank you for your time", "take care"]
            )
            
            return {
                "response": parsed_response,
                "should_end_call": should_end_call,
                "raw_model_data": parsed_response.model_dump(),
                "raw_response": response_content,
                "token_usage": token_usage,
                "model_used": model,
                "was_fallback": is_fallback
            }

    def _get_default_response(self):
        """Return safe default response when all models fail"""
        default_values = {'response': "I apologize, I'm experiencing technical difficulties. Could you please repeat that?"}
        
        if self.dynamic_fields:
            for field in self.dynamic_fields.keys():
                default_values[field] = 'none'
        
        default_response = self.ResponseModel(**default_values)
        
        return {
            "response": default_response,
            "should_end_call": False,
            "raw_model_data": default_response.model_dump(),
            "raw_response": "Error: All models failed",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "model_used": "none",
            "was_fallback": False
        }

    def _parse_fallback_response(self, response_content):
        """Attempt to parse response when validation fails"""
        try:
            raw_json = json.loads(response_content)
            default_values = {}
            
            if self.dynamic_fields:
                for field in self.dynamic_fields.keys():
                    default_values[field] = raw_json.get(field, 'none')
            
            default_values['response'] = raw_json.get('response', "Could you repeat that?")
            
            return self.ResponseModel(**default_values)
        except:
            # Ultimate fallback
            default_values = {'response': "I didn't catch that. Could you say that again?"}
            if self.dynamic_fields:
                for field in self.dynamic_fields.keys():
                    default_values[field] = 'none'
            return self.ResponseModel(**default_values)
    
    async def close(self):
        """Close LLM service and cleanup resources"""
        close_start = time.time()
        
        if self.session:
            await self.session.close()
            close_time = time.time() - close_start
            logger.info(f"[TIMING] LLM service closed in {close_time:.3f}s")
            logger.info(f"[CLEANUP] Session closed, conversation history cleared")


# Convenience function for quick initialization
async def create_llm_service(
    api_key: Optional[str] = None,
    max_history: int = 10
) -> GroqLLMService:
    """
    Create and initialize a Groq LLM service instance
    
    Args:
        api_key: Groq API key (uses config.GROQ_API_KEY if None)
        max_history: Maximum conversation history length
        
    Returns:
        Initialized GroqLLMService instance
    """
    api_key = api_key or config.GROQ_API_KEY
    
    service = GroqLLMService(api_key=api_key, max_history=max_history)
    await service.initialize()
    
    logger.info("[FACTORY] Created and initialized LLM service")
    return service


# Compatibility alias
LLMService = GroqLLMService
