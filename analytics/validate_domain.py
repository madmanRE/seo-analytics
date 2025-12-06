import urllib.parse

import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def normalize_domain(domain: str) -> str:
    domain = domain.strip().lower()
    parsed = urllib.parse.urlparse(domain if "://" in domain else f"https://{domain}")
    return f"https://{parsed.netloc}/"

def check_gsc_site(domain: str, creds: Credentials) -> bool:
    service = build("searchconsole", "v1", credentials=creds)
    try:
        sites = service.sites().list().execute()
        site_urls = [s["siteUrl"].replace("sc-domain:", "") for s in sites.get("siteEntry", [])]
        google_domains = {normalize_domain(u):u for u in site_urls}
        return google_domains.get(domain, None)

    except Exception as e:
        print(f"GSC error: {e}")
        raise e

def check_yandex_site(domain: str, oauth_token) -> bool:
    if isinstance(oauth_token, dict):
        oauth_token = oauth_token.get("access_token")

    if not oauth_token:
        print("Yandex token is missing")
        raise Exception("Yandex error: Yandex token is missing")

    try:
        headers = {"Authorization": f"OAuth {oauth_token}"}
        resp = httpx.get("https://api.webmaster.yandex.net/v4/user", headers=headers, timeout=10)
        resp.raise_for_status()
        uid = resp.json()["user_id"]

        url = f"https://api.webmaster.yandex.net/v4/user/{uid}/hosts"
        resp = httpx.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        yandex_domains = {normalize_domain(h["ascii_host_url"]):h["host_id"] for h in data.get("hosts", [])}
        return yandex_domains.get(domain, None)

    except Exception as e:
        print(f"Yandex error: {e}")
        raise e

def analyze_domain(domain: str, gsc_creds: Credentials, yandex_token: str) -> dict:
    domain = normalize_domain(domain)
    return {
        "google": check_gsc_site(domain, gsc_creds),
        "yandex": check_yandex_site(domain, yandex_token),
    }
