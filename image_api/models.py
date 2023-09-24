from django.contrib.auth.models import User
from django.db import models
from PIL import Image as PILImage
from django.core import signing
from django.utils import timezone
import os


class CustomTier(models.Model):
    name = models.CharField(max_length=100)
    # Store thumbnail size configurations
    thumbnail_sizes = models.CharField(max_length=100)
    original_file_link = models.BooleanField(default=False)
    expiring_links_enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.name


def get_account_tier_choices():
    # Retrieve custom tiers from the database
    custom_tiers = CustomTier.objects.all()

    # Define the choices for built-in tiers
    ACCOUNT_TIER_CHOICES = [
        ('Basic', 'Basic'),
        ('Premium', 'Premium'),
        ('Enterprise', 'Enterprise'),
    ]

    # Generate choices including predefined and custom tiers
    choices = [(tier[0], tier[0]) for tier in ACCOUNT_TIER_CHOICES]
    choices += [(tier.name, tier.name) for tier in custom_tiers]

    return choices


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_tier = models.CharField(
        max_length=50,  # Adjust max length as needed
        choices=get_account_tier_choices(),
        default='Basic',
        null=True,  # Allow NULL values
        blank=True,  # Make it optional
    )
    custom_tier = models.ForeignKey(
        CustomTier, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username


class Image(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def generate_thumbnail(self, size):
        try:
            with PILImage.open(self.image.path) as img:
                img.thumbnail((size, size))

                # Extract the filename from the image URL
                filename = os.path.basename(self.image.name)

                # Construct the thumbnail directory based on the provided directory structure
                thumbnail_dir = os.path.join('thumbnails', f'{size}px_images')
                thumbnail_path = os.path.join(thumbnail_dir, filename)

                # Create the directory if it doesn't exist
                os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)

                img.save(thumbnail_path)
                return thumbnail_path
        except Exception as e:
            # Handle any errors during image processing
            print("Thumbnail generation error:", str(e))
            return None

    def generate_expiring_link(self, expiration_seconds):
        try:
            expiration_time = timezone.now() + timezone.timedelta(seconds=expiration_seconds)

            # Convert the expiration_time to a string in ISO 8601 format
            expiration_time_str = expiration_time.isoformat()

            # Create a dictionary with the serialized expiration_time
            expiring_link_data = {'image_id': self.pk,
                                  'expiration_time': expiration_time_str}

            # Serialize the dictionary to a JSON string
            signed_url = signing.dumps(expiring_link_data)

            return signed_url
        except Exception as e:
            # Handle any errors during link generation
            return None
