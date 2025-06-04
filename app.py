from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from rembg import remove
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
import io
import os
import random # For randomization

app = Flask(__name__)
CORS(app)

# --- Configuration ---
FONT_WISHES_PATH = "Anton-Regular.ttf"
FONT_NAME_PATH = "Anton-Regular.ttf" # Can be the same or different

# --- Helper Functions ---
def get_random_wish_text_style(image):
    """
    Returns a random style (color, stroke) for wishes text.
    This is a simplified "randomization related to background."
    A more advanced version would analyze image regions.
    """
    styles = [
        {"fill": (255, 255, 255, 255), "stroke": (0, 0, 0, 255), "stroke_width": 2}, # White, black outline
        {"fill": (255, 220, 0, 255), "stroke": (50, 50, 0, 255), "stroke_width": 2}, # Yellow, dark gold outline
        {"fill": (20, 20, 20, 255), "stroke": (220, 220, 220, 255), "stroke_width": 2}, # Dark, light outline
        {"fill": (230, 230, 230, 255), "stroke": None}, # Light Gray, no outline (like example 1)
        {"fill": (255, 255, 0, 255), "stroke": None}    # Bright Yellow, no outline (like example 2)
    ]
    return random.choice(styles)

def get_random_name_text_style(image):
    """
    Returns a random style (color, stroke) for name text.
    """
    styles = [
        {"fill": (255, 220, 0, 255), "stroke": (50, 50, 0, 255), "stroke_width": 3},   # Bright Yellow, dark outline
        {"fill": (255, 255, 255, 255), "stroke": (0, 0, 0, 255), "stroke_width": 3},   # White, black outline
        {"fill": (50, 200, 255, 255), "stroke": (0, 0, 50, 255), "stroke_width": 3},   # Light Blue, dark blue outline
        {"fill": (255, 100, 150, 255), "stroke": (50, 0, 0, 255), "stroke_width": 3}, # Pink, dark red outline
    ]
    return random.choice(styles)

def get_random_vertical_offset_factor():
    """ Returns a small random factor for vertical position adjustment. """
    return random.uniform(-0.03, 0.03) # Adjusts position by up to 3% of image height

