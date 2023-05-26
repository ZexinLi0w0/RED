import torch
import time
import argparse
import subprocess
import os

def matrix_multiplication(matrix_size, duration, log_file):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    matrix1 = torch.randn(matrix_size, matrix_size, device=device)
    matrix2 = torch.randn(matrix_size, matrix_size, device=device)

    start_time = time.time()
    end_time = start_time + duration

    log_file.write("Matrix size: {}\n".format(matrix_size))
    log_file.write("Duration: {} seconds\n".format(duration))
    log_file.write("Start time: {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))))
    log_file.write("GPU Usage:\n")
    log_file.flush()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_file_path = os.path.join(script_dir, 'temp_gpu_usage.log')
    update_simple_time = ''
    tegrastats_process = subprocess.Popen("tegrastats --readall --interval 1000 > {}".format(temp_file_path), shell=True)
    
    while time.time() < end_time:
        _result = torch.matmul(matrix1, matrix2)
    # wait for tegrastats to finish writing to file
    tegrastats_process.terminate()
    tegrastats_process.wait()
    elapsed_time = time.time() - start_time
    log_file.write("Elapsed time: {} seconds\n".format(elapsed_time))
    time.sleep(1)
    raw_data = ""
    elapsed_time = 0
    total_gpu_usage = 0
    with open(temp_file_path, 'r') as f:
        for line in f.readlines():
            gpu_stats = line.strip()
            if gpu_stats is None or gpu_stats == "":
                continue
            gpu_usage = get_gpu_usage(gpu_stats)
            sample_time = gpu_stats[0:19]
            print(f'sample_time: {sample_time}')
            # skip repeated sample
            if update_simple_time == sample_time:
                continue
            elapsed_time += 1
            total_gpu_usage += float(gpu_usage)
            update_simple_time = sample_time
            log_file.write("{} GPU Usage: {}%\n".format(sample_time, gpu_usage))
            print("{} GPU Usage: {}%".format(sample_time, gpu_usage))
            raw_data += gpu_stats + "\n"

    
    log_file.write("Average GPU Usage: {}%\n".format(total_gpu_usage / elapsed_time))
    log_file.write("Raw Data: \n {}".format(raw_data))
    log_file.close()

    print("Matrix multiplication completed")
    # os.remove(temp_file_path)

def get_gpu_usage(stats):
    gpu_usage = None
    stats = stats.split("GR3D_FREQ", 1)
    if len(stats) > 1:
        stats = stats[1].split()[0]
        gpu_usage = stats.replace("%", "")
    return gpu_usage


def main():
    parser = argparse.ArgumentParser(description='Matrix multiplication using PyTorch on GPU')
    parser.add_argument('-s', '--matrix_size', type=int, default=1000, help='Size of the square matrix')
    parser.add_argument('-d', '--duration', type=int, default=10, help='Duration of matrix multiplication in seconds')
    parser.add_argument('-l', '--log_file', type=str, default='gpu_usage.log', help='Log file to store GPU usage')
    args = parser.parse_args()

    with open(args.log_file, 'w') as log_file:
        matrix_multiplication(args.matrix_size, args.duration, log_file)
if __name__ == '__main__':
    main()
