# main.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
from core.rules import GameConfig, RuleKind
from game import Game

LEDGER_DIR = "./ledger"
LATEST_PTR = os.path.join(LEDGER_DIR, "_latest.txt")

def ask_int(prompt: str, lo: int, hi: int, default: int) -> int:
    while True:
        s = input(f"{prompt} [{lo}-{hi}] (默认 {default})：").strip() or str(default)
        try:
            v = int(s)
            if lo <= v <= hi:
                return v
        except Exception:
            pass
        print("请输入有效数字。")

def maybe_resume(game: Game) -> bool:
    if not os.path.exists(LATEST_PTR):
        return False
    ans = input("检测到上次账本，是否从中恢复？[y/N]：").strip().lower()
    if ans == "y":
        with open(LATEST_PTR, "r", encoding="utf-8") as f:
            path = f.read().strip()
        if os.path.exists(path):
            game.resume_from_ledger(path)
            print(f"已从账本恢复：{path}")
            return True
        else:
            print("找不到账本文件，跳过恢复。")
    return False

def run() -> None:
    print("=== 扩展版（含账本恢复）终端斗地主 V2（Card.code 方案） ===")
    num_players = ask_int("玩家人数", 3, 6, 3)
    use_standard = (num_players == 3)
    num_decks = 1 if num_players <= 4 else 2

    cfg = GameConfig(
        num_players=num_players,
        num_decks=num_decks,
        include_jokers=True,
        rule_kind=RuleKind.STANDARD_DDZ if use_standard else RuleKind.GENERIC_BEAT,
    )

    names = []
    for i in range(num_players):
        n = input(f"请输入玩家{i+1}姓名：").strip() or f"玩家{i+1}"
        names.append(n)

    os.makedirs(LEDGER_DIR, exist_ok=True)
    g = Game(cfg, names, LEDGER_DIR)

    if not maybe_resume(g):
        g.setup()
        with open(LATEST_PTR, "w", encoding="utf-8") as f:
            f.write(g.ledger_path)

    g.play()
    print("游戏结束，感谢游玩！")

if __name__ == "__main__":
    run()
