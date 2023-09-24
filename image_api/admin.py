from django.contrib import admin
from .models import UserProfile, Image, CustomTier
from .forms import UserProfileAdminForm


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ('user', 'account_tier', 'custom_tier')
    list_filter = ('account_tier', 'custom_tier')
    search_fields = ('user__username', 'account_tier')
    ordering = ('user__username',)


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('user', 'uploaded_at')
    list_filter = ('user', 'uploaded_at')
    search_fields = ('user__username',)
    ordering = ('-uploaded_at',)


@admin.register(CustomTier)
class CustomTierAdmin(admin.ModelAdmin):
    list_display = ('name', 'thumbnail_sizes',
                    'original_file_link', 'expiring_links_enabled')
    list_filter = ('original_file_link', 'expiring_links_enabled')
    search_fields = ('name',)
