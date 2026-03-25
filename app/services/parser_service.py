import httpx
import feedparser
from bs4 import BeautifulSoup
from readability import Document
from trafilatura import fetch_url, extract

class ParserService:
    async def fetch_and_parse_rss(self, url: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            return feed.entries

    async def fetch_and_parse_article(self, url: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            doc = Document(response.text)
            return {
                "title": doc.title(),
                "content": BeautifulSoup(doc.summary(), "lxml").text
            }

    async def fetch_and_extract_content(self, url: str):
        downloaded = fetch_url(url)
        if downloaded:
            return extract(downloaded, include_images=True, include_formatting=True)
        return None
