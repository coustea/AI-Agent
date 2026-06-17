const fs = require('fs');
const path = require('path');

async function fetchChunk(text) {
  const encodedText = encodeURIComponent(text);
  const url = `https://translate.google.com/translate_tts?ie=UTF-8&tl=zh-CN&client=tw-ob&q=${encodedText}`;
  
  const res = await fetch(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
  });
  
  if (!res.ok) {
    throw new Error(`Failed to fetch TTS for text "${text}": ${res.statusText}`);
  }
  
  return Buffer.from(await res.arrayBuffer());
}

function splitText(text, maxLength = 180) {
  const sentences = text.match(/[^，。！？；、,\.\?!;]+[，。！？；、,\.\?!;]*/g) || [text];
  const chunks = [];
  let currentChunk = '';

  for (const sentence of sentences) {
    if ((currentChunk + sentence).length > maxLength) {
      if (currentChunk) {
        chunks.push(currentChunk);
      }
      currentChunk = sentence;
    } else {
      currentChunk += sentence;
    }
  }
  if (currentChunk) {
    chunks.push(currentChunk);
  }
  return chunks;
}

async function generateTTS() {
  const planPath = path.join(__dirname, '../input/rich_video_plan.json');
  const outputPlanPath = path.join(__dirname, '../input/rich_video_plan_voice.json');
  const voiceDir = path.join(__dirname, '../public/voice');

  if (!fs.existsSync(voiceDir)) {
    fs.mkdirSync(voiceDir, { recursive: true });
  }

  console.log('Reading video plan:', planPath);
  const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));

  console.log('Starting Chinese TTS generation for scenes...');

  for (let i = 0; i < plan.scenes.length; i++) {
    const scene = plan.scenes[i];
    const narration = scene.narration;

    if (narration && narration.trim()) {
      console.log(`[Scene ${i + 1}/${plan.scenes.length}] Generating audio for: "${narration.substring(0, 25)}..."`);
      const destPath = path.join(voiceDir, `scene_${scene.id}.mp3`);
      
      try {
        if (narration.length <= 180) {
          const buffer = await fetchChunk(narration);
          fs.writeFileSync(destPath, buffer);
        } else {
          const chunks = splitText(narration, 180);
          const buffers = [];
          for (const chunk of chunks) {
            buffers.push(await fetchChunk(chunk));
          }
          fs.writeFileSync(destPath, Buffer.concat(buffers));
        }
        
        // Inject voiceover path (web-accessible relative to public root)
        scene.audio_src = `/voice/scene_${scene.id}.mp3`;
        console.log(` -> Saved voiceover to: public/voice/scene_${scene.id}.mp3`);
      } catch (err) {
        console.error(` -> Error generating TTS for scene ${scene.id}:`, err.message);
      }
    }
  }

  // Save the voice-enabled plan
  fs.writeFileSync(outputPlanPath, JSON.stringify(plan, null, 2));
  console.log('\nSuccess! Voice-enabled video plan saved to:', outputPlanPath);
  console.log('You can now render the video with voiceover using:');
  console.log('  npx remotion render MainVideo out/sync_01_voice.mp4 --props=input/rich_video_plan_voice.json');
}

generateTTS().catch(console.error);
