import basehash


def get_serveur():
    with open("fichiers/serveur.txt", "r") as identifiants:
        serveur = identifiants.readline().strip()

    return serveur


def get_identifiants():
    hash_fn = basehash.base94()
    with open("fichiers/identifiants.txt", "r") as identifiants:
        pseudo = "".join([chr(hash_fn.decode(char)) for char in identifiants.readline().strip().split()])
        mdp = "".join([chr(hash_fn.decode(char)) for char in identifiants.readline().strip().split()])
        cookie = "".join([chr(hash_fn.decode(char)) for char in identifiants.readline().strip().split()])

    return pseudo, mdp, cookie
