# Installation Guide

## Requirements

- Python 3.8 or higher
- pip (Python package installer)

## Installing with pip

The recommended way to install Social Integrator is via pip:

```bash
pip install social-integrator
```

## Installing from source

To install from source:

```bash
git clone https://github.com/yourusername/social-integrator.git
cd social-integrator
pip install -e .
```

## Development Installation

For development, you'll want to install additional dependencies:

```bash
pip install -r requirements-dev.txt
```

## Platform-Specific Requirements

### Twitter

To use Twitter integration:

1. Create a Twitter Developer account
2. Create a Twitter App in the Developer Portal
3. Get your API keys (client ID and client secret)

## Verifying Installation

To verify your installation:

```python
from social_integrator import SocialIntegrator

integrator = SocialIntegrator()
print("Social Integrator installed successfully!")
```
