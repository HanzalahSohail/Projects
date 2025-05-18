# Color-Aware Tomato Leaf Disease Classification

<pre>
. 
├── Models/                     # Saved models and weights 
│ ├── baseline_model.pth
│ ├── improvement_1_model.pth
│ └── improvement_2_model.pth
├── Notebooks/                  # Jupyter notebooks for experiments 
│ ├── Baseline.ipynb            # TwoBranchInceptionV3 using Lab channels 
│ ├── Improvement-1a.ipynb      # EfficientNet-B0 with 6-channel RGB-Lab input
│ ├── Improvement-1b.ipynb      # 1a + advanced image augmentations
│ └── improvement_2.ipynb       # 1b + CBAM attention modules and residual blocks 
└── README.md 
</pre>


##  Tomato Leaf Disease Classification using Deep Learning
A deep learning pipeline for real-world tomato leaf disease detection, incorporating color space fusion, attention mechanisms, and robust augmentation. Trained and evaluated on the challenging PlantDoc dataset.

### Problem Overview
Tomatoes are a vital crop, yet extremely vulnerable to leaf diseases. Early diagnosis is critical for minimizing agricultural losses—especially in countries like Pakistan, where agriculture is the economic backbone.

Many prior works use the idealized PlantVillage dataset, which lacks real-world complexity. Our approach instead leverages the PlantDoc dataset—rich with noisy backgrounds, varied lighting, and multiple leaves per image—to develop more generalizable models for disease classification.
##  Key Contributions

|  Component        | Description                                                                 |
|--------------------|--------------------------------------------------------------------------------|
|  **Baseline**     | Dual-branch InceptionV3 leveraging Lab color space (luminance vs. chrominance) |
|  **Improvement 1A** | EfficientNet-B0 backbone with 6-channel RGB+Lab input                          |
|  **Improvement 1B** | Strong augmentations for RGB (e.g. perspective, jitter, blur)                 |
|  **Improvement 2**  | CBAM attention + custom residual block for focused learning                   |

  **Best model accuracy** on PlantDoc Tomato subset: **55.63%**, up from **33.11%** baseline.

---

##  Methodology Summary

###  Baseline – TwoBranchInceptionV3

Inspired by the _ColorAware Inception_ model, we separate the **L** (lightness) and **AB** (color) channels from Lab space into parallel CNN streams before fusion and InceptionV3-based classification.

###  Improvement 1A – EfficientNet with RGB+Lab

We combine raw RGB and Lab features (6 total channels) and modify the first convolutional layer of **EfficientNet-B0** to accept this input. The model is initialized with **ImageNet1K** pretrained weights.

###  Improvement 1B – Advanced Augmentations

To improve generalization on real-world backgrounds, we apply aggressive augmentations (e.g., flips, color jitter, affine/perspective transforms) to RGB images while keeping Lab inputs spatially aligned.

###  Improvement 2 – CBAM + Residual Learning

We introduce **Convolutional Block Attention Modules (CBAM)** to help the model attend to disease-relevant regions. A lightweight residual block is added for better feature refinement.

---

##  Results Summary

| Model              | Architecture                      | Accuracy (%) |
|--------------------|-----------------------------------|--------------|
| Baseline           | TwoBranchInceptionV3 (Lab)        | 33.11        |
| Improvement 1A     | EfficientNet-B0 (RGB+Lab)         | 46.67        |
| Improvement 1B     | 1A + Advanced Augmentations       | 51.64        |
| Improvement 2      | 1B + CBAM + Residual Block        | **55.63**    |

Additional insights include:

- **Class-wise F1 Scores**
- **Failure case visualizations**
- **Impact of augmentations**



Note: </br>
Detailed information of each model is given in the markdown of the relevant notebook