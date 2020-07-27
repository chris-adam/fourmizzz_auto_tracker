import pandas as pd

from tracker import tracker
from tui import connexion
from time import time

if __name__ == "__main__":
    # connexion()
    start = time()
    with pd.option_context("display.max_columns", None, "display.width", 180):
        print(tracker.compare())
    print(time()-start, "s")
