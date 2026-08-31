import time
import math
import logging
import os
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import subprocess
import threading
import platform
import queue
from pathlib import Path
from copy import deepcopy
from dataclasses import asdict, dataclass

try:
    from macos_gpu_test import log_gpu_utilization, read_latest_logged_gpu
except ImportError:
    log_gpu_utilization = None
    read_latest_logged_gpu = None

class SystemHealthMonitor:
    """
    Monitors system health indicators including GPU utilization, queue length, and deadline slack.
    """
    
    def __init__(self, logger=None, monitoring_interval: float = 0.1):
        self.logger = logger or logging.getLogger(__name__)
        self.gpu_utilization = 0.0
        self.queue_length = 0
        self.monitoring_active = False
        self.monitor_thread = None
        self.monitoring_interval = max(0.02, float(monitoring_interval))
        self.is_macos = platform.system() == "Darwin"
        self.mac_gpu_stop_event = None
        self.mac_gpu_logger_thread = None
        self.mac_gpu_log_path = Path("./mac_chip_gpu")
        
    def start_monitoring(self):
        """Start the system health monitoring thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.logger.info("[BURST] System health monitoring started")
            self._start_mac_gpu_logger_if_needed()
    
    def stop_monitoring(self):
        """Stop the system health monitoring thread."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()
            self.logger.info("[BURST] System health monitoring stopped")
        self._stop_mac_gpu_logger_if_needed()

    def _start_mac_gpu_logger_if_needed(self):
        if not self.is_macos:
            return
        if log_gpu_utilization is None:
            self.logger.warning("[BURST] macos_gpu_test helpers not available; cannot log GPU utilization.")
            return
        if self.mac_gpu_logger_thread and self.mac_gpu_logger_thread.is_alive():
            return
        self.mac_gpu_stop_event = threading.Event()
        self.mac_gpu_logger_thread = threading.Thread(
            target=log_gpu_utilization,
            kwargs={
                "output_path": str(self.mac_gpu_log_path),
                "interval_ms": 1000,
                "stop_event": self.mac_gpu_stop_event,
            },
            daemon=True,
        )
        self.mac_gpu_logger_thread.start()
        self.logger.info("[BURST] macOS GPU logging thread started.")

    def _stop_mac_gpu_logger_if_needed(self):
        if not self.is_macos or not self.mac_gpu_logger_thread:
            return
        if self.mac_gpu_stop_event:
            self.mac_gpu_stop_event.set()
        self.mac_gpu_logger_thread.join()
        self.mac_gpu_logger_thread = None
        self.mac_gpu_stop_event = None
        self.logger.info("[BURST] macOS GPU logging thread stopped.")
    
    def _monitor_loop(self):
        """Main monitoring loop that continuously updates system health metrics."""
        while self.monitoring_active:
            try:
                # Update GPU utilization
                self.gpu_utilization = self._get_gpu_utilization()
                # self.logger.debug(f"[BURST][HEALTH] GPU utilization: {self.gpu_utilization:.1f}%")
                
                # Sleep for a short interval before next measurement
                time.sleep(self.monitoring_interval)
                
            except RuntimeError as e:
                # GPU monitoring completely failed, log error and stop monitoring
                self.logger.error(f"[BURST] GPU monitoring failed: {e}")
                self.logger.error("[BURST] Stopping GPU monitoring due to persistent failures")
                self.monitoring_active = False
                break
            except Exception as e:
                self.logger.error(f"[BURST] Error in monitoring loop: {e}")
                time.sleep(1)
    
    def _load_sysfs_gpu(self) -> Optional[float]:
        """
        在 Jetson/Tegra 上，读取 `/sys/devices/platform/gpu.0/load`
        并把 0‑1000 的整数转换为 %
        返回 None 表示文件不存在或内容不可解析。
        """
        sysfs_path = "/sys/devices/platform/gpu.0/load"
        if not os.path.exists(sysfs_path):
            return None

        try:
            with open(sysfs_path, "r") as f:
                raw = f.read().strip()
            # 预期是整数 0‑1000
            val = int(raw)
            if 0 <= val <= 1000:
                return val / 10.0   # 0‑1000 → 0‑100%
        except Exception:
            return None
        return None

    def _get_gpu_utilization(self) -> float:
        """
        Get current GPU utilization percentage.
        Raises RuntimeError if GPU monitoring is not available.
        """
        tegrastats_error = None
        nvidia_smi_error = None
        apple_error = None
        
        # First try sysfs for Jetson devices (AGX Nano, etc.)
        gpu_util = self._load_sysfs_gpu()
        if gpu_util is not None:
            return float(gpu_util)

        # macOS flow: read from log file generated by macos_gpu_test helpers
        if self.is_macos:
            if read_latest_logged_gpu is None:
                raise RuntimeError("macOS GPU helpers unavailable; cannot read utilization.")
            timestamp, util = read_latest_logged_gpu(str(self.mac_gpu_log_path))
            if util is not None:
                return float(util)
            # No fresh data yet—return last known value to avoid cascading failures.
            # self.logger.debug("[BURST][HEALTH] macOS GPU log not populated yet, using last value.")
            return float(self.gpu_utilization)

        # Then try tegrastats for Jetson devices (AGX Nano, etc.)
        # try:
        #     # Use tegrastats --readall for single sample
        #     result = subprocess.run(
        #         ["tegrastats", "--readall"],
        #         capture_output=True, text=True, timeout=2
        #     )
        #     if result.returncode == 0:
        #         gpu_util = self._parse_tegrastats_gpu(result.stdout)
        #         if gpu_util is not None:
        #             return gpu_util
        #         else:
        #             tegrastats_error = "Failed to parse GPU utilization from tegrastats output"
        #     else:
        #         tegrastats_error = f"tegrastats failed with return code {result.returncode}: {result.stderr}"
        # except subprocess.TimeoutExpired:
        #     tegrastats_error = "tegrastats command timed out"
        # except FileNotFoundError:
        #     tegrastats_error = "tegrastats command not found"
        # except Exception as e:
        #     tegrastats_error = f"tegrastats error: {e}"
        
        # Fallback: try nvidia-smi for desktop GPUs
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                nvidia_smi_error = f"nvidia-smi failed with return code {result.returncode}: {result.stderr}"
        except subprocess.TimeoutExpired:
            nvidia_smi_error = "nvidia-smi command timed out"
        except FileNotFoundError:
            nvidia_smi_error = "nvidia-smi command not found"
        except ValueError as e:
            nvidia_smi_error = f"nvidia-smi parsing error: {e}"
        except Exception as e:
            nvidia_smi_error = f"nvidia-smi error: {e}"
            
        if platform.machine().startswith("arm"):
            try:
                # powermetrics 需要 root，若没有 root 则会报 PermissionError
                result = subprocess.run(
                    ["powermetrics", "--samplers", "smc"],
                    capture_output=True, text=True, timeout=2, check=True
                )
                gpu_util = self._parse_powermetrics_gpu(result.stdout)
                if gpu_util is not None:
                    return gpu_util
                apple_error = "failed to parse powermetrics output"
            except subprocess.TimeoutExpired:
                apple_error = "powermetrics timed out"
            except FileNotFoundError:
                apple_error = "powermetrics not found"
            except PermissionError:
                apple_error = ("powermetrics requires root privileges. "
                               "Run script with sudo or grant permissions.")
            except Exception as e:
                apple_error = f"powermetrics error: {e}"
        
        # Both methods failed, raise exception with detailed error information
        error_msg = "Failed to get GPU utilization from both methods:\n"
        if tegrastats_error is not None:
            error_msg += f"  tegrastats: {tegrastats_error}\n"
        if nvidia_smi_error is not None:
            error_msg += f"  nvidia-smi: {nvidia_smi_error}\n"
        if apple_error is not None:
            error_msg += f"  Apple powermetrics: {apple_error or 'N/A'}\n"
        
        raise RuntimeError(error_msg)
    
    # def _parse_tegrastats_gpu(self, stats_output: str) -> float:
    #     """Parse GPU utilization from tegrastats output."""
    #     try:
    #         # Look for GR3D_FREQ pattern in tegrastats output
    #         # Format: GR3D_FREQ 0%@318 (utilization%@frequency)
    #         import re
    #         match = re.search(r'GR3D_FREQ\s+(\d+)%@(\d+)', stats_output)
    #         if match:
    #             utilization = int(match.group(1))
    #             frequency = int(match.group(2))
    #             self.logger.debug(f"[BURST][HEALTH] Parsed GPU: {utilization}% @ {frequency}MHz")
    #             return float(utilization)
    #         else:
    #             self.logger.debug(f"[BURST][HEALTH] No GR3D_FREQ pattern found in: {stats_output.strip()}")
    #     except (ValueError, IndexError, AttributeError) as e:
    #         self.logger.debug(f"[BURST][HEALTH] Error parsing tegrastats: {e}")
    #     return 0.0
    
    def get_system_health(self) -> Dict[str, float]:
        """Get current system health metrics."""
        return {
            "gpu_utilization": self.gpu_utilization,
            "queue_length": self.queue_length
        }
    
    def _parse_powermetrics_gpu(self, output: str) -> Optional[float]:
        """
        解析 powermetrics 输出，返回 GPU 利用率（%）。
        这里使用“GPU Power”字段并按 10 W 作为最大功率进行估算。
        """
        max_power_w = 10.0   # 经验值：Apple GPU 最大功率 ~ 10 W
        for line in output.splitlines():
            if "GPU Power:" in line:
                try:
                    # 例如: "GPU Power: 3.12 W"
                    part = line.split(":")[1].strip()
                    power_str = part.split()[0]
                    power_w = float(power_str)
                    util = min(power_w / max_power_w * 100.0, 100.0)
                    return round(util, 1)
                except Exception:
                    return None
        return None
    
    def update_queue_length(self, length: int):
        """Update the current queue length."""
        self.queue_length = length

