[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputDirectory,

    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,

    [switch]$FixtureMode
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ExperimentRoot = Split-Path -Parent $PSScriptRoot
$AnswerKeyPath = Join-Path $ExperimentRoot "answer-key.json"

function Assert-Condition {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Assert-ExactProperties {
    param(
        [object]$Object,
        [string[]]$Expected,
        [string]$Context
    )

    $actual = @($Object.PSObject.Properties.Name | Sort-Object)
    $wanted = @($Expected | Sort-Object)
    Assert-Condition ($actual.Count -eq $wanted.Count) "$Context has an unexpected property count."
    for ($index = 0; $index -lt $wanted.Count; $index++) {
        Assert-Condition ($actual[$index] -eq $wanted[$index]) "$Context properties do not match the committed observation contract."
    }
}

function Get-Score {
    param(
        [object[]]$Answers,
        [object[]]$Key
    )

    $score = 0
    for ($index = 0; $index -lt 4; $index++) {
        if ([string]$Answers[$index] -eq [string]$Key[$index]) {
            $score++
        }
    }
    return $score
}

function Test-IsJsonNumber {
    param([object]$Value)
    return (
        $Value -is [byte] -or $Value -is [sbyte] -or
        $Value -is [int16] -or $Value -is [uint16] -or
        $Value -is [int32] -or $Value -is [uint32] -or
        $Value -is [int64] -or $Value -is [uint64] -or
        $Value -is [single] -or $Value -is [double] -or $Value -is [decimal]
    )
}

Assert-Condition (Test-Path -LiteralPath $AnswerKeyPath -PathType Leaf) "Missing committed answer key: $AnswerKeyPath"
Assert-Condition (Test-Path -LiteralPath $InputDirectory -PathType Container) "Input directory does not exist: $InputDirectory"

$key = Get-Content -LiteralPath $AnswerKeyPath -Raw | ConvertFrom-Json
$records = @(Get-ChildItem -LiteralPath $InputDirectory -File -Filter "*.json" | Sort-Object Name)
Assert-Condition ($records.Count -eq 5) "Expected exactly five observation JSON files; found $($records.Count)."

$expectedAssignments = @{
    "P-001" = @{ first = "video"; video = "A"; unguided = "B" }
    "P-002" = @{ first = "unguided"; video = "B"; unguided = "A" }
    "P-003" = @{ first = "unguided"; video = "A"; unguided = "B" }
    "P-004" = @{ first = "video"; video = "B"; unguided = "A" }
    "P-005" = @{ first = "video"; video = "A"; unguided = "B" }
}

$topLevelProperties = @(
    "experiment_id", "participant_id", "is_real_observation", "consent_confirmed",
    "unfamiliar_with_target_repository", "ai_assistance_used", "source_snapshot_confirmed",
    "assignment", "conditions", "captured_at", "observer_ref", "protocol_deviations"
)
$seen = @{}
$results = @()

foreach ($record in $records) {
    $raw = Get-Content -LiteralPath $record.FullName -Raw
    $observation = $raw | ConvertFrom-Json
    $context = $record.Name

    Assert-ExactProperties $observation $topLevelProperties $context
    Assert-ExactProperties $observation.assignment @("first_condition", "video_module", "unguided_module") "$context assignment"
    Assert-ExactProperties $observation.conditions @("video", "unguided") "$context conditions"
    Assert-ExactProperties $observation.conditions.video @("module", "duration_seconds", "answers") "$context video result"
    Assert-ExactProperties $observation.conditions.unguided @("module", "duration_seconds", "answers") "$context unguided result"

    foreach ($booleanField in @(
        "is_real_observation", "consent_confirmed", "unfamiliar_with_target_repository",
        "ai_assistance_used", "source_snapshot_confirmed"
    )) {
        Assert-Condition ($observation.$booleanField -is [bool]) "$context $booleanField must be a JSON boolean."
    }
    foreach ($stringField in @("experiment_id", "participant_id", "captured_at", "observer_ref")) {
        Assert-Condition ($observation.$stringField -is [string]) "$context $stringField must be a JSON string."
    }
    foreach ($assignmentField in @("first_condition", "video_module", "unguided_module")) {
        Assert-Condition ($observation.assignment.$assignmentField -is [string]) "$context assignment.$assignmentField must be a JSON string."
    }

    Assert-Condition ($observation.experiment_id -eq $key.experiment_id) "$context has the wrong experiment_id."
    $participantId = [string]$observation.participant_id
    Assert-Condition $expectedAssignments.ContainsKey($participantId) "$context has an unknown participant_id."
    Assert-Condition (-not $seen.ContainsKey($participantId)) "Duplicate participant_id: $participantId"
    $seen[$participantId] = $true

    if ($FixtureMode) {
        Assert-Condition ($observation.is_real_observation -eq $false) "$context must be explicitly non-real in fixture mode."
    }
    else {
        Assert-Condition ($observation.is_real_observation -eq $true) "$context is not explicitly declared as a real observation."
    }

    Assert-Condition ($observation.consent_confirmed -eq $true) "$context does not confirm consent."
    Assert-Condition ($observation.unfamiliar_with_target_repository -eq $true) "$context does not confirm repository unfamiliarity."
    Assert-Condition ($observation.ai_assistance_used -eq $false) "$context reports AI assistance."
    Assert-Condition ($observation.source_snapshot_confirmed -eq $true) "$context does not confirm the pinned source snapshot."
    Assert-Condition (@($observation.protocol_deviations).Count -eq 0) "$context reports a protocol deviation. Preserve it, but do not compile it as eligible evidence."
    Assert-Condition ([string]$observation.observer_ref -match '^human:[A-Za-z0-9][A-Za-z0-9._@+:/-]{1,127}$') "$context lacks a valid human observer reference."
    Assert-Condition ([string]$observation.captured_at -match 'Z$') "$context captured_at must be a UTC date-time ending in Z."

    $capturedAt = [DateTimeOffset]::Parse(
        [string]$observation.captured_at,
        [Globalization.CultureInfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::RoundtripKind
    )
    Assert-Condition ($capturedAt -le [DateTimeOffset]::UtcNow.AddMinutes(5)) "$context captured_at is implausibly far in the future."

    $assignment = $expectedAssignments[$participantId]
    Assert-Condition ($observation.assignment.first_condition -eq $assignment.first) "$context first_condition does not match assignments.csv."
    Assert-Condition ($observation.assignment.video_module -eq $assignment.video) "$context video_module does not match assignments.csv."
    Assert-Condition ($observation.assignment.unguided_module -eq $assignment.unguided) "$context unguided_module does not match assignments.csv."
    Assert-Condition ($observation.conditions.video.module -eq $assignment.video) "$context video result has the wrong module."
    Assert-Condition ($observation.conditions.unguided.module -eq $assignment.unguided) "$context unguided result has the wrong module."

    foreach ($conditionName in @("video", "unguided")) {
        $condition = $observation.conditions.$conditionName
        Assert-Condition ($condition.module -is [string]) "$context $conditionName module must be a JSON string."
        Assert-Condition (Test-IsJsonNumber $condition.duration_seconds) "$context $conditionName duration must be a JSON number."
        $duration = [double]$condition.duration_seconds
        Assert-Condition ($duration -gt 0 -and $duration -le 360) "$context $conditionName duration must be greater than zero and no more than 360 seconds."
        $answers = @($condition.answers)
        Assert-Condition ($answers.Count -eq 4) "$context $conditionName must contain exactly four answers."
        foreach ($answer in $answers) {
            Assert-Condition ($answer -is [string]) "$context $conditionName answers must be JSON strings."
            Assert-Condition ([string]$answer -in @("A", "B", "C", "D")) "$context $conditionName contains an invalid answer."
        }
    }

    $videoKey = @($key.modules.($assignment.video))
    $unguidedKey = @($key.modules.($assignment.unguided))
    $videoScore = Get-Score @($observation.conditions.video.answers) $videoKey
    $unguidedScore = Get-Score @($observation.conditions.unguided.answers) $unguidedKey
    $videoSeconds = [double]$observation.conditions.video.duration_seconds
    $unguidedSeconds = [double]$observation.conditions.unguided.duration_seconds
    $isVideoWin = (
        $videoScore -ge [int]$key.video_win_rule.minimum_video_score -and
        $videoScore -ge $unguidedScore -and
        $videoSeconds -lt $unguidedSeconds
    )

    $results += [pscustomobject][ordered]@{
        participant_id = $participantId
        first_condition = [string]$observation.assignment.first_condition
        video_module = [string]$assignment.video
        unguided_module = [string]$assignment.unguided
        video_score = $videoScore
        unguided_score = $unguidedScore
        video_duration_seconds = $videoSeconds
        unguided_duration_seconds = $unguidedSeconds
        video_win = $isVideoWin
        captured_at = $capturedAt.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        observer_ref = [string]$observation.observer_ref
        content_hash = "sha256:$((Get-FileHash -LiteralPath $record.FullName -Algorithm SHA256).Hash.ToLowerInvariant())"
    }
}

foreach ($participantId in $expectedAssignments.Keys) {
    Assert-Condition $seen.ContainsKey($participantId) "Missing required participant: $participantId"
}

$results = @($results | Sort-Object participant_id)
$wins = @($results | Where-Object { $_.video_win }).Count
$threshold = [int]$key.rank_one_threshold.target
$thresholdMet = $wins -ge $threshold

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

if ($FixtureMode) {
    $unexpectedEvidence = @(Get-ChildItem -LiteralPath $OutputDirectory -File -Filter "E-*.json" -ErrorAction SilentlyContinue)
    Assert-Condition ($unexpectedEvidence.Count -eq 0) "Fixture output contains evidence-shaped files; use a clean fixture output directory."
}
else {
    foreach ($result in $results) {
        $numericId = $result.participant_id.Substring(2)
        $evidenceId = "E-OBS-VIDEO-$numericId"
        $expiresAt = ([DateTimeOffset]::Parse($result.captured_at)).AddDays(90).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        $stance = if ($result.video_win) { "supports" } else { "contradicts" }
        $evidence = [ordered]@{
            evidence_id = $evidenceId
            source_type = "observed_user_behavior"
            source_reference = "experiment://X-LEARNING-COMPARISON-001/participant/$($result.participant_id)"
            captured_at = $result.captured_at
            freshness = [ordered]@{
                policy = "source_specific"
                expires_at = $expiresAt
            }
            content_hash = $result.content_hash
            claim_tested = "A developer obtains a correct high-level mental model of an unfamiliar repository faster from a concise source-linked video than from unguided file-by-file exploration."
            stance = $stance
            directness = "direct"
            sample_context = [ordered]@{
                description = "One anonymous, eligible, human-moderated within-participant comparison using counterbalanced modules at the pinned Understand-Anything source snapshot."
                sample_size = 1
                population = "Developers unfamiliar with the target repository"
            }
            collector = $result.observer_ref
            limitations = @(
                "One participant in a five-participant directional study; not a population estimate.",
                "Different counterbalanced modules may differ in difficulty.",
                "The second condition may be affected by carryover learning.",
                "The feasibility clip is not final production media."
            )
            hypothesis_refs = @("H-LEARNING-001")
            measurements = @(
                [ordered]@{ metric = [string]$key.rank_one_threshold.metric; value = $(if ($result.video_win) { 1 } else { 0 }); unit = [string]$key.rank_one_threshold.unit },
                [ordered]@{ metric = "Video-condition comprehension score"; value = $result.video_score; unit = "correct answers of 4" },
                [ordered]@{ metric = "Unguided-condition comprehension score"; value = $result.unguided_score; unit = "correct answers of 4" },
                [ordered]@{ metric = "Video-condition elapsed time"; value = $result.video_duration_seconds; unit = "seconds" },
                [ordered]@{ metric = "Unguided-condition elapsed time"; value = $result.unguided_duration_seconds; unit = "seconds" }
            )
            provenance = [ordered]@{
                kind = "external"
                collection_method = "Human-moderated, counterbalanced comparison under protocol X-LEARNING-COMPARISON-001; compiler-derived score and timing outcome."
                is_fixture = $false
                untrusted_input = $true
            }
        }

        $evidencePath = Join-Path $OutputDirectory "$evidenceId.json"
        $evidence | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $evidencePath -Encoding UTF8
    }
}

$summary = [ordered]@{
    experiment_id = [string]$key.experiment_id
    mode = $(if ($FixtureMode) { "fixture-validation-only" } else { "real-observation-compilation" })
    evidence_generated = (-not $FixtureMode)
    source_commit = [string]$key.source_commit
    eligible_observations = $results.Count
    video_wins = $wins
    required_video_wins = $threshold
    threshold_met = $thresholdMet
    results = $results
}

$summaryPath = Join-Path $OutputDirectory "summary.json"
$summary | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

if ($FixtureMode) {
    Write-Host "FIXTURE_VALID: compiler mechanics passed; no TEMPO evidence was generated."
}
else {
    Write-Host "REAL_OBSERVATIONS_COMPILED: generated $($results.Count) evidence proposals; video wins $wins/$($results.Count); threshold met: $thresholdMet"
}
Write-Host "Summary: $summaryPath"
