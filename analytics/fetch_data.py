from urllib.parse import urlparse

import httpx
import pandas as pd
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def gsc_fetch_all(creds: Credentials, site_url: str, start_date: str, end_date: str, dimension: str, page_filter):
    service = build("searchconsole", "v1", credentials=creds)

    LIMIT = 25000
    offset = 0

    results = []

    while True:
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": [dimension],
            "rowLimit": LIMIT,
            "startRow": offset
        }

        if page_filter is not None:
            body.update({
                'dimensionFilterGroups': [
                    {
                        'filters': [
                            {
                                'dimension': 'page',
                                'operator': 'contains',
                                'expression': page_filter,
                            },
                        ]
                    }
                ]
            })

        try:
            response = service.searchanalytics().query(
                siteUrl=site_url,
                body=body
            ).execute()
        except Exception as e:
            print(f"GSC error ({dimension}): {e}")
            break

        rows = response.get("rows", [])
        if not rows:
            break

        results.extend(rows)

        if len(rows) < LIMIT:
            break

        offset += LIMIT

    df = pd.DataFrame([
        {
            dimension: r["keys"][0],
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "ctr": r.get("ctr", 0),
            "position": r.get("position", 0),
        }
        for r in results
    ])

    len_ = len(df)

    if dimension == "page":
        df["page"] = df["page"].apply(lambda u: urlparse(u).path)

        df = df.groupby(["page"]).agg({
            "clicks": "sum",
            "impressions": "sum",
            "ctr": "mean",
            "position": "mean"
        }).reset_index()

    return df, len_


def get_gsc_pages(creds: Credentials, site_url: str, start_date: str, end_date: str, page_filter: str) -> pd.DataFrame:
    return gsc_fetch_all(creds, site_url, start_date, end_date, dimension="page", page_filter=page_filter)


def get_gsc_queries(creds: Credentials, site_url: str, start_date: str, end_date: str,
                    page_filter: str) -> pd.DataFrame:
    return gsc_fetch_all(creds, site_url, start_date, end_date, dimension="query", page_filter=page_filter)


def fetch_yandex_analytics_all(
        oauth_token: str,
        user_id: int,
        host_id: str,
        start_date: str,
        end_date: str,
        page_filter: str,
        text_type: str = "URL",  # "URL" или "QUERY"
        limit: int = 500,
        stop_iter_n: int = 50,
) -> pd.DataFrame:
    url = f"https://api.webmaster.yandex.net/v4/user/{user_id}/hosts/{host_id}/query-analytics/list"
    headers = {
        "Authorization": f"OAuth {oauth_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }

    all_rows = []
    offset = 0
    iter_n = 0

    while True:
        if iter_n > stop_iter_n:
            break

        payload = {
            'text_indicator': text_type,  # QUERY / URL
            'device_type_indicator': 'ALL',
            'date_from': start_date,
            'date_to': end_date,
            'offset': offset,
            'limit': limit,
        }

        if page_filter is not None:
            payload.update({
                "filters": {
                    "text_filters": [
                        {
                            "text_indicator": "URL",
                            "operation": "TEXT_CONTAINS",
                            "value": page_filter
                        }
                    ],
                }
            })

        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("text_indicator_to_statistics", [])
            if not items:
                break

            for item in items:
                query_value = item["text_indicator"]["value"]

                stats_by_date = {}

                for stat in item.get("statistics", []):
                    date = stat["date"]
                    field = stat["field"].lower()
                    value = stat["value"]

                    if date not in stats_by_date:
                        stats_by_date[date] = {"query": query_value, "date": date}

                    stats_by_date[date][field] = value

                all_rows.extend(stats_by_date.values())

            offset += limit
            iter_n += 1

        except Exception as e:
            print(f"Yandex analytics error at offset {offset}: {e}")
            break

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    if "ctr" in df.columns:
        df["ctr"] = df["ctr"] / 100

    if text_type == "URL":
        df["query"] = df["query"].apply(lambda u: urlparse(u).path)

    df = df.groupby(["query"]).agg({
        "clicks": "sum",
        "impressions": "sum",
        "ctr": "mean",
        "position": "mean"
    }).reset_index()

    if text_type == "URL":
        df = df.rename(columns={"query": "page"})

    return df


def get_yandex_pages(oauth_token: str, user_id: int, host_id: str, start_date: str, end_date: str, page_filter: str,
                     limit=500,
                     stop_iter_n=50):
    return fetch_yandex_analytics_all(oauth_token, user_id, host_id, start_date, end_date, text_type="URL", limit=limit,
                                      stop_iter_n=stop_iter_n, page_filter=page_filter)


def get_yandex_queries(oauth_token: str, user_id: int, host_id: str, start_date: str, end_date: str, page_filter: str,
                       limit=500,
                       stop_iter_n=50):
    return fetch_yandex_analytics_all(oauth_token, user_id, host_id, start_date, end_date, text_type="QUERY",
                                      limit=limit, stop_iter_n=stop_iter_n, page_filter=page_filter)


def get_metrika_data(
        token: str,
        counter_id: int,
        date1: str,
        date2: str,
        page_filter: str,
):
    url = "https://api-metrika.yandex.net/stat/v1/data"

    headers = {
        "Authorization": f"OAuth {token}",
    }

    params = {
        "id": counter_id,
        "date1": date1,
        "date2": date2,
        "metrics": "ym:s:visits,ym:s:pageDepth,ym:s:avgVisitDurationSeconds,ym:s:bounceRate,ym:s:sumGoalReachesAny",
        "dimensions": "ym:s:startURLPath",
        "filters": "ym:s:trafficSource=='organic'",
        "limit": 100000,
        "accuracy": 1,
    }

    if page_filter is not None:
        params.update({
            "filters": f"ym:s:trafficSource=='organic' AND ym:s:startURLPath=@'{page_filter}'"
        })

    resp = httpx.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    for item in data.get("data", []):
        dims = item["dimensions"]
        metrics = item["metrics"]

        page_path = dims[0]["name"]

        rows.append({
            "page": page_path,
            "visits": metrics[0],
            "page_depth": metrics[1],
            "avg_time_on_site": metrics[2],
            "bounce_rate": metrics[3],
            "total_actions": metrics[4],
        })

    df = pd.DataFrame(rows)
    return df
