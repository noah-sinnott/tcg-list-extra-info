"""
Card Matcher Service
Text normalisation, product indexing and TCGPlayer card-to-product matching.
"""
import re
import unicodedata
from threading import Lock

# In-memory caches (populated per-request lifetime or across requests)
products_index_cache = {}
products_cache_lock = Lock()


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def normalize_text(text):
    """Lower-case, strip accents and non-alphanumeric characters."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_card_suffixes(text):
    """Return the set of special Pokemon card suffixes found in *text*."""
    text_lower = text.lower()
    return {
        suffix
        for suffix in ("vmax", "vstar", "ex", "gx", "v")
        if re.search(r"\b" + suffix + r"\b", text_lower)
    }


# ---------------------------------------------------------------------------
# Product index
# ---------------------------------------------------------------------------

def build_products_index(products):
    """Build a dict mapping normalised card numbers to product lists."""
    index = {}
    for product in products:
        for data in product.get("extendedData", []):
            if data.get("name") == "Number":
                num = data.get("value", "")
                if "/" in num:
                    num = num.split("/")[0]
                num = num.lstrip("0") or "0"
                index.setdefault(num, []).append(product)
                break
    return index


def _match_card_to_product(card_info, products_index):
    """Return the first matching product for *card_info* using *products_index*."""
    norm_num = card_info["number"].lstrip("0") or "0"
    norm_name = normalize_text(card_info["name"])
    card_sfx = extract_card_suffixes(card_info["name"])

    for product in products_index.get(norm_num, []):
        names = filter(None, [product.get("cleanName"), product.get("name")])
        for pname in names:
            if extract_card_suffixes(pname) != card_sfx:
                continue
            pnorm = normalize_text(pname)
            if norm_name in pnorm or pnorm in norm_name:
                return product
    return None


def _extract_result(product, group_name, set_name, card_info):
    """Build the result dict from a matched product."""
    ext = {d.get("name"): d.get("value") for d in product.get("extendedData", [])}
    return {
        "name": product.get("name", ""),
        "image_url": product.get("imageUrl", ""),
        "rarity": ext.get("Rarity", ""),
        "group_name": group_name,
        "set_name": set_name,
        "card_url": (
            f"https://mytcgcollection.com{card_info.get('url', '')}"
            if card_info.get("url") else ""
        ),
    }


# ---------------------------------------------------------------------------
# Group resolution helpers
# ---------------------------------------------------------------------------

def _fix_set_name(set_name):
    """Apply common typo corrections."""
    if "Accended" in set_name:
        set_name = set_name.replace("Accended", "Ascended")
    return set_name


def _find_group_id(set_name, all_groups):
    """Try exact match, fuzzy match, and ampersand variants to find a group id."""
    gid = all_groups.get(set_name)
    if gid:
        return gid

    # Fuzzy substring match
    lower = set_name.lower()
    for name, gid in all_groups.items():
        if lower in name.lower() or name.lower() in lower:
            return gid

    if "&" not in set_name:
        return None

    # Variants: remove &, replace with "and", abbreviate
    variants = [
        set_name.replace("& ", "").replace("&", ""),
        set_name.replace("&", "and"),
    ]
    words = set_name.replace("&", "").split()
    if words:
        variants.append("".join(w[0].upper() for w in words if w))

    for variant in variants:
        gid = all_groups.get(variant)
        if gid:
            return gid
        vlow = variant.lower()
        for name, gid in all_groups.items():
            nl = name.lower()
            if vlow in nl or nl in vlow or nl.startswith(vlow):
                return gid
    return None


def _ensure_products(group_id, products_cache, tcgcsv_service):
    """Thread-safe fetch-and-cache of products + index for *group_id*."""
    with products_cache_lock:
        if group_id not in products_cache:
            products_cache[group_id] = tcgcsv_service.get_products(group_id)
    products = products_cache[group_id]
    if products and group_id not in products_index_cache:
        products_index_cache[group_id] = build_products_index(products)
    return products


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_card_details(card_info, set_name, all_groups, products_cache, tcgcsv_service):
    """Look up a single card against the TCGPlayer CSV data.

    Returns a result dict on match, or ``None``.
    """
    try:
        set_name = _fix_set_name(set_name)
        group_id = _find_group_id(set_name, all_groups)

        # Special promo search – try all promo groups
        if not group_id and "promo" in set_name.lower():
            promo_groups = [
                (n, gid) for n, gid in all_groups.items()
                if "promo" in n.lower()
            ]
            for pname, pgid in promo_groups:
                _ensure_products(pgid, products_cache, tcgcsv_service)
                idx = products_index_cache.get(pgid, {})
                product = _match_card_to_product(card_info, idx)
                if product:
                    return _extract_result(product, pname, set_name, card_info)

        if not group_id:
            print(f"  No group found for set: {set_name}")
            return None

        _ensure_products(group_id, products_cache, tcgcsv_service)
        idx = products_index_cache.get(group_id, {})
        product = _match_card_to_product(card_info, idx)
        matched_name = None

        if product:
            matched_name = next(
                (n for n, gid in all_groups.items() if gid == group_id), None
            )

        # Fallback: related / subset groups
        if not product:
            variants = [set_name.lower()]
            if "&" in set_name:
                variants.append(set_name.replace("& ", "").replace("&", "").lower())
                variants.append(set_name.replace("&", "and").lower())
                words = set_name.replace("&", "").split()
                abbr = "".join(w[0].lower() for w in words if w)
                if abbr:
                    variants.append(abbr)

            for gname, gid in all_groups.items():
                if gid == group_id:
                    continue
                gl = gname.lower()
                if any(v in gl for v in variants):
                    _ensure_products(gid, products_cache, tcgcsv_service)
                    ridx = products_index_cache.get(gid, {})
                    product = _match_card_to_product(card_info, ridx)
                    if product:
                        matched_name = gname
                        break

        if not product:
            print(f"  No product match for {card_info['name']} #{card_info['number']} in {set_name}")
            return None

        return _extract_result(product, matched_name or set_name, set_name, card_info)
    except Exception as exc:
        print(f"  Error processing: {exc}")
        return None
