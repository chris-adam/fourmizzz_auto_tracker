import logging as lg
from threading import Thread
from time import sleep

import pandas as pd
import requests
from boltons import iterutils
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException, \
    ElementNotInteractableException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

import data
from data import *


def wait_for_elem(driver, elem, by, tps=5, n_essais=5):
    for i in range(n_essais):
        try:
            return WebDriverWait(driver, tps).until(ec.presence_of_element_located((by, elem)))
        except (StaleElementReferenceException, TimeoutException):
            sleep(2)
    raise TimeoutException()


def verifier_connexion():
    url = "http://" + get_serveur() + ".fourmizzz.fr"

    try:
        pseudo, mdp, cookie_token = get_identifiants()
    except FileNotFoundError:
        return False

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    try:
        driver = webdriver.Chrome(options=options)
    except OSError:
        driver = webdriver.Chrome("/usr/lib/chromium-browser/chromedriver", options=options)

    try:
        driver.get(url)
        driver.add_cookie({'name': "PHPSESSID", 'value': cookie_token})

        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[2]/td[2]/input", By.XPATH).click()
        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[2]/td[2]/input", By.XPATH).send_keys(pseudo)

        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[3]/td[2]/input", By.XPATH).click()
        wait_for_elem(driver, "//*[@id='loginForm']/table/tbody/tr[3]/td[2]/input", By.XPATH).send_keys(mdp)

        wait_for_elem(driver, "//*[@id='loginForm']/input[2]", By.XPATH).click()

        wait_for_elem(driver, "/html/body/div[4]/table/tbody/tr[1]/td[4]/form/table/tbody/tr/td[1]/div[1]/input",
                      By.XPATH, tps=3, n_essais=1)
    except TimeoutException:
        return False
    finally:
        driver.close()
        driver.quit()

    return True


class PostForum(Thread):
    def __init__(self, queue=None):
        """
        Post a message on the fourmizzz forum
        """
        Thread.__init__(self)
        self.queue = list()
        if queue is not None:
            self.queue.extend(queue)
        self.stopped = False

    def run(self):
        while not self.stopped or len(self.queue) > 0:
            try:
                string, forum_id, sub_forum_name = self.queue.pop(0)
            except IndexError:
                sleep(2)
                continue
            forum_id = "forum" + forum_id

            url = "http://" + get_serveur() + ".fourmizzz.fr/alliance.php?forum_menu"

            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument("--start-maximized")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            try:
                driver = webdriver.Chrome(options=options)
            except OSError:
                driver = webdriver.Chrome("/usr/lib/chromium-browser/chromedriver", options=options)

            try:
                driver.get("http://" + get_serveur() + ".fourmizzz.fr")
                driver.add_cookie({'name': "PHPSESSID", 'value': get_identifiants()[-1]})
                driver.get(url)

                # Click on the forum name
                try:
                    wait_for_elem(driver, forum_id + ".categorie_forum", By.CLASS_NAME).click()
                except TimeoutException:
                    wait_for_elem(driver, forum_id + ".ligne_paire", By.CLASS_NAME).click()
                sleep(1)

                # Find the forum in which the message has to be posted
                i = 2
                while i > 0:
                    try:
                        # If the topic is locked, don't even try
                        if (len(driver.find_elements_by_xpath("//*[@id='form_cat']/table/tbody/tr["
                                                              + str(i) + "]/td[2]/img")) > 0
                                and wait_for_elem(driver, "//*[@id='form_cat']/table/tbody/tr["+str(i)+"]/td[2]/img",
                                                  By.XPATH).get_attribute('alt') == "Fermé"):
                            i += 2
                            continue

                        topic_name = wait_for_elem(driver, "//*[@id='form_cat']/table/tbody/tr[" + str(i) + "]/td[2]/a",
                                                   By.XPATH).text

                        # Click to open the sub forum
                        if topic_name.lower().startswith(sub_forum_name.lower()):
                            topic_name_button = wait_for_elem(driver, "//*[@id='form_cat']/table/tbody/tr["
                                                              + str(i) + "]/td[2]/a", By.XPATH)
                            try:
                                topic_name_button.click()
                            except ElementNotInteractableException:
                                ActionChains(driver).move_to_element(topic_name_button).perform()
                                topic_name_button.click()
                            sleep(5)  # Wait for the page to load, it can be long if there are a lot of messages
                            break

                    # Waits if the element didn't load yet
                    except StaleElementReferenceException:
                        sleep(1)
                    # Go to the next sub forum
                    else:
                        i += 2

                # Click to open answer form
                wait_for_elem(driver, "span[style='position:relative;top:-5px", By.CSS_SELECTOR).click()
                sleep(2)
                # Enter text in the form
                wait_for_elem(driver, "message", By.ID).click()
                for msg in iterutils.chunked(string, 32):
                    driver.find_element_by_id("message").send_keys(msg)
                # Click to send the message on the forum
                driver.find_element_by_id("repondre_focus").click()
                sleep(1)

            except (NoSuchElementException, TimeoutException, ElementClickInterceptedException):
                lg.warning("Forum " + sub_forum_name + " introuvable ou verrouillé\n" + string)
                # Changer "player_name" pour le pseudo du joueur qui doit recevoir les alertes
                # ou le supprimer pour rediriger les alertes vers le compte qui fait tourner le programme
                send_pm(subject="Traçage non posté", player_name="vivi86",
                        text="Forum " + sub_forum_name + " introuvable ou verrouillé\n" + string)
            else:
                lg.info("Mouvement de tdc posté sur le forum:\n{}".format(string))
            finally:
                driver.close()
                driver.quit()

    def extend_queue(self, new_msg):
        self.queue.extend(new_msg)

    def stop(self):
        self.stopped = True


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
            releve = pd.concat([releve, pd.DataFrame({i: [a] for i, a in zip(titles, lst)})])

    return list(pseudo.text for pseudo in releve["Pseudo"])


