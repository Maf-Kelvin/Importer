// scripts/check-imports.mjs
// Verifies that every relative or "@/" import points at a real file and that every NAMED import is really
// exported by that file. Catches the "module renamed / function missing" class of bug that only explodes at
// runtime. Needs only the `typescript` package.   Usage: node scripts/check-imports.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const src = path.join(root, 'src');
const EXT = ['.ts', '.tsx'];

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return e.name === 'generated' ? [] : walk(p);
    return EXT.includes(path.extname(p)) ? [p] : [];
  });
}

function resolveModule(spec, from) {
  const base = spec.startsWith('@/') ? path.join(src, spec.slice(2)) : path.resolve(path.dirname(from), spec);
  const candidates = [base, ...EXT.map((e) => base + e), ...EXT.map((e) => path.join(base, 'index' + e))];
  return candidates.find((c) => fs.existsSync(c) && fs.statSync(c).isFile()) ?? null;
}

const parsed = new Map();
function parse(file) {
  if (!parsed.has(file)) parsed.set(file, ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, file.endsWith('x') ? ts.ScriptKind.TSX : ts.ScriptKind.TS));
  return parsed.get(file);
}

const exportCache = new Map();
function exportsOf(file, seen = new Set()) {
  if (exportCache.has(file)) return exportCache.get(file);
  if (seen.has(file)) return { names: new Set(), hasDefault: false };
  seen.add(file);
  const names = new Set();
  let hasDefault = false;
  const hasExport = (n) => n.modifiers?.some((m) => m.kind === ts.SyntaxKind.ExportKeyword);
  for (const n of parse(file).statements) {
    if (ts.isExportDeclaration(n)) {
      if (n.exportClause && ts.isNamedExports(n.exportClause)) n.exportClause.elements.forEach((e) => names.add(e.name.text));
      else if (!n.exportClause && n.moduleSpecifier) {
        const target = resolveModule(n.moduleSpecifier.text, file);
        if (target) exportsOf(target, seen).names.forEach((x) => names.add(x)); // export * from
      } else if (n.exportClause && ts.isNamespaceExport(n.exportClause)) names.add(n.exportClause.name.text);
    } else if (ts.isExportAssignment(n)) hasDefault = true;
    else if (hasExport(n)) {
      if (n.modifiers.some((m) => m.kind === ts.SyntaxKind.DefaultKeyword)) hasDefault = true;
      if (ts.isVariableStatement(n)) n.declarationList.declarations.forEach((d) => ts.isIdentifier(d.name) && names.add(d.name.text));
      else if (n.name) names.add(n.name.text);
    }
  }
  const result = { names, hasDefault };
  exportCache.set(file, result);
  return result;
}

const problems = [];
let checked = 0;
for (const file of walk(src)) {
  const sf = parse(file);
  const rel = path.relative(root, file);
  for (const n of sf.statements) {
    const spec = (ts.isImportDeclaration(n) || ts.isExportDeclaration(n)) && n.moduleSpecifier ? n.moduleSpecifier.text : null;
    if (!spec || !(spec.startsWith('.') || spec.startsWith('@/'))) continue;
    checked += 1;
    const line = sf.getLineAndCharacterOfPosition(n.getStart()).line + 1;
    if (spec.includes('/generated/')) continue; // created by `npm run api:generate`, not committed
    const target = resolveModule(spec, file);
    if (!target) {
      // assets such as ./index.css are allowed when they exist
      const asset = spec.startsWith('@/') ? path.join(src, spec.slice(2)) : path.resolve(path.dirname(file), spec);
      if (!fs.existsSync(asset)) problems.push(`${rel}:${line}  cannot resolve '${spec}'`);
      continue;
    }
    if (ts.isImportDeclaration(n) && n.importClause) {
      const { names, hasDefault } = exportsOf(target);
      if (n.importClause.name && !hasDefault) problems.push(`${rel}:${line}  '${spec}' has no default export`);
      const nb = n.importClause.namedBindings;
      if (nb && ts.isNamedImports(nb)) for (const el of nb.elements) {
        const imported = (el.propertyName ?? el.name).text;
        if (!names.has(imported)) problems.push(`${rel}:${line}  '${imported}' is not exported by '${spec}'`);
      }
    }
    if (ts.isExportDeclaration(n) && n.exportClause && ts.isNamedExports(n.exportClause)) {
      const { names } = exportsOf(target);
      for (const el of n.exportClause.elements) {
        const imported = (el.propertyName ?? el.name).text;
        if (!names.has(imported)) problems.push(`${rel}:${line}  re-exports '${imported}', which '${spec}' does not export`);
      }
    }
  }
}
console.log(`checked ${checked} local imports in ${walk(src).length} files`);
if (problems.length) {
  console.log(`${problems.length} PROBLEM(S):`);
  problems.forEach((p) => console.log('  -', p));
  process.exit(1);
}
console.log('all local imports resolve');
