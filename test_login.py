import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from dotenv import load_dotenv
import os
import time

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

url = "https://etrm-greece-dev.stellarblue.eu/Account/Login"


@pytest.fixture(scope="class")
def driver_setup(request):
    driver = webdriver.Chrome()
    driver.maximize_window()
    wait = WebDriverWait(driver, 20)

    request.cls.driver = driver
    request.cls.wait = wait

    yield driver
    driver.quit()


@pytest.mark.usefixtures("driver_setup")
class TestLoginAndDashboardNavigation:
    driver = None
    wait = None

    def test_01_successful_login_and_dashboard_click(self):

        driver = self.driver
        wait = self.wait

        print(f"\nNavigating to {url}")
        driver.get(url)
        wait.until(EC.url_contains("Account/Login"))
        print(" Successfully navigated to login page.")

        print("Attempting to click 'Sign in with Microsoft' button...")
        microsoft_sign_in_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Sign in with Microsoft')]"))
        )
        microsoft_sign_in_button.click()
        print(" Clicked Microsoft sign-in")

        wait.until(EC.url_contains("microsoftonline.com") or EC.url_contains("login.live.com"))
        print("Waiting for email field on Microsoft page...")
        email_field = wait.until(EC.visibility_of_element_located((By.NAME, "loginfmt")))
        email_field.send_keys(EMAIL)
        email_field.send_keys(Keys.ENTER)
        print(f" Entered email: {EMAIL} and pressed ENTER")

        print("Waiting for password field on Microsoft page...")
        password_field = wait.until(EC.visibility_of_element_located((By.NAME, "passwd")))
        password_field.send_keys(PASSWORD)
        print("Entered password")

        signin_button = wait.until(EC.element_to_be_clickable((By.ID, "idSIButton9")))
        signin_button.click()
        print(" Clicked 'Sign In' button after entering password")

        print("Checking for 'Stay signed in?' prompt...")
        try:
            stay_signed_in_yes_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "idSIButton9"))
            )
            if "Keep you signed in?" in driver.page_source or "Stay signed in?" in driver.page_source:
                stay_signed_in_yes_btn.click()
                print(" Clicked 'Yes' on 'Stay signed in?' prompt.")
            else:
                print(" 'Stay signed in?' button found, but prompt text not confirmed. Proceeding.")

        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            print(" 'Stay signed in?' prompt did not appear within timeout. Proceeding.")
        except Exception as e:
            print(f"An unexpected error occurred while handling 'Stay signed in?' prompt: {e}")

        print("Verifying successful login and preparing to click Dashboards...")

        loading_indicators = [
            (By.CSS_SELECTOR, ".spinner-overlay"),
            (By.CSS_SELECTOR, ".loading-indicator"),
            (By.CSS_SELECTOR, ".ngx-loading-mask"),
            (By.XPATH, "//*[contains(@class, 'loading') and contains(@style, 'display: block')]"),
            (By.XPATH, "//*[contains(@class, 'overlay') and contains(@style, 'display: block')]"),
        ]

        for by_type, locator_value in loading_indicators:
            try:
                print(f"Checking for loading indicator: {locator_value}")
                WebDriverWait(driver, 5).until_not(
                    EC.presence_of_element_located((by_type, locator_value))
                )
                print(f" Loading indicator disappeared: {locator_value}")
            except TimeoutException:
                print(f" No active loading indicator found or it disappeared quickly for: {locator_value}")
            except Exception as e:
                print(f" Error while checking for loading indicator {locator_value}: {e}")

        print("Waiting for document to be ready (readyState 'complete')...")
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        print(" Document ready state is 'complete'.")

        print("Waiting for main dashboard content to load and Dashboards link to be present...")
        wait.until(
            EC.url_contains("/Dashboards") or
            EC.presence_of_element_located((By.XPATH, "//span[normalize-space()='Dashboards']"))
        )
        print(" Successfully logged in and dashboard area elements are present.")

        print("Attempting to click 'Dashboards' link using By.XPATH, \"//span[normalize-space()='Dashboards']\"...")
        dashboards_element = None
        try:
            dashboards_span = wait.until(
                EC.presence_of_element_located((By.XPATH, "//span[normalize-space()='Dashboards']"))
            )
            try:
                clickable_parent = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//span[normalize-space()='Dashboards']/ancestor::a[1]"))
                )
                clickable_parent.click()
                print(" Clicked 'Dashboards' link successfully via its parent <a> element.")
                dashboards_element = clickable_parent
            except (TimeoutException, NoSuchElementException):
                print(" No immediate clickable <a> parent found. Attempting to click the span directly.")
                dashboards_element = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//span[normalize-space()='Dashboards']"))
                )
                dashboards_element.click()
                print(" Clicked 'Dashboards' link successfully via direct span click.")

        except Exception as e:
            print(f"Direct/Parent click failed or element not immediately clickable: {e}")
            if dashboards_element:
                print("Attempting to click element using JavaScript fallback...")
                try:
                    driver.execute_script("arguments[0].click();", dashboards_element)
                    print(" Clicked element successfully with JavaScript fallback.")
                except Exception as js_e:
                    print(f" JavaScript click also failed: {js_e}")
                    pytest.fail(f"Failed to click Dashboards link even with JavaScript. Error: {js_e}")
            else:
                pytest.fail(f"Dashboards link element (span or parent) not found. Error: {e}")

        print("Verifying navigation to Dashboards page...")
        wait.until(EC.url_contains("/Dashboards"))
        print(" Successfully navigated to the Dashboards page.")
