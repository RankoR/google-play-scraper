"""Payload fixtures shaped like the real Google Play responses.

Search results and list clusters share one app-entry layout, so both suites build
entries from here. Keep the indices in sync with `client.OVERVIEW_SPECS`.
"""


def make_app_entry(
    app_id: str | None,
    title: str,
    price_micros: int = 0,
    price_text: str = "",
    currency: str = "USD",
):
    """Build one app entry as Play sends it: a single-element list wrapping the data."""
    inner = [None] * 15
    if app_id is not None:
        inner[0] = [app_id, 7]
    inner[1] = [None, None, None, [None, None, "https://img.test/icon.png"]]
    inner[3] = title
    inner[4] = ["4.5", 4.5]
    inner[8] = [None, [[price_micros, currency, price_text]]]
    inner[13] = [None, f"{title} summary"]
    inner[14] = f"{title} Dev"
    return [inner]


def make_search_page(entries, depth_index: int = 0):
    """Wrap entries the way a parsed search page nests them.

    Play puts the cluster at ds:4[0][1][0][22][0] for some queries and at
    ds:4[0][1][1][22][0] for others, so `depth_index` exercises both.
    """
    cluster_holder = [None] * 23
    cluster_holder[22] = [entries]

    branches = [None] * (depth_index + 1)
    branches[depth_index] = cluster_holder
    return {"ds:4": [[None, branches]]}
