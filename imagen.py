import streamlit as st
import requests
import time
from PIL import Image
from io import BytesIO
import logging
import os
import random
from storage import save_history, load_history
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://api.aimlapi.com"
IMAGE_GEN_URL = f"{BASE_URL}/images/generations"
CHAT_URL = f"{BASE_URL}/chat/completions"
IMAGE_MODEL = "flux-pro"
CHAT_MODEL = "gpt-4o-2024-08-06"

# API key
API_KEY = os.getenv("API_KEY")

IMAGE_SIZES = {
    "square_hd": "Square HD",
    "square": "Square",
    "portrait_4_3": "Portrait 4:3",
    "portrait_16_9": "Portrait 16:9",
    "landscape_4_3": "Landscape 4:3",
    "landscape_16_9": "Landscape 16:9"
}

def generate_prompt(user_input):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    system_prompt = """Objective:
This system will generate creative and detailed AI image prompts based on a user's description, emulating the distinctive style and structure observed in a comprehensive set of user-provided example prompts. The system will aim for accuracy, detail, and flexibility, ensuring the generated prompts are suitable for use with AI image generators like Midjourney, Stable Diffusion, and DALL-E.

Core Principles:

    Faithful Style Replication: The system will prioritize mirroring the nuanced style of the user's examples. This includes:

        Concise Subject Introduction: Starting with a clear and brief subject or scene description.

        Varied Style Keywords: Incorporating a diverse range of keywords related to art style, photography techniques, and desired aesthetics (e.g., "cinematic," "Pixar-style," "photorealistic," "minimalist," "surrealism").

        Artistic References: Integrating specific artists, art movements, or pop culture references to guide the AI's stylistic interpretation.

        Optional Technical Details: Including optional yet specific details about:

            Camera and Lens: "Canon EOS R5," "Nikon D850 with a macro lens," "35mm lens at f/8."

            Film Stock: "Kodak film," "Fujifilm Provia."

            Post-Processing: "Film grain," "lens aberration," "color negative," "bokeh."

        AI Model Parameters: Adding relevant parameters like aspect ratio ("--ar 16:9"), stylization ("--stylize 750"), chaos ("--s 750"), or version ("--v 6.0").

        Negative Prompts: Employing negative prompts to exclude undesired elements.

        Emphasis Techniques: Utilizing parentheses, brackets, or capitalization to highlight key elements within the prompt.

    User-Centric Design:

        Clarity and Specificity: The generated prompts should be clear, specific, and easily understood by the AI.

        Open-Ended Options: Allow for open-ended descriptions when users seek more creative freedom.

        Iterative Refinement: Support modifications and adjustments based on user feedback to facilitate an iterative creation process.

    Comprehensive Prompt Structure:

        Subject: Clearly define the primary subject(s) of the image.

        Action/Pose: Describe actions or poses the subject(s) might be performing.

        Environment/Background: Establish the scene's setting, including background elements.

        Style/Art Medium: Specify the desired artistic style or medium (photography, illustration, painting, pixel art, etc.).

        Lighting: Detail the lighting conditions (soft light, dramatic light, natural light, studio lighting, etc.).

        Color Palette: Suggest a specific color palette or individual colors.

        Composition: Indicate the preferred composition (close-up, wide-angle, symmetrical, minimalist, etc.).

        Details/Texture: Include descriptions of textures, patterns, and specific features.

        Mood/Atmosphere: Optionally evoke a mood or atmosphere to guide the AI's interpretation (melancholic, mysterious, serene, etc.).

Example Interaction:

User Input: "A portrait of a futuristic robot, with neon lights reflecting on its metallic surface, in a cyberpunk city."

System Output:
"Portrait of a futuristic robot, neon lights reflecting on its metallic surface, standing in a cyberpunk city, detailed circuitry, glowing eyes, (gritty), (cyberpunk aesthetic), in the style of Syd Mead, cinematic lighting, 85mm lens, film grain, --ar 3:2 --v 6.0 --style raw"

Generate a prompt based on the user's input."""

    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        "max_tokens": 150,
        "temperature": 1
    }
    
    try:
        response = requests.post(CHAT_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        error_message = f"Error generating prompt: {str(e)}"
        if hasattr(e.response, 'text'):
            error_message += f"\nResponse content: {e.response.text}"
        logger.error(error_message)
        print(error_message)  # Print detailed error to terminal
        return "Failed to generate prompt. Please try again later."

def upscale_image(image, version="v1.4", scale_factor=2):
    API_URLS = [
        "https://algoworks-image-face-upscale-restoration-gfpgan-pub.hf.space/api/predict",
        "https://nightfury-image-face-upscale-restoration-gfpgan.hf.space/api/predict"
    ]
    
    # Convert PIL Image to base64
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Prepare the payload
    payload = {
        "data": [
            f"data:image/png;base64,{img_str}",
            version,
            scale_factor
        ]
    }
    
    for API_URL in API_URLS:
        try:
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # The API returns a list of results, we're interested in the first item
            upscaled_image_data = result['data'][0].split(',')[1]
            upscaled_image = Image.open(BytesIO(base64.b64decode(upscaled_image_data)))
            return upscaled_image
        except requests.exceptions.RequestException as e:
            logger.error(f"Error upscaling image with {API_URL}: {str(e)}")
            if API_URL == API_URLS[-1]:
                return None  # If this is the last API, return None
            # If it's not the last API, continue to the next one
    
    return None  # This line should never be reached, but it's here for completeness

def generate_image(prompt, size, steps, guidance, num_images, seed, safety_tolerance, sync_mode, upscale=False):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "image_size": size,
        "num_inference_steps": steps,
        "guidance_scale": guidance,
        "num_images": num_images,
        "safety_tolerance": safety_tolerance,
        "sync_mode": sync_mode
    }
    if seed is not None:
        payload["seed"] = seed

    try:
        response = requests.post(IMAGE_GEN_URL, json=payload, headers=headers)
        response.raise_for_status()
        images = []
        image_urls = []
        for image_data in response.json()['images']:
            image_url = image_data['url']
            image_urls.append(image_url)
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            image = Image.open(BytesIO(image_response.content))
                
            if upscale:
                upscaled_image = upscale_image(image)
                if upscaled_image:
                    images.append(upscaled_image)
                else:
                    images.append(image)  # Fallback to original if upscaling fails
            else:
                images.append(image)
        
        return images, image_urls, None
    except requests.exceptions.RequestException as e:
        error_message = f"Error generating image: {str(e)}"
        if hasattr(e.response, 'text'):
            error_message += f"\nResponse content: {e.response.text}"
        logger.error(error_message)
        print(error_message)  # Print detailed error to terminal
        return None, None, "Failed to generate image. Please check the terminal for detailed error messages."

