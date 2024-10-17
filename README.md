```bash
#!/bin/bash
set -Eeuo pipefail
set -o nounset
set -o errexit

export VIRTIO_ISO="virtio.iso"
export PWSH_MSI="pwsh.msi"
export ROS_DRIVE="ros.img"

download_dir="downloads"
mkdir -p "$download_dir"
( cd "$download_dir"

DOWNLOAD_CMD="curl -L"
#DOWNLOAD_CMD="aria2c -x16 -s16 -o-"
download_and_verify() {
    local url="$1"
    local filename="$2"
    local checksum="$3"
    local is_ros="${4:-false}"

    if [[ -f "$filename" ]] && echo "$checksum $filename" | sha256sum -c --quiet; then
        echo "Checksum verified for existing $filename"
    else
        echo "Downloading $filename..."
        if [[ "$is_ros" == "true" ]]; then
            $DOWNLOAD_CMD "$url" | tee >(sha256sum | grep -q "$checksum" || (echo "Checksum verification failed"; exit 1)) | funzip > "$filename"
        else
            $DOWNLOAD_CMD "$filename" "$url"
            echo "$checksum $filename" | sha256sum -c || { echo "Checksum verification failed for $filename"; exit 1; }
        fi
        echo "Download and verification of $filename complete"
    fi
}
# Download and verify VIRTIO_ISO
virtio_url="https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/archive-virtio/virtio-win-0.1.262-2/virtio-win-0.1.262.iso"
virtio_iso_checksum="bdc2ad1727a08b6d8a59d40e112d930f53a2b354bdef85903abaad896214f0a3"
download_and_verify "$virtio_url" "$VIRTIO_ISO" "$virtio_iso_checksum"

# Download and verify PWSH_MSI
pwsh_url="https://github.com/PowerShell/PowerShell/releases/download/v7.4.5/PowerShell-7.4.5-win-x64.msi"
pwsh_sha="4d0286cc70c2e45404ad940ef96394b191da45d7de46340b05c013eef41c1eec"
download_and_verify "$pwsh_url" "$PWSH_MSI" "$pwsh_sha"

ros_url="https://download.mikrotik.com/routeros/7.16.1/chr-7.16.1.img.zip"
ros_sha="7a47c7bddf51c6f5153a7e402fd0a32044557eaf0d96af273b"
download_and_verify "$ros_url" "$ROS_DRIVE" "$ros_sha" true
)

podman build --build-arg ROS_DRIVE="$ROS_DRIVE" --build-arg PWSH_MSI="$PWSH_MSI"\
    --build-arg VIRTIO_ISO="$VIRTIO_ISO" -t image_name .

```


#### Note^ needs to be updated in accrodance with console.py
#### This is previous version
### Callback Function Structure: 
The code uses a linked list of callback functions `CallbackList` to process console output. Each callback function should follow this general structure:
```python
def callback_function(stream, events, data: Data, **args):
      # Process data
      # Return None to retry or continue, or return data to move to next callback
```
### Data Flow and Return Values:
Callbacks must return `None` or a `Data` object.
Returning` None` indicates that processing should be retried or continued from the current point.
Returning a `Data` object signals successful processing, and the system will move to the next callback.

The `Data` Class: The `Data` class encapsulates the state of the processing pipeline. It contains:
- The current console object
- The current callback list
- Any additional data needed for processing

### Main Processing Loop: 
The `main_callback` function is the core of the processing loop. It iterates through callbacks until it reaches the end or needs to retry.
### Callback Chaining: 
Callbacks in this system typically receive the following parameters:
```python
def callback_function(stream, events, data: Data, **args):
    # ...
- stream: The libvirt stream object for I/O operations.
- events: Event flags from libvirt.
- data:   A Data object containing the current state and context.
- **args: Additional keyword arguments specific to each callback.
```
Callbacks are chained using the `CallbackList` class. This allows for complex sequences of operations:
```python
cb = CallbackList(read_until(find_str), None, pattern="Login:")
cb = cb.add(send_command("admin"))
cb = cb.add(read_until(find_str), pattern="Password:")
# ... more callbacks ...
cb = cb.finish()
```

### Error Handling and Retries:
If a callback returns `None`, it will be retried in the next event loop iteration.
The retry method in `Data` allows for more complex retry logic if needed.

### Stream Reading: 
The `read_until` function is a key component that reads from the stream until a condition is met:
```python
def read_until(condition_fn: typing.Callable[[str], bool]):
    def _read_until(stream, events, data: Data, **args):
        # ... (reading logic)
        res = condition_fn(decoded_buffer, **args)
        if res:
          return data.set_return(**res)
    return _read_until
```
### Event Loop Integration: 
The system integrates with libvirt's event loop, allowing for non-blocking I/O:
```python
while check_console(console, data):
    libvirt.virEventRunDefaultImpl()
```
### Console State Management: 
The `Console` class manages the state of the virtual machine console, including connecting to the VM and handling state changes.
