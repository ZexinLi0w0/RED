platform="agx"
deadline="tight"
test_case_num=10

mkdir -p exp1/raw_data
for (( i=0 ; i < ${test_case_num} ; i++ ))
do python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/${platform}_${deadline}.json" -a "baseline"
done
mv log.info.txt exp1/raw_data/${platform}_${deadline}_baseline.txt
for (( i=0 ; i < ${test_case_num} ; i++ ))
do python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/${platform}_${deadline}.json" -a "feedback"
done
mv log.info.txt exp1/raw_data/${platform}_${deadline}_progress_tracker.txt
for (( i=0 ; i < ${test_case_num} ; i++ ))
do python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/${platform}_${deadline}.json" -a "fine-grained"
done
mv log.info.txt exp1/raw_data/${platform}_${deadline}_fine_grained.txt
for (( i=0 ; i < ${test_case_num} ; i++ ))
do python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/${platform}_${deadline}.json" -a "feedback-fine-grained"
done
mv log.info.txt exp1/raw_data/${platform}_${deadline}_REDdrop.txt

mkdir -p exp1/processed_data
cat exp1/raw_data/${platform}_${deadline}_baseline.txt | grep End | grep -oE ": [0-9]+.[0-9]+" | grep -oE "[0-9]+.[0-9]+" >> exp1/processed_data/${platform}_${deadline}_baseline.txt
cat exp1/raw_data/${platform}_${deadline}_progress_tracker.txt | grep End | grep -oE ": [0-9]+.[0-9]+" | grep -oE "[0-9]+.[0-9]+" >> exp1/processed_data/${platform}_${deadline}_progress_tracker.txt
cat exp1/raw_data/${platform}_${deadline}_fine_grained.txt | grep End | grep -oE ": [0-9]+.[0-9]+" | grep -oE "[0-9]+.[0-9]+" >> exp1/processed_data/${platform}_${deadline}_fine_grained.txt
cat exp1/raw_data/${platform}_${deadline}_REDdrop.txt | grep End | grep -oE ": [0-9]+.[0-9]+" | grep -oE "[0-9]+.[0-9]+" >> exp1/processed_data/${platform}_${deadline}_REDdrop.txt




platform="agx"
deadline="loose"
test_case_num=10

mkdir -p exp1/raw_data
for (( i=0 ; i < ${test_case_num} ; i++ ))
do python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/${platform}_${deadline}.json" -a "baseline"
done
mv log.info.txt exp1/raw_data/${platform}_${deadline}_baseline.txt
for (( i=0 ; i < ${test_case_num} ; i++ ))
do python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/${platform}_${deadline}.json" -a "feedback"
done
mv log.info.txt exp1/raw_data/${platform}_${deadline}_progress_tracker.txt
for (( i=0 ; i < ${test_case_num} ; i++ ))
do python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/${platform}_${deadline}.json" -a "fine-grained"
done
mv log.info.txt exp1/raw_data/${platform}_${deadline}_fine_grained.txt
for (( i=0 ; i < ${test_case_num} ; i++ ))
do python "./main.py" -c "./simo-handler_config.json" -t "./TaskConfigs/simo/${platform}_${deadline}.json" -a "feedback-fine-grained"
done
mv log.info.txt exp1/raw_data/${platform}_${deadline}_REDdrop.txt

mkdir -p exp1/processed_data
cat exp1/raw_data/${platform}_${deadline}_baseline.txt | grep End | grep -oE ": [0-9]+.[0-9]+" | grep -oE "[0-9]+.[0-9]+" >> exp1/processed_data/${platform}_${deadline}_baseline.txt
cat exp1/raw_data/${platform}_${deadline}_progress_tracker.txt | grep End | grep -oE ": [0-9]+.[0-9]+" | grep -oE "[0-9]+.[0-9]+" >> exp1/processed_data/${platform}_${deadline}_progress_tracker.txt
cat exp1/raw_data/${platform}_${deadline}_fine_grained.txt | grep End | grep -oE ": [0-9]+.[0-9]+" | grep -oE "[0-9]+.[0-9]+" >> exp1/processed_data/${platform}_${deadline}_fine_grained.txt
cat exp1/raw_data/${platform}_${deadline}_REDdrop.txt | grep End | grep -oE ": [0-9]+.[0-9]+" | grep -oE "[0-9]+.[0-9]+" >> exp1/processed_data/${platform}_${deadline}_REDdrop.txt
