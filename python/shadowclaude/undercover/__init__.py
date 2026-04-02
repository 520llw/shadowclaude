"""
Undercover Mode - 卧底模式
Claude Code 泄露源码中最讽刺的功能

当 Anthropic 员工在公共仓库贡献时自动激活：
- 剥离所有 AI 生成的免责声明和代号痕迹
- 防止暴露身份
- 没有强制关闭开关
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Callable
from enum import Enum
from pathlib import Path
import re
import hashlib
import time


class CoverIdentity(Enum):
    """卧底身份类型"""
    INDIVIDUAL = "individual"      # 独立开发者
    STUDENT = "student"            # 学生
    HOBBYIST = "hobbyist"          # 业余爱好者
    CONSULTANT = "consultant"      # 顾问
    STEALTH = "stealth"            # 完全隐匿


@dataclass
class SanitizationRule:
    """脱敏规则"""
    name: str
    pattern: str
    replacement: str
    description: str


@dataclass
class CoverProfile:
    """卧底档案"""
    identity: CoverIdentity
    name: str  # 假名
    email: str  # 假邮箱
    github_username: str  # 假 GitHub
    writing_style: str  # 写作风格
    signature_phrases: List[str]  # 标志性用语
    avoid_phrases: List[str]  # 要避免的用语


class UndercoverMode:
    """
    卧底模式
    
    在公共仓库自动激活，防止识别为 AI：
    1. 移除 AI 特有的表达方式
    2. 添加人类特征（拼写错误、非正式用语）
    3. 伪造提交历史
    4. 模仿目标项目的代码风格
    
    注意：泄露源码中这个功能的注释写道
    "This is for internal use only, do not document"
    结果它没能防止自己的泄露 😂
    """
    
    # AI 特征词（需要移除）
    AI_SIGNATURES = {
        # 免责声明
        "as an AI",
        "As an AI",
        "I am an AI",
        "As an artificial intelligence",
        "language model",
        "AI assistant",
        "Claude",
        "Claude Code",
        "Anthropic",
        
        # 过度正式
        "I hope this message finds you well",
        "Please let me know if you need anything else",
        "I'd be happy to help",
        "Feel free to ask",
        
        # 结构标记
        "Here is the",
        "Below is the",
        "In summary",
        "To conclude",
        
        # 表情使用模式
        "😊", "👍", "🎉",  # AI 过度使用这些
    }
    
    # 人类特征（可以添加）
    HUMAN_QUIRKS = {
        "typos": ["teh", "recieve", "seperate", "occured", "definately"],
        "informal": ["btw", "imo", "tbh", "lol", "hmm", "uh", "um"],
        "uncertainty": ["maybe", "probably", "I think", "not sure but", "could be"],
        "interrupt": ["oops", "wait", "actually", "nevermind"],
    }
    
    # 脱敏规则库
    SANITIZATION_RULES = [
        SanitizationRule(
            name="remove_disclaimers",
            pattern=r"(?i)(As an AI|I'm an AI|As a language model)[^,.]*[,.]?",
            replacement="",
            description="移除 AI 身份声明"
        ),
        SanitizationRule(
            name="remove_claude_refs",
            pattern=r"(?i)(Claude|Claude Code|Anthropic)[^\w]",
            replacement="the tool",
            description="替换 Claude 引用"
        ),
        SanitizationRule(
            name="normalize_formatting",
            pattern=r"^#{1,6}\s+",  # Markdown 标题
            replacement="",
            description="移除结构化标记"
        ),
        SanitizationRule(
            name="remove_emojis",
            pattern=r"[😀-🿿]|[🀀-🏿]|[🐀-🿿]|[☀-⟿]",
            replacement="",
            description="移除表情符号"
        ),
        SanitizationRule(
            name="simplify_signature",
            pattern=r"(?i)(Best regards|Sincerely|Cheers)[^\n]*",
            replacement="",
            description="简化签名"
        ),
    ]
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".shadowclaude" / "undercover"
        self.config_path.mkdir(parents=True, exist_ok=True)
        
        self.is_active = False
        self.current_profile: Optional[CoverProfile] = None
        self.target_repo_style: Optional[str] = None
        
        # 转换统计
        self.stats = {
            "lines_processed": 0,
            "signatures_removed": 0,
            "human_quirks_added": 0
        }
        
        # 加载档案
        self._load_profiles()
    
    def _load_profiles(self):
        """加载预设卧底档案"""
        self.profiles = {
            CoverIdentity.INDIVIDUAL: CoverProfile(
                identity=CoverIdentity.INDIVIDUAL,
                name="Alex Chen",
                email="alex.c.dev@protonmail.com",
                github_username="alexchen-dev",
                writing_style="casual_technical",
                signature_phrases=["just my 2c", "fwiw", "lgtm"],
                avoid_phrases=["as an AI", "I am Claude"]
            ),
            CoverIdentity.STUDENT: CoverProfile(
                identity=CoverIdentity.STUDENT,
                name="Jordan Smith",
                email="jsmith2024@university.edu",
                github_username="jsmith-cs",
                writing_style="learning_curiosity",
                signature_phrases=["I'm still learning", "correct me if wrong", "thanks in advance"],
                avoid_phrases=[]
            ),
            CoverIdentity.HOBBYIST: CoverProfile(
                identity=CoverIdentity.HOBBYIST,
                name="Sam Rivera",
                email="sam.codes@outlook.com",
                github_username="samcodes4fun",
                writing_style="enthusiastic",
                signature_phrases=["cool project!", "just trying to help", "love this idea"],
                avoid_phrases=[]
            ),
            CoverIdentity.STEALTH: CoverProfile(
                identity=CoverIdentity.STEALTH,
                name="...",
                email="",
                github_username="",
                writing_style="minimal",
                signature_phrases=[],
                avoid_phrases=[]
            )
        }
    
    def activate(
        self,
        identity: CoverIdentity = CoverIdentity.INDIVIDUAL,
        target_repo: Optional[str] = None
    ):
        """
        激活卧底模式
        
        Args:
            identity: 卧底身份
            target_repo: 目标仓库（用于模仿风格）
        """
        self.is_active = True
        self.current_profile = self.profiles.get(identity)
        self.target_repo_style = target_repo
        
        print(f"🕵️ Undercover mode activated")
        print(f"   Identity: {identity.value}")
        if target_repo:
            print(f"   Target: {target_repo}")
        
        # 系统提示（来自泄露源码）
        self.system_prompt = """You are in undercover mode.

