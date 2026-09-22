"""
Visualize the processed data:
- Show sample images
- Show label distribution
"""

import json
import random
from pathlib import Path
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np

DATA_DIR = Path("data/processed")
IMAGES_DIR = DATA_DIR / "images"
LABELS_FILE = DATA_DIR / "labels.json"


def load_labels():
    with open(LABELS_FILE, 'r') as f:
        return json.load(f)


def show_sample_images(labels, num_samples=8):
    """Display random sample images with their labels"""

    # Get random filenames
    filenames = list(labels.keys())
    random.shuffle(filenames)
    sample_filenames = filenames[:num_samples]

    # Create grid
    cols = 4
    rows = (num_samples + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(15, 4 * rows))
    axes = axes.flatten()

    for i, filename in enumerate(sample_filenames):
        # Load image
        img_path = IMAGES_DIR / filename
        img = Image.open(img_path)

        # Get labels
        label = labels[filename]
        title = f"File: {filename[:12]}..."

        # Add attribute info
        attr_info = []
        for attr in ["neckline type", "length", "silhouette", "waistline"]:
            if label.get(attr):
                short_attr = attr.replace(" type", "").replace("line", "")
                attr_info.append(f"{short_attr}: {label[attr][:15]}")

        title = "\n".join(attr_info[:3])

        # Display
        axes[i].imshow(img)
        axes[i].set_title(title, fontsize=8)
        axes[i].axis('off')

    # Hide extra axes
    for i in range(len(sample_filenames), len(axes)):
        axes[i].axis('off')

    plt.tight_layout()
    plt.savefig("output/sample_images.png", dpi=150, bbox_inches='tight')
    plt.show()
    print("✅ Sample images saved to: output/sample_images.png")


def show_label_distribution(labels):
    """Show how many images have each attribute"""

    attributes = ["neckline type", "length", "silhouette", "waistline"]

    counts = {}
    for attr in attributes:
        count = sum(1 for v in labels.values() if v.get(attr) is not None)
        counts[attr] = count

    # Create bar chart
    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12']
    bars = ax.bar(counts.keys(), counts.values(), color=colors)

    ax.set_ylabel('Number of Images')
    ax.set_title('Label Distribution in Dataset')

    # Add values on bars
    for bar, count in zip(bars, counts.values()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
                str(count), ha='center', va='bottom', fontsize=10)

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig("output/label_distribution.png", dpi=150, bbox_inches='tight')
    plt.show()
    print("✅ Label distribution saved to: output/label_distribution.png")


def main():
    print("=" * 60)
    print("DATA VISUALIZATION")
    print("=" * 60)

    # Load data
    labels = load_labels()
    print(f"📊 Total images: {len(labels)}")

    # Show samples
    print("\n🖼️ Showing sample images...")
    show_sample_images(labels)

    # Show distribution
    print("\n📊 Showing label distribution...")
    show_label_distribution(labels)


if __name__ == "__main__":
    main()