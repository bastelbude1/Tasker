# tasker/core/streaming_output_handler.py
"""
Streaming Output Handler - Memory-Efficient Command Output Management
-------------------------------------------------------------------
Handles large command outputs without loading everything into memory.
Provides configurable buffering and automatic temp file fallback.

CRITICAL: Python 3.6.8 compatible only - no 3.7+ features allowed
"""

import os
import tempfile
import threading
import time
from typing import Optional, Tuple, Dict, Any


class StreamingOutputHandler:
    """
    Memory-efficient output handler for command execution.

    Features:
    - Configurable memory buffer limits
    - Automatic temp file fallback for large outputs
    - Real-time streaming with timeout support
    - Thread-safe output collection
    - Maintains full compatibility with existing success condition evaluation
    """

    # Configuration constants
    DEFAULT_BUFFER_SIZE = 1024 * 1024  # 1MB memory buffer
    DEFAULT_TEMP_THRESHOLD = 10 * 1024 * 1024  # 10MB threshold for temp files
    CHUNK_SIZE = 8192  # 8KB read chunks
    MAX_IN_MEMORY = 100 * 1024 * 1024  # 100MB absolute memory limit

    def __init__(self, buffer_size=None, temp_threshold=None, temp_dir=None):
        """
        Initialize streaming output handler.

        Args:
            buffer_size: Memory buffer size before switching to temp files
            temp_threshold: Size threshold for using temp files
            temp_dir: Directory for temporary files (default: system temp)
        """
        self.temp_threshold = temp_threshold or self.DEFAULT_TEMP_THRESHOLD
        self.temp_dir = temp_dir or tempfile.gettempdir()

        # Output storage
        self.stdout_data = ""
        self.stderr_data = ""
        self.stdout_file = None
        self.stderr_file = None

        # State tracking
        self.stdout_size = 0
        self.stderr_size = 0
        self.using_temp_files = False

    def _create_temp_file(self, prefix):
        """Create a temporary file for large output storage."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w+',
            prefix=f'tasker_{prefix}_',
            dir=self.temp_dir,
            delete=False  # We'll clean up manually
        )
        return temp_file

    def _append_output(self, data, stream_type):
        """Append output data to appropriate storage (memory or temp file)."""
        if stream_type == 'stdout':
            if self.stdout_size + len(data) > self.temp_threshold and not self.stdout_file:
                # Switch to temp file
                self.stdout_file = self._create_temp_file('stdout')
                if self.stdout_data:
                    self.stdout_file.write(self.stdout_data)
                    self.stdout_data = ""  # Clear memory buffer
                self.using_temp_files = True

            if self.stdout_file:
                self.stdout_file.write(data)
                self.stdout_file.flush()
            else:
                self.stdout_data += data
            self.stdout_size += len(data)

        elif stream_type == 'stderr':
            if self.stderr_size + len(data) > self.temp_threshold and not self.stderr_file:
                # Switch to temp file
                self.stderr_file = self._create_temp_file('stderr')
                if self.stderr_data:
                    self.stderr_file.write(self.stderr_data)
                    self.stderr_data = ""  # Clear memory buffer
                self.using_temp_files = True

            if self.stderr_file:
                self.stderr_file.write(data)
                self.stderr_file.flush()
            else:
                self.stderr_data += data
            self.stderr_size += len(data)

    def stream_process_output(self, process, timeout=None):
        """
        Stream output from subprocess with memory-efficient handling.

        Args:
            process: subprocess.Popen instance
            timeout: Maximum time to wait for process completion

        Returns:
            tuple: (stdout_content, stderr_content, exit_code, timed_out)
        """
        def read_stream(stream, stream_type):
            """Read from a stream and append to appropriate storage."""
            try:
                while True:
                    chunk = stream.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    self._append_output(chunk, stream_type)
            except Exception as e:
                # Stream closed or error - expected when process ends
                import logging
                logging.debug("Stream reader for %s ended: %s", stream_type, e)

        # Start threads to read stdout and stderr concurrently
        stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, 'stdout'), daemon=True)
        stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, 'stderr'), daemon=True)

        stdout_thread.start()
        stderr_thread.start()

        # Wait for process completion with timeout
        timed_out = False
        if timeout:
            # Manual timeout handling for Python 3.6.8 compatibility
            start_wait = time.time()
            while process.poll() is None:
                if time.time() - start_wait > timeout:
                    timed_out = True
                    process.kill()
                    break
                time.sleep(0.1)  # Check every 100ms
            process.wait()  # Ensure process is cleaned up
        else:
            process.wait()  # Wait indefinitely if no timeout

        # Wait for reading threads to complete
        stdout_thread.join(timeout=5)  # Give threads time to finish reading
        stderr_thread.join(timeout=5)

        exit_code = process.returncode

        # Retrieve final output
        stdout_content = self._get_final_output('stdout')
        stderr_content = self._get_final_output('stderr')

        return stdout_content, stderr_content, exit_code, timed_out

    def _get_final_output(self, stream_type):
        """Get the final output content, reading from temp file if necessary."""
        if stream_type == 'stdout':
            if self.stdout_file:
                self.stdout_file.seek(0)
                content = self.stdout_file.read()
                return content
            else:
                return self.stdout_data
        elif stream_type == 'stderr':
            if self.stderr_file:
                self.stderr_file.seek(0)
                content = self.stderr_file.read()
                return content
            else:
                return self.stderr_data
        return ""

    def get_memory_usage_info(self):
        """
        Get information about current memory usage.

        Returns:
            dict: Memory usage information where size values are character counts
                  (not bytes) since we operate in text mode with universal_newlines=True.
        """
        return {
            'stdout_size': self.stdout_size,
            'stderr_size': self.stderr_size,
            'total_size': self.stdout_size + self.stderr_size,
            'using_temp_files': self.using_temp_files,
            'stdout_in_memory': not bool(self.stdout_file),
            'stderr_in_memory': not bool(self.stderr_file)
        }

    def cleanup(self):
        """Clean up temporary files and resources."""
        if self.stdout_file:
            try:
                self.stdout_file.close()
                os.unlink(self.stdout_file.name)
            except Exception as e:
                import logging
                logging.debug("Failed to cleanup stdout temp file %s: %s", getattr(self.stdout_file, 'name', '<unknown>'), e)

        if self.stderr_file:
            try:
                self.stderr_file.close()
                os.unlink(self.stderr_file.name)
            except Exception as e:
                import logging
                logging.debug("Failed to cleanup stderr temp file %s: %s", getattr(self.stderr_file, 'name', '<unknown>'), e)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.cleanup()


def create_memory_efficient_handler(max_memory_mb=10):
    """
    Factory function to create a memory-efficient output handler.

    Args:
        max_memory_mb: Maximum memory to use before switching to temp files

    Returns:
        StreamingOutputHandler instance configured for memory efficiency
    """
    buffer_size = min(max_memory_mb * 1024 * 1024, StreamingOutputHandler.MAX_IN_MEMORY)
    return StreamingOutputHandler(
        buffer_size=buffer_size,
        temp_threshold=buffer_size,
        temp_dir=None  # Use system default
    )