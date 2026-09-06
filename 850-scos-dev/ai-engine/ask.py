"""AI 问数据 — 命令行入口。

用法：
  python ask.py "RTL 本周 NACK 多少单？"
  python ask.py                    （不带参数进入交互模式，quit 退出）

数据只来自 SCOS Service Layer（默认 http://localhost:5051，可用 SCOS_API_BASE 覆盖）。
"""
import sys
from agent import ask


def _print_answer(q, debug=False):
    print(f'❓ {q}\n')
    try:
        print(ask(q, debug=debug))
    except RuntimeError as e:
        print(f'⚠️ {e}')
    except Exception as e:
        print(f'⚠️ 调用失败：{e}')


def main():
    debug = '--debug' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--debug']
    if args:
        _print_answer(' '.join(args), debug=debug)
        return
    print('850 SCOS · AI 问数据（输入 quit 退出）')
    while True:
        try:
            q = input('\n❓ ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q.lower() == 'quit':
            break
        print()
        _print_answer(q, debug=debug)


if __name__ == '__main__':
    main()
