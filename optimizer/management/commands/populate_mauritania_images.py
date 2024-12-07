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

class ImageProcessor:
    def __init__(self, max_size: int = 800, quality: int = 85):
        self.max_size = max_size
        self.quality = quality
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'image/webp,image/jpeg'
        }

    def download_image(self, url: str, timeout: int = 5) -> Optional[bytes]:
        """Download image from URL with timeout."""
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=timeout,
                stream=True
            )
            response.raise_for_status()
            return response.content
        except RequestException as e:
            logger.error(f"Failed to download image from {url}: {str(e)}")
            return None

    def process_image(self, image_content: bytes) -> Optional[NamedTemporaryFile]:
        """Process image content and return a temporary file."""
        try:
            img_temp = NamedTemporaryFile(delete=True)
            img = Image.open(BytesIO(image_content))

            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Resize if too large
            if max(img.size) > self.max_size:
                img.thumbnail((self.max_size, self.max_size), Image.Resampling.LANCZOS)

            # Save optimized image
            img.save(img_temp, format='JPEG', quality=self.quality, optimize=True)
            img_temp.flush()
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
                url='https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Nouakchott_Fishing_Port.jpg/640px-Nouakchott_Fishing_Port.jpg',
                title='Port de Pêche de Nouakchott',
                description='Le port de pêche artisanale de Nouakchott'
            ),
            ImageData(
                url='https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Mauritania_4432_Nouadhibou_Harbour_Luca_Galuzzi_2006.jpg/640px-Mauritania_4432_Nouadhibou_Harbour_Luca_Galuzzi_2006.jpg',
                title='Port de Nouadhibou',
                description='Vue panoramique du port de Nouadhibou'
            ),
            ImageData(
                url='https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Nouadhibou_boats.jpg/640px-Nouadhibou_boats.jpg',
                title='Bateaux de Pêche',
                description='Bateaux de pêche traditionnels à Nouadhibou'
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

    def _save_image(self, image_data: ImageData, temp_file: NamedTemporaryFile, strategy: CompressionStrategy) -> bool:
        """Save image to database."""
        try:
            filename = f"{image_data.title.lower().replace(' ', '_')}.jpg"
            image = OptimizedImage(
                title=image_data.title,
                description=image_data.description,
                compression_strategy=strategy
            )
            image.original_image.save(filename, File(temp_file), save=True)
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
            image_content = self.image_processor.download_image(image_data.url)
            if not image_content:
                continue

            temp_file = self.image_processor.process_image(image_content)
            if not temp_file:
                continue

            if self._save_image(image_data, temp_file, strategy):
                success_count += 1

        # Final status report
        self.stdout.write(
            self.style.SUCCESS(
                f'Processing complete: {success_count}/{total_images} images successfully processed'
            )
        )