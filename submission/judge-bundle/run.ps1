$ErrorActionPreference = 'Stop'

$bundle = Join-Path $PSScriptRoot 'understand-video-demo.mjs'
$arguments = @($args)
if ($arguments.Count -eq 0) {
    $arguments = @('demo', '--offline')
}

& node $bundle @arguments
exit $LASTEXITCODE