@dataclass(frozen=True)
class BurstWorkloadConfig:
    """Absolute release schedule for a burst workload."""

    regime: str
    burst_start_seconds: float
    release_horizon_seconds: float
    transient_duration_seconds: Optional[float] = None

    @property
    def burst_end_seconds(self) -> float:
        if self.regime == "transient":
            return self.burst_start_seconds + self.transient_duration_seconds
        return self.release_horizon_seconds


def burst_workload_config_from_mapping(config: Dict) -> BurstWorkloadConfig:
    """Parse and validate the paper's transient/sustained burst definition."""
    regime = config.get("burst_regime")
    if regime not in {"transient", "sustained"}:
        raise ValueError(
            "burst_regime must be either 'transient' or 'sustained'"
        )

    def finite_non_negative(field_name: str) -> float:
        value = config.get(field_name)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(f"{field_name} must be a finite non-negative number")
        return float(value)

    burst_start_seconds = finite_non_negative("burst_start_seconds")
    release_horizon_seconds = finite_non_negative("release_horizon_seconds")
    if release_horizon_seconds <= burst_start_seconds:
        raise ValueError(
            "release_horizon_seconds must be greater than burst_start_seconds"
        )

    transient_duration_seconds = None
    if regime == "transient":
        transient_duration_seconds = finite_non_negative(
            "transient_duration_seconds"
        )
        if transient_duration_seconds <= 0:
            raise ValueError("transient_duration_seconds must be positive")
        if burst_start_seconds + transient_duration_seconds > release_horizon_seconds:
            raise ValueError(
                "transient burst window cannot exceed release_horizon_seconds"
            )
    elif "transient_duration_seconds" in config:
        raise ValueError(
            "transient_duration_seconds is only valid for a transient burst"
        )

    return BurstWorkloadConfig(
        regime=regime,
        burst_start_seconds=burst_start_seconds,
        release_horizon_seconds=release_horizon_seconds,
        transient_duration_seconds=transient_duration_seconds,
    )


