import os
from abc import ABC, abstractmethod
from typing import List, Tuple, Any
from DataManagement.data_writer import save_data_file

class BaseProcessingModule(ABC):
    """
    Abstract base class for all processing modules.
    """
    PARAMETERS: List[Tuple[str, str, type, bool]] = []  # (name, label, type, required)

    def __init__(self, input_file: str, output_dir: str, params: dict):
        self.input_file = input_file
        self.output_dir = output_dir
        self.params = params
        self.data = None
        self.result = None

    @abstractmethod
    def load(self):
        """Load input data from file."""
        pass

    @abstractmethod
    def process(self):
        """Perform processing/calculation."""
        pass

    @abstractmethod
    def save(self):
        """Save processed data to output file."""
        pass

    def get_cooldown_name(self):
        """Extract cooldown name from input_file path."""
        return os.path.basename(os.path.dirname(self.input_file))

    def get_output_path(self, filename: str) -> str:
        """Get full output path in the output_dir/cooldown folder."""
        cooldown = self.get_cooldown_name()
        outdir = os.path.join(self.output_dir, cooldown)
        os.makedirs(outdir, exist_ok=True)
        return os.path.join(outdir, filename)

    def save_data(self, df, filepath, comments=None, metadata=None):
        """Save data using the standard format (calls data_writer.save_data_file)."""
        save_data_file(df, filepath, comments=comments, metadata=metadata)

class BasePreprocessingModule(BaseProcessingModule):
    """
    Base class for preprocessing modules.
    """
    pass

class BasePostprocessingModule(BaseProcessingModule):
    """
    Base class for postprocessing modules.
    """
    pass 