def get_alliance(pseudo):
    url = "http://" + get_serveur() + ".fourmizzz.fr/Membre.php?Pseudo=" + pseudo
    cookies = {'PHPSESSID': get_identifiants()[-1]}
    r = requests.get(url, cookies=cookies)
    soup = BeautifulSoup(r.text, "html.parser")
    try:
        return soup.find("div", {"class": "boite_membre"}).find("table").find("tr").find_all("td")[1].find("a").text
    except AttributeError:
        return


def send_pm(player_name=None, subject="", text="No text"):
    pseudo, mdp, phpssessid = data.get_identifiants()
    serveur = data.get_serveur()

    if player_name is None:
        player_name = pseudo

    url = "http://" + serveur + ".fourmizzz.fr/messagerie.php?defaut=Ecrire&destinataire=" + player_name
    cookies = {'PHPSESSID': phpssessid}

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        for key, value in cookies.items():
            driver.add_cookie({'name': key, 'value': value})
        driver.get(url)

        # write object
        wait_for_elem(driver, "/html/body/div[4]/div[1]/div[6]/div[1]/div[2]/span/input", By.XPATH, 5).click()
        wait_for_elem(driver, "/html/body/div[4]/div[1]/div[6]/div[1]/div[2]/span/input", By.XPATH, 5)\
            .send_keys(subject)
        sleep(0.5)

        # write main text
        wait_for_elem(driver, "/html/body/div[4]/div[1]/div[6]/div[1]/div[3]/span/textarea", By.XPATH, 5).click()
        wait_for_elem(driver, "/html/body/div[4]/div[1]/div[6]/div[1]/div[3]/span/textarea", By.XPATH, 5)\
            .send_keys(text)
        sleep(0.5)

        # send pm
        wait_for_elem(driver, "/html/body/div[4]/div[1]/div[6]/div[1]/div[4]/span[1]/input", By.XPATH, 50).click()
        sleep(1)
    finally:
        driver.close()
        driver.quit()
