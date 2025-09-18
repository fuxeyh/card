# 终端斗地主（精简可读版 · 3人单副牌 · 含账本恢复）

这是一份**易读、可扩展、可恢复**的终端版「斗地主」示例项目。代码风格简洁，注释充分：
- **3 名玩家**、**单副牌（54 张）**、**标准玩法**（叫分 + 地主拿 3 张底牌）；
- **`Card.code` 单字符串设计**（例如 `3♠ / 10♥ / BJ / RJ`），大小王**无花色**；
- **牌型系统可插拔**（`HandPattern` + `HandRegistry`）；
- **账本式数据库（append-only JSONL）**记录全过程，断电/崩溃可**回放恢复**。

---

## 一、怎么玩（终端操作）
1. 运行：
   ```bash
   python main.py
   ```
2. 依次输入三位玩家的名字。
3. 进入 **叫分**：每位玩家依次输入 0/1/2/3（无人叫分则随机地主）。
4. 对局开始。轮到你时，在终端输入：
   - **出牌**：直接输入牌面（空格分隔）。例如：  
     - `3 3`（对子）  
     - `7 8 9 10 J`（顺子，至少 5 张，不能包含 `2/BJ/RJ`）  
     - `Q Q Q 9`（三带一）  
     - `5 5 5 6 6`（三带一对）  
     - `10 10 J J Q Q`（连对）  
     - `4 4 4 5 5 5`（飞机：纯三顺）  
     - `2 2 2 2`（炸弹）  
     - `BJ RJ`（王炸）
   - **命令**：
     - `help` 查看帮助
     - `show` 查看三家手牌分布摘要
     - `last` 查看上家出牌
     - `tips` 简单提示（仅供参考）
     - `sort` 整理手牌显示
     - `pass` 过（**首家不能 pass**）

> 注：输入大小写不敏感，`t` 会被视作 `10`，`1/01` 会被视作 `A`，`bj/rj` 视作大小王。

---

## 二、项目结构 & 设计思路
```
core/
  enums.py          # 枚举：玩家身份、事件类型、牌型优先级
  cards.py          # 牌面：Card.code 单字段；建牌、排序、输入规范
  player.py         # 玩家：dataclass；取牌/加牌/检查/展示
  hand_patterns.py  # 牌型：HandPattern + 内置若干模式（可扩展）
  registry.py       # 牌型注册表：评估/比较规则（跨类型优先级）
  ledger.py         # 账本：JSONL 追加写入 + 链式哈希校验
  rules.py          # 标准 3 人斗地主：发牌/叫分/定地主（写账本）
  replay.py         # 恢复：从账本回放重建手牌、出牌与轮次
game.py             # 游戏循环：命令解析、出牌校验、写账本
main.py             # 入口：输入姓名、可选择恢复或新开
```

### 1）`Card.code`（如何“聪明”地表示牌）
- **普通牌**用形如 `'3♠'` 的单字符串；大小王用 `'BJ'/'RJ'`，**不含花色**；  
- 通过方法派生信息：`rank()`、`suit()`、`value()`、`short()`；
- 这样**不是所有牌都需要 rank+suit 字段**，也能统一比较与显示。

### 2）牌型系统（怎么“写成可扩展的”）
- 每种牌型是一个类，继承 `HandPattern`：实现 `match(cards)->HandMatch|None`；
- `HandMatch` 给出：`name`、`key`（比较主键）、`meta`（长度等）、`priority`（跨类型强弱）；
- `HandRegistry` 负责评估和比较：**优先比较优先级，其次同形状下比较 key**；
- 内置：单张、对子、三张、三带一、三带一对、顺子、连对、飞机（纯三顺）、四带二（两单/两对）、炸弹、王炸。

### 3）账本（如何“可恢复且可验证”）
- 每个事件写入一行 JSON（`JSONL`），包含：`seq`、`type`、`payload`、`ts`、`prev_hash`、`hash`；
- `hash = sha256(prev_hash + json.dumps(event))`，形成**链式哈希**，`read_all()` 会逐条校验；
- 记录**精确的发牌与出牌**（以 `codes` 表示，例如 `10♠`、`BJ`），恢复时逐一移除对应手牌；
- 最近一次游戏的账本路径保存在 `ledger/_latest.txt`，启动可选择恢复。

---

## 三、如何扩展（保持简洁的前提下）
### 新增牌型
1. 在 `core/hand_patterns.py` 新建一个类，例如：
   ```python
   class MyFancyPattern(HandPattern):
       name = "my_fancy"
       priority = int(PatternPriority.STRONG)
       def match(self, cards):
           # …检查 cards，返回 HandMatch或None
       def same_shape(self, a, b):
           # 如果需要长度等维度一致
           return a.meta.get("length") == b.meta.get("length")
   ```
2. 在 `core/registry.py` 初始化时 `register(MyFancyPattern())` 即可生效。

> 你也可以把内置列表 `BUILTIN_PATTERNS` 改为只包含你需要的模式，或改变 `priority` 以适配自家规则。

### 调整规则
- 规则集中在 `core/rules.py::StandardDouDizhuRules`：
  - 叫分范围、处理方式（例如“抢地主”）、底牌分配、先手都可以直接改；
  - 想做记分/倍数（炸弹翻倍、春天等），也建议在这里扩展并写入账本。

---

## 四、快速 FAQ
- **为什么用 `Card.code`？**  
  统一存储，**大小王无花色**也自然；打印和持久化更直观（`BJ/RJ`）。
- **为什么 Ledger 要记录 `codes` 而不是 rank？**  
  为了**精确恢复**：同 rank 的多张牌通过 suit 区分；王没有 suit 也不会冲突（用 `BJ/RJ`）。
- **AI 能加吗？**  
  可以：在 `game.py` 中给 `Player` 增加非人类策略，或引入一个 `choose_move()` 接口。

---

## 五、运行 & 恢复
```bash
python main.py
```
- 若存在 `ledger/_latest.txt`，程序会询问是否从上次中断处恢复；
- 新开一局会生成新的 `ledger/ledger_<uuid>.jsonl` 并覆盖 `_latest.txt`。

祝玩得开心！
