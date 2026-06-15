import os
import sys
from aria.config import print_config_summary
import aria.memory as memory

def run_tests():
    print("--- ARIA Core System Integration Tests ---")
    
    # 1. Config Test
    print("\n1. Testing Configuration Loading...")
    print_config_summary()
    
    # 2. Database/Memory Test
    print("\n2. Testing Database/Memory initialization...")
    try:
        memory.init_db()
        print("✔ Database initialized successfully.")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
        
    print("\n3. Testing profile retrieval...")
    try:
        profile = memory.get_profile()
        assert profile is not None
        assert "name" in profile
        assert profile["name"] == "Md. Mehedi Hasan"
        print(f"✔ Profile retrieved successfully. Name: {profile['name']}")
    except Exception as e:
        print(f"❌ Profile retrieval failed: {e}")
        return False
        
    print("\n4. Testing Task CRUD operations...")
    try:
        # Clear existing test tasks if any (normally we don't, but let's test add)
        desc = "Verify ARIA Phase 1 Core"
        task_id = memory.add_task(desc, "pending")
        print(f"✔ Added task #{task_id}: '{desc}'")
        
        # Get tasks
        tasks = memory.get_tasks()
        found = False
        for t in tasks:
            if t["id"] == task_id:
                assert t["description"] == desc
                assert t["status"] == "pending"
                found = True
                break
        assert found, "Created task not found in database task list."
        print(f"✔ Task retrieved and verified in task list.")
        
        # Update status
        memory.update_task_status(task_id, "in_progress")
        tasks = memory.get_tasks()
        for t in tasks:
            if t["id"] == task_id:
                assert t["status"] == "in_progress"
                break
        print(f"✔ Task status updated to 'in_progress'.")
        
        # Delete task
        memory.delete_task(task_id)
        tasks = memory.get_tasks()
        found = False
        for t in tasks:
            if t["id"] == task_id:
                found = True
                break
        assert not found, "Task was not deleted."
        print(f"✔ Task deleted successfully.")
    except Exception as e:
        print(f"❌ Task operations failed: {e}")
        return False
        
    print("\n5. Testing LLM wrapper imports and fallback checks...")
    try:
        import aria.llm as llm
        print("✔ LLM module imported successfully.")
        system_prompt = llm.get_system_prompt()
        assert "Md. Mehedi Hasan" in system_prompt
        print("✔ Dynamically formatted system prompt contains user profile details.")
    except Exception as e:
        print(f"❌ LLM wrapper imports or prompt formatting failed: {e}")
        return False

    print("\n=========================================")
    print("🎉 ALL CORE ARIA INTEGRATION TESTS PASSED 🎉")
    print("=========================================")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
