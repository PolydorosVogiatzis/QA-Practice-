import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
import os
import time

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

LOGIN_URL = "https://etrm-greece-dev.stellarblue.eu/Account/Login"
DASHBOARD_URL_PART = "https://etrm-greece-dev.stellarblue.eu"
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



@pytest.mark.usefixtures("driver_setup")
class TestLoginFlow:
    driver = None
    wait = None

    def test_01_open_login_page(self):
        self.driver.get(LOGIN_URL)
        self.wait.until(EC.url_contains("Account/Login"))
        assert "Account/Login" in self.driver.current_url, "Failed to load login page"
        print("Step 1: Login page opened")

    def test_02_click_sign_in_with_microsoft(self):
        btn = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Sign in with Microsoft')]"))
        )
        assert btn.is_displayed() and btn.is_enabled(), "Microsoft sign-in button not clickable"
        btn.click()
        time.sleep(1)
        self.wait.until(lambda d: MICROSOFT_LOGIN_URL_PART_1 in d.current_url or MICROSOFT_LOGIN_URL_PART_2 in d.current_url)
        assert MICROSOFT_LOGIN_URL_PART_1 in self.driver.current_url or MICROSOFT_LOGIN_URL_PART_2 in self.driver.current_url, \
            "Did not navigate to Microsoft login page"
        print("Step 2: Clicked 'Sign in with Microsoft' and navigated to Microsoft login")

    def test_03_enter_email(self):
        email_field = self.wait.until(EC.visibility_of_element_located((By.NAME, "loginfmt")))
        assert email_field.is_displayed() and email_field.is_enabled(), "Email field not visible/enabled"
        email_field.send_keys(EMAIL)
        email_field.send_keys(Keys.ENTER)
        time.sleep(1.5)
        print("Step 3: Email entered")

    def test_04_enter_password(self):
        password_field = self.wait.until(EC.visibility_of_element_located((By.NAME, "passwd")))
        assert password_field.is_displayed() and password_field.is_enabled(), "Password field not visible/enabled"
        password_field.send_keys(PASSWORD)
        signin_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "idSIButton9")))
        assert signin_btn.is_displayed() and signin_btn.is_enabled(), "Sign-in button not visible/enabled"
        signin_btn.click()
        time.sleep(3)
        print("Step 4: Password entered and sign-in clicked")

    def test_05_handle_stay_signed_in_prompt(self):
        try:
            stay_signed_in_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "idSIButton9"))
            )
            assert stay_signed_in_btn.is_displayed() and stay_signed_in_btn.is_enabled(), "'Stay signed in?' button not clickable"
            if "Stay signed in?" in self.driver.page_source or "Keep you signed in?" in self.driver.page_source:
                stay_signed_in_btn.click()
                self.wait.until(EC.staleness_of(stay_signed_in_btn))
                assert not self.driver.find_elements(By.ID, "idSIButton9"), "'Stay signed in?' prompt did not disappear"
                print("Step 5: 'Stay signed in?' prompt handled")
            else:
                print("Step 5: No 'Stay signed in?' prompt text detected, skipping click")
        except TimeoutException:
            print("Step 5: No 'Stay signed in?' prompt appeared")
        except Exception as e:
            pytest.fail(f"Unexpected error in step 5: {e}")

    def test_06_wait_for_dashboard_load(self):
        loaders = [
            (By.CSS_SELECTOR, ".spinner-overlay"),
            (By.CSS_SELECTOR, ".loading-indicator"),
            (By.CSS_SELECTOR, ".ngx-loading-mask"),
            (By.XPATH, "//*[contains(@class, 'loading') and contains(@style, 'display: block')]"),
            (By.XPATH, "//*[contains(@class, 'overlay') and contains(@style, 'display: block')]"),
        ]
        for by, locator in loaders:
            try:
                WebDriverWait(self.driver, 5).until_not(
                    EC.presence_of_element_located((by, locator))
                )
            except TimeoutException:
                pass
        self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        assert self.driver.execute_script("return document.readyState") == "complete", "Document readyState not complete"
        print("Step 6: Dashboard page loaded completely")

    def test_07_check_dashboard_elements(self):

        elem = self.wait.until(
            EC.presence_of_element_located((By.XPATH, "//span[normalize-space()='Dashboards']"))
        )
        assert elem.is_displayed(), "'Dashboards' element is not displayed"
        print("Step 7: Dashboards element found")

    def test_08_click_dashboards_link(self):
        success = False
        for attempt in range(2):
            try:
                clickable = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//span[normalize-space()='Dashboards']/ancestor::a[1]"))
                )
                clickable.click()
                self.wait.until(EC.url_contains(DASHBOARD_URL_PART))
                success = True
                break
            except (TimeoutException, WebDriverException):
                time.sleep(2)
        assert success, "Could not navigate to dashboards"
        print("Step 8: Clicked 'Dashboards' and navigated")
        tabs = self.driver.window_handles
        self.driver.switch_to.window(tabs[1])
    def test_09_click_dashboards_overview(self):
        try:
            time.sleep(3)
            dashboard_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[@title='Dashboards Overview']"))
            )

            assert dashboard_btn.is_displayed(),"'Dashboards Overview' is not visible"

            dashboard_btn.click()
            print("Step 9: Clicked 'Dashboards Overview'")
        except TimeoutException:
            pytest.fail("Step 9: 'Dashboards Overview' button not found or not clickable")

    def test_10_click_plus_icon(self):
        time.sleep(2)
        self.driver.save_screenshot("debug_plus_icon.png")

        try:
            plus_icon = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//i[contains(@class, 'fa-plus')]"))
            )
            assert plus_icon.is_displayed(),"Plus icon is not visible or not clickable"

            self.driver.execute_script("arguments[0].scrollIntoView(true);", plus_icon)
            plus_icon.click()
            print("Step 10: Clicked plus icon")
        except TimeoutException:
            pytest.fail("Step 10: Plus icon not found or not clickable")




