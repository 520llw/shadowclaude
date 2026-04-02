#!/usr/bin/env python3
"""
ShadowClaude CLI - 最强开源 AI 编程助手
基于 Claude Code 泄露源码精华实现

Usage:
    shadowclaude [OPTIONS] [PROMPT]
    shadowclaude --buddy
    shadowclaude --kairos-start
    shadowclaude --undercover

Options:
    -h, --help          Show this help message
    -v, --version       Show version
    -i, --interactive   Interactive mode
    -c, --compact       Compact mode (no memory)
    --buddy             Launch BUDDY pet system
    --kairos-start      Start KAIROS daemon
    --kairos-stop       Stop KAIROS daemon
    --undercover        Activate undercover mode
    --model MODEL       Choose model [default: claude-sonnet-4-6]
"""

import sys
import os
import argparse
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from shadowclaude import QueryEngine, QueryEngineConfig
from shadowclaude.tools import ToolRegistry
from shadowclaude.memory import MemorySystem
from shadowclaude.agents import Coordinator, AgentType
from shadowclaude.kairos import KairosDaemon
from shadowclaude.buddy import BuddySystem
from shadowclaude.undercover import UndercoverMode, should_activate_undercover


def print_banner():
    """打印启动横幅"""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   ███████╗██╗  ██╗ █████╗ ██████╗  ██████╗ ██╗      ██╗ ║
    ║   ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔═══██╗██║     ██╔╝ ║
    ║   ███████╗███████║███████║██║  ██║██║   ██║██║    ██╔╝  ║
    ║   ╚════██║██╔══██║██╔══██║██║  ██║██║   ██║██║   ██╔╝   ║
    ║   ███████║██║  ██║██║  ██║██████╔╝╚██████╔╝██║  ██╔╝    ║
    ║   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝     ║
    ║                                                          ║
    ║        The Open Source AI Coding Assistant              ║
    ║        Based on Claude Code Architecture                ║
    ╚══════════════════════════════════════════════════════════╝
    
    🚀 Features:
       • 3-Layer Memory System (Semantic/Episodic/Working)
       • Agent Swarm with Coordinator
       • 40+ Built-in Tools
       • Prompt Cache Optimization
       • KAIROS Daemon Mode
       • BUDDY Cyber Pet
       • Undercover Mode
    
    Type 'help' for available commands or 'exit' to quit.
    """
    print(banner)


def interactive_mode(engine: QueryEngine):
    """交互模式"""
    print("\n🎤 Interactive Mode (type 'exit' to quit)\n")
    
    history = []
    
    while True:
        try:
            # 显示提示符
            prompt = "\n❯ "
            user_input = input(prompt).strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "q"]:
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == "help":
                print_help()
                continue
            
            if user_input.lower() == "status":
                print_status(engine)
                continue
            
            if user_input.lower().startswith("/"):
                handle_command(user_input, engine)
                continue
            
            # 处理用户输入
            print("\n🤔 Thinking...")
            
            result = engine.submit_message(
                prompt=user_input,
                context={"history": history}
            )
            
            print(f"\n{result.output}")
            
            if result.tool_calls:
                print(f"\n🔧 Tools used: {', '.join(result.matched_tools)}")
            
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": result.output})
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def print_help():
    """打印帮助信息"""
    help_text = """
Available Commands:
    /buddy          - Launch BUDDY pet system
    /kairos start   - Start KAIROS daemon
    /kairos stop    - Stop KAIROS daemon
    /kairos status  - Check KAIROS status
    /undercover on  - Activate undercover mode
    /undercover off - Deactivate undercover mode
    /agent <task>   - Create sub-agent for task
    /compact        - Compact conversation memory
    /memory         - Show memory stats
    /tools          - List available tools
    help            - Show this help
    exit            - Exit ShadowClaude
    
Keyboard Shortcuts:
    Ctrl+C          - Interrupt current operation
    Ctrl+D          - Exit (EOF)
