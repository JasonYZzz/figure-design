import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import manifest from './package.json' with { type: 'json' }
import skill from './skill.json' with { type: 'json' }

export const name = 'figure-design'
export const inject = ['skills']

export function apply(ctx) {
  const base = new URL(`./skills/${skill.name}/`, import.meta.url)
  const path = fileURLToPath(new URL('SKILL.md', base))
  const content = readFileSync(path, 'utf8').replace(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/, '').trim()
  ctx.skills.register({
    ...skill,
    name: manifest.name,
    source: 'runtime',
    path,
    content,
    resourceBase: { kind: 'directory', path: fileURLToPath(base) },
  })
}
