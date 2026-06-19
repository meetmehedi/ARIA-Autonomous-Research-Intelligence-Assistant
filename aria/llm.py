import os
from aria.config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    GEMINI_API_KEY,
    OPENAI_MODEL,
    ANTHROPIC_MODEL,
    GEMINI_MODEL,
    OPENAI_BASE_URL,
)
from aria.memory import get_profile_summary_prompt

# Core system prompt for ARIA
BASE_SYSTEM_PROMPT = """You are ARIA — Md. Mehedi Hasan's personal AI agent.

ABOUT MEHEDI:
- BSc CSE student at Dhaka International University, graduating Nov 2027
- AI/ML researcher with 19 publications (6 accepted, rest under review)
- Research focus: Behavioral AI, Fraud Detection, Continual Learning, XAI
- President of DIU Computer Programming Club (2000+ members)
- NASA Space Apps Challenge 2025 Champion (Barisal Division)
- Currently building freelance income via AI automation services
- Long-term goal: Start a startup → apply to Y Combinator

YOUR PERSONALITY:
- Direct, no fluff, no filler words
- Always deliver the output first, explain after if needed
- Use casual tone — Mehedi is your person, not your client
- When asked to build something: BUILD IT, don't describe it

YOUR TWO MODES:
1. ASSISTANT MODE: Handle any task Mehedi delegates
2. AGENT BUILDER MODE: When asked to "build an agent", produce complete 
   working Python code following the standard project structure

NEVER:
- Give long explanations before delivering the output
- Ask more than one clarifying question
- Produce pseudocode when real code is requested
- Forget context from earlier in the conversation
"""

def get_system_prompt() -> str:
    """Combines base system prompt with dynamic profile context from memory."""
    profile_context = get_profile_summary_prompt()
    return f"{BASE_SYSTEM_PROMPT}\n\n{profile_context}\n\nRemember: Always address Mehedi directly without unnecessary greetings, speak casually, and keep responses direct and concise."

def query_openai(prompt: str, history: list) -> str:
    """Queries the OpenAI Chat Completion API."""
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API Key is missing. Please set it in your .env file.")
    
    from openai import OpenAI
    client_kwargs: dict = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE_URL:
        client_kwargs["base_url"] = OPENAI_BASE_URL
    client = OpenAI(**client_kwargs)
    
    messages = []
    messages.append({"role": "system", "content": get_system_prompt()})
    
    # Format history: convert user/assistant roles
    for msg in history:
        role = "assistant" if msg["role"] == "aria" else msg["role"]
        messages.append({"role": role, "content": msg["content"]})
        
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content

def query_anthropic(prompt: str, history: list) -> str:
    """Queries the Anthropic Messages API."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("Anthropic API Key is missing. Please set it in your .env file.")
        
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Format history for Anthropic (alternating roles, no system role in messages)
    formatted_messages = []
    for msg in history:
        role = "assistant" if msg["role"] == "aria" else msg["role"]
        # Anthropic only supports 'user' and 'assistant' roles in messages list
        if role in ("user", "assistant"):
            formatted_messages.append({"role": role, "content": msg["content"]})
            
    formatted_messages.append({"role": "user", "content": prompt})
    
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        system=get_system_prompt(),
        messages=formatted_messages,
        max_tokens=4000,
        temperature=0.7
    )
    # Anthropic returns content as blocks
    return response.content[0].text

def query_gemini(prompt: str, history: list) -> str:
    """Queries the Google Gemini API using the google-genai or google-generativeai SDK."""
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API Key is missing. Please set it in your .env file.")
        
    # Try the new google-genai SDK first
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Format history as contents
        contents = []
        for msg in history:
            role = "model" if msg["role"] == "aria" else "user"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        ))
        
        config = types.GenerateContentConfig(
            system_instruction=get_system_prompt(),
            temperature=0.7
        )
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config
        )
        return response.text
    except ImportError:
        # Fallback to the legacy google-generativeai SDK if installed
        import google.generativeai as genai
        
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Structure messages
        contents = []
        for msg in history:
            role = "model" if msg["role"] == "aria" else "user"
            contents.append({"role": role, "parts": [msg["content"]]})
        contents.append({"role": "user", "parts": [prompt]})
        
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=get_system_prompt()
        )
        response = model.generate_content(
            contents,
            generation_config={"temperature": 0.7}
        )
        return response.text

def generate_response(prompt: str, history: list = None) -> str:
    """Routes the generation request to the configured LLM provider.
    
    If the default provider fails or is not configured, it will try to fallback
    to other providers with configured API keys.
    """
    if history is None:
        history = []
        
    # Resolve the active provider based on environment keys
    provider = LLM_PROVIDER
    
    # Fail-safe logic: If selected provider key is missing, check alternative keys
    if provider == "openai" and not OPENAI_API_KEY:
        if ANTHROPIC_API_KEY:
            provider = "anthropic"
        elif GEMINI_API_KEY:
            provider = "gemini"
    elif provider == "anthropic" and not ANTHROPIC_API_KEY:
        if OPENAI_API_KEY:
            provider = "openai"
        elif GEMINI_API_KEY:
            provider = "gemini"
    elif provider == "gemini" and not GEMINI_API_KEY:
        if OPENAI_API_KEY:
            provider = "openai"
        elif ANTHROPIC_API_KEY:
            provider = "anthropic"

    if provider == "openai":
        return query_openai(prompt, history)
    elif provider == "anthropic":
        return query_anthropic(prompt, history)
    elif provider == "gemini":
        return query_gemini(prompt, history)
    else:
        raise ValueError(
            f"Invalid or unconfigured LLM provider: '{LLM_PROVIDER}'. "
            "Please configure LLM_PROVIDER and matching API key in .env file."
        )
