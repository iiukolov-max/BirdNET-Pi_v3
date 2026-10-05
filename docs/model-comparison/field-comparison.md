# BirdNET v2.4 vs v3: paired field comparison on Raspberry Pi Zero 2 W

Two identical Raspberry Pi Zero 2 W devices, with Sound Blaster G3 sound cards and identical microphones, ran side by side at one location from 27 September to 2 October 2026. A subset of their detections was manually marked TP or FP.

**V3 produced 3.38× as many raw detections and 57 TP-confirmed bird species versus 44 for V2.4. The gains were uneven: some species had a lower reviewed FP proportion, others a higher one.**

## 1. Overall output and species overlap

| Compared quantity | V2.4 | V3 |
|---|---:|---:|
| Raw detections, all labels | 2,825 | 9,547 |
| Bird species with at least one reviewed TP | 44 | 57 |
| Bird species with FP but no TP | 31 | 45 |
| Occupied species × 10-minute bins, confirmed species list | 816 | 1,871 |
| Species × 10-minute bins with at least one TP | 509 | 860 |

![Raw detections and shared/exclusive TP and FP-only bird species](https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/main/docs/model-comparison/field-comparison.svg)

Raw detection counts include all review statuses. The confirmed interval comparison uses the **union of the 58 bird species with at least one TP in either model**. FP-only species status is assigned separately for each model; a species may be FP-only in one model and confirmed in the other.

### Which species were confirmed?

![Complete TP species lists: shared, V2.4 only, V3 only](https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/main/docs/model-comparison/tp-species-overlap.svg)

There were **43 shared TP-confirmed species**, **1 confirmed only by V2.4** and **14 confirmed only by V3**. For example, Great Tit has one FP and no TP in V2.4, versus 91 TP and no marked FP in V3. Eurasian Pygmy Owl was confirmed only by V2.4. "Confirmed only" refers to the available annotations, not automatically a proven false negative in the other model.

## 2. Where the extra raw detections come from

V3 generated **6,722 additional detections**. The diagram shows the ten largest species contributions, with every other label combined into a net remainder.

![Contributions to the net increase in V3 raw detections](https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/main/docs/model-comparison/raw-detection-gains.svg)

**Fieldfare (+1,074) and Eurasian Bullfinch (+941) account for 30.0% of the net increase.** Adding Common Raven, Common Blackbird, Eurasian Siskin and Common Chaffinch brings the contribution to **57.5%**. All six species were TP-confirmed by both models: much of V3's extra output comes from more detections of familiar species, not only an expanded species list.

V3 generated just **11 non-bird records**, accounting for **0.16% of the net increase**. Its extra animal classes therefore barely explain the total detection growth in this experiment.

### More repetitions or broader temporal coverage?

This comparison follows the **same eight species with the largest raw gains** across three quantities: detections, occupied bins and bins containing TP. Each species is counted once per clock-aligned 10-minute bin.

![Raw detections, occupied bins and TP bins for the eight largest species gains](https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/main/docs/model-comparison/detection-interval-comparison.svg)

- **Common Blackbird:** raw detections rose from **8 to 494**, all occupied bins from **5 to 105**, and TP bins from **5 to 40**. The increase includes broader confirmed temporal coverage.
- **Common Raven:** raw detections rose from **54 to 607** and occupied bins from **19 to 109**, but TP bins remained **19 in both models**. Extra output has not translated into more confirmed bins in the current annotations.
- **Fieldfare:** raw detections rose from **564 to 1,638**, but all bins increased from **141 to 216**. Detections per occupied bin rose from **4.00 to 7.58**: both broader output coverage and more repeated detections within bins contributed.
- **Eurasian Bullfinch:** raw detections rose from **326 to 1,267** and all bins from **80 to 144**; detections per occupied bin rose from **4.08 to 8.80**.

These calculations locate the increase, but do not establish its acoustic cause. Weaker or more distant calls, repeated recognition within a calling bout, changed confidence values around the 0.60 cutoff, and misclassifications are possible explanations. Separating these requires matched audio review or running both models on identical recordings. A raw detection is not a separate bird or necessarily a separate vocalisation.

## 3. How the reviewed FP proportion changed by species

The compared quantity is **FP / (FP + TP) × 100%**, excluding every empty review mark. The proportion of records manually reviewed is not compared: it measures review effort, not model performance.

The diagram includes **every species with a changed FP proportion and at least 10 reviewed detections in each model**. This cutoff limits the influence of one- or two-record percentages; it is not a guarantee of statistical precision. Blue and orange points show the two models, and the displayed denominators are V2.4 / V3 reviewed counts. Unchanged values are omitted from this change-focused diagram.

![Paired FP proportions for species with at least ten reviewed detections per model](https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/main/docs/model-comparison/species-error-comparison.svg)

