import datetime
import math
import os.path
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from napari_dashboard.db_update.util import setup_cache
from napari_dashboard.gen_stat.conda import (
    get_conda_latest_download_info,
    get_conda_total_download_info,
    get_total_conda_download,
)
from napari_dashboard.gen_stat.generate_excel_file import generate_excel_file
from napari_dashboard.gen_stat.github import (
    calc_stars_per_day_cumulative,
    generate_basic_stats,
    generate_contributors_stats,
)
from napari_dashboard.gen_stat.imagesc import get_topics_count
from napari_dashboard.gen_stat.pypi import (
    add_country_info,
    add_plot_info,
    get_active_packages,
    get_download_info,
    get_download_per_operating_system,
    get_download_per_python_version,
    get_pepy_download_per_day,
    get_recent_releases_date,
    get_total_pypi_download,
    is_country,
)

TEMPLATE_DIR = Path(__file__).parent / "webpage_tmpl"
LABELS = [
    "bugfix",
    "feature",
    "documentation",
    "performance",
    "enhancement",
    "maintenance",
]


def get_plugin_count():
    return len(requests.get("https://api.napari.org/api/plugins").json())


LEGEND_POS = {"x": 0.01, "y": 0.95}


def generate_issue_plot(stats: dict):
    plot = go.Figure()
    plot.add_trace(
        go.Scatter(
            x=stats["pr_issue_time_stats"]["days"],
            y=stats["pr_issue_time_stats"]["issues_open_cumulative"],
            mode="lines",
            name="Issues open",
        )
    )
    plot.add_trace(
        go.Scatter(
            x=stats["pr_issue_time_stats"]["days"],
            y=stats["pr_issue_time_stats"]["issues_closed_cumulative"],
            mode="lines",
            name="Issues close",
        )
    )
    plot.update_layout(legend=LEGEND_POS)

    return plot.to_html(full_html=False, include_plotlyjs="cdn")


def generate_issue_plot2(stats: dict):
    plot = go.Figure()
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"],
            y=stats["pr_issue_time_stats"]["issues_open_weekly"],
            name="Issues open per week",
        )
    )
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"],
            y=stats["pr_issue_time_stats"]["issues_closed_weekly"],
            name="Issues close per week",
        )
    )
    plot.update_layout(legend=LEGEND_POS)
    return plot.to_html(full_html=False, include_plotlyjs="cdn")


def generate_pull_request_plot(stats: dict):
    plot = go.Figure()
    plot.add_trace(
        go.Scatter(
            x=stats["pr_issue_time_stats"]["days"],
            y=stats["pr_issue_time_stats"]["pr_open_cumulative"],
            mode="lines",
            name="Pull Requests open",
        )
    )
    plot.add_trace(
        go.Scatter(
            x=stats["pr_issue_time_stats"]["days"],
            y=stats["pr_issue_time_stats"]["pr_closed_cumulative"],
            mode="lines",
            name="Pull Requests close",
        )
    )
    plot.add_trace(
        go.Scatter(
            x=stats["pr_issue_time_stats"]["days"],
            y=stats["pr_issue_time_stats"]["pr_merged_cumulative"],
            mode="lines",
            name="Pull Requests merged",
        )
    )
    plot.update_layout(legend=LEGEND_POS)
    return plot.to_html(full_html=False, include_plotlyjs="cdn")


def generate_pull_request_plot2(stats: dict):
    plot = go.Figure()
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"],
            y=stats["pr_issue_time_stats"]["pr_open_weekly"],
            name="Pull Requests open per week",
        )
    )
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"],
            y=stats["pr_issue_time_stats"]["pr_closed_weekly"],
            name="Pull Requests close per week",
        )
    )
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"],
            y=stats["pr_issue_time_stats"]["pr_merged_weekly"],
            name="Pull Requests merged per week",
        )
    )
    plot.update_layout(legend=LEGEND_POS)
    return plot.to_html(full_html=False, include_plotlyjs="cdn")


def generate_pull_request_plot3(stats: dict, since: datetime.datetime):
    last_week_count = -(datetime.datetime.now() - since).days // 7
    plot = go.Figure()
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"][last_week_count:],
            y=stats["pr_issue_time_stats"]["pr_merged_feature_weekly"][
                last_week_count:
            ],
            name="Merged features",
        )
    )
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"][last_week_count:],
            y=stats["pr_issue_time_stats"]["pr_merged_enhancement_weekly"][
                last_week_count:
            ],
            name="Merged enhancements",
        )
    )
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"][last_week_count:],
            y=stats["pr_issue_time_stats"]["pr_merged_bugfix_weekly"][
                last_week_count:
            ],
            name="Merged bugfix",
        )
    )
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"][last_week_count:],
            y=stats["pr_issue_time_stats"]["pr_merged_maintenance_weekly"][
                last_week_count:
            ],
            name="Merged maintenance",
        )
    )
    plot.update_layout(
        legend=LEGEND_POS,
        barmode="stack",
        yaxis_title="number of merged pull requests per week",
    )
    return plot.to_html(full_html=False, include_plotlyjs="cdn")


