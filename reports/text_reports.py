import collections
import string

import nltk
import numpy as np
import pandas as pd
from nltk.corpus import stopwords
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

nltk.download("stopwords")
STOPWORDS = stopwords.words("russian") + stopwords.words("english")

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def clean_string(text):
    translator = str.maketrans('', '', string.punctuation)
    clean_text = text.translate(translator)
    return clean_text


def preprocess_data(df):
    data = df.copy()
    data["query"] = data["query"].apply(clean_string)
    data["query_len"] = data["query"].apply(len)
    data["query_word_count"] = data["query"].apply(lambda q: len(q.split()))
    data["full_clicks"] = data["clicks_g"] + data["clicks_y"]
    data["full_impressions"] = data["impressions_g"] + data["impressions_y"]

    data["position_g"] = data["position_g"].apply(lambda v: 50 if v == 0.0 else min(v, 50))
    data["position_y"] = data["position_y"].apply(lambda v: 50 if v == 0.0 else min(v, 50))

    return data


def search_engine_comparison(df):
    data = df.copy()
    summary_stats = data[["clicks_g", "clicks_y", "impressions_g", "impressions_y",
                          "ctr_g", "ctr_y", "position_g", "position_y"]].agg(['mean', 'std', 'min', 'max', 'sum'])

    summary_stats.columns = ['Clicks Google', 'Clicks Yandex',
                             'Impressions Google', 'Impressions Yandex',
                             'CTR Google', 'CTR Yandex',
                             'Position Google', 'Position Yandex']

    return summary_stats


