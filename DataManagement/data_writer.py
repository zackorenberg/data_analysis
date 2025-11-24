import numpy as np
from logger import get_logger

logger = get_logger(__name__)

def save_data_file(df, filepath, comments=None, metadata=None):
    """
    Save a DataFrame in the same format as read by data_reader.py:
    - Two-space separated
    - Header line for columns
    - Optional comments/metadata at the top
    """
    logger.debug(f"Saving data file: {filepath}")
    lines = []
    if comments:
        if type(comments) == str:
            comments = [c.strip() for c in comments.split("\n")]
        for c in comments:
            lines.append(f"# {c}" if not c.startswith('#') else c)
    if metadata and 'channels' in metadata:
        lines.append("#C " + ' '.join(f"'{ch}'" for ch in metadata['channels']))
    if metadata and 'instruments' in metadata:
        lines.append("#I " + ' '.join(f"'{inst}'" for inst in metadata['instruments']))
    if metadata and 'units' in metadata:
        lines.append("#P " + ' '.join(f"'{u}'" for u in metadata['units']))
    if metadata and 'start_time' in metadata:
        lines.append(f"#T {metadata['start_time']}")
    # Header for columns
    lines.append('#' + '  '.join(f"'{str(col)}'" for col in df.columns))
    # Data
    data_str = '\n'.join('  '.join(map(str, row)) for row in df.values)
    lines.append(data_str)
    try:
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        logger.info(f"Successfully saved data file: {filepath}")
    except Exception as e:
        logger.error(f"Error saving data file {filepath}: {e}")
        raise 