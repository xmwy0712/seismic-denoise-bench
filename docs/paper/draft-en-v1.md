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
## 1 Introduction

### 1.1 The problem

Seismic denoising spans a wide range of methods, covering filtering, transform-domain thresholding, decomposition, low-rank approximation and deep learning. Yet cross-method comparability has long been lacking: different studies report results on different data, against different metrics and under different tuning budgets, so a reader cannot judge whether one method is genuinely better than another. This difficulty is not an engineering detail but a structural problem of the evaluation system: when the criteria, the data splits and the tuning budget can all be adjusted after the fact, no method's advantage can be independently tested.

### 1.2 What the existing literature does not settle

Existing multi-method comparisons typically share two features. First, the method set and the evaluation metrics are fixed after the results are visible. Second, the comparison covers only a handful of methods and lacks any characterization of the **information relationship** between them. The former makes selection effects hard to rule out; the latter leaves the question of why several methods would be complementary without a quantifiable entry point. Reviews and benchmark-style work cover methods more completely, but they too rarely fix criteria and selection rules before the results.

In adjacent directions, recent work has compared learned denoising methods in a controlled way across the time domain, the time–frequency domain and hybrid domains [5]; a comparative analysis of convolutional neural networks for seismic noise attenuation [6], and a multi-scale feature-interaction enhancement network for desert data [7], likewise report comparisons dominated by a single method. Together these show that multi-method comparison has reached a certain scale, while its method sets and evaluation metrics are still largely fixed after results are visible.

### 1.3 Contributions

This paper makes three contributions.

First, **a pre-registered benchmark protocol**: criteria, configurations, random seeds and evaluation panels are frozen before any method output is observed, and the selection rule for the primary pair is fixed in advance, removing the interference of tuning and selective reporting with the conclusions. This protocol is the bench of this paper.

Second, **a measure pathology case**: the candidate measure M2 (windowed local complementarity) is treated as a **pathological specimen**, and its two artifacts — **zero inflation** and the **pooled-threshold construction** — together with their interaction with **cross-layer pooling**, are diagnosed systematically. In the controlled setting this construction induces a **reverse-selection trap**: on the same data, a within-noise-type threshold selects a different pairing, namely the pre-registered robustness comparator, and the primary pair scores zero under that caliber. The diagnosis provides a reproducible instance of the gap between a high measure score and a measure that works.

Third, **quantifying where the gain comes from, and the decision boundary**: an ablation replaces the fusion weights and suppression machinery wholesale with equal averaging, changing the ten-pair ΔSNR median by no more than 0.0252 dB; on that basis equations (8)–(10) are judged to be **mechanism redundancy and spurious complexity**, since the gain comes solely from arithmetic averaging. At the same time, the physical division of labour yields a **tested upper bound** for selection by type — 89.3% hits on the per-observation best single method in-sample and 81.5% on new seeds — alongside **partial out-of-sample validation** (5.9840 dB, ratio 0.453), which together delineate the applicable boundary between blind fusion and decision by class. The positive result of the second-best comparator pairing and the negative result of the primary pair are given side by side in the same section; see Section 4.3.

### 1.4 Structure of the paper

Section 2 describes the synthetic data generation and the source of the field data; Section 3 presents the five baseline methods, the evaluation metrics, the complementarity measures, the fusion method and the evaluation protocol; Section 4 reports the synthetic benchmark, the complementarity and the fusion results; Section 5 discusses what the measure disagreement means, the mechanism by which fusion did not benefit, and the applicable boundary; Section 6 concludes.

---

## 2 Study area and data

### 2.1 Synthetic data

The synthetic data are driven by two velocity models: a horizontally layered model, and a model containing dipping, curved and faulted structure. The noise settings comprise three types: band-limited random noise, linear coherent interference, and dispersive surface waves. The parameter grid is 2 models × 3 noise types × 3 intensity levels × 3 main frequencies, with 5 independent random seeds per combination, giving 54 configurations and 270 observations. Noise intensity is reported externally in terms of the **measured input signal-to-noise ratio**; the amplitude ratio is used only to generate the realization. The values and the selection rationale for each dimension are given in the table below.

