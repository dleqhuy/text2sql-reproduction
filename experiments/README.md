# Experiment references

- `historical/spider-v1-main-100.json`: references to benchmark artifacts generated before the fork/submodule migration, with their original recorded provenance. It is not accepted by the production runner as a new experiment.
- `manifests/`: immutable prepared experiment configurations captured from clean committed source. Prepared does not mean executed; actual inference/evaluation artifacts live in ignored `runs/` directories.
- `completed/native-main-100-20261017.json`: completed native CLI rerun on the same 100 IDs, with report/metrics and hashes of local run artifacts. Its prepared source/config/data references remain in `manifests/native-main-100-20261017.json`.

Create, commit and verify a manifest using the [repository workflow](../docs/repository_workflow.md). Source revisions come from gitlinks, not duplicate executable pins in upstream metadata. Secrets, datasets and source snapshots do not belong here.

Superseded prepared manifests that never ran are removed from the working tree; Git history retains them. Pre-migration benchmark provenance stays in historical; new completed experiments are recorded in completed.
