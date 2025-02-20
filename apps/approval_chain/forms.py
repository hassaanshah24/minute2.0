from django import forms
from .models import ApprovalChain, Approver
from django.contrib.auth import get_user_model

User = get_user_model()  # Dynamically fetch the user model

# --- ApprovalChainForm ---
class ApprovalChainForm(forms.ModelForm):
    """
    Form for creating or updating an Approval Chain.
    Ensures unique chain names and a user-friendly input.
    """
    class Meta:
        model = ApprovalChain
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Approval Chain Name'
            }),
        }

    def clean_name(self):
        """
        Ensure the chain name is unique to prevent duplication.
        """
        name = self.cleaned_data.get('name')
        if ApprovalChain.objects.filter(name=name).exists():
            raise forms.ValidationError("An approval chain with this name already exists.")
        return name


# --- ApproverForm ---
class ApproverForm(forms.Form):
    """
    Form for dynamically adding approvers to an approval chain.
    Validates user selection and ensures a valid order.
    """
    user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('username'),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select a user to add as an approver."
    )
    order = forms.IntegerField(
        required=True,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Approver Order'
        }),
        help_text="Specify the sequence order of the approver in the chain."
    )

    def __init__(self, *args, **kwargs):
        """
        Dynamically pass the current approval chain to ensure valid order validation.
        """
        self.approval_chain = kwargs.pop('approval_chain', None)
        super().__init__(*args, **kwargs)

    def clean_order(self):
        """
        Validate that the order is unique within the current approval chain.
        """
        order = self.cleaned_data.get('order')
        if self.approval_chain and Approver.objects.filter(approval_chain=self.approval_chain, order=order).exists():
            raise forms.ValidationError(f"Order {order} already exists in this approval chain.")
        return order

    def clean_user(self):
        """
        Ensure that the selected user is not already an approver in the chain.
        """
        user = self.cleaned_data.get('user')
        if self.approval_chain and Approver.objects.filter(approval_chain=self.approval_chain, user=user).exists():
            raise forms.ValidationError(f"{user.username} is already an approver in this chain.")
        return user
