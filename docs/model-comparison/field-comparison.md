# BirdNET v2.4 vs v3: paired field comparison on Raspberry Pi Zero 2 W

I ran two identical Raspberry Pi Zero 2 W devices with Sound Blaster G3 sound cards and identical microphones side by side at one location from 27 September to 2 October 2026. I manually reviewed a substantial subset of the saved detections using TP/FP marks. This post compares both raw outputs and the reviewed subset.

**The main finding is broader observed coverage with V3: 9,547 raw detections versus 2,825, and 57 bird species with at least one TP versus 44. V3 also produced more FP-only bird species.** The increased output should therefore be considered together with review results and the extra verification workload.

## Experimental setup and inclusion rules

- Hardware: two Raspberry Pi Zero 2 W devices, two Sound Blaster G3 sound cards and identical microphones at the same location.
- The devices started together. Export inclusion is 2026-09-27 12:38:04 through 2026-10-02 10:44:02 inclusive, in the timestamps as exported. The start boundary is the first V3 detection; V2.4 has no earlier detections on 27 September. The end is the latest V3 detection. Older V2.4 records and later records are excluded.
- Minimum confidence: 0.60 for both. Overlap: 0 for both. Sensitivity: **1.25 for V2.4 and 1.0 for V3**.
- The field export is identified as V3; its exact model filename/checksum was not included in the export. The model identity used in this deployment should be confirmed before treating these results as a benchmark of a specific preview build.
- `correct` means TP; `false_positive` means FP. Empty review marks are excluded from every TP/FP calculation and species classification.
- A **TP-confirmed species** has at least one reviewed TP for that model. An **FP-only species** has at least one reviewed FP and no reviewed TP for that model; remaining unreviewed records do not prove the entire species output is false.
- Species overlap is based on scientific names in these exports. No pair of renamed taxa requiring merging was identified in their confirmed lists. `Botaurus minutus` is retained as the V3 export label.
- TP/FP species overlap counts below include **birds only**. Non-bird V3 labels are reported separately. Raw detection totals include all labels.

## Raw detections and species overlap

| Metric | V2.4 | V3 | Shared | V2.4 only | V3 only |
| --- | --- | --- | --- | --- | --- |
| Raw detections, all taxa | 2825 | 9547 | — | — | — |
| TP-confirmed bird species | 44 | 57 | 43 | 1 | 14 |
| FP-only bird species | 31 | 45 | 18 | 13 | 27 |

![Raw detections and TP/FP species overlap](https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/main/docs/model-comparison/field-comparison.svg)

The raw detection increase is **3.38× (+238%)**; confirmed species increase is **13 species (+29.5%)**. Species confirmed by both models: 43. One was confirmed only by V2.4 and 14 only by V3, giving 58 species in the combined confirmed list.

The FP-only lists are model-specific. **Parus major is FP-only in V2.4 (one FP, no TP), but TP-confirmed in V3 (91 TP, no marked FP).** It therefore belongs to V2.4's exclusive FP-only list and V3's exclusive TP list. In an earlier combined report, all species confirmed by either model were removed from its false-species table; that produced 30 rather than 31 V2.4 FP species. Here the requested per-model classification is used consistently.

### TP-confirmed species lists

**Shared TP-confirmed species (43)**

`Acanthis flammea`, `Aegithalos caudatus`, `Anas platyrhynchos`, `Anser albifrons`, `Anser anser`, `Ardea cinerea`, `Bombycilla garrulus`, `Botaurus stellaris`, `Buteo buteo`, `Carduelis carduelis`, `Certhia familiaris`, `Chloris chloris`, `Chroicocephalus ridibundus`, `Coccothraustes coccothraustes`, `Corvus corax`, `Cyanistes caeruleus`, `Dendrocopos leucotos`, `Dryobates minor`, `Emberiza schoeniclus`, `Erithacus rubecula`, `Fringilla coelebs`, `Fringilla montifringilla`, `Gallinago gallinago`, `Garrulus glandarius`, `Linaria cannabina`, `Motacilla alba`, `Periparus ater`, `Phylloscopus collybita`, `Pica pica`, `Poecile montanus`, `Prunella modularis`, `Pyrrhula pyrrhula`, `Regulus regulus`, `Sitta europaea`, `Spinus spinus`, `Strix aluco`, `Tetrastes bonasia`, `Troglodytes troglodytes`, `Turdus iliacus`, `Turdus merula`, `Turdus philomelos`, `Turdus pilaris`, `Turdus viscivorus`

