from threading import Thread

import pandas as pd
import requests
from bs4 import BeautifulSoup

from data import get_serveur

N_PAGES = 30


class TdcSaver(Thread):
    def __init__(self, page):
        Thread.__init__(self)
        self.page = str(page)
        self.url = "http://" + get_serveur() + ".fourmizzz.fr/classement.php?page=" \
                   + self.page + "&typeClassement=terrain"

    def run(self):
        cookies = {"PHPSESSID": "qvhl5m23chghgo36tgs6brc6v4"}
        r = requests.get(self.url, cookies=cookies)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", {"class": "tab_triable"})
        df = pd.DataFrame(columns=["pseudo", "tdc"])
        for row in table.find_all("tr")[1:]:
            df = df.append(pd.DataFrame({i: elem.text for i, elem in enumerate(row.find_all("td"))}, index=[0]),
                           ignore_index=True)

        df.drop(0, axis=1, inplace=True)
        df.dropna(axis=1, inplace=True)
        df.columns = ["Alliance", "Pseudo", "Tdc"]
        df.to_pickle("tracker/tdc_temp/tdc_" + self.page)


def tdc():
    tdc_saver_lst = [TdcSaver(i) for i in range(1, N_PAGES+1)]
    for tdc_saver in tdc_saver_lst:
        tdc_saver.start()
    for i, tdc_saver in enumerate(tdc_saver_lst):
        tdc_saver.join()

    df = pd.DataFrame(columns=["Alliance", "Pseudo", "Tdc"])
    for page in range(1, N_PAGES+1):
        df = df.append(pd.read_pickle("tracker/tdc_temp/tdc_" + str(page)), ignore_index=True)

    return df

