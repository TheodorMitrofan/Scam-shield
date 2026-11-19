"""python -m model_detector  [--host 127.0.0.1] [--port 8001]"""
import argparse

import uvicorn

p = argparse.ArgumentParser()
p.add_argument("--host", default="127.0.0.1")
p.add_argument("--port", type=int, default=8001)
a = p.parse_args()
# single worker on purpose: the model is loaded once and kept in memory
uvicorn.run("model_detector.app:app", host=a.host, port=a.port, workers=1)