def search_engine_position_comparison(df):
    data = df.copy()
    bins = [0, 3, 6, 10, 15, 20, np.inf]
    labels = ["1-3", "4-6", "7-10", "11-15", "16-20", "20+"]
    data["position_interval_g"] = pd.cut(data["position_g"], bins=bins, labels=labels, include_lowest=True)
    data["position_interval_y"] = pd.cut(data["position_y"], bins=bins, labels=labels, include_lowest=True)

    position_interval_g_data = data[~data["position_interval_g"].isna()][
        ["clicks_g", "impressions_g", "ctr_g", "position_g", "position_interval_g"]]
    position_interval_y_data = data[~data["position_interval_y"].isna()][
        ["clicks_y", "impressions_y", "ctr_y", "position_y", "position_interval_y"]]

    position_interval_g_data = position_interval_g_data.groupby("position_interval_g", observed=True).agg({
        "clicks_g": "sum",
        "impressions_g": "sum",
        "ctr_g": "mean",
        "position_g": "count"
    }).reset_index().rename(columns={"position_g": "queries"})

    position_interval_y_data = position_interval_y_data.groupby("position_interval_y", observed=True).agg({
        "clicks_y": "sum",
        "impressions_y": "sum",
        "ctr_y": "mean",
        "position_y": "count"
    }).reset_index().rename(columns={"position_y": "queries"})

    ctr_g_pct = position_interval_g_data["ctr_g"] * 100
    ctr_y_pct = position_interval_y_data["ctr_y"] * 100

    GOOGLE_COLOR = '#4285F4'
    YANDEX_COLOR = '#FF0000'

    fig_dashboard = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Клики', 'Показы', 'CTR (%)', 'Запросы'),
        vertical_spacing=0.15,
        horizontal_spacing=0.15
    )

    fig_dashboard.add_trace(
        go.Bar(
            x=position_interval_g_data["position_interval_g"],
            y=position_interval_g_data["clicks_g"],
            name='Google',
            marker_color=GOOGLE_COLOR,
            showlegend=False
        ),
        row=1, col=1
    )
    fig_dashboard.add_trace(
        go.Bar(
            x=position_interval_y_data["position_interval_y"],
            y=position_interval_y_data["clicks_y"],
            name='Yandex',
            marker_color=YANDEX_COLOR,
            showlegend=False
        ),
        row=1, col=1
    )

    fig_dashboard.add_trace(
        go.Bar(
            x=position_interval_g_data["position_interval_g"],
            y=position_interval_g_data["impressions_g"],
            name='Google',
            marker_color=GOOGLE_COLOR,
            showlegend=False
        ),
        row=1, col=2
    )
    fig_dashboard.add_trace(
        go.Bar(
            x=position_interval_y_data["position_interval_y"],
            y=position_interval_y_data["impressions_y"],
            name='Yandex',
            marker_color=YANDEX_COLOR,
            showlegend=False
        ),
        row=1, col=2
    )

    fig_dashboard.add_trace(
        go.Scatter(
            x=position_interval_g_data["position_interval_g"],
            y=ctr_g_pct,
            name='Google',
            mode='lines+markers',
            line=dict(color=GOOGLE_COLOR, width=3),
            marker=dict(size=10, symbol='circle')
        ),
        row=2, col=1
    )
    fig_dashboard.add_trace(
        go.Scatter(
            x=position_interval_y_data["position_interval_y"],
            y=ctr_y_pct,
            name='Yandex',
            mode='lines+markers',
            line=dict(color=YANDEX_COLOR, width=3),
            marker=dict(size=10, symbol='circle')
        ),
        row=2, col=1
    )

    fig_dashboard.add_trace(
        go.Bar(
            x=position_interval_g_data["position_interval_g"],
            y=position_interval_g_data["queries"],
            name='Google',
            marker_color=GOOGLE_COLOR,
            opacity=0.8,
            showlegend=False
        ),
        row=2, col=2
    )
    fig_dashboard.add_trace(
        go.Bar(
            x=position_interval_y_data["position_interval_y"],
            y=position_interval_y_data["queries"],
            name='Yandex',
            marker_color=YANDEX_COLOR,
            opacity=0.8,
            showlegend=False
        ),
        row=2, col=2
    )

    fig_dashboard.update_layout(
        title_text='Сравнение Google и Yandex по интервалам позиций',
        height=700,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='lightgray',
            borderwidth=1
        ),
        hovermode='x unified',
        template='plotly_white'
    )

    fig_dashboard.update_yaxes(title_text="Клики", row=1, col=1)
    fig_dashboard.update_yaxes(title_text="Показы", row=1, col=2)
    fig_dashboard.update_yaxes(title_text="CTR (%)", row=2, col=1)
    fig_dashboard.update_yaxes(title_text="Количество запросов", row=2, col=2)

    return position_interval_g_data, position_interval_y_data, fig_dashboard