**TP-confirmed only by V2.4 (1)**

`Glaucidium passerinum`

**TP-confirmed only by V3 (14)**

`Alauda arvensis`, `Anser serrirostris`, `Anthus cervinus`, `Anthus pratensis`, `Botaurus minutus`, `Coloeus monedula`, `Corvus cornix`, `Dendrocopos major`, `Emberiza citrinella`, `Loxia curvirostra`, `Lyrurus tetrix`, `Nucifraga caryocatactes`, `Parus major`, `Strix uralensis`

"Confirmed only" describes the available review marks; it does not automatically establish a false negative in the other model. The other model may have unreviewed or FP-labelled detections.

## Reviewed detections

| Model | Reviewed TP | Reviewed FP | Unreviewed | Reviewed share (%) | FP among all reviewed (%) |
| --- | --- | --- | --- | --- | --- |
| v2.4 | 1377 | 188 | 1260 | 55.40 | 12.01 |
| v3 | 2411 | 298 | 6838 | 28.38 | 11.00 |

Across all reviewed labels, FP proportions are 12.01% for V2.4 and 11.00% for V3. Within the **combined 58-species TP-confirmed list**, they are 4.18% (60 FP / 1,437 reviewed) and 6.33% (163 FP / 2,574 reviewed). These are different denominators and answer different questions. The former includes erroneous species and V3 non-bird labels; the latter describes detections assigned to the confirmed bird list.

Neither aggregate is an unbiased estimate of performance on all recordings: review coverage and how recordings were selected for review affect the result. Counts of raw detections, reviewed TP and true acoustic events are also different quantities.

## Ten-minute intervals

The analysis uses clock-aligned bins (00–09:59, 10–19:59, etc.). Each species is counted once per bin. Detailed interval comparisons use the **union of species with at least one TP in either model** and include all detections for those species, including FP and unreviewed records. Edge bins are partial. A bin with at least one TP is confirmed even if it also contains FP.

| Metric | V2.4 | V3 |
| --- | --- | --- |
| All species × bins | 816 | 1871 |
| Species × bins with ≥1 TP | 509 | 860 |
| Completely unreviewed species × bins | 260 | 903 |

![All intervals and TP intervals for each confirmed species](https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/main/docs/model-comparison/species-intervals.svg)

V3 has **69.0% more TP-confirmed species × bins**. In the paired TP comparison, 307 bins were confirmed in both models, 202 only in V2.4, and 553 only in V3. These exclusive counts describe TP marks, not automatically missed sounds. For all detection bins, including unreviewed ones, overlap is 696, with 120 only in V2.4 and 1,175 only in V3.

### Complete per-species results

FP percentage is based solely on reviewed records. A missing percentage means no reviewed records. Unreviewed bins have no marks at all; partially reviewed bins contain both marked and unmarked detections.