def calc_fraction_of_pr(stats, total):
    return [x / t * 100 if t > 0 else 0 for x, t in zip(stats, total)]


def generate_pull_request_plot4(stats: dict, since: datetime.datetime):
    last_week_count = -(datetime.datetime.now() - since).days // 7
    aggregated_data = [
        sum(x)
        for x in zip(
            stats["pr_issue_time_stats"]["pr_merged_feature_weekly"],
            stats["pr_issue_time_stats"]["pr_merged_enhancement_weekly"],
            stats["pr_issue_time_stats"]["pr_merged_bugfix_weekly"],
            stats["pr_issue_time_stats"]["pr_merged_maintenance_weekly"],
        )
    ]
    plot = go.Figure()
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"][last_week_count:],
            y=calc_fraction_of_pr(
                stats["pr_issue_time_stats"]["pr_merged_feature_weekly"],
                aggregated_data,
            )[last_week_count:],
            name="Merged features",
        )
    )
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"][last_week_count:],
            y=calc_fraction_of_pr(
                stats["pr_issue_time_stats"]["pr_merged_enhancement_weekly"],
                aggregated_data,
            )[last_week_count:],
            name="Merged enhancements",
        )
    )
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"][last_week_count:],
            y=calc_fraction_of_pr(
                stats["pr_issue_time_stats"]["pr_merged_bugfix_weekly"],
                aggregated_data,
            )[last_week_count:],
            name="Merged bugfix",
        )
    )
    plot.add_trace(
        go.Bar(
            x=stats["pr_issue_time_stats"]["weeks"][last_week_count:],
            y=calc_fraction_of_pr(
                stats["pr_issue_time_stats"]["pr_merged_maintenance_weekly"],
                aggregated_data,
            )[last_week_count:],
            name="Merged maintenance",
        )
    )
    plot.update_layout(
        # legend=LEGEND_POS,
        barmode="stack",
        yaxis_title="fraction of merged pull requests per week [%]",
    )
    return plot.to_html(full_html=False, include_plotlyjs="cdn")


def generate_pull_request_plot5(stats: dict, since: datetime.datetime):
    last_week_count = -(datetime.datetime.now() - since).days // 7
    aggregated_data = [
        sum(x)
        for x in zip(
            stats["pr_issue_time_stats"]["pr_merged_feature_weekly"],
            stats["pr_issue_time_stats"]["pr_merged_enhancement_weekly"],
        )
    ]
    fraction = calc_fraction_of_pr(
        aggregated_data, stats["pr_issue_time_stats"]["pr_merged_weekly"]
    )

    plot = go.Figure()
    plot.add_trace(
        go.Scatter(
            x=stats["pr_issue_time_stats"]["weeks"][last_week_count:],
            y=fraction[last_week_count:],
            mode="lines",
            name="fraction of features and enhancements",
        )
    )
    plot.update_layout(
        # legend=LEGEND_POS,
        yaxis_title="fraction of merged pull requests<br>that are feature/enhancement per week [%]"
    )
    return plot.to_html(full_html=False, include_plotlyjs="cdn")


def generate_stars_plot(stars: dict):
    plot = go.Figure()
    plot.add_trace(
        go.Scatter(
            x=stars["day"], y=stars["stars"], mode="lines", name="Stars"
        )
    )
    plot.update_layout(legend=LEGEND_POS)
    return plot.to_html(full_html=False, include_plotlyjs="cdn")


def generate_download_per_day(napari_downloads_per_day):
    df_downloads = pd.DataFrame(
        napari_downloads_per_day.items(), columns=["date", "downloads"]
    )
    return px.line(df_downloads, x="date", y="downloads").to_html(
        full_html=False, include_plotlyjs="cdn"
    )


def generate_python_version_pie_chart(python_version_info):
    df = pd.DataFrame(python_version_info, columns=["version", "downloads"])
    return px.pie(df, values="downloads", names="version").to_html(
        full_html=False, include_plotlyjs="cdn"
    )


def generate_os_pie_chart(python_version_info):
    df = pd.DataFrame(python_version_info, columns=["os", "downloads"])
    return px.pie(df, values="downloads", names="os").to_html(
        full_html=False, include_plotlyjs="cdn"
    )


def generate_download_map():
    data = pd.read_csv(
        os.path.join(os.path.dirname(__file__), "data", "countries.csv")
    )
    data = data[data.COUNTRY_CODE.map(is_country)]
    data[["iso_alpha", "country_name"]] = data.apply(
        add_country_info, axis=1, result_type="expand"
    )
    data[["log_download", "text"]] = data.apply(
        add_plot_info(data), axis=1, result_type="expand"
    )

    log_download_max = math.ceil(data["log_download"].max())

    return go.Figure(
        data=go.Choropleth(
            locations=data["iso_alpha"],
            z=data["log_download"].astype(float),
            locationmode="ISO-3",
            colorscale="viridis",
            autocolorscale=False,
            text=data["text"],  # hover text
            # marker_line_color='white', # line markers between states
            hovertemplate="%{text}<extra>%{location}</extra>",
            colorbar={
                "title": "downloads",
                "tickvals": list(range(log_download_max)),
                "ticktext": [10**x for x in range(log_download_max)],
                "tickmode": "array",
            },
        ),
        layout={"height": 600},
    ).to_html(full_html=False, include_plotlyjs="cdn")


