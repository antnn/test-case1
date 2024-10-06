$defaultEntryPoint = 'start.ps1'
foreach ($drive in [char]'A'..[char]'Z') {
    $defaultFirstLogonCmd = 'powershell -NoExit -ExecutionPolicy Bypass -File '
    $drive = [char]$drive
    $path = "${drive}:\$defaultEntryPoint" 
    if (Test-Path $path) { 
        $defaultFirstLogonCmd = "${defaultFirstLogonCmd} ${path} " 
        & cmd /C $defaultFirstLogonCmd 
    } 
}

powershell_script=$(cat <<'EOF' | tr '\n' ';' | sed 's/"/\\"/g'
$defaultEntryPoint = 'start.ps1'
foreach ($drive in [char]'A'..[char]'Z') {
    $defaultFirstLogonCmd = 'powershell -NoExit -ExecutionPolicy Bypass -File '
    $drive = [char]$drive
    $path = "${drive}:\$defaultEntryPoint" 
    if (Test-Path $path) { 
        $defaultFirstLogonCmd = "${defaultFirstLogonCmd} ${path} " 
        & cmd /C $defaultFirstLogonCmd 
    } 
}
EOF
)
powershell_script="powershell -Command \"$powershell_script\""
echo $powershell_script