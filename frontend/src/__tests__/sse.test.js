/**
 * SSE 分发契约测试（对应 ADR-20260921 的 T1–T7）。
 *
 * 这些用例在修复前应当失败：
 * - T1/T2/T3：run_end 因载荷含 tokens 而被 `if (ev.tokens)` 吞掉；
 * - T5：tool_result 未按 id 配对；
 * - T7：thinking_done 无生产者时思考态永不结束。
 */
import { describe, it, expect, vi } from 'vitest'
import { applyEvent } from '../sse.js'

function newAst(extra = {}) {
  return { role: 'assistant', content: '', streaming: true, phase: '', ...extra }
}

function apply(ast, ev) {
  const hooks = { setContextTokens: vi.fn(), onUnknown: vi.fn() }
  const changed = applyEvent(ast, ev, hooks)
  return { ast, changed, hooks }
}

describe('applyEvent / run_end（RC2）', () => {
  it('T1 accepts tokens and writes back final_text', () => {
    const { ast, changed, hooks } = apply(newAst(), {
      status: 'run_end', interrupted: false, run_id: 'r1', tokens: 120, final_text: 'A',
    })
    expect(changed).toBe(true)
    expect(ast.content).toBe('A')
    expect(ast.phase).toBe('')
    expect(ast.tokens).toBe(120)
    // 上下文用量为 set 语义（最近一次调用），不是累加
    expect(hooks.setContextTokens).toHaveBeenCalledWith(120)
  })

  it('T2 still applies run_end when tokens is 0 (boundary)', () => {
    const { ast } = apply(newAst(), {
      status: 'run_end', interrupted: false, run_id: 'r2', tokens: 0, final_text: 'B',
    })
    expect(ast.content).toBe('B')
    expect(ast.phase).toBe('')
  })

  it('T3 ignores run_end without final_text instead of crashing', () => {
    const { ast } = apply(newAst({ content: 'kept' }), {
      status: 'run_end', interrupted: false, run_id: 'r3', tokens: 120,
    })
    expect(ast.content).toBe('kept')
    expect(ast.phase).toBe('')
  })

  it('regression: a run_end carrying tokens is not mistaken for a token event', () => {
    // 修复前：`if (ev.tokens)` 分支先命中，run_end 的 final_text 永远不生效。
    const { ast } = apply(newAst(), {
      status: 'run_end', interrupted: false, run_id: 'r4', tokens: 999, final_text: 'final answer',
    })
    expect(ast.content).toBe('final answer')
    expect(ast.content).not.toContain('999')
  })
})

describe('applyEvent / thinking（RC3）', () => {
  it('T1 ends the thinking phase when thinking_done arrives', () => {
    const { ast } = apply(newAst(), { type: 'reasoning', reasoning: 'hmm' })
    expect(ast.phase).toBe('thinking')
    expect(ast.thinkingTime).toBeUndefined()

    apply(ast, { type: 'thinking_done', seconds: 3.2 })
    expect(ast.thinkingTime).toBe(3.2)
    expect(ast.phase).toBe('')
  })

  it('T7 keeps thinkingTime undefined when no thinking_done is produced', () => {
    const { ast } = apply(newAst(), { type: 'token', token: 'hi' })
    expect(ast.thinkingTime).toBeUndefined()
    expect(ast.phase).toBe('generating')
  })
})

describe('applyEvent / tool pairing（RC1）', () => {
  it('T5 pairs tool_result with the matching id, not merely the same tool name', () => {
    const ast = newAst()
    apply(ast, { type: 'tool_call', id: 'c1', tool: 'web_search', args: { query: 'q1' } })
    apply(ast, { type: 'tool_call', id: 'c2', tool: 'web_search', args: { query: 'q2' } })

    apply(ast, { type: 'tool_result', id: 'c2', tool: 'web_search', result: 'r2', sources: [{ url: 'https://b' }] })
    const first = ast.toolCalls.find((c) => c.id === 'c1')
    const second = ast.toolCalls.find((c) => c.id === 'c2')
    expect(second.status).toBe('done')
    expect(second.sources).toHaveLength(1)
    expect(first.status).toBe('running')
  })

  it('T5b leaves phase set while another call is still running', () => {
    const ast = newAst()
    apply(ast, { type: 'tool_call', id: 'c1', tool: 'web_search', args: {} })
    apply(ast, { type: 'tool_call', id: 'c2', tool: 'web_search', args: {} })
    apply(ast, { type: 'tool_result', id: 'c1', tool: 'web_search', result: 'r1' })
    expect(ast.phase).toBe('tool:web_search')
    apply(ast, { type: 'tool_result', id: 'c2', tool: 'web_search', result: 'r2' })
    expect(ast.phase).toBe('')
  })
})

describe('applyEvent / protocol invariants（RC3 防复发）', () => {
  it('reports unknown events instead of silently ignoring them', () => {
    const { hooks, changed } = apply(newAst(), { status: 'searched', results: [] })
    expect(changed).toBe(false)
    expect(hooks.onUnknown).toHaveBeenCalledTimes(1)
  })

  it('does not treat the retired searching/searched/rag_loaded events as state changes', () => {
    for (const ev of [
      { status: 'searching', query: 'q' },
      { status: 'searched', results: [{ title: 't' }] },
      { status: 'rag_loaded', sources: ['f.txt'] },
    ]) {
      const { ast, changed } = apply(newAst(), ev)
      expect(changed).toBe(false)
      expect(ast.searchResults).toBeUndefined()
      expect(ast.ragSources).toBeUndefined()
    }
  })

  it('T4 surfaces errors and clears the phase', () => {
    const { ast } = apply(newAst({ phase: 'generating' }), { error: 'boom' })
    expect(ast.error).toBe(true)
    expect(ast.phase).toBe('')
    expect(ast.content).toContain('boom')
  })

  it('applies done without double counting context tokens', () => {
    const { ast, hooks } = apply(newAst(), { done: true, id: 7, tokens: 42 })
    expect(ast.id).toBe(7)
    expect(ast.tokens).toBe(42)
    expect(hooks.setContextTokens).not.toHaveBeenCalled()
  })

  it('T6 passes the raw value through (store enforces the "never overwrite with 0" guard)', () => {
    const { hooks } = apply(newAst(), {
      status: 'run_end', interrupted: false, run_id: 'r6', tokens: 0, final_text: 'x',
    })
    // 0 必须原样上报：由 store.setContextTokens 决定忽略，而不是在这里猜测
    expect(hooks.setContextTokens).toHaveBeenCalledWith(0)
  })
})

describe('applyEvent / sequence（RC1 时间线顺序）', () => {
  it('moves pre-tool talk into interim, keeping the answer bubble clean', () => {
    const ast = newAst()
    apply(ast, { type: 'token', token: 'let me search for you' })
    apply(ast, { type: 'tool_call', id: 'c1', tool: 'web_search', args: {} })
    expect(ast.content).toBe('')
    expect(ast.interim).toEqual(['let me search for you'])
  })

  it('assigns increasing seq so the timeline keeps event order', () => {
    const ast = newAst()
    apply(ast, { type: 'tool_call', id: 'c1', tool: 'web_search', args: {} })
    apply(ast, { status: 'sub_started', subagent: 'researcher', task: 't' })
    apply(ast, { type: 'tool_call', id: 'c2', tool: 'knowledge_search', args: {} })
    expect(ast.toolCalls[0].seq).toBe(1)
    expect(ast.subagents[0].seq).toBe(2)
    expect(ast.toolCalls[1].seq).toBe(3)
  })
})
