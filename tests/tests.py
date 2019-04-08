import unittest
import time
import urllib
import os
import urllib2
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


class SegAnnTest(unittest.TestCase):

    # The testprofile can be downloaded at
    # https://drive.google.com/open?id=0BxbS0oJuMJTHS1RGeGtvWmp3VzA

    def setUp(self):
        self.driver = webdriver.Firefox()
        # enter the test_profile_path here
        self.test_profile_path = os.path.join(os.getcwd(),"test_profile.bedGraph.gz")
        self.test_second_profile_path = os.path.join(os.getcwd(),"test_Normal02.bedGraph.gz")

    def test010_isSegAnnUp(self):
        """
        Test#1
        This test is for checking whether the page is loading or not
        """
        print "Test#1 isSegAnnUp?"
        driver = self.driver
        driver.get("http://127.0.0.1:8080")
        assert "SegAnnDB" in driver.title

    def test020_login(self):
        """
        Test#2
        This test is for testing whether the login functionality is working
        """
        print "Test#2 Persona login test"

        driver = self.driver
        driver.get("http://127.0.0.1:8080")

        # Call the login method to login the user
        self.login(driver)

        wait = WebDriverWait(driver, 60)
        assert wait.until(
            EC.element_to_be_clickable((By.ID, "signout"))).is_displayed()

    def test030_upload(self):
        """
        This test is for checking if we can successfully upload a profile
        """
        print "Test#3 Profile upload test"
        # login into the app
        driver = self.driver
        driver.get("http://127.0.0.1:8080/")
        self.login(driver)

        # make sure that we are logged in
        wait = WebDriverWait(driver, 60)
        assert wait.until(
            EC.element_to_be_clickable((By.ID, "signout"))).is_displayed()

        # go to the upload page
        driver.get("http://127.0.0.1:8080/upload")

        # in the upload file field, upload the file
        upload_field = driver.find_element_by_id("id_file")
        test_profile_path = self.test_profile_path
        upload_field.send_keys(test_profile_path)

        # we need to use the submit() button
        # because when we submit forms via click
        # the whole thing has been found to freeze.
        elem = driver.find_element_by_id("submit_button")
        elem.submit()

        assert wait.until(
            EC.presence_of_element_located((By.ID, "success")))

    def test040_annotate(self):
        """
        This test does two things -
        a. Annotate a region
        b. Delete that annotation

        This all happens on the test uploaded profile
        """

        print "Test#4 for testing annotation"

        # we need to give some time for profile processing before we can make
        # annotations
        time.sleep(60)

        driver = self.driver
        driver.get("http://127.0.0.1:8080/")
        self.login(driver)

        # make sure that we are logged in
        wait = WebDriverWait(driver, 60)
        assert wait.until(
            EC.element_to_be_clickable((By.ID, "signout"))).is_displayed()

        #
        url_for_annotation = (
            "http://127.0.0.1:8080/add_region/ES0004/3/breakpoints/1breakpoint/46469264/67723671/")

        delete_annotation = (
            "http://127.0.0.1:8080/delete_region/ES0004/3/breakpoints/0/")
        resp = urllib2.urlopen(url_for_annotation)

        if resp.getcode() != 200:
            print "Fail"
            assert False
        resp.close()

        del_resp = urllib2.urlopen(delete_annotation)
        if del_resp.getcode() != 200:
            assert False

        del_resp.close()

    def test050_trackhub(self):
        print "Test#5 Trackhub Creation Test"
        driver = self.driver
        driver.get("http://127.0.0.1:8080/")
        self.login(driver)

        # make sure that we are logged in
        wait = WebDriverWait(driver, 60)
        assert wait.until(
            EC.element_to_be_clickable((By.ID, "signout"))).is_displayed()
        driver.get("http://127.0.0.1:8080/trackhub_init/")
        shortname_field = driver.find_element_by_id("id_short_label")
        shortname_field.send_keys("test1")
        longname_field = driver.find_element_by_id("id_long_label")
        longname_field.send_keys("test1long")
        db_field = driver.find_element_by_id("id_db")
        db_field.send_keys("hg19")
        profile_box = driver.find_element_by_xpath("//input[@value='ES0004']")
        profile_box.click()
        submit_button = driver.find_element_by_id("submit_button")
        submit_button.click()
        sleep(10)
        if ("Trackhub data for test1" in driver.page_source) and ("ES0004" in driver.page_source):
            assert True
        else:
            assert False

    def test060_multi_profile_trackhub(self):
        print "Test#6 Multi Profile Trackhub Creation Test"
        driver = self.driver
        driver.get("http://127.0.0.1:8080/")
        self.login(driver)

        # make sure that we are logged in
        wait = WebDriverWait(driver, 60)
        assert wait.until(
            EC.element_to_be_clickable((By.ID, "signout"))).is_displayed()

        # go to the upload page
        driver.get("http://127.0.0.1:8080/upload")

        # in the upload file field, upload the file
        upload_field = driver.find_element_by_id("id_file")
        test_second_profile_path = self.test_second_profile_path
        upload_field.send_keys(test_second_profile_path)

        # we need to use the submit() button
        # because when we submit forms via click
        # the whole thing has been found to freeze.
        elem = driver.find_element_by_id("submit_button")
        elem.submit()

        assert wait.until(
            EC.presence_of_element_located((By.ID, "success")))

        time.sleep(60)

        driver.get("http://127.0.0.1:8080/trackhub_init/")
        shortname_field = driver.find_element_by_id("id_short_label")
        shortname_field.send_keys("test2")
        longname_field = driver.find_element_by_id("id_long_label")
        longname_field.send_keys("test2long")
        db_field = driver.find_element_by_id("id_db")
        db_field.send_keys("hg19")
        profile_box = driver.find_element_by_xpath("//input[@value='ES0004']")
        profile_box.click()
        profile_box2 = driver.find_element_by_xpath("//input[@value='Normal02']")
        profile_box2.click()
        submit_button = driver.find_element_by_id("submit_button")
        submit_button.click()
        sleep(10)
        if ("Trackhub data for test2" in driver.page_source) and ("ES0004" in driver.page_source) \
                and ("Normal02" in driver.page_source):
            assert True
        else:
            assert False

    def test070_no_header(self):
        """
        This test checks if header non-creation is properly done.
        It also performs no login to simulate UCSC access.
        """
        print "Test#7 Non-Header export test"
        bedfile = urllib2.urlopen('http://127.0.0.1:8080/trackhub/test1/hg19/ES0004_breaks.bed')
        if ("track" in bedfile.read()):
            assert False
        else:
            assert True

    def test080_header(self):
        """
        This checks that file header creation occurs by default
        """
        print "Test#8 Header export test"
        driver = self.driver
        driver.get("http://127.0.0.1:8080/")
        self.login(driver)
        # make sure that we are logged in
        wait = WebDriverWait(driver, 60)
        assert wait.until(
            EC.element_to_be_clickable((By.ID, "signout"))).is_displayed()
        driver.get("http://127.0.0.1:8080/export/seganntest2@gmail.com/ES0004/breaks/bed/")
        if ("track" in driver.page_source):
            assert True
        else:
            assert False

    def test090_delete(self):
        """
        This test is for checking if we are able to delete the uploaded profile
        """
        print "Test#9 Profile Deleting test."
        driver = self.driver
        driver.get("http://127.0.0.1:8080/")
        self.login(driver)

        # make sure that we are logged in
        wait = WebDriverWait(driver, 60)
        assert wait.until(
            EC.element_to_be_clickable((By.ID, "signout"))).is_displayed()

        # this is a hack, we need to change it to something more generic.
        # plausible for now
        driver.get("http://127.0.0.1:8080/delete_profile/ES0004/")

        # how to assert ?
        if ("deleted" in driver.page_source):
            assert True
        else:
            assert False

    def login(self, driver):
        """
        This method is internal to testing framework
        It is used to login the user.
        Each test requires the user to be logged in already

        Parameters:
            driver - reference to driver being used
        """
        # check if cookie file exists and is up to date
        import os.path
        if os.path.isfile('cookies.txt'):
            fr = open('cookies.txt')
            cookies = eval(fr.read())
            for cookie in cookies:
                if cookie["domain"] == "localhost" or cookie["domain"] == "127.0.0.1":
                    driver.get("http://127.0.0.1:8080/")
                    cookie["domain"] = "127.0.0.1"
                    driver.add_cookie(cookie)
                    driver.get("http://127.0.0.1:8080/")
            return
        # no usable cookie/cookie.txt, therefore let's switch back to localhost to get a cookie first
        driver.get("http://localhost:8080/")
        # this is the tricky part
        # We have to get the right handle for the correct popup login window
        main_window_handle = driver.current_window_handle

        driver.find_element_by_id('signin').click()

        wait = WebDriverWait(driver, 60)

        ### The Commented code was used to test for persona based login system
        ### It is no longer in use. Can be safely removed
        # signin_window_handle = None

        # iterating through all the handles to get the popup, since we only hve
        # one popup, making use of that
        # while not signin_window_handle:
            # for handle in driver.window_handles:
                # if handle != main_window_handle:
                    # signin_window_handle = handle
                    # break

        # switch to the signin popup
        # driver.switch_to.window(signin_window_handle)

        # xpath id obtained using firebug for the next button on persona dialog
        # (driver.find_element_by_xpath(
            # "/html/body/div/section[1]/form/div[2]/div[1]/div/div[2]/p[4]/button[1]")
            # .click())

        # switch to the main window
        # driver.switch_to.window(main_window_handle)

        # get the email field
        email_field = wait.until(
            EC.element_to_be_clickable((By.ID, "identifierId")))

        # enter the email of test user
        email_field.send_keys("seganntest2@gmail.com")
        sleep(10)
        # click next
        driver.find_element_by_id('identifierNext').click()
        sleep(10)
        # enter password
        wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys('segann@test', Keys.RETURN)
        wait = WebDriverWait(driver, 60)
        assert wait.until(
            EC.element_to_be_clickable((By.ID, "signout"))).is_displayed()  # This check is important so we get the localhost cookie
        cookies = driver.get_cookies()
        fw = open('cookies.txt', 'w')
        fw.write(str(cookies))
        fw.close()

    def tearDown(self):
        self.driver.close()

if __name__ == "__main__":
    # now we check for existence of the test file
    # if it does not exist then we create it
    file_name = "test_profile.bedGraph.gz"
    file_path = os.path.join(os.getcwd(), file_name)
    if os.path.isfile(file_path):
        print "Test file found!"
    else:
        print "Test file does not exists. Downloading."
        download_url = "https://raw.githubusercontent.com/abstatic/SegAnnDB-tests/master/test_profile.bedGraph.gz"
        urllib.urlretrieve(download_url, file_path)
        if os.path.isfile(file_path):
            print "Successfully downloaded the test profile."
        else:
            print "Failed to download the test profile."
    unittest.main()
