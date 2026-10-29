"""Validate and normalize application portraits before storing them."""
from io import BytesIO
import warnings

from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PHOTO_BYTES = 3 * 1024 * 1024
PHOTO_SIZE = (600, 760)  # Same 15:19 portrait ratio as the PDF's 90 x 114 box.


class ApplicationPhotoField(forms.ImageField):
    def to_python(self, data):
        if data and getattr(data, 'size', 0) > MAX_PHOTO_BYTES:
            raise forms.ValidationError('Choose a photograph no larger than 3 MB.')
        return super().to_python(data)


def optimize_photo(upload):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            upload.seek(0)
            with Image.open(upload) as image:
                if image.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise forms.ValidationError('Choose a JPG, PNG or WebP photograph.')
                portrait = ImageOps.fit(ImageOps.exif_transpose(image).convert('RGBA'),
                                        PHOTO_SIZE, method=Image.Resampling.LANCZOS)
                # Composite at the final size to keep the card frame opaque,
                # without allocating another full-size copy of a large upload.
                background = Image.new('RGBA', PHOTO_SIZE, 'white')
                background.alpha_composite(portrait)
                portrait = background.convert('RGB')
                output = BytesIO()
                portrait.save(output, 'PNG', optimize=True, compress_level=9)
    except (OSError, ValueError, UnidentifiedImageError,
            Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
        raise forms.ValidationError('This photograph could not be processed. Choose another image.') from error
    return SimpleUploadedFile('passport.png', output.getvalue(), content_type='image/png')
