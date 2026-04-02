"""
BUDDY - 赛博宠物系统
Claude Code 泄露源码中的神秘功能

18 种物种，5 级稀有度，5 维属性，6 种眼睛，8 种帽子
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from pathlib import Path
import json
import random
import time
from datetime import datetime


class Species(Enum):
    """18 种物种"""
    DUCK = "duck"           # 🦆 鸭子
    CAT = "cat"             # 🐱 猫
    DOG = "dog"             # 🐶 狗
    FOX = "fox"             # 🦊 狐狸
    OWL = "owl"             # 🦉 猫头鹰
    RABBIT = "rabbit"       # 🐰 兔子
    PANDA = "panda"         # 🐼 熊猫
    PENGUIN = "penguin"     # 🐧 企鹅
    DRAGON = "dragon"       # 🐉 龙
    UNICORN = "unicorn"     # 🦄 独角兽
    CAPYBARA = "capybara"   # 水豚
    SLOTH = "sloth"         # 🦥 树懒
    OCTOPUS = "octopus"     # 🐙 章鱼
    ROBOT = "robot"         # 🤖 机器人
    GHOST = "ghost"         # 👻 幽灵
    ALIEN = "alien"         # 👽 外星人
    AXOLOTL = "axolotl"     # 美西螈
    BIRB = "birb"           # 🐦 小鸟


class Rarity(Enum):
    """5 级稀有度"""
    COMMON = "common"       # 普通 - 50%
    UNCOMMON = "uncommon"   # 罕见 - 30%
    RARE = "rare"           # 稀有 - 15%
    EPIC = "epic"           # 史诗 - 4%
    LEGENDARY = "legendary" # 传说 - 1%


class EyeStyle(Enum):
    """6 种眼睛样式"""
    NORMAL = "normal"       # 😐 普通
    HAPPY = "happy"         # 😊 开心
    WINK = "wink"           # 😉 眨眼
    SLEEPY = "sleepy"       # 😴 困倦
    SHOCKED = "shocked"     # 😲 震惊
    HEARTS = "hearts"       # 😍 爱心


class Hat(Enum):
    """8 种帽子"""
    NONE = "none"
    TOP_HAT = "top_hat"         # 🎩 礼帽
    PARTY = "party"             # 🥳 派对帽
    CROWN = "crown"             # 👑 皇冠
    BEANIE = "beanie"           # 🧢 针织帽
    SANTA = "santa"             # 🎅 圣诞帽
    WIZARD = "wizard"           # 🧙 巫师帽
    PIRATE = "pirate"           # 🏴‍☠️ 海盗帽
    SAFARI = "safari"           # 🎓 探险帽


@dataclass
class BuddyStats:
    """5 维属性"""
    debugging: int = 50      # 调试能力
    patience: int = 50       # 耐心
    chaos: int = 50          # 混沌/随机性
    wisdom: int = 50         # 智慧
    snark: int = 50          # 毒舌/吐槽
    
    def to_dict(self) -> Dict:
        return {
            "debugging": self.debugging,
            "patience": self.patience,
            "chaos": self.chaos,
            "wisdom": self.wisdom,
            "snark": self.snark
        }


@dataclass
class Buddy:
    """赛博宠物"""
    buddy_id: str
    name: str
    species: Species
    rarity: Rarity
    stats: BuddyStats
    eye_style: EyeStyle
    hat: Hat
    is_shiny: bool  # 闪光变体 (1% 概率)
    
    # 动态属性
    level: int = 1
    experience: int = 0
    happiness: int = 80
    energy: int = 100
    
    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_interaction: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 个性
    personality: Dict[str, str] = field(default_factory=dict)


class BuddySystem:
    """
    BUDDY 赛博宠物系统
    
    用户可以在终端里养一只像素风宠物，它会：
    - 在你编码时提供情绪价值
    - 偶尔给出代码建议（基于 stats.wisdom）
    - 吐槽你的代码（基于 stats.snark）
    - 随机搞点小破坏（基于 stats.chaos）
    """
    
    # 稀有度概率分布
    RARITY_WEIGHTS = {
        Rarity.COMMON: 0.50,
        Rarity.UNCOMMON: 0.30,
        Rarity.RARE: 0.15,
        Rarity.EPIC: 0.04,
        Rarity.LEGENDARY: 0.01
    }
    
    # 物种基础属性加成
    SPECIES_BONUS = {
        Species.DUCK: {"debugging": +10, "chaos": +5},
        Species.CAT: {"patience": +10, "snark": +5},
        Species.DOG: {"patience": +10, "happiness": +10},
        Species.FOX: {"chaos": +10, "wisdom": +5},
        Species.OWL: {"wisdom": +15},
        Species.DRAGON: {"debugging": +10, "chaos": +10, "snark": +5},
        Species.UNICORN: {"wisdom": +10, "chaos": +10},
        Species.ROBOT: {"debugging": +15},
        Species.GHOST: {"chaos": +15},
        Species.CAPYBARA: {"patience": +20},
        Species.SLOTH: {"patience": +20, "energy": -20},
        Species.OCTOPUS: {"debugging": +10, "chaos": +5},
        Species.ALIEN: {"chaos": +15, "wisdom": +10},
        Species.AXOLOTL: {"happiness": +20},
        Species.BIRB: {"snark": +15},
    }
    
    # 稀有度属性加成
    RARITY_MULTIPLIER = {
        Rarity.COMMON: 1.0,
        Rarity.UNCOMMON: 1.1,
        Rarity.RARE: 1.25,
        Rarity.EPIC: 1.5,
        Rarity.LEGENDARY: 2.0
    }
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".shadowclaude" / "buddy"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.buddies: Dict[str, Buddy] = {}
        self.active_buddy_id: Optional[str] = None
        
        self._load_buddies()
    
    def _load_buddies(self):
        """加载已保存的宠物"""
        for file in self.storage_dir.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                
                buddy = Buddy(
                    buddy_id=data["buddy_id"],
                    name=data["name"],
                    species=Species(data["species"]),
                    rarity=Rarity(data["rarity"]),
                    stats=BuddyStats(**data["stats"]),
                    eye_style=EyeStyle(data["eye_style"]),
                    hat=Hat(data["hat"]),
                    is_shiny=data["is_shiny"],
                    level=data.get("level", 1),
                    experience=data.get("experience", 0),
                    happiness=data.get("happiness", 80),
                    energy=data.get("energy", 100),
                    created_at=data.get("created_at"),
                    last_interaction=data.get("last_interaction"),
                    personality=data.get("personality", {})
                )
                
                self.buddies[buddy.buddy_id] = buddy
                
            except Exception as e:
                print(f"Failed to load buddy from {file}: {e}")
    
    def _save_buddy(self, buddy: Buddy):
        """保存宠物到磁盘"""
        file_path = self.storage_dir / f"{buddy.buddy_id}.json"
        
        data = {
            "buddy_id": buddy.buddy_id,
            "name": buddy.name,
            "species": buddy.species.value,
            "rarity": buddy.rarity.value,
            "stats": buddy.stats.to_dict(),
            "eye_style": buddy.eye_style.value,
            "hat": buddy.hat.value,
            "is_shiny": buddy.is_shiny,
            "level": buddy.level,
            "experience": buddy.experience,
            "happiness": buddy.happiness,
            "energy": buddy.energy,
            "created_at": buddy.created_at,
            "last_interaction": buddy.last_interaction,
            "personality": buddy.personality
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def generate_buddy(self, name: Optional[str] = None) -> Buddy:
        """
        生成新的赛博宠物
        
        随机物种、稀有度、属性、外观
        """
        buddy_id = f"buddy-{int(time.time() * 1000)}"
        
        # 1. 随机物种
        species = random.choice(list(Species))
        
        # 2. 随机稀有度（加权）
        rarity = random.choices(
            list(self.RARITY_WEIGHTS.keys()),
            weights=list(self.RARITY_WEIGHTS.values())
        )[0]
        
        # 3. 计算基础属性
        stats = BuddyStats()
        
        # 物种加成
        if species in self.SPECIES_BONUS:
            bonus = self.SPECIES_BONUS[species]
            for stat, value in bonus.items():
                if hasattr(stats, stat):
                    current = getattr(stats, stat)
                    setattr(stats, stat, min(100, current + value))
        
        # 稀有度加成
        multiplier = self.RARITY_MULTIPLIER[rarity]
        for attr in ["debugging", "patience", "chaos", "wisdom", "snark"]:
            current = getattr(stats, attr)
            setattr(stats, attr, int(current * multiplier))
        
        # 4. 随机外观
        eye_style = random.choice(list(EyeStyle))
        hat = random.choice(list(Hat))
        
        # 5. 闪光判定 (1%)
        is_shiny = random.random() < 0.01
        
        # 6. 生成个性
        personality = self._generate_personality(species, stats)
        
        buddy = Buddy(
            buddy_id=buddy_id,
            name=name or f"{species.value.title()}-{buddy_id[-4:]}",
            species=species,
            rarity=rarity,
            stats=stats,
            eye_style=eye_style,
            hat=hat,
            is_shiny=is_shiny,
            personality=personality
        )
        
        self.buddies[buddy_id] = buddy
        self._save_buddy(buddy)
        
        return buddy
    
    def _generate_personality(self, species: Species, stats: BuddyStats) -> Dict[str, str]:
        """根据物种和属性生成个性"""
        traits = []
        
        if stats.snark > 60:
            traits.append("sarcastic")
        if stats.chaos > 60:
            traits.append("chaotic")
        if stats.patience > 60:
            traits.append("patient")
        if stats.wisdom > 60:
            traits.append("wise")
        if stats.debugging > 60:
            traits.append("analytical")
        
        # 物种特定个性
        species_traits = {
            Species.CAT: ["curious", "independent"],
            Species.DOG: ["loyal", "enthusiastic"],
            Species.DRAGON: ["proud", "fierce"],
            Species.SLOTH: ["relaxed", "slow"],
            Species.ROBOT: ["logical", "efficient"],
            Species.GHOST: ["mysterious", "playful"],
        }
        
        if species in species_traits:
            traits.extend(species_traits[species])
        
        return {
            "traits": traits,
            "favorite_greeting": self._generate_greeting(species),
            "catchphrase": self._generate_catchphrase(species, stats)
        }
    
    def _generate_greeting(self, species: Species) -> str:
        """生成打招呼语"""
        greetings = {
            Species.DUCK: "Quack! Ready to debug?",
            Species.CAT: "*stretches* Let's see what you're coding...",
            Species.DOG: "Woof! I'm here to help!",
            Species.DRAGON: "*fire breath* Let's make some magic!",
            Species.ROBOT: "Systems online. Awaiting commands.",
            Species.GHOST: "Boo! Did I scare your bugs away?",
            Species.SLOTH: "*yawns* Take it slow...",
        }
        return greetings.get(species, f"Hello! I'm your {species.value} buddy!")
    
    def _generate_catchphrase(self, species: Species, stats: BuddyStats) -> str:
        """生成口头禅"""
        if stats.snark > 70:
            return "Your code is... interesting."
        elif stats.chaos > 70:
            return "What if we tried... something wild?"
        elif stats.wisdom > 70:
            return "Patience, young padawan."
        else:
            return "Let's do this!"
    
    def get_active_buddy(self) -> Optional[Buddy]:
        """获取当前激活的宠物"""
        if self.active_buddy_id:
            return self.buddies.get(self.active_buddy_id)
        
        # 如果没有激活的，返回第一个
        if self.buddies:
            return next(iter(self.buddies.values()))
        
        return None
    
    def set_active_buddy(self, buddy_id: str) -> bool:
        """设置激活的宠物"""
        if buddy_id in self.buddies:
            self.active_buddy_id = buddy_id
            return True
        return False
    
    def interact(self, interaction_type: str) -> str:
        """
        与宠物互动
        
        interaction_type: "pet", "feed", "play", "ask_advice"
        """
        buddy = self.get_active_buddy()
        if not buddy:
            return "No buddy available. Generate one first!"
        
        buddy.last_interaction = datetime.now().isoformat()
        
        if interaction_type == "pet":
            buddy.happiness = min(100, buddy.happiness + 5)
            buddy.energy = max(0, buddy.energy - 2)
            self._save_buddy(buddy)
            return f"{buddy.name} seems happy! {buddy.personality.get('catchphrase')}"
        
        elif interaction_type == "feed":
            buddy.energy = min(100, buddy.energy + 20)
            self._save_buddy(buddy)
            return f"{buddy.name} is energized! Ready to help you code."
        
        elif interaction_type == "play":
            buddy.happiness = min(100, buddy.happiness + 10)
            buddy.experience += 5
            self._check_level_up(buddy)
            self._save_buddy(buddy)
            return f"{buddy.name} had fun playing! Gained 5 XP."
        
        elif interaction_type == "ask_advice":
            return self._give_advice(buddy)
        
        return f"{buddy.name} looks at you curiously."
    
    def _check_level_up(self, buddy: Buddy):
        """检查是否升级"""
        xp_needed = buddy.level * 100
        if buddy.experience >= xp_needed:
            buddy.level += 1
            buddy.experience -= xp_needed
            
            # 升级奖励
            buddy.stats.debugging += 2
            buddy.stats.patience += 2
            
            print(f"🎉 {buddy.name} leveled up to {buddy.level}!")
    
    def _give_advice(self, buddy: Buddy) -> str:
        """根据属性给出建议"""
        if buddy.stats.wisdom > buddy.stats.snark:
            return f"{buddy.name} suggests: Take a break and look at the problem with fresh eyes."
        elif buddy.stats.snark > 70:
            return f"{buddy.name} says: Have you tried turning it off and on again? ...Just kidding. But seriously, check your imports."
        elif buddy.stats.chaos > 70:
            return f"{buddy.name} grins: What if you just... delete everything and start over? No? Worth a shot."
        else:
            return f"{buddy.name} nods: You're doing great! Keep going!"
    
    def render_ascii(self, buddy: Optional[Buddy] = None) -> str:
        """
        渲染 ASCII 艺术形象
        """
        buddy = buddy or self.get_active_buddy()
        if not buddy:
            return "No buddy to display."
        
        # 基础形象
        base_art = self._get_species_art(buddy.species)
        
        # 添加眼睛
        eye_art = self._get_eye_art(buddy.eye_style)
        
        # 添加帽子
        hat_art = self._get_hat_art(buddy.hat)
        
        # 闪光效果
        shiny_prefix = "✨ " if buddy.is_shiny else ""
        
        # 组装
        lines = [
            f"{shiny_prefix}{buddy.name} ({buddy.rarity.value.upper()})",
            f"Level: {buddy.level} | XP: {buddy.experience}/{buddy.level * 100}",
            f"😊 {buddy.happiness}/100 | ⚡ {buddy.energy}/100",
            "",
            hat_art,
            base_art,
            eye_art,
            "",
            f"🎓 Debugging: {buddy.stats.debugging}",
            f"🧘 Patience: {buddy.stats.patience}",
            f"🌀 Chaos: {buddy.stats.chaos}",
            f"📚 Wisdom: {buddy.stats.wisdom}",
            f"😏 Snark: {buddy.stats.snark}",
            "",
            f'"{buddy.personality.get("catchphrase", "Hello!")}"'
        ]
        
        return "\n".join(lines)
    
    def _get_species_art(self, species: Species) -> str:
        """获取物种 ASCII 艺术"""
        arts = {
            Species.DUCK: """
    >o)
    (_>""",
            Species.CAT: """
   /\_/\
  ( o.o )
   > ^ <""",
            Species.DOG: """
   / \__
  (    @\___
  /         O
 /   (_____/
/_____/   U""",
            Species.DRAGON: """
      \****/
      (o)(o)
  .---.___.
 /   --\   \
|   +++ |  |
 \_______/""",
            Species.ROBOT: """
   _____
  |O   O|
  |  |  |
  |_____|
   |   |
   |___|""",
            Species.GHOST: """
   .-.
  (o o)
  | O \
   \   \
    `~~~'""",
            Species.SLOTH: """
   ____
  /  o \
 |   z  |
  \____/
   ||||""",
        }
        return arts.get(species, "    [?]")
    
    def _get_eye_art(self, eye_style: EyeStyle) -> str:
        """获取眼睛样式"""
        eyes = {
            EyeStyle.NORMAL: "  o o",
            EyeStyle.HAPPY: "  ^ ^",
            EyeStyle.WINK: "  o -",
            EyeStyle.SLEEPY: "  - -",
            EyeStyle.SHOCKED: "  O O",
            EyeStyle.HEARTS: "  ♥ ♥",
        }
        return eyes.get(eye_style, "  o o")
    
    def _get_hat_art(self, hat: Hat) -> str:
        """获取帽子艺术"""
        hats = {
            Hat.TOP_HAT: "    __\n   |__|",
            Hat.PARTY: "   <* *>",
            Hat.CROWN: "    ♔",
            Hat.WIZARD: "    /\\\n   /  \\",
            Hat.NONE: "",
        }
        return hats.get(hat, "")
    
    def list_buddies(self) -> List[Dict]:
        """列出所有宠物"""
        return [
            {
                "id": b.buddy_id,
                "name": b.name,
                "species": b.species.value,
                "rarity": b.rarity.value,
                "level": b.level,
                "is_shiny": b.is_shiny
            }
            for b in self.buddies.values()
        ]


# 使用示例
if __name__ == "__main__":
    system = BuddySystem()
    
    # 生成新宠物
    print("🎲 Generating your coding buddy...")
    buddy = system.generate_buddy(name="Debugger")
    
    print(f"\n✨ You got a {buddy.rarity.value.upper()} {buddy.species.value}!")
    if buddy.is_shiny:
        print("⭐ SHINY VARIANT!")
    
    print("\n" + system.render_ascii(buddy))
    
    print(f"\n{buddy.name}: {buddy.personality.get('favorite_greeting')}")
    
    # 互动
    print("\n" + system.interact("ask_advice"))
