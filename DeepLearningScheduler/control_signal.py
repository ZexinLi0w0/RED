from enum import Enum

class SignalCommand(Enum):
    PING = "PING"
    LOADDATA = "LOADDATA"
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

if __name__ == "__main__":
    # test
    signal1 = generate_signal(1, SignalCommand.LOADDATA)
    signal2 = generate_signal(2, SignalCommand.RUN, "--width 100 --height 100")
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