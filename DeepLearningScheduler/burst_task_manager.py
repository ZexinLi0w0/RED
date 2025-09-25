import time
import math
import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import subprocess
import threading
import platform
import queue

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
        
    def start_monitoring(self):
        """Start the system health monitoring thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.logger.info("[BURST] System health monitoring started")
    
    def stop_monitoring(self):
        """Stop the system health monitoring thread."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()
            self.logger.info("[BURST] System health monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop that continuously updates system health metrics."""
        while self.monitoring_active:
            try:
                # Update GPU utilization
                self.gpu_utilization = self._get_gpu_utilization()
                self.logger.debug(f"[BURST][HEALTH] GPU utilization: {self.gpu_utilization:.1f}%")
                
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

class BurstTaskManager:
    """
    Manages burst task scenarios with proactive task dropping mechanism.
    """
    
    def __init__(self, 
                 gpu_threshold: float = 80.0,
                 queue_threshold: int = 10,
                 default_drop_threshold: float = 0.5,
                 monitoring_interval: float = 0.1,
                 logger=None):
        self.gpu_threshold = gpu_threshold
        self.queue_threshold = queue_threshold
        self.default_drop_threshold = default_drop_threshold
        self.logger = logger or logging.getLogger(__name__)
        self.health_monitor = SystemHealthMonitor(logger, monitoring_interval=monitoring_interval)
        self.dropped_tasks = []
        self.burst_mode_active = False
        
    def start_monitoring(self):
        """Start the burst task monitoring."""
        self.health_monitor.start_monitoring()
    
    def stop_monitoring(self):
        """Stop the burst task monitoring."""
        self.health_monitor.stop_monitoring()
    
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
    
    def is_overload_detected(self) -> bool:
        """
        Check if system overload is detected based on health metrics.
        
        Returns:
            True if overload detected, False otherwise
        """
        health = self.health_monitor.get_system_health()
        gpu_util = health.get("gpu_utilization", 0.0)
        queue_len = health.get("queue_length", 0)
        
        overload = (gpu_util > self.gpu_threshold or queue_len > self.queue_threshold)
        
        if overload and not self.burst_mode_active:
            self.logger.warning(f"[BURST] Overload detected: GPU={gpu_util:.1f}%, Queue={queue_len}")
            self.burst_mode_active = True
        elif not overload and self.burst_mode_active:
            self.logger.info(f"[BURST] Overload resolved: GPU={gpu_util:.1f}%, Queue={queue_len}")
            self.burst_mode_active = False
        
        return overload
    
    def proactive_drop(self, task_queue: List[Dict], current_time: float) -> Tuple[List[Dict], List[Dict]]:
        """
        Implement proactive task dropping algorithm.
        
        Args:
            task_queue: List of tasks in the queue
            current_time: Current time since system start
            
        Returns:
            Tuple of (remaining_tasks, dropped_tasks)
        """
        if not self.is_overload_detected():
            return task_queue, []
        
        # Calculate criticality scores for all tasks
        # [TODO] This can be optimized by priority queue or min heap
        tasks_with_scores = []
        for task in task_queue:
            criticality = self.calculate_criticality_score(task, current_time)
            tasks_with_scores.append((task, criticality))
        
        # Sort tasks by criticality score (ascending - lower scores dropped first)
        tasks_with_scores.sort(key=lambda x: x[1])
        
        # Determine how many tasks to drop based on individual drop thresholds
        dropped_tasks = []
        remaining_tasks = []
        
        for task, criticality in tasks_with_scores:
            drop_threshold = float(task.get("DropThreshold", self.default_drop_threshold))
            
            # Drop task if its criticality is below its drop threshold
            if criticality < drop_threshold:
                dropped_tasks.append(task)
                self.logger.info(f"[BURST] Dropped task {task.get('TaskId', 'Unknown')} "
                               f"with criticality {criticality:.3f} (threshold: {drop_threshold:.3f})")
            else:
                remaining_tasks.append(task)
        
        self.dropped_tasks.extend(dropped_tasks)
        if len(dropped_tasks) > 0:
            self.logger.info(f"[BURST] Dropped {len(dropped_tasks)} tasks, "
                        f"remaining {len(remaining_tasks)} tasks")
        
        return remaining_tasks, dropped_tasks
    
    def get_burst_statistics(self) -> Dict:
        """Get statistics about burst management."""
        return {
            "burst_mode_active": self.burst_mode_active,
            "dropped_tasks_count": len(self.dropped_tasks),
            "current_gpu_utilization": self.health_monitor.gpu_utilization,
            "current_queue_length": self.health_monitor.queue_length,
            "gpu_threshold": self.gpu_threshold,
            "queue_threshold": self.queue_threshold
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