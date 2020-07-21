import pandas as pd
from selenium.webdriver.common.by import By

from data import get_serveur
from web import wait_for_elem, get_driver


def tdc():
    url = "http://" + get_serveur() + ".fourmizzz.fr/classement.php?page=1&typeClassement=terrain"

    try:
        driver = get_driver()
        driver.get(url)

        df = pd.DataFrame(columns=["pseudo", "tdc"])

        for i in range(2, 202):
            pseudo = wait_for_elem(driver,
                                   "//*[@id='centre']/table/tbody/tr/td/center/table/tbody/tr[" + str(i) + "]/td[3]/a",
                                   By.XPATH).text
            tdc = wait_for_elem(driver,
                                "//*[@id='centre']/table/tbody/tr/td/center/table/tbody/tr[" + str(i) + "]/td[4]",
                                By.XPATH).text
            tdc = int(tdc.replace(" ", ""))
            df = df.append(pd.DataFrame(dict(pseudo=pseudo, tdc=tdc), index=[0]), ignore_index=True)
    finally:
        driver.close()
        driver.quit()

    return df
