import pandas as pd
import re
from logger import get_logger
from localvars import RAW_DATA_DIR, POSTPROCESSED_DATA_DIR, DATA_DELIMITER

logger = get_logger(__name__)

def read_raw_file(filepath):
    """
    Note: This function is designed for use with LabGUI data files. Any other data file formats need to be custom coded here
    """
    comments = []
    metadata = {'channels': [], 'instruments': [], 'units': [], 'start_time': None}
    data_start = 0
    channel_names = None
    with open(filepath, 'r') as f:
        for i, line in enumerate(f):
            if not line.startswith('#'):
                data_start = i
                break
            
            if line.startswith("#C'"):
                # Channel names
                chs = re.findall(r"'([^']+)'", line)
                if len(chs):
                    metadata['channels'].extend(chs)
                    channel_names = chs
                    continue
            elif line.startswith("#I'"):
                # Instruments
                insts = re.findall(r"'([^']+)'", line)
                if len(insts):
                    metadata['instruments'].extend(insts)
                    continue
            elif line.startswith("#P'"):
                # Units
                units = re.findall(r"'([^']+)'", line)
                if len(units):
                    metadata['units'].extend(units)
                    continue
            elif line.startswith("#T'"):
                # Start time
                try:
                    start_time = re.findall(r"'([^']+)'", line)
                    if len(start_time) == 1:
                        #metadata['start_time'] = float(line[2:].strip().strip('\''))
                        metadata['start_time'] = float(start_time[0])
                        continue
                except Exception as e:
                    logger.warning(f"Could not parse start time from line: {line}") # Must be a comment then
                    print(e)
            
            
            comments.append(line[1:].strip()) # remove the #
            
    # Read data
    if channel_names:
        # Count columns in first data row
        with open(filepath, 'r') as f:
            for _ in range(data_start):
                next(f)
            first_data_line = next(f)
            ncols = len(first_data_line.split())
        use_names = [str(name) for name in channel_names[:ncols]]
        if use_names:
            df = pd.read_csv(filepath, comment='#', skiprows=data_start, sep=DATA_DELIMITER, names=use_names)
        else:
            df = pd.read_csv(filepath, comment='#', skiprows=data_start, sep=DATA_DELIMITER)
    else:
        df = pd.read_csv(filepath, comment='#', skiprows=data_start, sep=DATA_DELIMITER)
    return df, comments, metadata

def read_processed_file(filepath):
    comments = []
    header_cols = []
    data_start = 0
    with open(filepath, 'r') as f:
        for i, line in enumerate(f):
            if not line.startswith('#'):
                data_start = i
                break
            comments.append(line.strip())
            if line.startswith('#'): # The last line of the comments should conain the header labels
                # Header columns (e.g. # 'T' 'B' 'R' 'U' 'V')
                header_cols = re.findall(r"'([^']+)'", line) # If using quotes, this will work
                if not len(header_cols): # If re could not match any quotes, we try without quotes
                    header_cols = [x.strip('\'"') for x in line[1:].strip().split(DATA_DELIMITER if DATA_DELIMITER != '\s+' else ' ') if x]
                
    df = pd.read_csv(filepath, comment='#', skiprows=data_start, sep=DATA_DELIMITER, names=header_cols if header_cols else None)
    return df, comments, header_cols

def read_data_file(filepath, filetype=None):
    """
    filetype: 'raw', 'processed', or None (auto-detect)
    Returns: (df, comments, metadata/header_cols, filetype)
    """
    logger.debug(f'Reading data file: {filepath}')
    try:
        if filetype is None:
            # Auto-detect: if file has #C, #I, #P, treat as raw
            with open(filepath, 'r') as f:
                head = f.read(4096)
                if any(tag in head for tag in ['#C', '#I', '#P']):
                    filetype = 'raw'
                else:
                    filetype = 'processed'
        if filetype == 'raw':
            logger.debug(f"Reading raw file: {filepath}")
            df, comments, metadata = read_raw_file(filepath)
            logger.info(f'Successfully read raw file: {filepath}')
            return df, comments, metadata, 'raw'
        else:
            df, comments, header_cols = read_processed_file(filepath)
            logger.info(f'Successfully read processed file: {filepath}')
            return df, comments, header_cols, 'processed'
    except Exception as e:
        logger.error(f'Error reading data file {filepath}: {e}')
        raise e