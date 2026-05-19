# RefConSite3D Utils

Python GUI utilities for preprocessing, visualization, and quality control of the RefConSite3D dataset.

The repository provides standalone tools for:

- Semantic target extraction label processing and visualization
- K-nearest-neighbor-based extraction of target objects from scene point clouds
- Visualization of object verification labels for BIM-to-scan-based construction progress monitoring

The scripts are designed to work directly with the RefConSite3D dataset structure and automatically locate related files such as annotations, planning models, and synthetic point clouds.

All generated outputs are written to the local `outputs/` directory.

The original dataset files are never modified.

## Dataset

The RefConSite3D dataset is publicly available on Zenodo:

https://doi.org/10.5281/zenodo.20285732

## Repository Structure

```text
RefConSite3D-utils/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── scripts/
│   ├── ply_semantic_segmentation_class_splitter_and_colorizer_gui.py
│   ├── ply_object_knn_extractor_gui.py
│   └── ply_object_verification_class_colorizer_gui.py
└── outputs/
    └── .gitkeep
```

## Installation

The utility scripts are intended to be copied into the `utils/` directory of the RefConSite3D dataset.

### 1. Download the Dataset

Download and extract the dataset from Zenodo:

https://doi.org/10.5281/zenodo.20285732

### 2. Clone the Repository

```bash
git clone https://github.com/luca-fahrendholz-heiermann/RefConSite3D-utils.git
```

### 3. Copy the Scripts into the Dataset

Copy the contents of the `scripts/` directory into:

```text
dataset/utils/
```

After copying, the dataset structure should look like:

```text
dataset/
├── utils/
│   ├── ply_semantic_segmentation_class_splitter_and_colorizer_gui.py
│   ├── ply_object_knn_extractor_gui.py
│   ├── ply_object_verification_class_colorizer_gui.py
│   └── outputs/
```

### 4. Install the Required Python Packages

Run the following command from the repository root or from the dataset root:

```bash
pip install -r requirements.txt
```

### 5. Run the Scripts from `dataset/utils/`

```bash
cd dataset/utils
python ply_semantic_segmentation_class_splitter_and_colorizer_gui.py
```

## Requirements

The utility scripts were tested with Python 3.10 or newer.

Main dependencies:

- numpy
- open3d
- plyfile
- tkinterdnd2

## Processing Workflow and Utility Scripts

The RefConSite3D benchmark consists of two sequential tasks:

1. Target Extraction
2. Progress Monitoring via Object Verification

The utility scripts provided in this repository support visualization and validation of the corresponding annotations and intermediate results.

```text
Full Scene Point Cloud
        ↓
Semantic Target Extraction
        ↓
Target Point Cloud
        ↓
Registration with Planning Model
        ↓
Component-Level Verification
        ↓
Construction Progress Assessment
```

### 1. Semantic Segmentation Class Splitter and Colorizer

**Script:** `ply_semantic_segmentation_class_splitter_and_colorizer_gui.py`

This script processes semantic segmentation annotations for the target extraction benchmark.

#### Inputs

- Full scene point cloud (`.ply`)
- Semantic label file (`.txt`)

#### Label Definition

- `environment`
- `ground`
- `target`

#### Outputs

- `*_environment.ply`
- `*_ground.ply`
- `*_target.ply`
- `*_colored_class.ply`

#### Purpose

The script is used to:

- Validate semantic annotations
- Visualize class labels
- Extract the target point cloud for downstream processing

### 2. KNN Object Extractor

**Script:** `ply_object_knn_extractor_gui.py`

This script extracts scan points corresponding to a selected reference object using a K-nearest-neighbor search.

#### Inputs

- Source scene point cloud
- Reference object point cloud

#### Outputs

- Extracted object point cloud

#### Purpose

The script is used to:

- Isolate object-specific scan data
- Generate object-level subsets
- Prepare data for object verification

### 3. Object Verification Class Colorizer

**Script:** `ply_object_verification_class_colorizer_gui.py`

This script visualizes object verification labels and creates colorized planning models and synthetic point clouds. fileciteturn8file1L1-L120

#### Inputs

- Scene point cloud (`.ply`)
- Object verification labels (`.json`)
- Component OBJ models

#### Label Definition

- `0`: Object not verified (red)
- `1`: Object verified (green)

#### Outputs

- Colorized merged OBJ model
- Material file (`.mtl`)
- Colorized sampled PLY point cloud

#### Purpose

The script is used to:

- Validate object verification annotations
- Visualize component installation states
- Inspect construction progress monitoring results

## Usage

Run a script from the repository root:

```bash
python scripts/ply_semantic_segmentation_class_splitter_and_colorizer_gui.py
python scripts/ply_object_knn_extractor_gui.py
python scripts/ply_object_verification_class_colorizer_gui.py
```

Each script launches a standalone graphical user interface.

## Output Directory

All generated files are written to:

```text
outputs/
```

The original dataset files are never overwritten.

## Important Dataset Structure Requirement

The original RefConSite3D folder structure and file names should not be modified.

Several utility scripts automatically derive the locations of:

- Annotation files
- Planning models
- Synthetic point clouds
- Scene identifiers

Renaming or moving files may therefore prevent the scripts from functioning correctly.

## License

The source code in this repository is distributed under the MIT License.

## Citation

If you use the RefConSite3D dataset, please cite:

```text
Fahrendholz-Heiermann, J. L., Wu, C. H., & Brell-Cokcan, S. (2026). RefConSite3D: A Multi-Phase and Multi-Scenario Dataset from the Reference Construction Site Aachen for Target Extraction, BIM-to-Scan Verification, and Circular Construction Monitoring (Version 1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.20285732
```

## Acknowledgements

The RefConSite3D dataset was created within the TARGET-X project and further processed within the framework of the Cluster of Excellence CARE.

