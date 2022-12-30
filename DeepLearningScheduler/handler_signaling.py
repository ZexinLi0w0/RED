import asyncio
import queue
import logging, time

# self-defined modules
from control_signal import convert_args_to_dict, generate_signal, parse_signal, SignalCommand
from AbstractHandler import HandlerStatus

async def handle_signaling(control_queue, base_time, config=(), logger=logging, instance=None):
    """
    singaling response in child process
    handler the signals from controller to move itself to different status
    """
    handler_id, handler_name, handler_description, runargs = config
    if(instance is None):
        logger.critical(f"Can not create a signaling handler without task instance in task [{handler_id}]{handler_name}")
        return
    STATUS = HandlerStatus.Entry
    # logger.debug(f'handler signaling processing: {handler_id}, {handler_name}, {handler_description}, {handler_priority}, {handler_dependencies}, {STATUS}')
    while True:
        # 使用asyncio.sleep()挂起协程，让它不阻塞
        # await asyncio.sleep(0)
        # 使用queue.get_nowait()检查queue是否有信号，如果有就立即返回，如果没有就抛出queue.Empty异常
        try:
            signal_message = control_queue.get_nowait()
            # logging.debug(f"Received signal: {signal_message}")
            # only handle the signal with their handlerid
            signal_handlerid, signal_command, *signal_args = parse_signal(signal_message)
            if(signal_handlerid != handler_id):
                # put it back until the correct receiver handle it
                control_queue.put(signal_message)
                continue
            # logger.info(f"[{handler_id}][{handler_name}] Received signal: [{signal_command}]")
            # depends on different signal to execute handlers
            args_dict = convert_args_to_dict(signal_args)
            if(SignalCommand[signal_command] == SignalCommand.PING):
                # return a time
                reply_time = f"--time {time.time() - base_time}"
                # use this handler_id as unique identity
                reply_source = f"--source {handler_id}"
                # for enum value, must send it's value so that the receiver can match it.
                reply_status = f"--status {STATUS.value}"
                # only in status entry, reply heart ping
                if(STATUS == HandlerStatus.Entry):
                    signal_message = generate_signal(0, SignalCommand.PING, reply_time, reply_source, reply_status)
                    control_queue.put(signal_message)
                continue
            elif(SignalCommand[signal_command] == SignalCommand.LOADDATA):
                # skip repeat signal while already in execution
                if(STATUS == HandlerStatus.Load):
                    continue
                loop = asyncio.get_event_loop()
                start_time = time.time() - base_time
                # load data until finished
                await loop.create_task(instance.load_data())
                STATUS = HandlerStatus.Load
                reply_start_time = f"--start_time {start_time}"
                reply_end_time = f"--end_time {time.time() - base_time}"
                reply_source = f"--source {handler_id}" # use this handler_id as unique identity
                reply_status = f"--status {STATUS.value}" # for enum value, must send it's value so that the receiver can match it.
                signal_message = generate_signal(0, SignalCommand.PING, reply_source, reply_status, reply_start_time, reply_end_time)
                control_queue.put(signal_message)
                continue
            elif(SignalCommand[signal_command] == SignalCommand.READY):
                # skip repeat signal while already in execution
                if(STATUS == HandlerStatus.Ready):
                    continue
                start_time = time.time() - base_time
                # set to ready
                instance.ready()
                STATUS = HandlerStatus.Ready
                reply_start_time = f"--start_time {start_time}"
                reply_end_time = f"--end_time {time.time() - base_time}"
                reply_source = f"--source {handler_id}" # use this handler_id as unique identity
                reply_status = f"--status {STATUS.value}" # for enum value, must send it's value so that the receiver can match it.
                signal_message = generate_signal(0, SignalCommand.PING, reply_source, reply_status, reply_start_time, reply_end_time)
                control_queue.put(signal_message)
                continue
            elif(SignalCommand[signal_command] == SignalCommand.RUN):
                # skip repeat signal while already in execution
                if(STATUS == HandlerStatus.Running):
                    continue
                relative_time = args_dict['relative_time']
                taskid = args_dict['taskid']
                start_time = time.time() - relative_time
                # if this task is out of deadline, return failure
                if(args_dict['deadline'] <= time.time() - relative_time):
                    reply_task_id = f"--taskid {taskid}"
                    reply_start_time = f"--start_time {start_time}"
                    reply_end_time = f"--end_time {start_time}"
                    reply_source = f"--source {handler_id}" # use this handler_id as unique identity
                    reply_status = f"--status {STATUS.value}" # for enum value, must send it's value so that the receiver can match it.
                    reply_output = f"--output failure" # only return sucess, write output to log
                    logger.info(f"Task[{taskid}] in [{handler_id}]{handler_name} missing deadline, missing time: {start_time}")
                    signal_message = generate_signal(0, SignalCommand.DELIVERY, reply_source, reply_task_id, reply_status, reply_output, reply_start_time, reply_end_time)
                    control_queue.put(signal_message)
                    continue

                loop = asyncio.get_event_loop()
                STATUS = HandlerStatus.Running
                # load data until finished
                output = await loop.create_task(instance.run())
                STATUS = HandlerStatus.Ready
                end_time = time.time() - relative_time
                reply_task_id = f"--taskid {taskid}"
                reply_start_time = f"--start_time {start_time}"
                reply_end_time = f"--end_time {end_time}"
                reply_source = f"--source {handler_id}" # use this handler_id as unique identity
                reply_status = f"--status {STATUS.value}" # for enum value, must send it's value so that the receiver can match it.
                if(end_time > args_dict['deadline']):
                    reply_output = f"--output failure"
                    logger.info(f"Task[{taskid}] in [{handler_id}]{handler_name} missing deadline, missing time: {end_time}, deadline: {args_dict['deadline']}")
                else:
                    reply_output = f"--output success"
                    logger.info(f"Task[{taskid}] in [{handler_id}]{handler_name} finished, time: {end_time}, deadline: {args_dict['deadline']}")
                
                signal_message = generate_signal(0, SignalCommand.DELIVERY, reply_source, reply_task_id, reply_status, reply_output, reply_start_time, reply_end_time)
                control_queue.put(signal_message)
                continue
        except queue.Empty:
            continue