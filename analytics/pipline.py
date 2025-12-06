from datetime import datetime, timedelta

import httpx
import pandas as pd

from analytics.fetch_data import (
    get_gsc_pages,
    get_gsc_queries,
    get_yandex_pages,
    get_yandex_queries,
    get_metrika_data,
)
from analytics.validate_domain import analyze_domain


def full_pipline(domain, gsc_creds, yandex_token, counter):
    result = analyze_domain(domain, gsc_creds, yandex_token)
    googl_host_id = result["google"]
    yandex_host_id = result["yandex"]

    today = datetime.now().date()
    start_date = (today - timedelta(days=15)).isoformat()
    end_date = (today - timedelta(days=2)).isoformat()

    headers = {"Authorization": f"OAuth {yandex_token.get('access_token')}"}
    resp = httpx.get("https://api.webmaster.yandex.net/v4/user", headers=headers, timeout=10)
    resp.raise_for_status()
    uid = resp.json()["user_id"]

    gsc_pages = get_gsc_pages(gsc_creds, googl_host_id, start_date, end_date)
    gsc_queries = get_gsc_queries(gsc_creds, googl_host_id, start_date, end_date)

    yandex_pages = get_yandex_pages(yandex_token.get('access_token'), uid, yandex_host_id, start_date, end_date)
    yandex_queries = get_yandex_queries(yandex_token.get('access_token'), uid, yandex_host_id, start_date, end_date)

    metrika_data = get_metrika_data(yandex_token.get('access_token'), counter, start_date, end_date)

    combined_pages = pd.merge(
        gsc_pages,
        yandex_pages,
        on='page',
        how='outer',
        suffixes=('_g', '_y')
    ).fillna(0)

    combined_pages = pd.merge(
        combined_pages,
        metrika_data,
        on="page",
        how="outer"
    ).fillna(0)

    combined_queries = pd.merge(
        gsc_queries,
        yandex_queries,
        on='query',
        how='outer',
        suffixes=('_g', '_y')
    ).fillna(0)

    combined_pages.to_excel("combined_pages.xlsx", index=False)


    return "domain_ok"
