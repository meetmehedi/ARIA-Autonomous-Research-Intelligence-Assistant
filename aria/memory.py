import sqlite3
import datetime
from pathlib import Path
from aria.config import DATABASE_PATH

# Prepopulated profile data based on Section 6.1 of the Requirements Document
DEFAULT_PROFILE = {
    "name": "Md. Mehedi Hasan",
    "role": "BSc CSE student, Researcher, DIU CPC President",
    "university": "Dhaka International University",
    "supervisor": "Prof. Dr. Md. Abdul Based",
    "research_interests": "Behavioral AI, Fraud Detection, Continual Learning, XAI",
    "writing_style": "Casual, direct, no fluff",
    "email": "meetmehedi1@gmail.com",
    "portfolio": "mdmehedihasan.us",
    "current_goals": "Freelance income -> Startup -> YC"
}

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and prepopulates the profile."""
    # Ensure database parent directory exists
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create profile table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    # Create conversations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        summary TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create tasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending', 'in_progress', 'completed')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create built_agents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS built_agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        path TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    
    # Prepopulate profile if empty
    cursor.execute("SELECT COUNT(*) FROM profile")
    if cursor.fetchone()[0] == 0:
        for k, v in DEFAULT_PROFILE.items():
            cursor.execute("INSERT INTO profile (key, value) VALUES (?, ?)", (k, v))
        conn.commit()
        
    conn.close()

def get_profile() -> dict:
    """Retrieves the full user profile dictionary."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM profile")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def update_profile_field(key: str, value: str):
    """Updates or inserts a profile field."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO profile (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))
    conn.commit()
    conn.close()

def get_profile_summary_prompt() -> str:
    """Formats profile as a markdown block for prompt injection."""
    profile = get_profile()
    lines = ["USER PROFILE:"]
    for k, v in profile.items():
        formatted_key = k.replace("_", " ").title()
        lines.append(f"- {formatted_key}: {v}")
    return "\n".join(lines)

def add_conversation_message(role: str, content: str, summary: str = None):
    """Saves a conversation message."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO conversations (role, content, summary)
    VALUES (?, ?, ?)
    """, (role, content, summary))
    conn.commit()
    conn.close()

def get_conversation_history(limit: int = 20) -> list:
    """Retrieves the latest messages in chronological order.

    Rows with empty/whitespace-only content are skipped so they don't pollute
    the prompt context sent to the LLM.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch descending to get the latest, then reverse for chronological order
    cursor.execute("""
    SELECT id, role, content, summary, timestamp
    FROM conversations
    WHERE content IS NOT NULL AND TRIM(content) != ''
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    messages = []
    for row in reversed(rows):
        messages.append({
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
            "summary": row["summary"],
            "timestamp": row["timestamp"]
        })
    return messages

def clear_conversation_history():
    """Clears all conversation history from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()

def add_task(description: str, status: str = "pending") -> int:
    """Adds a new task to the task list.

    Validates ``status`` against the schema's CHECK constraint before
    hitting SQLite, so the caller gets a clear ``ValueError`` instead of a
    silent IntegrityError.
    """
    allowed_statuses = ("pending", "in_progress", "completed")
    if status not in allowed_statuses:
        raise ValueError(
            f"Invalid task status {status!r}. Must be one of {allowed_statuses}."
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO tasks (description, status)
    VALUES (?, ?)
    """, (description, status))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_tasks(status: str = None) -> list:
    """Retrieves all or filtered tasks."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute("""
        SELECT id, description, status, created_at, updated_at 
        FROM tasks 
        WHERE status = ? 
        ORDER BY created_at DESC
        """, (status,))
    else:
        cursor.execute("""
        SELECT id, description, status, created_at, updated_at 
        FROM tasks 
        ORDER BY status DESC, created_at DESC
        """)
    rows = cursor.fetchall()
    conn.close()
    
    tasks = []
    for row in rows:
        tasks.append({
            "id": row["id"],
            "description": row["description"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        })
    return tasks

def update_task_status(task_id: int, status: str):
    """Updates a task status and sets the updated_at timestamp."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tasks 
    SET status = ?, updated_at = CURRENT_TIMESTAMP 
    WHERE id = ?
    """, (status, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id: int):
    """Deletes a task from the list."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def add_built_agent(name: str, description: str, path: str):
    """Adds a generated agent record to the database index."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO built_agents (name, description, path)
    VALUES (?, ?, ?)
    """, (name, description, path))
    conn.commit()
    conn.close()

def get_built_agents() -> list:
    """Retrieves all generated agents from the index."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, path, created_at FROM built_agents ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    agents = []
    for row in rows:
        agents.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "path": row["path"],
            "created_at": row["created_at"]
        })
    return agents
