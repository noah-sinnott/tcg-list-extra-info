from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tcgcsv_service import TCGCSVService
from webdriver_pool_service import get_pool



app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
tcgcsv_service = TCGCSVService()

# Initialize WebDriver pool at startup
driver_pool = get_pool(pool_size=1)

# In-memory cache for indexed products (for faster lookups)
products_index_cache = {}

# Thread lock for products cache to prevent duplicate fetches
products_cache_lock = Lock()



def get_list_cards_selenium(list_url):
    """Scrape cards from list URL using a pooled WebDriver"""
    driver = None
    try:
        # Get driver from pool
        driver = driver_pool.get_driver(timeout=30)
        if not driver:
            raise Exception("Could not get WebDriver from pool")
        
        driver.get(list_url)
        wait = WebDriverWait(driver, 7)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-cardid]")))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards_by_set = {}
        card_elements = soup.select("div[data-cardid]")
        for card_elem in card_elements:
            card_name = card_elem.get("data-name", "")
            card_number = card_elem.get("data-number", "")

            if not card_name or not card_number:
                continue
            
            # Extract set name from the gray text paragraph
            set_name_elem = card_elem.select_one("div.flex.justify-between.mb-4 p.text-gray-500")
            set_name = set_name_elem.get_text(strip=True) if set_name_elem else "Unknown"
            
            # Extract card URL
            card_link = card_elem.select_one("a[href^='/card/']")
            card_url = card_link.get("href", "") if card_link else ""
            
            if set_name not in cards_by_set:
                cards_by_set[set_name] = []
            cards_by_set[set_name].append({
                "name": card_name,
                "number": card_number,
                "url": card_url
            })
        
        return cards_by_set
        
    finally:
        if driver:
            # Return driver to pool (it will be closed and replaced)
            driver_pool.return_driver(driver)




def normalize_text(text):
    normalized = text.lower()
    normalized = unicodedata.normalize('NFD', normalized)
    normalized = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def extract_card_suffixes(text):
    suffixes = []
    text_lower = text.lower()
    special_suffixes = ['vmax', 'vstar', 'ex', 'gx', 'v']
    for suffix in special_suffixes:
        if re.search(r'\b' + suffix + r'\b', text_lower):
            suffixes.append(suffix)
    return set(suffixes)


def build_products_index(products):
    """Build an index of products by card number for fast lookup"""
    index = {}
    for product in products:
        extended_data = product.get("extendedData", [])
        for data in extended_data:
            if data.get("name") == "Number":
                product_number = data.get("value", "")
                if "/" in product_number:
                    product_number = product_number.split("/")[0]
                # Normalize number (remove leading zeros)
                normalized_number = product_number.lstrip("0") or "0"
                if normalized_number not in index:
                    index[normalized_number] = []
                index[normalized_number].append(product)
                break
    return index


def match_card_to_product(card_info, products_index):
    """Match a card to a product using indexed lookup"""
    card_number = card_info["number"]
    card_name = card_info["name"]
    normalized_card_number = card_number.lstrip("0") or "0"
    normalized_card_name = normalize_text(card_name)
    card_suffixes = extract_card_suffixes(card_name)
    
    # Use indexed lookup - only check products with matching card number
    matching_products = products_index.get(normalized_card_number, [])
    
    for product in matching_products:
        product_names = []
        if product.get("cleanName"):
            product_names.append(product.get("cleanName"))
        if product.get("name"):
            product_names.append(product.get("name"))
        
        for product_name in product_names:
            normalized_product_name = normalize_text(product_name)
            product_suffixes = extract_card_suffixes(product_name)
            if card_suffixes != product_suffixes:
                continue
            if normalized_card_name in normalized_product_name or normalized_product_name in normalized_card_name:
                return product
    
    return None



