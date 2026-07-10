function rinline(s) {
  return s.replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
}

export function md(s) {
  s = s.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  let h = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  let blocks = []

  h = h.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    blocks.push({ lang: lang || '', code: code.trim() })
    return '\x00BLOCK' + (blocks.length - 1) + '\x00'
  })

  let tables = []
  h = h.replace(/(^\|.+\|\n^\|[-: |]+\|\n(?:^\|.+\|\n?)+)/gm, (m) => {
    tables.push(m)
    return '\x00TABLE' + (tables.length - 1) + '\x00'
  })

  h = h.replace(/^[-*_]{3,}$/gm, '<hr>')
  h = h.replace(/`([^`]+)`/g, '<code>$1</code>')
  h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  h = h.replace(/\*(.+?)\*/g, '<em>$1</em>')
  h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  h = h.replace(/^- (.+)$/gm, '<li-u>$1</li-u>')
  h = h.replace(/^\d+\. (.+)$/gm, '<li-o>$1</li-o>')
  h = h.replace(/(<\/li-[uo]>)\n{2,}(<li-[uo]>)/g, '$1\n$2')
  h = h.replace(/((?:<li-u>.*<\/li-u>\n?)+)/g, '<ul>$1</ul>')
  h = h.replace(/((?:<li-o>.*<\/li-o>\n?)+)/g, '<ol>$1</ol>')
  h = h.replace(/<\/?li-[uo]>/g, (m) => m.replace(/-[uo]/, ''))
  h = h.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')

  h = h.replace(/\x00TABLE(\d+)\x00/g, (_, i) => {
    let t = tables[+i], lines = t.trim().split('\n')
    if (lines.length < 2) return t
    let parseRow = r => r.replace(/^\||\|$/g, '').split('|').map(c => c.trim())
    let hdr = parseRow(lines[0]), body = lines.slice(2).map(parseRow)
    let html = '<table><thead><tr>' + hdr.map(c => '<th>' + rinline(c) + '</th>').join('') + '</tr></thead><tbody>'
    body.forEach(r => { html += '<tr>' + r.map(c => '<td>' + rinline(c) + '</td>').join('') + '</tr>' })
    html += '</tbody></table>'
    return html
  })

  h = h.replace(/\x00BLOCK(\d+)\x00/g, (_, i) => {
    let b = blocks[+i]
    let langTag = b.lang ? '<span class="lang-tag">' + b.lang + '</span>' : ''
    let escaped = b.code.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    return '<div class="code-block">' + langTag +
      '<button class="copy-btn" onclick="navigator.clipboard.writeText(this.dataset.code);this.textContent=\'Copied!\';this.classList.add(\'copied\');setTimeout(()=>{this.textContent=\'Copy\';this.classList.remove(\'copied\')},2000)" data-code="' + escaped + '">Copy</button>' +
      '<pre><code>' + b.code + '</code></pre></div>'
  })

  return h.split(/\n{2,}/).map(b => {
    let t = b.trim()
    if (!t) return ''
    if (/^<(h[1-4]|ol|ul|table|blockquote|hr|div|pre)\b/.test(t)) return t
    return '<p>' + t + '</p>'
  }).join('')
}

export function stripMd(s) {
  return s.replace(/```[\s\S]*?```/g, '').replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*(.+?)\*\*/g, '$1').replace(/\*(.+?)\*/g, '$1')
    .replace(/^#{1,4} (.+)$/gm, '$1').replace(/^- (.+)$/gm, '$1')
    .replace(/^\d+\. (.+)$/gm, '$1').replace(/^\|.+\|$/gm, '')
    .replace(/^> (.+)$/gm, '$1').replace(/^[-*_]{3,}$/gm, '')
    .replace(/\n{2,}/g, '\n').trim()
}
