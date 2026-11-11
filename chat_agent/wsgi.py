import os
import sys

_cur_dir = os.path.dirname(os.path.abspath(__file__))
if _cur_dir not in sys.path:
    sys.path.insert(0, _cur_dir)

from main import app

if __name__ == "__main__":
    app.run()
