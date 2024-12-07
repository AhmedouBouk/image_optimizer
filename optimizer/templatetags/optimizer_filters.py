from django import template
from django.template.defaultfilters import filesizeformat
import os

register = template.Library()

@register.filter(name='divide')
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
        
@register.filter
def format_size(size):
    """Format size in bytes to human readable format"""
    try:
        size = float(size)
        if size < 1024:
            return f"{size:.1f} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size/(1024*1024):.1f} MB"
        else:
            return f"{size/(1024*1024*1024):.1f} GB"
    except (ValueError, TypeError):
        return "0 B"

@register.filter
def size_to_load_time(size):
    """Convert file size to estimated load time in seconds"""
    try:
        # Convert to float
        size = float(size) if size else 0
        
        # Convert bytes to megabytes
        size_mb = size / (1024 * 1024)
        
        # Estimate load time based on typical 4G speed (5 MB/s)
        # Add 100ms baseline latency
        load_time = (size_mb / 5.0) + 0.1
        
        # Ensure minimum time of 0.1s and maximum of 10s
        load_time = max(0.1, min(10, load_time))
        
        return round(load_time, 2)
    except (ValueError, TypeError):
        return 0.1
