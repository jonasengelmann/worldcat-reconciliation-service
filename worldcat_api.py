import http
import json
import re
import string
import urllib.parse
from typing import Optional

import Levenshtein
import redis
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class MissingCookieException(Exception):
    pass


class WorldcatAPI:
    def __init__(self, remote_webdriver_address:str, redis_endpoint:str = None) -> None:
        self.remote_webdriver_address = remote_webdriver_address
        self.session = self.create_session()
        self.base_url = "https://www.worldcat.org/api"
        if redis_endpoint:
            self.redis_client = redis.Redis(host=redis_endpoint.replace("http://", ""), db=0)
            self.redis_client.config_set("maxmemory", "3GB")
            self.redis_client.config_set('maxmemory-policy', "allkeys-lru")
        else:
            self.redis_client = None
        self.types = {
            "book": "Book",
            "audiobook": "Audiobook",
            "artchap": "Article, Chapter",
            "archv": "Archival Material",
            "music": "Music",
            "snd": "Sound Recording",
            "msscr": "Musical Score",
            "game": "Game",
            "video": "Video",
            "toy": "Toy",
            "vis": "Visual Material",
            "map": "Map",
            "jrnl": "Journal, Magazine",
            "news": "Newspaper",
            "intmm": "Interactive Multimedia",
            "compfile": "Computer File",
            "kit": "Kit",
            "object": "Object",
            "web": "Website",
            "encyc": "Encyclopedia Article",
        }
        self.subtypes = {
            "book-printbook": "Print Book",
            "book-digital": "eBook",
            "book-thsis": "Thesis, Dissertation",
            "book-mss": "Manuscript",
            "book-braille": "Braille Book",
            "audiobook-cd": "Audiobook on CD",
            "audiobook-digital": "eAudiobook",
            "artchap-digital": "Downloadable Article",
            "artchap-mss": "Manuscript Article",
            "archv-digital": "Downloadable Archival Material",
            "music-cd": "Music CD",
            "music-digital": "Online Music",
            "msscr-digital": "Downloadable Musical Score",
            "video-dvd": "DVD-Video",
            "video-digital": "Online Video",
            "map-digital": "Online Map",
            "jrnl-print": "Print Journal",
            "jrnl-digital": "ejournal, eMagazine",
            "jrnl-government": "Government Publication",
            "news-digital": "eNewspaper",
            "news-print": "Print Newspaper",
        }

    def create_session(self) -> requests.sessions.Session:
        session = requests.session()
        session.headers.update({"referer": "https://www.worldcat.org/de/search"})
        session.cookies.set_cookie(self.get_worldcat_cookie())
        return session

    def get(self, url):
        retries = 5
        while retries:
            try:
                response = self.session.get(url)
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                last_connection_exception = e
                self.session = self.create_session()
                retries -= 1
        raise last_connection_exception

    def search(
        self,
        title: str,
        author: Optional[str] = None,
        type_: Optional[str] = None,
        publication_year: Optional[int] = None,
    ) -> list[dict]:
        preprocessed_title = WorldcatAPI.preprocess_string(title)
        url = f"{self.base_url}/search?q=ti:{urllib.parse.quote_plus(preprocessed_title)}"

        if author:
            url += f"+AND+au:{urllib.parse.quote_plus(author)}"

        if type_:
            url += f"&itemType={urllib.parse.quote_plus(type_)}"

        if publication_year:
            url += f"&datePublished={publication_year}-{publication_year}"

        records = self.get(url).json().get("briefRecords", [])

        results = []
        for record in records:
            if record.get('title'):
                score = self.calculate_score(preprocessed_title, record)
                if score > 0:
                    results.append({"score": score, "record": record})
                    if self.redis_client:
                        self.redis_client.set(record["oclcNumber"], json.dumps(record))
        return results

    def get_metadata(self, oclc: int) -> dict:
        if self.redis_client:
            result = self.redis_client.get(str(oclc))
            if result:
                return json.loads(result)

        url = f"{self.base_url}/search?q=no:{oclc}"
        records = self.get(url).json().get("briefRecords", [])
        if len(records) == 1:
            return records[0]
        else:
            return {}

    def get_all_editions(self, oclc: int, max_results: int = 100) -> list[dict]:
        result = []
        offset = 1
        while True:
            url = f"{self.base_url}/search-editions/{oclc}?limit=10&offset={offset}"
            data = self.session.get(url).json()
            result.extend(data.get("briefRecords", []))

            if (
                len(result) == data.get("numberOfRecords", 0)
                or len(result) >= max_results
            ):
                break
            offset += 10
        return result

    @staticmethod
    def calculate_score(title: str, record: dict) -> int:
        found_title = WorldcatAPI.preprocess_string(record["title"])
        distance = Levenshtein.distance(title, found_title)
        return int(max((1 - (distance / len(title))) * 100, 0))

    @staticmethod
    def preprocess_string(x: str) -> str:
        """Removes punctuation, double whitespace and converts to lowercase."""
        x = x.translate(str.maketrans(string.punctuation, ' '*len(string.punctuation))).lower()
        return re.sub(" +", " ", x).strip()

    def get_worldcat_cookie(self) -> http.cookiejar.Cookie:
        options = Options()
        options.add_argument("start-maximized")
        options.add_argument("disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--headless")
        driver = webdriver.Remote(
            command_executor=self.remote_webdriver_address, options=options
        )
        try:
            driver.get("https://www.worldcat.org/")
            search_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@data-testid='home-page-search-bar']")
                )
            )

            search_input.send_keys("test")
            search_input.send_keys(Keys.ENTER)

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@data-testid='search-results-count-container']")
                )
            )

            cookies = driver.get_cookies()
        finally:
            driver.quit()

        for cookie in cookies:
            if cookie["name"] == "wc_tkn":
                return requests.cookies.create_cookie(
                    domain=cookie["domain"], name=cookie["name"], value=cookie["value"]
                )
        raise MissingCookieException("Could not obtain cookie")
        return None
