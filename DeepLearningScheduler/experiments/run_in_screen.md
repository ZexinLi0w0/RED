# 在 Screen 中运行实验脚本

## 快速开始

### 方法 1: 使用已存在的 screen 会话 "schedule"

```bash
# 1. 连接到已存在的 screen 会话
screen -r schedule

# 2. 在 screen 会话中，切换到项目目录并运行脚本
cd /experiment/zexin/ATC23/DeepLearningScheduler
bash experiments/run_agx_new_scenarios.sh

# 3. 按 Ctrl+A 然后按 D 来 detach（分离）screen 会话
# 脚本会继续在后台运行，日志会正常写入 agx_new_scenarios.log
```

### 方法 2: 创建新的 screen 会话并运行

```bash
# 1. 创建并进入名为 "schedule" 的 screen 会话
screen -S schedule

# 2. 在 screen 会话中运行脚本
cd /experiment/zexin/ATC23/DeepLearningScheduler
bash experiments/run_agx_new_scenarios.sh

# 3. 按 Ctrl+A 然后按 D 来 detach
```

### 方法 3: 一行命令直接启动（推荐）

```bash
# 在 screen 会话中直接运行，自动 detach
screen -dmS schedule bash -c "cd /experiment/zexin/ATC23/DeepLearningScheduler && bash experiments/run_agx_new_scenarios.sh"
```

## Screen 常用命令

```bash
# 列出所有 screen 会话
screen -ls

# 连接到名为 "schedule" 的会话
screen -r schedule

# 如果会话被标记为 Attached，强制连接
screen -rd schedule

# 在 screen 会话中：
#   Ctrl+A 然后 D  - detach（分离，脚本继续运行）
#   Ctrl+A 然后 K  - 杀死当前窗口
#   Ctrl+A 然后 C  - 创建新窗口
#   Ctrl+A 然后 N  - 切换到下一个窗口
#   Ctrl+A 然后 P  - 切换到上一个窗口
```

## 检查运行状态

```bash
# 1. 检查 screen 会话是否在运行
screen -ls

# 2. 实时查看日志文件（在另一个终端或重新连接后）
tail -f /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/new_scenarios/agx_new_scenarios.log

# 3. 检查进程是否在运行
ps aux | grep run_agx_new_scenarios.sh
ps aux | grep main.py
```

## 重新连接查看进度

```bash
# 重新连接到 screen 会话查看实时输出
screen -r schedule

# 查看日志文件
tail -f /experiment/zexin/ATC23/DeepLearningScheduler/taskdata/new_scenarios/agx_new_scenarios.log
```

## 注意事项

1. **日志文件位置**: 日志会自动写入 `taskdata/new_scenarios/agx_new_scenarios.log`（相对于项目根目录）
2. **脚本输出**: 所有输出（包括错误）都已重定向到日志文件，不会丢失
3. **SSH 断开**: 即使 SSH 连接断开，screen 会话中的脚本也会继续运行
4. **多个设备**: 可以在不同的 screen 会话中同时运行不同设备的脚本

## 同时运行多个设备

```bash
# 在 AGX 上
screen -dmS agx_exp bash -c "cd /experiment/zexin/ATC23/DeepLearningScheduler && bash experiments/run_agx_new_scenarios.sh"

# 在 Nano 上（通过 SSH）
ssh nano_user@nano_host
screen -dmS nano_exp bash -c "cd /home/zexin/ATC23/DeepLearningScheduler && bash experiments/run_nano_new_scenarios.sh"

# 在 Mac 上
screen -dmS mac_exp bash -c "cd /Users/rentao/Documents/Github\ Projects/ATC23/DeepLearningScheduler && bash experiments/run_mac_new_scenarios.sh"
```

