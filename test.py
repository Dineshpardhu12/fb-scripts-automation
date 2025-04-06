import pandas as pd
import requests
import os
import time
import random
from datetime import datetime
import pytz
import re

def post_to_facebook(page_id, access_token, message, image_url=None, link_url=None):
    """
    Post content to a Facebook page using the Graph API.
    Can post text-only, with an image, or with a link preview.

    Args:
        page_id (str): The ID of the Facebook page.
        access_token (str): The Facebook Graph API access token.
        message (str): The message to post.
        image_url (str, optional): URL of an image to include in the post.
        link_url (str, optional): URL to include as a link with preview.

    Returns:
        dict: The response from the Facebook Graph API.
    """
    try:
        if link_url:
            # Post with link (will generate link preview)
            url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
            payload = {
                'message': message,
                'link': link_url,
                'access_token': access_token
            }
            print(f"Posting to Facebook with link URL: {link_url}")
        elif image_url:
            # Post with image
            url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
            payload = {
                'caption': message,
                'url': image_url,
                'access_token': access_token
            }
            print(f"Posting to Facebook with image URL: {image_url}")
        else:
            # Text-only post
            url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
            payload = {
                'message': message,
                'access_token': access_token
            }
            print("Posting text-only message to Facebook")

        response = requests.post(url, data=payload)
        result = response.json()
        print(f"Facebook API response: {result}")
        return result
    except Exception as e:
        print(f"Error posting to Facebook: {e}")
        return {"error": str(e)}

def extract_url_from_text(text):
    """
    Extract the first URL from text content.
    
    Args:
        text (str): Text that may contain URLs.
        
    Returns:
        str: First URL found, or None if no URL is present.
    """
    if not isinstance(text, str):
        return None
    
    # Regular expression pattern to match URLs
    url_pattern = r'https?://[^\s]+'
    match = re.search(url_pattern, text)
    
    if match:
        return match.group(0)
    return None

def get_next_post_content(file_path, index_file='.current_row_index'):
    """
    Read the next row from the Excel file using round-robin rotation.
    
    Args:
        file_path (str): Path to the Excel file.
        index_file (str): File to store the current index position.
        
    Returns:
        tuple: (message, image_url, link_url) or (None, None, None) if not found.
    """
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        if df.empty:
            print("Excel file is empty.")
            return None, None, None
        
        # Get the current index, or start from 0 if file doesn't exist
        current_index = 0
        try:
            if os.path.exists(index_file):
                with open(index_file, 'r') as f:
                    current_index = int(f.read().strip())
        except:
            current_index = 0
        
        # Get the total number of rows
        total_rows = len(df)
        
        # Round-robin: Ensure index is in valid range
        current_index = current_index % total_rows
        
        # Get the content from the current row
        # Assuming: Column A (index 0) = message content, Column B (index 1) = image URL (optional)
        row = df.iloc[current_index]
        
        message = row.iloc[0] if len(row) > 0 else None
        image_url = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else None
        
        # Extract link URL from message if present
        link_url = None
        if isinstance(message, str):
            link_url = extract_url_from_text(message)
        
        # If there's no explicit image URL but we have a link URL in column B,
        # it should be treated as a link URL rather than an image URL
        if image_url and isinstance(image_url, str) and image_url.startswith('http'):
            if not image_url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                if not link_url:  # Only set link_url if we don't already have one from the message
                    link_url = image_url
                    image_url = None
        
        print(f"Selected content from row #{current_index+1} out of {total_rows} rows (Excel row {current_index+2})")
        
        # Update the index for next time (increment and save)
        next_index = (current_index + 1) % total_rows
        with open(index_file, 'w') as f:
            f.write(str(next_index))
        
        # Check if the message is valid
        if isinstance(message, str) and message.strip():
            return message.strip(), image_url, link_url
        else:
            print(f"Invalid or empty message in Excel file at row {current_index+1}.")
            # Try next row if this one is invalid
            with open(index_file, 'w') as f:
                f.write(str(next_index))
            return get_next_post_content(file_path, index_file)  # Recursive call to get next valid content

    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None, None, None

def main():
    print(f"Script started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configuration
    PAGE_ID = '447788546001338'  # Your Facebook Page ID
    ACCESS_TOKEN = 'EAAQjopZAjD24BO0QObyvTXwXQjgvfslINjZBE5DbBcx8tx1bDbWRZA0wmSSNXcOhJP3fWve1lYaaYLW2er1ZBqw1BHlKpZAukMj7FLrLsnsNS9DDaNsEhA9YZBQ1f0EwOlLXdgTZAbCusZBqF0EYiHXhBOf9IZCZAPqyN890YW3NZCftPCYJ18B8SBFS1W84b8U2ZB91'  # Your access token
    EXCEL_FILE_PATH = 'job.xlsx'  # Path to your Excel file
    LOCAL_TIMEZONE = 'Asia/Kolkata'  # Change this to your local timezone
    
    try:
        local_tz = pytz.timezone(LOCAL_TIMEZONE)
    except pytz.exceptions.UnknownTimeZoneError:
        print(f"Unknown timezone: {LOCAL_TIMEZONE}. Falling back to system local time.")
        local_tz = None

    # Check if Excel file exists
    if not os.path.exists(EXCEL_FILE_PATH):
        print(f"Excel file not found at {EXCEL_FILE_PATH}")
        return
    
    # Read the next content from Excel file using round-robin
    message, image_url, link_url = get_next_post_content(EXCEL_FILE_PATH)
    
    if message:
        # Format current time
        if local_tz:
            current_time = datetime.now().astimezone(local_tz).strftime("%Y-%m-%d %H:%M:%S")
            print(f"Using local time ({LOCAL_TIMEZONE}): {current_time}")
        else:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"Using system local time: {current_time}")
        
        # Append timestamp to message if desired (optional)
        # message = f"{message}\n\n📅 Posted at: {current_time}"
        
        print(f"Prepared message to post:\n{message}")
        if link_url:
            print(f"With link preview: {link_url}")
        if image_url:
            print(f"With image: {image_url}")
        
        # Add a small delay before API call
        time.sleep(random.uniform(1, 2))
        
        # Post to Facebook - prioritize link posts over image posts
        if link_url:
            response = post_to_facebook(PAGE_ID, ACCESS_TOKEN, message, link_url=link_url)
        else:
            response = post_to_facebook(PAGE_ID, ACCESS_TOKEN, message, image_url=image_url)
        
        if 'id' in response:
            print(f"Successfully posted to Facebook. Post ID: {response['id']}")
        else:
            print(f"Error posting to Facebook: {response}")
            
            # If posting with link or image failed, try text-only as fallback
            if (link_url or image_url) and 'error' in response:
                print("Link/Image post failed. Trying text-only post as fallback...")
                time.sleep(random.uniform(1, 2))
                response = post_to_facebook(PAGE_ID, ACCESS_TOKEN, message)
                
                if 'id' in response:
                    print(f"Successfully posted text-only message. Post ID: {response['id']}")
                else:
                    print(f"Error posting text-only message: {response}")
    else:
        print("No valid content found in Excel.")
    
    print(f"Script completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()