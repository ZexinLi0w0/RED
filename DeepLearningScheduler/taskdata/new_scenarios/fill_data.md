Based on the filled latex table, update data and address comment in main text. Make sure to check logic and make transition smooth. All numbers keep two decimal places.

Results Table:
Device | Scenario                     | Deadline | Approach | Missing Deadline Rate | Finished Time      | Deadline Time | QoE Score          
----------------------------------------------------------------------------------------------------------------------------------------------
AGX    | Urban navigation             | Loose    | Baseline | 0.52                  | 27.89833974838257  | 16.68         | 0.07816459325612621
AGX    | Urban navigation             | Loose    | RED-IDA  | 0.02                  | 24.648674964904785 | 16.68         | 0.10664121306395663
AGX    | Urban navigation             | Loose    | RED-FG   | 0.06666666666666667   | 27.935713052749634 | 16.68         | 0.07792528114828812
AGX    | Urban navigation             | Loose    | RED      | 0.0                   | 14.236137390136719 | 16.68         | 1.0                
AGX    | Emergency obstacle avoidance | Loose    | Baseline | 0.375                 | 21.931200742721558 | 16.5          | 0.14903875163192004
AGX    | Emergency obstacle avoidance | Loose    | RED-IDA  | 0.125                 | 18.764435529708862 | 16.5          | 0.29581111155733886
AGX    | Emergency obstacle avoidance | Loose    | RED-FG   | 0.03333333333333333   | 21.904763221740723 | 16.5          | 0.1496586729160575 
AGX    | Emergency obstacle avoidance | Loose    | RED      | 0.0                   | 13.701050519943237 | 16.5          | 1.0                
AGX    | Night driving                | Loose    | Baseline | 0.16666666666666666   | 13.96184492111206  | 14.13         | 1.0                
AGX    | Night driving                | Loose    | RED-IDA  | 0.13333333333333333   | 11.354617595672607 | 14.13         | 1.0                
AGX    | Night driving                | Loose    | RED-FG   | 0.26666666666666666   | 13.998088598251343 | 14.13         | 1.0                
AGX    | Night driving                | Loose    | RED      | 0.03333333333333333   | 12.249221563339233 | 14.13         | 1.0 

Nano   | Urban navigation             | Loose    | Baseline | 1.0                   | 32.24140024185181  | 17.41         | 0.06027065480277153
Nano   | Urban navigation             | Loose    | RED-IDA  | 1.0                   | 31.372717142105103 | 17.41         | 0.06378120105583825
Nano   | Urban navigation             | Loose    | RED-FG   | 1.0                   | 29.16496181488037  | 17.41         | 0.07486345881152094
Nano   | Urban navigation             | Loose    | RED      | 0.16666666666666666   | 23.037281274795532 | 17.41         | 0.1445964699278325 
Nano   | Emergency obstacle avoidance | Loose    | Baseline | 1.0                   | 24.880135774612427 | 17.41         | 0.11295430159006623
Nano   | Emergency obstacle avoidance | Loose    | RED-IDA  | 1.0                   | 25.164552211761475 | 17.41         | 0.10926410335616027
Nano   | Emergency obstacle avoidance | Loose    | RED-FG   | 1.0                   | 23.02457618713379  | 17.41         | 0.14487626968656375
Nano   | Emergency obstacle avoidance | Loose    | RED      | 0.43333333333333335   | 22.200773239135742 | 17.41         | 0.16566161324249418
Nano   | Night driving                | Loose    | Baseline | 1.0                   | 16.067562341690063 | 14.55         | 0.3853016028032262 
Nano   | Night driving                | Loose    | RED-IDA  | 1.0                   | 16.308627128601074 | 14.55         | 0.35102574835996636
Nano   | Night driving                | Loose    | RED-FG   | 1.0                   | 16.421063899993896 | 14.55         | 0.33704130475915406
Nano   | Night driving                | Loose    | RED      | 0.9666666666666667    | 13.650720357894897 | 14.55         | 1.0

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