#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';

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

function normalizeReplaceEntries(mapping) {
  return Object.entries(mapping).map(([placeholder, value]) => ({
    replace: String(placeholder).replace(/^\{\{/, '').replace(/\}\}$/, ''),
    by: { text: String(value ?? '') },
  }));
}

async function run() {
  const args = parseArgs(process.argv.slice(2));
  const templatePptx = path.resolve(process.cwd(), args['template-pptx']);
  const manifestPath = path.resolve(process.cwd(), args.manifest);
  const mappingJson = path.resolve(process.cwd(), args['mapping-json']);
  const output = path.resolve(process.cwd(), args.output);
  const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf-8'));
  const mapping = JSON.parse(await fs.readFile(mappingJson, 'utf-8'));
  const slideCount = Number(manifest.slide_count || 0);
  if (!slideCount) throw new Error('Invalid manifest.slide_count');

  const mod = await import('pptx-automizer');
  const Automizer = mod.Automizer;
  const { modify } = mod;
  const templateDir = path.dirname(templatePptx);
  const templateName = path.basename(templatePptx);
  const outputDir = path.dirname(output);
  const outputName = path.basename(output);
  const replacements = normalizeReplaceEntries(mapping);

  const automizer = new Automizer({
    templateDir,
    outputDir,
    removeExistingSlides: true,
    autoImportSlideMasters: true,
    cleanup: true,
    verbosity: 0,
  });

  let pres = automizer.loadRoot(templateName).load(templateName, 'tpl');
  for (let slideNo = 1; slideNo <= slideCount; slideNo += 1) {
    pres = pres.addSlide('tpl', slideNo, async (slide) => {
      const ids = await slide.getAllTextElementIds();
      ids.forEach((id) => slide.modifyElement(id, [modify.replaceText(replacements)]));
    });
  }
  await pres.write(outputName);
}

run().catch((error) => {
  console.error(`Error: ${error.message}`);
  process.exitCode = 1;
});
