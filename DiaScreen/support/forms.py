from django import forms

from .models import SupportTicket


class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ("subject", "description", "page_context")
        widgets = {
            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Коротко опишіть проблему",
                    "maxlength": 255,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Детально опишіть запит або проблему",
                }
            ),
            "page_context": forms.HiddenInput(),
        }
        labels = {
            "subject": "Тема",
            "description": "Опис",
        }


