# %% [markdown]
# # Plotly figures
#
# A [plotly](https://plotly.com/python/) figure shows on the page as it does in a
# notebook: you can zoom, pan, and read values on hover. The example needs no
# setup: show the figure as the last expression of a cell, or call `fig.show()`.
#
# In the dark color scheme, zallery draws the figure again with plotly's dark
# template merged into the figure's own. Switch the scheme to see it.
#
# zallery copies plotly.js next to the page from the plotly package installed for
# the build, so the page loads nothing from plotly's servers.

# %%
import plotly.express as px

tips = px.data.tips()
fig = px.bar(
    tips,
    x="sex",
    y="total_bill",
    color="smoker",
    facet_col="day",
    barmode="group",
    template="presentation+plotly",
)
fig.update_layout(height=400)
fig

# %% [markdown]
# Click a continent in this sunburst chart to zoom in on its countries:

# %%
countries = px.data.gapminder().query("year == 2007")
fig = px.sunburst(
    countries,
    path=["continent", "country"],
    values="pop",
    color="lifeExp",
    color_continuous_scale="RdBu",
    title="Life expectancy in 2007",
)
fig.show()

# %% [markdown]
# Figures made with the lower-level `graph_objects` API show the same way:

# %%
import plotly.graph_objects as go
from plotly.subplots import make_subplots

fig = make_subplots(rows=1, cols=2, specs=[[{}, {"type": "domain"}]])
fig.add_trace(go.Bar(x=[2024, 2025, 2026], y=[3, 2, 5], showlegend=False), 1, 1)
fig.add_trace(go.Pie(labels=["A", "B", "C"], values=[1, 3, 6]), 1, 2)
fig.update_layout(height=400, yaxis_title_text="revenue")
fig
