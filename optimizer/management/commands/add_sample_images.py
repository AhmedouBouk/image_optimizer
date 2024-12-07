from django.core.management.base import BaseCommand
from django.core.files import File
from optimizer.models import OptimizedImage, CompressionStrategy
from PIL import Image
import os
from django.conf import settings
from io import BytesIO

class Command(BaseCommand):
    help = 'Add sample ocean images'

    def create_sample_image(self, width, height, color, filename):
        # Create a new image with a solid color
        image = Image.new('RGB', (width, height), color)
        
        # Save to BytesIO
        img_io = BytesIO()
        image.save(img_io, format='JPEG', quality=85)
        img_io.seek(0)
        
        return img_io, filename

    def handle(self, *args, **options):
        # Create or get compression strategy
        strategy, _ = CompressionStrategy.objects.get_or_create(
            name="Standard",
            defaults={
                'description': "Compression standard",
                'algorithm': 'intelligent',
                'output_format': 'WEBP',
                'quality_factor': 85
            }
        )

        # Sample image data
        images = [
            {
                'title': 'Ocean Bleu',
                'description': 'Vue de l\'océan atlantique mauritanien',
                'color': (0, 105, 148),  # Ocean blue
                'size': (800, 600)
            },
            {
                'title': 'Coucher de Soleil',
                'description': 'Coucher de soleil sur la côte',
                'color': (255, 164, 27),  # Sunset orange
                'size': (800, 600)
            },
            {
                'title': 'Plage Dorée',
                'description': 'Plage de sable doré',
                'color': (244, 215, 140),  # Sand color
                'size': (800, 600)
            }
        ]

        for img_data in images:
            try:
                # Generate sample image
                img_io, filename = self.create_sample_image(
                    img_data['size'][0],
                    img_data['size'][1],
                    img_data['color'],
                    f"{img_data['title'].lower().replace(' ', '_')}.jpg"
                )

                # Create OptimizedImage instance
                image = OptimizedImage(
                    title=img_data['title'],
                    description=img_data['description'],
                    compression_strategy=strategy
                )

                # Save the image
                image.original_image.save(
                    filename,
                    File(img_io),
                    save=True
                )

                self.stdout.write(
                    self.style.SUCCESS(f'Added sample image: {img_data["title"]}')
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating {img_data["title"]}: {str(e)}')
                )

        self.stdout.write(self.style.SUCCESS('Successfully added sample images'))
