[CmdletBinding()]
param(
    [string]$OutputDirectory,
    [string]$SourceRepository,
    [string]$ProofVideo
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ExperimentRoot = Split-Path -Parent $PSScriptRoot
$RepositoryRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ExperimentRoot))
$SourceCommit = "58cfb20ac8f3f98cd7dede428d147dbe9cdc94b2"
$ExpectedProofHash = "d93fa9554a6eab4412675175f929fea8dadc2bd581132f4698a1265bc521816d"

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $RepositoryRoot ".understand-video\experiments\learning-comparison\bundle"
}
if ([string]::IsNullOrWhiteSpace($SourceRepository)) {
    $SourceRepository = Join-Path $RepositoryRoot ".source-cache\Understand-Anything"
}
if ([string]::IsNullOrWhiteSpace($ProofVideo)) {
    $ProofVideo = Join-Path $RepositoryRoot ".understand-video\experiments\graph-video-spike\proof.mp4"
}

function Assert-Condition {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    [IO.File]::WriteAllText($Path, $Content, (New-Object Text.UTF8Encoding($false)))
}

function Export-SourceFile {
    param([string]$RelativePath, [string]$Destination)
    $gitObject = "${SourceCommit}:$RelativePath"
    $content = & git -C $SourceRepository show $gitObject
    Assert-Condition ($LASTEXITCODE -eq 0) "Could not extract $RelativePath from source commit $SourceCommit."
    Write-Utf8NoBom $Destination (($content -join "`n") + "`n")
}

Assert-Condition (Test-Path -LiteralPath $SourceRepository -PathType Container) "Missing Understand-Anything source clone: $SourceRepository"
Assert-Condition (Test-Path -LiteralPath $ProofVideo -PathType Leaf) "Missing verified feasibility video: $ProofVideo"
$proofHash = (Get-FileHash -LiteralPath $ProofVideo -Algorithm SHA256).Hash.ToLowerInvariant()
Assert-Condition ($proofHash -eq $ExpectedProofHash) "Proof video hash mismatch; refusing to build participant bundles."

& git -C $SourceRepository cat-file -e "${SourceCommit}^{commit}"
Assert-Condition ($LASTEXITCODE -eq 0) "The pinned source commit is unavailable in $SourceRepository."

$sampleGraph = Join-Path $SourceRepository "understand-anything-plugin\packages\dashboard\public\knowledge-graph.json"
Assert-Condition (Test-Path -LiteralPath $sampleGraph -PathType Leaf) "Missing sample knowledge graph: $sampleGraph"
$graph = Get-Content -LiteralPath $sampleGraph -Raw | ConvertFrom-Json
Assert-Condition ($graph.project.gitCommitHash -eq $SourceCommit) "Sample knowledge graph is not pinned to the required source commit."

