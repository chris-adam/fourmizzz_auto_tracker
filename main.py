from tracker import precision, classement
import tui

if __name__ == "__main__":

    tui.connexion()

    updaters = list()
    updaters.append(classement.TrackerLoop())
    updaters.append(precision.TrackerLoop())

    for uptater in updaters:
        uptater.start()

    tui.main_menu(updaters)

    for uptater in updaters:
        uptater.stop()

    for uptater in updaters:
        print("En attente de l'arrêt de \"{}\"".format(uptater))
        uptater.join()

    print("Programme arrêté")
