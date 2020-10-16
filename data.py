import basehash


def get_serveur():
    with open("fichiers/serveur.txt", "r") as identifiants:
        serveur = identifiants.readline().strip()

    return serveur


def get_identifiants():
    hash_fn = basehash.base94()
    with open("fichiers/identifiants.txt", "r") as identifiants:
        pseudo = hash_fn.encode(int(identifiants.readline().strip()))
        mdp = hash_fn.encode(int(identifiants.readline().strip()))
        cookie = hash_fn.encode(int(identifiants.readline().strip()))

    return pseudo, mdp, cookie
