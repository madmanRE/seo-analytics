from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from google.oauth2.credentials import Credentials
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional

from analytics.pipline import full_pipline
from auth.auth_router import auth_router

app = FastAPI()
app.include_router(auth_router)

app.add_middleware(SessionMiddleware, secret_key="qW4vX1TOaZEZ_laSFf4nMfox7rhDe9_Cv9zfPcpgT6c")

templates = Jinja2Templates(directory="templates")


@app.get("/")
async def index(request: Request):
    gsc_token = request.session.get("google_token")
    yandex_token = request.session.get("yandex_token")
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "gsc_token": gsc_token, "yandex_token": yandex_token}
    )


@app.post("/analytics")
async def analyze_traffic(
        request: Request,
        domain: str = Form(...),
        counter: str = Form(...),
        page_filter: Optional[str] = Form(None)
):
    gsc_data = request.session["google_token"]
    gsc_data_corrected = gsc_data.copy()
    gsc_data_corrected["token"] = gsc_data_corrected.pop("access_token")

    gsc_creds = Credentials(**gsc_data_corrected)
    yandex_token = request.session["yandex_token"]

    result = full_pipline(domain, gsc_creds, yandex_token, counter, page_filter)

    return templates.TemplateResponse(
        "report.html",
        {
            "request": request,
            "comparison_df": result.get('comparison_df'),
            "position_interval_g_data_df": result.get('position_interval_g_data_df'),
            "position_interval_y_data_df": result.get('position_interval_y_data_df'),
            "fig_dashboard_plot": result.get('fig_dashboard_plot'),
            "important_words_stats_df": result.get('important_words_stats_df'),
            "important_words_stats_heatmap_plot": result.get('important_words_stats_heatmap_plot'),
            "plot_top_words_plotly_plot": result.get('plot_top_words_plotly_plot'),
            "long_tails_queries_df": result.get('long_tails_queries_df')
        }
    )
