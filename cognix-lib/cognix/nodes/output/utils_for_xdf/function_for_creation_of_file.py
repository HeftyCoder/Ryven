from .xdfwriter import XDFWriter
import numpy as np
from pylsl import local_clock

def creation_of_xdf(xdfile:XDFWriter,streamid:int,stream_id_infos:dict,data_content:list|np.ndarray,timestamps:list|np.ndarray,write_header:bool,write_data:bool,write_footer:bool,first_time:float,last_time:float,samples_count:int):
    # print("Creation of XDF FILE for stream {}".format(stream_id_infos['stream_name']))
    # print(stream_id_infos)
    
    if write_header==True:
        # print("Write Header")
        header = (f"<?xml version=\"1.0\"?>"
                "<info>"
                "<name>{}</name>"
                "<type>{}</type>"
                "<channel_count>{}</channel_count>"
                "<nominal_srate>{}</nominal_srate>"
                "<channel_format>{}</channel_format>"
                "<created_at>{}</created_at>"
                "</info>".format(stream_id_infos['stream_name'],stream_id_infos['stream_type'],stream_id_infos['channel_count'],\
                    stream_id_infos['nominal_srate'],stream_id_infos['channel_format'],stream_id_infos['time_created']))
        xdfile.write_stream_header(streamid,header)
        xdfile.write_boundary_chunk()
    
    elif write_footer == True:   
        # print("Write Footer")    
        footer = (
                f"<?xml version=\"1.0\"?>"
                "<info>"
                "<first_timestamp>{}</first_timestamp>"
                "<last_timestamp>{}</last_timestamp>"
                "<sample_count>{}</sample_count>"
                "<clock_offsets>"
                "<offset><time>50979.7660030605</time><value>-3.436503902776167e-06</value></offset>"
                "</clock_offsets></info>"
            )
        xdfile.write_boundary_chunk()
        xdfile.write_stream_offset(streamid,local_clock(),-0.5)
        xdfile.write_stream_footer(streamid,footer)
    
    elif write_data == True:
        if isinstance(data_content,list):
            xdfile.write_data_chunk(streamid,timestamps,data_content,stream_id_infos['channel_count'])
        else: 
            xdfile.write_data_chunk_nested(streamid,timestamps,data_content)