# --- API Endpoints ---
@app.route('/process-image', methods=['POST'])
def process_image_endpoint():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    # ... (other initial checks for wishes_text, name_text are good)

    file = request.files['image']
    wishes_text_input = request.form['wishes_text']
    name_text_input = request.form['name_text']
    text_lines_option = request.form.get('text_lines', 'single')
    
    # Get font size multipliers from frontend, default to 1.0 (no change)
    wishes_font_size_multiplier = float(request.form.get('wishes_font_size_multiplier', 1.0))
    name_font_size_multiplier = float(request.form.get('name_font_size_multiplier', 1.0))
    # is_regenerate = request.form.get('regenerate', 'false').lower() == 'true' # Flag for regeneration

    try:
        input_image_bytes = file.read()
        input_image_pil = Image.open(io.BytesIO(input_image_bytes)).convert("RGBA")
    except UnidentifiedImageError:
        return jsonify({"error": "Cannot identify image file. Is it a valid image?"}), 400
    except Exception as e:
        return jsonify({"error": f"Error opening image: {str(e)}"}), 500

    try:
        bg_removed_bytes = remove(input_image_bytes)
        bg_removed_pil = Image.open(io.BytesIO(bg_removed_bytes)).convert("RGBA")
    except Exception as e:
        app.logger.error(f"Background removal failed: {e}")
        return jsonify({"error": f"Background removal failed: {str(e)}"}), 500

    output_image = input_image_pil.copy()
    draw = ImageDraw.Draw(output_image)
    img_width, img_height = output_image.size

    # --- Wishes Text ---
    # Apply font size multiplier
    initial_font_size_wishes = int((img_height / 10) * wishes_font_size_multiplier)
    if initial_font_size_wishes < 10: initial_font_size_wishes = 10 # Minimum font size

    font_wishes = ImageFont.truetype(FONT_WISHES_PATH, initial_font_size_wishes)
    max_text_width = img_width * 0.9

    wishes_texts_to_draw = []
    # ... (text splitting logic remains the same)
    if text_lines_option == 'double' and ' ' in wishes_text_input and img_height > img_width : # Portrait or square-ish
        # Simple split for two lines
        # Try to split near the middle, preferring a space before the middle
        split_point = -1
        # Look for a space in the first half, biasing towards the end of the first half
        search_end = len(wishes_text_input) // 2 + (len(wishes_text_input) % 2) # Include middle char for odd lengths
        for i in range(search_end, 0, -1):
            if wishes_text_input[i] == ' ':
                split_point = i
                break
        if split_point == -1: # If no space in first half, find first space overall
            split_point = wishes_text_input.find(' ')

        if split_point == -1: # no spaces at all
            line1 = wishes_text_input
            line2 = ""
        else:
            line1 = wishes_text_input[:split_point].strip()
            line2 = wishes_text_input[split_point+1:].strip()
        wishes_texts_to_draw = [line1, line2]
        if not line2: # if second line becomes empty after strip
             wishes_texts_to_draw = [line1]
    else: # Single line or landscape
        wishes_texts_to_draw = [wishes_text_input]


    # Get randomized style for wishes text
    wish_style = get_random_wish_text_style(output_image)
    wish_text_fill_color = wish_style["fill"]
    wish_text_stroke_color = wish_style.get("stroke")
    wish_text_stroke_width = wish_style.get("stroke_width", 0)

    # Random vertical offset for wishes text block
    vertical_offset_wish = img_height * get_random_vertical_offset_factor()
    current_y = (img_height * 0.05) + vertical_offset_wish
    if current_y < img_height * 0.02 : current_y = img_height * 0.02 # Min top margin
    
    total_wishes_text_height = 0
    adjusted_wishes_texts = []

    # First pass: adjust font size for all lines to fit
    common_font_size_wishes = initial_font_size_wishes
    temp_font_wishes = ImageFont.truetype(FONT_WISHES_PATH, common_font_size_wishes)

    for line_text in wishes_texts_to_draw:
        if not line_text.strip(): continue
        while temp_font_wishes.getbbox(line_text)[2] > max_text_width and common_font_size_wishes > 10:
            common_font_size_wishes -= 2
            if common_font_size_wishes < 10: common_font_size_wishes = 10
            temp_font_wishes = ImageFont.truetype(FONT_WISHES_PATH, common_font_size_wishes)
            if common_font_size_wishes <=10: break # Prevent infinite loop if text is too long even at min size

    # Second pass: draw with the determined common font size
    final_font_wishes = ImageFont.truetype(FONT_WISHES_PATH, common_font_size_wishes)
    for line_text in wishes_texts_to_draw:
        if not line_text.strip(): continue
        
        text_bbox = final_font_wishes.getbbox(line_text)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1] # Actual rendered height of the line
        
        x = (img_width - text_width) / 2
        y = current_y
        
        draw.text((x, y), line_text, font=final_font_wishes, fill=wish_text_fill_color,
                  stroke_width=wish_text_stroke_width if wish_text_stroke_color else 0,
                  stroke_fill=wish_text_stroke_color)
        current_y += text_height + (img_height * 0.02) # Add spacing

    # Step 5: Overlay bg_removed_pil
    if bg_removed_pil.size != output_image.size:
        bg_removed_pil = bg_removed_pil.resize(output_image.size, Image.Resampling.LANCZOS)
    output_image.paste(bg_removed_pil, (0,0), bg_removed_pil)

    # --- Name Text ---
    initial_font_size_name = int((img_height / 12) * name_font_size_multiplier)
    if initial_font_size_name < 10: initial_font_size_name = 10

    font_name = ImageFont.truetype(FONT_NAME_PATH, initial_font_size_name)
    max_name_text_width = img_width * 0.8

    # Get randomized style for name text
    name_style = get_random_name_text_style(output_image)
    name_text_fill_color = name_style["fill"]
    name_text_stroke_color = name_style.get("stroke")
    name_text_stroke_width = name_style.get("stroke_width", 0)
    
    # Adjust font size to fit
    current_font_size_name = initial_font_size_name
    current_font_name = ImageFont.truetype(FONT_NAME_PATH, current_font_size_name)
    while current_font_name.getbbox(name_text_input)[2] > max_name_text_width and current_font_size_name > 10:
        current_font_size_name -= 2
        if current_font_size_name < 10: current_font_size_name = 10
        current_font_name = ImageFont.truetype(FONT_NAME_PATH, current_font_size_name)
        if current_font_size_name <= 10: break


    name_text_bbox = current_font_name.getbbox(name_text_input)
    name_text_width = name_text_bbox[2] - name_text_bbox[0]
    name_text_height = name_text_bbox[3] - name_text_bbox[1]

    name_x = (img_width - name_text_width) / 2
    
    # Random vertical offset for name text (subtler for bottom text)
    vertical_offset_name = img_height * random.uniform(-0.02, 0.02)
    name_y = img_height - name_text_height - (img_height * 0.05) + vertical_offset_name
    if name_y > img_height - name_text_height - (img_height * 0.02): # Max bottom margin
        name_y = img_height - name_text_height - (img_height * 0.02)
    if name_y < img_height * 0.5: # Don't let it go too high
        name_y = img_height * 0.5


    draw.text((name_x, name_y), name_text_input, font=current_font_name, fill=name_text_fill_color,
              stroke_width=name_text_stroke_width if name_text_stroke_color else 0,
              stroke_fill=name_text_stroke_color)

    # Convert to RGB before saving
    if output_image.mode == 'RGBA':
        output_image = output_image.convert('RGB')

    byte_arr = io.BytesIO()
    output_image.save(byte_arr, format='JPEG', quality=90)
    byte_arr.seek(0)

    return send_file(byte_arr, mimetype='image/jpeg', as_attachment=True, download_name=f"{name_text_input.replace(' ', '_')}_card.jpg")

if __name__ == '__main__':
    if not os.path.exists(FONT_WISHES_PATH) or not os.path.exists(FONT_NAME_PATH):
        print(f"ERROR: Font file not found. Ensure '{FONT_WISHES_PATH}' and '{FONT_NAME_PATH}' exist.")
        exit()
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
