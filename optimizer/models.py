from django.db import models
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit, Transpose, ResizeToFill, SmartResize
from django.utils.text import slugify
from PIL import Image
import os
import io
from django.core.files.base import ContentFile
import uuid

# Create your models here.

class CompressionStrategy(models.Model):
    COMPRESSION_ALGORITHMS = [
        ('intelligent', 'Compression Intelligente'),
        ('lossy', 'Compression avec Perte Optimisée'),
        ('lossless', 'Compression sans Perte'),
        ('adaptive', 'Compression Adaptative'),
        ('content_aware', 'Compression Adaptée au Contenu'),
    ]

    OUTPUT_FORMATS = [
        ('WEBP', 'WebP (Recommandé)'),
        ('AVIF', 'AVIF (Nouvelle Génération)'),
        ('JPEG', 'JPEG'),
        ('PNG', 'PNG'),
    ]

    RESIZE_STRATEGIES = [
        ('fit', 'Ajuster aux Dimensions'),
        ('fill', 'Remplir les Dimensions'),
        ('smart', 'Redimensionnement Intelligent'),
        ('content_aware', 'Redimensionnement Adapté au Contenu'),
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
    resize_strategy = models.CharField(
        max_length=20,
        choices=RESIZE_STRATEGIES,
        default='smart'
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
    generate_responsive = models.BooleanField(
        default=True,
        help_text="Générer des versions responsives"
    )
    responsive_sizes = models.CharField(
        max_length=200,
        default="320,768,1024,1920",
        help_text="Tailles en pixels pour les images responsives (séparées par des virgules)"
    )
    enable_lazy_loading = models.BooleanField(
        default=True,
        help_text="Activer le chargement différé"
    )
    cache_control = models.CharField(
        max_length=100,
        default="public, max-age=31536000",
        help_text="Directives de mise en cache du navigateur"
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
        elif self.algorithm == 'content_aware':
            processors.append(ResizeToFill(self.max_dimensions, self.max_dimensions))
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
        elif self.output_format == 'AVIF':
            options.update({
                'quality': self.quality_factor,
                'optimize': True,
                'lossless': self.algorithm == 'lossless',
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

    def get_responsive_sizes(self):
        """Return responsive sizes as a list of integers"""
        if not self.responsive_sizes:
            return []
        return [int(size.strip()) for size in self.responsive_sizes.split(',') if size.strip()]

    def __str__(self):
        return f"{self.name} ({self.get_algorithm_display()})"

class OptimizedImage(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
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
            # Generate slug from title
            base_slug = slugify(self.title)
            unique_slug = base_slug
            counter = 1
            # Ensure unique slug
            while OptimizedImage.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug

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
    
    # Temps de chargement
    load_time_original = models.FloatField(
        help_text="Temps de chargement de l'image originale (en secondes)"
    )
    load_time_optimized = models.FloatField(
        help_text="Temps de chargement de l'image optimisée (en secondes)"
    )
    
    # Métriques de taille et bande passante
    bandwidth_saved = models.IntegerField(
        help_text="Bande passante économisée (en bytes)"
    )
    size_reduction_percentage = models.FloatField(
        default=0,
        help_text="Pourcentage de réduction de la taille"
    )
    
    # Métriques de qualité
    ssim_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Score SSIM (Structural Similarity Index)"
    )
    psnr_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Peak Signal-to-Noise Ratio"
    )
    
    # Métriques de performance web
    first_byte_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Time to First Byte (TTFB) en secondes"
    )
    dom_interactive_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Temps jusqu'à DOM Interactive (en secondes)"
    )
    
    # Métriques utilisateur
    perceived_loading_speed = models.FloatField(
        null=True,
        blank=True,
        help_text="Vitesse de chargement perçue (score de 1 à 10)"
    )
    
    # Métriques de cache
    cache_hit_rate = models.FloatField(
        default=0,
        help_text="Taux de succès du cache (%)"
    )
    
    measured_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Metrics for {self.image.title} at {self.measured_at}"
    
    class Meta:
        ordering = ['-measured_at']
        verbose_name = "Métrique de Performance"
        verbose_name_plural = "Métriques de Performance"
