# RefConSite3D Utils

Python GUI utilities for preprocessing, visualization, and quality control of the RefConSite3D dataset.

The repository provides standalone tools for:

- Semantic target extraction label processing and visualization
- K-nearest-neighbor-based extraction of target objects from scene point clouds
- Visualization of object verification labels for BIM-to-scan-based construction progress monitoring

The scripts are designed to work directly with the RefConSite3D dataset structure and automatically locate related files such as annotations, planning models, and synthetic point clouds.

All generated outputs are written to a local `outputs/` directory.

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
└── scripts/
    ├── ply_semantic_segmentation_class_splitter_and_colorizer_gui.py
    ├── ply_object_knn_extractor_gui.py
    └── ply_object_verification_class_colorizer_gui.py
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

### 4. Install the Required Python Packages

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

The utility scripts provided in this repository support visualization, preprocessing, and quality control of the corresponding annotations and intermediate results.

```text
Full Scene Point Cloud
        ↓
Semantic Segmentation Splitter
        ↓
Target Point Cloud
        ↓
Registration with Planning Model
        ↓
Component-Level Verification
        ↓
Construction Progress Assessment
```

### 1. `ply_semantic_segmentation_class_splitter_and_colorizer_gui.py`

This tool processes semantic segmentation annotations.

#### Inputs

- Full scene point cloud (`*_scene_*.ply`)
- Semantic label file (`*_semantic_segmentation_labels.txt`)

#### Functionality

- Splits the full scene point cloud into three separate point clouds:
  - `environment`
  - `ground`
  - `target`
- Creates a colorized point cloud for visual inspection.

#### Color Scheme

- Environment: red
- Ground: green
- Target: blue

#### Outputs

- `<scene>_environment.ply`
- `<scene>_ground.ply`
- `<scene>_target.ply`
- `<scene>_colored_class.ply`

#### Purpose

This script is used to:

- Validate semantic segmentation labels
- Visualize class assignments
- Generate target-only point clouds for subsequent registration

---

### 2. `ply_object_knn_extractor_gui.py`

This tool extracts candidate scan points corresponding to a selected reference object.

#### Inputs

- Scan point cloud (`.ply`)
- Reference object (`.obj` or `.ply`)

#### Functionality

- Samples points from OBJ meshes using Poisson-disk sampling.
- Performs a k-nearest-neighbor search in the scan point cloud.
- Extracts scan points located within a configurable distance threshold.

#### Parameters

- Number of sample points
- Number of nearest neighbors (`k`)
- Maximum distance threshold

#### Output

- `<object_name>_extracted_from_scan.ply`

#### Purpose

This script is intended for:

- Debugging object correspondences
- Generating approximate object-level scan subsets
- Preparing data for object verification

---

### 3. `ply_object_verification_class_colorizer_gui.py`

This tool visualizes object verification labels.

#### Inputs

- Scene point cloud (`*_scene_*.ply`)
- Object verification JSON file (`*_object_verification_labels.json`)
- Phase-specific component OBJ models

#### Functionality

- Loads all component labels from the annotation file.
- Assigns colors according to verification status.
- Merges all component meshes into a single colored OBJ model.
- Generates a sampled and colorized PLY representation.

#### Color Scheme

- Object not verified (`0`): red
- Object verified (`1`): green

#### Outputs

- `<scene>_object_verification_model_components_colored.obj`
- `<scene>_object_verification_model_components_colored.mtl`
- `<scene>_object_verification_model_components_colored.ply`

#### Purpose

This script is used to:

- Validate object verification annotations
- Visualize component installation states
- Inspect construction progress monitoring results

## Output Directory

All generated files are written to an automatically created:

```text
outputs/
```

Each script creates its own output subdirectory, typically named after the processed scene or input file.

The original dataset files are never overwritten.

## Important Dataset Structure Requirement

The utility scripts are designed to operate directly on the original RefConSite3D dataset structure.

After cloning this repository, copy the scripts into:

```text
dataset/utils/
```

The original dataset folder structure and file names should not be modified.

The scripts automatically infer the locations of related files, such as:

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

The ReStage demonstrator, including the planning models, construction activities, and data acquisition campaigns, was developed within the TARGET-X project. TARGET-X is funded by the Smart Networks and Services Joint Undertaking (SNS JU) under the European Union's Horizon Europe research and innovation programme (Grant Agreement No. 101096614).

The transformation of the acquired and simulated data into a structured benchmark dataset, including annotation generation, utility script development, and dataset documentation, was carried out within the framework of the Cluster of Excellence CARE. CARE – Climate-Neutral and Resource-Efficient Construction is funded by the Deutsche Forschungsgemeinschaft (DFG, German Research Foundation) under Germany's Excellence Strategy – EXC 3115 – 533767731.