def define_important_words(df):
    data = df.copy()

    words = [q for query in data["query"].tolist() for q in query.split() if q not in STOPWORDS and q != " "]
    counter = collections.Counter(words)
    top_20_words = [w[0] for w in counter.most_common(20)]

    for w in top_20_words:
        data[w] = data["query"].str.contains(rf'\b{w}\b', regex=True, na=False).astype(int)

    result = {
        "word": [],
        "n_queries": [],
        "sum_clicks_g": [],
        "sum_clicks_y": [],
        "sum_impressions_g": [],
        "sum_impressions_y": [],
        "avg_ctr_g": [],
        "avg_ctr_y": [],
        "avg_position_g": [],
        "avg_position_y": [],
    }

    for w in top_20_words:
        mask = data[w].astype(bool)
        subset = data.loc[mask]

        result["word"].append(w)
        result["n_queries"].append(mask.sum())

        sum_clicks_g = subset["clicks_g"].sum()
        sum_impressions_g = subset["impressions_g"].sum()

        result["sum_clicks_g"].append(sum_clicks_g)
        result["sum_impressions_g"].append(sum_impressions_g)

        sum_clicks_y = subset["clicks_y"].sum()
        sum_impressions_y = subset["impressions_y"].sum()

        result["sum_clicks_y"].append(sum_clicks_y)
        result["sum_impressions_y"].append(sum_impressions_y)

        if sum_impressions_g > 0:
            weighted_ctr_g = (subset["ctr_g"] * subset["impressions_g"]).sum() / sum_impressions_g
        else:
            weighted_ctr_g = 0

        if sum_impressions_y > 0:
            weighted_ctr_y = (subset["ctr_y"] * subset["impressions_y"]).sum() / sum_impressions_y
        else:
            weighted_ctr_y = 0

        result["avg_ctr_g"].append(weighted_ctr_g)
        result["avg_ctr_y"].append(weighted_ctr_y)

        if sum_clicks_g > 0:
            weighted_position_g = (subset["position_g"] * subset["clicks_g"]).sum() / sum_clicks_g
        else:
            weighted_position_g = 0

        if sum_clicks_y > 0:
            weighted_position_y = (subset["position_y"] * subset["clicks_y"]).sum() / sum_clicks_y
        else:
            weighted_position_y = 0

        result["avg_position_g"].append(weighted_position_g)
        result["avg_position_y"].append(weighted_position_y)

    df_stats = pd.DataFrame(result)

    if df_stats.empty:
        return pd.DataFrame()

    df_stats["sum_clicks_all"] = df_stats["sum_clicks_g"] + df_stats["sum_clicks_y"]
    df_stats["sum_impressions_all"] = df_stats["sum_impressions_g"] + df_stats["sum_impressions_y"]
    df_stats["ctr_g_pct"] = df_stats["avg_ctr_g"] * 100
    df_stats["ctr_y_pct"] = df_stats["avg_ctr_y"] * 100
    df_stats["clicks_ratio_g_y"] = df_stats["sum_clicks_g"] / df_stats["sum_clicks_y"].replace(0, 1)
    df_stats["impressions_ratio_g_y"] = df_stats["sum_impressions_g"] / df_stats["sum_impressions_y"].replace(0, 1)

    df_stats = df_stats.sort_values(
        by=["sum_clicks_all", "sum_impressions_all"],
        ascending=[False, False]
    ).reset_index(drop=True)

    return df_stats


