import argparse

def get_gpu_usage(stats):
    gpu_usage = None
    stats = stats.split("GR3D_FREQ", 1)
    if len(stats) > 1:
        stats = stats[1].split()[0]
        gpu_usage = stats.replace("%", "")
    return gpu_usage

def main():
    parser = argparse.ArgumentParser(description='Analysis tegrastats raw data')
    parser.add_argument('-l', '--log_file', type=str, default='raw_data.log', help='Log file to read GPU raw data')
    args = parser.parse_args()
    update_simple_time = ''
    elapsed_time = 0
    total_gpu_usage = 0
    with open('./gpu_analysis.log', 'w') as log_file:
        with open(args.log_file, 'r') as f:
            for line in f.readlines():
                gpu_stats = line.strip()
                if gpu_stats is None or gpu_stats == "":
                    continue
                gpu_usage = get_gpu_usage(gpu_stats)
                sample_time = gpu_stats[0:19]
                # skip repeated sample
                if update_simple_time == sample_time:
                    continue
                if(gpu_usage == None or gpu_usage == "0"):
                    continue
                elapsed_time += 1
                total_gpu_usage += float(gpu_usage)
                update_simple_time = sample_time
                log_file.write("{} GPU Usage: {}%\n".format(sample_time, gpu_usage))
                print("{} GPU Usage: {}%".format(sample_time, gpu_usage))
        
        print("Average GPU Usage: {}%".format(total_gpu_usage / elapsed_time))
        log_file.write("Average GPU Usage: {}%\n".format(total_gpu_usage / elapsed_time))
if __name__ == '__main__':
    main()