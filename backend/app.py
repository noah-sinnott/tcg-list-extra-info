from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import requests
from bs4 import BeautifulSoup
import time
import re
import unicodedata
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from tcgcsv_service import TCGCSVService

app = Flask(__name__)
CORS(app)

# Initialize TCGPlayer CSV service
tcgcsv_service = TCGCSVService()




def get_list_cards_selenium(list_url):
    print(f"Starting to scrape list from: {list_url}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = None
    try:
        print("Initializing Chrome WebDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("Loading webpage...")
        driver.get(list_url)
        
        # Wait for cards to load
        print("Waiting for cards to load...")
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-cardid]")))
        time.sleep(2)
        
        print("Parsing card data...")
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
        
        print(f"Successfully scraped {len(card_elements)} cards from {len(cards_by_set)} sets")
        return cards_by_set
        
    finally:
        if driver:
            driver.quit()
            print("Chrome WebDriver closed")





def normalize_text(text):
    """Normalize text by removing special characters and converting to lowercase"""
    # Convert to lowercase
    normalized = text.lower()
    # Normalize unicode characters (convert accented characters to ASCII equivalents)
    # NFD = Canonical Decomposition (separates base characters from diacritics)
    normalized = unicodedata.normalize('NFD', normalized)
    # Remove diacritical marks (accents)
    normalized = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
    # Remove all non-alphanumeric characters except spaces
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    # Remove extra spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def extract_card_suffixes(text):
    """Extract special card suffixes like ex, vmax, gx, v, vstar"""
    suffixes = []
    text_lower = text.lower()
    
    # Check for these suffixes in order (check longer ones first to avoid conflicts)
    special_suffixes = ['vmax', 'vstar', 'ex', 'gx', 'v']
    
    for suffix in special_suffixes:
        # Check if suffix appears as a separate word at the end or in the text
        if re.search(r'\b' + suffix + r'\b', text_lower):
            suffixes.append(suffix)
    
    return set(suffixes)


def match_card_to_product(card_info, products):
    """Try to match a card by number and name to a product in the list"""
    card_number = card_info["number"]
    card_name = card_info["name"]
    
    # Normalize card number (strip leading zeros)
    normalized_card_number = card_number.lstrip("0") or "0"
    normalized_card_name = normalize_text(card_name)
    card_suffixes = extract_card_suffixes(card_name)
    
    for product in products:
        # Get both cleanName and name for checking
        product_names = []
        if product.get("cleanName"):
            product_names.append(product.get("cleanName"))
        if product.get("name"):
            product_names.append(product.get("name"))
        
        # Check extended data for card number
        extended_data = product.get("extendedData", [])
        for data in extended_data:
            if data.get("name") == "Number":
                product_number = data.get("value", "")
                # Handle numbers like "22/107" - extract first part
                if "/" in product_number:
                    product_number = product_number.split("/")[0]
                # Strip leading zeros for comparison
                product_number = product_number.lstrip("0") or "0"
                
                # Match by number AND name (name can be substring)
                if product_number == normalized_card_number:
                    # Check if card name matches any of the product names
                    for product_name in product_names:
                        normalized_product_name = normalize_text(product_name)
                        product_suffixes = extract_card_suffixes(product_name)
                        
                        # Check if suffixes match
                        if card_suffixes != product_suffixes:
                            continue
                        
                        # Check name similarity
                        if normalized_card_name in normalized_product_name or normalized_product_name in normalized_card_name:
                            return product
                break
    
    return None



def get_card_details_from_tcgplayer(card_info, set_name, all_groups, products_cache):
    """Get card details from TCGPlayer CSV API"""
    try:
        # Special case mappings
        set_name_mappings = {
            "Scarlet & Violet Black Star Promos": "SV: Scarlet & Violet Promo Cards"
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
        
        # Get products for this group (with caching)
        if group_id not in products_cache:
            products_cache[group_id] = tcgcsv_service.get_products(group_id)
        
        products = products_cache[group_id]
        if not products:
            return None
        
        # Try to match card
        product = match_card_to_product(card_info, products)
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
                if related_gid not in products_cache:
                    products_cache[related_gid] = tcgcsv_service.get_products(related_gid)
                
                related_products = products_cache[related_gid]
                if related_products:
                    product = match_card_to_product(card_info, related_products)
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
        
        # Process cards
        results = []
        products_cache = {}
        total_cards = sum(len(cards) for cards in cards_by_set.values())
        
        for set_name, card_infos in cards_by_set.items():
            
            for card_info in card_infos:
   
                card_details = get_card_details_from_tcgplayer(
                    card_info, set_name, all_groups, products_cache
                )
                
                if card_details:
                    results.append(card_details)
        
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

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve React app"""
    if path != "" and os.path.exists(os.path.join('frontend/build', path)):
        return send_from_directory('frontend/build', path)
    else:
        return send_from_directory('frontend/build', 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
