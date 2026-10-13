# ADR-0005: Where this repo differs from the maintainer's earlier projects

## Context
verdrift, layerdelta and lastgreen kept their mission brief in a workspace folder outside
the repository and named `thanatchon36` as the copyright holder. This project's brief asks
for `MISSION.md` at the repository root and "Thanatchon" in the LICENSE.

## Decision
Follow the newer brief: `MISSION.md` is in the repo (it doubles as the design doc), and LICENSE
says "Thanatchon". Keep the rest of the house style: commits under the GitHub noreply address,
Actions pinned to commit SHAs with `persist-credentials: false`, a CI job that runs the README
example, and a README with "How it works" and "Limitations" sections.

## Consequences
The LICENSE holder string differs from the other repos. Both refer to the same person.
