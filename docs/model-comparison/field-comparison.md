# BirdNET v2.4 vs v3: paired field comparison on Raspberry Pi Zero 2 W

I ran two identical Raspberry Pi Zero 2 W devices with Sound Blaster G3 sound cards and identical microphones side by side at one location from 27 September to 2 October 2026. I manually reviewed a substantial subset of the saved detections using TP/FP marks. This post compares both raw outputs and the reviewed subset.

**The main finding is broader observed coverage with V3: 9,547 raw detections versus 2,825, and 57 bird species with at least one TP versus 44. V3 also produced more FP-only bird species.** The increased output should therefore be considered together with species-specific error proportions and temporal coverage.

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

## How the FP proportion changed by species

For each species, the compared quantity is **FP / (FP + TP) × 100%**, using reviewed detections only. The percentage of all detections reviewed is not compared: it reflects the amount of manual review rather than a property of either model. Total reviewed TP/FP counts are shown only as denominators for species-specific error proportions, not as measures of acoustic abundance.

The table below includes species with reviewed records in both models from the union of TP-confirmed species. Species with no reviewed records in one model have no comparable error percentage and are not assigned a zero. Rows are ordered by the change in FP proportion.

| Species | V2.4 TP | V2.4 FP | V2.4 FP (%) | V3 TP | V3 FP | V3 FP (%) | Change (percentage points) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Parus major | 0 | 1 | 100.00 | 91 | 0 | 0.00 | -100.00 |
| Dryobates minor | 1 | 1 | 50.00 | 9 | 1 | 10.00 | -40.00 |
| Turdus iliacus | 65 | 19 | 22.62 | 45 | 1 | 2.17 | -20.45 |
| Tetrastes bonasia | 4 | 1 | 20.00 | 13 | 0 | 0.00 | -20.00 |
| Turdus philomelos | 5 | 1 | 16.67 | 41 | 1 | 2.38 | -14.29 |
| Anser albifrons | 7 | 1 | 12.50 | 43 | 0 | 0.00 | -12.50 |
| Strix aluco | 61 | 17 | 21.79 | 160 | 25 | 13.51 | -8.28 |
| Coccothraustes coccothraustes | 22 | 4 | 15.38 | 39 | 3 | 7.14 | -8.24 |
| Botaurus stellaris | 13 | 3 | 18.75 | 17 | 3 | 15.00 | -3.75 |
| Ardea cinerea | 21 | 2 | 8.70 | 34 | 3 | 8.11 | -0.59 |
| Motacilla alba | 6 | 0 | 0.00 | 12 | 0 | 0.00 | 0.00 |
| Periparus ater | 8 | 0 | 0.00 | 32 | 0 | 0.00 | 0.00 |
| Cyanistes caeruleus | 21 | 0 | 0.00 | 77 | 0 | 0.00 | 0.00 |
| Linaria cannabina | 2 | 0 | 0.00 | 4 | 0 | 0.00 | 0.00 |
| Anas platyrhynchos | 16 | 0 | 0.00 | 8 | 0 | 0.00 | 0.00 |
| Chroicocephalus ridibundus | 1 | 0 | 0.00 | 3 | 0 | 0.00 | 0.00 |
| Phylloscopus collybita | 12 | 0 | 0.00 | 26 | 0 | 0.00 | 0.00 |
| Pica pica | 78 | 0 | 0.00 | 70 | 0 | 0.00 | 0.00 |
| Poecile montanus | 59 | 0 | 0.00 | 88 | 0 | 0.00 | 0.00 |
| Prunella modularis | 35 | 0 | 0.00 | 61 | 0 | 0.00 | 0.00 |
| Gallinago gallinago | 1 | 0 | 0.00 | 1 | 0 | 0.00 | 0.00 |
| Emberiza schoeniclus | 3 | 0 | 0.00 | 16 | 0 | 0.00 | 0.00 |
| Carduelis carduelis | 25 | 0 | 0.00 | 69 | 0 | 0.00 | 0.00 |
| Turdus merula | 8 | 0 | 0.00 | 97 | 0 | 0.00 | 0.00 |
| Pyrrhula pyrrhula | 118 | 0 | 0.00 | 72 | 0 | 0.00 | 0.00 |
| Troglodytes troglodytes | 6 | 0 | 0.00 | 23 | 0 | 0.00 | 0.00 |
| Spinus spinus | 85 | 0 | 0.00 | 89 | 0 | 0.00 | 0.00 |
| Sitta europaea | 16 | 0 | 0.00 | 31 | 0 | 0.00 | 0.00 |
| Dendrocopos leucotos | 17 | 0 | 0.00 | 21 | 0 | 0.00 | 0.00 |
| Aegithalos caudatus | 41 | 0 | 0.00 | 62 | 0 | 0.00 | 0.00 |
| Garrulus glandarius | 61 | 0 | 0.00 | 118 | 1 | 0.84 | 0.84 |
| Turdus pilaris | 145 | 0 | 0.00 | 86 | 1 | 1.15 | 1.15 |
| Regulus regulus | 30 | 0 | 0.00 | 85 | 1 | 1.16 | 1.16 |
| Erithacus rubecula | 31 | 0 | 0.00 | 58 | 1 | 1.69 | 1.69 |
| Chloris chloris | 27 | 0 | 0.00 | 72 | 3 | 4.00 | 4.00 |
| Fringilla montifringilla | 69 | 2 | 2.82 | 131 | 10 | 7.09 | 4.28 |
| Bombycilla garrulus | 23 | 0 | 0.00 | 63 | 3 | 4.55 | 4.55 |
| Certhia familiaris | 40 | 2 | 4.76 | 25 | 3 | 10.71 | 5.95 |
| Acanthis flammea | 55 | 0 | 0.00 | 126 | 8 | 5.97 | 5.97 |
| Buteo buteo | 13 | 1 | 7.14 | 4 | 1 | 20.00 | 12.86 |
| Fringilla coelebs | 66 | 4 | 5.71 | 73 | 17 | 18.89 | 13.17 |
| Corvus corax | 53 | 0 | 0.00 | 129 | 32 | 19.88 | 19.88 |
| Turdus viscivorus | 2 | 0 | 0.00 | 5 | 10 | 66.67 | 66.67 |
| Anser anser | 4 | 0 | 0.00 | 3 | 10 | 76.92 | 76.92 |

