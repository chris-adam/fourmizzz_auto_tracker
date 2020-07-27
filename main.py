import pandas as pd

from tracker import tracker
from tui import connexion
from time import time
from web import get_list_joueurs_dans_alliance

if __name__ == "__main__":
    # connexion()
    start = time()
    res = tracker.compare()
    cibles = {"Joueurs": [], "Alliances": ["SHAN"]}
    tracker.iter_correspondances(res, cibles)
    print(time()-start, "s")