def create_normalized_transposed_heatmap(df_stats, top_n=20):
    # Сортировка по суммарным кликам
    df_sorted = df_stats.sort_values('sum_clicks_all', ascending=True).head(top_n)

    # Конфигурация метрик
    metrics_config = [
        ('n_queries', 'Запросы', 'log', False),
        ('sum_clicks_g', 'G:Клики', 'log', False),
        ('sum_clicks_y', 'Y:Клики', 'log', False),
        ('sum_impressions_g', 'G:Показы', 'log', False),
        ('sum_impressions_y', 'Y:Показы', 'log', False),
        ('ctr_g_pct', 'G:CTR%', 'linear', False),
        ('ctr_y_pct', 'Y:CTR%', 'linear', False),
        ('avg_position_g', 'G:Позиция', 'linear', True),
        ('avg_position_y', 'Y:Позиция', 'linear', True)
    ]

    x_labels = [name for _, name, _, _ in metrics_config]
    y_labels = df_sorted['word'].tolist()

    # RAW values
    z_raw = np.array([df_sorted[m[0]].values for m in metrics_config]).T

    # Normalized matrix
    z_norm = np.zeros_like(z_raw, dtype=float)

    for j, (metric_code, _, norm_type, reverse) in enumerate(metrics_config):
        column_values = z_raw[:, j]
        clean_values = column_values[~np.isnan(column_values)]

        if len(clean_values) == 0:
            continue

        if norm_type == 'log':
            log_values = np.log1p(clean_values)
            min_val, max_val = log_values.min(), log_values.max()
            if max_val > min_val:
                z_norm[:, j] = (np.log1p(column_values) - min_val) / (max_val - min_val)
        else:
            min_val, max_val = clean_values.min(), clean_values.max()
            if max_val > min_val:
                z_norm[:, j] = (column_values - min_val) / (max_val - min_val)

        if reverse:
            z_norm[:, j] = 1 - z_norm[:, j]

    # Формирование текстов
    text_data = []
    for i, word in enumerate(y_labels):
        row = []
        for j, (metric_code, _, _, _) in enumerate(metrics_config):
            raw = z_raw[i, j]

            if 'clicks' in metric_code or 'impressions' in metric_code or 'queries' in metric_code:
                if raw < 1000:
                    txt = f"{int(raw)}"
                elif raw < 1_000_000:
                    txt = f"{raw / 1000:.0f}K"
                else:
                    txt = f"{raw / 1_000_000:.1f}M"
            elif 'ctr' in metric_code:
                txt = f"{raw:.1f}%"
            elif 'position' in metric_code:
                txt = f"{raw:.1f}"
            else:
                txt = str(raw)

            row.append(txt)

        text_data.append(row)

    # Создание Heatmap
    fig = go.Figure(data=go.Heatmap(
        z=z_norm,
        x=x_labels,
        y=y_labels,
        colorscale='RdYlGn',
        zmin=0,
        zmax=1,
        text=text_data,
        texttemplate="%{text}",
        textfont={"size": 10, "color": "white"},
        hoverinfo="text",
        showscale=True,
        colorbar=dict(
            tickvals=[0, 0.5, 1],
            ticktext=["Низкое", "Среднее", "Высокое"]
        )
    ))

    # Вертикальные линии — теперь по категорическим значениям
    split_positions = ["G:Клики", "Y:Клики", "G:Показы", "Y:Показы"]
    for label in split_positions:
        fig.add_vline(x=label, line_width=1, line_color="white", opacity=0.8)

    # Layout
    fig.update_layout(
        title=f"Анализ топ-{top_n} ключевых слов",
        xaxis_title="Метрики (G: Google, Y: Яндекс)",
        yaxis_title="Ключевые слова",
        height=700,
        width=1000,
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=11)
        ),
        yaxis=dict(
            tickfont=dict(size=11)
        )
    )

    return fig


def plot_top_words_plotly(model, feature_names, n_top_words, title,
                          n_rows=2, n_cols=5, height=800, width=1600):
    n_topics = model.components_.shape[0]

    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=[f"Тема {i + 1}" for i in range(n_topics)],
        vertical_spacing=0.12,
        horizontal_spacing=0.08
    )

    for topic_idx, topic in enumerate(model.components_):
        row = (topic_idx // n_cols) + 1
        col = (topic_idx % n_cols) + 1

        top_features_ind = topic.argsort()[-n_top_words:]
        top_features = feature_names[top_features_ind].tolist()
        weights = topic[top_features_ind].tolist()

        sorted_indices = sorted(range(len(weights)), key=lambda i: weights[i])
        top_features = [top_features[i] for i in sorted_indices]
        weights = [weights[i] for i in sorted_indices]

        fig.add_trace(
            go.Bar(
                x=weights,
                y=top_features,
                orientation='h',
                marker_color='#1f77b4',
                text=[f"{w:.3f}" for w in weights],
                textposition='outside',
                textfont=dict(size=10, color='black'),
                hovertemplate="<b>%{y}</b><br>Вес: %{x:.4f}<extra></extra>"
            ),
            row=row, col=col
        )

        fig.update_xaxes(
            title_text="Вес",
            row=row, col=col,
            title_font=dict(size=12),
            tickfont=dict(size=10, color='black')
        )

        fig.update_yaxes(
            row=row, col=col,
            tickfont=dict(size=10, color='black')
        )

    fig.update_layout(
        title_text=title,
        title_font=dict(size=20, color='black'),
        height=height,
        width=width,
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='black')
    )

    for i in range(n_topics):
        fig.layout.annotations[i].update(font=dict(size=14, color='black'))

    return fig


