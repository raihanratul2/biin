"""Shared printable layout for completed applications and blank paper forms."""
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    Flowable, Image, KeepInFrame, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


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
        [('Department', 'department'), ('Student ID', 'student_id')],
        [('Academic year', 'academic_year'), ('Weekly availability', 'weekly_hours')],
    ]),
    ('03  SOCIAL & PROFESSIONAL PROFILES', [
        [('Facebook', 'facebook_link'), ('LinkedIn', 'linkedin_link')],
        [('Website / portfolio', 'website')],
    ]),
    ('04  EXPERIENCE & SKILLS', [
        [('Previous campus ambassador?', 'has_previous_campus_ambassador'),
         ('Organized campus events?', 'has_organized_campus_events')],
        [('Previous experience', 'previous_experience_details'), ('Skills', 'skills')],
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
                            topMargin=25, bottomMargin=34,
                            title='BIIN Campus Ambassador Application Form')
    ink = colors.HexColor('#18334d')
    line = colors.HexColor('#b9c5cf')
    normal = ParagraphStyle('FormValue', fontName='Helvetica', fontSize=8.5, leading=11,
                            textColor=colors.HexColor('#596574'))
    label = ParagraphStyle('FormLabel', parent=normal, fontName='Helvetica-Bold',
                           fontSize=7.2, leading=9.5, textColor=colors.HexColor('#172b40'))
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
        if key == 'skills':
            from .models import CampusAmbassadorApplication
            selected = {item.strip() for item in str(value).split(',')}
            options = [SkillCheckbox(caption, key in selected)
                       for key, caption in CampusAmbassadorApplication.SKILL_CHOICES]
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
            return [text(caption.upper(), label), Spacer(1, 3), choices]
        return [text(caption.upper(), label), Spacer(1, 3),
                text(value or (' ' if application is None else 'N/A')),
                Spacer(1, 5 if application is None else 1), AnswerLine()]


    def section(application, title, rows):
        data = [[text(title, heading), '']]
        spans = [('SPAN', (0, 0), (1, 0))]
        for row in rows:
            cells = [field(application, caption, key) for caption, key in row]
            if len(cells) == 1:
                spans.append(('SPAN', (0, len(data)), (1, len(data))))
                cells.append('')
            data.append(cells)
        table = Table(data, colWidths=[doc.width / 2] * 2)
        table.setStyle(TableStyle(spans + [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf1f5')),
            ('BOX', (0, 0), (-1, -1), .5, line),
            ('INNERGRID', (0, 1), (-1, -1), .35, line),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
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
        content = [header, Spacer(1, 8),
                   text('CAMPUS AMBASSADOR APPLICATION FORM',
                        ParagraphStyle('FormTitle', parent=heading, alignment=1, fontSize=12, leading=15)),
                   Spacer(1, 4)]
        if application:
            meta = f'Application #{application.pk}  |  Submitted: {application.created_at:%d %b %Y}'
        else:
            meta = 'Please complete in BLOCK LETTERS. Tick the applicable boxes.'
        content.extend([text(meta, label), Spacer(1, 8)])
        for title, rows in SECTIONS:
            content.extend([section(application, title, rows), Spacer(1, 6)])
        content.append(section(application, '06  DECLARATION & SIGNATURE', [
            [('Information provided is accurate', 'declaration_accuracy'),
             ('Program terms accepted', 'declaration_terms')],
        ]) if application else section(None, '06  DECLARATION & SIGNATURE', [
            [('[  ] I confirm the information is accurate and accept the program terms.', 'declaration')],
        ]))
        signature = ('Applicant signature: Signed digitally' if application else
                     'Applicant signature: ____________________________     Date: __________________')
        content.extend([Spacer(1, 14), text(signature, label)])
        story.append(KeepInFrame(doc.width, doc.height - 12, content, mode='shrink'))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(ink)
        canvas.drawString(32, 18, 'BIIN  |  Campus Ambassador Program')
        canvas.drawRightString(A4[0] - 32, 18, f'Page {document.page} of {len(applications)}')
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