def get_card_details_from_tcgplayer(card_info, set_name, all_groups, products_cache):
    """Get card details from TCGPlayer CSV API"""
    try:
        # Special case mappings
        set_name_mappings = {
            "Scarlet & Violet Black Star Promos": "SV: Scarlet & Violet Promo Cards",
            "SWSH Black Star Promos": "SWSH: Sword & Shield Promo Cards"
        }
        
        # Check if this is a special case
        if set_name in set_name_mappings:
            mapped_name = set_name_mappings[set_name]
            group_id = all_groups.get(mapped_name)
            if not group_id:
                # Try fuzzy matching with mapped name
                for group_name, gid in all_groups.items():
                    if mapped_name.lower() in group_name.lower() or group_name.lower() in mapped_name.lower():
                        group_id = gid
                        break
        else:
            group_id = None
        
        # Find matching group (if not already found via special mapping)
        if not group_id:
            group_id = all_groups.get(set_name)
        if not group_id:
            # Try fuzzy matching
            for group_name, gid in all_groups.items():
                if set_name.lower() in group_name.lower() or group_name.lower() in set_name.lower():
                    group_id = gid
                    break
        
        # If still not found and set name contains "&", try without it
        if not group_id and "&" in set_name:
            modified_set_name = set_name.replace("& ", "").replace("&", "")
            group_id = all_groups.get(modified_set_name)
            if not group_id:
                # Try fuzzy matching with modified name
                for group_name, gid in all_groups.items():
                    if modified_set_name.lower() in group_name.lower() or group_name.lower() in modified_set_name.lower():
                        group_id = gid
                        break
        
        # If still not found, try replacing "&" with "and"
        if not group_id and "&" in set_name:
            modified_set_name = set_name.replace("&", "and")
            group_id = all_groups.get(modified_set_name)
            if not group_id:
                # Try fuzzy matching with "and" version
                for group_name, gid in all_groups.items():
                    if modified_set_name.lower() in group_name.lower() or group_name.lower() in modified_set_name.lower():
                        group_id = gid
                        break
        
        # If still not found, try abbreviation (e.g., "Sun & Moon" -> "SM")
        if not group_id and "&" in set_name:
            words = set_name.replace("&", "").split()
            abbreviation = "".join(word[0].upper() for word in words if word)
            group_id = all_groups.get(abbreviation)
            if not group_id:
                # Try fuzzy matching with abbreviation
                for group_name, gid in all_groups.items():
                    if abbreviation.lower() in group_name.lower() or group_name.lower().startswith(abbreviation.lower()):
                        group_id = gid
                        break
        
        if not group_id:
            print(f"  No group found for set: {set_name}")
            return None
        
        # Get products for this group (with caching and thread safety)
        with products_cache_lock:
            if group_id not in products_cache:
                products_cache[group_id] = tcgcsv_service.get_products(group_id)
        
        products = products_cache[group_id]
        if not products:
            return None
        
        # Build index for this group if not already done (fast, happens in memory)
        if group_id not in products_index_cache:
            products_index_cache[group_id] = build_products_index(products)
        
        products_index = products_index_cache[group_id]
        
        # Try to match card using indexed lookup
        product = match_card_to_product(card_info, products_index)
        matched_group_name = None
        
        # Store the group name if we found a match
        if product:
            # Find the group name for this group_id
            for group_name, gid in all_groups.items():
                if gid == group_id:
                    matched_group_name = group_name
                    break
        
        # If no match found, check related groups (subsets)
        if not product:
            related_groups = []
            
            # Generate variant set names to search with
            search_variants = [set_name.lower()]
            
            # Add variant without "&"
            if "&" in set_name:
                search_variants.append(set_name.replace("& ", "").replace("&", "").lower())
                # Add variant with "and" instead of "&"
                search_variants.append(set_name.replace("&", "and").lower())
                # Add abbreviation variant (e.g., "Sun & Moon" -> "sm")
                words = set_name.replace("&", "").split()
                abbreviation = "".join(word[0].lower() for word in words if word)
                if abbreviation:
                    search_variants.append(abbreviation)
            
            # Find groups that contain any of the variant names as a substring
            for group_name, gid in all_groups.items():
                if gid != group_id:
                    group_name_lower = group_name.lower()
                    for variant in search_variants:
                        if variant in group_name_lower:
                            related_groups.append((group_name, gid))
                            break  # Don't add the same group multiple times
            
            # Try to find the card in related groups
            for related_name, related_gid in related_groups:
                with products_cache_lock:
                    if related_gid not in products_cache:
                        products_cache[related_gid] = tcgcsv_service.get_products(related_gid)
                
                related_products = products_cache[related_gid]
                if related_products:
                    # Build index for related group if needed
                    if related_gid not in products_index_cache:
                        products_index_cache[related_gid] = build_products_index(related_products)
                    
                    related_products_index = products_index_cache[related_gid]
                    product = match_card_to_product(card_info, related_products_index)
                    if product:
                        matched_group_name = related_name
                        break
        
        if not product:
            print(f"  No product match for {card_info['name']} #{card_info['number']} in {set_name}")
            return None
        
        # Extract relevant data
        extended_data_dict = {}
        for data in product.get("extendedData", []):
            extended_data_dict[data.get("name")] = data.get("value")
        
        return {
            "name": product.get("name", ""),
            "image_url": product.get("imageUrl", ""),
            "rarity": extended_data_dict.get("Rarity", ""),
            "group_name": matched_group_name or set_name,
            "set_name": set_name,
            "card_url": f"https://mytcgcollection.com{card_info.get('url', '')}" if card_info.get('url') else "",
        }
    except Exception as e:
        print(f"  Error processing: {e}")
        return None


