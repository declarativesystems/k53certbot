# Developer instructions

## Where to add my code?
Entry point is `k53certbot/cli.py` in function `main()`

## Running locally

```shell
poetry run k53certbot
```

## Testing

```shell
make test
```

## Getting a shell
```shell
poetry shell
```

## Where does the executable come from?

`k53certbot` is a shim generated automatically by poetry, see `pyproject.toml`.

## K8S authentication

**In Cluster**

```
kubernetes.config.load_incluster_config()
```

Authentication is automatic. In-cluster config is loaded from well-known-files

**On workstation**

Run with `--use-active-kube-context` to use active kubernetes context, like this:

```bash
ZEROSSL_API_KEY=NOUSE CERTBOT_ADMIN_EMAIL=dummy@dummy poetry run k53certbot --debug --dry-run --use-active-kube-context --provider zerossl
```