import pandas as pd

from tracker import tracker
from tui import connexion
from time import time
from web import get_list_joueurs_dans_alliance

if __name__ == "__main__":
    # connexion()
    cibles = {"Joueurs": [], "Alliances": ["SHAN", "Raf"]}
    updater = tracker.TrackerLoop(cibles)
    updater.start()
