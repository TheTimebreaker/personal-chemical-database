$port = 12345
$listener = [System.Net.Sockets.TcpListener]::new(
    [System.Net.IPAddress]::Loopback,
    $port
)

$listener.Start()

try {
    $process = Start-Process `
        -FilePath "D:\Downloads\pcd.exe" `
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