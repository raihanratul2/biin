"""Remove portrait backgrounds on demand, keeping the original photograph."""
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from urllib import request, error
from urllib.request import urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image

from .models import CampusAmbassadorApplication, IntegrationRecord


class BackgroundRemovalError(Exception):
    pass


def remove_card_background(application, *, force=False, actor=None):
    audit = {}
    try:
        return _remove_card_background(application, force=force, audit=audit)
    except Exception as exc:
        if audit:
            audit['status'] = IntegrationRecord.Status.FAILED
            audit['error_type'] = type(exc).__name__
        raise
    finally:
        # Write after the image transaction exits, including when it rolls back.
        if audit:
            audit['completed_at'] = timezone.now()
            IntegrationRecord.objects.create(
                kind=IntegrationRecord.Kind.REMOVE_BG, application_id=application.pk,
                actor=actor, **audit,
            )


def _remove_card_background(application, *, force, audit):
    # Serialize requests for this application to avoid duplicate paid API calls.
    with transaction.atomic():
        application = CampusAmbassadorApplication.objects.select_for_update().get(pk=application.pk)
        if not force and application.card_cutout and application.card_cutout_source == application.picture.name:
            if application.card_cutout.storage.exists(application.card_cutout.name):
                return
        if not settings.REMOVE_BG_API_KEY:
            raise BackgroundRemovalError('Configure REMOVE_BG_API_KEY before removing backgrounds.')
        if not application.picture:
            raise BackgroundRemovalError('Upload a photograph first.')
        boundary = uuid4().hex
        try:
            with application.picture.open('rb') as source:
                photo = source.read()
            body = (
                f'--{boundary}\r\nContent-Disposition: form-data; name="size"\r\n\r\nauto\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="format"\r\n\r\npng\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="image_file"; filename="portrait.png"\r\n'
                'Content-Type: application/octet-stream\r\n\r\n'
            ).encode() + photo + f'\r\n--{boundary}--\r\n'.encode()
            api_request = request.Request(
                'https://api.remove.bg/v1.0/removebg', data=body, method='POST',
                headers={'X-Api-Key': settings.REMOVE_BG_API_KEY,
                         'Content-Type': f'multipart/form-data; boundary={boundary}'},
            )
            audit.update(status=IntegrationRecord.Status.FAILED)
            try:
                with urlopen(api_request, timeout=settings.REMOVE_BG_TIMEOUT) as response:
                    audit['http_status'] = 200
                    result = response.read(20 * 1024 * 1024 + 1)
                audit['status'] = IntegrationRecord.Status.SUCCESS
            except Exception as exc:
                audit['error_type'] = type(exc).__name__
                if isinstance(exc, error.HTTPError):
                    audit['http_status'] = exc.code
                raise
            finally:
                audit['completed_at'] = timezone.now()
            if len(result) > 20 * 1024 * 1024:
                raise BackgroundRemovalError('Background removal returned an oversized image.')
            with Image.open(BytesIO(result)) as image:
                if image.format != 'PNG':
                    raise BackgroundRemovalError('Background removal returned an invalid image.')
                image.load()
                output = BytesIO()
                image.convert('RGBA').save(output, format='PNG')
        except error.HTTPError as exc:
            messages = {402: 'The remove.bg account has no credits remaining.',
                        403: 'The remove.bg API key was rejected.',
                        429: 'Background removal is busy. Please try again shortly.'}
            raise BackgroundRemovalError(messages.get(exc.code, 'Background removal failed. Please try another photograph.')) from exc
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            raise BackgroundRemovalError('Could not process the photograph. Please try again.') from exc
        application.card_cutout.save(f'{Path(application.picture.name).stem}-{uuid4().hex}.png',
                                    ContentFile(output.getvalue()), save=False)
        application.card_cutout_source = application.picture.name
        application.save(update_fields=['card_cutout', 'card_cutout_source'])
