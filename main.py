import time, random, os, csv
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

from bs4 import BeautifulSoup
import pickle
import pandas as pd

# import pyautogui
from discord import SyncWebhook, Embed

from urllib.request import urlopen

import re
import yaml
from datetime import datetime, timedelta

log = logging.getLogger(__name__)
retrieveCookies = False

# LINUX BOX:
# from pyvirtualdisplay import Display
# display = Display(visible=1, size=(1920, 1080))
# display.start()
# s = webdriver.chrome.service.Service('/usr/bin/chromedriver')
# driver = webdriver.Chrome(service=s)

driver = webdriver.Chrome()

stealth(
    driver,
    languages=["en-US", "en"],
    vendor="Google Inc.",
    platform="Win32",
    webgl_vendor="Intel Inc.",
    renderer="Intel Iris OpenGL Engine",
    fix_hairline=True,
)

def setupLogger():
    dt = datetime.strftime(datetime.now(), "%m_%d_%y %H_%M_%S ")

    if not os.path.isdir("./logs"):
        os.mkdir("./logs")

    logging.basicConfig(
        filename=("./logs/" + str(dt) + "applyJobs.log"),
        filemode="w",
        format="%(asctime)s::%(name)s::%(levelname)s::%(message)s",
        datefmt="./logs/%d-%b-%y %H:%M:%S",
    )

    log.setLevel(logging.DEBUG)
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.DEBUG)
    c_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S"
    )
    c_handler.setFormatter(c_format)
    log.addHandler(c_handler)


