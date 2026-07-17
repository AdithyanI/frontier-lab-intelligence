import { readFileSync } from 'node:fs'

const sourceRoot = new URL('../src/', import.meta.url)
const styleOrder = [
  'base',
  'architecture',
  'status',
  'registry',
  'workspaces',
  'ranking',
  'feed',
  'artifacts',
  'insights',
]

export const readSource = (path) =>
  readFileSync(new URL(path, sourceRoot), 'utf8')

export const readStyles = () =>
  styleOrder.map((name) => readSource(`styles/${name}.css`)).join('\n')
