from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import UserProfile, Image, CustomTier
from .serializers import UserProfileSerializer, ImageSerializer, CustomTierSerializer
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseServerError, StreamingHttpResponse, HttpResponseForbidden, HttpResponseNotFound
from django.core import signing
from django.utils import timezone
from rest_framework.decorators import action
from django.urls import reverse
from django.http import FileResponse  
import os


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAdminUser]


class CustomTierViewSet(viewsets.ModelViewSet):
    queryset = CustomTier.objects.all()
    serializer_class = CustomTierSerializer
    # Ensure only admins can manage tiers
    permission_classes = [permissions.IsAdminUser]


class ImageViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        serializer = ImageSerializer(data=request.data)

        if serializer.is_valid():
            # Ensure that the user is the currently authenticated user
            user = request.user

            # Create and save the image with the authenticated user
            uploaded_image = serializer.validated_data['image']
            image = Image.objects.create(user=user, image=uploaded_image)

            # Set the 'account_tier' attribute on the created instance
            image.account_tier = user.userprofile.account_tier

            # Generate thumbnails, expiring links, etc., based on the account tier
            # Save the image and return appropriate links

            thumbnail_links = {}

            # Handle custom thumbnail sizes if user has a custom tier
            custom_tier = user.userprofile.custom_tier
            if custom_tier and custom_tier.thumbnail_sizes:
                sizes = [int(size)
                         for size in custom_tier.thumbnail_sizes.split(',')]
                for size in sizes:
                    thumbnail_links[f'{size}px'] = image.generate_thumbnail(
                        size)

            # Handle built-in account tiers
            if image.account_tier == 'Basic':
                thumbnail_links['200px'] = image.generate_thumbnail(200)
            elif image.account_tier == 'Premium':
                thumbnail_links['200px'] = image.generate_thumbnail(200)
                thumbnail_links['400px'] = image.generate_thumbnail(400)
                thumbnail_links['original'] = image.image.url
            elif image.account_tier == 'Enterprise':
                thumbnail_links['200px'] = image.generate_thumbnail(200)
                thumbnail_links['400px'] = image.generate_thumbnail(400)
                thumbnail_links['original'] = image.image.url

                # Generate the expiring link and include it in the response
                expiring_link = image.generate_expiring_link(
                    1800)  # 30 minutes expiration
                thumbnail_links['expiring'] = expiring_link

            # Handle custom tier settings
            if custom_tier:
                if custom_tier.original_file_link:
                    thumbnail_links['original'] = f"/images/original/{image.id}/"

                if custom_tier.expiring_links_enabled:
                    expiring_link = image.generate_expiring_link(
                        1800)  # 30 minutes expiration
                    thumbnail_links['expiring'] = expiring_link

                # Handle custom thumbnail sizes
                if custom_tier.thumbnail_sizes:
                    sizes = [int(size)
                             for size in custom_tier.thumbnail_sizes.split(',')]
                    for size in sizes:
                        thumbnail_links[f'{size}px'] = f"/images/thumbnails/{image.id}/{size}px/"
            else:  # Handle built-in tiers
                if image.account_tier == 'Basic':
                    thumbnail_links['200px'] = f"/images/thumbnails/{image.id}/200px/"
                elif image.account_tier == 'Premium':
                    thumbnail_links['200px'] = f"/images/thumbnails/{image.id}/200px/"
                    thumbnail_links['400px'] = f"/images/thumbnails/{image.id}/400px/"
                    thumbnail_links['original'] = f"/images/original/{image.id}/"
                elif image.account_tier == 'Enterprise':
                    thumbnail_links['200px'] = f"/images/thumbnails/{image.id}/200px/"
                    thumbnail_links['400px'] = f"/images/thumbnails/{image.id}/400px/"
                    thumbnail_links['original'] = f"/images/original/{image.id}/"

            # Return the appropriate links in the response
            response_data = {
                "id": image.id,
                "image": image.image.url,
                "uploaded_at": image.uploaded_at,
                "user": image.user.id,
                "thumbnail_links": thumbnail_links,  # Include all thumbnail links
            }
            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request):
        # List all images for the authenticated user
        images = Image.objects.filter(user=request.user)
        serializer = ImageSerializer(images, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='get_expiring_link')
    def get_expiring_link(self, request, pk=None):
        # Check if the user has "Enterprise" plan
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.account_tier != 'Enterprise':
            return Response({'detail': 'You do not have permission to generate expiring links.'}, status=status.HTTP_403_FORBIDDEN)

        # Retrieve the image
        image = get_object_or_404(Image, pk=pk)

        # Generate the expiring link
        expiration_seconds = int(request.query_params.get(
            'expiration_seconds', 1800))  # Default to 30 minutes
        expiring_link = image.generate_expiring_link(expiration_seconds)

        if expiring_link:
            return Response({'expiring_link': expiring_link}, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Error generating expiring link.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def serve_expiring_image(request, image_id, expiring_link):
        # Retrieve the image object using the image_id from the URL
        image = get_object_or_404(Image, pk=image_id)

        # Verify the expiring link
        if not image.is_valid_expiring_link(expiring_link):
            return HttpResponseNotFound('Invalid or expired link.')

        # Serve the image using FileResponse
        try:
            return FileResponse(open(image.image.path, 'rb'), content_type='image/jpeg')
        except FileNotFoundError:
            # Handle the case where the image file is not found
            return HttpResponseNotFound('Image not found.')

    def is_valid_expiring_link(self, expiring_link):
        expiration_data = self.decode_expiring_link(expiring_link)
        if not expiration_data:
            return False

        expiration_time = expiration_data.get('expiration_time')
        return self.is_link_valid(expiration_time)

    def decode_expiring_link(self, signed_url):
        try:
            expiring_data = signing.loads(signed_url)
            print("Decoded expiring data:", expiring_data)
            return expiring_data
        except signing.BadSignature:
            print("Bad signature for expiring link:", signed_url)
            return None

    def is_link_valid(self, expiration_time):
        return timezone.now() < expiration_time

    def fetch_image(self, image_id):
        try:
            image = Image.objects.get(pk=image_id)
            return image
        except Image.DoesNotExist:
            return None


def serve_original_image(request, image_id):
    image = get_object_or_404(Image, pk=image_id)

    # Check if the user has permission to access the original image
    user_profile = UserProfile.objects.get(user=request.user)
    account_tier = user_profile.account_tier

    # Allow access for "Premium" and "Enterprise" tiers and custom tiers with access to the original image configured
    if (
        account_tier in ["Premium", "Enterprise"] or
        (user_profile.custom_tier and user_profile.custom_tier.original_file_link)
    ):
        return FileResponse(open(image.image.path, 'rb'), content_type='image/jpeg')
    else:
        return HttpResponseForbidden('You do not have permission to access the original image.')


def serve_thumbnail_image(request, image_id, size):
    image = get_object_or_404(Image, pk=image_id)
    # Extract the filename from the image URL
    filename = image.image.name.split('/')[-1]

    # Construct the thumbnail path based on the provided directory structure
    thumbnail_dir = f'thumbnails/{size}_images'  # Use forward slashes
    thumbnail_path = os.path.join(thumbnail_dir, filename)

    if os.path.exists(thumbnail_path):
        try:
            def file_iterator(file_path, chunk_size=8192):
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk

            response = StreamingHttpResponse(file_iterator(
                thumbnail_path), content_type='image/jpeg')
            return response
        except FileNotFoundError:
            return HttpResponse('Thumbnail not found', status=404)
        except Exception as e:
            print(f"Error while serving thumbnail: {str(e)}")
            return HttpResponseServerError('Error serving thumbnail')
    else:
        return HttpResponse('Thumbnail not found', status=404)
