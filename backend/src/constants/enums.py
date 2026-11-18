from enum import Enum
class Role(str, Enum):
    admin = 'admin'
    analyst = 'analyst'
    viewer = 'viewer'
class JobStatus(str, Enum):
    queued = 'queued'
    running = 'running'
    completed = 'completed'
    failed = 'failed'
class UndercountStatus(str, Enum):
    pending = 'pending'
    computed = 'computed'
    failed = 'failed'
class Direction(str, Enum):
    positive = 'positive'
    negative = 'negative'
    unclear = 'unclear'
