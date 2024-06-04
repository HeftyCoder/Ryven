
if __name__ != '__main__':
    exit()

from cognixnodes.core import StreamSignal, LabeledSignal, Signal
from beartype.door import is_subhint

print(is_subhint(StreamSignal | LabeledSignal, LabeledSignal))