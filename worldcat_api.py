import re
import string
import urllib.parse
from typing import Optional

import Levenshtein
import requests


class WorldcatAPI:
    def __init__(self) -> None:
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

        records = requests.get(url).json().get("briefRecords", [])

        results = []
        for record in records:
            score = self.calculate_score(title, record)
            if score > 0:
                results.append({"score": score, "record": record})
        return results

    def get_metadata(self, oclc: int) -> dict:
        url = f"{self.base_url}/search?q=no:{oclc}"
        records = requests.get(url).json().get("briefRecords", [])
        if len(records) == 1:
            return records[0]
        else:
            return {}

    def get_all_editions(self, oclc: int, max_results: int = 100) -> list[dict]:
        result = []
        offset = 1
        while True:
            url = f"{self.base_url}/search-editions/{oclc}?limit=10&offset={offset}"
            data = requests.get(url).json()
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
