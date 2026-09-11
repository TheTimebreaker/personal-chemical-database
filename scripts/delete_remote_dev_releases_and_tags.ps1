$Owner = "TheTimebreaker"
$Repo  = "personal_chemical_database"

# Set to $false to actually delete things
$DryRun = $false

$FullRepo = "$Owner/$Repo"

Write-Host "Looking for releases/tags starting with 'dev-' in $FullRepo..." -ForegroundColor Cyan
Write-Host ""

# Get all releases
$Releases = gh release list `
    --repo $FullRepo `
    --limit 1000 `
    --json tagName |
    ConvertFrom-Json

$DevReleases = $Releases |
    Where-Object { $_.tagName.StartsWith("dev-") }

Write-Host "Releases to delete:" -ForegroundColor Yellow

foreach ($Release in $DevReleases) {
    Write-Host "  $($Release.tagName)"
}

Write-Host ""
Write-Host "Tags to delete:" -ForegroundColor Yellow

# Get remote tags
$RemoteTags = git ls-remote --tags "https://github.com/$FullRepo.git"

$DevTags = $RemoteTags |
    ForEach-Object {
        # Format is:
        # <SHA> refs/tags/<tag>
        $Tag = ($_ -split "`t")[1] -replace "^refs/tags/", ""

        # Ignore ^{} dereference entries
        if ($Tag -notmatch "\^\{\}$" -and $Tag.StartsWith("dev-")) {
            $Tag
        }
    } |
    Sort-Object -Unique

foreach ($Tag in $DevTags) {
    Write-Host "  $Tag"
}

Write-Host ""

if ($DryRun) {
    Write-Host "DRY RUN: Nothing was deleted." -ForegroundColor Green
    Write-Host "Review the list above, then change `$DryRun = `$false and run again." -ForegroundColor Cyan
    exit
}

# Confirmation
$Answer = Read-Host "Delete ALL of these releases and tags? Type YES to continue"

if ($Answer -ne "YES") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit
}

Write-Host ""
Write-Host "Deleting releases..." -ForegroundColor Red

foreach ($Release in $DevReleases) {
    $Tag = $Release.tagName

    Write-Host "Deleting release: $Tag"

    gh release delete $Tag `
        --repo $FullRepo `
        --yes
}

Write-Host ""
Write-Host "Deleting Git tags..." -ForegroundColor Red

foreach ($Tag in $DevTags) {
    Write-Host "Deleting tag: $Tag"

    git push "https://github.com/$FullRepo.git" --delete $Tag
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green

# Run this to "sync" local tags with remote
# git fetch --prune --prune-tags