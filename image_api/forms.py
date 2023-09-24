from django import forms
from .models import UserProfile, CustomTier, get_account_tier_choices


class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(UserProfileAdminForm, self).__init__(*args, **kwargs)

        # Customize the account tier field choices
        account_tier_field = self.fields['account_tier']
        account_tier_field.choices = get_account_tier_choices()

    def clean_account_tier(self):
        # Ensure that the selected account tier is either a built-in tier or a custom tier
        account_tier = self.cleaned_data['account_tier']

        # If the selected account tier is a built-in tier or it's empty (None), it's valid
        if not account_tier or account_tier in [choice[0] for choice in get_account_tier_choices()]:
            return account_tier

        # If it's a custom tier, ensure it exists
        if CustomTier.objects.filter(name=account_tier).exists():
            return account_tier

        # If none of the conditions are met, return None (which will trigger a validation error)
        return None
