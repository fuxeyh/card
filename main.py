# main.py
# -*- coding: utf-8 -*-
"""Entry point – focused 3-player, single-deck Dou Dizhu with a recoverable ledger."""

from __future__ import annotations

import os
from game import Game, LATEST_PTR


def run() -> None:
    print("=== 精简可读版终端斗地主（3人、单副牌、含账本恢复） ===")
    names = []
    for i in range(3):
        n = input(f"请输入玩家{i + 1}姓名：").strip() or f"玩家{i + 1}"
        names.append(n)

    g = Game(names)

    # Offer resume if a latest ledger is found
    if os.path.exists(LATEST_PTR):
        ans = input("检测到上次账本，是否从中恢复？[y/N]：").strip().lower()
        if ans == "y":
            with open(LATEST_PTR, "r", encoding="utf-8") as f:
                path = f.read().strip()
            if os.path.exists(path):
                g.resume_from_ledger(path)
                print(f"已从账本恢复：{path}")
            else:
                print("找不到最新账本文件，忽略恢复。")
        else:
            g.setup()
    else:
        g.setup()

    g.play()
    print("游戏结束，感谢游玩！")


if __name__ == "__main__":
    run()
