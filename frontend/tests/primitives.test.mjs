import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import Module from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ts from 'typescript'

const here = path.dirname(fileURLToPath(import.meta.url))
const componentPath = path.resolve(here, '../src/components/Primitives.tsx')
const source = readFileSync(componentPath, 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText
const componentModule = new Module(componentPath)
componentModule.filename = componentPath
componentModule.paths = Module._nodeModulePaths(path.dirname(componentPath))
componentModule._compile(compiled, componentPath)
const { ErrorState, EmptyState } = componentModule.exports

test('error state renders a useful message and retry control', () => {
  const markup = renderToStaticMarkup(React.createElement(ErrorState, { message: 'API offline', retry: () => {} }))
  assert.match(markup, /Algo não saiu como esperado/)
  assert.match(markup, /API offline/)
  assert.match(markup, /Tentar novamente/)
})

test('empty state renders its title and guidance', () => {
  const markup = renderToStaticMarkup(React.createElement(EmptyState, { title: 'Nenhum jogo', detail: 'Adicione seu primeiro jogo.' }))
  assert.match(markup, /Nenhum jogo/)
  assert.match(markup, /Adicione seu primeiro jogo\./)
})