def _dag_instance_groups(tasks: List[Dict]) -> List[Tuple[Tuple[int, int], List[Dict]]]:
    groups = defaultdict(list)
    for task in tasks:
        if task.get("DagIndex") is None or task.get("DagPeriod") is None:
            raise ValueError(
                "burst workloads require every task to define DagIndex and DagPeriod"
            )
        groups[(int(task["DagIndex"]), int(task["DagPeriod"]))].append(task)
    return sorted(
        groups.items(),
        key=lambda item: (
            min(float(task["ReleaseTime"]) for task in item[1]),
            item[0],
        ),
    )


def _evenly_selected_groups(groups, burst_ratio: float):
    """Select a deterministic, temporally distributed ratio of DAG releases."""
    selected = []
    accumulator = 0.0
    for group in groups:
        accumulator += burst_ratio
        if accumulator + 1e-12 >= 100.0:
            selected.append(group)
            accumulator -= 100.0
    return selected


class BurstTaskManager:
    """
    Manages burst task scenarios with proactive task dropping mechanism.
    """
    
    def __init__(self, 
                 gpu_threshold: float = 90.0,
                 queue_threshold: int = 8,
                 queue_recovery_threshold: Optional[int] = None,
                 persistence_window: int = 3,
                 default_drop_threshold: float = 0.5,
                 monitoring_interval: float = 0.1,
                 overload_sample_interval_seconds: float = 0.0,
                 workload_config: Optional[BurstWorkloadConfig] = None,
                 management_enabled: bool = True,
                 logger=None):
        if isinstance(gpu_threshold, bool) or not isinstance(
            gpu_threshold, (int, float)
        ) or not 0 <= gpu_threshold <= 100:
            raise ValueError("gpu_threshold must be between 0 and 100")
        if isinstance(queue_threshold, bool) or not isinstance(
            queue_threshold, int
        ) or queue_threshold < 0:
            raise ValueError("queue_threshold must be a non-negative integer")
        if isinstance(persistence_window, bool) or not isinstance(
            persistence_window, int
        ) or persistence_window <= 0:
            raise ValueError("persistence_window must be a positive integer")
        if queue_recovery_threshold is None:
            queue_recovery_threshold = max(0, queue_threshold - 1)
        if (
            isinstance(queue_recovery_threshold, bool)
            or not isinstance(queue_recovery_threshold, int)
            or not 0 <= queue_recovery_threshold <= queue_threshold
        ):
            raise ValueError(
                "queue_recovery_threshold must be an integer between zero "
                "and queue_threshold"
            )
        if (
            isinstance(overload_sample_interval_seconds, bool)
            or not isinstance(overload_sample_interval_seconds, (int, float))
            or not math.isfinite(overload_sample_interval_seconds)
            or overload_sample_interval_seconds < 0
        ):
            raise ValueError(
                "overload_sample_interval_seconds must be a finite "
                "non-negative number"
            )
        if isinstance(default_drop_threshold, bool) or not isinstance(
            default_drop_threshold, (int, float)
        ) or not 0 <= default_drop_threshold <= 1:
            raise ValueError("default_drop_threshold must be between 0 and 1")

        self.gpu_threshold = float(gpu_threshold)
        self.queue_threshold = queue_threshold
        self.queue_recovery_threshold = queue_recovery_threshold
        self.persistence_window = persistence_window
        self.overload_sample_interval_seconds = float(
            overload_sample_interval_seconds
        )
        self.default_drop_threshold = float(default_drop_threshold)
        self.workload_config = workload_config
        self.management_enabled = bool(management_enabled)
        self.logger = logger or logging.getLogger(__name__)
        self.health_monitor = SystemHealthMonitor(logger, monitoring_interval=monitoring_interval)
        self.dropped_tasks = []
        self.drop_records = []
        self.burst_mode_active = False
        self.consecutive_overload_ticks = 0
        self.maximum_consecutive_overload_ticks = 0
        self.overload_activation_count = 0
        self.workload_statistics = None
        self.last_overload_sample_time = None
        self.workload_phase = "normal"
        self.phase_transitions = []
        self.transient_recovery_completed = False
        self.transient_recovery_completion_seconds = None
        
    def start_monitoring(self):
        """Start the burst task monitoring."""
        self.health_monitor.start_monitoring()
    
    def stop_monitoring(self):
        """Stop the burst task monitoring."""
        self.health_monitor.stop_monitoring()
    
    def generate_burst_tasks(self, base_tasks: List[Dict], burst_ratio: float) -> List[Dict]:
        """
        Duplicate complete DAG releases inside the configured burst window.

        A 100 percent burst adds one DAG release for every base DAG release in
        the window. A 50 percent burst adds one for half of those releases,
        distributed across the window. Clones retain release times, deadlines,
        and priorities but receive an independent DAG-period identity.
        """
        if (
            isinstance(burst_ratio, bool)
            or not isinstance(burst_ratio, (int, float))
            or not math.isfinite(burst_ratio)
            or not 0 <= burst_ratio <= 100
        ):
            raise ValueError("burst_ratio must be between 0 and 100")
        if self.workload_config is None:
            raise ValueError("a validated burst workload configuration is required")
        if not base_tasks:
            self.workload_statistics = self._workload_statistics(
                burst_ratio, 0, 0, 0, 0
            )
            return []

        maximum_release = max(float(task["ReleaseTime"]) for task in base_tasks)
        if maximum_release > self.workload_config.release_horizon_seconds:
            raise ValueError(
                "release_horizon_seconds must cover every base-task ReleaseTime"
            )

        groups = _dag_instance_groups(base_tasks)
        eligible_groups = [
            group
            for group in groups
            if self.workload_config.burst_start_seconds
            <= min(float(task["ReleaseTime"]) for task in group[1])
            < self.workload_config.burst_end_seconds
        ]
        selected_groups = _evenly_selected_groups(eligible_groups, burst_ratio)
        maximum_period = max(int(task["DagPeriod"]) for task in base_tasks)
        burst_tasks = []
        for burst_instance_index, ((source_dag_index, source_period), tasks) in enumerate(
            selected_groups, start=1
        ):
            burst_period = maximum_period + burst_instance_index
            for original in tasks:
                duplicate = deepcopy(original)
                orig_id = duplicate["TaskId"]
                duplicate["TaskId"] = (
                    f"{orig_id}_burst_{self.workload_config.regime}_"
                    f"{burst_instance_index}"
                )
                duplicate["ConstituentTaskIds"] = [duplicate["TaskId"]]
                duplicate["DagPeriod"] = burst_period
                merge_suffix = str(duplicate["MergeKey"]).split("/", 2)[-1]
                duplicate["MergeKey"] = (
                    f"dag={source_dag_index}/period={burst_period}/"
                    f"{merge_suffix}"
                )
                duplicate["IsBurstTask"] = True
                duplicate["BurstRegime"] = self.workload_config.regime
                duplicate["BurstInstanceIndex"] = burst_instance_index
                duplicate["BurstSourceDagIndex"] = source_dag_index
                duplicate["BurstSourceDagPeriod"] = source_period
                duplicate.pop("SignalMsg", None)
                burst_tasks.append(duplicate)

        self.workload_statistics = self._workload_statistics(
            burst_ratio,
            len(groups),
            len(eligible_groups),
            len(selected_groups),
            len(burst_tasks),
        )
        self.logger.info(
            "[BURST] Generated %d nodes from %d additional DAG releases "
            "(%s, ratio=%s%%, window=[%.3f, %.3f)).",
            len(burst_tasks),
            len(selected_groups),
            self.workload_config.regime,
            burst_ratio,
            self.workload_config.burst_start_seconds,
            self.workload_config.burst_end_seconds,
        )
        return burst_tasks

    def _set_workload_phase(self, phase: str, current_time: float) -> None:
        if phase == self.workload_phase:
            return
        self.phase_transitions.append(
            {
                "from": self.workload_phase,
                "to": phase,
                "time_seconds": float(current_time),
            }
        )
        self.workload_phase = phase

    def _reset_overload_state(self) -> None:
        self.consecutive_overload_ticks = 0
        self.burst_mode_active = False

    def _update_workload_phase(
        self, task_queue: List[Dict], current_time: float
    ) -> str:
        if self.workload_config is None:
            return self.workload_phase
        if (
            self.workload_statistics is not None
            and self.workload_statistics.get("burst_ratio_percent") == 0.0
        ):
            self._set_workload_phase("normal", current_time)
            self._reset_overload_state()
            return self.workload_phase
        if current_time < self.workload_config.burst_start_seconds:
            self._set_workload_phase("normal", current_time)
            return self.workload_phase
        if self.workload_config.regime == "sustained":
            self._set_workload_phase("burst_active", current_time)
            return self.workload_phase
        if current_time < self.workload_config.burst_end_seconds:
            self._set_workload_phase("burst_active", current_time)
            return self.workload_phase

        # A transient has stopped producing new work. Enter recovery even when
        # the first post-window observation finds no residual Burst node, so
        # the transition is explicit and auditable in every completed run.
        if self.workload_phase == "burst_active":
            self._set_workload_phase("recovery", current_time)
        residual_burst = any(
            task.get("IsBurstTask", False)
            and task.get("BurstRegime") == "transient"
            for task in task_queue
        )
        if residual_burst or len(task_queue) > self.queue_recovery_threshold:
            self._set_workload_phase("recovery", current_time)
            return self.workload_phase

        self._set_workload_phase("normal", current_time)
        self.transient_recovery_completed = True
        self.transient_recovery_completion_seconds = float(current_time)
        self._reset_overload_state()
        return self.workload_phase

    def finalize_workload(self, current_time: float) -> None:
        """Finalize the Burst state after the execution queue becomes empty."""
        self._update_workload_phase([], current_time)

    def _workload_statistics(
        self,
        burst_ratio,
        base_dag_release_count,
        eligible_dag_release_count,
        added_dag_release_count,
        added_node_count,
    ):
        config = asdict(self.workload_config)
        config["burst_end_seconds"] = self.workload_config.burst_end_seconds
        return {
            **config,
            "burst_ratio_percent": float(burst_ratio),
            "base_dag_release_count": base_dag_release_count,
            "eligible_dag_release_count": eligible_dag_release_count,
            "added_dag_release_count": added_dag_release_count,
            "added_node_count": added_node_count,
        }
    
    def calculate_criticality_score(self, task: Dict, current_time: float) -> float:
        """
        Calculate the criticality score for a task.
        
        Criticality score formula per spec: C_i = 1 - (S_i / D_i)
        where S_i = D_i - t is the slack time, D_i is the relative intermediate deadline,
        and t is the elapsed time since task release.
        
        Args:
            task: Task dictionary containing deadline and other attributes
            current_time: Current time since task start
            
        Returns:
            Criticality score (higher = more critical)
        """
        try:
            # Here current_time is expected to be relative to TaskStartTime
            deadline = float(task.get("Deadline", 0.0))       # relative to TaskStartTime
            release_time = float(task.get("ReleaseTime", 0.0)) # relative to TaskStartTime

            # Relative intermediate deadline duration D_i
            relative_deadline = deadline - release_time
            if relative_deadline <= 0:
                return 0.0
            
            # Elapsed time since release t (non-negative)
            elapsed_time = max(0.0, current_time - release_time)

            # Slack S_i = D_i - t
            slack_time = relative_deadline - elapsed_time

            # C_i = 1 - (S_i / D_i)
            criticality = 1.0 - (slack_time / relative_deadline)
            # Clamp between 0 and 1
            criticality = max(0.0, min(1.0, criticality))
            return criticality
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"[BURST] Error calculating criticality score: {e}")
            return 0.0
    
    def is_overload_detected(self, sample_time: Optional[float] = None) -> bool:
        """
        Check if system overload is detected based on health metrics.
        
        Returns:
            True if overload detected, False otherwise
        """
        sample_time = time.monotonic() if sample_time is None else sample_time
        if (
            self.last_overload_sample_time is not None
            and sample_time - self.last_overload_sample_time
            < self.overload_sample_interval_seconds
        ):
            return self.burst_mode_active
        self.last_overload_sample_time = sample_time

        health = self.health_monitor.get_system_health()
        gpu_util = health.get("gpu_utilization", 0.0)
        queue_len = health.get("queue_length", 0)
        
        queue_limit = (
            self.queue_recovery_threshold
            if self.burst_mode_active
            else self.queue_threshold
        )
        raw_overload = gpu_util > self.gpu_threshold or queue_len > queue_limit
        if raw_overload:
            self.consecutive_overload_ticks += 1
            self.maximum_consecutive_overload_ticks = max(
                self.maximum_consecutive_overload_ticks,
                self.consecutive_overload_ticks,
            )
        else:
            self.consecutive_overload_ticks = 0

        sustained_overload = self.burst_mode_active or (
            self.consecutive_overload_ticks >= self.persistence_window
        )
        if sustained_overload and not self.burst_mode_active:
            self.logger.warning(
                "[BURST] Sustained overload detected after "
                f"{self.consecutive_overload_ticks} ticks: "
                f"GPU={gpu_util:.1f}%, Queue={queue_len}"
            )
            self.burst_mode_active = True
            self.overload_activation_count += 1
        elif not raw_overload and self.burst_mode_active:
            self.logger.info(f"[BURST] Overload resolved: GPU={gpu_util:.1f}%, Queue={queue_len}")
            self.burst_mode_active = False
        
        return self.burst_mode_active
    
    def proactive_drop(self, task_queue: List[Dict], current_time: float) -> Tuple[List[Dict], List[Dict]]:
        """
        Implement proactive task dropping algorithm.
        
        Args:
            task_queue: List of tasks in the queue
            current_time: Current time since system start
            
        Returns:
            Tuple of (remaining_tasks, dropped_tasks)
        """
        if not self.management_enabled:
            return task_queue, []

        phase = self._update_workload_phase(task_queue, current_time)
        if phase == "normal":
            self._reset_overload_state()
            return task_queue, []
        if not self.is_overload_detected():
            return task_queue, []
        
        # Evaluate each already-released queued task independently. The caller
        # passes tasks in scheduler order, which must remain unchanged for the
        # retained tasks so Burst management does not silently replace EDF or
        # LLF-DAG with a different scheduling policy.
        tasks_with_scores = []
        for index, task in enumerate(task_queue):
            criticality = self.calculate_criticality_score(task, current_time)
            tasks_with_scores.append((index, task, criticality))
        
        # Determine how many tasks to drop based on individual drop thresholds
        candidates = []
        for index, task, criticality in tasks_with_scores:
            drop_threshold = float(
                task.get("DropThreshold", self.default_drop_threshold)
            )
            droppable = bool(task.get("Droppable", drop_threshold > 0.0))
            if phase == "recovery" and not task.get("IsBurstTask", False):
                continue
            if droppable and drop_threshold > 0.0 and criticality < drop_threshold:
                candidates.append((index, task, criticality, drop_threshold))

        # Burst replicas are shed before baseline work. Within the same class,
        # lower-priority and lower-criticality work is removed first.
        candidates.sort(
            key=lambda item: (
                not bool(item[1].get("IsBurstTask", False)),
                int(item[1].get("Priority", 0)),
                item[2],
                item[0],
            )
        )
        drop_budget = max(
            1, len(task_queue) - self.queue_recovery_threshold
        )
        selected = candidates[:drop_budget]
        selected_indices = {item[0] for item in selected}
        dropped_tasks = []
        for index, task, criticality, drop_threshold in selected:
            dropped_tasks.append(task)
            self.drop_records.append(
                {
                    "task_id": task.get("TaskId"),
                    "constituent_task_ids": list(
                        task.get("ConstituentTaskIds", [task.get("TaskId")])
                    ),
                    "criticality_score": criticality,
                    "drop_threshold": drop_threshold,
                    "is_burst_task": bool(task.get("IsBurstTask", False)),
                    "burst_regime": task.get("BurstRegime"),
                    "burst_source_dag_index": task.get(
                        "BurstSourceDagIndex"
                    ),
                    "burst_source_dag_period": task.get(
                        "BurstSourceDagPeriod"
                    ),
                    "workload_phase": phase,
                    "priority": task.get("Priority"),
                    "release_time_seconds": task.get("ReleaseTime"),
                    "deadline_seconds": task.get("Deadline"),
                }
            )
            self.logger.info(
                f"[BURST] Dropped task {task.get('TaskId', 'Unknown')} "
                f"with criticality {criticality:.3f} "
                f"(threshold: {drop_threshold:.3f}, phase: {phase})"
            )

        remaining_tasks = [
            task
            for index, task in enumerate(task_queue)
            if index not in selected_indices
        ]
        
        self.dropped_tasks.extend(dropped_tasks)
        if len(dropped_tasks) > 0:
            self.logger.info(f"[BURST] Dropped {len(dropped_tasks)} tasks, "
                        f"remaining {len(remaining_tasks)} tasks")
        
        self._update_workload_phase(remaining_tasks, current_time)
        return remaining_tasks, dropped_tasks
    
    def get_burst_statistics(self) -> Dict:
        """Get statistics about burst management."""
        return {
            "management_enabled": self.management_enabled,
            "workload": self.workload_statistics,
            "burst_mode_active": self.burst_mode_active,
            "dropped_tasks_count": len(self.dropped_tasks),
            "drop_records": self.drop_records,
            "current_gpu_utilization": self.health_monitor.gpu_utilization,
            "current_queue_length": self.health_monitor.queue_length,
            "gpu_threshold": self.gpu_threshold,
            "queue_threshold": self.queue_threshold,
            "queue_recovery_threshold": self.queue_recovery_threshold,
            "persistence_window": self.persistence_window,
            "overload_sample_interval_seconds": (
                self.overload_sample_interval_seconds
            ),
            "consecutive_overload_ticks": self.consecutive_overload_ticks,
            "maximum_consecutive_overload_ticks": self.maximum_consecutive_overload_ticks,
            "overload_activation_count": self.overload_activation_count,
            "drop_threshold": self.default_drop_threshold,
            "workload_phase": self.workload_phase,
            "phase_transitions": self.phase_transitions,
            "transient_recovery_completed": self.transient_recovery_completed,
            "transient_recovery_completion_seconds": (
                self.transient_recovery_completion_seconds
            ),
        }
    
    def update_queue_length(self, length: int):
        """Update the current queue length for monitoring."""
        self.health_monitor.update_queue_length(length)

