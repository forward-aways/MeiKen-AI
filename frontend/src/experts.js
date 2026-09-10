// Built-in expert team: maps agent names to identity visuals (SVG icons, colors).
// Title/tagline text lives in i18n under the given keys.

export const EXPERTS = [
  {
    agentName: 'general',
    titleKey: 'expertGeneral',
    tagKey: 'tagGeneral',
    color: '#5b57d2',
    icon: '<rect x="4" y="4" width="16" height="16" rx="4"/><circle cx="9" cy="10" r="1.6"/><path d="M7 16c.8-1.4 2.4-2 4-2s3.2.6 4 2"/>'
  },
  {
    agentName: 'coder',
    titleKey: 'expertCoder',
    tagKey: 'tagCoder',
    color: '#0ea5e9',
    icon: '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>'
  },
  {
    agentName: 'analyst',
    titleKey: 'expertAnalyst',
    tagKey: 'tagAnalyst',
    color: '#f59e0b',
    icon: '<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/>'
  },
  {
    agentName: 'researcher',
    titleKey: 'expertResearcher',
    tagKey: 'tagResearcher',
    color: '#10b981',
    icon: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>'
  },
  {
    agentName: 'writer',
    titleKey: 'expertWriter',
    tagKey: 'tagWriter',
    color: '#ec4899',
    icon: '<path d="M12 19l7-7 3 3-7 7-3-3z"/><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/><path d="M2 2l7.586 7.586"/><circle cx="11" cy="11" r="2"/>'
  }
]

export function expertForAgent(agent) {
  if (!agent) return null
  const e = EXPERTS.find((x) => x.agentName === agent.name)
  if (e) return { ...e, displayName: agent.display_name }
  return {
    agentName: agent.name,
    titleKey: null,
    tagKey: null,
    color: '#8b5cf6',
    icon: '<rect x="4" y="4" width="16" height="16" rx="4"/><circle cx="9" cy="10" r="1.6"/><path d="M7 16c.8-1.4 2.4-2 4-2s3.2.6 4 2"/>',
    displayName: agent.display_name || agent.name
  }
}