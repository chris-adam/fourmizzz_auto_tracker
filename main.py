import logging as lg
import os
import platform
import traceback
from pathlib import Path

import tui
from tracker import precision, classement


def effacer_fichiers_temporaires():
    # Efface les fichiers de sauvegarde de tdc pour éviter les incohérences lors du prochain lancement
    lg.info("Suppression des fichiers temporaires...")
    for folder in ("tracker/pseudo_temp/", "tracker/tdc_temp/", "tracker/queue/"):
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                os.remove(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))


if __name__ == "__main__":
    try:
        os.chdir(Path(__file__).parent)
        effacer_fichiers_temporaires()
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
            lg.info("En attente de l'arrêt de \"{}\"".format(uptater))
            uptater.join()

    except Exception:
        if platform.system() == "Windows":
            traceback.print_exc()
            os.system("pause")
        raise

    finally:
        effacer_fichiers_temporaires()
        lg.info("Programme arrêté")
