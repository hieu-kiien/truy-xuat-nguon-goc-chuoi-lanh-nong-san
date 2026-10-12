param([string[]]$TestArgs = @('-q'))
$ErrorActionPreference = 'Stop'
$testEnvNames = @('DB_HOST','DB_PORT','DB_NAME','DB_USER','DB_PASSWORD','DB_ADMIN_USER','DB_ADMIN_PASSWORD','APP_ENV','DATABASE_URL_ENV','MIGRATION_DATABASE_URL_ENV')
$previousTestEnvironment = @{}
foreach ($name in $testEnvNames) { $previousTestEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    # This database is separate from the web demo (ttcs_test on port 55434).
    $env:DB_HOST = '127.0.0.1'
    $env:DB_PORT = '55434'
    $env:DB_NAME = 'ttcs_s34_tests'
    $env:DB_USER = 'ttcs_s34_test_app'
    $env:DB_PASSWORD = 'app-test-password'
    $env:DB_ADMIN_USER = 'postgres'
    $env:DB_ADMIN_PASSWORD = 'postgres-test-password'
    $env:APP_ENV = 'test'
    $env:DATABASE_URL_ENV = ''
    $env:MIGRATION_DATABASE_URL_ENV = ''
    & '.venv/Scripts/python.exe' -m pytest @TestArgs
    if ($LASTEXITCODE -ne 0) { throw "Pytest failed ($LASTEXITCODE)." }
} finally {
    foreach ($name in $testEnvNames) { [Environment]::SetEnvironmentVariable($name, $previousTestEnvironment[$name], 'Process') }
    Pop-Location
}
