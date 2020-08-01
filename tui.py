from web import verifier_connexion

import pandas as pd

PATH_CIBLES = "fichiers/cibles"


def main_menu(updaters):
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
                cibles = cibles.append(pd.DataFrame({"Type": ["Joueur"],
                                                     "Nom": [input("Nom du joueur: ")],
                                                     "ID forum": [input("ID du forum (seulement les chiffres): ")]}),
                                       ignore_index=True)
            elif choice == 3:
                cibles = cibles.append(pd.DataFrame({"Type": ["Alliance"],
                                                     "Nom": [input("Nom de l'alliance: ")],
                                                     "ID forum": [input("ID du forum (seulement les chiffres): ")]}),
                                       ignore_index=True)
            elif choice == 4:
                print(cibles)
                ligne_a_supprimer = int(input("Numéro de la ligne à supprimer: "))
                cibles = cibles.drop(ligne_a_supprimer).reset_index(drop=True)
            elif choice == 5:
                for updater in updaters:
                    if not updater.isAlive():
                        updaters.remove(updater)
                        new_thread = type(updater)()
                        new_thread.start()
                        updaters.append(new_thread)
                        print(updater, "réparé")
                print("Réparation terminée")
            elif choice == 6:
                print("Vous quittez le programme ...")
            else:
                raise ValueError

            cibles.to_pickle(PATH_CIBLES)

        except ValueError:
            print("Entrée erronée")


def connexion():
    while not verifier_connexion():
        print("Identifiants inconnus ou erronés")
        update_identifiants()


def update_identifiants():
    pseudo = input("Pseudo: ")
    mdp = input("Mot de passe: ")

    with open("fichiers/identifiants.txt", "w+") as identifiants:
        identifiants.write(pseudo)
        identifiants.write("\n")
        identifiants.write(mdp)
