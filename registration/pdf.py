"""Shared printable layout for completed applications and blank paper forms."""
from xml.sax.saxutils import escape

from PIL import Image as PILImage, ImageOps
from reportlab.lib.utils import ImageReader

from .pdf_layout import LONG_FIELDS, field_height

from django.conf import settings
from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    Flowable, Image, KeepInFrame, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


class PassportPhoto(Flowable):
    """Fixed portrait box shared by uploaded photos and printable forms."""
    width = 90
    height = 114

    def __init__(self, application):
        super().__init__()
        self.width, self.height = 90, 114
        self.photo = None
        picture = getattr(application, 'picture', None)
        if picture:
            try:
                with picture.open('rb') as source:
                    with PILImage.open(source) as original:
                        portrait = ImageOps.exif_transpose(original).convert('RGB')
                        portrait = ImageOps.fit(portrait, (600, 760))
                        self.photo = ImageReader(portrait)
            except (OSError, ValueError):
                # Older submissions may reference a photo that is no longer stored.
                pass

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        if self.photo:
            canvas.drawImage(self.photo, 0, 0, self.width, self.height)
        else:
            canvas.setFillColor(colors.HexColor('#596574'))
            canvas.setFont('Helvetica', 9)
            canvas.drawCentredString(self.width / 2, self.height / 2, 'Passport Size')
            canvas.setFont('Helvetica', 8)
            canvas.drawCentredString(self.width / 2, self.height / 2 - 13, 'Photograph')
        canvas.setStrokeColor(colors.HexColor('#b9c5cf'))
        canvas.rect(0, 0, self.width, self.height)
        canvas.restoreState()


class AnswerLine(Flowable):
    """A dashed writing line that follows the width of its form cell."""
    def __init__(self):
        super().__init__()
        self.height = 5

    def wrap(self, available_width, available_height):
        self.width = available_width
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(colors.HexColor('#a6afb9'))
        self.canv.setLineWidth(.4)
        self.canv.setDash(3, 2)
        self.canv.line(0, 1, self.width, 1)
        self.canv.restoreState()


class FixedFieldValue(Flowable):
    """Reserve the same value height for empty and completed fields."""
    def __init__(self, paragraph, height):
        super().__init__()
        self.paragraph = paragraph
        self.height = height

    def wrap(self, available_width, available_height):
        self.width = available_width
        return self.width, self.height

    def draw(self):
        value = KeepInFrame(self.width, self.height, [self.paragraph], mode='shrink')
        _, height = value.wrapOn(self.canv, self.width, self.height)
        value.drawOn(self.canv, 0, self.height - height)


class TwoLineAnswer(Flowable):
    """A fixed answer area with two writing lines for section 05."""
    def __init__(self, paragraph, lines=2, line_height=15):
        super().__init__()
        self.paragraph = paragraph
        self.lines = lines
        self.line_height = line_height
        self.height = lines * line_height

    def wrap(self, available_width, available_height):
        self.width = available_width
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#a6afb9'))
        canvas.setLineWidth(.4)
        canvas.setDash(3, 2)
        for y in range(0, self.height, self.line_height):
            canvas.line(0, y, self.width, y)
        canvas.restoreState()
        paragraph = self.paragraph
        _, height = paragraph.wrap(self.width, self.height)
        if height > self.height:
            # Keep the writing-line spacing fixed while fitting at most N lines.
            low, high = .1, paragraph.style.fontSize
            for _ in range(24):
                size = (low + high) / 2
                style = ParagraphStyle('FittedAnswer', parent=paragraph.style, fontSize=size)
                candidate = Paragraph(paragraph.text, style)
                _, candidate_height = candidate.wrap(self.width, self.height)
                if candidate_height <= self.height:
                    low = size
                else:
                    high = size
            paragraph = Paragraph(paragraph.text, ParagraphStyle(
                'FittedAnswer', parent=paragraph.style, fontSize=low))
            _, height = paragraph.wrap(self.width, self.height)
        paragraph.drawOn(canvas, 0, self.height - height)


class SkillCheckbox(Flowable):
    def __init__(self, caption, selected=False):
        super().__init__()
        self.caption = caption
        self.selected = selected
        self.height = 15

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#24374b'))
        canvas.setFillColor(colors.HexColor('#24374b') if self.selected else colors.white)
        canvas.roundRect(0, 3, 8, 8, 1, fill=1, stroke=1)
        if self.selected:
            canvas.setStrokeColor(colors.white)
            canvas.setLineWidth(1)
            path = canvas.beginPath()
            path.moveTo(1.5, 7)
            path.lineTo(3.5, 5)
            path.lineTo(6.5, 9)
            canvas.drawPath(path)
        canvas.setFillColor(colors.HexColor('#596574'))
        canvas.setFont('Helvetica', 7.5)
        canvas.drawString(13, 4, self.caption)
        canvas.restoreState()


