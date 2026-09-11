Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$tag="dev-$(git rev-parse HEAD)"
git tag $tag
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

git push --tags
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

gh release create $tag --notes "development release" --latest=false
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }