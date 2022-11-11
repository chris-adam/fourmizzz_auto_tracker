import itertools
import logging as lg
import os
import pickle
import sys
from datetime import datetime, timedelta
from threading import Thread
from time import sleep

import pandas as pd
import requests
from bs4 import BeautifulSoup

from data import get_serveur, get_identifiants
from web import PostForum, get_alliance
# import tui

N_PAGES = 40
COLUMNS = ("Pseudo", "Tdc", "Fourmilière", "Technologie", "Trophées", "Alliance")


class TrackerLoop(Thread):
    def __init__(self):
        Thread.__init__(self)
        if not os.path.exists("fichiers/cibles"):
            pd.DataFrame(columns=["Type", "Nom", "ID forum"]).to_pickle("fichiers/cibles")
        self.pursue = True
        self.post_forum_thread = PostForum()

    def run(self):
        self.post_forum_thread.start()
        next_time = datetime.now().replace(second=10, microsecond=0) + timedelta(minutes=1)
        while self.pursue:
            if next_time <= datetime.now():
                lg.info("Début " + str(self))
                comp_tdc, comp_trophees = compare()

                # Tdc
                if len(comp_tdc.columns) > 1 and len(os.listdir("tracker/queue/")) > 0:
                    processed_comp_tdc = self.process_comparison(comp_tdc)
                    msg_lst = iter_correspondances(processed_comp_tdc)
                    self.post_forum_thread.extend_queue(msg_lst)

                # Trophées
                if len(comp_trophees.columns) > 1 and len(os.listdir("tracker/queue_trophees/")) > 0:
                    processed_comp_trophees = self.process_comparison(comp_trophees)
                    msg_lst = iter_correspondances_trophees(processed_comp_trophees)
                    self.post_forum_thread.extend_queue(msg_lst)

                lg.info("Fin " + str(self))
                next_time = datetime.now().replace(second=10, microsecond=0) + timedelta(minutes=1)
            sleep(3)

            if not self.post_forum_thread.is_alive():
                self.post_forum_thread = PostForum(self.post_forum_thread.queue)
                self.post_forum_thread.start()

        self.post_forum_thread.stop()
        self.post_forum_thread.join()

    @classmethod
    def process_comparison(cls, comparison_df):
        comparison = comparison_df.iloc[1, 1:] - comparison_df.iloc[0, 1:]
        processed_comp = {None: dict()}
        r = 2
        while r <= len(comparison) and r < 5:
            for perm_index in itertools.combinations(comparison.index, r):
                perm = comparison.loc[list(perm_index)]
                if sum(perm) == 0:
                    move_dict = dict()
                    for player in perm.index:
                        move_dict[player] = (comparison_df.loc[comparison_df.index[0], player],
                                             comparison_df.loc[comparison_df.index[1], player])

                    comparison = comparison.drop(perm.index)
                    processed_comp.update(**{player: move_dict for player in perm.index})
                    r = 1
                    break
            r += 1

        if len(comparison) > 0:
            for player in comparison.index:
                processed_comp[None][player] = (comparison_df.loc[comparison_df.index[0], player],
                                                comparison_df.loc[comparison_df.index[1], player])

        return processed_comp

    def stop(self):
        self.pursue = False

    def __str__(self):
        return "Traqueur de classement"


class TdcSaver(Thread):
    def __init__(self, page):
        Thread.__init__(self)
        self.page = str(page)
        self.url = "http://" + get_serveur() + ".fourmizzz.fr/classement2.php?page=" \
                   + self.page + "&typeClassement=terrain"

    def run(self):
        cookies = {"PHPSESSID": get_identifiants()[-1]}
        try:
            r = requests.get(self.url, cookies=cookies)
        except requests.exceptions.ConnectionError:
            lg.error("Erreur lors de l'ouverture de la page {} du classement".format(self.page))
            sys.exit()

        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", {"class": "tab_triable"})
        df = pd.DataFrame(columns=list(range(6)))

        row_lst = None
        while row_lst is None:
            try:
                row_lst = table.find_all("tr")[1:]
            except AttributeError:
                print("Error for {}".format(self.url))
                # tui.connexion()
                raise
        for row in row_lst:
            elems = row.find_all("td")
            elems = {i: elem for i, elem in enumerate(elems)}
            if len(elems[1].find_all("a")) == 2:
                pseudo, alliance = elems[1].find_all("a")
                elems[1] = pseudo
                elems[len(elems)] = alliance

            df = pd.concat([df, pd.DataFrame({i: [elem.text] for i, elem in elems.items()}, index=[0])],
                           ignore_index=True)

        df.drop(0, axis=1, inplace=True)
        df.dropna(axis=1, inplace=True)
        if len(df.columns) == 5:
            df = pd.concat([df, pd.DataFrame(columns=["Alliance"])])
        df.columns = COLUMNS
        df["Tdc"] = [int(tdc.replace(" ", "")) for tdc in df["Tdc"]]
        df["Trophées"] = [int(tdc.replace(" ", "")) for tdc in df["Trophées"]]
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
        return pd.DataFrame(dict(Date=[datetime.now()])), pd.DataFrame(dict(Date=[datetime.now()]))

    # df pour le tdc
    releve_1 = merge_files()
    releve_1_tdc = pd.DataFrame({row[0]: [row[1]] for index, row in releve_1.loc[:, ["Pseudo", "Tdc", "Trophées"]].iterrows()})
    date = os.path.getmtime("tracker/tdc_temp/tdc_1")
    date = datetime.fromtimestamp(date).replace(microsecond=0)
    releve_1_tdc = pd.concat([pd.DataFrame(dict(Date=[date])), releve_1_tdc], axis=1)

    scrap_tdc()
    releve_2 = merge_files()
    releve_2_tdc = pd.DataFrame({row[0]: [row[1]] for index, row in releve_2.loc[:, ["Pseudo", "Tdc", "Trophées"]].iterrows()})
    releve_2_tdc = pd.concat([pd.DataFrame(dict(Date=[datetime.now().replace(microsecond=0)])), releve_2_tdc], axis=1)

    df_tdc = pd.concat([releve_1_tdc, releve_2_tdc], axis=0, ignore_index=True)
    df_tdc = df_tdc.dropna(axis=1)
    df_tdc = df_tdc.loc[:, (df_tdc != df_tdc.iloc[0]).any()]

    # df pour les trophées
    releve_1_trophees = pd.DataFrame({row[0]: [row[1]] for index, row in releve_1.loc[:, ["Pseudo", "Trophées"]].iterrows()})
    releve_1_trophees = pd.concat([pd.DataFrame(dict(Date=[date])), releve_1_trophees], axis=1)

    releve_2_trophees = pd.DataFrame({row[0]: [row[1]] for index, row in releve_2.loc[:, ["Pseudo", "Trophées"]].iterrows()})
    releve_2_trophees = pd.concat([pd.DataFrame(dict(Date=[datetime.now().replace(microsecond=0)])), releve_2_trophees], axis=1)

    df_trophees = pd.concat([releve_1_trophees, releve_2_trophees], axis=0, ignore_index=True)
    df_trophees = df_trophees.dropna(axis=1)
    df_trophees = df_trophees.loc[:, (df_trophees != df_trophees.iloc[0]).any()]

    return df_tdc, df_trophees


def merge_files():
    df = pd.DataFrame(columns=COLUMNS)
    for page in range(1, N_PAGES+1):
        df = pd.concat([df, pd.read_pickle("tracker/tdc_temp/tdc_" + str(page))], ignore_index=True)

    return df


