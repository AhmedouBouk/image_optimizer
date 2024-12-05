from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.db.models import Avg, Sum, Count
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from .models import OptimizedImage, CompressionStrategy, PerformanceMetric
import time
import json
from PIL import Image
import io
import os
from PIL import ImageFilter
from django.conf import settings
from django.utils import timezone
import uuid

class ImageListView(ListView):
    model = OptimizedImage
    template_name = 'optimizer/image_list.html'
    context_object_name = 'images'
    ordering = ['-created_at']
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer les statistiques globales depuis le cache ou les calculer
        stats = cache.get('optimization_stats')
        if not stats:
            stats = self.calculate_global_stats()
            cache.set('optimization_stats', stats, 300)  # Cache pour 5 minutes
            
        context.update(stats)
        return context
    
    def calculate_global_stats(self):
        total_images = OptimizedImage.objects.count()
        if total_images == 0:
            return {
                'total_images': 0,
                'total_saved': 0,
                'avg_compression': 0,
                'best_compression': None
            }
            
        stats = OptimizedImage.objects.aggregate(
            total_saved=Sum('original_size') - Sum('compressed_size'),
            avg_compression=Avg('compression_ratio')
        )
        
        # Trouver l'image avec la meilleure compression
        best_compression = OptimizedImage.objects.order_by('-compression_ratio').first()
        
        return {
            'total_images': total_images,
            'total_saved': stats['total_saved'],
            'avg_compression': stats['avg_compression'],
            'best_compression': best_compression
        }

class ImageDetailView(DetailView):
    model = OptimizedImage
    template_name = 'optimizer/image_detail.html'
    context_object_name = 'image'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer les métriques de performance
        try:
            context['metrics'] = PerformanceMetric.objects.filter(
                image=self.object
            ).latest('measured_at')
        except PerformanceMetric.DoesNotExist:
            context['metrics'] = None
            
        # Ajouter l'historique des compressions si disponible
        context['compression_history'] = PerformanceMetric.objects.filter(
            image=self.object
        ).order_by('-measured_at')[:5]
        
        # Ajouter des statistiques comparatives
        avg_stats = OptimizedImage.objects.aggregate(
            avg_compression=Avg('compression_ratio'),
            avg_load_time=Avg('performancemetric__load_time_optimized')
        )
        context['comparative_stats'] = {
            'avg_compression': avg_stats['avg_compression'],
            'avg_load_time': avg_stats['avg_load_time']
        }
        
        return context

