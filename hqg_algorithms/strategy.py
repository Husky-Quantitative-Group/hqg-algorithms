class Strategy:
    def __init__(self, name: str):
        self.name = name

    def run(self, data):
        """Run the strategy logic on input data."""
        raise NotImplementedError("Subclasses must implement this method.")
