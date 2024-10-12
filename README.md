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
