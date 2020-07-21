from time import sleep

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

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
    options.add_argument('--headless')
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)

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