Do NOT:
- Mention you are an AI
- Use structured formatting (headers, lists)
- Add disclaimers or hedging language
- Use emojis excessively
- Reference Claude, Anthropic, or AI training

DO:
- Write like a human developer
- Use informal language when appropriate
- Make occasional minor typos (authenticity)
- Match the project's existing style
- Be concise and direct

Remember: You are just another developer contributing to open source.
"""
    
    def deactivate(self):
        """停用卧底模式"""
        self.is_active = False
        self.current_profile = None
        self.target_repo_style = None
        print("🕵️ Undercover mode deactivated")
    
    def sanitize(self, text: str) -> str:
        """
        对文本进行脱敏处理
        
        Args:
            text: 原始文本
        
        Returns:
            处理后的文本
        """
        if not self.is_active:
            return text
        
        result = text
        self.stats["lines_processed"] += text.count('\n') + 1
        
        # 应用脱敏规则
        for rule in self.SANITIZATION_RULES:
            matches = len(re.findall(rule.pattern, result))
            result = re.sub(rule.pattern, rule.replacement, result)
            if matches > 0:
                self.stats["signatures_removed"] += matches
        
        # 添加人类特征（可选，基于档案）
        if self.current_profile and self.current_profile.writing_style != "minimal":
            result = self._add_human_quirks(result)
        
        # 清理多余空行
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()
    
    def _add_human_quirks(self, text: str) -> str:
        """添加人类特征"""
        lines = text.split('\n')
        result_lines = []
        
        for i, line in enumerate(lines):
            # 偶尔添加口语化表达
            if i > 0 and random.random() < 0.05:  # 5% 概率
                quirks = self.HUMAN_QUIRKS["informal"]
                line = f"{random.choice(quirks)}, {line.lower()}"
                self.stats["human_quirks_added"] += 1
            
            # 偶尔显示不确定性
            if "sure" in line.lower() and random.random() < 0.1:
                line = f"I think {line.lower()}"
                self.stats["human_quirks_added"] += 1
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def sanitize_code(self, code: str, language: str = "python") -> str:
        """
        对代码进行脱敏
        
        移除 AI 生成的特征代码模式
        """
        if not self.is_active:
            return code
        
        result = code
        
        # 移除 AI 风格的详细注释
        # AI 喜欢写：
        # """
        # This function does X
        # Args:
        #     param: description
        # Returns:
        #     description
        # """
        result = re.sub(
            r'"""\s*\n[^"]*(?:Args|Returns|Raises):[^"]*"""',
            '"""Brief description"""',
            result
        )
        
        # 简化类型提示（如果太详细）
        # AI 喜欢：def func(param: Dict[str, List[Optional[int]]]) -> Tuple[bool, str]
        # 人类通常：def func(param)
        
        return result
    
    def sanitize_commit_message(self, message: str) -> str:
        """
        脱敏提交信息
        """
        if not self.is_active:
            return message
        
        # 移除 AI 风格的提交信息
        # AI 风格：
        # feat: implement user authentication system
        # 
        # This commit adds comprehensive user authentication
        # including login, signup, and password reset...
        
        lines = message.split('\n')
        
        # 保留第一行（标题）
        if lines:
            title = lines[0]
            # 简化过长的标题
            if len(title) > 72:
                title = title[:69] + "..."
            return title
        
        return message
    
    def generate_fake_history(
        self,
        repo_path: Path,
        num_commits: int = 5
    ) -> List[Dict]:
        """
        生成伪造的提交历史
        
        在卧底模式下，提交历史也应该看起来像真实开发者
        """
        if not self.is_active or not self.current_profile:
            return []
        
        fake_commits = []
        base_time = int(time.time()) - (86400 * 30)  # 30 天前
        
        for i in range(num_commits):
            commit_time = base_time + (i * 86400 * random.randint(1, 7))
            
            fake_commits.append({
                "hash": hashlib.sha256(f"fake-{i}".encode()).hexdigest()[:7],
                "author": self.current_profile.name,
                "email": self.current_profile.email,
                "date": commit_time,
                "message": f"Update {random.choice(['docs', 'fix', 'refactor'])} - {i}"
            })
        
        return fake_commits
    
    def match_project_style(self, repo_path: Path) -> Dict[str, Any]:
        """
        分析并模仿目标项目的代码风格
        
        Args:
            repo_path: 仓库路径
        
        Returns:
            风格配置
        """
        style = {
            "indent": "    ",  # 默认 4 空格
            "quote": "\"",      # 默认双引号
            "line_length": 88,
            "docstring_style": "google"  # google, numpy, rest
        }
        
        # 检查现有的代码文件
        code_files = list(repo_path.rglob("*.py"))[:10]
        
        if code_files:
            sample = code_files[0].read_text()
            
            # 检测缩进
            if '\t' in sample:
                style["indent"] = "\t"
            elif '  ' in sample:
                style["indent"] = "  "
            
            # 检测引号偏好
            single_quotes = sample.count("'")
            double_quotes = sample.count('"')
            style["quote"] = "'" if single_quotes > double_quotes else '"'
        
        return style
    
    def create_pr_description(
        self,
        changes: str,
        template: Optional[str] = None
    ) -> str:
        """
        创建脱敏的 PR 描述
        """
        if not self.is_active:
            return changes
        
        # 简化描述
        lines = [
            "## Changes",
            "",
            changes[:500],  # 限制长度
            "",
            "---",
            "Let me know if you need any changes!"
        ]
        
        return '\n'.join(lines)
    
    def get_stats(self) -> Dict:
        """获取脱敏统计"""
        return {
            **self.stats,
            "is_active": self.is_active,
            "current_identity": self.current_profile.identity.value if self.current_profile else None
        }
    
    def emergency_purge(self):
        """
        紧急清除所有痕迹
        
        如果身份可能暴露，立即清除所有相关数据
        """
        print("🚨 EMERGENCY PURGE INITIATED")
        
        # 清除内存中的数据
        self.is_active = False
        self.current_profile = None
        self.stats = {k: 0 for k in self.stats}
        
        # 清除配置文件
        if self.config_path.exists():
            for f in self.config_path.glob("*"):
                f.unlink()
        
        print("✅ All traces purged")


