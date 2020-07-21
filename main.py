import pandas as pd

from tracker import tracker
from tui import connexion

if __name__ == "__main__":
    connexion()

    with pd.option_context("display.max_rows", None):
        print(tracker.tdc())