**Table 1** Model, noise and level definitions for the synthetic configurations

| Dimension | Values | Selection and notes |
| :--- | :--- | :--- |
| Velocity model | M1 horizontally layered; M2 with dipping, curved and faulted structure | Covers the two principal cases, layered and structural |
| Noise type | N1 band-limited random; N2 linear coherent interference; N3 dispersive surface wave | N2 is coherent interference with a controllable apparent velocity, introducing a predictable linear event across traces |
| Intensity level | L1 / L2 / L3 | N1 and N3 are generated at amplitude ratios 0.30 / 0.60 / 1.00, corresponding to measured input signal-to-noise ratios of 10.46 / 4.44 / 0.00 dB; N2 does not take an amplitude ratio, and its level is carried by the apparent-velocity slot, at 800 / 1500 / 3000 m/s |
| Main frequency | 15 / 25 / 40 Hz | Covers the low to mid frequency band |
| Random seeds | 5 independent seeds per combination | Separates between-observation variation from between-configuration differences |

### 2.2 Field data

The field data are taken from the public seismic surveys of the onshore–offshore freshwater systems of Martha's Vineyard and Nantucket, under a CC BY 4.0 licence; the citation is:

> Dugan, B. (2023). *Seismic and Hydrostratigraphic Characterization of the Onshore-Offshore Freshwater Systems of Martha's Vineyard and Nantucket, Massachusetts, USA: Field Survey Report* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.10407771

