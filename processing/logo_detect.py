"""
Optional template for vision/logo detection.
Keep this out of MVP unless you already have a logo dataset.

How to use later:
- pip install ultralytics opencv-python
- Provide a trained model .pt and class map sponsor->class_id
- Add a task to run on thumbnails/frames and insert SponsorTag(source='vision')

This file is intentionally a template.
"""

def not_enabled():
    raise SystemExit("Logo detection not enabled in MVP. Start with text tagging + human QA.")

if __name__ == "__main__":
    not_enabled()
