param(
    [Parameter(Mandatory = $true)]
    [string]$ExecutablePath
)

$timeoutSeconds = 30
$listener = [System.Net.Sockets.TcpListener]::new(
    [System.Net.IPAddress]::Loopback,
    0
)

$listener.Start()
$port = $listener.LocalEndpoint.Port
$stdout = Join-Path $env:TEMP "exe-test-$PID-stdout.txt"
$stderr = Join-Path $env:TEMP "exe-test-$PID-stderr.txt"

try {
    $process = Start-Process `
        -FilePath $ExecutablePath `
        -ArgumentList "--ready-port", $port `
        -PassThru `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr

    Write-Host "Started file $ExecutablePath process $($process.Id)"
    Write-Host "Waiting for READY..."

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    while ($true) {
        # 1. Did the application connect?
        if ($listener.Pending()) {
            $client = $listener.AcceptTcpClient()

            try {
                $stream = $client.GetStream()

                $buffer = New-Object byte[] 1024
                $bytesRead = $stream.Read($buffer, 0, $buffer.Length)

                $message = [System.Text.Encoding]::UTF8.GetString(
                    $buffer,
                    0,
                    $bytesRead
                )

                if ($message -eq "READY") {
                    Write-Host "Application initialized successfully"
                    exit 0
                }

                throw "Unexpected readiness message: '$message'"
            }
            finally {
                $client.Close()
            }
        }

        # 2. Did the application die?
        if ($process.HasExited) {
            Write-Host ""
            Write-Host "========== APPLICATION STDOUT =========="
            if (Test-Path $stdout) {
                Get-Content $stdout
            }

            Write-Host ""
            Write-Host "========== APPLICATION STDERR =========="
            if (Test-Path $stderr) {
                Get-Content $stderr
            }

            Write-Host ""
            throw "Application exited before becoming ready. Exit code: $($process.ExitCode)"
        }

        # 3. Did we exceed the timeout?
        if ($stopwatch.Elapsed.TotalSeconds -ge $timeoutSeconds) {
            throw "Application did not become ready within $timeoutSeconds seconds"
        }

        # Don't busy-loop
        Start-Sleep -Milliseconds 100
    }
}
finally {
    $listener.Stop()

    # Make sure the application doesn't remain running after the test
    if ($process -and -not $process.HasExited) {
        Write-Host "Stopping application..."
        taskkill /PID $process.Id /T /F
        $process.WaitForExit()
        Write-Host "Stopped application (and all its children processes) :)"
    }
}