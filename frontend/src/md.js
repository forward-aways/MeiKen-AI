import MarkdownIt from 'markdown-it'
import katex from 'katex'
import 'katex/dist/katex.min.css'

// Markdown rendered via markdown-it (robust GFM tables / nesting), with math
// ($...$ / $$...$$ / \(...\) / \[...\]) rendered by KaTeX.
//
// Math and code are extracted into placeholders BEFORE markdown parsing so the
// parser never sees $ or backtick content it could mangle; placeholders are
// swapped for the final HTML afterwards.

const mdit = new MarkdownIt({ html: false, linkify: true })

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

// Fenced code block with language tag + copy button (same DOM as before).
function fenceHTML(lang, code) {
  const langTag = lang ? '<span class="lang-tag">' + esc(lang) + '</span>' : ''
  const codeEsc = esc(code)
  return '<div class="code-block">' + langTag +
    '<button class="copy-btn" onclick="navigator.clipboard.writeText(this.dataset.code);this.textContent=\'Copied!\';this.classList.add(\'copied\');setTimeout(()=>{this.textContent=\'Copy\';this.classList.remove(\'copied\')},2000)" data-code="' + codeEsc + '">Copy</button>' +
    '<pre><code>' + codeEsc + '</code></pre></div>'
}
mdit.renderer.rules.fence = (tokens, idx) => {
  const t = tokens[idx]
  const info = (t.info || '').trim().split(/\s+/)[0]
  return fenceHTML(info || '', t.content.replace(/\n$/, ''))
}

function renderMath(tex, display) {
  try {
    return katex.renderToString(tex, { displayMode: display, throwOnError: false, strict: false })
  } catch (e) {
    const body = esc(tex || e.message)
    return display ? '<div class="math-fallback">' + body + '</div>' : '<span class="math-fallback">' + body + '</span>'
  }
}

// "$" math only when it looks like real math (has letters/symbols) — avoids
// treating currency-ish "$5 and $3" as LaTeX.
const MATHY = /[A-Za-z\\^_{}=+<>\-*/.,()[\]|]/ 

export function md(s) {
  if (!s) return ''
  s = String(s).replace(/\r\n/g, '\n')

  const blocks = []
  s = s.replace(/```(\w*)\n?([\s\S]*?)```/g, (_m, lang, code) => {
    blocks.push(fenceHTML(lang || '', code))
    return '\uE000C' + (blocks.length - 1) + '\uE000'
  })
  s = s.replace(/`([^`]+)`/g, (_m, c) => {
    blocks.push('<code>' + esc(c) + '</code>')
    return '\uE000C' + (blocks.length - 1) + '\uE000'
  })

  const math = []
  s = s.replace(/\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]/g, (_m, a, b) => {
    math.push(renderMath((a != null ? a : b).trim(), true))
    return '\uE000M' + (math.length - 1) + '\uE000'
  })
  s = s.replace(/\$([^$\n]+?)\$|\\\(([\s\S]+?)\\\)/g, (_m, a, b) => {
    const tex = (a != null ? a : b).trim()
    if (b == null && !(tex.length > 1 && MATHY.test(tex))) return _m
    math.push(renderMath(tex, false))
    return '\uE000M' + (math.length - 1) + '\uE000'
  })

  let html = mdit.render(s)
  // Unwrap <p> that only wraps a block placeholder (code block / display math),
  // otherwise a <div>/<span class="katex-display"> would sit inside <p>.
  html = html.replace(/<p>(\uE000M\d+\uE000)<\/p>/g, '$1')
  html = html.replace(/<p>(\uE000C\d+\uE000)<\/p>/g, '$1')
  html = html.replace(/\uE000M(\d+)\uE000/g, (_m, i) => math[+i])
  html = html.replace(/\uE000C(\d+)\uE000/g, (_m, i) => blocks[+i])
  return html
}

export function stripMd(s) {
  return s
    .replace(/\$\$[\s\S]*?\$\$/g, '').replace(/\$([^$\n]+?)\$/g, '$1')
    .replace(/\\\[[\s\S]*?\\\]/g, '').replace(/\\\(([^()\n]*)\\\)/g, '$1')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*(.+?)\*\*/g, '$1').replace(/\*(.+?)\*/g, '$1')
    .replace(/^#{1,4} (.+)$/gm, '$1').replace(/^- (.+)$/gm, '$1')
    .replace(/^\d+\. (.+)$/gm, '$1').replace(/^\|.+\|$/gm, '')
    .replace(/^> (.+)$/gm, '$1').replace(/^[-*_]{3,}$/gm, '')
    .replace(/\n{2,}/g, '\n').trim()
}