| Species | V2.4 FP / reviewed | V3 FP / reviewed | Change in FP proportion |
|---|---:|---:|---:|
| Redwing | 19/84 = 22.62% | 1/46 = 2.17% | −20.45 percentage points |
| Tawny Owl | 17/78 = 21.79% | 25/185 = 13.51% | −8.28 percentage points |
| Hawfinch | 4/26 = 15.38% | 3/42 = 7.14% | −8.24 percentage points |
| Common Chaffinch | 4/70 = 5.71% | 17/90 = 18.89% | +13.17 percentage points |
| Common Raven | 0/53 = 0% | 32/161 = 19.88% | +19.88 percentage points |

**Tawny Owl illustrates why absolute FP counts can mislead:** FP increased from 17 to 25, but TP rose from 61 to 160, so the FP proportion decreased. Redwing likewise combines more raw detections (111 to 159) with a lower reviewed error proportion.

For Common Blackbird, Bullfinch and Siskin, both models had zero marked FP despite substantial raw output growth. This supports useful additional detections in the reviewed examples; it does not certify all unreviewed output.

Large percentage differences based on very small samples are not highlighted as reliable gains. Great Tit has only one reviewed V2.4 detection; Grey Goose has four and Mistle Thrush two. Their raw counts and species status remain in the comparison, but species-level error estimates from such small samples are unstable.

These percentages describe the reviewed sample and can depend on which recordings were selected for review. Empty-record exclusion does not remove that selection effect. A lower error proportion is not a measure of recall.

## 4. Agreement between models in time

For each species, matching clock-aligned 10-minute bins separates common output from output found in only one model.

| Bin overlap category | All detection bins | Bins containing reviewed TP |
|---|---:|---:|
| Shared between models | 696 | 307 |
| V2.4 only | 120 | 202 |
| V3 only | 1,175 | 553 |

Both columns use the same union of confirmed species. "TP only" means no TP annotation in the other model for that species/bin, not automatically a missed sound. The totals count **species × bins**, not unique time bins. A bin can contain both TP and FP and still be TP-confirmed.

## 5. Confidence threshold trade-off

Thresholds are applied to detections **before** bin aggregation. The confirmed species list is fixed across thresholds; FP percentages use reviewed records only.

![Paired threshold curves for TP bins and reviewed FP proportions](https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/main/docs/model-comparison/threshold-comparison.svg)

| Minimum confidence | TP bins V2.4 → V3 | Reviewed FP proportion V2.4 → V3 |
|---|---:|---:|
| 0.60 | 509 → 860 | 4.18% → 6.33% |
| 0.70 | 394 → 759 | 3.46% → 3.75% |
| 0.80 | 272 → 585 | 2.30% → 2.16% |
| 0.90 | 151 → 336 | 1.90% → 1.13% |
| 0.95 | 70 → 84 | 1.43% → 0% |

At **0.80**, V3 retains **585 TP bins versus 272**, with similar reviewed FP proportions. At **0.90**, it retains **336 versus 151**, with a lower reviewed FP proportion. This is a promising trade-off in the current sample, not an independently validated universal threshold. Confidence is not calibrated between models. Zero marked FP at 0.95 means zero in that reviewed subset, not error-free output.

## 6. FP-only species: shared and exclusive lists

![Complete FP-only bird species lists: shared, V2.4 only, V3 only](https://raw.githubusercontent.com/iiukolov-max/BirdNET-Pi_v3/main/docs/model-comparison/fp-species-overlap.svg)

**18 FP-only species were shared**, **13 occurred only in the V2.4 FP-only list**, and **27 only in the V3 list**. These categories use reviewed records and bird labels only. Remaining unreviewed records do not prove every detection of a listed species false. Species with no reviews at all are not labelled erroneous.

The full list with FP counts and **maximum confidence among FP detections** is available as [a downloadable comparison table](fp-only-species.csv), keeping the main post readable.

## 7. Conditions and limits of this comparison

The included interval is **2026-09-27 12:38:04 through 2026-10-02 10:44:02 inclusive**, using export timestamps. The devices started together; the first V3 detection provides the start boundary and the latest V3 detection provides the end. Older and later V2.4 records are excluded.

Both used minimum confidence **0.60** and overlap **0**. Sensitivity was **1.25 for V2.4 and 1.0 for V3**. The export identifies V3, but does not record its exact model filename/checksum; that deployment identity should be confirmed before associating these results with a specific preview build. Scientific names are retained as exported.

This is one location, one autumn period and two separate audio chains, not an identical-audio benchmark. Uptime was not reconstructed from recording logs; silence in the detection export is not treated as downtime. Edge bins are partial. Neighbouring detections and bins can represent one calling bout, so they are not independent experimental replicates. Full recall cannot be calculated because sounds missed by both models are absent from the exports.

The practical finding is **more confirmed species and broader confirmed temporal coverage with V3, alongside species-specific improvements and regressions in reviewed error proportion**. Matched audio review is needed to determine why V3 generates more output and whether it detects weaker calls more successfully.

### Exact numbers for further analysis

- [Per-species comparison data](species-results.csv)
- [Paired interval overlap data](paired-intervals.csv)
- [FP-only species and maximum FP confidence](fp-only-species.csv)

I would welcome comparable field results, especially species-level FP/(FP+TP) changes and matched audio examples explaining extra V3 detections. Please include model build, sensitivity, confidence threshold and filtering settings.