### Clear differences in the reviewed sample

- **Redwing (*Turdus iliacus*):** FP proportion fell from **22.62% to 2.17%** (19 FP / 84 reviewed versus 1 / 46). Raw detections increased from 111 to 159. This is a useful example of greater output accompanied by fewer errors in the reviewed sample.
- **Tawny Owl (*Strix aluco*):** FP proportion fell from **21.79% to 13.51%**, while raw detections increased from **131 to 305** and TP bins from **13 to 25**. Absolute FP count increased (17 to 25), but its proportion decreased because TP increased from 61 to 160. More absolute FP does not necessarily mean a higher error proportion.
- **Song Thrush (*Turdus philomelos*):** FP proportion fell from **16.67% to 2.38%** and raw detections increased from 6 to 63. The V2.4 denominator is only six reviewed detections, so the size of the improvement is less secure than the point percentages suggest.
- **Common Raven (*Corvus corax*):** FP proportion rose from **0% to 19.88%** (0 / 53 versus 32 / 161), while raw detections increased from **54 to 607**. TP bins remained **19 in both models**. The extra output therefore does not establish a broader confirmed temporal coverage for this species; reviewed FP make a documented contribution to the increase.
- **Common Chaffinch (*Fringilla coelebs*):** FP proportion rose from **5.71% to 18.89%**, while raw detections increased from **87 to 484**. Unlike Redwing, more output here coincides with a higher error proportion in the reviewed sample.
- **Eurasian Bullfinch, Eurasian Siskin and Common Blackbird:** raw detections increased substantially, while both models had **zero marked FP** for these species. This supports additional useful output in the reviewed examples, but does not certify every raw detection as correct.

Large percentage changes based on very small samples should be treated separately. Great Tit has only one reviewed V2.4 record (FP); Grey Goose has four (all TP); Mistle Thrush has two (both TP). Their 100%, 0% and subsequent changes are descriptive counts, not stable species-level accuracy estimates.

The proportions above describe the reviewed sample. They can still depend on which sounds were selected for review; eliminating empty marks does not remove this selection effect. No assumption is made that the reviewed sample was random.

## Which species account for the extra raw detections?

