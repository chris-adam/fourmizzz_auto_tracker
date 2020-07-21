from tracker import tracker
from tui import connexion
from time import time

if __name__ == "__main__":
    # connexion()
    start = time()
    print(tracker.tdc())
    print(time()-start, "s")
