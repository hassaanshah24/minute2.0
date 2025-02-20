from django import forms
from apps.minute.models import Minute, MinuteApproval
from apps.approval_chain.models import ApprovalChain
from django.core.exceptions import ValidationError
from django.utils.timezone import now

class MinuteForm(forms.ModelForm):
    """
    Form to create or update a Minute document.
    Ensures the approval chain is linked before submission.
    """

    approval_chain = forms.ModelChoiceField(
        queryset=ApprovalChain.objects.all(),
        required=False,  # Optional for drafts
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select an approval chain for this minute."
    )

    class Meta:
        model = Minute
        fields = ['title', 'subject', 'description', 'attachment', 'sheet_number', 'approval_chain']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter the title of the minute'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter the subject'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter a detailed description'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
            'sheet_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        """
        Initialize the form and ensure the approval_chain field is preloaded safely.
        """
        self.request = kwargs.pop('request', None)  # Extract request object
        super().__init__(*args, **kwargs)

        # 🔹 Ensure instance exists and contains approval_chain before setting it
        if hasattr(self.instance, 'approval_chain') and 'approval_chain' in self.instance.__dict__:
            self.fields['approval_chain'].initial = self.instance.approval_chain.id if self.instance.approval_chain else None
        else:
            # If 'approval_chain' does not exist, remove it from the fields to prevent KeyError
            self.fields.pop('approval_chain', None)

    def clean(self):
        """
        Custom validation for the form.
        Ensures an approval chain is selected when submitting.
        """
        cleaned_data = super().clean()
        approval_chain = cleaned_data.get('approval_chain')
        is_submit = self.data.get('submit') == 'true'  # Check if form is being submitted

        if is_submit and not approval_chain:
            raise ValidationError("An approval chain is required to submit this minute.")

        return cleaned_data

    def save(self, commit=True):
        """
        Save the Minute instance and link the approval chain before saving.
        """
        instance = super().save(commit=False)
        is_submit = self.data.get('submit') == 'true'

        # Set the status based on whether the form is being submitted or saved as a draft
        instance.status = 'Submitted' if is_submit else 'Draft'

        # Ensure department is assigned properly
        if self.request and hasattr(self.request.user, 'department'):
            instance.department = self.request.user.department

        # Ensure the approval chain is created before saving
        if is_submit and not instance.approval_chain:
            approval_chain = ApprovalChain.objects.create(
                name=f"Approval Chain for {instance.title}",
                created_by=instance.created_by,
                minute=instance  # Link the approval chain to the minute
            )
            instance.approval_chain = approval_chain

        if commit:
            instance.save()
        return instance

class MinuteApprovalForm(forms.ModelForm):
    """
    Form to manage MinuteApproval records.
    Validates action and ensures status consistency.
    """

    class Meta:
        model = MinuteApproval
        fields = ['action', 'remarks']
        widgets = {
            'action': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Optional remarks'}),
        }

    def clean(self):
        """
        Custom validation to ensure action and status consistency.
        """
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        status = self.instance.status if self.instance else 'Pending'

        # Ensure valid transitions between action and status
        if action == 'approve' and status != 'Pending':
            raise ValidationError("Action 'approve' can only be performed on a Pending status.")
        if action == 'reject' and status != 'Pending':
            raise ValidationError("Action 'reject' can only be performed on a Pending status.")

        return cleaned_data

    def save(self, commit=True):
        """
        Save the MinuteApproval instance and set the action timestamp.
        """
        instance = super().save(commit=False)
        if instance.action:
            instance.action_time = now()
        if commit:
            instance.save()
        return instance
