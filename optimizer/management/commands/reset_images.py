from django.core.management.base import BaseCommand
from optimizer.models import OptimizedImage
import shutil
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Reset all images in the database and media directory'

    def handle(self, *args, **options):
        # Delete all image records from database
        OptimizedImage.objects.all().delete()

        # Clear media directories
        media_root = settings.MEDIA_ROOT
        for dir_name in ['original_images', 'optimized_images']:
            dir_path = os.path.join(media_root, dir_name)
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                os.makedirs(dir_path)

        self.stdout.write(self.style.SUCCESS('Successfully reset all images'))