| Species | Model | Detections | TP | FP | FP (%) | All bins | TP bins | Unreviewed bins | Partly reviewed bins |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Acanthis flammea | v2.4 | 55 | 55 | 0 | 0.00 | 22 | 22 | 0 | 0 |
| Aegithalos caudatus | v2.4 | 58 | 41 | 0 | 0.00 | 11 | 9 | 2 | 3 |
| Alauda arvensis | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Anas platyrhynchos | v2.4 | 16 | 16 | 0 | 0.00 | 6 | 6 | 0 | 0 |
| Anser albifrons | v2.4 | 183 | 7 | 1 | 12.50 | 18 | 2 | 15 | 0 |
| Anser anser | v2.4 | 4 | 4 | 0 | 0.00 | 4 | 4 | 0 | 0 |
| Anser serrirostris | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Anthus cervinus | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Anthus pratensis | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Ardea cinerea | v2.4 | 24 | 21 | 2 | 8.70 | 10 | 7 | 1 | 0 |
| Bombycilla garrulus | v2.4 | 24 | 23 | 0 | 0.00 | 13 | 13 | 0 | 1 |
| Botaurus minutus | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Botaurus stellaris | v2.4 | 18 | 13 | 3 | 18.75 | 10 | 7 | 1 | 1 |
| Buteo buteo | v2.4 | 14 | 13 | 1 | 7.14 | 4 | 3 | 0 | 0 |
| Carduelis carduelis | v2.4 | 25 | 25 | 0 | 0.00 | 15 | 15 | 0 | 0 |
| Certhia familiaris | v2.4 | 85 | 40 | 2 | 4.76 | 8 | 3 | 4 | 0 |
| Chloris chloris | v2.4 | 38 | 27 | 0 | 0.00 | 4 | 4 | 0 | 1 |
| Chroicocephalus ridibundus | v2.4 | 1 | 1 | 0 | 0.00 | 1 | 1 | 0 | 0 |
| Coccothraustes coccothraustes | v2.4 | 26 | 22 | 4 | 15.38 | 12 | 8 | 0 | 0 |
| Coloeus monedula | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Corvus corax | v2.4 | 54 | 53 | 0 | 0.00 | 19 | 19 | 0 | 1 |
| Corvus cornix | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Cyanistes caeruleus | v2.4 | 23 | 21 | 0 | 0.00 | 10 | 9 | 1 | 1 |
| Dendrocopos leucotos | v2.4 | 19 | 17 | 0 | 0.00 | 1 | 1 | 0 | 1 |
| Dendrocopos major | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Dryobates minor | v2.4 | 2 | 1 | 1 | 50.00 | 2 | 1 | 0 | 0 |
| Emberiza citrinella | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Emberiza schoeniclus | v2.4 | 3 | 3 | 0 | 0.00 | 3 | 3 | 0 | 0 |
| Erithacus rubecula | v2.4 | 31 | 31 | 0 | 0.00 | 4 | 4 | 0 | 0 |
| Fringilla coelebs | v2.4 | 87 | 66 | 4 | 5.71 | 32 | 23 | 7 | 3 |
| Fringilla montifringilla | v2.4 | 71 | 69 | 2 | 2.82 | 35 | 34 | 0 | 0 |
| Gallinago gallinago | v2.4 | 1 | 1 | 0 | 0.00 | 1 | 1 | 0 | 0 |
| Garrulus glandarius | v2.4 | 83 | 61 | 0 | 0.00 | 29 | 25 | 4 | 1 |
| Glaucidium passerinum | v2.4 | 2 | 1 | 1 | 50.00 | 2 | 1 | 0 | 0 |
| Linaria cannabina | v2.4 | 2 | 2 | 0 | 0.00 | 1 | 1 | 0 | 0 |
| Loxia curvirostra | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Lyrurus tetrix | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Motacilla alba | v2.4 | 6 | 6 | 0 | 0.00 | 3 | 3 | 0 | 0 |
| Nucifraga caryocatactes | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Parus major | v2.4 | 1 | 0 | 1 | 100.00 | 1 | 0 | 0 | 0 |
| Periparus ater | v2.4 | 8 | 8 | 0 | 0.00 | 6 | 6 | 0 | 0 |
| Phylloscopus collybita | v2.4 | 12 | 12 | 0 | 0.00 | 7 | 7 | 0 | 0 |
| Pica pica | v2.4 | 91 | 78 | 0 | 0.00 | 23 | 16 | 7 | 2 |
| Poecile montanus | v2.4 | 103 | 59 | 0 | 0.00 | 35 | 21 | 14 | 4 |
| Prunella modularis | v2.4 | 49 | 35 | 0 | 0.00 | 26 | 21 | 5 | 0 |
| Pyrrhula pyrrhula | v2.4 | 326 | 118 | 0 | 0.00 | 80 | 43 | 37 | 13 |
| Regulus regulus | v2.4 | 37 | 30 | 0 | 0.00 | 14 | 14 | 0 | 1 |
| Sitta europaea | v2.4 | 31 | 16 | 0 | 0.00 | 1 | 1 | 0 | 1 |
| Spinus spinus | v2.4 | 251 | 85 | 0 | 0.00 | 91 | 39 | 52 | 7 |
| Strix aluco | v2.4 | 131 | 61 | 17 | 21.79 | 27 | 13 | 0 | 2 |
| Strix uralensis | v2.4 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Tetrastes bonasia | v2.4 | 5 | 4 | 1 | 20.00 | 5 | 4 | 0 | 0 |
| Troglodytes troglodytes | v2.4 | 6 | 6 | 0 | 0.00 | 1 | 1 | 0 | 0 |
| Turdus iliacus | v2.4 | 111 | 65 | 19 | 22.62 | 66 | 37 | 15 | 1 |
| Turdus merula | v2.4 | 8 | 8 | 0 | 0.00 | 5 | 5 | 0 | 0 |
| Turdus philomelos | v2.4 | 6 | 5 | 1 | 16.67 | 6 | 5 | 0 | 0 |
| Turdus pilaris | v2.4 | 564 | 145 | 0 | 0.00 | 141 | 46 | 95 | 6 |
| Turdus viscivorus | v2.4 | 2 | 2 | 0 | 0.00 | 1 | 1 | 0 | 0 |
| Acanthis flammea | v3 | 178 | 126 | 8 | 5.97 | 44 | 34 | 8 | 2 |
| Aegithalos caudatus | v3 | 202 | 62 | 0 | 0.00 | 18 | 10 | 8 | 8 |
| Alauda arvensis | v3 | 2 | 2 | 0 | 0.00 | 1 | 1 | 0 | 0 |
| Anas platyrhynchos | v3 | 8 | 8 | 0 | 0.00 | 5 | 5 | 0 | 0 |
| Anser albifrons | v3 | 214 | 43 | 0 | 0.00 | 27 | 8 | 19 | 3 |
| Anser anser | v3 | 13 | 3 | 10 | 76.92 | 5 | 3 | 0 | 0 |
| Anser serrirostris | v3 | 11 | 8 | 0 | 0.00 | 5 | 4 | 1 | 1 |
| Anthus cervinus | v3 | 5 | 5 | 0 | 0.00 | 5 | 5 | 0 | 0 |
| Anthus pratensis | v3 | 33 | 29 | 2 | 6.45 | 23 | 21 | 0 | 1 |
| Ardea cinerea | v3 | 37 | 34 | 3 | 8.11 | 12 | 10 | 0 | 0 |
| Bombycilla garrulus | v3 | 81 | 63 | 3 | 4.55 | 22 | 14 | 7 | 0 |
| Botaurus minutus | v3 | 6 | 2 | 3 | 60.00 | 5 | 1 | 1 | 0 |
| Botaurus stellaris | v3 | 31 | 17 | 3 | 15.00 | 11 | 7 | 1 | 2 |
| Buteo buteo | v3 | 12 | 4 | 1 | 20.00 | 3 | 1 | 1 | 1 |
| Carduelis carduelis | v3 | 91 | 69 | 0 | 0.00 | 38 | 34 | 4 | 5 |
| Certhia familiaris | v3 | 142 | 25 | 3 | 10.71 | 12 | 7 | 3 | 5 |
| Chloris chloris | v3 | 197 | 72 | 3 | 4.00 | 25 | 14 | 10 | 1 |
| Chroicocephalus ridibundus | v3 | 4 | 3 | 0 | 0.00 | 1 | 1 | 0 | 1 |
| Coccothraustes coccothraustes | v3 | 45 | 39 | 3 | 7.14 | 19 | 14 | 2 | 1 |
| Coloeus monedula | v3 | 1 | 1 | 0 | 0.00 | 1 | 1 | 0 | 0 |
| Corvus corax | v3 | 607 | 129 | 32 | 19.88 | 109 | 19 | 71 | 11 |
| Corvus cornix | v3 | 1 | 1 | 0 | 0.00 | 1 | 1 | 0 | 0 |
| Cyanistes caeruleus | v3 | 305 | 77 | 0 | 0.00 | 64 | 33 | 31 | 23 |
| Dendrocopos leucotos | v3 | 26 | 21 | 0 | 0.00 | 2 | 2 | 0 | 1 |
| Dendrocopos major | v3 | 6 | 3 | 2 | 40.00 | 5 | 3 | 0 | 1 |
| Dryobates minor | v3 | 10 | 9 | 1 | 10.00 | 5 | 5 | 0 | 0 |
| Emberiza citrinella | v3 | 2 | 2 | 0 | 0.00 | 2 | 2 | 0 | 0 |
| Emberiza schoeniclus | v3 | 18 | 16 | 0 | 0.00 | 13 | 11 | 2 | 0 |
| Erithacus rubecula | v3 | 231 | 58 | 1 | 1.69 | 38 | 18 | 19 | 13 |
| Fringilla coelebs | v3 | 484 | 73 | 17 | 18.89 | 96 | 25 | 62 | 29 |
| Fringilla montifringilla | v3 | 171 | 131 | 10 | 7.09 | 64 | 50 | 9 | 6 |
| Gallinago gallinago | v3 | 1 | 1 | 0 | 0.00 | 1 | 1 | 0 | 0 |
| Garrulus glandarius | v3 | 243 | 118 | 1 | 0.84 | 62 | 36 | 26 | 5 |
| Glaucidium passerinum | v3 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 |
| Linaria cannabina | v3 | 4 | 4 | 0 | 0.00 | 1 | 1 | 0 | 0 |
| Loxia curvirostra | v3 | 43 | 22 | 15 | 40.54 | 22 | 8 | 3 | 1 |
| Lyrurus tetrix | v3 | 2 | 1 | 1 | 50.00 | 2 | 1 | 0 | 0 |
| Motacilla alba | v3 | 12 | 12 | 0 | 0.00 | 7 | 7 | 0 | 0 |
| Nucifraga caryocatactes | v3 | 1 | 1 | 0 | 0.00 | 1 | 1 | 0 | 0 |
| Parus major | v3 | 395 | 91 | 0 | 0.00 | 88 | 45 | 43 | 32 |
| Periparus ater | v3 | 35 | 32 | 0 | 0.00 | 17 | 14 | 3 | 0 |
| Phylloscopus collybita | v3 | 28 | 26 | 0 | 0.00 | 9 | 8 | 1 | 1 |
| Pica pica | v3 | 97 | 70 | 0 | 0.00 | 21 | 17 | 4 | 3 |
| Poecile montanus | v3 | 363 | 88 | 0 | 0.00 | 57 | 25 | 32 | 19 |
| Prunella modularis | v3 | 69 | 61 | 0 | 0.00 | 29 | 29 | 0 | 1 |
| Pyrrhula pyrrhula | v3 | 1267 | 72 | 0 | 0.00 | 144 | 33 | 111 | 32 |
| Regulus regulus | v3 | 206 | 85 | 1 | 1.16 | 37 | 25 | 11 | 19 |
| Sitta europaea | v3 | 58 | 31 | 0 | 0.00 | 10 | 7 | 3 | 1 |
| Spinus spinus | v3 | 666 | 89 | 0 | 0.00 | 165 | 49 | 116 | 41 |
| Strix aluco | v3 | 305 | 160 | 25 | 13.51 | 64 | 25 | 17 | 7 |
| Strix uralensis | v3 | 4 | 2 | 2 | 50.00 | 4 | 2 | 0 | 0 |
| Tetrastes bonasia | v3 | 13 | 13 | 0 | 0.00 | 7 | 7 | 0 | 0 |
| Troglodytes troglodytes | v3 | 23 | 23 | 0 | 0.00 | 3 | 3 | 0 | 0 |
| Turdus iliacus | v3 | 159 | 45 | 1 | 2.17 | 64 | 29 | 34 | 15 |
| Turdus merula | v3 | 494 | 97 | 0 | 0.00 | 105 | 40 | 65 | 26 |
| Turdus philomelos | v3 | 63 | 41 | 1 | 2.38 | 38 | 25 | 12 | 3 |
| Turdus pilaris | v3 | 1638 | 86 | 1 | 1.15 | 216 | 54 | 161 | 52 |
| Turdus viscivorus | v3 | 17 | 5 | 10 | 66.67 | 16 | 4 | 2 | 0 |

