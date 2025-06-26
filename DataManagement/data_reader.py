import pandas as pd
import re
from logger import get_logger
from localvars import RAW_DATA_DIR, POSTPROCESSED_DATA_DIR

logger = get_logger(__name__)

def read_raw_file(filepath):
    comments = []
    metadata = {'channels': [], 'instruments': [], 'units': [], 'start_time': None}
    data_start = 0
    channel_names = None
    with open(filepath, 'r') as f:
        for i, line in enumerate(f):
            if not line.startswith('#'):
                data_start = i
                break
            comments.append(line.strip())
            if line.startswith("#C"):
                # Channel names
                chs = re.findall(r"'([^']+)'", line)
                metadata['channels'].extend(chs)
                channel_names = chs
            elif line.startswith("#I"):
                # Instruments
                insts = re.findall(r"'([^']+)'", line)
                metadata['instruments'].extend(insts)
            elif line.startswith("#P"):
                # Units
                units = re.findall(r"'([^']+)'", line)
                metadata['units'].extend(units)
            elif line.startswith("#T"):
                # Start time
                metadata['start_time'] = line[2:].strip()
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
            df = pd.read_csv(filepath, comment='#', skiprows=data_start, delim_whitespace=True, names=use_names)
        else:
            df = pd.read_csv(filepath, comment='#', skiprows=data_start, delim_whitespace=True)
    else:
        df = pd.read_csv(filepath, comment='#', skiprows=data_start, delim_whitespace=True)
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
            if line.startswith('#T') or line.startswith('#'):
                # Header columns (e.g. #T B R U V)
                header_cols = line[1:].strip().split()
    df = pd.read_csv(filepath, comment='#', skiprows=data_start, delim_whitespace=True, names=header_cols if header_cols else None)
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
            print(f"Reading raw file: {filepath}")
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