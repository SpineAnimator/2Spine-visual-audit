# 2Spine visual audit — public runner

Dedicated public GitHub Actions execution host for the 2Spine native-frame visual and provenance audit.

## Runner
- GitHub-hosted `ubuntu-latest`
- Workflow: `.github/workflows/runner.yml`
- Unit tests run on push; real-frame review is manually dispatched after native evidence is available.
- Audit scripts and tests are mirrored from `vladleopold/3Spine-core`.

## Required repository secret
- `ACCESS_TOKEN`: read access to the repository containing the licensed native Editor run and its Actions artifacts.

The runner is allocated successfully. The mirrored test suite currently needs its full dependency closure and the real-frame job must be wired to the separate `SpineAnimator/Native-360-Editor` run artifact before it can be considered an end-to-end audit.
