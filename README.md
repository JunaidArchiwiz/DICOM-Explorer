# DICOM Viewer and De-Identification Tool

## Overview

This project is a **Streamlit-based application** designed for visualizing and de-identifying **DICOM** (Digital Imaging and Communications in Medicine) files. It allows users to navigate through DICOM series, view individual slices interactively, and ensure patient privacy by removing sensitive metadata.

## Features

- **Interactive DICOM Viewer**:
  - Navigate through slices of a DICOM series.
  - View DICOM images with interactive zoom, pan, and annotation tools powered by Plotly.

- **De-identification of DICOM Data**:
  - Remove sensitive metadata to ensure patient privacy.
  - Visualize and compare raw and de-identified metadata.

- **Mobile-Optimized UI**:
  - Adaptive layout for better usability on mobile devices.

- **3D Visualization Support**:
  - Launch a Dash-based 3D visualization app directly from the Streamlit interface.

## Technologies Used

- **Python Libraries**:
  - `os`: For file and directory operations.
  - `pandas`: For handling and displaying metadata in tabular form.
  - `streamlit`: For building the web-based interface.
  - `SimpleITK`: For handling DICOM series and de-identification.
  - `plotly.graph_objects`: For creating interactive plots.
  - `webbrowser`: For opening external applications (e.g., Dash app).

- **DICOM Handling**:
  - `SimpleITK.ImageSeriesReader` for reading and processing DICOM series.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ## Installation

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows, use `venv\\Scripts\\activate`
  