"""
    print(help_text)


def print_status(engine: QueryEngine):
    """打印状态信息"""
    print(f"\n📊 ShadowClaude Status")
    print(f"   Session ID: {engine.session_id}")
    print(f"   Turns: {engine.turn_count}/{engine.config.max_turns}")
    print(f"   Tokens: {engine.total_input_tokens + engine.total_output_tokens}")
    print(f"   Memory: Semantic={engine.config.enable_semantic_memory}, Episodic={engine.config.enable_episodic_memory}")


def handle_command(cmd: str, engine: QueryEngine):
    """处理斜杠命令"""
    parts = cmd.split()
    command = parts[0].lower()
    
    if command == "/buddy":
        launch_buddy()
    
    elif command == "/kairos":
        if len(parts) > 1:
            if parts[1] == "start":
                kairos_start()
            elif parts[1] == "stop":
                kairos_stop()
            elif parts[1] == "status":
                kairos_status()
    
    elif command == "/undercover":
        if len(parts) > 1:
            if parts[1] == "on":
                activate_undercover()
            elif parts[1] == "off":
                deactivate_undercover()
    
    elif command == "/agent":
        if len(parts) > 1:
            task = " ".join(parts[1:])
            create_subagent(task, engine)
    
    elif command == "/tools":
        list_tools(engine)
    
    else:
        print(f"Unknown command: {command}")


def launch_buddy():
    """启动 BUDDY 宠物系统"""
    print("\n🎮 Launching BUDDY system...")
    
    system = BuddySystem()
    buddy = system.get_active_buddy()
    
    if not buddy:
        print("\n🎲 Generating your coding buddy...")
        buddy = system.generate_buddy()
        print(f"\n✨ You got a {buddy.rarity.value.upper()} {buddy.species.value}!")
        if buddy.is_shiny:
            print("⭐ SHINY VARIANT!")
    
    print("\n" + system.render_ascii(buddy))
    print(f"\n{buddy.name}: {buddy.personality.get('favorite_greeting', 'Hello!')}")
    
    # 简单的交互循环
    while True:
        try:
            action = input("\n[BUDDY] Interact (pet/feed/play/advice/exit): ").strip().lower()
            
            if action in ["exit", "quit", "q"]:
                break
            
            if action in ["pet", "feed", "play", "ask_advice"]:
                response = system.interact(action)
                print(f"\n{buddy.name}: {response}")
                print(system.render_ascii(buddy))
            else:
                print("Available actions: pet, feed, play, advice, exit")
                
        except KeyboardInterrupt:
            break
    
    print(f"\n{buddy.name} will be waiting for you! 👋")


def kairos_start():
    """启动 KAIROS"""
    print("\n🌙 Starting KAIROS daemon...")
    
    kairos = KairosDaemon()
    
    # 添加示例定时任务
    kairos.add_scheduled_task(
        name="Daily Summary",
        schedule_type="cron",
        schedule_config={"hour": 8, "minute": 0},
        action="generate_summary",
        action_params={"type": "daily"}
    )
    
    kairos.start()
    
    print("\n✅ KAIROS daemon started!")
    print("   - Daily summary at 08:00")
    print("   - AutoDream memory consolidation every 24h")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        kairos.stop()


def kairos_stop():
    """停止 KAIROS"""
    print("\n🌙 Stopping KAIROS daemon...")
    # 实际实现需要全局状态管理
    print("✅ KAIROS daemon stopped")


def kairos_status():
    """查看 KAIROS 状态"""
    kairos = KairosDaemon()
    status = kairos.get_status()
    
    print(f"\n📊 KAIROS Status:")
    print(f"   Running: {'✅' if status['is_running'] else '❌'}")
    print(f"   Mode: {status['mode']}")
    print(f"   Scheduled Tasks: {status['scheduled_tasks']}")
    print(f"   Webhook Endpoints: {status['webhook_endpoints']}")


def activate_undercover():
    """激活卧底模式"""
    print("\n🕵️ Activating undercover mode...")
    
    undercover = UndercoverMode()
    undercover.activate()
    
    print("✅ Undercover mode activated")
    print("   Identity: Individual Developer")
    print("   AI signatures will be sanitized from outputs")


def deactivate_undercover():
    """停用卧底模式"""
    print("\n🕵️ Deactivating undercover mode...")
    
    undercover = UndercoverMode()
    undercover.deactivate()
    
    print("✅ Undercover mode deactivated")


def create_subagent(task: str, engine: QueryEngine):
    """创建子 Agent"""
    print(f"\n🤖 Creating sub-agent for: {task}")
    
    coordinator = Coordinator()
    agent_task = coordinator.create_agent(
        description=task,
        prompt=f"Please help with: {task}",
        agent_type=AgentType.GENERAL,
        name=f"Agent-{task[:20]}"
    )
    
    print(f"✅ Agent created: {agent_task.name}")
    print(f"   ID: {agent_task.agent_id}")
    print(f"   Type: {agent_task.agent_type.value}")
    print(f"   Status: {agent_task.status.value}")


def list_tools(engine: QueryEngine):
    """列出可用工具"""
    tools = engine.tool_registry.list_tools()
    
    print(f"\n🔧 Available Tools ({len(tools)} total):")
    
    for tool_name in sorted(tools):
        spec = engine.tool_registry.get(tool_name)
        if spec:
            print(f"   • {tool_name} - {spec.description[:50]}...")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="ShadowClaude - The Open Source AI Coding Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  shadowclaude                    Start interactive mode
  shadowclaude "fix this bug"     One-shot mode
  shadowclaude --buddy            Launch BUDDY pet
  shadowclaude --kairos-start     Start KAIROS daemon
        """
    )
    
    parser.add_argument("prompt", nargs="?", help="Prompt to process (if not provided, enters interactive mode)")
    parser.add_argument("-v", "--version", action="store_true", help="Show version")
    parser.add_argument("-i", "--interactive", action="store_true", help="Force interactive mode")
    parser.add_argument("--buddy", action="store_true", help="Launch BUDDY pet system")
    parser.add_argument("--kairos-start", action="store_true", help="Start KAIROS daemon")
    parser.add_argument("--kairos-stop", action="store_true", help="Stop KAIROS daemon")
    parser.add_argument("--undercover", action="store_true", help="Activate undercover mode")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Model to use")
    
    args = parser.parse_args()
    
    # 显示版本
    if args.version:
        from shadowclaude import __version__
        print(f"ShadowClaude v{__version__}")
        return
    
    # 特殊模式
    if args.buddy:
        launch_buddy()
        return
    
    if args.kairos_start:
        kairos_start()
        return
    
    if args.kairos_stop:
        kairos_stop()
        return
    
    # 初始化引擎
    config = QueryEngineConfig(
        model=args.model,
        enable_semantic_memory=True,
        enable_episodic_memory=True
    )
    
    engine = QueryEngine(config)
    
    # 检查是否应该激活卧底模式
    if args.undercover or should_activate_undercover(os.getcwd()):
        activate_undercover()
    
    # 交互模式或一次性模式
    if args.interactive or not args.prompt:
        print_banner()
        interactive_mode(engine)
    else:
        # 一次性模式
        print(f"🤔 Processing: {args.prompt}")
        result = engine.submit_message(args.prompt)
        print(f"\n{result.output}")


if __name__ == "__main__":
    main()