def topic_modeling(df):
    n_features = 1000
    n_components = 10
    n_top_words = 20
    init = "nndsvda"

    data = df.copy()
    queries = data["query"].tolist()

    tfidf_vectorizer = TfidfVectorizer(
        max_df=0.95, min_df=5, max_features=n_features, stop_words=list(STOPWORDS)
    )

    tfidf = tfidf_vectorizer.fit_transform(queries)

    nmf = NMF(
        n_components=n_components,
        random_state=1,
        init=init,
        beta_loss="frobenius",
        alpha_W=0.00005,
        alpha_H=0.00005,
        l1_ratio=1,
    ).fit(tfidf)

    tfidf_feature_names = tfidf_vectorizer.get_feature_names_out()
    fig = plot_top_words_plotly(
        nmf, tfidf_feature_names, n_top_words, "Тематическое моделирование"
    )

    return fig


def get_long_tail_queries(df):
    long_tails_queries = df[
        (df['query_word_count'].isin([6, 7, 8, 9, 10])) &
        ((df['position_g'] < 20) & (df['position_y'] < 20)) &
        ((df['position_g'] > 5) & (df['position_y'] > 5)) &
        ((df['position_g'] != 0) & (df['position_y'] != 0))].sort_values(by=["full_impressions"], ascending=False).iloc[
        :20, :]

    return long_tails_queries


def get_text_report(df):
    df = df.copy()
    result = {}

    try:
        df = preprocess_data(df)
        result['preprocessed_data'] = df
    except Exception as e:
        result['preprocessed_data_error'] = f"Ошибка предобработки: {str(e)}"
        result['preprocessed_data'] = None

    try:
        comparison_df = search_engine_comparison(df)
        result['comparison_df'] = comparison_df
    except Exception as e:
        result['comparison_df_error'] = f"Ошибка сравнения поисковиков: {str(e)}"
        result['comparison_df'] = None

    try:
        position_interval_g_data_df, position_interval_y_data_df, fig_dashboard_plot = search_engine_position_comparison(
            df)
        result['position_interval_g_data_df'] = position_interval_g_data_df
        result['position_interval_y_data_df'] = position_interval_y_data_df
        result['fig_dashboard_plot'] = fig_dashboard_plot
    except Exception as e:
        result['position_comparison_error'] = f"Ошибка сравнения позиций: {str(e)}"
        result['position_interval_g_data_df'] = None
        result['position_interval_y_data_df'] = None
        result['fig_dashboard_plot'] = None

    try:
        important_words_stats_df = define_important_words(df)
        result['important_words_stats_df'] = important_words_stats_df
    except Exception as e:
        result['important_words_error'] = f"Ошибка анализа важных слов: {str(e)}"
        result['important_words_stats_df'] = None

    try:
        if result.get('important_words_stats_df') is not None:
            important_words_stats_heatmap_plot = create_normalized_transposed_heatmap(important_words_stats_df)
            result['important_words_stats_heatmap_plot'] = important_words_stats_heatmap_plot
        else:
            result['important_words_stats_heatmap_plot'] = None
            result['heatmap_error'] = "Не удалось создать heatmap: нет данных о словах"
    except Exception as e:
        result['heatmap_error'] = f"Ошибка создания heatmap: {str(e)}"
        result['important_words_stats_heatmap_plot'] = None
        print(str(e))

    try:
        plot_top_words_plotly_plot = topic_modeling(df)
        result['plot_top_words_plotly_plot'] = plot_top_words_plotly_plot
    except Exception as e:
        result['topic_modeling_error'] = f"Ошибка тематического моделирования: {str(e)}"
        result['plot_top_words_plotly_plot'] = None

    try:
        long_tails_queries_df = get_long_tail_queries(df)
        result['long_tails_queries_df'] = long_tails_queries_df
    except Exception as e:
        result['long_tail_error'] = f"Ошибка анализа длинных хвостов: {str(e)}"
        result['long_tails_queries_df'] = None

    return result
