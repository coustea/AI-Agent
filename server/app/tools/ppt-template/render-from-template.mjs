#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import JSZip from 'jszip';
import { XMLParser, XMLBuilder } from 'fast-xml-parser';

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const value = argv[i + 1];
      if (!value || value.startsWith('--')) throw new Error(`Missing value for --${key}`);
      args[key] = value;
      i += 1;
    }
  }
  return args;
}

function collectSlideFiles(fileNames) {
  return fileNames
    .filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name))
    .sort((a, b) => Number(a.match(/slide(\d+)\.xml$/)[1]) - Number(b.match(/slide(\d+)\.xml$/)[1]));
}

function replaceTextNodes(node, mapping) {
  if (Array.isArray(node)) return node.forEach((item) => replaceTextNodes(item, mapping));
  if (!node || typeof node !== 'object') return;
  Object.entries(node).forEach(([key, value]) => {
    if (key === 'a:t' && typeof value === 'string' && typeof mapping[value] === 'string') {
      node[key] = mapping[value];
      return;
    }
    replaceTextNodes(value, mapping);
  });
}

async function run() {
  const args = parseArgs(process.argv.slice(2));
  const templatePptx = path.resolve(process.cwd(), args['template-pptx']);
  const mappingJson = path.resolve(process.cwd(), args['mapping-json']);
  const output = path.resolve(process.cwd(), args.output);
  const mapping = JSON.parse(await fs.readFile(mappingJson, 'utf-8'));

  const zip = await JSZip.loadAsync(await fs.readFile(templatePptx));
  const parser = new XMLParser({ ignoreAttributes: false, trimValues: false, parseTagValue: false, preserveOrder: false });
  const builder = new XMLBuilder({ ignoreAttributes: false, preserveOrder: false, suppressEmptyNode: false, format: false });

  for (const slidePath of collectSlideFiles(Object.keys(zip.files))) {
    const xml = await zip.file(slidePath)?.async('string');
    if (!xml) continue;
    const parsed = parser.parse(xml);
    replaceTextNodes(parsed, mapping);
    zip.file(slidePath, builder.build(parsed));
  }

  await fs.writeFile(output, await zip.generateAsync({ type: 'nodebuffer' }));
}

run().catch((error) => {
  console.error(`Error: ${error.message}`);
  process.exitCode = 1;
});
