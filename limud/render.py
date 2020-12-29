import pathlib

# from bidi.algorithm import get_display
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

# Rendering parameters
ASSETS_ROOT = pathlib.Path.cwd() / "static"
FONT_PATH = ASSETS_ROOT / "KeterYG-Medium.ttf"
DEFAULT_HEIGHT = 500
DEFAULT_WIDTH = 1000
DEFAULT_TEXT_POSITION = (DEFAULT_WIDTH // 4, DEFAULT_HEIGHT // 4)
DEFAULT_FONT_SIZE = 120
DEFAULT_BACKGROUND_COLOR = (0, 0, 0, 255)
DEFAULT_FOREGROUND_COLOR = (255, 255, 255, 255)


def render_hebrew_text(text: str):
    #text = get_display(text)

    image = PIL.Image.new(
        mode="RGBA",
        size=(DEFAULT_WIDTH, DEFAULT_HEIGHT),
        color=DEFAULT_BACKGROUND_COLOR)

    font = PIL.ImageFont.truetype(
        font=str(FONT_PATH.absolute()),
        size=DEFAULT_FONT_SIZE)

    draw = PIL.ImageDraw.Draw(image)
    draw.text(
        xy=DEFAULT_TEXT_POSITION,
        text=text,
        font=font,
        fill=DEFAULT_FOREGROUND_COLOR)
    
    image.show()