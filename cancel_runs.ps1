param()
foreach ($r in 1..10) {
    $repo = "lawdachuss/node-$r"
    $json = gh run list --repo $repo --limit 50 --json databaseId,status --jq ".[]" 2>$null
    $count = 0
    if ($json) {
        $runs = $json | ConvertFrom-Json
        foreach ($run in $runs) {
            if ($run.status -eq "in_progress" -or $run.status -eq "queued") {
                gh run cancel $run.databaseId --repo $repo 2>$null
                $count++
            }
        }
    }
    if ($count -gt 0) {
        Write-Host ("node-${r}: cancelled $count run(s)")
    } else {
        Write-Host ("node-${r}: no active runs")
    }
}
