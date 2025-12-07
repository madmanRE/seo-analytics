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
from reports.text_reports import get_text_report


def full_pipline(domain, gsc_creds, yandex_token, counter, page_filter):
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

    # ===========   QUERIES   ===========
    gsc_queries, query_cnt = get_gsc_queries(gsc_creds, googl_host_id, start_date, end_date, page_filter=page_filter)
    yandex_queries = get_yandex_queries(yandex_token.get('access_token'), uid, yandex_host_id, start_date, end_date, stop_iter_n=query_cnt // 500 + 2, page_filter=page_filter)

    combined_queries = pd.merge(
        gsc_queries,
        yandex_queries,
        on='query',
        how='outer',
        suffixes=('_g', '_y')
    ).fillna(0)

    text_reports = get_text_report(combined_queries)

    # ===========   PAGES   ===========
    # gsc_pages, page_cnt = get_gsc_pages(gsc_creds, googl_host_id, start_date, end_date, page_filter=page_filter)
    # yandex_pages = get_yandex_pages(yandex_token.get('access_token'), uid, yandex_host_id, start_date, end_date, stop_iter_n=page_cnt // 500 + 2, page_filter=page_filter)
    # metrika_data = get_metrika_data(yandex_token.get('access_token'), counter, start_date, end_date, page_filter=page_filter)
    #
    # combined_pages = pd.merge(
    #     gsc_pages,
    #     yandex_pages,
    #     on='page',
    #     how='outer',
    #     suffixes=('_g', '_y')
    # ).fillna(0)
    #
    # combined_pages = pd.merge(
    #     combined_pages,
    #     metrika_data,
    #     on="page",
    #     how="outer"
    # ).fillna(0)

    return text_reports
