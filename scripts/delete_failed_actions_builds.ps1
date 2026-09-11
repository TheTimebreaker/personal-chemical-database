gh run list --limit 100 --status failure

$Answer = Read-Host "Delete ALL of these build logs? Type YES to continue"
if ($Answer -ne "YES") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit
}

$runs = gh run list --limit 100 --status failure --json databaseId |
    ConvertFrom-Json
$runs | ForEach-Object {
    Write-Host "Deleting run $($_.databaseId)..."
    gh run delete $_.databaseId
}