import asyncio
import re
from pathlib import Path
import streamlit as st
import aria.memory as memory
from aria.rl_agent import execute_rl_agent
from aria.config import LLM_PROVIDER

# Page Configuration
st.set_page_config(
    page_title="ARIA - Autonomous Research & Intelligence Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Premium Dark Mode Glassmorphism Theme)
st.markdown("""
<style>
    /* Dark Theme Base */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
    }
    
    /* Card Glassmorphism Styling */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    
    .profile-title {
        color: #38bdf8;
        font-weight: 700;
        font-size: 1.25rem;
        border-bottom: 2px solid rgba(56, 189, 248, 0.2);
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    
    .profile-field {
        margin-bottom: 0.75rem;
        font-size: 0.9rem;
    }
    
    .profile-label {
        font-weight: 600;
        color: #94a3b8;
    }
    
    .profile-value {
        color: #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# Helper to load state
if "chat_history" not in st.session_state:
    memory.init_db()
    st.session_state.chat_history = memory.get_conversation_history(30)

def refresh_state():
    st.session_state.chat_history = memory.get_conversation_history(30)

# Sidebar UI
with st.sidebar:
    st.image("https://img.icons8.com/isometric/512/artificial-intelligence.png", width=80)
    st.title("ARIA Engine")
    st.caption(f"LLM Provider: **{LLM_PROVIDER.upper()}**")
    
    # 1. User Profile Cards
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="profile-title">👤 User Profile</div>', unsafe_allow_html=True)
    
    profile = memory.get_profile()
    for field_name in ["name", "role", "university", "supervisor", "research_interests", "writing_style", "current_goals"]:
        val = profile.get(field_name, "Not configured")
        label = field_name.replace("_", " ").title()
        st.markdown(f'<div class="profile-field"><span class="profile-label">{label}:</span> <span class="profile-value">{val}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 2. Task Manager Card
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="profile-title">📝 Task Manager</div>', unsafe_allow_html=True)
    
    # Add Task Form
    with st.form("add_task_form", clear_on_submit=True):
        new_task_desc = st.text_input("New Task Description", placeholder="Draft outreach emails...")
        submitted = st.form_submit_button("Add Task")
        if submitted and new_task_desc:
            memory.add_task(new_task_desc)
            st.success("Task added!")
            st.rerun()
            
    # List active tasks
    tasks = memory.get_tasks()
    active_tasks = [t for t in tasks if t["status"] in ("pending", "in_progress")]
    
    if active_tasks:
        st.write("**Active Tasks Checklist:**")
        for t in active_tasks:
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                # Show status emoji
                emoji = "⏳" if t["status"] == "pending" else "⚡"
                st.markdown(f"{emoji} {t['description']}")
            with col2:
                if st.button("✓", key=f"complete_{t['id']}", help="Mark as Completed"):
                    memory.update_task_status(t["id"], "completed")
                    st.rerun()
    else:
        st.info("No active tasks pending.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 3. Built Agents Directory Card
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="profile-title">📁 Generated Agents</div>', unsafe_allow_html=True)
    agents = memory.get_built_agents()
    if agents:
        for a in agents:
            st.write(f"🤖 **{a['name']}**")
            st.caption(a["description"])
            
            # Extract zip package file path for download button
            zip_file = Path(a["path"]).parent / f"{a['name']}.zip"
            if zip_file.exists():
                with open(zip_file, "rb") as f:
                    st.download_button(
                        label=f"Download {a['name']}.zip",
                        data=f,
                        file_name=zip_file.name,
                        mime="application/zip",
                        key=f"dl_{a['id']}"
                    )
            st.markdown("---")
    else:
        st.info("No agents built yet.")
    st.markdown('</div>', unsafe_allow_html=True)

# Main Chat Area
st.title("ARIA Chat Dashboard")
st.write("Welcome back, Mehedi. How can I help you today?")

# Clear History button
if st.button("🧹 Clear Chat History"):
    memory.clear_conversation_history()
    st.session_state.chat_history = []
    st.success("Chat history cleared!")
    st.rerun()

# Display Messages from SQLite state
for msg in st.session_state.chat_history:
    role = "user" if msg["role"] == "user" else "assistant"
    avatar = "👤" if role == "user" else "🤖"
    
    with st.chat_message(role, avatar=avatar):
        # Render markdown content
        st.markdown(msg["content"])
        
        # Check if the assistant's message has a file link to provide a direct download button
        if role == "assistant":
            match = re.search(r"file://([^\s\)]+\.zip)", msg["content"])
            if match:
                zip_path = Path(match.group(1))
                if zip_path.exists():
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label=f"📥 Download {zip_path.name}",
                            data=f,
                            file_name=zip_path.name,
                            mime="application/zip",
                            key=f"chat_dl_{msg['id']}"
                        )

# Chat Input
if user_input := st.chat_input("Message ARIA..."):
    # Display user message immediately
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)
        
    with st.chat_message("assistant", avatar="🤖"):
        # Display thinking status
        with st.spinner("ARIA is typing..."):
            try:
                # Classify request
                is_builder_request = any(phrase in user_input.lower() for phrase in [
                    "build me an agent", "build an agent", "create an agent", 
                    "make me an agent", "generate an agent", "build a chatbot"
                ])
                
                # Fetch recent messages context
                history = memory.get_conversation_history(20)
                
                if is_builder_request:
                    response = asyncio.run(execute_rl_agent(user_input, history=[]))
                    st.markdown(response)
                else:
                    response = asyncio.run(execute_rl_agent(user_input, history))
                    st.markdown(response)
                    
                # Save to memory DB
                memory.add_conversation_message("user", user_input)
                memory.add_conversation_message("aria", response)
                
                # Refresh local state
                refresh_state()
                
            except Exception as e:
                st.error(f"Error executing request: {e}")
