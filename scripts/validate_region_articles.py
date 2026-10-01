"""Validate complete, exact Wikipedia coverage for every mapped region.

Map features are not article identities: Natural Earth can represent one named
administrative area with several features.  The durable identity used by the
atlas and browser is ``<country code>|<region name>``.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit(features, titles, articles):
    feature_keys = [f'{row["properties"]["code"]}|{row["properties"]["name"]}' for row in features]
    mapped = set(feature_keys)
    title_keys = set(titles)
    article_keys = set(articles)
    title_owners = defaultdict(list)
    for key, title in titles.items():
        if isinstance(title, str) and title.strip():
            title_owners[title.strip().casefold()].append(key)

    malformed_articles = []
    request_mismatches = []
    for key in sorted(mapped & article_keys):
        article = articles[key]
        if article is None:
            continue
        required = ("title", "extract", "url", "license", "license_url")
        if not isinstance(article, dict) or any(not article.get(field) for field in required):
            malformed_articles.append(key)
            continue
        # Older durable snapshots predate requested_title.  Their resolved
        # title remains sufficient when it exactly equals the reviewed mapping.
        saved_request = article.get("requested_title") or article["title"]
        if key in titles and saved_request != titles[key]:
            request_mismatches.append(key)

    return {
        "feature_count": len(feature_keys),
        "region_count": len(mapped),
        "multipart_regions": sorted(key for key, count in Counter(feature_keys).items() if count > 1),
        "missing_title_keys": sorted(mapped - title_keys),
        "extra_title_keys": sorted(title_keys - mapped),
        "blank_title_keys": sorted(key for key in mapped & title_keys
                                   if not isinstance(titles[key], str) or not titles[key].strip()),
        # Same-country labels can intentionally describe duplicate Natural
        # Earth entities/transliterations with one page. Cross-country title
        # reuse is almost always an ambiguous or incorrect mapping.
        "duplicate_titles": {
            title: sorted(keys) for title, keys in sorted(title_owners.items())
            if len({key.split("|", 1)[0] for key in keys}) > 1
        },
        "missing_article_keys": sorted(mapped - article_keys),
        "extra_article_keys": sorted(article_keys - mapped),
        "null_article_keys": sorted(key for key in mapped & article_keys if articles[key] is None),
        "malformed_article_keys": malformed_articles,
        "request_mismatch_keys": request_mismatches,
    }


def failures(report):
    informational = {"feature_count", "region_count", "multipart_regions"}
    return {key: value for key, value in report.items() if key not in informational and value}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the full machine-readable audit")
    args = parser.parse_args()
    features = read(ROOT / "web" / "data" / "regions.geojson")["features"]
    titles = read(ROOT / "research" / "region_article_titles.json")
    articles = read(ROOT / "research" / "wiki_articles.json").get("regions", {})
    report = audit(features, titles, articles)
    incomplete = failures(report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f'{report["region_count"]} distinct regions from {report["feature_count"]} map features')
        print(f'{report["region_count"] - len(report["null_article_keys"]) - len(report["missing_article_keys"])} '
              f'non-null article entries')
        for name, values in incomplete.items():
            print(f"{name}: {len(values)}")
    if incomplete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
