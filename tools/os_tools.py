"""
This module provides tools for interacting with operating system services.
"""
import time 

def get_current_time() -> str:
    """Returns the current time in a string of the following form: 'Sun Jun 20 23:21:05 1993'"""

    return time.asctime()

__all__ = ['get_current_time']