Raw detections include **all records**, irrespective of manual review. V3 produced 9,547 versus 2,825 detections, a net increase of **6,722**. Only 11 V3 records are non-bird labels, so its new non-bird classes explain **0.16% of the net increase**, not the overall 3.38× difference.

| Species | V2.4 raw | V3 raw | Extra V3 detections | V3 / V2.4 | Share of net total increase (%) |
| --- | --- | --- | --- | --- | --- |
| Turdus pilaris | 564 | 1638 | 1074 | 2.90 | 15.98 |
| Pyrrhula pyrrhula | 326 | 1267 | 941 | 3.89 | 14.00 |
| Corvus corax | 54 | 607 | 553 | 11.24 | 8.23 |
| Turdus merula | 8 | 494 | 486 | 61.75 | 7.23 |
| Spinus spinus | 251 | 666 | 415 | 2.65 | 6.17 |
| Fringilla coelebs | 87 | 484 | 397 | 5.56 | 5.91 |
| Parus major | 1 | 395 | 394 | 395.00 | 5.86 |
| Cyanistes caeruleus | 23 | 305 | 282 | 13.26 | 4.20 |
| Poecile montanus | 103 | 363 | 260 | 3.52 | 3.87 |
| Erithacus rubecula | 31 | 231 | 200 | 7.45 | 2.98 |
| Strix aluco | 131 | 305 | 174 | 2.33 | 2.59 |
| Regulus regulus | 37 | 206 | 169 | 5.57 | 2.51 |
| Garrulus glandarius | 83 | 243 | 160 | 2.93 | 2.38 |
| Chloris chloris | 38 | 197 | 159 | 5.18 | 2.37 |
| Aegithalos caudatus | 58 | 202 | 144 | 3.48 | 2.14 |
| Acanthis flammea | 55 | 178 | 123 | 3.24 | 1.83 |
| Fringilla montifringilla | 71 | 171 | 100 | 2.41 | 1.49 |
| Carduelis carduelis | 25 | 91 | 66 | 3.64 | 0.98 |
| Certhia familiaris | 85 | 142 | 57 | 1.67 | 0.85 |
| Bombycilla garrulus | 24 | 81 | 57 | 3.38 | 0.85 |
| Turdus philomelos | 6 | 63 | 57 | 10.50 | 0.85 |
| Turdus iliacus | 111 | 159 | 48 | 1.43 | 0.71 |
| Loxia curvirostra | 0 | 43 | 43 | — | 0.64 |
| Anthus pratensis | 0 | 33 | 33 | — | 0.49 |
| Anser albifrons | 183 | 214 | 31 | 1.17 | 0.46 |
| Periparus ater | 8 | 35 | 27 | 4.38 | 0.40 |
| Sitta europaea | 31 | 58 | 27 | 1.87 | 0.40 |
| Prunella modularis | 49 | 69 | 20 | 1.41 | 0.30 |
| Coccothraustes coccothraustes | 26 | 45 | 19 | 1.73 | 0.28 |
| Troglodytes troglodytes | 6 | 23 | 17 | 3.83 | 0.25 |
| Phylloscopus collybita | 12 | 28 | 16 | 2.33 | 0.24 |
| Turdus viscivorus | 2 | 17 | 15 | 8.50 | 0.22 |
| Emberiza schoeniclus | 3 | 18 | 15 | 6.00 | 0.22 |
| Ardea cinerea | 24 | 37 | 13 | 1.54 | 0.19 |
| Botaurus stellaris | 18 | 31 | 13 | 1.72 | 0.19 |
| Anser serrirostris | 0 | 11 | 11 | — | 0.16 |
| Anser anser | 4 | 13 | 9 | 3.25 | 0.13 |
| Dryobates minor | 2 | 10 | 8 | 5.00 | 0.12 |
| Tetrastes bonasia | 5 | 13 | 8 | 2.60 | 0.12 |
| Dendrocopos leucotos | 19 | 26 | 7 | 1.37 | 0.10 |
| Botaurus minutus | 0 | 6 | 6 | — | 0.09 |
| Dendrocopos major | 0 | 6 | 6 | — | 0.09 |
| Pica pica | 91 | 97 | 6 | 1.07 | 0.09 |
| Motacilla alba | 6 | 12 | 6 | 2.00 | 0.09 |
| Anthus cervinus | 0 | 5 | 5 | — | 0.07 |
| Strix uralensis | 0 | 4 | 4 | — | 0.06 |
| Chroicocephalus ridibundus | 1 | 4 | 3 | 4.00 | 0.04 |
| Alauda arvensis | 0 | 2 | 2 | — | 0.03 |
| Linaria cannabina | 2 | 4 | 2 | 2.00 | 0.03 |
| Emberiza citrinella | 0 | 2 | 2 | — | 0.03 |
| Lyrurus tetrix | 0 | 2 | 2 | — | 0.03 |
| Nucifraga caryocatactes | 0 | 1 | 1 | — | 0.01 |
| Corvus cornix | 0 | 1 | 1 | — | 0.01 |
| Coloeus monedula | 0 | 1 | 1 | — | 0.01 |
| Gallinago gallinago | 1 | 1 | 0 | 1.00 | 0.00 |
| Buteo buteo | 14 | 12 | -2 | 0.86 | -0.03 |
| Glaucidium passerinum | 2 | 0 | -2 | 0.00 | -0.03 |
| Anas platyrhynchos | 16 | 8 | -8 | 0.50 | -0.12 |

