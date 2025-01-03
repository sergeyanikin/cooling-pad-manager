param (
    [Parameter(Mandatory=$true, Position=0)]
    [int]$ThrottleValue
)

if ($ThrottleValue -ge 50 -and $ThrottleValue -le 100) {
    powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX $ThrottleValue
    powercfg.exe -setactive SCHEME_CURRENT
} else {
    Write-Host "Error: Value must be an integer between 50 and 100."
}
