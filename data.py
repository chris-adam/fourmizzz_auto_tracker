def get_serveur():
    with open("fichiers/serveur.txt", "r") as identifiants:
        serveur = identifiants.readline().strip()

    return serveur


def get_identifiants():
    with open("fichiers/identifiants.txt", "r") as identifiants:
        pseudo = identifiants.readline().strip()
        mdp = identifiants.readline().strip()

    return pseudo, mdp