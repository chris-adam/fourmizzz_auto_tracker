import os
from datetime import datetime, timedelta
from threading import Thread
from time import sleep

import pandas as pd
import requests
from bs4 import BeautifulSoup

from data import get_serveur, get_identifiants
from web import get_list_joueurs_dans_alliance, PostForum, get_alliance


class TrackerLoop(Thread):
    def __init__(self):
        Thread.__init__(self)
        if not os.path.exists("fichiers/cibles"):
            pd.DataFrame(columns=["Type", "Nom", "ID forum"]).to_pickle("fichiers/cibles")
        self.cibles = pd.read_pickle("fichiers/cibles")
        self.pursue = True

    def run(self):
        next_time = datetime.now().replace(second=3).replace(microsecond=0) + timedelta(minutes=1)
        while self.pursue:
            if next_time <= datetime.now():
                # TODO à enlever si le programme ne plante plus
                print("--- start precision", datetime.now().replace(microsecond=0))
                self.iter_cibles()
                # TODO à enlever si le programme ne plante plus
                print("--- end precision", datetime.now().replace(microsecond=0))
                next_time = datetime.now().replace(second=3).replace(microsecond=0) + timedelta(minutes=1)
            sleep(3)

    def iter_cibles(self):
        for i, row in self.cibles.iterrows():
            type_cible, nom, id_forum = row

            if type_cible == "Joueur":
                ComparerTdc(nom, id_forum).start()

            elif type_cible == "Alliance":
                for membre in get_list_joueurs_dans_alliance(nom):
                    ComparerTdc(membre, id_forum).start()

    def stop(self):
        self.pursue = False

    def __str__(self):
        return "Tracker de précision"


class ComparerTdc(Thread):
    def __init__(self, pseudo, forum_id):
        Thread.__init__(self)
        self.pseudo = pseudo
        self.forum_id = forum_id
        self.url = "http://" + get_serveur() + ".fourmizzz.fr/Membre.php?Pseudo=" + self.pseudo
        self.path = "tracker/pseudo_temp/tdc_" + self.pseudo

    def run(self):
        with open(self.path, "r") as file:
            old_tdc = int(file.readline().strip())
        new_tdc = self.scrap_tdc()

        if old_tdc != new_tdc:
            diff = new_tdc - old_tdc
            alliance = get_alliance(self.pseudo)
            message = datetime.now().strftime("%m/%d/%Y %H:%M") + " (Temps exact)\n\n"
            message += ("[player]{}[/player]({}): {} -> {} ({})\n\n"
                        .format(self.pseudo,
                                "[ally]{}[/ally]".format(alliance) if alliance is not None else "SA",
                                '{:,}'.format(old_tdc).replace(",", " "),
                                '{:,}'.format(new_tdc).replace(",", " "),
                                ("+" if diff > 0 else "") + '{:,}'.format(diff).replace(",", " ")))

            message += "Calcul de la correspondance en cours..."

            PostForum(message, self.forum_id, self.pseudo).start()

    def scrap_tdc(self):
        cookies = {'PHPSESSID': get_identifiants()[-1]}
        r = requests.get(self.url, cookies=cookies)
        soup = BeautifulSoup(r.text, "html.parser")
        tdc = soup.find("table", {"class": "tableau_score"}).find_all("tr")[1].find_all("td")[1].text.replace(" ", "")
        with open(self.path, "w+") as file:
            file.write(tdc)
        return int(tdc)
