from threading import Thread
from time import sleep
import basehash
from getpass import getpass
import sys

import pandas as pd

from web import verifier_connexion

PATH_CIBLES = "fichiers/cibles"


class AutoRepair(Thread):
    def __init__(self, threads):
        Thread.__init__(self)
        self.pursue = True
        self.threads = threads

    def run(self):
        while self.pursue:
            repair(self.threads)
            sleep(10)

    def stop(self):
        self.pursue = False


def main_menu(updaters):
    auto_repair = AutoRepair(updaters)
    auto_repair.start()

    main_menu_text = "\n- ~ - MENU PRINCIPAL - ~ -\n" \
                     "1) Afficher joueurs/alliances surveillés\n" \
                     "2) Ajouter joueur\n" \
                     "3) Ajouter alliance\n" \
                     "4) Supprimer joueur/alliance\n" \
                     "5) Réparer\n" \
                     "6) Arrêter le programme"

    choice = 0
    while choice != 6:
        try:
            print(main_menu_text)
            choice = int(input(">>> "))
            print()

            cibles = pd.read_pickle(PATH_CIBLES)
            if choice == 1:
                with pd.option_context("display.max_rows", None):
                    print(cibles)
            elif choice == 2:
                cibles = pd.concat([cibles, pd.DataFrame({"Type": ["Joueur"],
                                 "Nom": [input("Nom du joueur: ")],
                                 "ID forum": [input("ID du forum (seulement les chiffres): ")]})], ignore_index=True)
            elif choice == 3:
                cibles = pd.concat([cibles, pd.DataFrame({"Type": ["Alliance"],
                                 "Nom": [input("Nom de l'alliance: ")],
                                 "ID forum": [input("ID du forum (seulement les chiffres): ")]})], ignore_index=True)
            elif choice == 4:
                print(cibles)
                ligne_a_supprimer = int(input("Numéro de la ligne à supprimer: "))
                cibles = cibles.drop(ligne_a_supprimer).reset_index(drop=True)
            elif choice == 5:
                repair(updaters)
                print("Réparation terminée")
            elif choice == 6:
                print("Vous quittez le programme... Veuillez patienter.")
                auto_repair.stop()
                auto_repair.join()
            else:
                raise ValueError

            cibles.to_pickle(PATH_CIBLES)

        except ValueError:
            print("Entrée erronée")


def repair(updaters):
    for updater in updaters:
        if not updater.is_alive():
            updaters.remove(updater)
            new_thread = type(updater)()
            new_thread.start()
            updaters.append(new_thread)
            print(updater, "réparé")


def connexion():
    print("Connexion en cours ...")
    while not verifier_connexion():
        print("Identifiants inconnus ou erronés")
        update_identifiants()


def update_identifiants():
    def safe_input(prompt):
        if not sys.stdin.isatty():
            msg = input(prompt)
        else:
            msg = getpass(prompt=prompt)
        return msg

    pseudo = input("Pseudo: ")
    mdp = safe_input("Mot de passe: ")
    cookie_token = safe_input("Cookie d'auto-connection: ")

    hash_fn = basehash.base94()
    with open("fichiers/identifiants.txt", "w+") as identifiants:
        identifiants.write(" ".join([hash_fn.encode(ord(char)) for char in pseudo]))
        identifiants.write("\n")
        identifiants.write(" ".join([hash_fn.encode(ord(char)) for char in mdp]))
        identifiants.write("\n")
        identifiants.write(" ".join([hash_fn.encode(ord(char)) for char in cookie_token]))
