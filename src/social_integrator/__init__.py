"""Social media integration package."""

from social_integrator.core.platform import SocialPost, PlatformError, RateLimitError
from social_integrator.main import SocialIntegrator

__all__ = [
    'SocialIntegrator',
    'SocialPost',
    'PlatformError',
    'RateLimitError',
]

__version__ = '0.1.0'