### Paired interval overlap by species

| Species | TP both | TP V2.4 only | TP V3 only | All both | All V2.4 only | All V3 only |
| --- | --- | --- | --- | --- | --- | --- |
| Acanthis flammea | 19 | 3 | 15 | 20 | 2 | 24 |
| Aegithalos caudatus | 7 | 2 | 3 | 10 | 1 | 8 |
| Alauda arvensis | 0 | 0 | 1 | 0 | 0 | 1 |
| Anas platyrhynchos | 3 | 3 | 2 | 3 | 3 | 2 |
| Anser albifrons | 2 | 0 | 6 | 16 | 2 | 11 |
| Anser anser | 1 | 3 | 2 | 1 | 3 | 4 |
| Anser serrirostris | 0 | 0 | 4 | 0 | 0 | 5 |
| Anthus cervinus | 0 | 0 | 5 | 0 | 0 | 5 |
| Anthus pratensis | 0 | 0 | 21 | 0 | 0 | 23 |
| Ardea cinerea | 6 | 1 | 4 | 7 | 3 | 5 |
| Bombycilla garrulus | 7 | 6 | 7 | 12 | 1 | 10 |
| Botaurus minutus | 0 | 0 | 1 | 0 | 0 | 5 |
| Botaurus stellaris | 5 | 2 | 2 | 6 | 4 | 5 |
| Buteo buteo | 1 | 2 | 0 | 2 | 2 | 1 |
| Carduelis carduelis | 11 | 4 | 23 | 12 | 3 | 26 |
| Certhia familiaris | 2 | 1 | 5 | 7 | 1 | 5 |
| Chloris chloris | 2 | 2 | 12 | 4 | 0 | 21 |
| Chroicocephalus ridibundus | 1 | 0 | 0 | 1 | 0 | 0 |
| Coccothraustes coccothraustes | 8 | 0 | 6 | 10 | 2 | 9 |
| Coloeus monedula | 0 | 0 | 1 | 0 | 0 | 1 |
| Corvus corax | 6 | 13 | 13 | 18 | 1 | 91 |
| Corvus cornix | 0 | 0 | 1 | 0 | 0 | 1 |
| Cyanistes caeruleus | 7 | 2 | 26 | 9 | 1 | 55 |
| Dendrocopos leucotos | 1 | 0 | 1 | 1 | 0 | 1 |
| Dendrocopos major | 0 | 0 | 3 | 0 | 0 | 5 |
| Dryobates minor | 1 | 0 | 4 | 1 | 1 | 4 |
| Emberiza citrinella | 0 | 0 | 2 | 0 | 0 | 2 |
| Emberiza schoeniclus | 3 | 0 | 8 | 3 | 0 | 10 |
| Erithacus rubecula | 2 | 2 | 16 | 4 | 0 | 34 |
| Fringilla coelebs | 14 | 9 | 11 | 26 | 6 | 70 |
| Fringilla montifringilla | 27 | 7 | 23 | 31 | 4 | 33 |
| Gallinago gallinago | 1 | 0 | 0 | 1 | 0 | 0 |
| Garrulus glandarius | 15 | 10 | 21 | 29 | 0 | 33 |
| Glaucidium passerinum | 0 | 1 | 0 | 0 | 2 | 0 |
| Linaria cannabina | 1 | 0 | 0 | 1 | 0 | 0 |
| Loxia curvirostra | 0 | 0 | 8 | 0 | 0 | 22 |
| Lyrurus tetrix | 0 | 0 | 1 | 0 | 0 | 2 |
| Motacilla alba | 3 | 0 | 4 | 3 | 0 | 4 |
| Nucifraga caryocatactes | 0 | 0 | 1 | 0 | 0 | 1 |
| Parus major | 0 | 0 | 45 | 1 | 0 | 87 |
| Periparus ater | 5 | 1 | 9 | 5 | 1 | 12 |
| Phylloscopus collybita | 4 | 3 | 4 | 5 | 2 | 4 |
| Pica pica | 9 | 7 | 8 | 18 | 5 | 3 |
| Poecile montanus | 13 | 8 | 12 | 34 | 1 | 23 |
| Prunella modularis | 16 | 5 | 13 | 19 | 7 | 10 |
| Pyrrhula pyrrhula | 21 | 22 | 12 | 80 | 0 | 64 |
| Regulus regulus | 12 | 2 | 13 | 12 | 2 | 25 |
| Sitta europaea | 1 | 0 | 6 | 1 | 0 | 9 |
| Spinus spinus | 19 | 20 | 30 | 84 | 7 | 81 |
| Strix aluco | 11 | 2 | 14 | 17 | 10 | 47 |
| Strix uralensis | 0 | 0 | 2 | 0 | 0 | 4 |
| Tetrastes bonasia | 3 | 1 | 4 | 3 | 2 | 4 |
| Troglodytes troglodytes | 1 | 0 | 2 | 1 | 0 | 2 |
| Turdus iliacus | 15 | 22 | 14 | 35 | 31 | 29 |
| Turdus merula | 2 | 3 | 38 | 4 | 1 | 101 |
| Turdus philomelos | 2 | 3 | 23 | 3 | 3 | 35 |
| Turdus pilaris | 16 | 30 | 38 | 135 | 6 | 81 |
| Turdus viscivorus | 1 | 0 | 3 | 1 | 0 | 15 |

