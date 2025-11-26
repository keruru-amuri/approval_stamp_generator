from flask import Flask, render_template, jsonify, request, send_from_directory, send_file
import os
import json
from PIL import Image, ImageDraw, ImageFont
import io

app = Flask(__name__)
STAMP_FOLDER = os.path.join(os.getcwd(), 'stamp')
CONFIG_FILE = 'stamp_config.json'

# Ensure config file exists
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({}, f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calibrate')
def calibrate():
    return render_template('calibration.html')

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(STAMP_FOLDER, filename)

@app.route('/api/stamps')
def list_stamps():
    if not os.path.exists(STAMP_FOLDER):
        return jsonify([])
    files = [f for f in os.listdir(STAMP_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return jsonify(files)

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        data = request.json
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return jsonify({"status": "success"})
    else:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                try:
                    return jsonify(json.load(f))
                except json.JSONDecodeError:
                    return jsonify({})
        return jsonify({})

def generate_stamp_image(stamp_name, approval_number, target_width=None):
    """
    Generate a stamp image with the given approval number.
    
    Args:
        stamp_name: Name of the stamp file
        approval_number: Text to draw on the stamp
        target_width: Optional width to resize to (maintains aspect ratio)
    
    Returns:
        PIL Image object
    """
    # Load config
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    if stamp_name not in config:
        raise ValueError("Stamp not configured")
    
    stamp_config = config[stamp_name]
    
    # Load Image
    image_path = os.path.join(STAMP_FOLDER, stamp_name)
    try:
        img = Image.open(image_path).convert("RGBA")
    except FileNotFoundError:
        raise FileNotFoundError("Image not found")
    
    # Calculate scale factor if resizing
    scale_factor = 1.0
    if target_width:
        original_width = img.width
        scale_factor = target_width / original_width
        # Resize image first
        new_height = int(img.height * scale_factor)
        img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)

    # Draw Text
    draw = ImageDraw.Draw(img)
    
    # Font handling - support both Windows and Linux font paths
    # Also check for bundled fonts in the fonts/ directory
    font_map_bundled = {
        "Arial": "fonts/LiberationSans-Regular.ttf",
        "Verdana": "fonts/LiberationSans-Regular.ttf",
        "Times New Roman": "fonts/LiberationSerif-Regular.ttf",
        "Courier New": "fonts/LiberationMono-Regular.ttf",
        "Georgia": "fonts/LiberationSerif-Regular.ttf",
        "Impact": "fonts/LiberationSans-Bold.ttf"
    }
    
    font_map_linux = {
        "Arial": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "Verdana": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "Times New Roman": "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "Courier New": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "Georgia": "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "Impact": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    }
    
    font_map_windows = {
        "Arial": "arial.ttf",
        "Verdana": "verdana.ttf",
        "Times New Roman": "times.ttf",
        "Courier New": "cour.ttf",
        "Georgia": "georgia.ttf",
        "Impact": "impact.ttf"
    }
    
    font_name = stamp_config.get('font', 'Arial')
    font_size = int(stamp_config.get('size', 24) * scale_factor)
    
    # Try multiple font paths in order of preference
    font = None
    font_paths_to_try = [
        font_map_bundled.get(font_name),  # Try bundled fonts first
        font_map_linux.get(font_name),  # Try Linux system fonts
        font_map_windows.get(font_name),  # Try Windows fonts
        font_name,  # Try the name directly
    ]
    
    for font_path in font_paths_to_try:
        if font_path:
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    break
                else:
                    # Try without checking existence (for system fonts)
                    font = ImageFont.truetype(font_path, font_size)
                    break
            except (IOError, OSError):
                continue
    
    # If no font loaded, use default
    if font is None:
        print(f"Warning: Could not load font {font_name}. Using default.")
        # Use a larger default font size by creating a scaled default
        font = ImageFont.load_default()

    text_color = stamp_config.get('color', '#000000')
    x = int(stamp_config.get('x', 0) * scale_factor)
    y = int(stamp_config.get('y', 0) * scale_factor)

    # Draw text centered at the coordinates (matching calibration logic)
    bbox = draw.textbbox((0, 0), approval_number, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Adjust x, y to be top-left for PIL, based on center coordinates
    draw_x = x - (text_width / 2)
    draw_y = y - (text_height / 2)
    
    draw.text((draw_x, draw_y), approval_number, font=font, fill=text_color)
    
    return img

@app.route('/generate', methods=['POST'])
def generate_stamp():
    data = request.json
    stamp_name = data.get('stamp')
    approval_number = data.get('number')
    width = data.get('width')  # Optional width parameter

    if not stamp_name or not approval_number:
        return jsonify({"error": "Missing data"}), 400

    try:
        img = generate_stamp_image(stamp_name, approval_number, width)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404

    # Save to buffer
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    # Azure Web App will use the WEBSITE_HOSTNAME environment variable
    # Use PORT environment variable if available (for Azure), otherwise default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
