import { readFileSync } from 'node:fs'

const sourceRoot = new URL('../src/', import.meta.url)
const styleOrder = [
  'base',
  'architecture',
  'how-it-works',
  'registry',
  'workspaces',
  'ranking',
  'feed',
  'artifacts',
  'insights',
  'bit-lens',
]

export const readSource = (path) =>
  readFileSync(new URL(path, sourceRoot), 'utf8')

export const readStyles = () =>
  styleOrder.map((name) => readSource(`styles/${name}.css`)).join('\n')
