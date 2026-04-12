import asyncio
import os
import shutil
from pathlib import Path
from toolbelt.registry import get_registry

async def verify_tool(name, args):
    print(f"Testing {name:20} | Args: {str(args):40} -> ", end="")
    try:
        registry = get_registry()
        result = await registry.call(name, args)
        if hasattr(result, 'success') and result.success:
            print("✅ SUCCESS")
            return True
        elif isinstance(result, dict) and result.get("success"):
            print("✅ SUCCESS")
            return True
        else:
            error = getattr(result, 'error', str(result)) if hasattr(result, 'error') else result.get('error', 'Unknown error') if isinstance(result, dict) else "Unexpected result format"
            print(f"❌ FAILED: {error}")
            return False
    except Exception as e:
        print(f"💥 EXCEPTION: {str(e)}")
        return False

async def main():
    print("=== Stack 3.0 Exhaustive Tool Audit ===\n")

    # Setup temporary environment
    test_dir = Path("exhaustive_audit_env").absolute()
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "target.txt"
    test_file.write_text("Line 1: Hello World\nLine 2: Stack 2.9 Testing")

    reg = get_registry()

    # Create a Task
    task_res = await reg.call("TaskCreate", {"subject": "Audit", "description": "Testing", "activeForm": "Testing"})
    task_id = "test_task_1"
    if hasattr(task_res, 'data') and task_res.data: task_id = task_res.data.get('id', task_id)
    elif isinstance(task_res, dict) and task_res.get('data'): task_id = task_res['data'].get('id', task_id)

    # Create a Team
    team_res = await reg.call("team_create", {"team_name": "AuditTeam", "agents": ["AgentA", "AgentB"]})
    team_id = "audit_team_1"
    if hasattr(team_res, 'data') and team_res.data: team_id = team_res.data.get('id', team_id)
    elif isinstance(team_res, dict) and team_res.get('data'): team_id = team_res['data'].get('id', team_id)

    # Fixed test cases based on co_varnames and failure logs
    test_cases = {
        # File Ops - Most of these failed because they expected positional args or different keys
        # But the BaseTool.call passes the whole dict as 'input_data' to execute()
        # If execute(self, input_data, ...), the registry call is fine.
        # If execute(self, path, ...), we must provide exactly those.
        # Based on co_varnames:
        "file_read": {"path": str(test_file)},
        "file_exists": {"path": str(test_file)},
        "file_write": {"path": str(test_dir / "write.txt"), "content": "verified"},
        "file_delete": {"path": str(test_dir / "write.txt")},
        "file_edit": {"path": str(test_file), "operation": "replace", "pattern": "Hello", "replacement": "Hi"},
        "file_edit_insert": {"path": str(test_file), "content": "New Line", "line": 1},
        "file_edit_delete": {"path": str(test_file), "line": 1},
        "file_edit_replace": {"path": str(test_file), "pattern": "Stack", "replacement": "StackAI"},
        "glob": {"path": str(test_dir), "pattern": "*.txt"},
        "glob_list": {"path": str(test_dir)},
        "grep": {"path": str(test_dir), "pattern": "Hello"},
        "grep_count": {"path": str(test_dir), "pattern": "Hello"},

        # Tasks & Planning
        "TaskCreate": {"subject": "Task", "description": "Desc", "activeForm": "Creating"},
        "TaskList": {},
        "TaskUpdate": {"id": task_id, "status": "completed"},
        "TaskGet": {"id": task_id},
        "TaskDelete": {"id": task_id},
        "EnterPlanMode": {},
        "ExitPlanMode": {},

        # Agent & Team
        "agent_list": {},
        "agent_status": {"agent_id": "system"},
        "agent_spawn": {"task": "Verify tools", "runtime": "subagent"},
        "team_create": {"team_name": "TestTeam", "agents": ["A1"]},
        "team_list": {},
        "team_status": {"team_id": team_id},
        "team_assign": {"team_id": team_id, "task": "Audit"},
        "team_leave": {"team_id": team_id, "agent_name": "AgentA"},
        "team_disband": {"team_id": team_id},
        "team_delete": {"team_id": team_id, "force": True},

        # Web & MCP
        "WebSearch": {"query": "Stack 2.9 AI"},
        "web_fetch": {"url": "https://google.com"},
        "web_fetch_meta": {"url": "https://google.com"},
        "mcp_list_servers": {},
        "mcp_call": {"server_name": "default", "tool_name": "echo", "args": {}},
        "mcp_add_server": {"server_name": "test", "command": "echo hello"},
        "read_mcp_resource": {"server_name": "default", "resource_uri": "test"},

        # Messaging & Communication
        "message_send": {"recipient": "admin", "content": "Test message"},
        "message_list": {},
        "message_channel": {"action": "create", "name": "audit-channel"},
        "message_template": {"action": "get", "name": "welcome"},
        "ask_question": {"question": "Is the system working?"},
        "get_pending_questions": {},
        "answer_question": {"question_id": "1", "answer": "Yes"},

        # Scheduling & Skills
        "CronCreate": {"cron": "0 * * * *", "prompt": "cleanup"},
        "CronList": {},
        "CronDelete": {"id": "1"},
        "skill_list": {"search": "code"},
        "skill_execute": {"skill_name": "echo"},
        "skill_info": {"skill_name": "echo"},
        "skill_chain": {"skills": [{"skill_name": "echo"}]},
        "skill_search": {"query": "code"},

        # Utils & Misc
        "sleep": {"seconds": 0.1},
        "wait_for": {"seconds": 0.1},
        "synthetic_output": {"output_type": "text", "content": "Verified"},
        "structure_data": {"data": "test data"},
        "brief": {"task": "Audit", "context": "Verify the tools are working"},
        "brief_summary": {"content": "The tools are working perfectly"},
        "Config": {"key": "test_mode", "value": "on", "operation": "set"},
        "TodoWrite": {"item": "Fix badges", "operation": "add", "task": "UI"},
        "tool_search": {"query": "file"},
        "tool_list_all": {"category": None},
        "tool_info": {"name": "file_read"},
        "tool_capabilities": {},
        "enter_worktree": {"worktree_path": str(test_dir)},
        "exit_worktree": {"worktree_id": "1"},
        "list_worktrees": {},

        # Remote Trigger
        "remote_add": {"name": "test_remote", "url": "http://localhost"},
        "remote_list": {},
        "remote_trigger": {"remote": "test_remote", "action": "trigger"},
        "remote_remove": {"name": "test_remote"},
    }

    all_tools = reg.list()
    success_count = 0

    print(f"{'Tool Name':20} | {'Result':15}")
    print("-" * 40)

    for name in all_tools:
        args = test_cases.get(name, {})
        if await verify_tool(name, args):
            success_count += 1

    # 3. Verify Hierarchical Router categorization
    print("\n--- Verifying Hierarchical Router Categorization ---")
    try:
        from cognitive_core.router import HierarchicalRouter
        router = HierarchicalRouter()
        for tool in all_tools:
            category = router.get_category(tool)
            if category:
                print(f"Tool {tool} is correctly categorized as {category}")
            else:
                print(f"❌ Tool {tool} is missing a category in the router")
    except ImportError:
        print("⚠️ HierarchicalRouter not found, skipping categorization check.")

    shutil.rmtree(test_dir)
    print(f"\n--- FINAL AUDIT RESULT: {success_count}/{len(all_tools)} tools passed ({(success_count/len(all_tools))*100:.1f}%) ---")

if __name__ == "__main__":
    asyncio.run(main())
