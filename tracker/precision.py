import logging as lg
import os
import pickle
from datetime import datetime, timedelta
from threading import Thread
from time import sleep

import pandas as pd
import requests
from bs4 import BeautifulSoup

from data import get_serveur, get_identifiants
from web import get_list_joueurs_dans_alliance


class TrackerLoop(Thread):
    def __init__(self):
        Thread.__init__(self)
        if not os.path.exists("fichiers/cibles"):
            pd.DataFrame(columns=["Type", "Nom", "ID forum"]).to_pickle("fichiers/cibles")
        self.pursue = True

    def run(self):
        next_time = datetime.now().replace(second=3).replace(microsecond=0) + timedelta(minutes=1)
        while self.pursue:
            if next_time <= datetime.now():
                lg.info("Début " + str(self))
                TrackerLoop.iter_cibles()
                lg.info("Fin " + str(self))
                next_time = datetime.now().replace(second=3).replace(microsecond=0) + timedelta(minutes=1)
            sleep(3)

    @classmethod
    def iter_cibles(cls):
        cibles = pd.read_pickle("fichiers/cibles")

        for i, row in cibles.iterrows():
            type_cible, nom, id_forum = row

            if type_cible == "Joueur":
                ComparerTdc(nom, id_forum).start()

            elif type_cible == "Alliance":
                for membre in get_list_joueurs_dans_alliance(nom):
                    ComparerTdc(membre, id_forum).start()

    def stop(self):
        self.pursue = False

    def __str__(self):
        return "Traqueur de précision"


class ComparerTdc(Thread):
    def __init__(self, pseudo, forum_id):
        Thread.__init__(self)
        self.pseudo = pseudo
        self.forum_id = forum_id
        self.url = "http://" + get_serveur() + ".fourmizzz.fr/Membre.php?Pseudo=" + self.pseudo
        self.path = "tracker/pseudo_temp/tdc_" + self.pseudo

    def run(self):
        if not os.path.exists(self.path):
            self.scrap_tdc()

        with open(self.path, "r") as file:
            old_tdc = int(file.readline().strip())
        new_tdc = self.scrap_tdc()

        if old_tdc != new_tdc:
            queue = {"Date": datetime.now(),
                     "Pseudo": self.pseudo,
                     "Tdc avant": old_tdc,
                     "Tdc après": new_tdc,
                     "File name": "tracker/queue/" + datetime.now().strftime("%Y-%m-%d_%Hh%M") + "_" + self.pseudo}
            with open(queue["File name"], "wb+") as file:
                pickle.dump(queue, file)
            lg.info("Ajouté à la queue: {}".format(queue))

    def scrap_tdc(self):
        cookies = {'PHPSESSID': get_identifiants()[-1]}
        r = requests.get(self.url, cookies=cookies)
        soup = BeautifulSoup(r.text, "html.parser")
        tdc = soup.find("table", {"class": "tableau_score"}).find_all("tr")[1].find_all("td")[1].text.replace(" ", "")
        with open(self.path, "w+") as file:
            file.write(tdc)
        return int(tdc)
