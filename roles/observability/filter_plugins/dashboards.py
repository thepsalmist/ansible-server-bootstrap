def add_sections(dashboard, sections):
    panels = dashboard["panels"]
    at = next(
        i
        for i, p in enumerate(panels)
        if p["type"] == "row" and p["title"] == "Traffic"
    )
    start = top = panels[at]["gridPos"]["y"]
    added = []
    for section in sections:
        added += [moved(p, top) for p in section["panels"]]
        top += max(p["gridPos"]["y"] + p["gridPos"]["h"] for p in section["panels"])
    variables = dashboard["templating"]["list"] + [
        v for s in sections for v in s["templating"]
    ]
    return {
        **dashboard,
        "panels": panels[:at] + added + [moved(p, top - start) for p in panels[at:]],
        "templating": {**dashboard["templating"], "list": variables},
    }


def moved(panel, by):
    return {**panel, "gridPos": {**panel["gridPos"], "y": panel["gridPos"]["y"] + by}}


class FilterModule:
    def filters(self):
        return {"add_sections": add_sections}