SECTIONS = [
    ('01  PERSONAL INFORMATION', [
        [('Full name', 'full_name'), ('Phone number', 'phone_number')],
        [('Email address', 'email'), ('Present address', 'address')],
    ]),
    ('02  ACADEMIC INFORMATION', [
        [('Campus / institution', 'campus_name')],
        [('Department', 'department'), ('Student ID', 'student_id'),
         ('Academic year', 'academic_year'), ('Weekly availability', 'weekly_hours')],
    ]),
    ('03  SOCIAL & PROFESSIONAL PROFILES', [
        [('Facebook', 'facebook_link'), ('LinkedIn', 'linkedin_link'),
         ('Website / portfolio', 'website')],
    ]),
    ('04  EXPERIENCE & SKILLS', [
        [('Previous campus ambassador?', 'has_previous_campus_ambassador'),
         ('Organized campus events?', 'has_organized_campus_events')],
        [('Skills', 'skills'), ('Previous experience', 'previous_experience_details')],
    ]),
    ('05  MOTIVATION & CAMPUS ENGAGEMENT', [
        [('Why do you want to join?', 'motivation')],
        [('How will you promote BIIN?', 'promotion_plan')],
        [('Activities you plan to organize', 'activities_to_organize')],
        [('Active student network?', 'has_active_student_network')],
    ]),
]


