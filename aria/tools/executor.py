import sys
import subprocess
import time

def execute_python_script(script_path: str, args: list = None, timeout: int = 20) -> dict:
    """Executes a Python script in a sandboxed subprocess and returns stdout, stderr, and exit code.
    
    Includes timeout safety to prevent hanging.
    """
    if args is None:
        args = []
        
    cmd = [sys.executable, script_path] + args
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        duration = time.time() - start_time
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "duration_seconds": round(duration, 3)
        }
    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        return {
            "success": False,
            "stdout": e.stdout if e.stdout else "",
            "stderr": f"Error: Execution timed out after {timeout} seconds.\n" + (e.stderr if e.stderr else ""),
            "exit_code": -1,
            "duration_seconds": round(duration, 3)
        }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution error: {e}",
            "exit_code": -2,
            "duration_seconds": round(duration, 3)
        }

if __name__ == "__main__":
    print("Testing Code Executor...")
    # Test execution by running a quick inline task or printing info
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("print('Hello from Code Executor')")
        temp_path = f.name
        
    res = execute_python_script(temp_path)
    print(f"Success: {res['success']}, Output: {res['stdout'].strip()}")
    try:
        import os
        os.unlink(temp_path)
    except:
        pass
