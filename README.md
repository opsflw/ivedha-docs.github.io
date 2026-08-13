# iVedha documentation distribution

This repository is the static distribution target for
[docs.ivedha.cloud](https://docs.ivedha.cloud/). It hosts a catalog at the
domain root and independently built MkDocs sites under application-specific
paths.

## Path contract

| Path | Owner | Purpose |
| --- | --- | --- |
| `/` | This repository | Documentation catalog |
| `/elastic/` | `opsflw/opsflw-docs-src` | Elastic Stack documentation and versions |
| `/airflow/` | Airflow documentation repository | Reserved for Airflow documentation |

An application may change its MkDocs theme, overrides, navigation, and assets
without affecting another application because every build is contained by its
path prefix.

## Publishing an application

In the application's `mkdocs.yml`, set the unversioned application URL and
Mike prefix:

```yaml
site_url: https://docs.ivedha.cloud/<application>/

plugins:
  - mike:
      alias_type: copy
      canonical_version: latest
      deploy_prefix: <application>

extra:
  version:
    provider: mike
```

Publish the continuously updated site and named releases with the same prefix
on every Mike command:

```bash
mike deploy latest \
  --deploy-prefix <application> \
  --push \
  --remote dist \
  --branch gh-pages

mike deploy <version> \
  --deploy-prefix <application> \
  --push \
  --remote dist \
  --branch gh-pages

mike set-default latest \
  --deploy-prefix <application> \
  --push \
  --remote dist \
  --branch gh-pages
```

Never run an unprefixed Mike deployment against this repository. An
unprefixed deployment owns root files and can replace the catalog.

## Onboarding another MkDocs site

1. Choose a unique lowercase path such as `airflow`.
2. Keep its MkDocs configuration and styling in its source repository.
3. Set `site_url` and `plugins.mike.deploy_prefix` to the assigned path.
4. Install the documentation GitHub App for this repository with only
   `Contents: read and write`, and use a short-lived installation token.
5. Add the site to `sites.json` and to the catalog in `index.html`.
6. Validate the MkDocs build with `mkdocs build --strict` before publishing.
7. Confirm the application root, latest alias, search, canonical links, and
   version selector after deployment.

The old root `/latest/` path is not part of the multi-site contract and is not
redirected. Each application's current alias belongs under its own prefix.

## Root files

- `CNAME` owns the `docs.ivedha.cloud` custom domain.
- `.nojekyll` publishes all static assets without Jekyll processing.
- `sites.json` is the machine-readable application catalog.
- `index.html` and `assets/hub.css` render the human-facing catalog.

GitHub Pages must remain configured to publish the root of the `gh-pages`
branch. Application workflows modify only their assigned prefix.
