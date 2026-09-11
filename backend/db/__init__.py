"""数据访问层入口：按业务域聚合导出。

其他模块统一使用 ``from backend.db import xxx``，
不要直接导入子模块，以保持引用点集中。
"""
from backend.db._core import DB, _db, _ts

from backend.db.users import *
from backend.db.convs import *
from backend.db.kb import *
from backend.db.agents import *
from backend.db.providers import *
from backend.db.skills import *
from backend.db.images import *
