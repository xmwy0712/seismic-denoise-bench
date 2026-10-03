# A Pre-Registered Benchmark and Complementarity Analysis of Seismic Denoising Methods: Diagnosing Selection Failure in Method Pairing

**Zhang Tao**

School of Earth Sciences and Engineering, Nanjing University, Nanjing, China

**Corresponding author**: Zhang Tao (251830064@smail.nju.edu.cn)

---

## Abstract

**Background and problem.** Seismic denoising offers a large and growing catalogue of methods, yet cross-method comparability has long been lacking: methods are reported on different data, against different metrics and under different tuning budgets, so a reader cannot tell whether one method is genuinely better than another.

**Methods.** We establish a first pre-registered denoising benchmark, restricted to this dataset, this rule set and a controlled setting, and use it as a bench to test, under control, the hypothesis that complementarity drives fusion. Criteria, configurations, random seeds and evaluation panels are frozen before any method output is observed, and the selection rule for the primary pair is fixed in advance; the evaluation framework comprises signal-to-noise ratio gain, ground-truth event-window leakage, coherent-noise attenuation and event-level metrics. On this basis we define three cross-method complementarity measures — error orthogonality, local complementarity and band complementarity — and implement a time–frequency weighted fusion under the pre-registered rule.

**Data.** The synthetic part covers two velocity models × three noise types × three intensity levels × three main frequencies with five independent seeds each, giving 54 configurations and 270 observations; the field part uses three frozen panels.

**Results.** The pre-registered machinery was executed in full, and its output is an interpretable failure sample.

**First, the failure.** The primary pair selected by the pre-registered rule is the lowest-gain pair of the ten (0.0588 dB, with the other nine all at or above 0.42 dB). Meanwhile seven of the ten exceed the best fixed single method (0.9482 dB), and those seven are exactly the pairs containing either F-K filtering or low-rank approximation.

**Second, the mechanism** (a mechanistic account; no discriminative experiment was designed). The candidate measure M2 is treated as a pathological specimen: zero inflation and the pooled-threshold construction produce, in interaction with pooling across layers, a reverse-selection trap. Changing the threshold from cross-layer pooling to within-noise-type pooling drops the primary pair's score from 0.500000 to 0.000000 and promotes the pre-registered robustness comparator to first place; the caliber dependency is unresolved and both calibers are reported, and no re-selection is made on that basis. The division of labour across noise types accounts for every winner and loser. An ablation that replaces the weighting and suppression machinery wholesale with equal weights changes the ten-pair ΔSNR median by no more than 0.0252 dB, establishing that equations (8)–(10) carry no measurable contribution on this data.

**Third, the decision boundary.** Selecting by noise type on physical grounds hits the per-observation best single method in 89.3% of observations in-sample and 81.5% on new seeds, with a median of 5.9840 dB and a mean shortfall against the oracle of 0.27 dB and 0.28 dB (means). The route remains exploratory; the magnitude in the linear coherent layer depends on the seed (ratio 0.453, hit rate falling from 87.8% to 63.3%), and the out-of-sample criterion is only partially met.

**Fourth, an external stress test.** The field data serve as an exploratory external stress test: across the two computable panels the three pairings order inconsistently on the four raw indicators, and the third panel is not computable.

These extensions are all post hoc and exploratory (pairs are not independent; magnitudes vary with the gain definition) and do not alter the pre-registered conclusions.

**Conclusion.** Using a first pre-registered seismic denoising benchmark as a bench, we carry out a controlled test of one hypothesis together with a diagnosis of its pathology. The complementarity-drives-fusion hypothesis was executed in full and was not supported: the rule selected the lowest-gain pair of the ten. The failure of the candidate measure M2 is located as a reproducible pathology — a reverse-selection trap induced by the pooled-threshold construction. The fusion algorithm is dissected into mechanism redundancy and spurious complexity, since the gain comes entirely from arithmetic averaging while the adaptive weighting carries no measurable contribution. The decision boundary follows from the physical division of labour: a 89.3% / 81.5% hit rate against the per-observation best single method. What was not shown to work is the pair-selection rule itself; what was shown to be usable is the benchmark protocol and the diagnostic path for measure pathology. All selection-by-type conclusions are labelled post hoc and exploratory, and their promotion to a main claim would require three further ingredients: new configurations, mixed noise, and blind classification.

## Keywords

Seismic denoising; pre-registered benchmark; method comparability; complementarity measures; time–frequency fusion; reproducibility

---
