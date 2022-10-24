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
