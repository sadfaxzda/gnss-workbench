"""All filesystem state is explicit and relocatable."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COURSE_ROOT = Path(os.environ.get("GNSS_COURSE_ROOT", PROJECT_ROOT / "fixtures" / "course"))
RUNTIME_ROOT = Path(os.environ.get("GNSS_RUNTIME_ROOT", PROJECT_ROOT / "runtime"))

DATASETS = {
    "D02_sim_clean": {
        "title": "正常动态观测",
        "kind": "simulation",
        "epochs": 600,
        "description": "600 个历元 · 1 Hz · 位置与钟差仿真真值",
    },
    "D03_sim_demo": {
        "title": "异常诊断演示",
        "kind": "simulation",
        "epochs": 600,
        "description": "单星偏差、共同偏差、少星与观测中断",
    },
    "D01_real_excerpt": {
        "title": "真实历史观测",
        "kind": "real",
        "epochs": 20,
        "description": "20 个历元 · 约 30 s · 无独立位置真值",
    },
}
