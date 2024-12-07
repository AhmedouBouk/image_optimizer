from django.core.management.base import BaseCommand
from optimizer.models import CompressionStrategy

class Command(BaseCommand):
    help = 'Populate default compression strategies'

    def handle(self, *args, **kwargs):
        strategies = [
            {
                'name': 'Compression Intelligente WebP',
                'description': 'Optimisation automatique basée sur le contenu avec WebP',
                'algorithm': 'intelligent',
                'output_format': 'WEBP',
                'resize_strategy': 'smart',
                'quality_factor': 85,
                'max_dimensions': 2000,
                'progressive_loading': True,
                'auto_optimize': True,
                'generate_responsive': True,
            },
            {
                'name': 'Haute Qualité JPEG',
                'description': 'Compression JPEG optimisée pour la qualité',
                'algorithm': 'lossy',
                'output_format': 'JPEG',
                'resize_strategy': 'fit',
                'quality_factor': 90,
                'max_dimensions': 2048,
                'progressive_loading': True,
                'auto_optimize': False,
                'generate_responsive': True,
            },
            {
                'name': 'PNG Sans Perte',
                'description': 'Compression sans perte pour les images avec transparence',
                'algorithm': 'lossless',
                'output_format': 'PNG',
                'resize_strategy': 'fit',
                'quality_factor': 100,
                'max_dimensions': 2048,
                'progressive_loading': False,
                'auto_optimize': False,
                'generate_responsive': False,
            },
            {
                'name': 'AVIF Nouvelle Génération',
                'description': 'Format moderne avec compression avancée',
                'algorithm': 'adaptive',
                'output_format': 'AVIF',
                'resize_strategy': 'smart',
                'quality_factor': 80,
                'max_dimensions': 2000,
                'progressive_loading': True,
                'auto_optimize': True,
                'generate_responsive': True,
            },
            {
                'name': 'Optimisation Contenu',
                'description': 'Adapte la compression selon le type de contenu',
                'algorithm': 'content_aware',
                'output_format': 'WEBP',
                'resize_strategy': 'content_aware',
                'quality_factor': 85,
                'max_dimensions': 2000,
                'progressive_loading': True,
                'auto_optimize': True,
                'generate_responsive': True,
            }
        ]

        for strategy in strategies:
            CompressionStrategy.objects.get_or_create(
                name=strategy['name'],
                defaults=strategy
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created strategy "{strategy["name"]}"')
            )
