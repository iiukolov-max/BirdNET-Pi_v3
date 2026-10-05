# Model sources and attribution

V3 artifacts are pinned in `model/v3-manifest.json` to the [official Preview 3.1 record](https://zenodo.org/records/20703646). The model binary and label CSV are downloaded separately; they are not added by this integration to the code archive.

The pinned file hashes and sizes match the installed development artifacts. An earlier label audit found 11,560 unique scientific names with contiguous indices. The V3 loader checks for an output tensor matching the label count. A fresh download from the official server has not been repeated during these release checks; the web request to the record returned HTTP 429.

The source repository retains its existing [LICENSE](../LICENSE), credits and upstream README. Do not substitute the BirdNET-Analyzer code license for the BirdNET-Pi license.

V3 has separate [official terms of use](https://github.com/birdnet-team/birdnet-V3.0-dev/blob/main/TERMS_OF_USE.txt). They describe CC BY-SA 4.0 for these preview models, attribution/share-alike requirements, research/evaluation status and additional prohibited uses involving poaching or military purposes. Review the actual terms for the chosen artifact. These are different from the license stated for older BirdNET models; this file does not relicense any upstream material.

Attribution: Lasseck, M., Eibl, M., Klinck, H., & Kahl, S. (2026). *BirdNET+ V3.0 model developer preview (Preview 3.1).* Zenodo. [DOI: 10.5281/zenodo.20703646](https://doi.org/10.5281/zenodo.20703646).

The integration uses the unmodified pinned model and labels, with application changes for local inference, audio preprocessing, geographic filtering and web review/export. The [developer repository](https://github.com/birdnet-team/birdnet-V3.0-dev) documents the experimental model and its terms.
