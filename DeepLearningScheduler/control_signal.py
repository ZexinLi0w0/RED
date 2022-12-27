from enum import Enum

class SignalCommand(Enum):
    PING = "PING"
    LOADDATA = "LOADDATA"
    READY = "READY"
    RUN = "RUN"
    STOP = "STOP"
    EXIT = "EXIT"

def generate_signal(taskid, signal, *args):
    """
    Generate a signal to the task with the given taskid.
    The signal can have additional arguments.
    The signal is passed to the task as a string in the following format:
    "{taskid} {signal} {args1} {args2} {args3}"
    """
    assert signal in SignalCommand.__members__.values(), f"{signal} is not a valid signal command"
    signal_str = f"{taskid} {signal.value}"
    for arg in args:
        signal_str += f" {arg}"
    return signal_str



def parse_signal(signal_str):
    """
    Parses a signal string into a tuple (taskid, signal, *args).
    The signal string is in the following format:
    "{taskid} {signal} {args1} {args2} {args3}"
    """
    parts = signal_str.split()
    taskid = int(parts[0])
    signal = parts[1]
    args = parts[2:]
    return (taskid, signal, *args)


def convert_args_to_dict(args_data):
    """
    convert a list/string of arguments to a dictionary
    e.g. ["--width", "100", "--height", "100"] -> {"width": "100", "height": "100"}
    e.g. "--width 100 --height 100" -> {"width": "100", "height": "100"}
    """
    if(isinstance(args_data, str)):
        args_data = args_data.split()
    if(not isinstance(args_data, list)):
        return {}
    result = {}
    for i in range(0, len(args_data), 2):
        result[args_data[i][2:]] = args_data[i + 1]
    return result




if __name__ == "__main__":
    # test
    signal1 = generate_signal(1, SignalCommand.LOADDATA)
    signal2 = generate_signal(2, SignalCommand.RUN, "--width 100", "--height 100")
    # print(signal1)
    # print(signal2)
    # parse a signal string
    taskid, signal, *args = parse_signal(signal1)
    assert(taskid == 1)
    assert(SignalCommand[signal] == SignalCommand.LOADDATA)
    assert(args == [])
    taskid, signal, *args = parse_signal(signal2)
    assert(taskid == 2)
    assert(SignalCommand[signal] == SignalCommand.RUN)
    assert(args == ['--width', '100', '--height', '100'])
    formatted_dict = convert_args_to_dict(args)
    assert(formatted_dict['width'] == '100' and formatted_dict['height'] == '100')
    formatted_dict = convert_args_to_dict("--release_time 10 --height 100")
    assert(formatted_dict['release_time'] == '10' and formatted_dict['height'] == '100')