class ImageUploadView(CreateView):
    model = OptimizedImage
    template_name = 'optimizer/image_upload.html'
    fields = ['title', 'description', 'original_image', 'compression_strategy']
    success_url = reverse_lazy('image-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['compression_strategies'] = CompressionStrategy.objects.all()
        return context

    def form_valid(self, form):
        try:
            # Sauvegarder d'abord l'image originale
            self.object = form.save(commit=False)
            
            # Mesurer le temps de chargement original
            start_time = time.time()
            
            # Si aucune stratégie n'est sélectionnée, utiliser la stratégie par défaut
            if not self.object.compression_strategy:
                default_strategy = CompressionStrategy.objects.filter(name='Compression Intelligente WebP').first()
                if not default_strategy:
                    default_strategy = CompressionStrategy.objects.create(
                        name='Compression Intelligente WebP',
                        description='Stratégie de compression par défaut',
                        algorithm='intelligent',
                        output_format='WEBP',
                        quality_factor=85,
                        max_dimensions=2000,
                        progressive_loading=True,
                        auto_optimize=True
                    )
                self.object.compression_strategy = default_strategy
            
            # Sauvegarder pour obtenir l'image originale sur le disque
            self.object.save()
            
            if not self.object.original_image:
                raise ValueError("Aucune image n'a été téléchargée")
            
            # S'assurer que le fichier original existe
            if not os.path.exists(self.object.original_image.path):
                raise ValueError("Le fichier original n'existe pas")
            
            # Créer le répertoire de destination
            today = timezone.now()
            upload_path = f'optimized_images/{today.year}/{today.month:02d}/{today.day:02d}'
            full_upload_path = os.path.join(settings.MEDIA_ROOT, upload_path)
            os.makedirs(full_upload_path, exist_ok=True)
            
            # Générer un nom de fichier unique
            filename = f"{uuid.uuid4().hex}.webp"
            dest_path = os.path.join(upload_path, filename)
            full_dest_path = os.path.join(settings.MEDIA_ROOT, dest_path)
            
            # Ouvrir et optimiser l'image
            with Image.open(self.object.original_image.path) as img:
                # Appliquer les transformations selon la stratégie
                if self.object.compression_strategy.algorithm == 'intelligent':
                    is_photo = self.is_photographic_content(img)
                    has_text = self.has_text_content(img)
                    
                    if has_text:
                        quality = max(85, self.object.compression_strategy.quality_factor)
                    elif is_photo:
                        quality = self.object.compression_strategy.quality_factor
                    else:
                        quality = min(75, self.object.compression_strategy.quality_factor)
                else:
                    quality = self.object.compression_strategy.quality_factor
                
                # Redimensionner si nécessaire
                max_dim = self.object.compression_strategy.max_dimensions
                if img.width > max_dim or img.height > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                
                # Convertir en RGB si nécessaire
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Sauvegarder l'image optimisée
                img.save(
                    full_dest_path,
                    'WEBP',
                    quality=quality,
                    method=6,  # Meilleure compression
                    lossless=self.object.compression_strategy.algorithm == 'lossless'
                )
            
            # Assigner le chemin à l'image optimisée
            self.object.optimized_image = dest_path
            self.object.save()
            
            # Mesurer le temps de chargement optimisé
            load_time_optimized = time.time() - start_time
            
            # Créer les métriques de performance
            PerformanceMetric.objects.create(
                image=self.object,
                load_time_original=start_time,
                load_time_optimized=load_time_optimized,
                bandwidth_saved=self.object.original_size - self.object.compressed_size
            )
            
            # Invalider le cache des statistiques
            cache.delete('optimization_stats')
            
            messages.success(
                self.request,
                f'Image optimisée avec succès ! Réduction de taille : {self.object.compression_ratio:.1f}%'
            )
            return HttpResponseRedirect(self.get_success_url())
            
        except Exception as e:
            messages.error(
                self.request,
                f'Erreur lors de l\'optimisation de l\'image : {str(e)}'
            )
            # En cas d'erreur, supprimer les fichiers partiellement créés
            if hasattr(self, 'object') and self.object.pk:
                if self.object.original_image:
                    try:
                        if os.path.exists(self.object.original_image.path):
                            os.remove(self.object.original_image.path)
                    except Exception:
                        pass
                self.object.delete()
            return self.form_invalid(form)

    def auto_optimize_image(self, image):
        """Optimise automatiquement l'image en fonction de son contenu"""
        with Image.open(image.original_image.path) as img:
            # Analyser le type d'image
            is_photo = self.is_photographic_content(img)
            has_text = self.has_text_content(img)
            
            strategy = image.compression_strategy
            
            # Ajuster les paramètres en fonction du contenu
            if is_photo:
                if strategy.algorithm == 'intelligent':
                    strategy.quality_factor = max(75, strategy.quality_factor)
            elif has_text:
                strategy.quality_factor = max(85, strategy.quality_factor)
                if strategy.output_format == 'WEBP':
                    strategy.quality_factor = max(90, strategy.quality_factor)
            
            strategy.save()
    
    def is_photographic_content(self, img):
        """Détecte si l'image est une photo"""
        # Convertir en niveaux de gris
        gray = img.convert('L')
        # Calculer l'histogramme
        hist = gray.histogram()
        # Calculer la variance
        mean = sum(i * h for i, h in enumerate(hist)) / sum(hist)
        variance = sum(((i - mean) ** 2) * h for i, h in enumerate(hist)) / sum(hist)
        # Une variance élevée indique généralement une photo
        return variance > 1000
    
    def has_text_content(self, img):
        """Détecte la présence probable de texte dans l'image"""
        # Convertir en niveaux de gris
        gray = img.convert('L')
        # Appliquer un seuil pour détecter les bords
        edges = gray.filter(ImageFilter.FIND_EDGES)
        # Calculer le nombre de pixels de bord
        edge_pixels = sum(1 for pixel in edges.getdata() if pixel > 128)
        # Un grand nombre de bords peut indiquer la présence de texte
        return edge_pixels > (img.width * img.height * 0.1)

@require_http_methods(['GET'])
def get_optimization_stats(request):
    """API endpoint pour obtenir les statistiques d'optimisation"""
    stats = cache.get('optimization_stats')
    if not stats:
        total_images = OptimizedImage.objects.count()
        stats = OptimizedImage.objects.aggregate(
            total_saved=Sum('original_size') - Sum('compressed_size'),
            avg_compression=Avg('compression_ratio')
        )
        stats['total_images'] = total_images
        cache.set('optimization_stats', stats, 300)
    
    return JsonResponse({
        'total_images': stats['total_images'],
        'total_bandwidth_saved': stats['total_saved'],
        'average_compression_ratio': round(stats['avg_compression'], 2) if stats['avg_compression'] else 0
    })

@require_http_methods(['POST'])
def measure_load_time(request):
    """API endpoint pour mesurer le temps de chargement des images"""
    data = json.loads(request.body)
    image_id = data.get('image_id')
    load_time = data.get('load_time')
    
    image = get_object_or_404(OptimizedImage, id=image_id)
    
    metric = PerformanceMetric.objects.create(
        image=image,
        load_time_original=0,  # Déjà mesuré lors du upload
        load_time_optimized=load_time,
        bandwidth_saved=image.original_size - image.compressed_size
    )
    
    return JsonResponse({
        'status': 'success',
        'compression_ratio': image.compression_ratio,
        'bandwidth_saved': metric.bandwidth_saved
    })
