import asyncio
import queue
import logging
from enum import Enum

# self-defined modules
from control_signal import convert_args_to_dict, generate_signal, parse_signal, SignalCommand

class HandlerStatus(Enum):
    Entry = "Entry"
    Load = "Load"
    Ready = "Ready"
    Running = "Running"
    Error = "Error"
    Exit = "Exit"

async def main_process_signaling(control_queue, logger=logging):
    """
    signaling repsonse in controller process
    """
    # controller signal handle
    while True:
        await asyncio.sleep(0)
        try:
            signal_message = control_queue.get_nowait()
            # logger.debug(f"Received signal: {signal_message}")
            # only handle the signal with their handlerid
            signal_handlerid, signal_command, *signal_args = parse_signal(signal_message)
            if(signal_handlerid != 0):
                # put it back until the correct receiver handle it
                control_queue.put(signal_message)
                continue
            # 处理信号
            # logger.info(f"[CTRL] Received signal: {signal_message}")
            args_dict = convert_args_to_dict(signal_command)
            if(SignalCommand[signal_command] == SignalCommand.PING):
                if(HandlerStatus[args_dict["status"]] == HandlerStatus.Entry):
                    # send a signal to subprocess to load data
                    signal_message = generate_signal(args_dict["source"], SignalCommand.LOADDATA)
                    control_queue.put(signal_message)
                    continue
                elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Load):
                    # send a signal to subprocess to ready(ready to run)
                    signal_message = generate_signal(args_dict["source"], SignalCommand.READY)
                    control_queue.put(signal_message)
                    continue
                elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Ready):
                    # send a signal to subprocess to run
                    # for different subprocess, we can pass constrain as arguments
                    signal_message = generate_signal(args_dict["source"], SignalCommand.RUN)
                    control_queue.put(signal_message)
                    continue

        except queue.Empty:
            continue