def generate_webpage(
    target_path: Path,
    db_path: Path,
    date: datetime.datetime,
    dump_excel: bool = True,
) -> None:
    """
    Generate webpage from template

    Parameters
    ----------
    target_path: Path
        Path where to save the generated webpage
    """
    target_path.mkdir(parents=True, exist_ok=True)
    print(f"db path {db_path.absolute()}, sqlite://{db_path.absolute()}")
    engine = create_engine(f"sqlite:///{db_path.absolute()}")
    setup_cache(timeout=60 * 60 * 4)

    skip_plugins = {"PartSeg", "skan"}
    plugins = requests.get("https://api.napari.org/api/plugins").json()
    valid_plugins = {x for x in plugins if x not in skip_plugins}

    with Session(engine) as session:
        stats = generate_basic_stats("napari", "napari", session, date, LABELS)
        stars = calc_stars_per_day_cumulative("napari", "napari", session)
        stats["stars"] = stars["stars"][-1]
        stats["contributors"] = generate_contributors_stats(
            [("napari", "napari"), ("napari", "docs"), ("napari", "npe2")],
            session,
            date,
        )
        forums_stats = get_topics_count(date, session)
        pypi_download_info = get_download_info(
            session, ["napari", "npe2", "napari-plugin-manager"]
        )
        napari_downloads_per_day = get_pepy_download_per_day(session, "napari")
        active_plugin_stats = get_active_packages(
            session, packages=valid_plugins, threshold=1500
        )
        all_plugin_downloads_from_pypi = get_total_pypi_download(
            session, valid_plugins
        )
        all_plugin_downloads_from_conda = get_total_conda_download(
            session, valid_plugins
        )
        under_active_development = get_recent_releases_date(
            session, valid_plugins, date
        )
        conda_download_info = {
            "Total": get_conda_total_download_info(
                session, {"napari", "npe2", "napari-plugin-manager"}
            ),
            "Last version": get_conda_latest_download_info(
                session, {"napari", "npe2", "napari-plugin-manager"}
            ),
        }
        python_version_info = get_download_per_python_version(
            session, "napari", date
        )
        os_info = get_download_per_operating_system(session, "napari", date)

    # Data to be rendered
    data = {
        "title": "Napari dashboard",
        "project": "Napari",
        "author": "Grzegorz Bokota",
        "stats": stats,
        "napari_downloads_per_day_dates": [
            x.isoformat() for x in napari_downloads_per_day
        ],
        "napari_downloads_per_day_values": list(
            napari_downloads_per_day.values()
        ),
        "today": datetime.datetime.now().strftime("%Y-%m-%d"),
        "base_day": date.strftime("%Y-%m-%d"),
        "pypi_downloads": pypi_download_info,
        "forum": forums_stats,
        "conda_downloads": conda_download_info,
        "plugins": {
            "count": get_plugin_count(),
            "all_plugin_downloads_from_pypi": all_plugin_downloads_from_pypi,
            "all_plugin_downloads_from_conda": all_plugin_downloads_from_conda,
            "active": len(active_plugin_stats),
            "under_active_development": under_active_development,
            "skip": skip_plugins,
        },
        "py_version": generate_python_version_pie_chart(python_version_info),
        "os_plot": generate_os_pie_chart(os_info),
        "napari_downloads_per_day": generate_download_per_day(
            napari_downloads_per_day
        ),
        "issue_activity": generate_issue_plot(stats),
        "issue_activity2": generate_issue_plot2(stats),
        "pr_activity_plot": generate_pull_request_plot(stats),
        "pr_activity_plot2": generate_pull_request_plot2(stats),
        "pr_activity_plot3": generate_pull_request_plot3(stats, date),
        "pr_activity_plot4": generate_pull_request_plot4(stats, date),
        "pr_activity_plot5": generate_pull_request_plot5(stats, date),
        "stars_plot": generate_stars_plot(stars),
        "download_map": generate_download_map(),
    }
    print("generating webpage")

    # Create an environment
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    # Load the template
    index_template = env.get_template("index.html")
    dashboard_css_template = env.get_template("dashboard.css")
    color_mode_template = env.get_template("color-modes.js")

    # Render the template with data
    with open(target_path / "index.html", "w") as f:
        f.write(index_template.render(data))

    with open(target_path / "dashboard.css", "w") as f:
        f.write(dashboard_css_template.render(data))

    with open(target_path / "color-modes.js", "w") as f:
        f.write(color_mode_template.render(data))

    if dump_excel:
        print("Save data to excel")

        with Session(engine) as session:
            generate_excel_file(target_path / "napari_dashboard.xlsx", session)

    # Print the rendered HTML


# conda download stats
# plugin download stats
# more plots
