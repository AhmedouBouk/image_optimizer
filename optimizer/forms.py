from django import forms
from .models import OptimizedImage, CompressionStrategy

class ImageUploadForm(forms.ModelForm):
    title = forms.CharField(
        label='Titre',
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'})
    )
    
    description = forms.CharField(
        label='Description',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'rows': 3
        })
    )
    
    compression_strategy = forms.ModelChoiceField(
        label='Stratégie de Compression',
        queryset=CompressionStrategy.objects.all(),
        required=False,
        empty_label='Compression Intelligente (Recommandé)',
        widget=forms.Select(attrs={'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'})
    )
    
    class Meta:
        model = OptimizedImage
        fields = ['title', 'description', 'original_image', 'compression_strategy']
        widgets = {
            'original_image': forms.FileInput(attrs={
                'class': 'hidden',
                'accept': 'image/*'
            })
        }
    
    def clean_original_image(self):
        image = self.cleaned_data.get('original_image')
        if image:
            # Vérifier la taille du fichier (10MB max)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError("La taille du fichier ne doit pas dépasser 10MB.")
            
            # Vérifier l'extension du fichier
            ext = image.name.split('.')[-1].lower()
            valid_extensions = ['jpg', 'jpeg', 'png', 'webp', 'heic', 'heif']
            if ext not in valid_extensions:
                raise forms.ValidationError(
                    f"Format de fichier non supporté. Formats acceptés: {', '.join(valid_extensions)}"
                )
        return image
