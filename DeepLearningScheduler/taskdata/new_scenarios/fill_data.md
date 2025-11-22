Based on the filled latex table, update data and address comment in main text. Make sure to check logic and make transition smooth. All numbers keep two decimal places.

Results Table:
Device | Scenario                     | Deadline | Approach | Missing Deadline Rate | Finished Time      | Deadline Time      | QoE Score         
--------------------------------------------------------------------------------------------------------------------------------------------------
Mac    | Urban navigation             | Loose    | Baseline | 0.0                   | 7.763628005981445  | 5.946              | 0.3435458301423162
Mac    | Urban navigation             | Loose    | RED-IDA  | 0.0                   | 4.123502969741821  | 5.946              | 1.0               
Mac    | Urban navigation             | Loose    | RED-FG   | 0.0                   | 7.766097068786621  | 5.946              | 0.3432397542493702
Mac    | Urban navigation             | Loose    | RED      | 0.0                   | 3.2012200355529785 | 5.946              | 1.0               
Mac    | Emergency obstacle avoidance | Loose    | Baseline | 0.275                 | 3.4520747661590576 | 2.8709999999999996 | 0.6207836735675429
Mac    | Emergency obstacle avoidance | Loose    | RED-IDA  | 0.0                   | 2.627624988555908  | 2.8709999999999996 | 1.0               
Mac    | Emergency obstacle avoidance | Loose    | RED-FG   | 0.03333333333333333   | 3.4481253623962402 | 2.8709999999999996 | 0.6223878334113846
Mac    | Emergency obstacle avoidance | Loose    | RED      | 0.0                   | 2.2696919441223145 | 2.8709999999999996 | 1.0               
Mac    | Night driving                | Loose    | Baseline | 0.0                   | 1.4355590343475342 | 1.4460000000000002 | 1.0               
Mac    | Night driving                | Loose    | RED-IDA  | 0.0                   | 1.1590237617492676 | 1.4460000000000002 | 1.0               
Mac    | Night driving                | Loose    | RED-FG   | 0.03333333333333333   | 1.4358839988708496 | 1.4460000000000002 | 1.0               
Mac    | Night driving                | Loose    | RED      | 0.0                   | 1.1465232372283936 | 1.4460000000000002 | 1.0 

Adjusted QoE Score Table:
================================================================================
Device: Mac
================================================================================

  Scenario: Emergency obstacle avoidance
--------------------------------------------------------------------------------
    Deadline: Loose

Approach       λ=0.01       
----------------------------
Baseline          0.630154* 
RED-IDA           1.000000* 
RED-FG            0.631742* 
RED               1.000000* 

  Scenario: Night driving
--------------------------------------------------------------------------------
    Deadline: Loose

Approach       λ=0.01       
----------------------------
Baseline          1.000000* 
RED-IDA           1.000000* 
RED-FG            1.000000* 
RED               1.000000* 

  Scenario: Urban navigation
--------------------------------------------------------------------------------
    Deadline: Loose

Approach       λ=0.01       
----------------------------
Baseline          0.352622* 
RED-IDA           1.000000* 
RED-FG            0.352312* 
RED               1.000000* 


Text:
\begin{table}[!tbp]
\centering
\caption{Overall performance of \tool evaluated on extended minibenchmarks on tight deadline settings, resource-constrained intelligent robotic systems. \tool optimizes throughput, real-time performance, and QoE, demonstrating substantial improvements over baseline methods. }
\label{tab:extended_overall_effectiveness}
\resizebox{\textwidth}{!}{
\begin{tabular}{l|cccc|cccc|cccc}
\hline
\multirow{2}{*}{Platform} 
& \multicolumn{4}{c|}{Urban navigation} 
& \multicolumn{4}{c|}{Emergency obstacle avoidance} 
& \multicolumn{4}{c}{Night driving} \\
\cline{2-13}
& EDF & RED-FG & RED-IDA & RED 
& EDF & RED-FG & RED-IDA & RED
& EDF & RED-FG & RED-IDA & RED \\
\hline
\multicolumn{13}{c}{End-to-end Latency} \\
\hline
Nano Orin     & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
AGX Orin      & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
MacBook Pro   & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
\hline
\multicolumn{13}{c}{Deadline Miss Rate} \\
\hline
Nano Orin     & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
AGX Orin      & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
MacBook Pro   & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
\hline
\multicolumn{13}{c}{QoE} \\
\hline
Nano Orin     & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
AGX Orin      & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
MacBook Pro   & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} & \zx{xx} \\
\hline
\end{tabular}}
\end{table}