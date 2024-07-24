from unittest.mock import Mock


class MockTask:
    def __init__(self):
        self.cancel = Mock()
        self.done = Mock(return_value=False)

    def __await__(self):
        yield
