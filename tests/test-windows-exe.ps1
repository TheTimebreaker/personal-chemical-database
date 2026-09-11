$port = 12345
$listener = [System.Net.Sockets.TcpListener]::new(
    [System.Net.IPAddress]::Loopback,
    $port
)

$listener.Start()

try {
    $process = Start-Process `
        -FilePath "D:\Downloads\personal-chemical-database_dev-e90914ba92d19eb31b2f88b4dd9945552caebcd6_windows_x86_64_portable\personal-chemical-database.exe" `
        -ArgumentList "--ready-port", $port `
        -PassThru

    Write-Host "Started process $($process.Id)"
    Write-Host "Waiting for READY..."

    # Wait for the application to connect
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
        }
        else {
            throw "Unexpected readiness message: $message"
        }
    }
    finally {
        $client.Close()
    }
}
finally {
    $listener.Stop()
}