class BurstAwareTaskScheduler:
    """
    Task scheduler that integrates burst task management.
    """
    
    def __init__(self, 
                 burst_manager: BurstTaskManager,
                 base_scheduler,
                 logger=None):
        self.burst_manager = burst_manager
        self.base_scheduler = base_scheduler
        self.logger = logger or logging.getLogger(__name__)
        
    def schedule_tasks(self, task_queue: List[Dict], current_time: float) -> Tuple[List[Dict], List[Dict]]:
        """
        Schedule tasks with burst awareness.
        
        Args:
            task_queue: List of tasks to schedule
            current_time: Current time since system start
            
        Returns:
            Tuple of (scheduled_tasks, dropped_tasks)
        """
        # Update queue length for monitoring
        self.burst_manager.update_queue_length(len(task_queue))
        
        # Check for burst conditions and apply proactive dropping
        remaining_tasks, dropped_tasks = self.burst_manager.proactive_drop(task_queue, current_time)
        
        # Apply base scheduler to remaining tasks
        scheduled_tasks = remaining_tasks.copy()
        
        # Apply sorting based on scheduler type
        if self.base_scheduler == 'edf':
            # Sort by deadline (EDF)
            scheduled_tasks.sort(key=lambda x: x.get("Deadline", 0))
        elif self.base_scheduler == 'priority':
            # Sort by priority (descending)
            scheduled_tasks.sort(key=lambda x: x.get("Priority", 0), reverse=True)
        elif self.base_scheduler == 'fcfs':
            # Sort by release time (FCFS)
            scheduled_tasks.sort(key=lambda x: x.get("ReleaseTime", 0))
        elif self.base_scheduler == 'fcls':
            # Sort by release time (descending) (FCLS)
            scheduled_tasks.sort(key=lambda x: x.get("ReleaseTime", 0), reverse=True)
        
        return scheduled_tasks, dropped_tasks
    
    def get_burst_statistics(self) -> Dict:
        """Get burst management statistics."""
        return self.burst_manager.get_burst_statistics()
