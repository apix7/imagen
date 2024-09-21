import json
import os
from PIL import Image
import io
import base64
import logging

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

HISTORY_FILE = "image_history.json"

def image_to_base64(image):
    if image is None:
        return None
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def base64_to_image(base64_string):
    if base64_string is None:
        return None
    image_data = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(image_data))

def save_history(history):
    serialized_history = []
    for item in history:
        serialized_item = item.copy()
        if 'image' in item and item['image'] is not None:
            serialized_item['image'] = image_to_base64(item['image'])
        else:
            serialized_item['image'] = None
        serialized_history.append(serialized_item)
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(serialized_history, f)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    
    with open(HISTORY_FILE, 'r') as f:
        serialized_history = json.load(f)
    
    history = []
    for item in serialized_history:
        deserialized_item = item.copy()
        if 'image' in item and item['image'] is not None:
            try:
                deserialized_item['image'] = base64_to_image(item['image'])
            except Exception as e:
                logger.error(f"Error deserializing image: {str(e)}")
                deserialized_item['image'] = None
        else:
            logger.warning("Image data missing in history item")
            deserialized_item['image'] = None
        history.append(deserialized_item)
    
    return history

# Add this new function to save all history items
def save_all_history(history):
    serialized_history = []
    for item in history:
        serialized_item = item.copy()
        serialized_item['image'] = image_to_base64(item['image'])
        serialized_history.append(serialized_item)
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(serialized_history, f)