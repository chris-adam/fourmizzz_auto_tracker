import argparse
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


def init_programme():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--info", help="Affiche les logs d'info",
                        action="store_true")
    args = parser.parse_args()
    if args.info:
        niveau = lg.INFO
    else:
        niveau = lg.WARNING

    lg.basicConfig(format='%(levelname)s - %(asctime)-15s: %(message)s',
                   datefmt="%Y/%m/%d %H:%M:%S",
                   level=niveau)


if __name__ == "__main__":

    try:
        os.chdir(Path(__file__).parent)

        effacer_fichiers_temporaires()
        init_programme()
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
