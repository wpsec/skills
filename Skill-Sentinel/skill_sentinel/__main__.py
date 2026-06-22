# skill_sentinel/__main__.py
# 允许通过 python -m skill_sentinel 运行

import sys
import os
import importlib.util

# 加载 scripts/sentinel 模块
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sentinel_path = os.path.join(script_dir, "scripts", "sentinel.py")

if os.path.exists(sentinel_path):
    spec = importlib.util.spec_from_file_location("sentinel", sentinel_path)
    sentinel = importlib.util.module_from_spec(spec)
    sys.modules["sentinel"] = sentinel
    spec.loader.exec_module(sentinel)
    sentinel.main()
else:
    print("错误: 找不到 CLI 入口脚本", file=sys.stderr)
    sys.exit(1)