#https://www.redhat.com/sysadmin/podman-inside-container
FROM registry.fedoraproject.org/fedora:40 as build

ENV BRIDGE="virbr1" \
    PROJECT_DIR="/opt/project"\
    DOWNLOADS="/opt/project/downloads"\
    VM_DIR="/opt/vm"\
    TEMPLATE_DIR="/opt/project/templates"\
    WIN_VM_DIR="/opt/vm/win"\
    ROS_VM_DIR="/opt/vm/ros"\
    WIN_VM_NAME="win2k22"\
    ROS_VM_NAME="ros"\
    WIN_XML_FILE="/opt/vm/win/win2k22.domain.xml"\
    ROS_XML_FILE="/opt/vm/ros/ros.xml"\
    NET_NAME="private"\
    ROS_VM_DISK="/opt/vm/ros/drive.img"

ARG ISO_DIR="/iso"
ARG WIN_ISO="win_server.iso"
ARG WIN_IMAGE_INDEX=2
ARG WIN_DRIVE_SIZE="120G"
ARG PWSH_MSI="pwsh.msi"
ARG VIRTIO_ISO="virtio.iso"
ARG ROS_DRIVE="ros.img"
COPY . $PROJECT_DIR

RUN set -Eeuo pipefail; set -o nounset ; set -o errexit ; \
dnf install -y qemu-kvm libvirt virt-manager bridge-utils systemd p7zip-plugins python3 ; \
useradd user -G wheel,libvirt ; \
chmod +x /opt/project/*.sh ; \
source /opt/project/main.sh; build; \
echo -e "\e[33mRun on host to use systemd inside container, see https://developers.redhat.com/blog/2019/04/24/how-to-run-systemd-in-a-container\e[0m" ;\
echo -e "\e[32msetsebool -P container_manage_cgroup true\e[0m\n" ; \
echo -e "\e[33mStart container with: \e[0m" ; \
echo -e "\e[32mUSERID=\$(id -u); podman run --rm -it \
  --cap-add=sys_admin,net_admin,net_raw,mknod \
  --device=/dev/fuse \
  --device=/dev/urandom \
  --device=/dev/kvm \
  --device=/dev/dri \
  --device=/dev/net/tun \
  --security-opt label=disable \
  -e XDG_RUNTIME_DIR=/run/user/1000 \
  -e WAYLAND_DISPLAY=wayland-0 \
  -e WIN_ISO=\$ISO_DIR/win_server.iso \
  -v /run/user/\$USERID/wayland-0:/tmp/wayland-0:z \
  -v \$PWD/iso:/\$OS_ISO -v /proc/sys/net/ipv6/conf:/proc/sys/net/ipv6/conf:rw --name container_name image_name\e[0m\n" ; \
echo -e "\e[33mExecute this command on the host after working with the container :\e[0m" ; \
echo -e "\e[32msudo chown \$USER /run/user/\$USERID/wayland-0; sudo chcon unconfined_u:object_r:user_tmp_t:s0 /run/user/\$USERID/wayland-0\e[0m" ;
#
FROM build
CMD [ "/sbin/init" ]
