import pandas as pd
import requests
import os
import time
import json
import random
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import re

def get_product_details(affiliate_link, max_retries=3):
    """
    Extract product details (name, price, image) from the affiliate link using web scraping.
    Enhanced with improved anti-detection measures and better HD image extraction.

    Args:
        affiliate_link (str): The product's affiliate link.
        max_retries (int): Maximum number of retries for extraction.

    Returns:
        tuple: (Product Name, Price, Image URL) or None if extraction fails.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "cross-site",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Add random delay to mimic human behavior
            time.sleep(random.uniform(1.5, 4))
            
            session = requests.Session()
            
            # First get the redirect URL without following
            print(f"Fetching initial URL: {affiliate_link}")
            initial_response = session.get(
                affiliate_link, 
                headers=headers, 
                allow_redirects=False,
                timeout=20
            )
            
            # Handle redirects manually to better track the path
            final_url = affiliate_link
            redirect_count = 0
            max_redirects = 7
            
            while (initial_response.status_code in [301, 302, 303, 307, 308]) and redirect_count < max_redirects:
                redirect_url = initial_response.headers.get('Location')
                if not redirect_url:
                    break
                    
                print(f"Redirect #{redirect_count + 1}: {redirect_url}")
                
                # If it's a relative URL, make it absolute
                if redirect_url.startswith('/'):
                    parsed_url = requests.utils.urlparse(final_url)
                    redirect_url = f"{parsed_url.scheme}://{parsed_url.netloc}{redirect_url}"
                
                final_url = redirect_url
                redirect_count += 1
                
                # Small delay between redirects
                time.sleep(random.uniform(0.8, 2.0))
                
                # Follow the redirect
                try:
                    initial_response = session.get(
                        redirect_url,
                        headers=headers,
                        allow_redirects=False,
                        timeout=20
                    )
                except requests.exceptions.RequestException as e:
                    print(f"Error during redirect {redirect_count}: {e}")
                    break
            
            print(f"Final URL after redirects: {final_url}")
            
            # Now fetch the actual page
            print("Fetching final product page...")
            response = session.get(
                final_url, 
                headers=headers,
                timeout=25
            )
            
            if response.status_code != 200:
                print(f"Failed to fetch product page. Status code: {response.status_code}")
                retry_count += 1
                time.sleep(random.uniform(2, 5))
                continue
                
            # Save HTML for debugging (uncomment if needed)
            # with open(f"amazon_response_{retry_count}.html", "w", encoding="utf-8") as f:
            #     f.write(response.text)
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Debug output to see what we're parsing
            print(f"Page title: {soup.title.text if soup.title else 'No title found'}")
            
            # Extract product name (trying multiple possible selectors)
            product_name = None
            possible_name_selectors = [
                soup.find("span", {"id": "productTitle"}),
                soup.find("h1", {"id": "title"}),
                soup.find("h1", {"class": "a-spacing-none"}),
                soup.select_one("#productTitle"),
                soup.select_one(".product-title-word-break"),
                soup.select_one(".product-title"),
                soup.select_one("h1.a-size-large"),
                soup.select_one("h1")
            ]
            
            for selector in possible_name_selectors:
                if selector:
                    product_name = selector.get_text(strip=True)
                    if product_name:  # Ensure it's not empty
                        break
                    
            # If still no product name, try to find in JSON-LD
            if not product_name or product_name == "Surprice Product with maximum discount":
                json_ld_scripts = soup.find_all("script", {"type": "application/ld+json"})
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and "name" in data:
                            product_name = data["name"]
                            break
                        elif isinstance(data, list) and data and "name" in data[0]:
                            product_name = data[0]["name"]
                            break
                    except:
                        pass
                    
            product_name = product_name if product_name else "Unknown Product"

            # Extract price (trying multiple selectors)
            price = None
            price_selectors = [
                soup.find("span", {"class": "a-price-whole"}),
                soup.find("span", {"id": "priceblock_ourprice"}),
                soup.find("span", {"class": "a-offscreen"}),
                soup.select_one(".a-price .a-offscreen"),
                soup.select_one("#corePriceDisplay_desktop_feature_div .a-price-whole"),
                soup.select_one("#corePrice_feature_div .a-price-whole"),
                soup.select_one(".a-price"),
                soup.select_one("#price"),
                soup.select_one(".price")
            ]
            
            for selector in price_selectors:
                if selector:
                    price_text = selector.get_text(strip=True)
                    if price_text:  # Check that we have text
                        price = price_text
                        break
                        
            # If still no price, try to find in JSON-LD
            if not price or price == "N/A":
                json_ld_scripts = soup.find_all("script", {"type": "application/ld+json"})
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and "offers" in data:
                            if isinstance(data["offers"], dict) and "price" in data["offers"]:
                                price = data["offers"]["price"]
                            elif isinstance(data["offers"], list) and data["offers"] and "price" in data["offers"][0]:
                                price = data["offers"][0]["price"]
                        elif isinstance(data, list) and data and "offers" in data[0]:
                            if isinstance(data[0]["offers"], dict) and "price" in data[0]["offers"]:
                                price = data[0]["offers"]["price"]
                            elif isinstance(data[0]["offers"], list) and data[0]["offers"] and "price" in data[0]["offers"][0]:
                                price = data[0]["offers"][0]["price"]
                    except:
                        pass
                        
            price = price if price else "N/A"

            # IMPROVED HIGH-RESOLUTION IMAGE EXTRACTION
            # We'll prioritize the highest resolution images available
            image_url = None
            hd_image_found = False
            
            # Function to check if an image URL is likely high-resolution
            def is_high_res(url):
                if not url:
                    return False
                # Check for typical high-res indicators in the URL
                high_res_indicators = ['_SL1500_', '_SL1200_', '_SL1000_', '_SX1500_', '_UL1500_', 
                                      'large', 'hiRes', 'hires', 'XXL', 'high', 'original']
                return any(indicator in url for indicator in high_res_indicators)
            
            # Function to clean up Amazon image URLs to get highest resolution
            def optimize_amazon_image_url(url):
                if not url:
                    return None
                    
                # Remove size constraints from URL to get highest resolution
                # Pattern 1: Remove _SX... _SY... parameters
                url = re.sub(r'_(SX|SY|UX|UY|AA|AB|AC|AD)\d+_', '_', url)
                
                # Pattern 2: Replace small/medium size indicators with large
                url = url.replace('_SR75,75_', '_SL1500_')
                url = url.replace('_SR140,140_', '_SL1500_')
                url = url.replace('_SR200,200_', '_SL1500_')
                url = url.replace('_SL160_', '_SL1500_')
                url = url.replace('_SL500_', '_SL1500_')
                
                # Pattern 3: Handle URLs with ?_encoding=... parameters
                if '?' in url:
                    url = url.split('?')[0]
                
                return url
            
            # 1. First try to extract from image detail scripts which often have multiple resolutions
            print("Searching for high-resolution images in scripts...")
            script_tags = soup.find_all("script", {"type": "text/javascript"})
            for script in script_tags:
                script_text = script.string if script.string else ""
                
                # Look for specific image data patterns
                image_patterns = [
                    (r'"hiRes":"(https://[^"]+)"', 'hiRes'),
                    (r'"large":"(https://[^"]+)"', 'large'),
                    (r'"mainImage":"(https://[^"]+)"', 'mainImage')
                ]
                
                for pattern, img_type in image_patterns:
                    matches = re.findall(pattern, script_text)
                    if matches:
                        for match in matches:
                            candidate_url = match.replace('\\', '')
                            if is_high_res(candidate_url):
                                image_url = optimize_amazon_image_url(candidate_url)
                                print(f"Found high-resolution {img_type} image: {image_url}")
                                hd_image_found = True
                                break
                    if hd_image_found:
                        break
                
                # Alternative approach: Look for image JSON data
                if not hd_image_found and "'colorImages'" in script_text:
                    try:
                        start_idx = script_text.find("'colorImages'") + len("'colorImages'") + 1
                        end_idx = script_text.find("'colorToAsin'")
                        if end_idx == -1:
                            end_idx = script_text.find("'heroImage'")
                        if end_idx == -1:
                            end_idx = start_idx + 2000
                        
                        image_data = script_text[start_idx:end_idx].strip()
                        
                        # Search for high-resolution image URLs
                        hiRes_match = re.search(r'"hiRes":"(https://[^"]+)"', image_data)
                        large_match = re.search(r'"large":"(https://[^"]+)"', image_data)
                        
                        if hiRes_match:
                            image_url = optimize_amazon_image_url(hiRes_match.group(1).replace('\\', ''))
                            print(f"Found hiRes image in colorImages: {image_url}")
                            hd_image_found = True
                        elif large_match:
                            image_url = optimize_amazon_image_url(large_match.group(1).replace('\\', ''))
                            print(f"Found large image in colorImages: {image_url}")
                            hd_image_found = True
                    except Exception as e:
                        print(f"Error parsing image data from script: {e}")
            
            # 2. Try to extract from data-zoom-hires attribute which typically has high-res images
            if not hd_image_found:
                print("Searching for data-zoom-hires attributes...")
                zoom_images = soup.select("[data-zoom-hires]")
                for img in zoom_images:
                    zoom_url = img.get('data-zoom-hires')
                    if zoom_url:
                        image_url = optimize_amazon_image_url(zoom_url)
                        print(f"Found high-resolution zoom image: {image_url}")
                        hd_image_found = True
                        break
            
            # 3. Try to extract from data-old-hires attribute
            if not hd_image_found:
                print("Searching for data-old-hires attributes...")
                old_hires_images = soup.select("[data-old-hires]")
                for img in old_hires_images:
                    hires_url = img.get('data-old-hires')
                    if hires_url:
                        image_url = optimize_amazon_image_url(hires_url)
                        print(f"Found high-resolution old-hires image: {image_url}")
                        hd_image_found = True
                        break
            
            # 4. Try to extract from data-a-dynamic-image which contains multiple resolutions
            if not hd_image_found:
                print("Searching for data-a-dynamic-image attributes...")
                dynamic_images = soup.select("[data-a-dynamic-image]")
                for img in dynamic_images:
                    dynamic_attr = img.get('data-a-dynamic-image')
                    if dynamic_attr and dynamic_attr.startswith('{'):
                        try:
                            image_dict = json.loads(dynamic_attr)
                            # Get the URL with the highest resolution by comparing dimensions
                            best_url = None
                            best_size = 0
                            for url, dimensions in image_dict.items():
                                if isinstance(dimensions, list) and len(dimensions) >= 2:
                                    size = dimensions[0] * dimensions[1]  # width * height
                                    if size > best_size:
                                        best_size = size
                                        best_url = url
                            
                            if best_url:
                                image_url = optimize_amazon_image_url(best_url)
                                print(f"Found highest resolution dynamic image: {image_url} ({best_size} pixels)")
                                hd_image_found = True
                        except Exception as e:
                            print(f"Error parsing dynamic image data: {e}")
            
            # 5. Try to find in JSON-LD which sometimes contains high-res images
            if not hd_image_found:
                print("Searching for images in JSON-LD...")
                json_ld_scripts = soup.find_all("script", {"type": "application/ld+json"})
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and "image" in data:
                            img_data = data["image"]
                            if isinstance(img_data, str):
                                image_url = optimize_amazon_image_url(img_data)
                                print(f"Found image in JSON-LD: {image_url}")
                                hd_image_found = True
                            elif isinstance(img_data, list) and img_data:
                                # Find the highest resolution image in the list
                                for img in img_data:
                                    if is_high_res(img):
                                        image_url = optimize_amazon_image_url(img)
                                        print(f"Found high-res image in JSON-LD list: {image_url}")
                                        hd_image_found = True
                                        break
                                # If no high-res, use the first one
                                if not hd_image_found:
                                    image_url = optimize_amazon_image_url(img_data[0])
                                    print(f"Using first image from JSON-LD list: {image_url}")
                                    hd_image_found = True
                            break
                    except Exception as e:
                        print(f"Error parsing JSON-LD: {e}")
            
            # 6. Fallback to standard image selectors if nothing found yet
            if not hd_image_found:
                print("Falling back to standard image selectors...")
                image_selectors = [
                    soup.find("img", {"id": "landingImage"}),
                    soup.find("img", {"id": "imgBlkFront"}),
                    soup.select_one("#main-image-container img"),
                    soup.select_one("#imgTagWrapperId img"),
                    soup.select_one("#imageBlock_feature_div img"),
                    soup.select_one("#imageBlock img"),
                    soup.select_one("#main-image"),
                    soup.select_one(".a-dynamic-image"),
                    soup.select_one("#product-image"),
                    soup.select_one(".product-image img")
                ]
                
                for selector in image_selectors:
                    if selector:
                        for attr in ["src", "data-old-hires", "data-a-dynamic-image"]:
                            if selector.get(attr):
                                img_attr = selector[attr]
                                if attr == "data-a-dynamic-image" and img_attr.startswith('{'):
                                    try:
                                        image_dict = json.loads(img_attr)
                                        first_url = list(image_dict.keys())[0]
                                        image_url = optimize_amazon_image_url(first_url)
                                    except:
                                        pass
                                else:
                                    image_url = optimize_amazon_image_url(img_attr)
                                break
                        if image_url:
                            print(f"Found image using standard selector: {image_url}")
                            break
            
            # Ensure the image URL is absolute
            if image_url and not image_url.startswith('http'):
                image_url = "https:" + image_url if image_url.startswith('//') else f"https://www.amazon.com{image_url}"
                
            # Debug info
            print(f"Found product: {product_name}")
            print(f"Found price: {price}")
            print(f"Found image URL: {image_url if image_url else 'No image found'}")
            if image_url:
                print(f"Image appears to be high-resolution: {is_high_res(image_url)}")

            # If we have a good product name and either price or image, consider it successful
            if product_name != "Unknown Product" and (price != "N/A" or image_url):
                return product_name, price, image_url
            
            print("Missing product details, will retry...")
            retry_count += 1
            time.sleep(random.uniform(3, 7))

        except Exception as e:
            print(f"Error extracting product details (attempt {retry_count+1}): {e}")
            print(f"Exception details: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            retry_count += 1
            time.sleep(random.uniform(3, 7))
    
    # If we've exhausted all retries, return what we have even if incomplete
    return product_name if 'product_name' in locals() else "Unknown Product", \
           price if 'price' in locals() else "N/A", \
           image_url if 'image_url' in locals() and image_url else None

def post_to_facebook(page_id, access_token, message, image_url):
    """
    Post a message with an image to a Facebook page using the Graph API.

    Args:
        page_id (str): The ID of the Facebook page.
        access_token (str): The Facebook Graph API access token.
        message (str): The message to post.
        image_url (str): URL of the product image.

    Returns:
        dict: The response from the Facebook Graph API.
    """
    url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
    
    payload = {
        'caption': message,
        'url': image_url,
        'access_token': access_token
    }
    
    try:
        print(f"Posting to Facebook with image URL: {image_url}")
        response = requests.post(url, data=payload)
        result = response.json()
        print(f"Facebook API response: {result}")
        return result
    except Exception as e:
        print(f"Error posting to Facebook: {e}")
        return {"error": str(e)}

def get_next_affiliate_link(file_path, index_file='.current_link_index'):
    """
    Read the next affiliate link from the Excel file using round-robin rotation.
    
    Args:
        file_path (str): Path to the Excel file.
        index_file (str): File to store the current index position.
        
    Returns:
        str: The affiliate link or None if not found.
    """
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        if df.empty:
            print("Excel file is empty.")
            return None
        
        # Get the current index, or start from 0 if file doesn't exist
        current_index = 0
        try:
            if os.path.exists(index_file):
                with open(index_file, 'r') as f:
                    current_index = int(f.read().strip())
        except:
            current_index = 0
        
        # Get the total number of links
        total_links = len(df)
        
        # Round-robin: Ensure index is in valid range
        current_index = current_index % total_links
        
        # Get the link from the appropriate row
        link = df.iloc[current_index, 0]  # Column A (index 0)
        
        print(f"Selected link #{current_index+1} out of {total_links} links (Excel row A{current_index+1})")
        
        # Update the index for next time (increment and save)
        next_index = (current_index + 1) % total_links
        with open(index_file, 'w') as f:
            f.write(str(next_index))
        
        # Check if the link is valid
        if isinstance(link, str) and link.strip():
            return link.strip()
        else:
            print(f"Invalid or empty link in Excel file at row {current_index+1}.")
            # Try next link if this one is invalid
            with open(index_file, 'w') as f:
                f.write(str(next_index))
            return get_next_affiliate_link(file_path, index_file)  # Recursive call to get next valid link

    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None

def post_text_only_to_facebook(page_id, access_token, message):
    """
    Post a text-only message to a Facebook page if image is unavailable.

    Args:
        page_id (str): The ID of the Facebook page.
        access_token (str): The Facebook Graph API access token.
        message (str): The message to post.

    Returns:
        dict: The response from the Facebook Graph API.
    """
    url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
    
    payload = {
        'message': message,
        'access_token': access_token
    }
    
    try:
        print("Posting text-only message to Facebook as fallback")
        response = requests.post(url, data=payload)
        result = response.json()
        print(f"Facebook API response: {result}")
        return result
    except Exception as e:
        print(f"Error posting text to Facebook: {e}")
        return {"error": str(e)}

def main():
    print(f"Script started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    PAGE_ID = '415136901932889'  # Your Facebook Page ID
    ACCESS_TOKEN = ''  # Your access token
    EXCEL_FILE_PATH = '/app/fb.xlsx'  # Path to your Excel file
    MAX_RETRIES = 3  # Maximum number of retries for product extraction

    # Check if Excel file exists
    if not os.path.exists(EXCEL_FILE_PATH):
        print(f"Excel file not found at {EXCEL_FILE_PATH}")
        return
    
    # Read the next affiliate link using round-robin
    affiliate_link = get_next_affiliate_link(EXCEL_FILE_PATH)
    
    if affiliate_link:
        print(f"Extracting details for: {affiliate_link}")
        
        # Add a small delay to avoid rate limiting
        time.sleep(random.uniform(2, 4))
        
        # Get product details with internal retries
        product_details = get_product_details(affiliate_link, max_retries=MAX_RETRIES)

        if product_details:
            product_name, price, image_url = product_details
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Prepare message for Facebook post
            message = (
                f"🔥 {product_name} 🔥\n"
                f"💰 Price: {price}\n"
                f"🔗 Buy here: {affiliate_link}\n\n"
                f"📅 Posted at: {current_time}"
            )

            print(f"Prepared post message:\n{message}")
            
            # Post to Facebook
            success = False
            
            # Try posting with image first if available
            if image_url:
                time.sleep(random.uniform(1, 2))  # Small delay before API call
                response = post_to_facebook(PAGE_ID, ACCESS_TOKEN, message, image_url)

                if 'id' in response:
                    print(f"Successfully posted with image. Post ID: {response['id']}")
                    success = True
                else:
                    print(f"Error posting with image: {response}")
                    if 'error' in response:
                        print(f"Facebook Error: {response['error'].get('message', 'Unknown error')}")
            else:
                print("No image URL available, will try text-only post")
            
            # If posting with image failed or no image is available, try text-only post
            if not success:
                time.sleep(random.uniform(1, 2))  # Small delay before retry
                response = post_text_only_to_facebook(PAGE_ID, ACCESS_TOKEN, message)
                
                if 'id' in response:
                    print(f"Successfully posted text-only message. Post ID: {response['id']}")
                else:
                    print(f"Error posting text-only message: {response}")
                    if 'error' in response:
                        print(f"Facebook Error: {response['error'].get('message', 'Unknown error')}")
        else:
            print("Failed to extract product details after all attempts.")
    else:
        print("No valid affiliate link found in Excel.")
    
    print(f"Script completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
