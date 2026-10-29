"""Render the ambassador artwork with an application's own details and portrait."""
from base64 import b64encode
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET

from django.conf import settings
from django.contrib.staticfiles import finders
from PIL import Image, ImageOps
from reportlab.pdfbase.pdfmetrics import stringWidth

from .card_layout import application_photo_position

SVG_NAMESPACE = 'http://www.w3.org/2000/svg'
XLINK_NAMESPACE = 'http://www.w3.org/1999/xlink'
CARD_TEMPLATE = 'card/hamim v4.svg'
CARD_SIZE = (1080, 1080)
CARD_TEXT_FIELDS = (
    ('ambassador-name', 'full_name', 59.6791),
    ('ambassador-campus', 'campus_name', 21.1765),
)

ET.register_namespace('', SVG_NAMESPACE)
ET.register_namespace('xlink', XLINK_NAMESPACE)


def build_ambassador_card(application, *, inline=False):
    template = finders.find(CARD_TEMPLATE)
    if not template:
        template = Path(settings.STATIC_ROOT or settings.BASE_DIR / 'static') / CARD_TEMPLATE
        if not template.is_file():
            template = settings.BASE_DIR / 'static' / CARD_TEMPLATE
    root = ET.parse(template).getroot()
    image = root.find(".//*[@id='ambassador-photo']")
    position = application_photo_position(application)
    # Transform only the portrait, leaving the diagonal mask fixed in place.
    image.set('transform', (
        f"translate({position['x']:g} {position['y']:g}) "
        f"translate(760.62 587.4) scale({position['scale']:g}) "
        'translate(-760.62 -587.4)'
    ))

    for element_id, field, font_size in CARD_TEXT_FIELDS:
        element = root.find(f".//*[@id='{element_id}']")
        element.text = ' '.join(getattr(application, field).split())
        element.attrib.pop('textLength', None)
        element.attrib.pop('lengthAdjust', None)
        # Compress only overflowing text, keeping the original type size otherwise.
        max_width = float(element.attrib['data-max-width'])
        if stringWidth(element.text, 'Helvetica-Bold', font_size) > max_width:
            element.set('textLength', element.attrib['data-max-width'])
            element.set('lengthAdjust', 'spacingAndGlyphs')

    picture = application.picture
    if picture:
        try:
            with picture.open('rb') as source:
                with Image.open(source) as original:
                    portrait = ImageOps.exif_transpose(original).convert('RGBA')
                    portrait.thumbnail((1200, 1600), Image.Resampling.LANCZOS)
                    output = BytesIO()
                    portrait.save(output, format='PNG')
            # Keep the preview and PNG renderer independent of media URLs.
            image.set(f'{{{XLINK_NAMESPACE}}}href',
                      'data:image/png;base64,' + b64encode(output.getvalue()).decode('ascii'))
            root.find(".//*[@id='ambassador-photo-placeholder']").set('display', 'none')
        except (OSError, ValueError):
            # Missing older uploads keep the neutral portrait placeholder.
            pass

    return ET.tostring(root, encoding='utf-8', xml_declaration=not inline)


def build_ambassador_card_png(application):
    from cairosvg import svg2png

    root = ET.fromstring(build_ambassador_card(application))
    # CairoSVG does not implement textLength. Apply the same horizontal fit
    # with a transform so long names stay inside their original text area.
    for element_id, _, font_size in CARD_TEXT_FIELDS:
        element = root.find(f".//*[@id='{element_id}']")
        if 'textLength' in element.attrib:
            width = stringWidth(element.text, 'Helvetica-Bold', font_size)
            scale = float(element.attrib.pop('textLength')) / width
            element.attrib.pop('lengthAdjust', None)
            element.set('transform', f"{element.get('transform', '')} scale({scale:g} 1)")

    rendered = svg2png(bytestring=ET.tostring(root, encoding='utf-8'),
                       output_width=CARD_SIZE[0], output_height=CARD_SIZE[1],
                       background_color='#ffffff')
    output = BytesIO()
    with Image.open(BytesIO(rendered)) as image:
        # Lossless compression, full color, and no unnecessary alpha channel.
        image.convert('RGB').save(output, format='PNG', optimize=True, compress_level=9)
    optimized = output.getvalue()
    return optimized if len(optimized) < len(rendered) else rendered
