import subprocess
import re
import time
import threading
from pathlib import Path

def log_gpu_utilization(
    output_path="./mac_chip_gpu",
    interval_ms=1000,
    stop_event=None,
    duration=None,
):
    """
    Continuously sample GPU utilization using powermetrics and write results to a file.

    Args:
        output_path: Destination file. Will be created (parents too) if missing.
        interval_ms: powermetrics sampling interval in milliseconds.
        stop_event: Optional threading.Event (or similar) used to signal a stop.
        duration: Optional max runtime in seconds. When reached, logging stops.
    """

    cmd = [
        "sudo",
        "/usr/bin/powermetrics",
        "--samplers",
        "gpu_power",
        "-i",
        str(interval_ms),
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,  # unbuffered for streaming
    )

    pattern = re.compile(r"GPU HW active residency:\s+([\d.]+)%")
    buffer = ""
    start_time = time.time()
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", buffering=1) as gpu_file:  # line-buffered
        try:
            while True:
                if stop_event and stop_event.is_set():
                    break

                if duration is not None and (time.time() - start_time) >= duration:
                    break

                chunk = process.stdout.read(4096)
                if not chunk:
                    break

                buffer += chunk
                matches = pattern.findall(buffer)

                if matches:
                    util = float(matches[-1])
                    timestamp = time.time()
                    gpu_file.write(f"{timestamp:.3f},{util:.2f}\n")
                    gpu_file.flush()
                    buffer = ""
        except KeyboardInterrupt:
            print("Stopping GPU monitor.")
        finally:
            process.kill()


def read_latest_logged_gpu(output_path="./mac_chip_gpu"):
    """
    Read and return the most recent GPU utilization entry from the log file.

    Returns:
        (timestamp, utilization) as floats, or (None, None) if no data exists.
    """
    path = Path(output_path)
    if not path.exists() or path.stat().st_size == 0:
        return None, None

    with path.open("r") as gpu_file:
        lines = gpu_file.read().strip().splitlines()
        if not lines:
            return None, None
        last_line = lines[-1]

    try:
        timestamp_str, util_str = last_line.split(",", maxsplit=1)
        return float(timestamp_str), float(util_str)
    except ValueError:
        return None, None


if __name__ == "__main__":
    print("Logging GPU utilization to ./mac_chip_gpu and echoing latest sample (Ctrl+C to stop)...")

    stop_event = threading.Event()
    log_thread = threading.Thread(
        target=log_gpu_utilization,
        kwargs={"output_path": "./mac_chip_gpu", "interval_ms": 1000, "stop_event": stop_event},
        daemon=True,
    )
    log_thread.start()

    try:
        while True:
            timestamp, util = read_latest_logged_gpu("./mac_chip_gpu")
            if timestamp is not None:
                print(f"[{timestamp:.3f}] GPU Utilization: {util:.2f}%")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping GPU monitor.")
    finally:
        stop_event.set()
        log_thread.join()
