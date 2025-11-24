import os
from abc import ABC, abstractmethod
from typing import List, Tuple, Any
from DataManagement.data_writer import save_data_file

class BaseProcessingModule(ABC):
    """
    Abstract base class for all processing modules.
    """
    # If we define it here, they will all be blank. They must form this typing however
    # PARAMETERS: List[Tuple[str, str, type, bool]] = []  # (name, label, type, required)

    def __init__(self, input_file: str, output_dir: str, params: dict):
        self.input_file = input_file
        self.output_dir = output_dir
        self.params = params
        self.data = None
        self.result = None

    # @abstractmethod, we should probably not define this here, otherwise we are forced to overload it
    def load(self):
        """Load input data from file."""
        pass

    @abstractmethod
    def process(self):
        """Perform processing/calculation."""
        raise NotImplementedError("Subclasses must implement this method.")  # this code will never execute

    @abstractmethod
    def save(self):
        """Save processed data to output file."""
        raise NotImplementedError("Subclasses must implement this method.")  # this code will never execute

    # Helper functions

    def get_cooldown_name(self):
        """Extract cooldown name as the first folder after 'raw', 'preprocessed', or 'postprocessed' in the input_file path."""
        parts = os.path.normpath(self.input_file).split(os.sep)
        for key in ('raw', 'preprocessed', 'postprocessed'):
            try:
                idx = parts.index(key)
                if idx+1 < len(parts):
                    return parts[idx+1]
            except ValueError:
                continue
        return ''

    def get_output_path(self, filename: str) -> str:
        """Get full output path in the output_dir/cooldown folder."""
        cooldown = self.get_cooldown_name()
        outdir = os.path.join(self.output_dir, cooldown)
        os.makedirs(outdir, exist_ok=True)
        return os.path.join(outdir, filename)

    def save_data(self, df, filename, comments=None, metadata=None, subfolder=None):
        """Save data using the standard format (calls data_writer.save_data_file)."""
        # Use cooldown from params if present, else use get_cooldown_name()
        cooldown = self.params.get('cooldown', self.get_cooldown_name())
        outdir = os.path.join(self.output_dir, cooldown, subfolder) if subfolder else os.path.join(self.output_dir, cooldown)
        os.makedirs(outdir, exist_ok=True)
        outpath = os.path.join(outdir, filename)
        save_data_file(df, outpath, comments=comments, metadata=metadata)