def trouver_correspondance(comparaison, mouvements):
    # Vérifie que le mouvement est présent dans l'analyse du classement
    pseudo = mouvements[0]["Pseudo"]
    if pseudo not in comparaison:
        clef = None
        if pseudo not in comparaison[clef]:
            return
    else:
        clef = pseudo

    # Prépare la première partie du message concernant la cible surveillée (date + variation de tdc)
    message = ""
    mouvements = sorted(mouvements, key=lambda x: x["Date"])
    for mouvement in mouvements:
        diff = mouvement["Tdc après"] - mouvement["Tdc avant"]
        pseudo_alliance = get_alliance(mouvement["Pseudo"])
        message += ("[b]Tdc[/b] {}\n[player]{}[/player]({}): {} -> {} ({})\n"
                    .format(mouvement["Date"].strftime("%d/%m/%Y %H:%M"),
                            mouvement["Pseudo"],
                            "[ally]{}[/ally]".format(pseudo_alliance) if pseudo_alliance is not None else "SA",
                            '{:,}'.format(mouvement["Tdc avant"]).replace(",", " "),
                            '{:,}'.format(mouvement["Tdc après"]).replace(",", " "),
                            ("+" if diff > 0 else "") + '{:,}'.format(diff).replace(",", " ")))

    message += "\n"
    # Parfois, rien n'est trouvé: chasse, échange C+, etc.
    if clef is None:
        message += "Aucune correspondance trouvée.\n"
        if len(comparaison[None]) > 1:
            message += "Les autres mouvements orphelins sont:\n"
    # Complète le message avec la ou les correspondances possibles
    for correspondance, tdc in comparaison[clef].items():
        if correspondance == pseudo:
            continue
        corresp_alliance = get_alliance(correspondance)
        corresp_diff = tdc[1] - tdc[0]
        message += ("[player]{}[/player]({}): {} -> {} ({})\n"
                    .format(correspondance,
                            "[ally]{}[/ally]".format(corresp_alliance)
                            if corresp_alliance is not None else "SA",
                            '{:,}'.format(tdc[0]).replace(",", " "),
                            '{:,}'.format(tdc[1]).replace(",", " "),
                            ("" if corresp_diff < 0 else "+") + '{:,}'.format(corresp_diff).replace(",", " ")))

    # Supprime les mouvements de la queue pour qu'ils ne soient plus analysés
    for mouvement in mouvements:
        file_name = mouvement["File name"]
        try:
            os.remove(file_name)
        except Exception as e:
            lg.error("{}: Le mouvement de tdc \"{}\" n'a pas pu être supprimé de la queue (fichier: {})"
                     .format(e, mouvement, file_name))

    # Renvoie le message décrivant le traçage de la cible
    return message


def iter_correspondances(comparaison):
    # Récupère la queue
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
            queue.append(queue_elem)

    # Fusionne les records des mêmes joueurs pour prendre en compte les floods fait sur plusieurs minutes
    dict_mouvements = dict()
    for mouvement in queue:
        if mouvement["Pseudo"] in dict_mouvements:
            dict_mouvements[mouvement["Pseudo"]].append(mouvement)
        else:
            dict_mouvements[mouvement["Pseudo"]] = [mouvement]

    # Récupère les cibles
    cibles = pd.read_pickle("fichiers/cibles").set_index("Nom")

    # Trouve les correspondances pour tous les éléments dans la queue
    to_be_posted = list()
    for joueur, mouvements in dict_mouvements.items():
        message = trouver_correspondance(comparaison, mouvements)
        try:
            id_forum = cibles.at[joueur, "ID forum"]
        except KeyError:
            alliance = get_alliance(joueur)
            id_forum = cibles.at[alliance, "ID forum"]
        if message is not None:
            to_be_posted.append((message, id_forum, joueur))

    return to_be_posted


