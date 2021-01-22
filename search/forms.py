from django.forms import ModelForm
from .models import Field

class FieldForm(ModelForm):

    class Meta:
        model = Field
        fields = ['field_id', 'search_id']