def build_application_pdf(response, applications):
    applications = list(applications)
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=32, leftMargin=32,
                            topMargin=25, bottomMargin=60,
                            title='BIIN Campus Ambassador Application Form')
    ink = colors.HexColor('#18334d')
    line = colors.HexColor('#b9c5cf')
    normal = ParagraphStyle('FormValue', fontName='Helvetica', fontSize=8.5, leading=9,
                            textColor=colors.HexColor('#596574'))
    label = ParagraphStyle('FormLabel', parent=normal, fontName='Helvetica-Bold',
                           fontSize=7.2, leading=8, textColor=colors.HexColor('#172b40'))
    heading = ParagraphStyle('FormHeading', parent=normal, fontName='Helvetica-Bold',
                             fontSize=8, leading=11, textColor=ink)

    def text(value, style=normal):
        return Paragraph(escape(str(value)).replace('\n', '<br/>'), style)

    def field(application, caption, key):
        value = getattr(application, key, '') if application else ''
        if isinstance(value, bool):
            value = 'Yes' if value else 'No'
        if application is None and key.startswith('has_'):
            value = '[  ] Yes     [  ] No'
        if key in {'has_previous_campus_ambassador', 'has_organized_campus_events'}:
            width = doc.width / 2 - 16
            choices = Table([[
                text(caption.upper(), label),
                SkillCheckbox('Yes', application is not None and value == 'Yes'),
                SkillCheckbox('No', application is not None and value == 'No'),
            ]], colWidths=[width - 72, 36, 36])
            choices.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            return [choices]
        if key == 'previous_experience_details':
            return [text(caption.upper(), label), Spacer(1, 2),
                    TwoLineAnswer(
                        text(' '.join(str(value).split()) or ' ',
                             ParagraphStyle('ExperienceValue', parent=normal, leading=23)),
                        lines=3, line_height=23)]
        if key == 'skills':
            from .models import CampusAmbassadorApplication
            selected = {item.strip() for item in str(value).split(',')}
            options = [SkillCheckbox(caption, key in selected)
                       for key, caption in CampusAmbassadorApplication.SKILL_CHOICES]
            for option in options:
                option.height = 13
            rows = [options[i:i + 2] for i in range(0, len(options), 2)]
            if len(rows[-1]) == 1:
                rows[-1].append('')
            choices = Table(rows, colWidths=[(doc.width / 2 - 16) / 2] * 2)
            choices.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            return [text(caption.upper(), label), Spacer(1, 1), choices]
        if key in LONG_FIELDS:
            return [text(caption.upper(), label), Spacer(1, 2),
                    TwoLineAnswer(text(' '.join(str(value).split()) or ' ',
                                       ParagraphStyle('TwoLineValue', parent=normal, leading=15)))]
        return [text(caption.upper(), label), Spacer(1, 2),
                FixedFieldValue(
                    text(' '.join(str(value).split()) or (' ' if application is None else 'N/A')),
                    field_height(key) - 21), AnswerLine()]



    def section(application, title, rows):
        data = [[text(title, heading), '']]
        spans = [('SPAN', (0, 0), (1, 0))]
        widths = [doc.width / 2] * 2
        if title.startswith('01 '):
            widths = [doc.width - 110, 110]
            personal = [('Full name', 'full_name'), ('Phone number', 'phone_number'),
                        ('Email address', 'email'), ('Present address', 'address')]
            data.extend([[field(application, caption, key), PassportPhoto(application) if i == 0 else '']
                         for i, (caption, key) in enumerate(personal)])
            spans.append(('SPAN', (1, 1), (1, 4)))
            row_heights = [19, 30, 30, 30, 30]
        elif title.startswith('02 ') or title.startswith('03 '):
            columns = 4 if title.startswith('02 ') else 3
            widths = [doc.width / columns] * columns
            data = [[text(title, heading)] + [''] * (columns - 1)]
            spans = [('SPAN', (0, 0), (columns - 1, 0))]
            for row in rows:
                cells = [field(application, caption, key) for caption, key in row]
                if len(cells) == 1:
                    spans.append(('SPAN', (0, len(data)), (columns - 1, len(data))))
                    cells += [''] * (columns - 1)
                data.append(cells)
            row_heights = [19] + [30] * len(rows)
        elif title.startswith('04 '):
            questions = []
            for caption, key in rows[0]:
                questions.extend(field(application, caption, key))
            data.extend([
                [questions, field(application, 'Previous experience', 'previous_experience_details')],
                [field(application, 'Skills', 'skills'), ''],
            ])
            spans.append(('SPAN', (1, 1), (1, 2)))
            row_heights = [19, 36, 54]
        else:
            for row in rows:
                cells = [field(application, caption, key) for caption, key in row]
                if len(cells) == 1:
                    spans.append(('SPAN', (0, len(data)), (1, len(data))))
                    cells.append('')
                data.append(cells)
            row_heights = [19] + [max(field_height(key) for _, key in row) for row in rows]
        table = Table(data, colWidths=widths, rowHeights=row_heights)
        table.setStyle(TableStyle(spans + [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf1f5')),
            ('BOX', (0, 0), (-1, -1), .5, line),
            ('INNERGRID', (0, 1), (-1, -1), .35, line),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return table

    story = []
    for index, application in enumerate(applications):
        if index:
            story.append(PageBreak())
        contact_style = ParagraphStyle('Contact', parent=label, fontSize=8.5, leading=12)
        brand = [
            text('BANGLADESH ICT AND INNOVATION NETWORK',
                 ParagraphStyle('Company', parent=heading, fontSize=12.5, leading=16)),
            Spacer(1, 3),
            text(getattr(settings, 'BIIN_OFFICE_ADDRESS', 'SimpleTree Attalika (Level 19), 134 Gulshan Avenue, Dhaka 1212, Bangladesh'), contact_style),
            text(getattr(settings, 'BIIN_CONTACT_EMAIL', 'info@biin.org.bd'), contact_style),
        ]
        phone = getattr(settings, 'BIIN_CONTACT_PHONE', '+88 09640 123 701-3')
        if phone:
            brand.append(text(phone, contact_style))
        logo_path = finders.find('BIIN_Logo.png')
        logo = Image(logo_path, width=80, height=52, kind='proportional') if logo_path else text('BIIN', heading)
        header = Table([[logo, brand]], colWidths=[96, doc.width - 96])
        header.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                   ('LINEBELOW', (0, 0), (-1, -1), 1, ink),
                                   ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f2f5f8')),
                                   ('TOPPADDING', (0, 0), (-1, -1), 9),
                                   ('BOTTOMPADDING', (0, 0), (-1, -1), 10)]))
        content = [KeepInFrame(doc.width, 90, [header], mode='shrink'), Spacer(1, 8),
                   text('CAMPUS AMBASSADOR APPLICATION FORM',
                        ParagraphStyle('FormTitle', parent=heading, alignment=1, fontSize=12, leading=15)),
                   Spacer(1, 4)]
        if application:
            meta = (
                f'Application #{application.pk}  |  Submitted: {application.created_at:%d %b %Y}'
                if application.pk is not None else 'SAMPLE APPLICATION — Email delivery test'
            )
        else:
            meta = 'Please complete in BLOCK LETTERS. Tick the applicable boxes.'
        content.extend([text(meta, label), Spacer(1, 8)])
        for title, rows in SECTIONS:
            content.extend([section(application, title, rows), Spacer(1, 4)])
        story.extend(content)

    def footer(canvas, document):
        canvas.saveState()
        application = applications[document.page - 1]
        canvas.setFont('Helvetica-Bold', 7.2)
        canvas.setFillColor(ink)
        signature = ('Applicant signature: Signed digitally' if application is not None else
                     'Applicant signature: ____________________________     Date: __________________')
        canvas.drawString(32, 42, signature)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(ink)
        canvas.drawString(32, 18, 'BIIN  |  Campus Ambassador Program')
        canvas.drawRightString(A4[0] - 32, 18, f'Page {document.page} of {len(applications)}')
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
