#!/bin/bash
set -Eeuo pipefail
set -o nounset
set -o errexit
create_config_iso() {
    local iso_temp_root_build_dir=""
    local drivers_dir="\$WinPeDriver\$"
    local config_iso_output_path=""
    local virtio_iso_url=""
    local virtio_iso_checksum=""

    # Parse named arguments
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            --build-dir) iso_temp_root_build_dir="$2"; shift ;;
            --output-path) config_iso_output_path="$2"; shift ;;
            --virtio-url) virtio_iso_url="$2"; shift ;;
            --virtio-checksum) virtio_iso_checksum="$2"; shift ;;
            *) echo "Unknown parameter passed: $1"; return 1 ;;
        esac
        shift
    done

    if [[ -z "$iso_temp_root_build_dir" || -z "$config_iso_output_path" ]]; then
        echo "Error: --build-dir and --output-path are required parameters."
        return 1
    fi

    echo "Creating drivers directory..."
    mkdir -p "$iso_temp_root_build_dir/iso/$drivers_dir"

    echo "Copying pwsh scripts to iso..."
    cp -r /opt/project/pwsh "$iso_temp_root_build_dir/iso/pwsh"

    echo "Downloading Virtio Drivers..."
    curl "$virtio_iso_url" > "$iso_temp_root_build_dir/virtio-win.iso"

    echo "Verifying checksum..."
    echo "$virtio_iso_checksum $iso_temp_root_build_dir/virtio-win.iso" | sha256sum -c

    echo "Extracting virtio drivers..."
    7z e "$iso_temp_root_build_dir/virtio-win.iso" -o"$iso_temp_root_build_dir/iso/$drivers_dir" \
        vioscsi/2k22/amd64/vioscsi.cat \
        vioscsi/2k22/amd64/vioscsi.inf \
        vioscsi/2k22/amd64/vioscsi.pdb \
        vioscsi/2k22/amd64/vioscsi.sys \
        viostor/2k22/amd64/viostor.cat \
        viostor/2k22/amd64/viostor.inf \
        viostor/2k22/amd64/viostor.sys \
        viostor/2k22/amd64/viostor.pdb \
        NetKVM/2k22/amd64/netkvm.cat \
        NetKVM/2k22/amd64/netkvm.inf \
        NetKVM/2k22/amd64/netkvm.pdb \
        NetKVM/2k22/amd64/netkvm.sys \
        NetKVM/2k22/amd64/netkvmco.exe \
        NetKVM/2k22/amd64/netkvmco.pdb \
        NetKVM/2k22/amd64/netkvmp.exe \
        NetKVM/2k22/amd64/netkvmp.pdb

    echo "Creating Windows config ISO..."
    mkisofs -o "$config_iso_output_path" \
        -J -l -R -V "WIN_AUTOINSTALL" \
        -iso-level 4 \
        -joliet-long \
        "$iso_temp_root_build_dir/iso/$drivers_dir" \
        "$iso_temp_root_build_dir/iso/pwsh" \
        "$iso_temp_root_build_dir/iso/autounattend.xml"

    echo "Windows config ISO created successfully at $config_iso_output_path"
}

create_config_iso "$@"