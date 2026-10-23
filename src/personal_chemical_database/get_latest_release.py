import requests
from pydantic import BaseModel


class Release(BaseModel):
    version: str
    release_title: str
    date: str
    url: str


def get_latest_release() -> Release | None:
    try:
        repo = "TheTimebreaker/personal-chemical-database"  # owner/repo
        url = f"https://api.github.com/repos/{repo}/releases/latest"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        release = response.json()

        version = release["tag_name"]
        release_name = release["name"]
        publication = release["published_at"]
        url = release["html_url"]

        return Release(version=version, release_title=release_name, date=publication, url=url)

    except Exception:
        return None