## Confidence thresholds

Thresholds are applied to individual detections before interval aggregation. The combined confirmed species list is fixed across thresholds. TP/FP percentages exclude unreviewed records.

![Threshold comparison](https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/main/docs/model-comparison/threshold-comparison.svg)

| Model | Threshold | TP | FP | FP (%) | TP bins | All bins |
| --- | --- | --- | --- | --- | --- | --- |
| v2.4 | 0.60 | 1377 | 60 | 4.18 | 509 | 816 |
| v2.4 | 0.70 | 978 | 35 | 3.46 | 394 | 629 |
| v2.4 | 0.80 | 637 | 15 | 2.30 | 272 | 449 |
| v2.4 | 0.90 | 310 | 6 | 1.90 | 151 | 250 |
| v2.4 | 0.95 | 138 | 2 | 1.43 | 70 | 113 |
| v3 | 0.60 | 2411 | 163 | 6.33 | 860 | 1871 |
| v3 | 0.70 | 2077 | 81 | 3.75 | 759 | 1522 |
| v3 | 0.80 | 1537 | 34 | 2.16 | 585 | 1106 |
| v3 | 0.90 | 785 | 9 | 1.13 | 336 | 551 |
| v3 | 0.95 | 156 | 0 | 0.00 | 84 | 124 |

