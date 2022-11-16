import http
import re
import string
import urllib.parse
from typing import Optional

import Levenshtein
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
    def __init__(self, remote_webdriver_address:str) -> None:
        self.remote_webdriver_address = remote_webdriver_address
        self.session = self.create_session()
        self.base_url = "https://www.worldcat.org/api"
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

    def search(
        self,
        title: str,
        author: Optional[str] = None,
        type_: Optional[str] = None,
        publication_year: Optional[int] = None,
    ) -> list[dict]:
        url = f"{self.base_url}/search?q=ti:{urllib.parse.quote_plus(title)}"

        if author:
            url += f"+AND+au:{urllib.parse.quote_plus(author)}"

        if type_:
            url += f"&itemType={urllib.parse.quote_plus(type_)}"

        if publication_year:
            url += f"&datePublished={publication_year}-{publication_year}"

        records = self.session.get(url).json().get("briefRecords", [])

        results = []
        for record in records:
            score = self.calculate_score(title, record)
            if score > 0:
                results.append({"score": score, "record": record})
        return results

    def get_metadata(self, oclc: int) -> dict:
        url = f"{self.base_url}/search?q=no:{oclc}"
        records = self.session.get(url).json().get("briefRecords", [])
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
        title = WorldcatAPI.preprocess_string(title)
        found_title = WorldcatAPI.preprocess_string(record["title"])
        distance = Levenshtein.distance(title, found_title)
        return int(max((1 - (distance / len(title))) * 100, 0))

    @staticmethod
    def preprocess_string(x: str) -> str:
        """Removes punctuation, double whitespace and converts to lowercase."""
        x = x.translate(str.maketrans("", "", string.punctuation)).lower()
        return re.sub(" +", " ", x).strip()

    def get_worldcat_cookie(self) -> http.cookiejar.Cookie:
        options = Options()
        driver = webdriver.Remote(
            command_executor=self.remote_webdriver_address, options=options
        )
        driver.get("https://www.worldcat.org/")
        try:
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