@app.route('/api/scrape', methods=['POST'])
def scrape_list():
    """API endpoint to scrape TCG list"""
    try:
        data = request.get_json()
        list_url = data.get('url')
        
        if not list_url:
            return jsonify({"error": "URL is required"}), 400
        
        if not list_url.startswith("https://mytcgcollection.com/"):
            return jsonify({"error": "Invalid URL. Must be a mytcgcollection.com list URL"}), 400
        
        # Get cards grouped by set
        cards_by_set = get_list_cards_selenium(list_url)
        if not cards_by_set:
            return jsonify({"error": "No cards found on the list"}), 404
        
        # Fetch all TCGPlayer groups once (with caching)
        print("Fetching TCGPlayer groups...")
        all_groups = tcgcsv_service.get_groups()
        
        if not all_groups:
            return jsonify({"error": "Failed to fetch TCGPlayer groups"}), 500
        
        # Process cards in parallel
        results = []
        products_cache = {}
        total_cards = sum(len(cards) for cards in cards_by_set.values())
        
        # Flatten cards with their set names for parallel processing
        card_tasks = []
        for set_name, card_infos in cards_by_set.items():
            for card_info in card_infos:
                card_tasks.append((card_info, set_name))
        
        print(f"Processing {total_cards} cards in parallel...")
        
        # Process cards in parallel with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            future_to_card = {
                executor.submit(
                    get_card_details_from_tcgplayer,
                    card_info,
                    set_name,
                    all_groups,
                    products_cache
                ): (card_info, set_name)
                for card_info, set_name in card_tasks
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_card):
                completed += 1
                if completed % 10 == 0 or completed == total_cards:
                    print(f"Progress: {completed}/{total_cards} cards processed")
                
                try:
                    card_details = future.result()
                    if card_details:
                        results.append(card_details)
                except Exception as e:
                    card_info, set_name = future_to_card[future]
                    print(f"Error processing {card_info['name']}: {e}")
        
        print(f"\nCompleted: {len(results)}/{total_cards} cards matched")
        
        return jsonify({
            "success": True,
            "cards": results,
            "total": total_cards,
            "matched": len(results)
        })
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