**Fieldfare (+1,074) and Eurasian Bullfinch (+941) together account for 30.0% of the net increase.** Adding Common Raven (+553), Common Blackbird (+486), Eurasian Siskin (+415) and Common Chaffinch (+397) brings the contribution of these six species to **57.5%**. Most extra output therefore comes from more detections of species already represented in V2.4, rather than simply adding newly confirmed species.

### More repeated detections, broader interval coverage, or errors?

A detection is a model output, not a separate bird or necessarily a separate vocalisation. Comparing raw counts with occupied 10-minute bins distinguishes a concentration of repeated detections from broader recorded temporal coverage:

| Species | Raw V2.4 → V3 | All bins V2.4 → V3 | Detections per occupied bin V2.4 | Detections per occupied bin V3 |
| --- | --- | --- | --- | --- |
| Turdus pilaris | 564 → 1638 | 141 → 216 | 4.00 | 7.58 |
| Pyrrhula pyrrhula | 326 → 1267 | 80 → 144 | 4.08 | 8.80 |
| Corvus corax | 54 → 607 | 19 → 109 | 2.84 | 5.57 |
| Turdus merula | 8 → 494 | 5 → 105 | 1.60 | 4.70 |
| Spinus spinus | 251 → 666 | 91 → 165 | 2.76 | 4.04 |
| Fringilla coelebs | 87 → 484 | 32 → 96 | 2.72 | 5.04 |

For Fieldfare and Bullfinch, both the number of occupied bins and the number of detections per occupied bin increased. Common Blackbird has a particularly large increase in temporal coverage: **5 to 105 raw bins**, with **5 to 40 TP-confirmed bins**. Raven's raw bins increased from **19 to 109**, but TP bins remained 19 and the reviewed FP proportion rose.

These results show **where the increase comes from**, but the exports cannot establish its acoustic mechanism. Detecting weaker or more distant calls, repeated recognition within a calling bout, changed confidence scores around the 0.60 cutoff, and additional misclassifications are possible explanations. Two separate audio chains and sensitivity 1.25 versus 1.0 are additional configuration differences. Distinguishing these explanations requires reviewing matched audio events or running both models on the same recordings. No claim that V3 specifically detected quieter calls is made from these tables alone.

## Ten-minute intervals

The analysis uses clock-aligned bins (00–09:59, 10–19:59, etc.). Each species is counted once per bin. Detailed interval comparisons use the **union of species with at least one TP in either model** and include all detections for those species, including FP and unreviewed records. Edge bins are partial. A bin with at least one TP is confirmed even if it also contains FP.

| Metric | V2.4 | V3 |
| --- | --- | --- |
| All species × bins | 816 | 1871 |
| Species × bins with ≥1 TP | 509 | 860 |


![All intervals and TP intervals for each confirmed species](https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/main/docs/model-comparison/species-intervals.svg)

V3 has **69.0% more TP-confirmed species × bins**. In the paired TP comparison, 307 bins were confirmed in both models, 202 only in V2.4, and 553 only in V3. These exclusive counts describe TP marks, not automatically missed sounds. For all detection bins, including unreviewed ones, overlap is 696, with 120 only in V2.4 and 1,175 only in V3.

