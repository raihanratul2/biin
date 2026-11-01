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
CARD_TEMPLATE = 'card/card-template.svg'
CARD_SIZE = (1080, 1080)
CAMPUS_LINE_HEIGHT = 44
# Visible text bounds in the template, before centering above the footer.
CONTENT_TOP = 195
CAMPUS_FIRST_LINE_BOTTOM = 721
FOOTER_TOP = 1002.07
CARD_TEXT_FIELDS = (
    ('ambassador-name', 'full_name', 66),
    ('ambassador-campus', 'campus_name', 36),
)

ET.register_namespace('', SVG_NAMESPACE)
ET.register_namespace('xlink', XLINK_NAMESPACE)


def campus_lines(text, max_width, font_size):
    """Wrap campus text at a fixed size in the space above the footer."""
    def fits(value):
        return stringWidth(value, 'Helvetica-Bold', font_size) <= max_width

    lines = []
    remainder = text
    while remainder and len(lines) < 5:
        if fits(remainder):
            lines.append(remainder)
            break
        end = 0
        while end < len(remainder) and fits(remainder[:end + 1]):
            end += 1
        if len(lines) == 4:
            last = remainder[:end].rstrip()
            while last and not fits(last + '…'):
                last = last[:-1]
            lines.append(last.rstrip() + '…')
            break
        # Prefer word boundaries, splitting a single oversized word if needed.
        boundary = remainder.rfind(' ', 0, end + 1)
        end = boundary if boundary > 0 else max(1, end)
        lines.append(remainder[:end].rstrip())
        remainder = remainder[end:].lstrip()
    return lines or ['']


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
        if field == 'full_name':
            element.text = ' '.join(word[0].upper() + word[1:] for word in element.text.split())
        element.attrib.pop('textLength', None)
        element.attrib.pop('lengthAdjust', None)
        # Compress only overflowing text, keeping the original type size otherwise.
        max_width = float(element.attrib['data-max-width'])
        if field == 'campus_name':
            lines = campus_lines(element.text, max_width, font_size)
            element.text = None
            element.set('font-size', f'{font_size:g}px')
            for index, line in enumerate(lines):
                span = ET.SubElement(element, f'{{{SVG_NAMESPACE}}}tspan',
                                     {'x': '0', 'y': str(index * CAMPUS_LINE_HEIGHT)})
                span.text = line
            continue
        if stringWidth(element.text, 'Helvetica-Bold', font_size) > max_width:
            element.set('textLength', element.attrib['data-max-width'])
            element.set('lengthAdjust', 'spacingAndGlyphs')

    campus = root.find(".//*[@id='ambassador-campus']")
    content_bottom = CAMPUS_FIRST_LINE_BOTTOM + (len(campus) - 1) * CAMPUS_LINE_HEIGHT
    offset = (FOOTER_TOP - content_bottom - CONTENT_TOP) / 2
    root.find(".//*[@id='ambassador-content']").set('transform', f'translate(0 {offset:g})')

    picture = application.picture
    if application.card_cutout and application.card_cutout_source == picture.name:
        if application.card_cutout.storage.exists(application.card_cutout.name):
            picture = application.card_cutout
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
