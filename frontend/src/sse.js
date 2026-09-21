/**
 * SSE 事件分发（唯一真源）。
 *
 * 契约（不变量，见 ADR-20260921）：
 * 1. 每个事件恰好有一个判别符：`status` 或 `type`；终态为 `done` / `error`。
 * 2. 禁止按字段判断事件类型（例如 `if (ev.tokens)`）——字段会在多个事件间
 *    复用，一旦某个更具体的事件先带上该字段，其专属分支会被静默吞掉。
 * 3. `run_end` 对每个 run 恰好应用一次：写回 `final_text`、清空 `phase`、
 *    累加上下文用量。
 */

/** 工具回合前的过程辞令移出正文，交给时间线的"过程记录"。 */
export function splitInterim(ast) {
  if (ast.content && ast.content.trim()) {
    ast.interim = ast.interim || []
    ast.interim.push(ast.content.trim())
    ast.content = ''
  }
}

function applyStatus(ast, ev, hooks) {
  switch (ev.status) {
    case 'run_end': {
      if (typeof ev.final_text === 'string') ast.content = ev.final_text
      ast.interrupted = !!ev.interrupted
      ast.phase = ''
      ast.tokens = ev.tokens || 0
      // 上下文用量取"最近一次调用"的值（set 语义），不是历史累加
      hooks.setContextTokens?.(ev.tokens || 0)
      return true
    }
    case 'sub_started': {
      splitInterim(ast)
      ast.subagents = ast.subagents || []
      ast.seq = (ast.seq || 0) + 1
      ast.subagents.push({ name: ev.subagent, task: ev.task, status: 'running', seq: ast.seq })
      ast.phase = 'sub:' + ev.subagent
      return true
    }
    case 'sub_done': {
      const s = (ast.subagents || []).find((x) => x.name === ev.subagent)
      if (s) s.status = 'done'
      ast.phase = ''
      return true
    }
    default:
      hooks.onUnknown?.(ev)
      return false
  }
}

function applyType(ast, ev, hooks) {
  switch (ev.type) {
    case 'token': {
      ast.content += ev.token
      ast.phase = 'generating'
      return true
    }
    case 'reasoning': {
      ast.reasoning = (ast.reasoning || '') + ev.reasoning
      ast.phase = 'thinking'
      return true
    }
    case 'thinking_done': {
      ast.thinkingTime = ev.seconds
      if (ast.phase === 'thinking') ast.phase = ''
      return true
    }
    case 'todo': {
      ast.todos = ev.todos
      return true
    }
    case 'tool_call': {
      splitInterim(ast)
      ast.toolCalls = ast.toolCalls || []
      ast.seq = (ast.seq || 0) + 1
      ast.toolCalls.push({
        id: ev.id || '', tool: ev.tool, args: ev.args,
        status: 'running', result: '', sources: [], seq: ast.seq,
      })
      ast.phase = 'tool:' + ev.tool
      return true
    }
    case 'tool_result': {
      const list = ast.toolCalls || []
      // 优先按 tool_call id 配对（同名工具可能被多次调用），退回首个同名运行中调用。
      let tc = ev.id ? list.find((x) => x.id === ev.id) : null
      if (!tc) tc = list.find((x) => x.tool === ev.tool && x.status === 'running')
      if (tc) {
        tc.status = 'done'
        tc.result = ev.result
        if (ev.sources) tc.sources = ev.sources
      }
      if (!list.some((x) => x.status === 'running')) ast.phase = ''
      return true
    }
    case 'approval_request': {
      ast.approvals = ast.approvals || []
      ast.approvals.push({
        action_id: ev.action_id, tool: ev.tool, args: ev.args,
        allowed: ev.allowed, status: 'pending',
      })
      ast.pendingApproval = true
      ast.phase = 'approval'
      return true
    }
    default:
      hooks.onUnknown?.(ev)
      return false
  }
}

function applyError(ast, ev) {
  ast.content = '⚠ ' + ev.error
  ast.error = true
  ast.phase = ''
  return true
}

function applyDone(ast, ev) {
  if (ev.tokens) ast.tokens = ev.tokens
  if (ev.id != null) ast.id = ev.id
  return true
}

/**
 * 应用单个 SSE 事件到流式 assistant 消息。
 * @returns {boolean} 是否产生了状态变更（调用方据此触发滚动/渲染）
 */
export function applyEvent(ast, ev, hooks = {}) {
  if (ev.status) return applyStatus(ast, ev, hooks)
  if (ev.type) return applyType(ast, ev, hooks)
  if (ev.error) return applyError(ast, ev)
  if (ev.done) return applyDone(ast, ev)
  hooks.onUnknown?.(ev)
  return false
}
