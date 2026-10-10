# Redeploy HeatShift to Elastic Beanstalk from the CLI.
# Usage:  .\deploy.ps1            (label = timestamp, e.g. v20261010-2215)
#         .\deploy.ps1 -Label v2
# Needs a valid `aws login` session.
param(
    [string]$Label = ("v" + (Get-Date -Format "yyyyMMdd-HHmmss"))
)

$ErrorActionPreference = "Stop"

$Region  = "ap-southeast-2"
$App     = "heatshift"
$EnvName = "heatshift-env"
$Bucket  = "heatshift-deploy-186712717803"
$Url     = "http://heatshift-env.eba-umys9bjc.ap-southeast-2.elasticbeanstalk.com"
$Key     = "app-$Label.zip"

function Check($step) {
    if ($LASTEXITCODE -ne 0) { throw "FAILED: $step (exit code $LASTEXITCODE)" }
}

Set-Location $PSScriptRoot

# 1. Build app.zip from the deployable paths that exist (files at the zip root)
$paths = @("application.py", "Procfile", "requirements.txt", "templates", "heatshift", "static", "data") |
    Where-Object { Test-Path $_ }
Remove-Item app.zip -ErrorAction SilentlyContinue
Write-Host "Zipping: $($paths -join ', ')"
tar -a -c -f app.zip --exclude "__pycache__" --exclude "*.pyc" @paths
Check "build app.zip"

# 2. Upload to S3
aws s3 cp app.zip "s3://$Bucket/$Key" --region $Region
Check "upload to S3"

# 3. Register the zip as a new application version
aws elasticbeanstalk create-application-version --region $Region --application-name $App `
    --version-label $Label --source-bundle "S3Bucket=$Bucket,S3Key=$Key" --output text --query "ApplicationVersion.VersionLabel"
Check "create-application-version"

# 4. Deploy that version to the environment
aws elasticbeanstalk update-environment --region $Region --environment-name $EnvName `
    --version-label $Label --output text --query "Status"
Check "update-environment"

# 5. Poll until the environment is Ready again (max ~15 min)
for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 10
    $s = aws elasticbeanstalk describe-environments --region $Region --environment-names $EnvName `
        --query "Environments[0].[Status,Health,VersionLabel]" --output text
    Check "describe-environments"
    Write-Host "  $s"
    $status, $health, $version = $s -split "\s+"
    if ($status -eq "Ready") { break }
}
if ($status -ne "Ready") { throw "Environment not Ready after 15 minutes" }
if ($version -ne $Label) { throw "Deploy failed: environment is still on version $version (check Events in the console)" }
if ($health -ne "Green") { Write-Warning "Health is $health. Check Logs in the console." }

# 6. Smoke test
$resp = Invoke-WebRequest -UseBasicParsing "$Url/health"
Write-Host "/health -> $($resp.StatusCode) $($resp.Content)"
Write-Host "Deployed $Label to $Url"
