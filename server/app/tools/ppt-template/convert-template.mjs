#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import JSZip from 'jszip';
import { XMLParser, XMLBuilder } from 'fast-xml-parser';


function printHelp() {
  console.log(`Usage:
  node server/app/tools/ppt-template/convert-template.mjs --input <input.pptx> [--output <template.pptx>] [--manifest <template.manifest.json>] [--prefix <name>]

Options:
  --input     Input PPTX path (required)
  --output    Output PPTX path (default: <input>.template.pptx)
  --manifest  Manifest path (default: <output>.manifest.json)
  --prefix    Placeholder prefix (default: slide)
`);
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') {
      args.help = true;
      continue;
    }
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const value = argv[i + 1];
      if (value === undefined || value.startsWith('--')) {
        throw new Error(`Missing value for --${key}`);
      }
      args[key] = value;
      i += 1;
    }
  }
  return args;
}

function normalizeText(value) {
  return String(value).replace(/\s+/g, ' ').trim();
}

function shouldReplace(text) {
  if (!text) return false;
  if (text.startsWith('{{') && text.endsWith('}}')) return false;
  if (!/[\p{L}\p{N}]/u.test(text)) return false;
  return true;
}

function collectSlideFiles(fileNames) {
  return fileNames
    .filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name))
    .sort((a, b) => {
      const ai = Number((a.match(/slide(\d+)\.xml$/) || [])[1] || 0);
      const bi = Number((b.match(/slide(\d+)\.xml$/) || [])[1] || 0);
      return ai - bi;
    });
}

function visitAndReplace(node, context, pushRecord) {
  if (Array.isArray(node)) {
    node.forEach((item) => visitAndReplace(item, context, pushRecord));
    return;
  }
  if (!node || typeof node !== 'object') {
    return;
  }

  Object.entries(node).forEach(([key, value]) => {
    if (key === 'a:t' && typeof value === 'string') {
      const original = normalizeText(value);
      if (!shouldReplace(original)) {
        return;
      }
      context.textIndex += 1;
      const placeholder = `{{${context.prefix}_${String(context.slideIndex).padStart(2, '0')}_${String(context.textIndex).padStart(2, '0')}}}`;
      node[key] = placeholder;
      pushRecord({
        slide_index: context.slideIndex,
        text_index: context.textIndex,
        original_text: original,
        placeholder,
      });
      return;
    }

    visitAndReplace(value, context, pushRecord);
  });
}

async function run() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    return;
  }

  if (!args.input) {
    throw new Error('Missing required argument --input');
  }

  const inputPath = path.resolve(process.cwd(), args.input);
  const outputPath = args.output
    ? path.resolve(process.cwd(), args.output)
    : path.join(path.dirname(inputPath), `${path.basename(inputPath, '.pptx')}.template.pptx`);
  const manifestPath = args.manifest
    ? path.resolve(process.cwd(), args.manifest)
    : outputPath.replace(/\.pptx$/i, '.manifest.json');
  const prefix = args.prefix || 'slide';

  const bytes = await fs.readFile(inputPath);
  const zip = await JSZip.loadAsync(bytes);

  const parser = new XMLParser({
    ignoreAttributes: false,
    trimValues: false,
    parseTagValue: false,
    preserveOrder: false,
  });
  const builder = new XMLBuilder({
    ignoreAttributes: false,
    preserveOrder: false,
    suppressEmptyNode: false,
    format: false,
  });

  const slideFiles = collectSlideFiles(Object.keys(zip.files));
  if (slideFiles.length === 0) {
    throw new Error('No slide XML files found under ppt/slides/');
  }

  const replacements = [];

  for (let i = 0; i < slideFiles.length; i += 1) {
    const slidePath = slideFiles[i];
    const slideIndex = i + 1;
    const xml = await zip.file(slidePath)?.async('string');
    if (!xml) {
      continue;
    }

    const parsed = parser.parse(xml);
    const context = { slideIndex, textIndex: 0, prefix };

    visitAndReplace(parsed, context, (item) => replacements.push({ slide_path: slidePath, ...item }));

    const newXml = builder.build(parsed);
    zip.file(slidePath, newXml);
  }

  const outBuffer = await zip.generateAsync({ type: 'nodebuffer' });
  await fs.writeFile(outputPath, outBuffer);

  const manifest = {
    tool: 'ppt-template-converter',
    version: '1.0.0',
    created_at: new Date().toISOString(),
    input: path.relative(process.cwd(), inputPath),
    output: path.relative(process.cwd(), outputPath),
    slide_count: slideFiles.length,
    replacement_count: replacements.length,
    placeholder_prefix: prefix,
    replacements,
  };

  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf-8');

  console.log(`Input:     ${inputPath}`);
  console.log(`Output:    ${outputPath}`);
  console.log(`Manifest:  ${manifestPath}`);
  console.log(`Slides:    ${slideFiles.length}`);
  console.log(`Replaced:  ${replacements.length}`);
}

run().catch((error) => {
  console.error(`Error: ${error.message}`);
  process.exitCode = 1;
});
