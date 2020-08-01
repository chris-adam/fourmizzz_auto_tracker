from threading import Thread
import os
from datetime import datetime, timedelta
from time import time, sleep

import pandas as pd
import requests
from bs4 import BeautifulSoup

from data import get_serveur
from web import get_list_joueurs_dans_alliance, PostForum

N_PAGES = 30
COLUMNS = ("Pseudo", "Tdc", "Fourmilière", "Technologie", "Trophées", "Alliance")


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
                print("start", datetime.now())
                next_time += timedelta(minutes=1)
                iter_correspondances(compare(), self.cibles)
            sleep(3)

    def stop(self):
        self.pursue = False

    def __str__(self):
        return "Tracker"


class TdcSaver(Thread):
    def __init__(self, page):
        Thread.__init__(self)
        self.page = str(page)
        self.url = "http://" + get_serveur() + ".fourmizzz.fr/classement2.php?page=" \
                   + self.page + "&typeClassement=terrain"

    def run(self):
        cookies = {"PHPSESSID": "qvhl5m23chghgo36tgs6brc6v4"}
        r = requests.get(self.url, cookies=cookies)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", {"class": "tab_triable"})
        df = pd.DataFrame(columns=list(range(6)))
        for row in table.find_all("tr")[1:]:
            elems = row.find_all("td")
            elems = {i: elem for i, elem in enumerate(elems)}
            if len(elems[1].find_all("a")) == 2:
                pseudo, alliance = elems[1].find_all("a")
                elems[1] = pseudo
                elems[len(elems)] = alliance
            df = df.append(pd.DataFrame({i: [elem.text] for i, elem in elems.items()}, index=[0]), ignore_index=True)

        df.drop(0, axis=1, inplace=True)
        df.dropna(axis=1, inplace=True)
        if len(df.columns) == 5:
            df = pd.concat([df, pd.DataFrame(columns=["Alliance"])])
        df.columns = COLUMNS
        df["Tdc"] = [int(tdc.replace(" ", "")) for tdc in df["Tdc"]]
        df.to_pickle("tracker/tdc_temp/tdc_" + self.page)


def scrap_tdc():
    tdc_saver_lst = [TdcSaver(i) for i in range(1, N_PAGES+1)]
    for tdc_saver in tdc_saver_lst:
        tdc_saver.start()
    for i, tdc_saver in enumerate(tdc_saver_lst):
        tdc_saver.join()


def compare():
    if not os.path.exists("tracker/tdc_temp/tdc_" + str(N_PAGES)):
        scrap_tdc()

    releve_1 = merge_files()
    releve_1 = pd.DataFrame({row[0]: [row[1]] for index, row in releve_1.loc[:, ["Pseudo", "Tdc"]].iterrows()})
    date = os.path.getmtime("tracker/tdc_temp/tdc_1")
    date = datetime.fromtimestamp(date).replace(microsecond=0)
    releve_1 = pd.concat([pd.DataFrame(dict(Date=[date])), releve_1], axis=1)

    scrap_tdc()
    releve_2 = merge_files()
    releve_2 = pd.DataFrame({row[0]: [row[1]] for index, row in releve_2.loc[:, ["Pseudo", "Tdc"]].iterrows()})
    releve_2 = pd.concat([pd.DataFrame(dict(Date=[datetime.now().replace(microsecond=0)])), releve_2], axis=1)

    df = pd.concat([releve_1, releve_2], axis=0, ignore_index=True)
    df = df.dropna(axis=1)
    df = df.loc[:, (df != df.iloc[0]).any()]

    return df


def merge_files():
    df = pd.DataFrame(columns=COLUMNS)
    for page in range(1, N_PAGES+1):
        df = df.append(pd.read_pickle("tracker/tdc_temp/tdc_" + str(page)), ignore_index=True)

    return df


def trouver_correspondance(comparaison, pseudo):
    if pseudo not in comparaison.columns:
        return ""

    diff = comparaison.at[comparaison.index[1], pseudo] - comparaison.at[comparaison.index[0], pseudo]
    correspondances = list()
    for col in comparaison.loc[:, comparaison.columns != pseudo].columns[1:]:
        if comparaison.at[comparaison.index[1], col] - comparaison.at[comparaison.index[0], col] == -diff:
            correspondances.append(col)

    resultat = (pseudo + ": " + '{:,}'.format(comparaison.at[comparaison.index[0], pseudo]).replace(",", " ")
                + " -> " + '{:,}'.format(comparaison.at[comparaison.index[1], pseudo])).replace(",", " ") + "\n\n"

    if len(correspondances) == 0:
        resultat += "Aucune correspondance trouvée. Le mouvement de tdc est une chasse, ou le joueur correspondant " \
                    "est trop bas en tdc, ou plusieurs floods se sont croisés et le traçage est trop complexe."
    else:
        for correspondance in correspondances:
            resultat += (correspondance + ": "
                         + '{:,}'.format(comparaison.at[comparaison.index[0], correspondance]).replace(",", " ")
                         + " -> "
                         + '{:,}'.format(comparaison.at[comparaison.index[1], correspondance])).replace(",", " ") + "\n"

    return resultat


def iter_correspondances(res, cibles):
    for i, row in cibles.iterrows():
        type_cible, nom, id_forum = row

        if type_cible == "Joueur":
            message = trouver_correspondance(res, nom)
            if message != "":
                PostForum(message, "forum"+id_forum, nom).start()

        elif type_cible == "Alliance":
            for membre in get_list_joueurs_dans_alliance(nom):
                message = trouver_correspondance(res, membre)
                if message != "":
                    PostForum(message, id_forum, membre).start()
