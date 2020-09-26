import os
from datetime import datetime, timedelta
from threading import Thread
from time import sleep
import logging as lg
import pickle

import pandas as pd
import requests
from bs4 import BeautifulSoup

from data import get_serveur, get_identifiants
from web import PostForum, get_alliance

N_PAGES = 50
COLUMNS = ("Pseudo", "Tdc", "Fourmilière", "Technologie", "Trophées", "Alliance")


class TrackerLoop(Thread):
    def __init__(self):
        Thread.__init__(self)
        if not os.path.exists("fichiers/cibles"):
            pd.DataFrame(columns=["Type", "Nom", "ID forum"]).to_pickle("fichiers/cibles")
        self.pursue = True

    def run(self):
        next_time = datetime.now().replace(second=5).replace(microsecond=0) + timedelta(minutes=1)
        while self.pursue:
            if next_time <= datetime.now():
                lg.info("Start classement")
                comp = compare()
                if len(comp.columns) > 1:
                    iter_correspondances(comp)
                lg.info("End classement")
                next_time = datetime.now().replace(second=5).replace(microsecond=0) + timedelta(minutes=1)
            sleep(3)

    def stop(self):
        self.pursue = False

    def __str__(self):
        return "Tracker de classement"


class TdcSaver(Thread):
    def __init__(self, page):
        Thread.__init__(self)
        self.page = str(page)
        self.url = "http://" + get_serveur() + ".fourmizzz.fr/classement2.php?page=" \
                   + self.page + "&typeClassement=terrain"

    def run(self):
        cookies = {"PHPSESSID": get_identifiants()[-1]}
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


def trouver_correspondance(comparaison, mouvement):
    # Vérifie que le mouvement est présent dans l'analyse du classement
    if mouvement["Pseudo"] not in comparaison.columns:
        # Si ça fait plus de deux minutes que le mouvement est dans la queue, c'est pas normal
        delta_t = datetime.now() - mouvement["Date"]
        if delta_t > timedelta(minutes=2):
            lg.warning("Le mouvement \"{}\" n'apparait pas dans l'analyse du classement".format(mouvement))
        return ""

    # Prépare la première partie du message concernant la cible surveillée (date + variation de tdc)
    diff = mouvement["Tdc après"] - mouvement["Tdc avant"]
    pseudo_alliance = get_alliance(mouvement["Pseudo"])
    message = "Heure exacte: {}\n\n".format(mouvement["Date"].strftime("%d/%m/%Y %H:%M"))
    message += ("[player]{}[/player]({}): {} -> {} ({})\n\n"
                .format(mouvement["Pseudo"],
                        "[ally]{}[/ally]".format(pseudo_alliance) if pseudo_alliance is not None else "SA",
                        '{:,}'.format(mouvement["Tdc avant"]).replace(",", " "),
                        '{:,}'.format(mouvement["Tdc après"]).replace(",", " "),
                        ("+" if diff > 0 else "") + '{:,}'.format(diff).replace(",", " ")))

    # Cherche les correspondances dans le classement
    correspondances = list()
    for col in comparaison.loc[:, comparaison.columns != mouvement["Pseudo"]].columns[1:]:
        if comparaison.at[comparaison.index[1], col] - comparaison.at[comparaison.index[0], col] == -diff:
            correspondances.append(col)

    # Parfois, rien n'est trouvé: chasse, croisement de floods, échange C+, etc.
    if len(correspondances) == 0:
        message += "Aucune correspondance trouvée."
    # Complète le message avec la ou les correspondances possibles
    else:
        for correspondance in correspondances:
            correspondance_alliance = get_alliance(correspondance)
            message += ("[player]{}[/player]({}): {} -> {} ({})\n"
                        .format(correspondance,
                                "[ally]{}[/ally]".format(correspondance_alliance)
                                if correspondance_alliance is not None else "SA",
                                '{:,}'.format(comparaison.at[comparaison.index[0], correspondance]).replace(",", " "),
                                '{:,}'.format(comparaison.at[comparaison.index[1], correspondance]).replace(",", " "),
                                ("" if diff > 0 else "+") + '{:,}'.format(-diff).replace(",", " ")))

    # Supprime le mouvement de la queue pour qu'il ne soit plus analysé
    try:
        os.remove(mouvement["File name"])
    except Exception as e:
        lg.error("{}: Le mouvement \"{}\" n'a pas pu être supprimé de la queue".format(e, mouvement))

    # Renvoie le message décrivant le traçage de la cible
    return message


def iter_correspondances(comparaison):
    folder = "tracker/queue/"
    queue = list()
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            with open(file_path, "rb") as file:
                queue_elem = pickle.load(file)
        except Exception as e:
            lg.error('Failed to read {}. Reason: {}'.format(file_path, e))
        else:
            queue_elem["File name"] = file_path
            queue.append(queue_elem)

    cibles = pd.read_pickle("fichiers/cibles").set_index("Nom")

    for mouvement in queue:
        message = trouver_correspondance(comparaison, mouvement)
        try:
            id_forum = cibles.at[mouvement["Pseudo"], "ID forum"]
        except KeyError:
            alliance = get_alliance(mouvement["Pseudo"])
            id_forum = cibles.at[alliance, "ID forum"]
        if message != "":
            PostForum(message, id_forum, mouvement["Pseudo"]).start()
            lg.info("Mouvement de tdc posté sur le forum:\n{}".format(message))