class EasyApplyBot:
    setupLogger()
    # MAX_SEARCH_TIME is 10 hours by default, feel free to modify it
    MAX_SEARCH_TIME = 10 * 60 * 60

    def __init__(
        self,
        username=None,
        password=None,
        filename="output.csv",
        blacklistCompanies=[],
        blackListTitles=[],
        positions=[],
        locations=[],
        keywords=[],
        webhook=None,
    ):

        log.info("LinkedIn JobAlert Bot by Landon Crabtree.")
        log.info("Forked from LinkedIn-Easy-Apply-Bot by nicolomantini")

        self.appliedJobIDs = self.get_appliedIDs(filename) if self.get_appliedIDs(filename) != None else []
        self.filename = filename
        self.options = self.browser_options()
        self.browser = driver
        self.wait = WebDriverWait(self.browser, 5)
        self.blacklistCompanies = blacklistCompanies
        self.blackListTitles = blackListTitles
        self.positions = positions
        self.locations = locations
        self.keywords = keywords
        self.webhook = webhook
        
        log.info(f"Loaded {len(self.appliedJobIDs)} applied job IDs from {filename}")
        
        self.authenticate(username, password)

    def get_appliedIDs(self, filename):
        try:
            df = pd.read_csv(
                filename,
                header=None,
                names=["timestamp", "jobID", "job", "company", "matches", "result"],
                lineterminator="\n",
                encoding="utf-8",
            )

            df["timestamp"] = pd.to_datetime(
                df["timestamp"], format="%Y-%m-%d %H:%M:%S"
            )
            df = df[df["timestamp"] > (datetime.now() - timedelta(days=7))]
            jobIDs = list(df.jobID)
            return jobIDs
        except Exception as e:
            return None

    def browser_options(self):
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        return options

    def authenticate(self, username, password):
        log.info("Logging in... Please wait. ")
        self.browser.get(
            "https://www.linkedin.com/login?trk=guest_homepage-basic_nav-header-signin"
        )
        if not retrieveCookies:
            cookies = pickle.load(open("cookies.pkl", "rb"))
            for cookie in cookies:
                driver.add_cookie(cookie)
        else:
            try:
                user_field = self.browser.find_element("id","username")
                pw_field = self.browser.find_element("id","password")
                login_button = self.browser.find_element("xpath", '//*[@id="organic-div"]/form/div[3]/button')
                user_field.send_keys(username)
                user_field.send_keys(Keys.TAB)
                time.sleep(0.25)
                pw_field.send_keys(password)
                time.sleep(0.25)
                login_button.click()
                time.sleep(0.25)
                time.sleep(20)
            except TimeoutException:
                log.info("TimeoutException! Username/password field or login button not found")
            except KeyboardInterrupt:
                log.info("Saving cookies and exiting...")
                pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))
                exit()

    def fill_data(self):
        self.browser.set_window_position(1, 1)
        self.browser.maximize_window()

    def start_apply(self):
        if len(self.positions) == 0:
            exit()
        self.fill_data()

        combos = []
        while len(combos) < len(self.positions) * len(self.locations):
            position = self.positions[random.randint(0, len(self.positions) - 1)]
            location = self.locations[random.randint(0, len(self.locations) - 1)]
            self.positions.remove(position)  # Remove searched position
            self.locations.remove(location)  # Remove searched location
            combo = (position, location)
            if combo not in combos:
                combos.append(combo)
                log.info(f"Applying to {position}: {location}")
                if (location.lower() == "remote"):
                    location = "&f_WT=2"
                else:
                    # location = "&location=" + location
                    location = ""
                self.applications_loop(position, location)
            if len(combos) > 500:
                break

    # self.finish_apply() --> this does seem to cause more harm than good, since it closes the browser which we usually don't want, other conditions will stop the loop and just break out

    def applications_loop(self, position, location):

        count_application = 0
        count_job = 0
        jobs_per_page = 0
        start_time = time.time()

        self.browser, _ = self.next_jobs_page(position, location, jobs_per_page)
        log.info("Looking for jobs.. Please wait..")

        no_jobs_found = 0

        while time.time() - start_time < self.MAX_SEARCH_TIME:
            # Keep track of how many time 0 jobs are found to skip to the next role.
            if no_jobs_found > 1:
                # Start application process over.
                log.info("No more jobs, going to next role.")
                self.start_apply()
            try:
                log.info(
                    f"{(self.MAX_SEARCH_TIME - (time.time() - start_time)) // 60} minutes left in this search"
                )

                # sleep to make sure everything loads, add random to make us look human.
                # randoTime = random.uniform(3.5, 4.9)
                # log.debug(f"Sleeping for {round(randoTime, 1)}")
                # time.sleep(randoTime)
                self.load_page(sleep=0.25)

                # LinkedIn displays the search results in a scrollable <div> on the left side, we have to scroll to its bottom
                try:
                    scrollresults = self.browser.find_element(By.CLASS_NAME, "jobs-search-results-list")
                except NoSuchElementException:
                    log.info("An error occured while searching for jobs, going to next role.")
                    self.start_apply()

                # Selenium only detects visible elements; if we scroll to the bottom too fast, only 8-9 results will be loaded into IDs list
                for i in range(300, 3000, 100):
                    self.browser.execute_script(
                        "arguments[0].scrollTo(0, {})".format(i), scrollresults
                    )

                time.sleep(0.25)

                # get job links
                links = self.browser.find_elements("xpath", "//div[@data-job-id]")

                if len(links) == 0:
                    log.info("No more jobs, going to next role.")
                    self.start_apply()

                # get job ID of each job link
                IDs = []
                blacklistCompaniesLower = [x.lower() for x in self.blacklistCompanies]
                blackListTitlesLower = [x.lower() for x in self.blackListTitles]
                for link in links:
                    jobID = link.get_attribute("data-job-id").split(":")[-1]
                    if jobID in self.appliedJobIDs:
                        continue
                    name = link.find_element(By.CLASS_NAME, "job-card-list__title").text
                    employer = link.find_element(By.CLASS_NAME, "job-card-container__primary-description").text
                    if (name.lower() in blackListTitlesLower or employer.lower() in blacklistCompaniesLower):
                        #log.info(f"Ignoring job posting from blacklist {name} @ {employer}.")
                        continue
                    
                    # You could add conditions here to filter out jobs that don't match your criteria
                    # if "intern" not in name.lower():
                    #     #log.info(f"Ignoring non-internship job posting {name} @ {employer}.")
                    #     continue
                    
                    IDs.append(int(jobID))

                # remove duplicates
                IDs = set(IDs)

                # remove already applied jobs
                jobIDs = [x for x in IDs if x not in self.appliedJobIDs]
                after = len(jobIDs)
                print("JOBS FOUND: " + str(after))
                if len(jobIDs) == 0:
                    no_jobs_found += 1

                # it assumed that 25 jobs are listed in the results window
                if len(jobIDs) == 0 and len(IDs) > 23:
                    jobs_per_page = jobs_per_page + 25
                    count_job = 0
                    self.avoid_lock()
                    self.browser, jobs_per_page = self.next_jobs_page(
                        position, location, jobs_per_page
                    )
                # loop over IDs to apply
                zero_matches = 0
                for i, jobID in enumerate(jobIDs):
                    if zero_matches > 10:
                        log.info("Looks like jobs are no longer relevant, going to next role.")
                        return self.start_apply()
                    count_job += 1
                    self.get_job_page(jobID)

                    # Check for keywords
                    keywords = self.keywords

                    matches = 0
                    matched_keywords = []
                    time.sleep(0.1)
                    show_more = self.browser.find_element(By.CLASS_NAME, "jobs-description__footer-button")
                    show_more.click()
                    
                    company_name = self.browser.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__company-name").text
                    
                    job_subtitle = self.browser.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__primary-description-container").text
                    job_location = job_subtitle.split(" · ")[0].strip()
                    
                    job_title = self.browser.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__job-title").text
                    job_description = self.browser.find_element(By.CLASS_NAME, "jobs-description-content__text").text
                    #company_logo_url = self.browser.find_element(By.XPATH, "//img[contains(@alt, 'company logo')]").get_attribute("src")
                    #company_logo_url = self.browser.find_element(By.XPATH, f"//img[contains(@alt, '{company_name} Company logo')]").get_attribute("src")
                    # find by XPATH with height of 40
                    company_logo_url = self.browser.find_element(By.XPATH, f"//img[contains(@height, '40')]").get_attribute("src")
                    posting_url = "https://www.linkedin.com/jobs/view/" + str(jobID)
                    
                    # try to get salary
                    try:
                        salary = self.browser.find_element(By.CLASS_NAME, "job-details-jobs-unified-top-card__job-insight").text
                        if salary.startswith("$"):
                            salary = salary.split(" ")[0]
                        else:
                            salary = "Unknown"
                    except:
                        salary = "Unknown"

                    for keyword in keywords:
                        if keyword.lower() in job_description.lower():
                            # print(keyword + " matched")
                            matches += 1
                            matched_keywords.append(keyword)
                    if matches >= 3:
                        log.info("Job posting matches keywords.")
                        string_easy = "* " + str(matches) + " matches"
                        result = True
                        matched_formatted = ",".join(matched_keywords)
                        if self.webhook is not None:
                            webhook = SyncWebhook.from_url(self.webhook)
                            e = Embed(
                                url=posting_url,
                                title=f"{job_title} @ {company_name}",
                                description=f"New job match found!\n{job_location}\nSalary: {salary}",
                                color=0x00FF00,
                                timestamp=None,
                            )
                            e.set_thumbnail(url=company_logo_url)
                            e.set_footer(text="Matched keywords: " + matched_formatted)
                            webhook.send(embed=e)
                            webhook.send(content="<@391055696713613315>")
                    else:
                        log.info("Job posting has <3 keywords.")
                        string_easy = "* " + str(matches) + "  matches"
                        result = False
                        matched_formatted = ",".join(matched_keywords)
                        if self.webhook is not None:
                            webhook = SyncWebhook.from_url(self.webhook)
                            e = Embed(
                                url=posting_url,
                                title=f"{job_title} @ {company_name}",
                                description="Job posting didn't meet the criteria.",
                                color=0xFF0000,
                                timestamp=None,
                            )
                            e.set_thumbnail(url=company_logo_url)
                            e.set_footer(text="Matched keywords: " + matched_formatted)
                            webhook.send(embed=e)
                            if matches == 0:
                                zero_matches += 1
                    position_number = str(count_job + jobs_per_page)
                    log.info(f"\nPosition {position_number}:\n {self.browser.title} \n {string_easy} \n")

                    self.write_to_file(matches, jobID, self.browser.title, result)
                    self.appliedJobIDs = self.get_appliedIDs(self.filename)  # Reinitialize applied JobIDS

                    # go to new page if all jobs are done
                    if count_job == len(jobIDs):
                        jobs_per_page = jobs_per_page + 25
                        count_job = 0
                        log.info("Finished page, going to next page.")
                        self.avoid_lock()
                        self.browser, jobs_per_page = self.next_jobs_page(
                            position, location, jobs_per_page
                        )
            except Exception as e:
                print(e)

    def write_to_file(self, matches, jobID, browserTitle, result):
        def re_extract(text, pattern):
            target = re.search(pattern, text)
            if target:
                target = target.group(1)
            return target

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # attempted = False if button == False else True
        job = re_extract(browserTitle.split(" | ")[0], r"\(?\d?\)?\s?(\w.*)")
        company = re_extract(browserTitle.split(" | ")[1], r"(\w.*)")

        toWrite = [timestamp, jobID, job, company, str(matches), result]
        with open(self.filename, "a") as f:
            writer = csv.writer(f)
            writer.writerow(toWrite)

    def get_job_page(self, jobID):
        jobURL = "https://www.linkedin.com/jobs/view/" + str(jobID)
        self.browser.get(jobURL)
        self.job_page = self.load_page(sleep=0.25)
        return self.job_page

    def load_page(self, sleep=0.25):
        scroll_page = 0
        while scroll_page < 4000:
            self.browser.execute_script("window.scrollTo(0," + str(scroll_page) + " );")
            scroll_page += 200
            time.sleep(0.1)

        if sleep != 1:
            self.browser.execute_script("window.scrollTo(0,0);")
            time.sleep(sleep * 3)

        page = BeautifulSoup(self.browser.page_source, "lxml")
        return page

    def avoid_lock(self):
        # x, _ = pyautogui.position()
        # pyautogui.moveTo(x + 200, pyautogui.position().y, duration=0.1)
        # pyautogui.moveTo(x, pyautogui.position().y, duration=0.1)
        # pyautogui.keyDown('ctrl')
        # pyautogui.press('esc')
        # pyautogui.keyUp('ctrl')
        # time.sleep(0.1)
        # pyautogui.press('esc')
        pass

    def next_jobs_page(self, position, location, jobs_per_page):
        # Easy Apply: ?f_LF=f_AL
        # Some other things you can do:
        # - Internships: &f_E=1
        # - Entry Level: &f_E=2
        
        self.browser.get(
            "https://www.linkedin.com/jobs/search/"
            + f"?keywords={position}"
            + f"&location={location}"
            + f"&f_E=2"
            + f"&f_TPR=r2592000" # r2592000 for 30 days | #r604800 for 7 days
            + f"&start={str(jobs_per_page)}"
        )
        # self.avoid_lock()
        self.load_page(sleep=0.25)
        return (self.browser, jobs_per_page)

    def finish_apply(self):
        self.browser.close()


if __name__ == "__main__":
    with open("config.yaml", "r") as file:
        try:
            config = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            raise exc

    assert len(config["positions"]) > 0
    assert len(config["locations"]) > 0
    assert config["username"] is not None
    assert config["password"] is not None

    webhook = config.get("webhook", None)

    output_filename = "output.csv"
    blacklistCompanies = config.get("blacklistCompanies", [])
    blackListTitles = config.get("blackListTitles", [])
    keywords = config.get("keywords", [])

    locations = [l for l in config["locations"] if l != None]
    positions = [p for p in config["positions"] if p != None]
    
    log.info(f"Applying to {', '.join(positions)} positions in {', '.join(locations)} locations.")
    log.info(f"[CONFIG] Blacklisted companies: {', '.join(blacklistCompanies)}")
    log.info(f"[CONFIG] Blacklisted titles: {', '.join(blackListTitles)}")

    bot = EasyApplyBot(
        config["username"],
        config["password"],
        filename=output_filename,
        blacklistCompanies=blacklistCompanies,
        blackListTitles=blackListTitles,
        positions=positions,
        locations=locations,
        keywords=keywords,
        webhook=webhook,
    )
    bot.start_apply()
