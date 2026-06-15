import re
import json
import sys
import aria.memory as memory
import aria.llm as llm

# Import tools
from aria.tools.search import search_web
from aria.tools.scraper import scrape_url
from aria.tools.pdf import read_pdf
from aria.tools.telegram import send_telegram_message as send_telegram
from aria.tools.gmail import send_email

# Define tool registry
TOOL_REGISTRY = {
    "search_web": search_web,
    "scrape_url": scrape_url,
    "read_pdf": read_pdf,
    "send_telegram": send_telegram,
    "send_email": send_email,
    "add_task": memory.add_task,
    "update_task_status": memory.update_task_status,
    "get_tasks": memory.get_tasks,
    "get_profile": memory.get_profile
}

ASSISTANT_SYSTEM_PROMPT = """You are ARIA's Action Executor. You can use tools to answer Mehedi's request.
To call a tool, use this exact syntax on a single line:
Call: <tool_name>(<arguments_in_python_format>)

For example:
Call: search_web(query="continual learning in neural networks")
Call: scrape_url(url="https://arxiv.org/abs/2401.12345")
Call: send_email(subject="Meeting Schedule", body="Hi Based, let's meet tomorrow.", to_email="based@diu.edu")
Call: add_task(description="Draft review responses for MEWC-LLM")

Rules:
1. ONLY write ONE "Call: ..." line per response. Do not chain multiple calls in a single turn.
2. If you output a "Call: ...", do NOT output any final answer yet. Just write your reasoning/thought on the preceding line.
3. Once you have enough information (or if no tool is needed), deliver your final answer to Mehedi directly.
4. Keep the final response short, direct, and conversational (Mehedi's voice: casual, direct, researcher-credible).

Available Tools:
- search_web(query: str) -> searches the web for queries.
- scrape_url(url: str) -> reads and cleans content from standard websites.
- read_pdf(file_path: str) -> extracts text from local PDF files.
- send_telegram(message: str) -> sends a notification to Mehedi's Telegram.
- send_email(subject: str, body: str, to_email: str = None) -> sends SMTP email or prints a draft.
- add_task(description: str) -> adds task to SQLite TODO list. Returns task ID.
- update_task_status(task_id: int, status: str) -> updates task status ('pending', 'in_progress', 'completed').
- get_tasks() -> gets all tasks in the database.
- get_profile() -> gets Mehedi's current profile settings.
"""

def parse_and_run_tool(llm_output: str) -> tuple:
    """Parses 'Call: tool_name(args)' from output and runs the matching tool.
    
    Returns (tool_called_bool, tool_output_str).
    """
    match = re.search(r"Call:\s*(\w+)\((.*)\)", llm_output)
    if not match:
        return False, ""
        
    tool_name = match.group(1)
    args_str = match.group(2)
    
    if tool_name not in TOOL_REGISTRY:
        return True, f"Error: Tool '{tool_name}' is not in the registry."
        
    tool_func = TOOL_REGISTRY[tool_name]
    
    # Safely evaluate arguments in the context of python datatypes
    try:
        # Wrap in dictionary/tuple evaluation
        # E.g., if args_str is `query="hello"`, we can evaluate it by wrapping it
        # We can construct a local namespace and execute
        local_vars = {}
        eval_str = f"dict({args_str})"
        safe_globals = {
            "__builtins__": None,
            "dict": dict,
            "list": list,
            "tuple": tuple,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool
        }
        args_dict = eval(eval_str, safe_globals, local_vars)
        
        # Invoke tool function
        result = tool_func(**args_dict)
        
        # Format tool result as string
        if isinstance(result, (dict, list)):
            result_str = json.dumps(result, indent=2)
        else:
            result_str = str(result)
            
        return True, result_str
        
    except Exception as e:
        return True, f"Error parsing or executing tool command arguments '{args_str}': {e}"

def execute_assistant_task(user_prompt: str, history: list = None, max_steps: int = 5) -> str:
    """Runs a ReAct loop executing assistant tasks with tools."""
    if history is None:
        history = []
        
    # Copy history so we don't modify the database logs during execution steps
    temp_history = list(history)
    
    # We append a system reminder about tools to the active context
    step_instruction = f"{ASSISTANT_SYSTEM_PROMPT}\n\nUser Query: {user_prompt}"
    
    for step in range(max_steps):
        # Format prompt including history and the tool context
        # We query the LLM
        response = llm.generate_response(step_instruction, temp_history)
        
        # Check if LLM called a tool
        tool_called, tool_result = parse_and_run_tool(response)
        
        if tool_called:
            # Print execution step to stderr for visibility in CLI
            print(f"  [ARIA executing: {response.strip()}]", file=sys.stderr)
            
            # Append tool interaction to temp history as context for next LLM turn
            temp_history.append({"role": "aria", "content": response})
            temp_history.append({"role": "user", "content": f"Tool Output:\n{tool_result}"})
            
            # Update the step instruction to focus on continuing
            step_instruction = "Continue planning or output your final response based on the tool output."
        else:
            # No tool called: this is the final answer!
            return response
            
    # Timeout response if we hit max_steps
    return "Error: I ran into a loop while planning your request. Here is what I generated so far:\n" + response
