from time import sleep

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
import requests
from bs4 import BeautifulSoup
import pandas as pd

from data import *


def wait_for_elem(driver, elem, by, tps=15, n_essais=5):
    for i in range(n_essais):
        try:
            return WebDriverWait(driver, tps).until(ec.presence_of_element_located((by, elem)))
        except StaleElementReferenceException:
            sleep(5)


def verifier_connexion():
    url = "http://" + get_serveur() + ".fourmizzz.fr"

    try:
        pseudo, mdp = get_identifiants()
    except FileNotFoundError:
        return False

    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)

        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[2]/td[2]/input", By.XPATH).click()
        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[2]/td[2]/input", By.XPATH).send_keys(pseudo)

        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[3]/td[2]/input", By.XPATH).click()
        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[3]/td[2]/input", By.XPATH).send_keys(mdp)

        wait_for_elem(driver, "//*[@id='loginForm']/input[2]", By.XPATH).click()

        sleep(30)
        wait_for_elem(driver, "/html/body/div[4]/table[2]/tbody/tr[1]/td[4]/form/table/tbody/tr/td[2]/div/input",
                      By.XPATH, tps=3, n_essais=1)
    except TimeoutException:
        return False
    finally:
        driver.close()
        driver.quit()

    return True


def get_driver():
    url = "http://" + get_serveur() + ".fourmizzz.fr"
    pseudo, mdp = get_identifiants()

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    driver.add_cookie({'name': "PHPSESSID", 'value': get_identifiants()[-1]})

    wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[2]/td[2]/input", By.XPATH).click()
    wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[2]/td[2]/input", By.XPATH).send_keys(pseudo)

    wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[3]/td[2]/input", By.XPATH).click()
    wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[3]/td[2]/input", By.XPATH).send_keys(mdp)

    wait_for_elem(driver, "//*[@id='loginForm']/input[2]", By.XPATH).click()

    return driver


def post_forum(string, forum_id, sub_forum_name):
    """
    Post a message on the fourmizzz forum
    :param string: string to post
    :param forum_id: id of the forum to click first
    :param sub_forum_name: name of the forum in which to post
    :return: None
    """

    url = "http://s1.fourmizzz.fr/alliance.php?forum_menu"

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        driver.add_cookie({'name': "PHPSESSID", 'value': get_identifiants()[-1]})
        driver.get(url)

        # Click on the forum name
        wait_for_elem(driver, forum_id, By.CLASS_NAME).click()
        # Click on the subject inside the forum
        wait_for_elem(driver, sub_forum_name, By.LINK_TEXT).click()
        # Click to open answer form
        sleep(5)
        wait_for_elem(driver, "span[style='position:relative;top:-5px", By.CSS_SELECTOR).click()
        # Enter text in the form
        wait_for_elem(driver, "message", By.ID).click()
        driver.find_element_by_id("message").send_keys(string)
        # Click to send the message on the forum
        driver.find_element_by_id("repondre_focus").click()
    finally:
        driver.close()
        driver.quit()


def get_list_joueurs_dans_alliance(tag):
    url = "http://" + get_serveur() + ".fourmizzz.fr/classementAlliance.php?alliance=" + tag
    cookies = {'PHPSESSID': get_identifiants()[-1]}
    r = requests.get(url, cookies=cookies)
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find(id="tabMembresAlliance")
    rows = table.find_all("tr")

    titles = ["Num", "Rank", "Pseudo", "Hf", "Tech", "Fourm"]
    releve = pd.DataFrame(columns=titles)
    for row in rows:
        lst = []
        for cell in row.find_all("td"):
            for sub_cell in cell:
                lst.append(sub_cell)
        if len(lst) == len(titles):
            releve = releve.append(pd.DataFrame({i: [a] for i, a in zip(titles, lst)}))

    return list(pseudo.text for pseudo in releve["Pseudo"])
