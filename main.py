from tracker import tracker
import tui

if __name__ == "__main__":

    tui.connexion()

    updaters = list()
    updaters.append(tracker.TrackerLoop())

    for uptater in updaters:
        uptater.start()

    tui.main_menu(updaters)

    for uptater in updaters:
        uptater.stop()

    for uptater in updaters:
        print("En attente de l'arrêt de \"{}\"".format(uptater))
        uptater.join()

    print("Programme arrêté")