def trouver_correspondance_trophees(comparaison, mouvements):
    # Vérifie que le mouvement est présent dans l'analyse du classement
    pseudo = mouvements[0]["Pseudo"]
    if pseudo not in comparaison:
        clef = None
        if pseudo not in comparaison[clef]:
            return
    else:
        clef = pseudo

    # Prépare la première partie du message concernant la cible surveillée (date + variation de tdc)
    message = ""
    mouvements = sorted(mouvements, key=lambda x: x["Date"])
    for mouvement in mouvements:
        diff = mouvement["Trophees après"] - mouvement["Trophees avant"]
        pseudo_alliance = get_alliance(mouvement["Pseudo"])
        message += ("[color=#c5130f][b]Trophées[/b][/color] {}\n[player]{}[/player]({}): {} -> {} ({})\n"
                    .format(mouvement["Date"].strftime("%d/%m/%Y %H:%M"),
                            mouvement["Pseudo"],
                            "[ally]{}[/ally]".format(pseudo_alliance) if pseudo_alliance is not None else "SA",
                            '{:,}'.format(mouvement["Trophees avant"]).replace(",", " "),
                            '{:,}'.format(mouvement["Trophees après"]).replace(",", " "),
                            ("+" if diff > 0 else "") + '{:,}'.format(diff).replace(",", " ")))

    message += "\n"
    # Parfois, rien n'est trouvé: chasse, échange C+, etc.
    if clef is None:
        message += "Aucune correspondance trouvée.\n"
        if len(comparaison[None]) > 1:
            message += "Les autres mouvements orphelins sont:\n"
    # Complète le message avec la ou les correspondances possibles
    for correspondance, trophees in comparaison[clef].items():
        if correspondance == pseudo:
            continue
        corresp_alliance = get_alliance(correspondance)
        corresp_diff = trophees[1] - trophees[0]
        message += ("[player]{}[/player]({}): {} -> {} ({})\n"
                    .format(correspondance,
                            "[ally]{}[/ally]".format(corresp_alliance)
                            if corresp_alliance is not None else "SA",
                            '{:,}'.format(trophees[0]).replace(",", " "),
                            '{:,}'.format(trophees[1]).replace(",", " "),
                            ("" if corresp_diff < 0 else "+") + '{:,}'.format(corresp_diff).replace(",", " ")))

    # Supprime les mouvements de la queue pour qu'ils ne soient plus analysés
    for mouvement in mouvements:
        file_name = mouvement["File name"]
        try:
            os.remove(file_name)
        except Exception as e:
            lg.error("{}: Le mouvement de trophées \"{}\" n'a pas pu être supprimé de la queue (fichier: {})"
                     .format(e, mouvement, file_name))

    # Renvoie le message décrivant le traçage de la cible
    return message


def iter_correspondances_trophees(comparaison):
    # Récupère la queue
    folder = "tracker/queue_trophees/"
    queue = list()
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            with open(file_path, "rb") as file:
                queue_elem = pickle.load(file)
        except Exception as e:
            lg.error('Failed to read {}. Reason: {}'.format(file_path, e))
        else:
            queue.append(queue_elem)

    # Fusionne les records des mêmes joueurs pour prendre en compte les floods fait sur plusieurs minutes
    dict_mouvements = dict()
    for mouvement in queue:
        if mouvement["Pseudo"] in dict_mouvements:
            dict_mouvements[mouvement["Pseudo"]].append(mouvement)
        else:
            dict_mouvements[mouvement["Pseudo"]] = [mouvement]

    # Récupère les cibles
    cibles = pd.read_pickle("fichiers/cibles").set_index("Nom")

    # Trouve les correspondances pour tous les éléments dans la queue
    to_be_posted = list()
    for joueur, mouvements in dict_mouvements.items():
        message = trouver_correspondance_trophees(comparaison, mouvements)
        try:
            id_forum = cibles.at[joueur, "ID forum"]
        except KeyError:
            alliance = get_alliance(joueur)
            id_forum = cibles.at[alliance, "ID forum"]
        if message is not None:
            to_be_posted.append((message, id_forum, joueur))

    return to_be_posted
