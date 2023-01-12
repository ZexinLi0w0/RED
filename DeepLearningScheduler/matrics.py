import math
def throughput_score(latencies):
    """
    Calculates the throughput score for a given list of latencies.
    latencies: Array<Latency:int>
    """
    latency_avg = sum(latencies) / len(latencies)
    return round(min(latencies) / latency_avg, 4)

def RTscore(finished_times, deadlines):
    missing_deadline = []
    for i in range(len(finished_times)):
        if(finished_times[i] > deadlines[i]):
            missing_deadline.append(1)
        else:
            missing_deadline.append(0)
    return 1 - (sum(missing_deadline) / len(missing_deadline))

def QoEScore(finished_times, deadlines, lambda_param = 1):
    """
    1 / (1 + e^lambda * (max(0, miss_deadline_time)))
    """
    QoEScore_total = 0

    for i in range(len(finished_times)):
        tmp = 1/(1 + math.pow(math.e, lambda_param) * max(0, finished_times[i] - deadlines[i]))
        QoEScore_total += tmp
    return QoEScore_total / len(finished_times)

if __name__ == "__main__":
    assert(throughput_score([1,2,3,4]) - 0.4 < 0.0001)
    assert(RTscore([3,3,4,3,3], [3,3,3,3,3]) - 0.8 < 0.0001)
    assert(QoEScore([3,3,4,3,3], [3,3,3,3,3]) - 0.8538 < 0.0001)
    print('All tests passed!')

        
         


