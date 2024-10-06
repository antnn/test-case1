$ErrorActionPreference = "Stop"

try {
    Install-WindowsFeature -Name DHCP
    Add-DhcpServerv4Scope -Name "MyDHCPScope" -StartRange 192.168.122.3 -EndRange 192.168.122.254 -SubnetMask 255.255.255.0
    Set-DhcpServerv4OptionValue -DnsDomain test.corp -DnsServer 192.168.122.2 -Router 192.168.122.1
    Add-DhcpServerInDC -DnsName test.corp
    Restart-Service dhcpserver
    Write-Host "DHCP configuration completed successfully."
}
catch {
    Write-Error "An error occurred: $_"
    exit 1
}