### Complete per-species results

FP percentages use only reviewed records; raw detections and all bins include all review statuses. Missing FP percentages mean no reviewed records.

| Species | Model | Raw detections | TP | FP | FP (%) | All bins | TP bins |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Acanthis flammea | v2.4 | 55 | 55 | 0 | 0.00 | 22 | 22 |
| Aegithalos caudatus | v2.4 | 58 | 41 | 0 | 0.00 | 11 | 9 |
| Alauda arvensis | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Anas platyrhynchos | v2.4 | 16 | 16 | 0 | 0.00 | 6 | 6 |
| Anser albifrons | v2.4 | 183 | 7 | 1 | 12.50 | 18 | 2 |
| Anser anser | v2.4 | 4 | 4 | 0 | 0.00 | 4 | 4 |
| Anser serrirostris | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Anthus cervinus | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Anthus pratensis | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Ardea cinerea | v2.4 | 24 | 21 | 2 | 8.70 | 10 | 7 |
| Bombycilla garrulus | v2.4 | 24 | 23 | 0 | 0.00 | 13 | 13 |
| Botaurus minutus | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Botaurus stellaris | v2.4 | 18 | 13 | 3 | 18.75 | 10 | 7 |
| Buteo buteo | v2.4 | 14 | 13 | 1 | 7.14 | 4 | 3 |
| Carduelis carduelis | v2.4 | 25 | 25 | 0 | 0.00 | 15 | 15 |
| Certhia familiaris | v2.4 | 85 | 40 | 2 | 4.76 | 8 | 3 |
| Chloris chloris | v2.4 | 38 | 27 | 0 | 0.00 | 4 | 4 |
| Chroicocephalus ridibundus | v2.4 | 1 | 1 | 0 | 0.00 | 1 | 1 |
| Coccothraustes coccothraustes | v2.4 | 26 | 22 | 4 | 15.38 | 12 | 8 |
| Coloeus monedula | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Corvus corax | v2.4 | 54 | 53 | 0 | 0.00 | 19 | 19 |
| Corvus cornix | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Cyanistes caeruleus | v2.4 | 23 | 21 | 0 | 0.00 | 10 | 9 |
| Dendrocopos leucotos | v2.4 | 19 | 17 | 0 | 0.00 | 1 | 1 |
| Dendrocopos major | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Dryobates minor | v2.4 | 2 | 1 | 1 | 50.00 | 2 | 1 |
| Emberiza citrinella | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Emberiza schoeniclus | v2.4 | 3 | 3 | 0 | 0.00 | 3 | 3 |
| Erithacus rubecula | v2.4 | 31 | 31 | 0 | 0.00 | 4 | 4 |
| Fringilla coelebs | v2.4 | 87 | 66 | 4 | 5.71 | 32 | 23 |
| Fringilla montifringilla | v2.4 | 71 | 69 | 2 | 2.82 | 35 | 34 |
| Gallinago gallinago | v2.4 | 1 | 1 | 0 | 0.00 | 1 | 1 |
| Garrulus glandarius | v2.4 | 83 | 61 | 0 | 0.00 | 29 | 25 |
| Glaucidium passerinum | v2.4 | 2 | 1 | 1 | 50.00 | 2 | 1 |
| Linaria cannabina | v2.4 | 2 | 2 | 0 | 0.00 | 1 | 1 |
| Loxia curvirostra | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Lyrurus tetrix | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Motacilla alba | v2.4 | 6 | 6 | 0 | 0.00 | 3 | 3 |
| Nucifraga caryocatactes | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Parus major | v2.4 | 1 | 0 | 1 | 100.00 | 1 | 0 |
| Periparus ater | v2.4 | 8 | 8 | 0 | 0.00 | 6 | 6 |
| Phylloscopus collybita | v2.4 | 12 | 12 | 0 | 0.00 | 7 | 7 |
| Pica pica | v2.4 | 91 | 78 | 0 | 0.00 | 23 | 16 |
| Poecile montanus | v2.4 | 103 | 59 | 0 | 0.00 | 35 | 21 |
| Prunella modularis | v2.4 | 49 | 35 | 0 | 0.00 | 26 | 21 |
| Pyrrhula pyrrhula | v2.4 | 326 | 118 | 0 | 0.00 | 80 | 43 |
| Regulus regulus | v2.4 | 37 | 30 | 0 | 0.00 | 14 | 14 |
| Sitta europaea | v2.4 | 31 | 16 | 0 | 0.00 | 1 | 1 |
| Spinus spinus | v2.4 | 251 | 85 | 0 | 0.00 | 91 | 39 |
| Strix aluco | v2.4 | 131 | 61 | 17 | 21.79 | 27 | 13 |
| Strix uralensis | v2.4 | 0 | 0 | 0 | — | 0 | 0 |
| Tetrastes bonasia | v2.4 | 5 | 4 | 1 | 20.00 | 5 | 4 |
| Troglodytes troglodytes | v2.4 | 6 | 6 | 0 | 0.00 | 1 | 1 |
| Turdus iliacus | v2.4 | 111 | 65 | 19 | 22.62 | 66 | 37 |
| Turdus merula | v2.4 | 8 | 8 | 0 | 0.00 | 5 | 5 |
| Turdus philomelos | v2.4 | 6 | 5 | 1 | 16.67 | 6 | 5 |
| Turdus pilaris | v2.4 | 564 | 145 | 0 | 0.00 | 141 | 46 |
| Turdus viscivorus | v2.4 | 2 | 2 | 0 | 0.00 | 1 | 1 |
| Acanthis flammea | v3 | 178 | 126 | 8 | 5.97 | 44 | 34 |
| Aegithalos caudatus | v3 | 202 | 62 | 0 | 0.00 | 18 | 10 |
| Alauda arvensis | v3 | 2 | 2 | 0 | 0.00 | 1 | 1 |
| Anas platyrhynchos | v3 | 8 | 8 | 0 | 0.00 | 5 | 5 |
| Anser albifrons | v3 | 214 | 43 | 0 | 0.00 | 27 | 8 |
| Anser anser | v3 | 13 | 3 | 10 | 76.92 | 5 | 3 |
| Anser serrirostris | v3 | 11 | 8 | 0 | 0.00 | 5 | 4 |
| Anthus cervinus | v3 | 5 | 5 | 0 | 0.00 | 5 | 5 |
| Anthus pratensis | v3 | 33 | 29 | 2 | 6.45 | 23 | 21 |
| Ardea cinerea | v3 | 37 | 34 | 3 | 8.11 | 12 | 10 |
| Bombycilla garrulus | v3 | 81 | 63 | 3 | 4.55 | 22 | 14 |
| Botaurus minutus | v3 | 6 | 2 | 3 | 60.00 | 5 | 1 |
| Botaurus stellaris | v3 | 31 | 17 | 3 | 15.00 | 11 | 7 |
| Buteo buteo | v3 | 12 | 4 | 1 | 20.00 | 3 | 1 |
| Carduelis carduelis | v3 | 91 | 69 | 0 | 0.00 | 38 | 34 |
| Certhia familiaris | v3 | 142 | 25 | 3 | 10.71 | 12 | 7 |
| Chloris chloris | v3 | 197 | 72 | 3 | 4.00 | 25 | 14 |
| Chroicocephalus ridibundus | v3 | 4 | 3 | 0 | 0.00 | 1 | 1 |
| Coccothraustes coccothraustes | v3 | 45 | 39 | 3 | 7.14 | 19 | 14 |
| Coloeus monedula | v3 | 1 | 1 | 0 | 0.00 | 1 | 1 |
| Corvus corax | v3 | 607 | 129 | 32 | 19.88 | 109 | 19 |
| Corvus cornix | v3 | 1 | 1 | 0 | 0.00 | 1 | 1 |
| Cyanistes caeruleus | v3 | 305 | 77 | 0 | 0.00 | 64 | 33 |
| Dendrocopos leucotos | v3 | 26 | 21 | 0 | 0.00 | 2 | 2 |
| Dendrocopos major | v3 | 6 | 3 | 2 | 40.00 | 5 | 3 |
| Dryobates minor | v3 | 10 | 9 | 1 | 10.00 | 5 | 5 |
| Emberiza citrinella | v3 | 2 | 2 | 0 | 0.00 | 2 | 2 |
| Emberiza schoeniclus | v3 | 18 | 16 | 0 | 0.00 | 13 | 11 |
| Erithacus rubecula | v3 | 231 | 58 | 1 | 1.69 | 38 | 18 |
| Fringilla coelebs | v3 | 484 | 73 | 17 | 18.89 | 96 | 25 |
| Fringilla montifringilla | v3 | 171 | 131 | 10 | 7.09 | 64 | 50 |
| Gallinago gallinago | v3 | 1 | 1 | 0 | 0.00 | 1 | 1 |
| Garrulus glandarius | v3 | 243 | 118 | 1 | 0.84 | 62 | 36 |
| Glaucidium passerinum | v3 | 0 | 0 | 0 | — | 0 | 0 |
| Linaria cannabina | v3 | 4 | 4 | 0 | 0.00 | 1 | 1 |
| Loxia curvirostra | v3 | 43 | 22 | 15 | 40.54 | 22 | 8 |
| Lyrurus tetrix | v3 | 2 | 1 | 1 | 50.00 | 2 | 1 |
| Motacilla alba | v3 | 12 | 12 | 0 | 0.00 | 7 | 7 |
| Nucifraga caryocatactes | v3 | 1 | 1 | 0 | 0.00 | 1 | 1 |
| Parus major | v3 | 395 | 91 | 0 | 0.00 | 88 | 45 |
| Periparus ater | v3 | 35 | 32 | 0 | 0.00 | 17 | 14 |
| Phylloscopus collybita | v3 | 28 | 26 | 0 | 0.00 | 9 | 8 |
| Pica pica | v3 | 97 | 70 | 0 | 0.00 | 21 | 17 |
| Poecile montanus | v3 | 363 | 88 | 0 | 0.00 | 57 | 25 |
| Prunella modularis | v3 | 69 | 61 | 0 | 0.00 | 29 | 29 |
| Pyrrhula pyrrhula | v3 | 1267 | 72 | 0 | 0.00 | 144 | 33 |
| Regulus regulus | v3 | 206 | 85 | 1 | 1.16 | 37 | 25 |
| Sitta europaea | v3 | 58 | 31 | 0 | 0.00 | 10 | 7 |
| Spinus spinus | v3 | 666 | 89 | 0 | 0.00 | 165 | 49 |
| Strix aluco | v3 | 305 | 160 | 25 | 13.51 | 64 | 25 |
| Strix uralensis | v3 | 4 | 2 | 2 | 50.00 | 4 | 2 |
| Tetrastes bonasia | v3 | 13 | 13 | 0 | 0.00 | 7 | 7 |
| Troglodytes troglodytes | v3 | 23 | 23 | 0 | 0.00 | 3 | 3 |
| Turdus iliacus | v3 | 159 | 45 | 1 | 2.17 | 64 | 29 |
| Turdus merula | v3 | 494 | 97 | 0 | 0.00 | 105 | 40 |
| Turdus philomelos | v3 | 63 | 41 | 1 | 2.38 | 38 | 25 |
| Turdus pilaris | v3 | 1638 | 86 | 1 | 1.15 | 216 | 54 |
| Turdus viscivorus | v3 | 17 | 5 | 10 | 66.67 | 16 | 4 |

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

- V3 produced **3.38× as many raw detections and 13 more TP-confirmed bird species** in this deployment. The overlap was 43 confirmed species, with 1 confirmed only by V2.4 and 14 only by V3.
- **Most extra raw output comes from more detections of familiar species.** Fieldfare and Bullfinch alone contribute 30.0% of the total increase; six species contribute 57.5%. Non-bird labels contribute only 11 records.
- **Changes in the reviewed FP proportion differ by species.** Redwing and Tawny Owl improved; Raven and Chaffinch had higher error proportions. A single overall percentage conceals these differences.
- **Raw output growth and useful temporal coverage are different.** Blackbird gained many confirmed bins; Raven produced much more output without increasing its number of TP bins in the current annotations.
- The proportion of records manually reviewed and the number remaining unreviewed are not used to compare models: they reflect review effort. Reviewed counts accompany FP percentages to show the denominator and identify small samples.
- This is one location, one autumn period, separate recording chains and different sensitivity settings. Full recall and the causes of extra detections cannot be established from these exports. A same-audio comparison with a predefined review sample is the next step for testing these explanations.

I would welcome comparable field results, particularly species-level changes in FP/(FP+TP) and examples explaining extra V3 detections. Please include the model build, sensitivity, confidence threshold and filtering settings.
