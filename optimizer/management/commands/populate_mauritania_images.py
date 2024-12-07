from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from optimizer.models import OptimizedImage, CompressionStrategy
import requests
from requests.exceptions import RequestException
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
from PIL import Image
import logging
from io import BytesIO
import os
from django.core.files.temp import NamedTemporaryFile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ImageData:
    url: str
    title: str
    description: str
    is_local: bool = False

class ImageProcessor:
    def __init__(self, max_size: int = 800, quality: int = 85):
        self.max_size = max_size
        self.quality = quality
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'image/webp,image/jpeg'
        }

    def get_image_content(self, image_data: ImageData, timeout: int = 5) -> Optional[bytes]:
        """Get image content from URL or local file."""
        if image_data.is_local:
            try:
                with open(image_data.url, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read local image {image_data.url}: {str(e)}")
                return None
        else:
            try:
                response = requests.get(
                    image_data.url,
                    headers=self.headers,
                    timeout=timeout,
                    stream=True
                )
                response.raise_for_status()
                return response.content
            except RequestException as e:
                logger.error(f"Failed to download image from {image_data.url}: {str(e)}")
                return None

    def process_image(self, image_content: bytes) -> Optional[NamedTemporaryFile]:
        """Process image content and return a temporary file."""
        try:
            img_temp = NamedTemporaryFile()
            img = Image.open(BytesIO(image_content))

            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Resize if too large
            if max(img.size) > self.max_size:
                img.thumbnail((self.max_size, self.max_size), Image.Resampling.LANCZOS)

            # Save optimized image
            img.save(img_temp, format='JPEG', quality=self.quality, optimize=True)
            img_temp.seek(0)
            return img_temp
        except Exception as e:
            logger.error(f"Failed to process image: {str(e)}")
            return None

class Command(BaseCommand):
    help = 'Populate database with Mauritanian ocean images'

    def __init__(self):
        super().__init__()
        self.image_processor = ImageProcessor()
        self.images = self._get_image_data()

    def _get_image_data(self) -> List[ImageData]:
        """Return list of image data."""
        return [
            ImageData(
                url='c:/Users/HP/OneDrive/Desktop/espirt/image_optimizer/media/sample_images/mauritania_landscape.jpg',
                title='Paysage de Mauritanie',
                description='Vue panoramique d\'un paysage mauritanien avec des chevaux sur une dune de sable au coucher du soleil',
                is_local=True
            )
        ]

    def _get_or_create_strategy(self) -> CompressionStrategy:
        """Get or create default compression strategy."""
        strategy, created = CompressionStrategy.objects.get_or_create(
            name="Compression Standard",
            defaults={
                'description': "Compression standard pour les images océaniques",
                'algorithm': 'intelligent',
                'output_format': 'WEBP',
                'quality_factor': 85
            }
        )
        if created:
            logger.info("Created new compression strategy")
        return strategy

    def _save_image(self, image_data: ImageData, strategy: CompressionStrategy) -> bool:
        """Save image to database."""
        try:
            filename = f"{image_data.title.lower().replace(' ', '_')}.jpg"
            image = OptimizedImage(
                title=image_data.title,
                description=image_data.description,
                compression_strategy=strategy
            )
            
            # Open and process the image
            with open(image_data.url, 'rb') as f:
                image.original_image.save(filename, File(f), save=True)
                
            logger.info(f'Successfully saved image: {image_data.title}')
            return True
        except Exception as e:
            logger.error(f'Failed to save image {image_data.title}: {str(e)}')
            return False

    def handle(self, *args, **options):
        """Main command handler."""
        strategy = self._get_or_create_strategy()
        success_count = 0
        total_images = len(self.images)

        for image_data in self.images:
            if self._save_image(image_data, strategy):
                success_count += 1

        # Final status report
        self.stdout.write(
            self.style.SUCCESS(
                f'Processing complete: {success_count}/{total_images} images successfully processed'
            )
        )