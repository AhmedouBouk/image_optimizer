from django.db import models
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit, Transpose, ResizeToFill, SmartResize
from django.utils.text import slugify
from PIL import Image
import os

# Create your models here.

class CompressionStrategy(models.Model):
    COMPRESSION_ALGORITHMS = [
        ('intelligent', 'Compression Intelligente'),
        ('lossy', 'Compression avec Perte Optimisée'),
        ('lossless', 'Compression sans Perte'),
        ('adaptive', 'Compression Adaptative'),
    ]

    OUTPUT_FORMATS = [
        ('WEBP', 'WebP (Recommandé)'),
        ('JPEG', 'JPEG'),
        ('PNG', 'PNG'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    algorithm = models.CharField(
        max_length=20,
        choices=COMPRESSION_ALGORITHMS,
        default='intelligent'
    )
    output_format = models.CharField(
        max_length=10,
        choices=OUTPUT_FORMATS,
        default='WEBP'
    )
    quality_factor = models.IntegerField(
        default=85,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Facteur de qualité (1-100)"
    )
    max_dimensions = models.IntegerField(
        default=2000,
        validators=[MinValueValidator(100), MaxValueValidator(8000)],
        help_text="Dimension maximale en pixels"
    )
    preserve_metadata = models.BooleanField(
        default=False,
        help_text="Conserver les métadonnées importantes"
    )
    progressive_loading = models.BooleanField(
        default=True,
        help_text="Activer le chargement progressif"
    )
    auto_optimize = models.BooleanField(
        default=True,
        help_text="Optimisation automatique basée sur le contenu"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def get_processors(self):
        processors = []
        
        # Toujours commencer par Transpose pour corriger l'orientation
        processors.append(Transpose())
        
        # Ajouter le redimensionnement approprié selon la stratégie
        if self.algorithm == 'intelligent':
            processors.append(SmartResize(self.max_dimensions, self.max_dimensions))
        elif self.algorithm in ['lossy', 'adaptive']:
            processors.append(ResizeToFit(self.max_dimensions, self.max_dimensions))
        else:  # lossless
            processors.append(ResizeToFill(self.max_dimensions, self.max_dimensions))
        
        return processors

    def get_format_options(self):
        options = {
            'quality': self.quality_factor,
            'optimize': True
        }
        
        if self.output_format == 'WEBP':
            options.update({
                'method': 6,  # Meilleure compression
                'lossless': self.algorithm == 'lossless',
                'quality': self.quality_factor,
                'progressive': self.progressive_loading
            })
        elif self.output_format == 'JPEG':
            options.update({
                'progressive': self.progressive_loading,
                'optimize': True,
                'quality': self.quality_factor
            })
        elif self.output_format == 'PNG':
            options.update({
                'optimize': True,
                'compress_level': 9  # Maximum compression
            })
            
        return options

    def __str__(self):
        return f"{self.name} ({self.get_algorithm_display()})"

class OptimizedImage(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    
    original_image = ProcessedImageField(
        upload_to='original_images/%Y/%m/%d/',
        processors=[Transpose(), ResizeToFit(2048, 2048)],
        format='JPEG',
        options={'quality': 90},
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'heic', 'heif'])]
    )
    
    optimized_image = ProcessedImageField(
        upload_to='optimized_images/%Y/%m/%d/',
        processors=[],  # Will be set dynamically
        format='WEBP',  # Will be set dynamically
        options={},     # Will be set dynamically
        blank=True,
        null=True
    )
    
    compression_strategy = models.ForeignKey(
        CompressionStrategy,
        on_delete=models.SET_NULL,
        null=True
    )
    
    original_size = models.IntegerField(default=0)
    compressed_size = models.IntegerField(default=0)
    compression_ratio = models.FloatField(default=0)
    image_dimensions = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_image_url(self):
        """Retourne l'URL de l'image optimisée si elle existe, sinon l'originale"""
        if self.optimized_image:
            return self.optimized_image.url
        return self.original_image.url

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            
        if self.original_image:
            # Enregistrer la taille originale
            self.original_size = self.original_image.size
            
            # Appliquer la stratégie de compression
            if self.compression_strategy:
                self.optimized_image.processors = self.compression_strategy.get_processors()
                self.optimized_image.format = self.compression_strategy.output_format
                self.optimized_image.options = self.compression_strategy.get_format_options()
            else:
                # Stratégie par défaut si aucune n'est spécifiée
                self.optimized_image.processors = [Transpose(), ResizeToFit(2000, 2000)]
                self.optimized_image.format = 'WEBP'
                self.optimized_image.options = {'quality': 85, 'method': 6}
            
            # Obtenir les dimensions de l'image
            with Image.open(self.original_image) as img:
                self.image_dimensions = f"{img.width}x{img.height}"
        
        if hasattr(self, 'optimized_image') and self.optimized_image:
            self.compressed_size = self.optimized_image.size
            if self.original_size > 0:
                self.compression_ratio = (self.original_size - self.compressed_size) / self.original_size * 100
                
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title

class PerformanceMetric(models.Model):
    image = models.ForeignKey(OptimizedImage, on_delete=models.CASCADE)
    load_time_original = models.FloatField()
    load_time_optimized = models.FloatField()
    bandwidth_saved = models.IntegerField()
    measured_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Metrics for {self.image.title}"
