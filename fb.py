import pandas as pd
import requests
import os
import time
import json
import random
from datetime import datetime, timezone
from bs4 import BeautifulSoup

def get_product_details(affiliate_link):
    """
    Extract product details (name, price, image) from the affiliate link using web scraping.
    Enhanced with improved anti-detection measures.

    Args:
        affiliate_link (str): The product's affiliate link.

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
    
    try:
        # Add random delay to mimic human behavior
        time.sleep(random.uniform(1, 3))
        
        session = requests.Session()
        
        # First get the redirect URL without following
        print(f"Fetching initial URL: {affiliate_link}")
        initial_response = session.get(
            affiliate_link, 
            headers=headers, 
            allow_redirects=False,
            timeout=15
        )
        
        # Handle redirects manually to better track the path
        final_url = affiliate_link
        redirect_count = 0
        max_redirects = 5
        
        while 'Location' in initial_response.headers and redirect_count < max_redirects:
            redirect_url = initial_response.headers['Location']
            print(f"Redirect #{redirect_count + 1}: {redirect_url}")
            
            # If it's a relative URL, make it absolute
            if redirect_url.startswith('/'):
                parsed_url = requests.utils.urlparse(final_url)
                redirect_url = f"{parsed_url.scheme}://{parsed_url.netloc}{redirect_url}"
            
            final_url = redirect_url
            redirect_count += 1
            
            # Small delay between redirects
            time.sleep(random.uniform(0.5, 1.5))
            
            # Follow the redirect
            initial_response = session.get(
                redirect_url,
                headers=headers,
                allow_redirects=False,
                timeout=15
            )
        
        print(f"Final URL after redirects: {final_url}")
        
        # Now fetch the actual page
        print("Fetching final product page...")
        response = session.get(
            final_url, 
            headers=headers,
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"Failed to fetch product page. Status code: {response.status_code}")
            return None
            
        # Save HTML for debugging (uncomment if needed)
        # with open("amazon_response.html", "w", encoding="utf-8") as f:
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
            soup.select_one(".product-title")
        ]
        
        for selector in possible_name_selectors:
            if selector:
                product_name = selector.get_text(strip=True)
                break
                
        product_name = product_name if product_name else "Unknown Product"

        # Extract price (trying multiple selectors)
        price = None
        price_selectors = [
            soup.find("span", {"class": "a-price-whole"}),
            soup.find("span", {"id": "priceblock_ourprice"}),
            soup.find("span", {"class": "a-offscreen"}),
            soup.select_one(".a-price .a-offscreen"),
            soup.select_one("#corePriceDisplay_desktop_feature_div .a-price-whole"),
            soup.select_one("#corePrice_feature_div .a-price-whole")
        ]
        
        for selector in price_selectors:
            if selector:
                price = selector.get_text(strip=True)
                break
                
        price = price if price else "N/A"

        # Try multiple strategies for image URL
        image_url = None
        
        # Try to find in script tags first (more reliable)
        script_tags = soup.find_all("script", {"type": "text/javascript"})
        for script in script_tags:
            if script.string and "ImageBlockATF" in script.string:
                try:
                    script_text = script.string
                    # Find the data block with images
                    if "'colorImages'" in script_text:
                        start_idx = script_text.find("'colorImages'") + len("'colorImages'") + 1
                        end_idx = script_text.find("'colorToAsin'")
                        if end_idx == -1:  # If not found, look for another boundary
                            end_idx = script_text.find("'heroImage'")
                        if end_idx == -1:  # If still not found, use a reasonable portion
                            end_idx = start_idx + 1000
                        
                        image_data = script_text[start_idx:end_idx].strip()
                        if image_data.startswith('{') and ':' in image_data:
                            # Extract the first image URL using a simple regex approach
                            import re
                            hiRes_match = re.search(r'"hiRes":"(https://[^"]+)"', image_data)
                            large_match = re.search(r'"large":"(https://[^"]+)"', image_data)
                            if hiRes_match:
                                image_url = hiRes_match.group(1)
                            elif large_match:
                                image_url = large_match.group(1)
                except Exception as img_err:
                    print(f"Error extracting image from script: {img_err}")
                
                if image_url:
                    break
        
        # If script extraction failed, try direct image extraction
        if not image_url:
            image_selectors = [
                soup.find("img", {"id": "landingImage"}),
                soup.find("img", {"id": "imgBlkFront"}),
                soup.select_one("#main-image-container img"),
                soup.select_one("#imgTagWrapperId img"),
                soup.select_one("#imageBlock_feature_div img"),
                soup.select_one("#imageBlock img"),
                soup.select_one("#main-image")
            ]
            
            for selector in image_selectors:
                if selector:
                    for attr in ["src", "data-old-hires", "data-a-dynamic-image"]:
                        if selector.get(attr):
                            img_attr = selector[attr]
                            # If it's a JSON string of multiple images, extract the first one
                            if attr == "data-a-dynamic-image" and img_attr.startswith('{'):
                                try:
                                    image_dict = json.loads(img_attr)
                                    image_url = list(image_dict.keys())[0]  # Get first image URL
                                except:
                                    pass
                            else:
                                image_url = img_attr
                            break
                    if image_url:
                        break
        
        # Ensure the image URL is absolute
        if image_url and not image_url.startswith('http'):
            image_url = "https:" + image_url if image_url.startswith('//') else f"https://www.amazon.com{image_url}"
            
        # Debug info
        print(f"Found product: {product_name}")
        print(f"Found price: {price}")
        print(f"Found image URL: {image_url}")

        return product_name, price, image_url

    except Exception as e:
        print(f"Error extracting product details: {e}")
        print(f"Exception details: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None

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

def read_excel_affiliate_link_by_hour(file_path):
    """
    Read the affiliate link from the Excel file based on the current UTC hour.
    
    Args:
        file_path (str): Path to the Excel file.
        
    Returns:
        str: The affiliate link or None if not found.
    """
    try:
        # Get current UTC hour (0-23)
        current_utc_hour = datetime.now(timezone.utc).hour
        
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        if df.empty:
            print("Excel file is empty.")
            return None
        
        # Make sure we have a row for the current hour
        if current_utc_hour >= len(df):
            print(f"Warning: Current hour ({current_utc_hour}) exceeds available rows in Excel.")
            # Use modulo to cycle through available rows
            row_index = current_utc_hour % len(df)
            print(f"Using row {row_index+1} instead (Excel row A{row_index+1})")
        else:
            # Row index is the current hour (e.g., 3 PM UTC would be row index 3)
            row_index = current_utc_hour
            
        # Get the link from the appropriate row
        link = df.iloc[row_index, 0]  # Column A (index 0) in the specified row
        
        print(f"Current UTC hour: {current_utc_hour}, selecting row {row_index+1} (Excel row A{row_index+1})")
        
        # Check if the link is valid
        if isinstance(link, str) and link.strip():
            return link.strip()
        else:
            print(f"Invalid or empty link in Excel file at row {row_index+1}.")
            return None

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
    
    PAGE_ID = ''  # Your Facebook Page ID
    ACCESS_TOKEN = ''  # Your access token
    EXCEL_FILE_PATH = '/app/fb.xlsx'  # Path to your Excel file

    # Check if Excel file exists
    if not os.path.exists(EXCEL_FILE_PATH):
        print(f"Excel file not found at {EXCEL_FILE_PATH}")
        return
    
    # Read the affiliate link from Excel based on current UTC hour
    affiliate_link = read_excel_affiliate_link_by_hour(EXCEL_FILE_PATH)
    
    if affiliate_link:
        print(f"Extracting details for: {affiliate_link}")
        
        # Add a small delay to avoid rate limiting
        time.sleep(2)
        
        # Try up to 3 times to get product details
        max_attempts = 3
        product_details = None
        
        for attempt in range(1, max_attempts + 1):
            print(f"Attempt {attempt} of {max_attempts} to extract product details")
            product_details = get_product_details(affiliate_link)
            if product_details and product_details[0] != "Unknown Product":
                break
            elif attempt < max_attempts:
                print(f"Retrying in 5 seconds...")
                time.sleep(5)  # Wait before retrying

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
            
            # Try posting with image first
            if image_url:
                time.sleep(1)  # Small delay before API call
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
                time.sleep(1)  # Small delay before retry
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
        print("No affiliate link found in Excel.")
    
    print(f"Script completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()