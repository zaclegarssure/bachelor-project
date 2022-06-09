## Flatpak attestation using Reproducible Builds
This repository contains the report for the semester project I did at EPFL,
where I measured and tried to improve build reproducibility for
[flatpaks](https://www.flatpak.org/), a cross-distribution packaging tool for
Linux.

## Installation

The report is written in $\LaTeX$ and uses `make`, `rubber-pipe`, and `biber`
to compile, in particular it will require the following Tex packages:
```
sudo pacman -S make texlive-core texlive-bibtexextra texlive-latexextra \
    texlive-langextra texlive-science texlive-bibtexextra biber rubber
```
Once done you can just run `make` to compile.

## Acknowledgment
The report is based on the template provided by
[HexHive](https://hexhive.epfl.ch/), available
[here](https://github.com/HexHive/thesis_template)
