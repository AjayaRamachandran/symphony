# gui/vfx.py
# handles visual effects of gui elements, like blurring, etc.

###### IMPORT ######

import cv2
from io import BytesIO
import numpy as np
import pygame

##### METHODS ######

def processImage(image_bytes: bytes, width: int, height: int, blurRadius: int) -> BytesIO:
    """
    fields:
        image_bytes (bytes): Raw image bytes (e.g., from a file or surface).
        crop_width (int): Width in pixels to crop from the left side.
    outputs:
        BytesIO: A buffer containing the blurred, cropped JPEG image.

    Blur and crop an image provided as raw bytes.
    """
    image = np.frombuffer(image_bytes, np.uint8).reshape((height, width, 3))

    # Convert RGB (pygame) → BGR (opencv)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    # Kernel size must be odd
    k = blurRadius if blurRadius % 2 == 1 else blurRadius + 1
    blurred = cv2.GaussianBlur(image, (k, k), 0)

    success, buffer = cv2.imencode(".jpg", blurred)
    if not success:
        raise ValueError("Failed to encode image.")

    return BytesIO(buffer.tobytes())


def surfaceBlur(surface: pygame.Surface, blurRadius: 5) -> pygame.Surface:
    """
    fields:
        surface (pygame.Surface): Input Pygame surface.
        crop_width (int): Width in pixels to crop from the left side.
    outputs:
        pygame.Surface: A new Pygame surface containing the blurred image.
        
    Apply a blur to a Pygame surface using OpenCV and return a new surface.
    """
    width, height = surface.get_size()

    image_bytes = pygame.image.tostring(surface, "RGB")

    image_io = processImage(image_bytes, width, height, blurRadius)
    image_io.seek(0)

    return pygame.image.load(image_io).convert()