$ffmpeg = Get-Command ffmpeg -ErrorAction Stop
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$stagingRoot = Join-Path ([IO.Path]::GetTempPath()) ("understand-video-experiment-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $stagingRoot | Out-Null

try {
    $sharedRoot = Join-Path $stagingRoot "shared"
    $moduleARoot = Join-Path $sharedRoot "module-a"
    $moduleBRoot = Join-Path $sharedRoot "module-b"
    New-Item -ItemType Directory -Path $moduleARoot, $moduleBRoot -Force | Out-Null

    Export-SourceFile "packages/core/src/types.ts" (Join-Path $moduleARoot "types.ts")
    Export-SourceFile "packages/core/src/schema.ts" (Join-Path $moduleARoot "schema.ts")
    Export-SourceFile "packages/core/src/analyzer/tour-generator.ts" (Join-Path $moduleBRoot "tour-generator.ts")
    Export-SourceFile "packages/dashboard/src/components/LearnPanel.tsx" (Join-Path $moduleBRoot "LearnPanel.tsx")
    Copy-Item -LiteralPath $sampleGraph -Destination (Join-Path $sharedRoot "knowledge-graph.json")

    $clipA = Join-Path $sharedRoot "video-module-A.mp4"
    $clipB = Join-Path $sharedRoot "video-module-B.mp4"
    & $ffmpeg.Source -hide_banner -loglevel error -y -ss 0 -i $ProofVideo -t 17.581043 -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 128k $clipA
    Assert-Condition ($LASTEXITCODE -eq 0) "ffmpeg failed while producing the Module A clip."
    & $ffmpeg.Source -hide_banner -loglevel error -y -ss 17.581043 -i $ProofVideo -t 18.715873 -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 128k $clipB
    Assert-Condition ($LASTEXITCODE -eq 0) "ffmpeg failed while producing the Module B clip."

    $assignments = Import-Csv -LiteralPath (Join-Path $ExperimentRoot "assignments.csv")
    Assert-Condition (@($assignments).Count -eq 5) "assignments.csv must contain exactly five participants."
    $manifestFiles = @()

    foreach ($assignment in $assignments) {
        foreach ($condition in @("video", "unguided")) {
            $module = if ($condition -eq "video") { $assignment.video_module } else { $assignment.unguided_module }
            $conditionRoot = Join-Path $stagingRoot "$($assignment.participant_id)-$condition"
            $sourcesRoot = Join-Path $conditionRoot "source-extracts"
            New-Item -ItemType Directory -Path $sourcesRoot -Force | Out-Null

            $questionSource = Join-Path $ExperimentRoot ("module-{0}-questions.md" -f $module.ToLowerInvariant())
            Copy-Item -LiteralPath $questionSource -Destination (Join-Path $conditionRoot "questions.md")
            Copy-Item -LiteralPath (Join-Path $sharedRoot "knowledge-graph.json") -Destination (Join-Path $sourcesRoot "knowledge-graph.json")
            Get-ChildItem -LiteralPath (Join-Path $sharedRoot "module-$($module.ToLowerInvariant())") -File |
                Copy-Item -Destination $sourcesRoot

            $conditionText = if ($condition -eq "video") {
                @"
# Video condition - Module $module

Participant: $($assignment.participant_id)
Pinned source commit: $SourceCommit

1. Ask the observer to start the timer before you open any other file.
2. Watch video.mp4 once. Playback time counts toward the 360-second cap.
3. You may inspect files in source-extracts for traceability.
4. Record four answers from questions.md and tell the observer when finished.

Do not use AI assistance, web search, or any material outside this ZIP. Do not
open a second-condition bundle until the observer provides it.
"@
            }
            else {
                @"
# Unguided condition - Module $module

Participant: $($assignment.participant_id)
Pinned source commit: $SourceCommit

1. Ask the observer to start the timer before you open any other file.
2. Explore only the files in source-extracts.
3. Record four answers from questions.md and tell the observer when finished.

There is no explanatory video in this condition. Do not use AI assistance, web
search, or any material outside this ZIP. Do not open a second-condition bundle
until the observer provides it. The condition has a 360-second cap.
"@
            }
            Write-Utf8NoBom (Join-Path $conditionRoot "instructions.md") $conditionText

            if ($condition -eq "video") {
                Copy-Item -LiteralPath (Join-Path $sharedRoot "video-module-$module.mp4") -Destination (Join-Path $conditionRoot "video.mp4")
            }

            $order = if ($assignment.first_condition -eq $condition) { "01-first" } else { "02-second" }
            $zipName = "$($assignment.participant_id)-$order-$condition-module-$module.zip"
            $zipPath = Join-Path $OutputDirectory $zipName
            Compress-Archive -Path (Join-Path $conditionRoot "*") -DestinationPath $zipPath -CompressionLevel Optimal -Force
            $manifestFiles += [ordered]@{
                file = $zipName
                participant_id = $assignment.participant_id
                order = $order
                condition = $condition
                module = $module
                sha256 = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
    }

    $observerRoot = Join-Path $stagingRoot "observer"
    New-Item -ItemType Directory -Path $observerRoot -Force | Out-Null
    foreach ($fileName in @("README.md", "protocol.md", "assignments.csv", "answer-key.json", "observation.schema.json", "observation.example.json")) {
        Copy-Item -LiteralPath (Join-Path $ExperimentRoot $fileName) -Destination $observerRoot
    }
    $observerZip = Join-Path $OutputDirectory "observer-kit.zip"
    Compress-Archive -Path (Join-Path $observerRoot "*") -DestinationPath $observerZip -CompressionLevel Optimal -Force
    $manifestFiles += [ordered]@{
        file = "observer-kit.zip"
        participant_id = $null
        order = $null
        condition = "observer-only"
        module = $null
        sha256 = (Get-FileHash -LiteralPath $observerZip -Algorithm SHA256).Hash.ToLowerInvariant()
    }

    $manifest = [ordered]@{
        experiment_id = "X-LEARNING-COMPARISON-001"
        generated_at = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        source_repository = "https://github.com/Egonex-AI/Understand-Anything"
        source_commit = $SourceCommit
        proof_video_sha256 = $ExpectedProofHash
        fixtures_are_evidence = $false
        files = $manifestFiles
    }
    $manifestPath = Join-Path $OutputDirectory "manifest.json"
    $manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    Write-Host "BUNDLE_READY: 10 sealed participant condition ZIPs plus one observer kit."
    Write-Host "Manifest: $manifestPath"
}
finally {
    if (Test-Path -LiteralPath $stagingRoot) {
        $resolvedTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
        $resolvedStaging = [IO.Path]::GetFullPath($stagingRoot)
        Assert-Condition ($resolvedStaging.StartsWith($resolvedTemp, [StringComparison]::OrdinalIgnoreCase)) "Refusing to clean a staging path outside the system temporary directory."
        Remove-Item -LiteralPath $resolvedStaging -Recurse -Force
    }
}