Three frozen panels from this dataset are used: FP1 (Nantucket survey area), and FP2 and FP3 (Martha's Vineyard survey area), covering two survey areas (Figure 1). The panels were chosen by ranking against a set of criteria frozen in advance, not on the basis of any denoising result. Under the **frozen threshold**, FP3 yields no event windows: this study **holds that threshold and does not relax it after the fact to backfill values**, and the way this boundary is recorded is described in Section 4.4.

![Figure 1 Preview of the three raw field panels](figures/fig1_field_panels.png)
**Figure 1** Preview of the three raw field panels. (a) FP1 (Nantucket survey area); (b) FP2 (Martha's Vineyard survey area); (c) FP3 (Martha's Vineyard survey area). The horizontal axis is trace number (dimensionless); the vertical axis is two-way travel time (ms); the colour scale is amplitude (dimensionless).

---

## 3 Methods

### 3.1 Baseline methods

Five deterministic denoising methods are selected, covering four required families of mechanism.

**Filtering.** F-K filtering exploits apparent-velocity differences in the frequency–wavenumber domain to suppress linear interference and dispersive surface waves. F-X deconvolution estimates the **predictable component** on the same frequency–space gather using a lateral prediction operator: it retains coherent events that are predictable along the trace direction and suppresses the **unpredictable** part, namely random noise and interference that cannot be extrapolated laterally; the idea derives from lateral-prediction noise attenuation [1].

**Transform-domain thresholding.** Wavelet thresholding separates signal from noise in the time–scale domain and is widely used to suppress coherent noise such as ground roll [2].

**Decomposition.** Damped multichannel singular spectrum analysis arranges multichannel data into a trajectory matrix and performs a low-rank reconstruction, and is used for 3D random-noise suppression [3].

**Low rank.** Empirical low-rank approximation constructs similar block matrices and imposes a low-rank constraint to attenuate noise [4].

All five implementations are deterministic maps and admit no random component. A cross-domain pretrained deep network was not included in the method set, because it would require changing the frozen evaluation environment; this is an explicit limitation in method coverage.

**Tuning policy.** All method parameters take the registry defaults, with no per-method tuning in this study. The reason is that per-method tuning would rest the comparison on each method's own optimum rather than on its default behaviour, which amounts to introducing a selection effect method by method. Parameters not fixed by the protocol are recorded as method-level defaults and frozen together with the configuration; if a change were needed, the registry would change first and the implementation second.

**Table 2** Key parameters and provenance for the baseline methods

| Method | Family | Key parameters (values) | Parameter provenance |
| :--- | :--- | :--- | :--- |
| F-K filtering | Filtering | apparent-velocity cut-off 800.0 m/s; band 5.0–80.0 Hz | the cut-off is a method-level default; the band comes from the frozen configuration |
| F-X deconvolution | Filtering | prediction order 4; band 5.0–80.0 Hz; ridge 1e-08 | order and ridge are method-level defaults; the band comes from the frozen configuration |
| Wavelet thresholding | Transform thresholding | wavelet db4; soft thresholding; threshold factor 1.0; levels automatic | all method-level defaults |
| Decomposition (multichannel SSA) | Decomposition | embedding dimension 64; number of components 8 | method-level defaults |
| Low rank (empirical low-rank approximation) | Low rank | rank automatic (energy fraction 0.95) | method-level defaults |

### 3.2 Evaluation metrics

**Signal-to-noise ratio gain.** With the clean record as $s$, the noisy input as $x$ and the method output as $y$, we define

$$
\Delta\mathrm{SNR} = 10\log_{10}\frac{\lVert x-s\rVert^{2}}{\lVert y-s\rVert^{2}} \qquad (1)
$$

in dB, where a higher value means more complete denoising. The metric describes error reduction in an overall energy sense.

**Ground-truth event-window leakage.** Let $\mathcal{W}$ be the set of ground-truth event windows; the leakage metric is defined as the relative error energy of the output within the event windows:

$$
L_{\mathrm{sig}} = \frac{\sum_{w\in\mathcal{W}}\lVert (y-s)\rVert_{w}^{2}}{\sum_{w\in\mathcal{W}}\lVert s\rVert_{w}^{2}} \qquad (2)
$$

in dimensionless ratio, where a lower value means better fidelity to the effective signal. This metric runs opposite to the signal-to-noise ratio gain: the former rewards reduction of the total error energy, while the latter penalises error within the windows where the effective signal lies. In denoising evaluation the two do not always move together: an operator may suppress background energy (raising the signal-to-noise ratio gain) while damaging effective reflection events (worsening the leakage metric). A single metric is therefore not sufficient to judge denoising quality, and this paper reports the overall gain and the fidelity metric together and considers them jointly.

**Coherent-noise attenuation.** Let $n_{c}$ be the known injected coherent noise and $P_{\mathcal{C}}$ the least-squares projection onto the subspace spanned by the injected-component basis; then

$$
\mathrm{CNA} = 10\log_{10}\frac{\lVert n_{c}\rVert^{2}}{\lVert P_{\mathcal{C}}(y-s)\rVert^{2}} \qquad (3)
$$

in dB, higher being better. Its scope must be stated explicitly: the projection subspace shares its origin with the injection parameters, so the metric measures suppression of **that injected component** and does not represent a universal assessment of arbitrary coherent noise.

**Event-level metrics.** Taking the analytic-signal envelope of both output and ground truth, we locate the envelope peak within the ground-truth event window and define the arrival-time error as the difference between the two peak positions:

$$
\Delta t_{\mathrm{event}} = \left| t_{\mathrm{peak}}(y) - t_{\mathrm{peak}}(s) \right| \qquad (4)
$$

in ms; we also compute the normalised within-window energy error $\left| E_{y}-E_{s}\right|/E_{s}$, reporting its median and maximum.

### 3.3 Complementarity measures

**Error orthogonality.** Let $e_{i}$ and $e_{j}$ be the error vectors of two methods on the same observation. Taking an absolute value hides the **direction** of the error correlation — anti-correlated error pairs benefit from averaging, whereas positively correlated ones do not — so we also define the form without the absolute value, as an analytical supplement:

$$
O_{ij} = 1 - \frac{\left|\langle e_{i}, e_{j}\rangle\right|}{\lVert e_{i}\rVert\,\lVert e_{j}\rVert}, \qquad
O^{\mathrm{s}}_{ij} = 1 - \frac{\langle e_{i}, e_{j}\rangle}{\lVert e_{i}\rVert\,\lVert e_{j}\rVert} \qquad (5)
$$

where $O^{\mathrm{s}}_{ij}$ has **range $[0,2]$**: a value of $0$ means the two errors are fully positively correlated (redundant), $1$ means uncorrelated, and $2$ means fully anti-correlated (complementary).

**Local complementarity.** For each window we compute the difference in within-window fidelity between the two methods and compare its magnitude against $1.5$ times the pooled interquartile range of that pair's differences:

$$
C_{ij} = \frac{\#\left\{ w : \left| D_{ij}(w) \right| > 1.5\,\mathrm{IQR}\!\left( D_{ij} \right) \right\}}{\#\left\{ w \right\}} \qquad (6)
$$

where $D_{ij}(w)$ is the difference in fidelity of the two methods on window $w$, and the $\mathrm{IQR}$ is pooled over the whole set of windows for that pair, so each pairing corresponds to a fixed threshold constant. The range is $[0,1]$.

**Band complementarity.** Dividing the error spectrum into five bands and normalising to probability distributions $p$ and $q$, we define

$$
B_{ij} = \frac{1}{2}\sum_{k} p_{k}\,\log_{2}\frac{p_{k}}{m_{k}}
+ \frac{1}{2}\sum_{k} q_{k}\,\log_{2}\frac{q_{k}}{m_{k}}, \qquad
m = \frac{p + q}{2} \qquad (7)
$$

that is, the base-2 Jensen–Shannon divergence between the two distributions, with range $[0,1]$. Both the pre-registration and the implementation use this form, and the measure does not enter pair selection.

**Pair-selection rule.** The primary pair is the one with the highest global median of $C_{ij}$ in descending order; ties are broken by a predetermined order. The rule was written into the evaluation configuration and frozen before any fusion result was visible.

**Table 3** Symbol table

| Symbol | Meaning | Unit or range |
| :--- | :--- | :--- |
| $s$ | clean record (ground truth) | amplitude (dimensionless) |
| $x$ | noisy input | amplitude (dimensionless) |
| $y$, $y_{i}$, $y_{j}$ | output of a method or of the fusion | amplitude (dimensionless) |
| $e_{i}$ | error of method $i$, $y_{i}-s$ | amplitude (dimensionless) |
| $\mathcal{W}$ | set of ground-truth event windows | — |
| $n_{c}$ | injected coherent-noise component | amplitude (dimensionless) |
| $\Delta\mathrm{SNR}$ | signal-to-noise ratio gain, equation (1) | dB |
| $L_{\mathrm{sig}}$ | ground-truth event-window leakage, equation (2) | dimensionless |
| $\mathrm{CNA}$ | coherent-noise attenuation, equation (3) | dB |
| $O_{ij}$, $O^{\mathrm{s}}_{ij}$ | error orthogonality (unsigned / signed), equation (5) | $[0,1]$ / $[0,2]$ |
| $C_{ij}$ | local complementarity, equation (6) | $[0,1]$ |
| $B_{ij}$ | band complementarity, equation (7) | $[0,1]$ |
| $w_{i}$ | initial fusion weight, equation (8) | $[0,1]$ |
| $s_{i}$ | fusion discriminative score, equation (9) | $[0,1]$ |
| $\gamma$ | weight suppression coefficient, equation (10) | 0.4 / 0.5 / 0.6 |
| $w_{i}'$ | suppressed weight | $[0,1]$ |
| $\nu_{i}$ | per-coefficient normalised fusion weight | $[0,1]$, $\nu_i+\nu_j=1$ |
| $d,\, b,\, a$ | the three sub-scores of the discriminative score $s$ (apparent velocity / bandwidth / amplitude) | $[0,1]$ |

### 3.4 Fusion method

Fusion proceeds coefficient by coefficient in the short-time Fourier domain. With the two method outputs $y_{i}$ and $y_{j}$, each output gives its own lateral coherence $C_{i}$ and $C_{j}$ (determined by that output alone), and the weights are

$$
w_{i} = C_{i}^{2}, \qquad w_{j} = C_{j}^{2} \qquad (8)
$$

A per-window discriminative score $s_{i}$ is then computed, formed from three weighted sub-scores: the apparent-velocity difference, the bandwidth difference and the amplitude difference:

$$
s_{i} = \mathrm{clip}\!\left( 0.4\,d + 0.3\,b + 0.3\,a,\; 0,\; 1 \right) \qquad (9)
$$

where $d$ is normalised by the apparent-velocity lower bound $v_{\mathrm{lo}} = 100.0$ m/s. The final weights are suppressed by

$$
w_{i}' = w_{i}\left( 1 - \gamma\, s_{i} \right), \qquad \gamma \in \{{0.4,\ 0.5,\ 0.6\}} \qquad (10)
$$

On reconstruction the weights are normalised per coefficient; when both weights are zero, the result degenerates to equal averaging. The formal parameters of the fusion function comprise only the two method outputs and the parameter table, never the ground truth, and this constraint is enforced by a syntax-level check.

The design contains three mechanisms against the misjudgement that agreement implies correctness: first, the weights $w$ contain no cross-method comparison term; second, agreement enters only the discriminative score $s$, and $s$ is used only to **lower** weights; third, the agreement sub-score carries only 0.3 of $s$. Together they ensure that two methods agreeing cannot be exchanged mathematically for higher confidence.

### 3.5 Evaluation protocol

Criteria and thresholds are pre-registered before any evaluation run. The primary pair and the robustness comparator are both determined in advance by the rule of Section 3.3; all three $\gamma$ levels are reported, with no selective presentation. Statistical comparisons use the paired sign-flip permutation test with Holm multiple-comparison correction and bootstrap confidence intervals; the three levels mean that the larger $\gamma$, the stronger the weight suppression and the more conservative the result.

**Unit of analysis (consistent with the implementation).** The 270 observations come from 54 configurations, each with five random seeds. Observations within a configuration share the velocity model, the noise type, the intensity level and the main frequency, so their errors are **not mutually independent**. Significance testing therefore always takes **the configuration as the unit of analysis** ($n = 54$), treating **seeds as within-configuration replicates**: the five seeds are first reduced to a median within each configuration, and the sign-flip permutation test and bootstrap intervals are then computed on the 54 configuration-level differences. The observation count $n = 270$ is used only for descriptive statistics and for displaying per-observation distributions, and **never for any significance statement**. The statistics scripts implement both calibers; this paper quotes the configuration-level results.

Field evaluation uses four reference-free indicators (amplitude preservation, spectral residual, event continuity, and structured reading of difference sections by raters blind to method labels), with weights 30/25/25/20.

Before computation, the event-continuity indicator passed through three pre-declared distinguishability criteria: a dip-alignment gain over zero-lag greater than 0.1, a three-panel range greater than 0.05, and a trace-shuffle reduction greater than 0.1. The measured values are 0.0503, 0.0790 and 0.0838. **One of the three passes and two fail**: the directional criteria (dip alignment 0.0503, trace shuffle 0.0838) both fall short of 0.1, whereas the three-panel range of 0.0790 **exceeds** its 0.05 threshold. Under the pre-declared rule, two failures out of three means the indicator is judged indistinguishable, so it is removed from the composite score and the weights are renormalised to 0.4000, 0.3333 and 0.2667. No threshold was relaxed.

The **asymmetry** of this test should be noted: what passes is the **cross-panel range** criterion (0.0790 against 0.05), while what fails are the two **directional** criteria (0.0503 and 0.0838 against 0.1). That is, on this data the indicator **can distinguish different panels**, yet is **not sufficient to distinguish dip alignment from trace shuffling**, two perturbations that ought to be detected. The conclusion should therefore be phrased as "indistinguishable on this dataset and under these thresholds" rather than "the indicator itself has no discriminative power"; and it must be acknowledged that although the two directional values fall short of the threshold, they lie at the same order of magnitude (0.05 and 0.08 against 0.1), so the robustness of this judgement is limited.

---

## 4 Results

### 4.1 Synthetic benchmark

Table 4 gives the median signal-to-noise ratio gain and leakage metric for the five methods over 270 observations. F-K filtering and the low-rank method are close on the gain, at 0.9320 dB and 0.9482 dB respectively; F-X deconvolution has a median gain of 0.0000 dB yet a leakage metric of 0.029151, an intermediate level; wavelet thresholding and the decomposition method have gains of 0.0422 dB and 0.2101 dB. The lowest leakage is F-K filtering (0.009706) and the highest is the decomposition method (0.045928).

**Table 4** Macro-average medians of the five methods over 270 observations

| Method | ΔSNR (dB) | Lsig (dimensionless) |
| :--- | ---: | ---: |
| F-K filtering | 0.9320 | 0.009706 |
| F-X deconvolution | 0.0000 | 0.029151 |
| Wavelet thresholding | 0.0422 | 0.015129 |
| Decomposition (multichannel SSA) | 0.2101 | 0.045928 |
| Low rank | 0.9482 | 0.011218 |

**Division of labour by noise type.** The table above is a mixed median over all 270 observations and conceals a key difference between the methods: they are good at different noise types. Grouped by noise type (n = 90 per group), the highest within-group medians are F-X deconvolution on band-limited random noise (5.5231 dB), low rank on linear coherent interference (4.4591 dB), and F-K filtering on dispersive surface waves (12.4354 dB).

**Table 5** Median signal-to-noise ratio gain by noise type (dB, n = 90 per group)

| Noise type | F-K filtering | F-X deconvolution | Wavelet thresholding | Decomposition | Low rank | **Within-group best** |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| N1 band-limited random | 0.8528 | **5.5231** | 2.4351 | 3.3458 | 0.8715 | **F-X deconvolution** |
| N2 linear coherent | −0.1709 | −0.1028 | −0.0000 | 0.3020 | **4.4591** | **low rank** |
| N3 dispersive surface wave | **12.4354** | −0.0393 | 0.0422 | −0.0323 | 0.7927 | **F-K filtering** |

**Dilution in the mixed median.** The same methods over all 270 observations give medians of 0.9482 dB (low rank), 0.9320 dB (F-K filtering), 0.2101 dB (decomposition), 0.0422 dB (wavelet thresholding) and 0.0000 dB (F-X deconvolution). F-X deconvolution reaches 5.5231 dB on band-limited random noise yet falls to 0.0000 dB in the mixed caliber — not because the method is ineffective, but because **mixing across noise types flattens its median with the types it is not good at**. The same holds for F-K filtering, which reaches 12.4354 dB on dispersive surface waves and only 0.9320 dB when mixed. This dilution effect is a prerequisite for reading the pairing results that follow.

Figure 2 shows the same data as a grouped bar chart of within-group comparisons by noise type.

![Figure 2 Median signal-to-noise ratio gain by noise type](figures/fig2_noise_specialization.png)
**Figure 2** Median signal-to-noise ratio gain by noise type (grouped bars). The horizontal axis is the noise type; the vertical axis is the median ΔSNR (dB); each group has 90 observations; the value at the top of each bar is that of the best method in the group (dB).

Figure 3 shows the medians and bootstrap 95% confidence intervals of the methods under the mixed caliber, where the differences between methods are far smaller in magnitude than the variation between observations.

![Figure 3 Median ΔSNR and 95% confidence intervals](figures/fig3_method_delta_snr_ci.png)
**Figure 3** Median ΔSNR with bootstrap 95% confidence intervals for the five methods over 270 observations. The horizontal axis is the method; the vertical axis is ΔSNR (dB); the error bars are the 95% confidence intervals; the annotated values are the medians (dB).

### 4.2 Complementarity

The complementarity measures produce 540 records across 10 method pairings, 3 measures and 18 stratum keys. Under the pre-registered rule, the pairing with the highest global median of the local complementarity measure is the primary pair, with a value of 0.500000 and no tie; the runner-up has a value of 0.200000.

There is one disagreement between the three measures that needs to be stated explicitly. The local complementarity measure has a global median of 0.000 for 8 of the 10 pairings, a pronounced zero inflation; meanwhile the primary pair it selects has an error orthogonality of 0.093807, the lowest of all 10 pairings, corresponding to a normalized inner product of about 0.906 — that is, the two methods' errors are nearly collinear. The runner-up pairing of the local complementarity measure has an error orthogonality of 0.575710, clearly higher. Error orthogonality and the local complementarity measure therefore point to different pairings.

Under the pre-registered rule, pair selection is bound to the local complementarity measure and is not changed. The disagreement itself is retained as a **finding at the level of the measure framework**: it shows that the two measures do not characterise complementarity equivalently, and that the difference has observable consequences in the fusion results (see Section 4.3).

**Predictive power of the measures (post hoc, exploratory; n = 10, pairings not independent).** Extending the fusion runs to all 10 pairings makes it possible to test the rank correlation of each measure with the fusion gain. **M1 is positive**: error orthogonality correlates positively with the fusion gain under 4 of the 5 gain definitions, that is, it predicts a **degree of recovery toward the oracle**; **M1 does not predict beating the stronger member**: when the gain is defined as the difference between the fusion and the stronger of its two members, the correlation turns negative, which indicates that high orthogonality often means one member is already strong enough on its own; **M2 has no positive predictive power**: the local complementarity measure is negative under four of the five gain definitions and only $+0.0432$ (a **magnitude near zero**) under the relative-to-stronger-member definition, so the accurate statement is that it has **no positive predictive power under any of the five calibers (one near zero, four negative)**.

**Gain definitions and calibers side by side (both calibers listed; neither merged nor preferred).** Rank correlation is sensitive to the gain definition, so both calibers are listed below:

**Table 6** Rank correlation between the global measure values and the fusion gain (n = 10, post hoc exploratory)

| Gain definition | Caliber | M1 | M1 (signed) | M2 | M3 |
| :--- | :--- | ---: | ---: | ---: | ---: |
| Definition A (used initially) | median of the fusion's own ΔSNR | +0.8303 | +0.8303 | −0.3114 | +0.6242 |
| Definition B | median difference of the fusion relative to the best fixed single method | +0.4909 | +0.4909 | −0.5449 | +0.5030 |
| Definition C | median difference of the fusion relative to the stronger of its two members | −0.7091 | −0.7091 | +0.0432 | −0.3455 |
| Definition D (independent recomputation) | median difference of the fusion relative to the per-observation oracle | +0.6727 | +0.6727 | −0.0779 | +0.5030 |
| Definition E | mean of the fusion's own ΔSNR | +0.7939 | +0.7939 | −0.1384 | +0.4545 |

> Note: the rank correlations above uniformly use average ranks for ties. Definitions A and D differ both in the gain caliber and in the handling of ranks, and both calibers were checked against an independent recomputation. **The magnitude changes markedly with the definition while the direction is broadly stable**: M1 is positive under four of the five definitions and turns negative under the relative-to-stronger-member one; M2 is negative under four of the five and $+0.0432$ (a **magnitude near zero**) under the relative-to-stronger-member one. The accurate statement is therefore that M2 has no positive predictive power under any of the five calibers (one near zero, four negative), not that it is uniformly negative. This is direct evidence that with n = 10 and non-independent pairings the numbers should not be over-interpreted. All values are labelled post hoc and exploratory and do not enter the main conclusions.

The values of the local complementarity measure are highly uneven across strata. For the primary pair, for instance, the strata with a value of **0.0000 are $\mathrm{model}=\mathrm{M1}$ (n = 135), $\mathrm{noise}=\mathrm{N3}$ (n = 90), and $\mathrm{M1\_N2}$ and $\mathrm{M1\_N3}$ (n = 45 each)**; the $\mathrm{model}=\mathrm{M2}$ stratum is **0.631579** (non-zero), and the horizontal-layered-model × band-limited-random-noise stratum is 1.0000. The global value is a median over 270 observations and the stratum values are medians over subsets, so the global median must lie between the medians of the two model strata (0 and 0.631579). The stratum sample sizes range from 45 to 135 — small-sample fractions whose evidential strength depends on the model and the noise type and cannot be extrapolated across strata. Figure 4 gives the stratum heat map of the local complementarity measure and Figure 5 the global matrices of the two measures.

![Figure 4 Stratum heat map of local complementarity](figures/fig4_complementarity_heatmap.png)
**Figure 4** Stratum heat map of the local complementarity measure for method pairings. The horizontal axis is the stratum key; the vertical axis is the method pairing; the colour scale is the local complementarity value (dimensionless, range 0–1).

![Figure 5 Global matrices of the two complementarity measures](figures/fig5_m1_m2_matrices.png)
**Figure 5** Global matrices of the two complementarity measures (medians over 270 observations). Left: error orthogonality; right: local complementarity. The colour scale runs 0–1 (dimensionless).

