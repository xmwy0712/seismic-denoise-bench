# Release package — pre-registered seismic denoising benchmark

This archive accompanies the manuscript *A Pre-Registered Benchmark and Complementarity
Analysis of Seismic Denoising Methods: Diagnosing Selection Failure in Method Pairing*
(Chinese draft `draft-v13.md`, English draft `draft-en-v1.md`).

## Layout

```
payload/                         contents, source hierarchy preserved
  docs/paper/                    manuscript (both languages), compliance report,
                                 numerical provenance table, glossary, figures (8)
  configs/                       frozen configurations and the method registry
  preregistration/               pre-registration documents (statistics, complementarity,
                                 fusion, validation, stratified-threshold test)
  results/                       metric tables, statistical products and diagnostics
  execution/  src/  tests/        code
MANIFEST.sha256                  SHA256 for every payload file, with its source path
ARRAYS.sha256                    SHA256 for every output array (.npy), listed separately
README.md                        this file
```

## Conventions

* **Source path mapping.** The archive preserves the repository hierarchy rather than
  flattening it, so that files with the same name but different provenance (for example
  the several `metrics.csv` and `pairwise.csv` products) remain distinct and nothing is
  overwritten. Each line of `MANIFEST.sha256` records the package path and, after the
  arrow, the repository path it came from.
* **Checksums are measured, never transcribed.** Every hash in both checksum files was
  computed from the file bytes at packaging time, and the packaging step verifies that
  each packaged file is byte-identical to its source before the archive is accepted.
* **Output arrays.** The arrays are large (about 4.4 GB across 17823 files) and are not
  distributed with the code repository; `ARRAYS.sha256` lists their checksums. A copy can
  be requested using the checksums as the identity of each file.

## Licence

Code in this study is released under the MIT licence, copyright held by the author. The
field data are redistributed under their original CC BY 4.0 licence and the attribution
must be retained; the full citation is given in Section 2.2 of the manuscript.

## Contact

Zhang Tao, School of Earth Sciences and Engineering, Nanjing University.