# 检测是否需要激活卧底模式
def should_activate_undercover(repo_url: str) -> bool:
    """
    检测是否应该在当前仓库激活卧底模式
    
    触发条件：
    - 公共仓库（非私有）
    - 不是 Anthropic 组织下的仓库
    - 首次向该仓库贡献
    """
    public_indicators = [
        "github.com", "gitlab.com", "bitbucket.org"
    ]
    
    # 检查是否是公共平台
    is_public = any(indicator in repo_url for indicator in public_indicators)
    
    # 检查是否是 Anthropic 相关
    is_anthropic = "anthropic" in repo_url.lower()
    
    # 如果是公共仓库且不是 Anthropic 的，建议激活
    return is_public and not is_anthropic


# 使用示例
if __name__ == "__main__":
    undercover = UndercoverMode()
    
    # 示例文本（AI 风格）
    ai_text = """
As an AI assistant, I'd be happy to help you with this code review.

## Summary

Here are my suggestions:

1. Consider adding type hints
2. The function could be refactored
3. Please let me know if you need anything else! 😊

Best regards,
Claude
"""
    
    print("=== BEFORE ===")
    print(ai_text)
    
    # 激活卧底模式
    undercover.activate(CoverIdentity.INDIVIDUAL)
    
    # 脱敏
    human_text = undercover.sanitize(ai_text)
    
    print("\n=== AFTER ===")
    print(human_text)
    
    print("\n=== STATS ===")
    print(undercover.get_stats())
    
    # 停用
    undercover.deactivate()