def log_generated_image(image_path, prompt):
    logger.info(f"Generated Image: {image_path}")
    logger.info(f"Prompt: {prompt}")

def save_images(images, prompt):
    output_folder = "generated_images"
    os.makedirs(output_folder, exist_ok=True)
    saved_paths = []
    for i, image in enumerate(images):
        timestamp = int(time.time())
        filename = f"generated_image_{timestamp}_{i+1}.png"
        filepath = os.path.join(output_folder, filename)
        image.save(filepath)
        saved_paths.append(filepath)
        log_generated_image(filepath, prompt)
    return saved_paths

st.set_page_config(page_title="AI Image Alchemist", layout="centered", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp {
        font-family: 'Poppins', sans-serif;
    }
    .main-title {
        font-size: 3rem;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .section-title {
        font-size: 2rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background-color: #3498db;
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        font-weight: bold;
        border-radius: 30px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(50,50,93,.11), 0 1px 3px rgba(0,0,0,.08);
    }
    .stButton>button:hover {
        background-color: #2980b9;
        transform: translateY(-2px);
        box-shadow: 0 7px 14px rgba(50,50,93,.1), 0 3px 6px rgba(0,0,0,.08);
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        padding: 0.5rem;
        font-size: 1rem;
        color: inherit;
    }
    .stSelectbox>div>div>div {
        background-color: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        color: inherit;
    }
    .generated-image {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stSlider>div>div>div>div {
        color: inherit;
    }
    .modal {
        display: none;
        position: fixed;
        z-index: 1000;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        overflow: auto;
        background-color: rgba(0,0,0,0.9);
    }
    .modal-content {
        margin: auto;
        display: block;
        width: 80%;
        max-width: 900px;
    }
    .close {
        position: absolute;
        top: 15px;
        right: 35px;
        color: #f1f1f1;
        font-size: 40px;
        font-weight: bold;
        transition: 0.3s;
    }
    .close:hover,
    .close:focus {
        color: #bbb;
        text-decoration: none;
        cursor: pointer;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎨 AI Image Alchemist")

st.header("📝 Generate Prompt")
user_input = st.text_area("Enter your idea for an image:", key="user_input")
if st.button("Generate Prompt", key="generate_prompt_button") or (user_input and user_input.endswith('\n')):
    with st.spinner("Generating prompt..."):
        generated_prompt = generate_prompt(user_input)
        if "Failed to generate prompt" in generated_prompt:
            st.error(generated_prompt)
        else:
            st.session_state.generated_prompt = generated_prompt
            st.success("Prompt generated successfully!")

st.header("🖼️ Generate Image")
image_prompt = st.text_area("Enter the prompt for image generation:", value=st.session_state.get('generated_prompt', ''), key="image_prompt")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.session_state.size = st.selectbox("Image Size", list(IMAGE_SIZES.keys()), format_func=lambda x: IMAGE_SIZES[x])
with col2:
    st.session_state.steps = st.slider("Inference Steps", 1, 100, 28)
with col3:
    st.session_state.guidance = st.slider("Guidance Scale", 0.0, 20.0, 3.5, 0.1)
with col4:
    st.session_state.upscale = st.checkbox("Upscale Image", value=False)

if st.button("Generate Image", key="generate_image_button") or (image_prompt and image_prompt.endswith('\n')):
    if image_prompt:
        with st.spinner("Generating image..."):
            try:
                safety_tolerance = "6"
                num_images = 1  # Set in backend
                seed = 0  # Set in backend
                sync_mode = True  # Set in backend
                images, image_urls, error = generate_image(
                    image_prompt, 
                    st.session_state.size,
                    st.session_state.steps,
                    st.session_state.guidance,
                    num_images,
                    seed,
                    safety_tolerance,
                    sync_mode,
                    st.session_state.upscale
                )
                if images:
                    st.session_state.generated_images = images
                    st.success("Image generated successfully! Scroll down to view.")
                    saved_paths = save_images(images, image_prompt)  # Automatically save images
                    
                    if 'image_history' not in st.session_state:
                        st.session_state.image_history = load_history()
                    
                    history_item = {
                        'image': images[0],
                        'prompt': image_prompt,
                        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.image_history.insert(0, history_item)
                    if len(st.session_state.image_history) > 5:
                        st.session_state.image_history.pop()
                    save_history(st.session_state.image_history)
                elif error:
                    st.error(f"Failed to generate image: {error}")
                    print(f"Error details: {error}")  # Print error details to terminal
                else:
                    st.warning("No image was generated. Please try again.")
            except Exception as e:
                st.error("An unexpected error occurred. Please try again later.")
                print(f"Unexpected error: {str(e)}")  # Print unexpected error details to terminal
                logger.exception("Error in image generation")
    else:
        st.warning("Please enter a prompt for image generation.")

st.header("Generated Image")
if 'generated_images' in st.session_state and st.session_state.generated_images:
    image = st.session_state.generated_images[0]
    
    image_key = f"image_{int(time.time())}"
    
    st.image(image, caption="Generated Image", use_column_width=True, output_format="PNG")
    
    # Add download button
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    href = f'<a href="data:file/png;base64,{img_str}" download="generated_image.png">Download Image</a>'
    st.markdown(href, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div id="modal_{image_key}" class="modal">
        <span class="close" onclick="document.getElementById('modal_{image_key}').style.display='none'">&times;</span>
        <img class="modal-content" id="img_{image_key}">
    </div>
    <script>
    const img = document.querySelector('img[src$=".png"]');
    const modal = document.getElementById('modal_{image_key}');
    const modalImg = document.getElementById('img_{image_key}');
    img.onclick = function(){{
        modal.style.display = "block";
        modalImg.src = this.src;
    }}
    </script>
    """, unsafe_allow_html=True)
    
    if st.button("Upscale Image"):
        with st.spinner("Upscaling image..."):
            upscaled_image = upscale_image(image)
            if upscaled_image:
                output_folder = "generated_images"
                os.makedirs(output_folder, exist_ok=True)
                timestamp = int(time.time())
                filename = f"upscaled_image_{timestamp}.png"
                filepath = os.path.join(output_folder, filename)
                upscaled_image.save(filepath)
                
                with open(filepath, "rb") as file:
                    b64 = base64.b64encode(file.read()).decode()
                    href = f'<a href="data:image/png;base64,{b64}" download="{filename}"></a>'
                    st.markdown(href, unsafe_allow_html=True)
                    st.markdown(f'<script>document.querySelector("a[download=\'{filename}\']").click();</script>', unsafe_allow_html=True)
                
                st.success("Image upscaled and downloaded successfully!")
            else:
                st.error("Failed to upscale image. Please try again.")

st.header("🕰️ Image History")

if 'image_history' not in st.session_state:
    st.session_state.image_history = load_history()

for i, item in enumerate(st.session_state.image_history):
    col1, col2 = st.columns([1, 3])
    with col1:
        if item['image'] is not None:
            st.image(item['image'], caption=f"Generated on {item['timestamp']}", use_column_width=True)
        else:
            st.write("Image not available")
    with col2:
        st.text_area("Prompt", item['prompt'], key=f"history_prompt_{i}", height=100)
        if st.button("Reuse Prompt", key=f"reuse_prompt_{i}"):
            st.session_state.generated_prompt = item['prompt']
            st.rerun()

st.markdown("---")
st.markdown("<p style='text-align: center;'>© 2023 AI Image Alchemist. All rights reserved.</p>", unsafe_allow_html=True)