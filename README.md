# RED
ATC’23 Robotic Environmental Dynamics (RED)

## Idea

1. Identify an experimental robotic scenario that highlight potential environ-
mental dynamics 

2. Target three observations or challenges: 

a. workload structure change (mainly adding or sometimes reducing nodes into the graph, or even
simply structural changes), coupled with the fact that end to end deadline should
never change 

b. potentially weak candidate: fundamental criticality changes at
runtime; multi-tasking, mixed CPU/DNN workloads; MIMO, 

c. memory issue
due to hardware constraints

If MIMO, then two long subsections in Sec. 2. first one due to workload
strctural change (three pars-add, reduce, change), second one due to MIMO
(mem challenge, optimization flexibility opportunities).

## Plan

1. Case study:

1.1 Design: experimental dynamics, dynamic workloads structures, dynamic workload criticality.

1.2 Basic approach: multi-tasking mixed CPU/DNN workload + MIMO.

2. System design:

2.1 MIMO: naturally solve memory-limit challenge, involve bigger reconfiguration space (can enroll layer-level quantification (similar to NeuOS)).

2.2 Adaptive enrionmentally-aware mechanism: heuristically re-structure / re-scheduling when meeting environmental dynamics.

2.3 Scheduling policy: RR, EDF, Preempt-RT (or some dynamic scheudling alg. @Cong)

2.4 Resource reservation scheme: Best-Effort, Highest-Throughput, etc. ... (ref to Shin Pei ATC')

2.5 Proactive and safe-critical strategy: reduce latency for tight-deadline and boost performance for loose-deadline; stop / reboot tasks when definitely miss sporadic task's deadline.

3. Evaluation:

3.1 Setup: DNN, embedded systems (AGX/TX2/Nano/Orin) / robotics testbed (build sth. or Jetbot).

3.2 Experiments: (TODO)

## Discussion
MIMO的是系统本质的要求：（如果end2end当作黑盒来看）

现有系统是多个独立的SISO/MISO/SIMO/small MIMO组成的 

现有的2个问题：1. 由于独立模型之间存在sharable knowledge，所以memory usage suboptimal 2. 在现有MI/MO中都会存在async IO问题

为了解决这2个问题

我们引入了end2end MIMO model

contribution: 1. miminize memory usage 2. support async IO

怎么写故事线：是否加入dynamic workloads

改一下ATC meeting时间 +16国内时间

xiaoxi: 方法不novel；宏观上是否加入dynamic workloads，像是硬凹的；case study可能需要过度构造，不真实（但还OK）；implementation上，不加入PAM，理论上能够搞完

From Cong意见：

a: 方法不novel 🆗

b: 要加入dynamic workload，因为另外两块在system-level不够

c: case study主要强调是由于robotic specific environmental dynamics带来的几个challenge 我们提出一个ecosystem全面解决 效果好；突出强调一个environmental dynamics对于robotics在系统层面 调度 内存 的challenges

d: 
1. high-level: workload dynamic 有不同的model 而且有timing constraint。system-level上有resource reservation/scheduling问题

2. low-level: 可能在某一节多个SISO yolo可能不够，比如天然地体现是多输入/多任务场景 induce MIMO idea就完美了
