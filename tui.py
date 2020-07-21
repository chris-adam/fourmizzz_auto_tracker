from web import verifier_connexion


def menu():
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
