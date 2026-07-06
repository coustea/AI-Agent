import asyncio
import sys
from pathlib import Path

# Add server directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.shared.cartoon.pipeline import CartoonPipeline
from app.shared.cartoon.schemas import CartoonVideoRequest
from app.shared.cartoon.renderer import CartoonVideoRenderer


async def main():
    output_dir = Path(__file__).resolve().parent / "output_bst"
    output_dir.mkdir(parents=True, exist_ok=True)

    request = CartoonVideoRequest(
        learning_need="二叉搜索树（BST）的构建与节点插入过程。从空树开始，以纯动画、纯图形的形式展示依次插入 5（根）、3、7、4、6，最终构建出一个包含三层的完整二叉搜索树的过程。不需要在画面上体现代码，重点是精细而饱满的动画演示。每次插入新节点时，必须展示从根节点开始的路径查找比对动画（高亮路径、粒子沿线流动等）。配合使用比较状态指标卡和步骤看板丰富画面布局，样式使用简约白色的风格。",
        profile="计算机专业大二学生，正在学习数据结构，需要清晰的可视化逻辑",
        style="minimal",  # 使用简约白色主题
        depth="deep",
        pace="normal",
        visuals="detailed",
        output_dir=output_dir,
    )

    async def progress_callback(message: str, percent: int) -> None:
        print(f"[{percent}%] {message}")

    pipeline = CartoonPipeline(renderer=CartoonVideoRenderer())
    print("Starting cartoon generation for BST...")
    try:
        artifact = await pipeline.generate(request, progress=progress_callback)
        print("\nSuccess!")
        print(f"HTML output saved to: {output_dir / 'index.html'}")
        print(f"Video output: {artifact.video_path} ({artifact.video_path.stat().st_size} bytes)")
        print(f"Total duration: {artifact.brief.total_duration} seconds")
        print(f"Scene count: {artifact.scene_count}")
        print(f"Render profile: {artifact.render_profile}")
    except Exception as e:
        print(f"\nFailed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
