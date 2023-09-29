from typing import Dict, Tuple
# use the 'OrderedDict' type to ensure that data emission events within a stream are sorted by key, where key = time
from collections import OrderedDict

from globals import MICROSECONDS_PER_SECOND

# updated this function to process emission- and reception data (event_type is either "emissions" or "rcv").


def compute_inter_event_delays(stream_val: Dict, event_type: str, participant: str, last_creation_event: int) -> None:

    sorted_events = OrderedDict(
        sorted(stream_val[f'{event_type}_{participant}'].items()))

    stream_val[f'{event_type}_{participant}'] = dict()

    # bootstrap last event
    last_event = last_creation_event

    # now let's also compute the delays for the emission events on this stream
    for event_key, event_val in sorted_events.items():

        # emission_key = emission_time; now compute the delay in between this emission and the previous one respectively the creation of the stream if this is the first emission event
        delay = event_key - last_event

        # sanity check
        if delay < 0:
            print(
                f"Something went wrong, negative delay!! ({event_type} level)")

        # now we're making a keeeeewwwwl dict key which is a tuple of the form (time, delay) where time is the respective timestamp in microseconds adjusted for start time and the delay is the inter-event delay so we know how long to wait in between emissions.
        # this ensures uniqueness of dict keys, if we'd use the delays as dict keys we'd likely overwrite data from time to time due to collisions
        key: Tuple[int, int] = (event_key, delay)

        stream_val[f'{event_type}_{participant}'].update({
            key: event_val})

        last_event = event_key


def parse_tgen_traffic(dir: str, num: int = None) -> Dict:

    client_file = open(f"../../tgen-traces/{dir}/client{num}.tgen.stdout")
    client_lines = client_file.readlines()

    server_file = open(f"../../tgen-traces/{dir}/server{num}.tgen.stdout")
    server_lines = server_file.readlines()

    data_dict = {'streams': dict()}

    # start with the client stdout file; it contains the stream creation information as well as information on data emission in the direction of server as well as data reception from the server

    # grab the start time (in seconds)
    start_time = int(client_lines[0].split(" ")[2].split(".")[0])

    # aggregate the total number of bytes emitted by client/server, information we'll use for msg emitters to know they're done (not currently, but maybe in the future)
    total_bytes_emitted_client: int = 0
    total_bytes_emitted_server: int = 0

    for client_line in client_lines:

        client_line_chunks = client_line.split(" ")

        if client_line_chunks[5] == "[_tgengenerator_createStream]":
            # 1st kind of line we are interested in: stream creation, i.e. lines looking like this:
            """
            2000-01-01 00:05:53 946685153.000000 [message] [tgen-generator.c:448] [_tgengenerator_createStream] [T] STREAM with mmodel seed 2743373598 was successfully generated by flow with mmodel seed 3591772533
            """

            # parse the seeds of the stream's mmodel
            stream_mm_seed = int(client_line_chunks[11])

            # check for collisions (highly unlikely that there will be any)
            if stream_mm_seed in data_dict['streams']:
                print("Stream mmodel seed collision!")

            # parse creation time, adjusted for the start_time we determined above
            # split time_unix_seconds.time_microseconds
            time = client_line_chunks[2].split(".")

            # grab unix seconds
            time_unix_seconds = int(time[0])

            # adjust for start time
            time_adjusted_seconds = time_unix_seconds - start_time

            # grab microseconds
            time_microseconds = int(time[1])

            # compute total microseconds
            time_total = time_adjusted_seconds * MICROSECONDS_PER_SECOND + time_microseconds

            data_dict['streams'].update(
                {stream_mm_seed: {'time_created': time_total, 'emissions_client': dict(), 'rcv_client': dict(), 'emissions_server': dict(), 'rcv_server': dict()}})

        elif client_line_chunks[5] == "[_tgenstream_flushOut]":

            # 2nd kind of line we are interested in: data emission, i.e. lines looking like this:
            """
            2000-01-01 00:05:53 946685153.574350 [message] [tgen-stream.c:1026] [_tgenstream_flushOut] [T] Stream with mmodel seed 2743373598 wrote 261 bytes to network
            """

            # parse the seed of the parent stream's mmodel
            stream_mm_seed = int(client_line_chunks[11])

            # parse creation time, adjusted for the start_time we determined above
            # split time_unix_seconds.time_microseconds
            time = client_line_chunks[2].split(".")

            # grab unix seconds
            time_unix_seconds = int(time[0])

            # adjust for start time
            time_adjusted_seconds = time_unix_seconds - start_time

            # grab microseconds
            time_microseconds = int(time[1])

            # compute total microseconds
            time_total = time_adjusted_seconds * MICROSECONDS_PER_SECOND + time_microseconds

            # parse the number of bytes emitted
            num_bytes = int(client_line_chunks[13])

            # add to the total bytes emitted for client
            total_bytes_emitted_client += num_bytes

            if time_total in data_dict['streams'][stream_mm_seed]['emissions_client']:

                # print("Time collision in data emission client stdout file, appending!")

                data_dict['streams'][stream_mm_seed]['emissions_client'][time_total] += num_bytes

            else:

                data_dict['streams'][stream_mm_seed]['emissions_client'].update(
                    {time_total: num_bytes})

        elif client_line_chunks[5] == "[_tgenstream_onReadable]":

            # this type of line looks like this:
            # 2000-01-01 00:05:05 946685105.198910 [message] [tgen-stream.c:973] [_tgenstream_onReadable] [T] active stream [id=3,vertexid=flow,name=markovclient6exit,peername=server6exit,sendsize=0,recvsize=0,sendstate=SEND_PAYLOAD,recvstate=RECV_PAYLOAD,error=NONE] with markov model seed 174178766 read 7170 more bytes

            # parse the seed of the parent stream's mmodel
            stream_mm_seed = int(client_line_chunks[14])

            # parse creation time, adjusted for the start_time we determined above
            # split time_unix_seconds.time_microseconds
            time = client_line_chunks[2].split(".")

            # grab unix seconds
            time_unix_seconds = int(time[0])

            # adjust for start time
            time_adjusted_seconds = time_unix_seconds - start_time

            # grab microseconds
            time_microseconds = int(time[1])

            # compute total microseconds
            time_total = time_adjusted_seconds * MICROSECONDS_PER_SECOND + time_microseconds

            # parse the number of bytes received
            num_bytes = int(client_line_chunks[16])

            if time_total in data_dict['streams'][stream_mm_seed]['rcv_client']:

                # print("Time collision in data rcv client stdout file, appending!")

                data_dict['streams'][stream_mm_seed]['rcv_client'][time_total] += num_bytes

            else:

                data_dict['streams'][stream_mm_seed]['rcv_client'].update(
                    {time_total: num_bytes})

        # Account for fails
        # 2000-01-01 00:05:44 946685144.301498 [critical] [tgen-stream.c:1621] [_tgenstream_runTransportEventLoop] transport connection or proxy handshake failed, stream cannot begin
        elif client_line_chunks[3] == "[critical]":

            return None

        else:

            pass

    # now we're adding the data emission for the other direction, which we will parse from the server stdout

    for server_line in server_lines:

        server_line_chunks = server_line.split(" ")

        if server_line_chunks[5] == "[_tgenstream_flushOut]":

            # first kind of line we are interested in: data emission, i.e. lines looking like this:
            """
            2000-01-01 00:05:53 946685153.574350 [message] [tgen-stream.c:1026] [_tgenstream_flushOut] [T] Stream with mmodel seed 2743373598 wrote 261 bytes to network
            """

            # parse the seed of the parent stream's mmodel (luckily, the stream mmodel seeds are the same on the client vs server side)
            stream_mm_seed = int(server_line_chunks[11])

            # parse creation time, adjusted for the start_time we determined above
            # split time_unix_seconds.time_microseconds
            time = server_line_chunks[2].split(".")

            # grab unix seconds
            time_unix_seconds = int(time[0])

            # adjust for start time
            time_adjusted_seconds = time_unix_seconds - start_time

            # grab microseconds
            time_microseconds = int(time[1])

            # compute total microseconds
            time_total = time_adjusted_seconds * MICROSECONDS_PER_SECOND + time_microseconds

            # parse the number of bytes emitted
            num_bytes = int(server_line_chunks[13])

            # add to the total bytes emitted for server
            total_bytes_emitted_server += num_bytes

            if time_total in data_dict['streams'][stream_mm_seed]['emissions_server']:

                # print("Time collision in data emission server stdout file, appending!")

                data_dict['streams'][stream_mm_seed]['emissions_server'][time_total] += num_bytes

            else:

                data_dict['streams'][stream_mm_seed]['emissions_server'].update(
                    {time_total: num_bytes})

        elif server_line_chunks[5] == "[_tgenstream_onReadable]":

            # this type of line looks like this:
            # 2000-01-01 00:05:05 946685105.198910 [message] [tgen-stream.c:973] [_tgenstream_onReadable] [T] active stream [id=3,vertexid=flow,name=markovclient6exit,peername=server6exit,sendsize=0,recvsize=0,sendstate=SEND_PAYLOAD,recvstate=RECV_PAYLOAD,error=NONE] with markov model seed 174178766 read 7170 more bytes

            # parse the seed of the parent stream's mmodel
            stream_mm_seed = int(server_line_chunks[14])

            # parse creation time, adjusted for the start_time we determined above
            # split time_unix_seconds.time_microseconds
            time = server_line_chunks[2].split(".")

            # grab unix seconds
            time_unix_seconds = int(time[0])

            # adjust for start time
            time_adjusted_seconds = time_unix_seconds - start_time

            # grab microseconds
            time_microseconds = int(time[1])

            # compute total microseconds
            time_total = time_adjusted_seconds * MICROSECONDS_PER_SECOND + time_microseconds

            # parse the number of bytes received
            num_bytes = int(server_line_chunks[16])

            if time_total in data_dict['streams'][stream_mm_seed]['rcv_server']:

                # print("Time collision in data rcv server stdout file, appending!")

                data_dict['streams'][stream_mm_seed]['rcv_server'][time_total] += num_bytes

            else:

                data_dict['streams'][stream_mm_seed]['rcv_server'].update(
                    {time_total: num_bytes})

        else:

            pass

    # additionally, we want to ensure that
    # - emission events within a stream are sorted (why would they not be sorted in the first place? - Because we are parsing the server stdout after the client stdout, and a server emission may lie in between two existing client emissions temporally) NOTE this remark doesn't really make sense anymore now that we have decoupled client and server from each other
    # - we have delays in between creation of streams, as well as delays in between emission events on a stream available
    stream_data = data_dict['streams']

    for stream_key, stream_val in stream_data.items():

        # store the stream creation time so we can compute the delay until the first emission on this flow

        # note that since we computed all creation times in relation to the start time of the simulation (by subtracting it), the creation time of the first stream also corresponds to the delay in between starting the simulation and creating this stream.

        # initialize 'last_creation_event' with the parent stream's creation time, since for the first emission created by this stream, we want to know the delay in between the parent stream's creation and the creation of this emission∂
        last_creation_event = stream_val['time_created']

        # compute delays in between emissions and receptions, for client and server separately

        compute_inter_event_delays(
            stream_val=stream_val, event_type="emissions", participant="client", last_creation_event=last_creation_event)

        compute_inter_event_delays(
            stream_val=stream_val, event_type="emissions", participant="server", last_creation_event=last_creation_event)

        compute_inter_event_delays(
            stream_val=stream_val, event_type="rcv", participant="client", last_creation_event=last_creation_event)

        compute_inter_event_delays(
            stream_val=stream_val, event_type="rcv", participant="server", last_creation_event=last_creation_event)

    # lastly, we need the delays in between stream creation (just a few values)
    # note that since we computed all creation times in relation to the start time of the simulation (by subtracting it), the creation time of the first stream also corresponds to the delay in between starting the simulation and creating this stream.
    stream_creation_time = 0

    for stream_key, stream_val in stream_data.items():

        delay = stream_val['time_created'] - stream_creation_time

        # sanity check
        if delay < 0:
            print("Something went wrong, negative delay!! (Stream level)")

        stream_val.update(
            {'delay': delay})

        stream_creation_time = stream_val['time_created']

    # add the total number of bytes emitted for this entire flow to dict (client as well as server separately)
    # NOTE not currently using this information
    data_dict["total_bytes_emitted_client"] = total_bytes_emitted_client
    data_dict["total_bytes_emitted_server"] = total_bytes_emitted_server

    return data_dict