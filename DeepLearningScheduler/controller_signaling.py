import asyncio, math, time
import queue
import logging

# self-defined modules
from control_signal import convert_args_to_dict, generate_signal, parse_signal, SignalCommand
from AbstractHandler import HandlerStatus


async def send_heart_ping(control_queue, handlers, relative_start_time, logger=logging):
    """
    A heart beat ping task, excuted by controller process.
    Send a ping with relative time to every handlers
    """
    basetime = relative_start_time
    while True:
        try:
            for handler in handlers:    
                # Generate the PING signal
                signal_heart = generate_signal(handler["id"], SignalCommand.PING, f"--time {math.floor(time.time()-basetime)}")
                # Send the PING signal to the control queue
                control_queue.put(signal_heart)
                # logger.debug(f'Send heart signal to subprocess {signal_heart}')

            # 6ms overhead

            # Wait for 1 second
            await asyncio.sleep(1/60)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in heart ping: {e}")
            continue

async def sendsignal_later(control_queue, signal_message, delay_time):
    """
    Send a signal to the control queue after delay_time
    """
    await asyncio.sleep(delay_time)
    control_queue.put(signal_message)

async def controller_signaling(control_queue, handlers, tasks_list, id2process, id2config, logger=logging, base_time = 0):
    """
    signaling repsonse in controller process
    """
    TaskQueue = []
    logger.debug(f"recevied id2config: {id2config}")
    # controller signal handle
    while True:
        # await asyncio.sleep(0)
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
            args_dict = convert_args_to_dict(signal_args)
            # logger.debug(f"[CTRL] Received signal: {signal_message},\n Parse args_dict: {args_dict}")
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
                elif(HandlerStatus[args_dict["status"]] == HandlerStatus.Running):
                    # send a signal to subprocess to ready
                    config = id2config[int(args_dict["source"])]
                    handler_id, handler_name, handler_description, runargs = config
                    if("release-time" in runargs):
                        # wait until delay to release time
                        if(float(runargs["release-time"]) > time.time() - base_time):
                            continue
                    logger.info(f'[CTRL] Received task[{args_dict["source"]}] running output: {signal_message}')
                    signal_message = generate_signal(args_dict["source"], SignalCommand.READY)
                    control_queue.put(signal_message)
                    continue

        except queue.Empty:
            continue