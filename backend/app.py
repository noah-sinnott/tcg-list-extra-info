"""
Flask application – thin route handler.
All business logic lives in browser_service, card_matcher and tcgcsv_service.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, request, jsonify
from flask_cors import CORS

from tcgcsv_service import TCGCSVService
from browser_service import start_browser, get_shared_browser, run_async, scrape_all_lists
from card_matcher import normalize_text, get_card_details

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
    }
})

tcgcsv_service = TCGCSVService()

# Pre-load the shared Playwright browser in a background thread
start_browser()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@app.route("/api/scrape", methods=["POST"])
def scrape_list():
    """Scrape one or more mytcgcollection lists and match cards to TCGPlayer data."""
    try:
        data = request.get_json()

        # Support legacy single-URL format
        sources = data.get("sources", [])
        if not sources and data.get("url"):
            sources = [{"url": data["url"], "name": "List 1"}]

        if not sources:
            return jsonify({"error": "At least one URL is required"}), 400

        for src in sources:
            url = src.get("url", "")
            if not url:
                return jsonify({"error": "Each source must have a URL"}), 400
            if not url.startswith("https://mytcgcollection.com/"):
                return jsonify({"error": f"Invalid URL: {url}. Must be a mytcgcollection.com list URL"}), 400

        # Fetch TCGPlayer groups (cached)
        print("Fetching TCGPlayer groups...")
        all_groups = tcgcsv_service.get_groups()
        if not all_groups:
            return jsonify({"error": "Failed to fetch TCGPlayer groups"}), 500

        # ---- Step 1: Concurrent scraping ----
        print("\nStarting concurrent scraping of lists...")
        browser = _wait_for_browser(timeout=15.0)

        if browser is None:
            scrape_results = _fallback_scrape(sources)
        else:
            try:
                scrape_results = run_async(scrape_all_lists(sources, browser))
            except Exception as exc:
                print(f"Error running async scraper: {exc}")
                scrape_results = [(s.get("name", "Unknown Source"), {}) for s in sources]

        # ---- Deduplicate cards ----
        dedupe_map = {}
        total_raw = 0
        for source_name, cards_by_set in scrape_results:
            if not cards_by_set:
                print(f"  No cards found for {source_name}")
                continue
            for set_name, cards in cards_by_set.items():
                for card in cards:
                    total_raw += 1
                    key = _dedupe_key(card)
                    if key not in dedupe_map:
                        dedupe_map[key] = {
                            "card_info": card,
                            "set_names": {set_name},
                            "sources": {source_name},
                        }
                    else:
                        dedupe_map[key]["sources"].add(source_name)
                        dedupe_map[key]["set_names"].add(set_name)

        print(f"  Found {total_raw} raw cards, {len(dedupe_map)} unique after dedupe")

        # ---- Step 2: Parallel card lookup ----
        products_cache = {}
        all_results = _lookup_cards(dedupe_map, all_groups, products_cache)

        print(f"\n=== Completed: {len(all_results)} cards matched from {len(sources)} list(s) ===")

        return jsonify({
            "success": True,
            "cards": all_results,
            "total": len(all_results),
            "matched": len(all_results),
        })

    except Exception as exc:
        print(f"Error: {exc}")
        return jsonify({"error": f"An error occurred: {exc}"}), 500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_browser(timeout=15.0):
    """Block until the shared browser is ready or *timeout* elapses."""
    waited = 0.0
    while get_shared_browser() is None and waited < timeout:
        time.sleep(0.25)
        waited += 0.25
    return get_shared_browser()


def _fallback_scrape(sources):
    """Run the async scraper in-process when the background browser isn't available."""
    import asyncio
    try:
        return asyncio.run(scrape_all_lists(sources, None))
    except Exception as exc:
        print(f"Fallback scraper error: {exc}")
        return [(s.get("name", "Unknown Source"), {}) for s in sources]


def _dedupe_key(card):
    """Build a deduplication key from a card's number + normalised name."""
    num = (card.get("number", "").lstrip("0") or "0")
    name = normalize_text(card.get("name", ""))
    return f"{num}|{name}"


def _lookup_cards(dedupe_map, all_groups, products_cache):
    """Look up all unique cards in parallel and return matched results."""
    total = len(dedupe_map)
    print(f"\nProcessing {total} unique cards...")
    results = []

    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_key = {}
        for key, info in dedupe_map.items():
            chosen_set = next(iter(info["set_names"]))
            fut = executor.submit(
                get_card_details,
                info["card_info"],
                chosen_set,
                all_groups,
                products_cache,
                tcgcsv_service,
            )
            future_to_key[fut] = key

        completed = 0
        for future in as_completed(future_to_key):
            completed += 1
            if completed % 10 == 0 or completed == total:
                print(f"  Progress: {completed}/{total} cards processed")

            key = future_to_key[future]
            info = dedupe_map[key]
            try:
                details = future.result()
                if details:
                    src_list = sorted(info["sources"])
                    details["source_names"] = src_list
                    details["source_name"] = ", ".join(src_list)
                    results.append(details)
            except Exception as exc:
                print(f"  Error processing {info['card_info'].get('name', '')}: {exc}")

    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)

