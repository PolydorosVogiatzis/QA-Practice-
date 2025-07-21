import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import os
import time

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

LOGIN_URL = "https://etrm-greece-dev.stellarblue.eu/Account/Login"
DASHBOARD_URL_PART = "/Dashboards"
MICROSOFT_LOGIN_URL_PART_1 = "microsoftonline.com"
MICROSOFT_LOGIN_URL_PART_2 = "login.live.com"

@pytest.fixture(scope="class")
def driver_setup(request):
    chrome_options = Options()
    chrome_options.add_argument('--disable-notifications')
    
    driver = webdriver.Chrome(options=chrome_options)
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

    def _login_to_microsoft(self):
        driver = self.driver
        wait = self.wait

        print(f"\nNavigating to {LOGIN_URL}")
        driver.get(LOGIN_URL)
        wait.until(EC.url_contains("Account/Login"))
        print(" Successfully navigated to login page.")
        assert "Account/Login" in driver.current_url, "Assertion Failed: Not on the expected login page URL."

        print("Attempting to click 'Sign in with Microsoft' button...")
        microsoft_sign_in_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Sign in with Microsoft')]"))
        )
        assert microsoft_sign_in_button.is_displayed() and microsoft_sign_in_button.is_enabled(), \
            "Assertion Failed: Microsoft Sign-in button is not displayed or enabled."
        microsoft_sign_in_button.click()
        print(" Clicked Microsoft sign-in")
        time.sleep(1)

        wait.until(EC.url_contains(MICROSOFT_LOGIN_URL_PART_1) or EC.url_contains(MICROSOFT_LOGIN_URL_PART_2))
        assert MICROSOFT_LOGIN_URL_PART_1 in driver.current_url or MICROSOFT_LOGIN_URL_PART_2 in driver.current_url, \
            "Assertion Failed: Did not navigate to Microsoft login page."
        
        print("Waiting for email field on Microsoft page...")
        email_field = wait.until(EC.visibility_of_element_located((By.NAME, "loginfmt")))
        assert email_field.is_displayed() and email_field.is_enabled(), "Assertion Failed: Email field not visible/enabled."
        email_field.send_keys(EMAIL)
        email_field.send_keys(Keys.ENTER)
        print(f" Entered email: {EMAIL} and pressed ENTER")
        time.sleep(1.5)

        print("Waiting for password field on Microsoft page...")
        password_field = wait.until(EC.visibility_of_element_located((By.NAME, "passwd")))
        assert password_field.is_displayed() and password_field.is_enabled(), "Assertion Failed: Password field not visible/enabled."
        password_field.send_keys(PASSWORD)
        print("Entered password")

        signin_button = wait.until(EC.element_to_be_clickable((By.ID, "idSIButton9")))
        assert signin_button.is_displayed() and signin_button.is_enabled(), "Assertion Failed: Sign In button not displayed/enabled."
        signin_button.click()
        print(" Clicked 'Sign In' button after entering password")
        time.sleep(3)

        try:
            wait.until_not(EC.url_contains(MICROSOFT_LOGIN_URL_PART_1), "Microsoft URL not left within timeout.")
        except TimeoutException:
            print(f"ℹ️ Did not explicitly see URL change from {MICROSOFT_LOGIN_URL_PART_1}, but might have redirected quickly. Verifying current URL.")
        assert MICROSOFT_LOGIN_URL_PART_1 not in driver.current_url and MICROSOFT_LOGIN_URL_PART_2 not in driver.current_url, \
            "Assertion Failed: Still on Microsoft login page after sign-in, authentication likely failed."


    def _handle_stay_signed_in_prompt(self):
        driver = self.driver
        wait = self.wait

        print("Checking for 'Stay signed in?' prompt...")
        try:
            stay_signed_in_yes_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "idSIButton9"))
            )
            assert stay_signed_in_yes_btn.is_displayed() and stay_signed_in_yes_btn.is_enabled(), \
                "Assertion Failed: 'Stay signed in?' button found but not clickable."

            if "Keep you signed in?" in driver.page_source or "Stay signed in?" in driver.page_source:
                stay_signed_in_yes_btn.click()
                print(" Clicked 'Yes' on 'Stay signed in?' prompt.")
                wait.until(EC.staleness_of(stay_signed_in_yes_btn) or EC.invisibility_of_element_located((By.ID, "idSIButton9")))
                assert not self._is_element_present(By.ID, "idSIButton9"), \
                    "Assertion Failed: 'Stay signed in?' prompt did not disappear after clicking Yes."
            else:
                print(" 'Stay signed in?' button found, but prompt text not confirmed. Proceeding.")

        except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            print(" 'Stay signed in?' prompt did not appear within timeout. Proceeding.")
            assert not self._is_element_present(By.ID, "idSIButton9", timeout=3), \
                "Assertion Failed: 'Stay signed in?' prompt was unexpectedly present after timeout."
        except Exception as e:
            print(f"An unexpected error occurred while handling 'Stay signed in?' prompt: {e}")
            pytest.fail(f"Unhandled exception during 'Stay signed in?' prompt: {e}")

    def _wait_for_dashboard_load(self):
        driver = self.driver
        wait = self.wait

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
                print(f"✅ Loading indicator disappeared: {locator_value}")
                assert not self._is_element_present(by_type, locator_value, timeout=2), \
                    f"Assertion Failed: Loading indicator {locator_value} is still present after wait."
            except TimeoutException:
                print(f"ℹ️ No active loading indicator found or it disappeared quickly for: {locator_value}")
            except Exception as e:
                print(f" Error while checking for loading indicator {locator_value}: {e}")

        print("Waiting for document to be ready (readyState 'complete')...")
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        print(" Document ready state is 'complete'.")
        assert driver.execute_script("return document.readyState") == "complete", \
            "Assertion Failed: Document did not reach 'complete' readyState."

        print("Waiting for main dashboard content to load and Dashboards link to be present...")
        wait.until(
            EC.url_contains(DASHBOARD_URL_PART) or
            EC.presence_of_element_located((By.XPATH, "//span[normalize-space()='Dashboards']"))
        )
        print(" Successfully logged in and dashboard area elements are present.")
        assert DASHBOARD_URL_PART in driver.current_url or \
               self._is_element_present(By.XPATH, "//span[normalize-space()='Dashboards']"), \
               "Assertion Failed: Not logged in or Dashboards element not found after initial load. Check URL or element presence."


    def _click_dashboards_link(self):
        driver = self.driver
        wait = self.wait
        
        print("Attempting to click 'Dashboards' link using By.XPATH, \"//span[normalize-space()='Dashboards']\"...")
        dashboards_element = None
        try:
            dashboards_span = wait.until(
                EC.presence_of_element_located((By.XPATH, "//span[normalize-space()='Dashboards']"))
            )
            assert dashboards_span.is_displayed(), "Assertion Failed: Dashboards span element is not displayed."

            try:
                clickable_parent = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//span[normalize-space()='Dashboards']/ancestor::a[1]"))
                )
                assert clickable_parent.is_displayed() and clickable_parent.is_enabled(), \
                    "Assertion Failed: Clickable parent is not displayed/enabled."
                clickable_parent.click()
                print(" Clicked 'Dashboards' link successfully via its parent <a> element.")
                dashboards_element = clickable_parent
            except (TimeoutException, NoSuchElementException):
                print(" No immediate clickable <a> parent found. Attempting to click the span directly.")
                dashboards_element = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//span[normalize-space()='Dashboards']"))
                )
                assert dashboards_element.is_displayed() and dashboards_element.is_enabled(), \
                    "Assertion Failed: Dashboards span not displayed/enabled for direct click."
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
        wait.until(EC.url_contains(DASHBOARD_URL_PART))
        print(" Successfully navigated to the Dashboards page.")
        assert DASHBOARD_URL_PART in driver.current_url, \
            "Assertion Failed: Did not navigate to the Dashboards URL after clicking."

    def _is_element_present(self, by_type, locator_value, timeout=0):
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by_type, locator_value)))
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def test_01_successful_login_and_dashboard_click(self):
        self._login_to_microsoft()
        self._handle_stay_signed_in_prompt()
        self._wait_for_dashboard_load()
        self._click_dashboards_link()
