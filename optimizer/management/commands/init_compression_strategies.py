from django.core.management.base import BaseCommand
from optimizer.models import CompressionStrategy

class Command(BaseCommand):
    help = 'Initialize default compression strategies'

    def handle(self, *args, **options):
        strategies = [
            {
                'name': 'Compression Intelligente WebP',
                'description': 'Utilise l\'algorithme de compression intelligent avec WebP pour un excellent équilibre entre qualité et taille',
                'algorithm': 'intelligent',
                'output_format': 'WEBP',
                'quality_factor': 85,
                'max_dimensions': 2000,
                'progressive_loading': True,
                'auto_optimize': True
            },
            {
                'name': 'Haute Qualité Sans Perte',
                'description': 'Compression sans perte pour les images nécessitant une qualité maximale',
                'algorithm': 'lossless',
                'output_format': 'WEBP',
                'quality_factor': 100,
                'max_dimensions': 4000,
                'preserve_metadata': True,
                'progressive_loading': True,
                'auto_optimize': True
            },
            {
                'name': 'Compression Maximale',
                'description': 'Compression agressive pour une réduction maximale de la taille des fichiers',
                'algorithm': 'lossy',
                'output_format': 'WEBP',
                'quality_factor': 60,
                'max_dimensions': 1600,
                'progressive_loading': True,
                'auto_optimize': True
            },
            {
                'name': 'Compression Adaptative',
                'description': 'Ajuste automatiquement les paramètres de compression en fonction du contenu de l\'image',
                'algorithm': 'adaptive',
                'output_format': 'WEBP',
                'quality_factor': 75,
                'max_dimensions': 2000,
                'progressive_loading': True,
                'auto_optimize': True
            }
        ]

        for strategy in strategies:
            CompressionStrategy.objects.get_or_create(
                name=strategy['name'],
                defaults=strategy
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created compression strategy "{strategy["name"]}"')
            )
