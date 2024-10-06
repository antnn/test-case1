#https://www.redhat.com/sysadmin/podman-inside-container
#use with sha256 to imporve security and reproduction
FROM registry.fedoraproject.org/fedora@sha256:0096c473ae7faeeb365fda479480d6bf4c1270542b96cd975a1eeb7e03eea1c7

COPY . /opt/project

RUN set -Eeuo pipefail; set -o nounset ; set -o errexit ; \
dnf install -y qemu-kvm libvirt virt-manager bridge-utils systemd p7zip-plugins ansible git python3-pip ; pip3 install pycdlib ; \
useradd user -G wheel,libvirt ; \
chmod +x /opt/project/*.sh ; \
source /opt/project/main.sh; build; \
echo -e "\nRun on host to use systemd inside container, see https://developers.redhat.com/blog/2019/04/24/how-to-run-systemd-in-a-container :\n" ;\
echo -e "setsebool -P container_manage_cgroup true\n\n" ; \
echo -e "Start container with: \n" ; \
echo -e "USERID=\$(id -u); podman run --rm -it \
 --cap-add=sys_admin,net_admin,net_raw,mknod \
 --device=/dev/fuse \
 --device=/dev/urandom \
 --device=/dev/kvm \
 --device=/dev/dri \
 --device=/dev/net/tun \
 --security-opt label=disable \
 -e XDG_RUNTIME_DIR=/run/user/1000 \
 -e WAYLAND_DISPLAY=wayland-0 \
 -v /run/user/\$USERID/wayland-0:/tmp/wayland-0:z \
 -v \$PWD/iso:/iso -v /proc/sys/net/ipv6/conf:/proc/sys/net/ipv6/conf:rw --name oblako oblako\n\n" ; \
echo -e "Run this line after working with container in host:\n" ; \
echo -e "sudo chown \$USER /run/user/\$USERID/wayland-0 ; sudo chcon unconfined_u:object_r:user_tmp_t:s0 /run/user/\$USERID/wayland-0" ; \
echo -e "\n\n" ;
#
CMD [ "/sbin/init" ]
