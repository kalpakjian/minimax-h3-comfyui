# Prevent system sleep while long jobs run. Exits when marker file appears.
$marker = "C:\minimax+comfyUI\logs\_jobs_done.marker"
$end = (Get-Date).AddHours(6)
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class SleepBlock {
  [DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);
  public const uint ES_CONTINUOUS = 0x80000000;
  public const uint ES_SYSTEM_REQUIRED = 0x00000001;
  public const uint ES_AWAYMODE_REQUIRED = 0x00000040;
}
"@
[SleepBlock]::SetThreadExecutionState([SleepBlock]::ES_CONTINUOUS -bor [SleepBlock]::ES_SYSTEM_REQUIRED -bor [SleepBlock]::ES_AWAYMODE_REQUIRED) | Out-Null
Write-Output ("keep_awake start " + (Get-Date -Format o))
while ((Get-Date) -lt $end) {
  if (Test-Path $marker) { break }
  [SleepBlock]::SetThreadExecutionState([SleepBlock]::ES_CONTINUOUS -bor [SleepBlock]::ES_SYSTEM_REQUIRED) | Out-Null
  Start-Sleep -Seconds 30
}
[SleepBlock]::SetThreadExecutionState([SleepBlock]::ES_CONTINUOUS) | Out-Null
Write-Output ("keep_awake end " + (Get-Date -Format o))
