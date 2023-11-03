import io
import base64
from PIL import Image

def image_to_base64(image:Image):
    image_binary = io.BytesIO()
    image.save(image_binary, format='JPEG')
    binary_data = image_binary.getvalue()

    base64_data = base64.b64encode(binary_data).decode('utf-8')
    return base64_data

def base64_to_image(base64_image):
    binary_data = base64.b64decode(base64_image)

    # Convert binary data into a PIL Image object
    original_image = Image.open(io.BytesIO(binary_data))
    return original_image