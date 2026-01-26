<div align="center">

<img src="app/static/logo.svg" alt="Vitreous Logo" width="120">

# Vitreous
### Western Blot Quantification

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![YOLO](https://img.shields.io/badge/YOLO-v8-green.svg)](https://docs.ultralytics.com/)

*by Mansus*

</div>

---

## Overview

**Vitreous** is a web-based tool for automated western blot band detection and densitometry analysis. It uses machine learning to detect protein bands in blot images and calculates quantitative intensity metrics for each band.

The application provides researchers with precise measurements for comparative protein expression analysis, eliminating tedious manual band selection and intensity calculation.

## Key Features

- **Automated Band Detection**: ML-powered detection of protein bands using a fine-tuned YOLO model.
- **Row Grouping**: Automatic organization of detected bands into logical rows for multi-lane analysis.
- **Densitometry Metrics**:
    - **Integrated Density**: Total signal intensity per band.
    - **Background Correction**: Edge-based background subtraction for accurate quantification.
    - **Relative Intensity**: Normalized values for lane-to-lane comparison.
- **Interactive Visualization**: Real-time intensity profiles with adjustable detection thresholds.
- **Sample Gallery**: Built-in collection of western blot images for demonstration and testing.
- **CSV Export**: Export band measurements for downstream statistical analysis.

## Technical Stack

- **Backend**: Flask (Python) with REST API for detection and analysis.
- **Detection**: Ultralytics YOLO for band detection, NumPy for densitometry calculations.
- **Frontend**: Vanilla JavaScript (ES6+), Tailwind CSS with light/dark theme support.
- **Testing**: Pytest for core detection and densitometry services.

## Installation & Usage

### 1. Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Recommended for dependency management)

### 2. Setup
```bash
uv sync
```

### 3. Run Application
```bash
uv run python run.py
```
Then visit `http://localhost:5000` in your browser.

## Deployment with Docker

You can deploy **Vitreous** using Docker and Docker Compose. This ensures all system dependencies (YOLO, NumPy, etc.) are correctly configured.

### Using Docker Compose (Recommended)
1. **Build and Start**:
   ```bash
   docker compose up --build -d
   ```
2. **Access**: The application will be available at `http://localhost:5000`.

### Using Dockerfile Directly
1. **Build**:
   ```bash
   docker build -t vitreous .
   ```
2. **Run**:
   ```bash
   docker run -p 5000:5000 vitreous
   ```

### 4. Run Tests
```bash
PYTHONPATH=. uv run python3 -m pytest
```

## Methodology

The application follows a multi-stage processing pipeline:
1. **Detection**: YOLO-based object detection identifies protein bands in the blot image.
2. **Row Grouping**: Bands are clustered into rows based on Y-coordinate proximity.
3. **Densitometry**: For each band, intensity is calculated by inverting pixel values (dark bands = high signal) and computing integrated density with edge-based background correction.
4. **Normalization**: Relative intensities are computed by normalizing each band's value to the row maximum.

## License

This project is licensed under the GNU General Public License v3.0.
