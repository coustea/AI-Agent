import { makeScene2D } from '@motion-canvas/2d';
import { renderScene } from '../renderer/TemplateRouter';
import { renderErrorScene } from '../renderer/ErrorScene';
import videoPlanData from '../data/video_plan.json';
import { TeachingVideoPlan } from '../schema/videoPlan';
import { setThemeStyle } from '../styles/theme';
import type { ThemeStyle } from '../styles/theme';

export default makeScene2D(function* (view) {
  // Cast JSON data safely
  const plan = videoPlanData as any as TeachingVideoPlan;

  // Validate plan structure
  if (!plan || plan.resource_type !== 'computer_teaching_video' || !Array.isArray(plan.scenes)) {
    yield* renderErrorScene(view, {
      title: 'Validation',
      errorMessage: 'Invalid video plan JSON structure. Must match "TeachingVideoPlan" format.',
      duration: 10,
    });
    return;
  }

  // Apply user style preference to theme
  const style = plan.user_config?.style || 'clean';
  setThemeStyle(style as ThemeStyle);

  // Run scenes sequentially
  for (let idx = 0; idx < plan.scenes.length; idx++) {
    const scene = plan.scenes[idx];

    // Clear canvas between scenes
    view.removeChildren();

    // Delegate rendering to router
    const renderMode = plan.video_config?.mode || 'standard';
    yield* renderScene(view, scene, renderMode);
  }
});
