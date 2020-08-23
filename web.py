from time import sleep
from threading import Thread
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
import requests
from bs4 import BeautifulSoup
import pandas as pd

from data import *


def wait_for_elem(driver, elem, by, tps=10, n_essais=5):
    for i in range(n_essais):
        try:
            return WebDriverWait(driver, tps).until(ec.presence_of_element_located((by, elem)))
        except StaleElementReferenceException:
            sleep(5)


def verifier_connexion():
    url = "http://" + get_serveur() + ".fourmizzz.fr"

    try:
        pseudo, mdp, cookie_token = get_identifiants()
    except FileNotFoundError:
        return False

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        driver.add_cookie({'name': "PHPSESSID", 'value': cookie_token})

        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[2]/td[2]/input", By.XPATH).click()
        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[2]/td[2]/input", By.XPATH).send_keys(pseudo)

        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[3]/td[2]/input", By.XPATH).click()
        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[3]/td[2]/input", By.XPATH).send_keys(mdp)

        wait_for_elem(driver, "//*[@id='loginForm']/input[2]", By.XPATH).click()

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


class PostForum(Thread):
    def __init__(self, string, forum_id, sub_forum_name):
        """
        Post a message on the fourmizzz forum
        :param string: string to post
        :param forum_id: id of the forum to click first
        :param sub_forum_name: name of the forum in which to post
        :return: None
        """
        Thread.__init__(self)
        self.string = string
        print(self.string)
        self.forum_id = "forum" + forum_id
        self.sub_forum_name = sub_forum_name

    def run(self):

        url = "http://s4.fourmizzz.fr/alliance.php?forum_menu"

        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)
        try:
            driver.get("http://s4.fourmizzz.fr")
            driver.add_cookie({'name': "PHPSESSID", 'value': get_identifiants()[-1]})
            driver.get(url)

            # Click on the forum name
            try:
                wait_for_elem(driver, self.forum_id + ".categorie_forum", By.CLASS_NAME).click()
            except TimeoutException:
                wait_for_elem(driver, self.forum_id + ".ligne_paire", By.CLASS_NAME).click()

            # Find the forum in which the message has to be posted
            i = 2
            while i > 0:
                try:
                    # If the topic is locked, don't even try
                    if (len(driver.find_elements_by_xpath("//*[@id='form_cat']/table/tbody/tr["
                                                          + str(i) + "]/td[2]/img")) > 0
                            and wait_for_elem(driver, "//*[@id='form_cat']/table/tbody/tr["+str(i)+"]/td[2]/img",
                                              By.XPATH, 2).get_attribute('alt') == "Fermé"):
                        i += 2
                        continue

                    topic_name = wait_for_elem(driver, "//*[@id='form_cat']/table/tbody/tr[" + str(i) + "]/td[2]/a",
                                               By.XPATH, 2).text

                    # Click to open the sub forum
                    if topic_name.lower().startswith(self.sub_forum_name.lower()):
                        wait_for_elem(driver, "//*[@id='form_cat']/table/tbody/tr[" + str(i) + "]/td[2]/a",
                                      By.XPATH, 2).click()
                        sleep(5)  # Wait for the page to load
                        break

                # Waits if the element didn't load yet
                except StaleElementReferenceException:
                    print("StaleElementReferenceException")
                    sleep(1)
                # Leave the loop if there is no more sub forum to read
                except TimeoutException:
                    print("Forum", self.sub_forum_name, "introuvable ou verrouillé")
                    print(self.string)
                    break
                # Go to the next sub forum
                else:
                    i += 2

            # Click to open answer form
            wait_for_elem(driver, "span[style='position:relative;top:-5px", By.CSS_SELECTOR).click()
            # Enter text in the form
            sleep(2)
            wait_for_elem(driver, "message", By.ID).click()
            driver.find_element_by_id("message").send_keys(self.string)
            # Click to send the message on the forum
            driver.find_element_by_id("repondre_focus").click()
            sleep(1)
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


def get_alliance(pseudo):
    url = "http://" + get_serveur() + ".fourmizzz.fr/Membre.php?Pseudo=" + pseudo
    cookies = {'PHPSESSID': get_identifiants()[-1]}
    r = requests.get(url, cookies=cookies)
    soup = BeautifulSoup(r.text, "html.parser")
    try:
        # print(soup.prettify())
        return soup.find("div", {"class": "boite_membre"}).find("table").find("tr").find_all("td")[1].find("a").text
    except AttributeError:
        return
