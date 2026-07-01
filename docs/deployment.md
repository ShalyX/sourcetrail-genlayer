# SourceTrail deployment prep

SourceTrail is ready for GenVM lint/validation locally. Live deployment needs a configured GenLayer CLI account and target network.

## Prerequisites

- `genlayer` CLI installed
- account created/imported locally
- network configured for `studionet` or `testnet-bradbury`
- enough faucet/test funds if the selected network requires them
- never paste private keys or keystore passwords into chat; enter them locally when CLI prompts

## Local verification before deploy

```bash
python3.12 -m venv .venv312
. .venv312/bin/activate
pip install pytest genvm-linter
./scripts/check.sh
```

This runs:

- `pytest tests -q`
- `genvm-lint lint contracts/source_trail.py --json`
- `genvm-lint validate contracts/source_trail.py --json`
- `genvm-lint check contracts/source_trail.py --json`

## Network commands

Inspect available CLI config/network state:

```bash
genlayer network list
genlayer config get network
genlayer account show
```

Set the network:

```bash
genlayer network set studionet
# or
genlayer network set testnet-bradbury
```

Deploy:

```bash
./scripts/deploy.sh studionet
# or
./scripts/deploy.sh testnet-bradbury
```

## Post-deploy verification

After deployment, do not stop at `ACCEPTED` or `FINALIZED`. Inspect execution success:

```bash
genlayer receipt <TX_ID>
genlayer trace <TX_ID>
genlayer schema <CONTRACT_ADDRESS>
genlayer code <CONTRACT_ADDRESS>
```

Record in submission notes:

- network
- contract address
- deploy tx id
- receipt/trace status
- schema methods count
- runner hash from first contract line

## Security note

Do not store account secrets in this repo. `.gitignore` excludes local virtualenv/cache files only; GenLayer keystores should stay in the CLI's normal secure config location.
