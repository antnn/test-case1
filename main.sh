#!/bin/bash
set -Eeuo pipefail
set -o nounset
set -o errexit
export USER=user
#Converts it to one line to pass to cmd in SynchronousCommand
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
powershell_script="C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -Command \"$powershell_script\""


BRIDGE=virbr1
build() {
    local ISO_TEMP_ROOT_BUILD_DIR="/tmp/iso"
    local OS_ISO="/iso/win_server.iso"
    local CONFIG_ISO="/opt/vm/win/config.iso"
    local WIN_SOCKET_MON="/tmp/qemu.win.socket"

    local WIN_MAC_ADDRESS="00:11:22:33:44:55"
    local WIN_IP_ADDRESS="192.168.152.3/24"

    local ROUTER_IP="192.168.152.2"

    /opt/project/render_template.sh /opt/project/internal.net.template.xml bridge="$BRIDGE" > /opt/project/internal.net.xml
    
    mkdir -p "$ISO_TEMP_ROOT_BUILD_DIR/iso"
    mkdir -p "$(dirname "$CONFIG_ISO")"

    /opt/project/generate_autounattend.sh --image-index "2" \
        --template-file "/opt/project/autounattend.template.xml" \
        --output-dir "$ISO_TEMP_ROOT_BUILD_DIR/iso" \
        --lang "ru-RU" --user-name "IEUSER" --user-password "Passw0rd!" \
        --admin-password "Passw0rd!" --computer-name "MAINSERVER" \
        --mac-address "$WIN_MAC_ADDRESS" --ip-address "$WIN_IP_ADDRESS" \
        --route-prefix "0.0.0.0/0" --default-gw "$ROUTER_IP" --dns-server "127.0.0.1" \
        --secondary-dns "1.1.1.1" --setup-command "$powershell_script"

    /opt/project/create_config_iso.sh --build-dir "$ISO_TEMP_ROOT_BUILD_DIR" \
        --output-path "$CONFIG_ISO" \
        --virtio-url "https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/archive-virtio/virtio-win-0.1.262-2/virtio-win-0.1.262.iso" \
        --virtio-checksum "bdc2ad1727a08b6d8a59d40e112d930f53a2b354bdef85903abaad896214f0a3"
    
    local WIN_DRIVE="/opt/vm/win/win.qcow2"
    echo Creating disk for Windows Server...
    qemu-img create -f qcow2  "$WIN_DRIVE" 120G
    chown user $WIN_DRIVE

    echo Rendering Windows Server domain template...
    /opt/project/render_template.sh /opt/project/win2k22.template.xml \
        drive="$WIN_DRIVE" \
        mac_address="$WIN_MAC_ADDRESS" \
        bridge="$BRIDGE" \
        os_iso="$OS_ISO" \
        socket_mon="$WIN_SOCKET_MON" \
        config_iso="$CONFIG_ISO" > /opt/vm/win/win2k22.domain.xml
    
    curl 
}

# Function to run commands as user
#BRIDGE=virbr1
run_as_root() {
    echo "allow $BRIDGE" >> /etc/qemu/bridge.conf
    systemctl enable --now virtnetworkd-ro.socket
    virsh net-define /opt/project/internal.net.xml
    virsh net-start private && virsh net-autostart private
    chown -R user /tmp/wayland-0
    # Fixing wayland
    bash -c "sleep 3; mkdir -p /run/user/1000; ln -sf /tmp/wayland-0 /run/user/1000/wayland-0 ; chown -R user /run/user/1000" &
    sudo -u user bash
}
run_as_user() {
    echo Defining Windows Server KVM domain...
    virsh define /opt/vm/win/win2k22.domain.xml
    virt-manager -c qemu:///session
}


