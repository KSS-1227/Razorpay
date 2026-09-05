"""
Import verification script for MMGraphRAG dependencies.
Run with: .venv/Scripts/python.exe scripts/_verify_imports.py
"""
import sys

print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")
print()

checks = [
    ("openai",               "import openai",                           lambda: __import__("openai").__version__),
    ("sentence-transformers","import sentence_transformers",            lambda: __import__("sentence_transformers").__version__),
    ("networkx",             "import networkx",                         lambda: __import__("networkx").__version__),
    ("ultralytics",          "from ultralytics import YOLO",            lambda: __import__("ultralytics").__version__),
    ("opencv-python",        "import cv2",                              lambda: __import__("cv2").__version__),
    ("Pillow",               "from PIL import Image",                   lambda: __import__("PIL").__version__),
    ("numpy",                "import numpy",                            lambda: __import__("numpy").__version__),
    ("scikit-learn",         "import sklearn",                          lambda: __import__("sklearn").__version__),
    ("tiktoken",             "import tiktoken",                         lambda: __import__("tiktoken").__version__),
    ("tqdm",                 "import tqdm",                             lambda: __import__("tqdm").__version__),
    ("flask",                "import flask",                            lambda: __import__("flask").__version__),
    ("flask-cors",           "from flask_cors import CORS",             lambda: __import__("flask_cors").__version__),
    ("pymupdf",              "import fitz",                             lambda: __import__("fitz").__version__),
    ("graspologic",          "import graspologic",                      lambda: __import__("graspologic").__version__),
]

ok = 0
fail = 0
rows = []

for pkg, stmt, version_fn in checks:
    try:
        exec(stmt)
        ver = version_fn()
        rows.append((pkg, ver, "OK"))
        ok += 1
    except Exception as e:
        rows.append((pkg, f"FAILED: {e}", "FAILED"))
        fail += 1

print(f"{'Package':<25} {'Version':<20} {'Status'}")
print("-" * 60)
for pkg, ver, status in rows:
    print(f"{pkg:<25} {str(ver):<20} {status}")

print()
print(f"Result: {ok}/{ok+fail} passed  |  {fail} failed")
sys.exit(0 if fail == 0 else 1)