At 0.80, V3 retains 585 TP bins versus 272 for V2.4, with reviewed FP proportions of 2.16% and 2.30%. At 0.90, the counts are 336 versus 151 and FP proportions 1.13% versus 1.90%. This suggests a useful trade-off in the current reviewed data, but confidence scores are not calibrated between models and these thresholds have not been independently validated. Zero marked FP at 0.95 in V3 means zero in the reviewed subset, not guaranteed error-free output.

## One comparison of FP-only species

These species are not included in separate detailed false-species charts. The following single table combines both FP-only lists, indicates shared/exclusive membership and gives maximum confidence among reviewed FP. A species can have FP-only status in one model but TP in the other.

| Species | FP-only membership | v2.4 FP | v2.4 max FP confidence | v3 FP | v3 max FP confidence |
| --- | --- | --- | --- | --- | --- |
| Aegolius funereus | Both | 1 | 0.71 | 1 | 0.67 |
| Alcedo atthis | V2.4 only | 3 | 0.74 | 0 | — |
| Anthus hodgsoni | V2.4 only | 3 | 0.79 | 0 | — |
| Anthus richardi | V3 only | 0 | — | 1 | 0.61 |
| Anthus trivialis | Both | 1 | 0.69 | 2 | 0.67 |
| Ardea alba | V3 only | 0 | — | 1 | 0.64 |
| Asio otus | V3 only | 0 | — | 1 | 0.65 |
| Astur cooperii | V3 only | 0 | — | 1 | 0.65 |
| Athene noctua | Both | 12 | 0.83 | 1 | 0.66 |
| Branta bernicla | V3 only | 0 | — | 1 | 0.81 |
| Branta canadensis | V3 only | 0 | — | 20 | 0.83 |
| Branta leucopsis | V2.4 only | 2 | 0.76 | 0 | — |
| Bubo bubo | V3 only | 0 | — | 2 | 0.66 |
| Caprimulgus europaeus | V2.4 only | 1 | 0.75 | 0 | — |
| Certhia brachydactyla | V2.4 only | 2 | 0.77 | 0 | — |
| Cettia cetti | V3 only | 0 | — | 2 | 0.68 |
| Clangula hyemalis | V3 only | 0 | — | 1 | 0.69 |
| Coturnix coturnix | V3 only | 0 | — | 1 | 0.61 |
| Cuculus canorus | V3 only | 0 | — | 1 | 0.69 |
| Dryocopus martius | Both | 2 | 0.64 | 7 | 0.87 |
| Emberiza hortulana | V3 only | 0 | — | 1 | 0.61 |
| Emberiza pusilla | Both | 8 | 0.90 | 1 | 0.60 |
| Emberiza rustica | Both | 2 | 0.67 | 2 | 0.74 |
| Ficedula parva | V3 only | 0 | — | 2 | 0.75 |
| Fulica atra | Both | 2 | 0.69 | 2 | 0.81 |
| Gallinula chloropus | Both | 4 | 0.89 | 6 | 0.91 |
| Gavia immer | V3 only | 0 | — | 3 | 0.86 |
| Lagopus lagopus | V2.4 only | 1 | 0.67 | 0 | — |
| Lophophanes cristatus | V3 only | 0 | — | 1 | 0.66 |
| Loxia leucoptera | V3 only | 0 | — | 2 | 0.76 |
| Loxia pytyopsittacus | Both | 3 | 0.75 | 5 | 0.93 |
| Motacilla cinerea | Both | 2 | 0.88 | 2 | 0.68 |
| Muscicapa striata | Both | 6 | 0.72 | 2 | 0.66 |
| Numenius arquata | V2.4 only | 1 | 0.67 | 0 | — |
| Nycticorax nycticorax | Both | 8 | 0.83 | 6 | 0.83 |
| Oriolus oriolus | V3 only | 0 | — | 1 | 0.91 |
| Otus scops | Both | 2 | 0.81 | 9 | 0.90 |
| Panurus biarmicus | V2.4 only | 1 | 0.71 | 0 | — |
| Parus major | V2.4 only | 1 | 0.76 | 0 | — |
| Perdix perdix | V2.4 only | 2 | 0.82 | 0 | — |
| Phoenicurus phoenicurus | Both | 2 | 0.61 | 2 | 0.86 |
| Phylloscopus proregulus | V2.4 only | 1 | 0.73 | 0 | — |
| Phylloscopus trochiloides | V3 only | 0 | — | 1 | 0.64 |
| Phylloscopus trochilus | V3 only | 0 | — | 1 | 0.62 |
| Pinicola enucleator | V3 only | 0 | — | 1 | 0.82 |
| Plectrophenax nivalis | V3 only | 0 | — | 1 | 0.63 |
| Pluvialis apricaria | V2.4 only | 1 | 0.61 | 0 | — |
| Poecile palustris | Both | 4 | 0.76 | 1 | 0.70 |
| Porzana porzana | Both | 44 | 0.92 | 2 | 0.62 |
| Rallus aquaticus | Both | 2 | 0.89 | 1 | 0.76 |
| Regulus ignicapilla | Both | 1 | 0.62 | 2 | 0.74 |
| Scolopax rusticola | V3 only | 0 | — | 15 | 0.75 |
| Strix nebulosa | V2.4 only | 4 | 0.77 | 0 | — |
| Tetrao urogallus | V3 only | 0 | — | 1 | 0.66 |
| Tringa ochropus | V3 only | 0 | — | 1 | 0.66 |
| Turdus torquatus | V3 only | 0 | — | 2 | 0.65 |
| Tyto furcata | V3 only | 0 | — | 1 | 0.69 |
| Vanellus vanellus | V3 only | 0 | — | 7 | 0.82 |

