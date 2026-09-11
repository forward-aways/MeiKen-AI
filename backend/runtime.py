"""应用运行时状态：跨请求共享的单例。

生命周期由 ``backend.main.lifespan`` 管理：
启动时初始化，关闭时释放。路由与业务模块从这里读取，避免全局变量散落。
"""

saver = None       # langgraph AsyncSqliteSaver：对话检查点
store = None       # langgraph AsyncSqliteStore：技能文件存储
factory = None     # AgentFactory：代理构建与缓存
semaphore = None   # threading.Semaphore：并发运行数限制