### V3 non-bird outputs, excluded from bird overlap counts

| Non-bird label | Detections | TP | FP | Unreviewed |
| --- | --- | --- | --- | --- |
| Alouatta palliata | 1 | 0 | 1 | 0 |
| Capreolus capreolus | 1 | 0 | 1 | 0 |
| Chorthippus biguttulus | 3 | 0 | 1 | 2 |
| Leptophyes punctatissima | 1 | 0 | 0 | 1 |
| Pan troglodytes | 3 | 0 | 3 | 0 |
| Vulpes vulpes | 2 | 0 | 2 | 0 |

## Interpretation and next steps

- V3 produced substantially more raw detections and more manually confirmed species and intervals in this deployment.
- Broader coverage also came with a longer FP-only bird list and more unreviewed output. The greater output volume implies more potential review work, but review time was not measured.
- Species-level changes differ. For Tawny Owl, TP bins increased from 13 to 25 and reviewed FP proportion decreased from 21.79% to 13.51%. For Common Raven, TP bins remained 19 in both models, while V3 had 32 reviewed FP (19.88% among reviewed raven detections).
- This is one location, one autumn period, two separate recording chains and different sensitivity settings. It compares practical field results of these configurations. Exact device uptime was not reconstructed from recording logs, and lack of detections was not interpreted as downtime.
- Adjacent detections and bins may represent the same calling event. They are not independent experimental replicates. No significance claim is made.
- Full recall/FN cannot be measured from detection exports because events missed by both models are absent. A stronger follow-up would run both models on identical saved audio and independently annotate a defined sample, including intervals without detections.

I would welcome comparable field results, especially on Raspberry Pi Zero 2 W, and comments on which species improved or became more prone to false positives. Please include model build, sensitivity, confidence threshold, filtering settings and review method when sharing results.
